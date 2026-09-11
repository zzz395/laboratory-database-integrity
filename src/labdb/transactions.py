"""Atomic equipment-transfer transaction and reconciliation support."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import pymysql
from pymysql.connections import Connection
from pymysql.constants.SERVER_STATUS import SERVER_STATUS_IN_TRANS

from .config import DatabaseConfig
from .db import connect_server
from .errors import (
    CommitOutcomeUnknown,
    EquipmentNotFound,
    InvalidTransferInput,
    SameSourceTarget,
    StaleSource,
    TargetNotFound,
    TransactionAlreadyActive,
    TransferDatabaseError,
    TransferIdConflict,
    TransferRefused,
)
from .initialize import quote_validated_database_name


Clock = Callable[[], datetime]
ConnectFactory = Callable[[DatabaseConfig], Connection]


@dataclass(frozen=True)
class TransferResult:
    transfer_id: str
    equipment_id: str
    source_lab_id: str
    target_lab_id: str
    transferred_at: datetime
    reason: str


@dataclass(frozen=True)
class TransferRecord:
    transfer_id: str
    equipment_id: str
    source_lab_id: str
    target_lab_id: str
    transferred_at: datetime
    reason: str


class ReconciliationStatus(str, Enum):
    MATCHING_COMMITTED = "MATCHING_COMMITTED"
    NOT_FOUND = "NOT_FOUND"
    ID_CONFLICT = "TRANSFER_ID_CONFLICT"


@dataclass(frozen=True)
class ReconciliationResult:
    status: ReconciliationStatus
    record: TransferRecord | None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _validate_nonblank(value: str, name: str, maximum: int) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise InvalidTransferInput(
            f"{name} must be a nonblank string of at most {maximum} characters"
        )


def _validate_transfer_input(
    transfer_id: str,
    equipment_id: str,
    source_lab_id: str,
    target_lab_id: str,
    reason: str,
) -> None:
    _validate_nonblank(transfer_id, "transfer_id", 32)
    _validate_nonblank(equipment_id, "equipment_id", 32)
    _validate_nonblank(source_lab_id, "source_lab_id", 32)
    _validate_nonblank(target_lab_id, "target_lab_id", 32)
    _validate_nonblank(reason, "reason", 1000)


def _transaction_is_active(connection: Connection) -> bool:
    try:
        server_status = connection.server_status
    except (AttributeError, TypeError) as exc:
        raise TransferDatabaseError(
            "could not confirm the connection transaction state"
        ) from exc
    if not isinstance(server_status, int):
        raise TransferDatabaseError(
            "could not confirm the connection transaction state"
        )
    return bool(server_status & SERVER_STATUS_IN_TRANS)


def _discard_connection(connection: Connection) -> None:
    try:
        connection.close()
    except Exception:
        pass


def _rollback_or_raise_database_error(connection: Connection) -> None:
    try:
        connection.rollback()
    except Exception as exc:
        _discard_connection(connection)
        raise TransferDatabaseError(
            "a pre-commit failure occurred and rollback could not be confirmed"
        ) from exc


def _as_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise InvalidTransferInput("clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _is_duplicate_key(exc: pymysql.MySQLError) -> bool:
    return bool(exc.args) and exc.args[0] == 1062


def transfer_equipment(
    connection: Connection,
    transfer_id: str,
    equipment_id: str,
    source_lab_id: str,
    target_lab_id: str,
    reason: str,
    *,
    clock: Clock = _utc_now,
) -> TransferResult:
    """Move one equipment row and append its history as one transaction.

    The caller must provide a connection with the target database selected and
    no active transaction. A COMMIT exception is deliberately not rolled back
    or retried because the server outcome may already be durable.
    """

    _validate_transfer_input(
        transfer_id, equipment_id, source_lab_id, target_lab_id, reason
    )
    if _transaction_is_active(connection):
        raise TransactionAlreadyActive(
            "the connection already has an active transaction"
        )

    try:
        connection.begin()
    except pymysql.MySQLError as exc:
        raise TransferDatabaseError("could not start the transfer transaction") from exc

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT `设备编号`, `实验室编号` FROM `实验设备` "
                "WHERE `设备编号` = %s FOR UPDATE",
                (equipment_id,),
            )
            equipment = cursor.fetchone()
            if equipment is None:
                raise EquipmentNotFound(
                    f"equipment {equipment_id!r} does not exist"
                )

            current_lab_id = equipment["实验室编号"]
            if current_lab_id != source_lab_id:
                raise StaleSource(
                    f"equipment {equipment_id!r} is not currently in source "
                    f"laboratory {source_lab_id!r}"
                )
            if source_lab_id == target_lab_id:
                raise SameSourceTarget(
                    "source and target laboratories must be different"
                )

            cursor.execute(
                "SELECT `实验室编号` FROM `实验室` "
                "WHERE `实验室编号` = %s FOR SHARE",
                (target_lab_id,),
            )
            if cursor.fetchone() is None:
                raise TargetNotFound(
                    f"target laboratory {target_lab_id!r} does not exist"
                )

            cursor.execute(
                "UPDATE `实验设备` SET `实验室编号` = %s "
                "WHERE `设备编号` = %s",
                (target_lab_id, equipment_id),
            )
            if cursor.rowcount != 1:
                raise TransferDatabaseError(
                    "equipment location update did not affect exactly one row"
                )

            transferred_at = _as_utc(clock())
            database_timestamp = transferred_at.replace(tzinfo=None)
            cursor.execute(
                "INSERT INTO `设备移库记录` "
                "(`移库记录编号`, `设备编号`, `原实验室编号`, "
                "`目标实验室编号`, `移动时间`, `移动原因`) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    transfer_id,
                    equipment_id,
                    source_lab_id,
                    target_lab_id,
                    database_timestamp,
                    reason,
                ),
            )
    except TransferRefused:
        _rollback_or_raise_database_error(connection)
        raise
    except pymysql.MySQLError as exc:
        _rollback_or_raise_database_error(connection)
        if _is_duplicate_key(exc):
            raise TransferIdConflict(
                f"transfer ID {transfer_id!r} already exists"
            ) from exc
        raise TransferDatabaseError(
            "database execution failed before commit; the transaction was rolled back"
        ) from exc
    except Exception as exc:
        _rollback_or_raise_database_error(connection)
        if isinstance(exc, TransferDatabaseError):
            raise
        raise TransferDatabaseError(
            "transfer execution failed before commit; the transaction was rolled back"
        ) from exc

    try:
        connection.commit()
    except Exception as exc:
        _discard_connection(connection)
        raise CommitOutcomeUnknown(transfer_id) from exc

    return TransferResult(
        transfer_id=transfer_id,
        equipment_id=equipment_id,
        source_lab_id=source_lab_id,
        target_lab_id=target_lab_id,
        transferred_at=transferred_at,
        reason=reason,
    )


def find_transfer_by_id(
    connection: Connection, transfer_id: str
) -> TransferRecord | None:
    """Read one transfer record from an independently established session."""

    _validate_nonblank(transfer_id, "transfer_id", 32)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT `移库记录编号`, `设备编号`, `原实验室编号`, "
                "`目标实验室编号`, `移动时间`, `移动原因` "
                "FROM `设备移库记录` WHERE `移库记录编号` = %s",
                (transfer_id,),
            )
            row = cursor.fetchone()
    except pymysql.MySQLError as exc:
        raise TransferDatabaseError("transfer reconciliation query failed") from exc
    if row is None:
        return None
    transferred_at = row["移动时间"]
    if transferred_at.tzinfo is None:
        transferred_at = transferred_at.replace(tzinfo=timezone.utc)
    else:
        transferred_at = transferred_at.astimezone(timezone.utc)
    return TransferRecord(
        transfer_id=row["移库记录编号"],
        equipment_id=row["设备编号"],
        source_lab_id=row["原实验室编号"],
        target_lab_id=row["目标实验室编号"],
        transferred_at=transferred_at,
        reason=row["移动原因"],
    )


def _open_database(
    config: DatabaseConfig, connect_factory: ConnectFactory | None
) -> Connection:
    factory = connect_server if connect_factory is None else connect_factory
    connection = factory(config)
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"USE {quote_validated_database_name(config.database)}")
    except pymysql.MySQLError as exc:
        _discard_connection(connection)
        raise TransferDatabaseError(
            "could not select the configured database"
        ) from exc
    except Exception:
        _discard_connection(connection)
        raise
    return connection


def transfer_equipment_for_config(
    config: DatabaseConfig,
    transfer_id: str,
    equipment_id: str,
    source_lab_id: str,
    target_lab_id: str,
    reason: str,
    *,
    clock: Clock = _utc_now,
    connect_factory: ConnectFactory | None = None,
) -> TransferResult:
    """Open a safe session, select the configured database, and transfer."""

    connection = _open_database(config, connect_factory)
    try:
        return transfer_equipment(
            connection,
            transfer_id,
            equipment_id,
            source_lab_id,
            target_lab_id,
            reason,
            clock=clock,
        )
    finally:
        _discard_connection(connection)


def reconcile_transfer_for_config(
    config: DatabaseConfig,
    transfer_id: str,
    equipment_id: str,
    source_lab_id: str,
    target_lab_id: str,
    reason: str,
    *,
    connect_factory: ConnectFactory | None = None,
) -> ReconciliationResult:
    """Confirm a stable transfer ID using a newly opened read-only session."""

    _validate_transfer_input(
        transfer_id, equipment_id, source_lab_id, target_lab_id, reason
    )
    connection = _open_database(config, connect_factory)
    try:
        record = find_transfer_by_id(connection, transfer_id)
    finally:
        _discard_connection(connection)
    if record is None:
        return ReconciliationResult(ReconciliationStatus.NOT_FOUND, None)
    expected = (
        transfer_id,
        equipment_id,
        source_lab_id,
        target_lab_id,
        reason,
    )
    actual = (
        record.transfer_id,
        record.equipment_id,
        record.source_lab_id,
        record.target_lab_id,
        record.reason,
    )
    status = (
        ReconciliationStatus.MATCHING_COMMITTED
        if actual == expected
        else ReconciliationStatus.ID_CONFLICT
    )
    return ReconciliationResult(status, record)
