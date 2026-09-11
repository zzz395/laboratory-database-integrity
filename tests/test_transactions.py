from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pymysql
import pytest
from pymysql.constants.SERVER_STATUS import SERVER_STATUS_IN_TRANS

from labdb import cli
from labdb.config import DatabaseConfig
from labdb.errors import (
    CommitOutcomeUnknown,
    EquipmentNotFound,
    InvalidTransferInput,
    SameSourceTarget,
    StaleSource,
    TargetNotFound,
    TransactionAlreadyActive,
    TransferDatabaseError,
    TransferIdConflict,
)
from labdb.transactions import (
    ReconciliationStatus,
    reconcile_transfer_for_config,
    transfer_equipment,
    transfer_equipment_for_config,
)


FIXED_TIME = datetime(2026, 7, 8, 9, 10, 11, 123456, tzinfo=timezone.utc)


class FakeCursor:
    def __init__(self, connection: "FakeConnection") -> None:
        self.connection = connection
        self.result = None
        self.rowcount = -1

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, query: str, parameters: tuple[object, ...] | None = None) -> int:
        compact = " ".join(query.split())
        self.connection.trace.append((compact, parameters))
        if compact.startswith("USE "):
            if self.connection.use_error is not None:
                raise self.connection.use_error
            self.result = None
        elif compact.endswith("FOR UPDATE"):
            self.result = (
                None
                if self.connection.location is None
                else {
                    "设备编号": parameters[0],
                    "实验室编号": self.connection.location,
                }
            )
        elif compact.endswith("FOR SHARE"):
            self.result = (
                {"实验室编号": parameters[0]}
                if self.connection.target_exists
                else None
            )
        elif compact.startswith("UPDATE `实验设备`"):
            self.connection.pending_location = parameters[0]
            self.rowcount = self.connection.update_rowcount
        elif compact.startswith("INSERT INTO `设备移库记录`"):
            if self.connection.insert_error is not None:
                raise self.connection.insert_error
            self.connection.pending_record = parameters
            self.rowcount = 1
        elif compact.startswith("SELECT `移库记录编号`"):
            self.result = self.connection.reconciliation_row
        else:
            raise AssertionError(f"unexpected SQL: {compact}")
        return self.rowcount

    def fetchone(self):
        return self.result


class FakeConnection:
    def __init__(
        self,
        *,
        location: str | None = "LAB_A",
        target_exists: bool = True,
        transaction_active: bool = False,
        update_rowcount: int = 1,
        insert_error: Exception | None = None,
        commit_error: Exception | None = None,
        use_error: Exception | None = None,
        reconciliation_row: dict[str, object] | None = None,
    ) -> None:
        self.location = location
        self.original_location = location
        self.target_exists = target_exists
        self.transaction_active = transaction_active
        self.update_rowcount = update_rowcount
        self.insert_error = insert_error
        self.commit_error = commit_error
        self.use_error = use_error
        self.reconciliation_row = reconciliation_row
        self.pending_location: object | None = None
        self.pending_record: tuple[object, ...] | None = None
        self.trace: list[tuple[str, tuple[object, ...] | None]] = []
        self.begin_count = 0
        self.commit_count = 0
        self.rollback_count = 0
        self.close_count = 0

    @property
    def server_status(self) -> int:
        return SERVER_STATUS_IN_TRANS if self.transaction_active else 0

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def begin(self) -> None:
        self.begin_count += 1
        self.transaction_active = True

    def commit(self) -> None:
        self.commit_count += 1
        if self.commit_error is not None:
            raise self.commit_error
        self.location = self.pending_location
        self.transaction_active = False

    def rollback(self) -> None:
        self.rollback_count += 1
        self.pending_location = None
        self.pending_record = None
        self.location = self.original_location
        self.transaction_active = False

    def close(self) -> None:
        self.close_count += 1


def _transfer(connection: FakeConnection):
    return transfer_equipment(
        connection,
        "MOVE_02",
        "EQ_01",
        "LAB_A",
        "LAB_B",
        "controlled reason",
        clock=lambda: FIXED_TIME,
    )


def test_success_uses_locking_read_bound_values_and_one_commit() -> None:
    connection = FakeConnection()

    result = _transfer(connection)

    assert result.transferred_at == FIXED_TIME
    assert connection.location == "LAB_B"
    assert connection.begin_count == connection.commit_count == 1
    assert connection.rollback_count == 0
    queries = [query for query, _ in connection.trace]
    assert queries == [
        "SELECT `设备编号`, `实验室编号` FROM `实验设备` WHERE `设备编号` = %s FOR UPDATE",
        "SELECT `实验室编号` FROM `实验室` WHERE `实验室编号` = %s FOR SHARE",
        "UPDATE `实验设备` SET `实验室编号` = %s WHERE `设备编号` = %s",
        "INSERT INTO `设备移库记录` (`移库记录编号`, `设备编号`, `原实验室编号`, `目标实验室编号`, `移动时间`, `移动原因`) VALUES (%s, %s, %s, %s, %s, %s)",
    ]
    assert all("EQ_01" not in query and "LAB_B" not in query for query in queries)
    assert connection.pending_record == (
        "MOVE_02",
        "EQ_01",
        "LAB_A",
        "LAB_B",
        FIXED_TIME.replace(tzinfo=None),
        "controlled reason",
    )


@pytest.mark.parametrize(
    ("connection", "arguments", "error_type"),
    [
        (FakeConnection(location=None), (), EquipmentNotFound),
        (FakeConnection(location="LAB_OTHER"), (), StaleSource),
        (FakeConnection(), ("LAB_A",), SameSourceTarget),
        (FakeConnection(target_exists=False), (), TargetNotFound),
    ],
)
def test_domain_refusals_roll_back_without_update_or_log(
    connection: FakeConnection,
    arguments: tuple[str, ...],
    error_type: type[Exception],
) -> None:
    target = arguments[0] if arguments else "LAB_B"

    with pytest.raises(error_type):
        transfer_equipment(
            connection,
            "MOVE_02",
            "EQ_01",
            "LAB_A",
            target,
            "controlled reason",
            clock=lambda: FIXED_TIME,
        )

    assert connection.rollback_count == 1
    assert connection.commit_count == 0
    assert connection.pending_record is None
    assert not any(query.startswith("UPDATE") for query, _ in connection.trace)


def test_duplicate_transfer_id_occurs_after_update_and_rolls_it_back() -> None:
    connection = FakeConnection(
        insert_error=pymysql.IntegrityError(1062, "controlled duplicate")
    )

    with pytest.raises(TransferIdConflict) as captured:
        _transfer(connection)

    assert captured.value.code == "TRANSFER_ID_CONFLICT"
    assert connection.location == "LAB_A"
    assert connection.rollback_count == 1
    queries = [query for query, _ in connection.trace]
    update_index = next(i for i, query in enumerate(queries) if query.startswith("UPDATE"))
    insert_index = next(i for i, query in enumerate(queries) if query.startswith("INSERT"))
    assert update_index < insert_index


def test_preexisting_transaction_is_refused_without_commit_or_rollback() -> None:
    connection = FakeConnection(transaction_active=True)

    with pytest.raises(TransactionAlreadyActive) as captured:
        _transfer(connection)

    assert captured.value.code == "TRANSACTION_ALREADY_ACTIVE"
    assert connection.begin_count == 0
    assert connection.commit_count == 0
    assert connection.rollback_count == 0
    assert connection.transaction_active is True
    assert connection.trace == []


def test_commit_exception_is_unknown_closes_connection_and_never_rolls_back() -> None:
    connection = FakeConnection(
        commit_error=pymysql.OperationalError(2013, "controlled acknowledgement loss")
    )

    with pytest.raises(CommitOutcomeUnknown) as captured:
        _transfer(connection)

    assert captured.value.code == "COMMIT_OUTCOME_UNKNOWN"
    assert captured.value.transfer_id == "MOVE_02"
    assert "may or may not" in str(captured.value)
    assert connection.commit_count == 1
    assert connection.rollback_count == 0
    assert connection.close_count == 1
    assert connection.begin_count == 1


def test_update_cardinality_failure_and_invalid_clock_roll_back() -> None:
    connection = FakeConnection(update_rowcount=0)
    with pytest.raises(TransferDatabaseError):
        _transfer(connection)
    assert connection.rollback_count == 1

    connection = FakeConnection()
    with pytest.raises(InvalidTransferInput, match="timezone-aware"):
        transfer_equipment(
            connection,
            "MOVE_02",
            "EQ_01",
            "LAB_A",
            "LAB_B",
            "controlled reason",
            clock=lambda: datetime(2026, 1, 1),
        )
    assert connection.rollback_count == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("transfer_id", ""),
        ("equipment_id", " " * 3),
        ("source_lab_id", "S" * 33),
        ("target_lab_id", "T" * 33),
        ("reason", "R" * 1001),
    ],
)
def test_invalid_business_values_are_rejected_before_database_work(
    field: str, value: str
) -> None:
    connection = FakeConnection()
    values = {
        "transfer_id": "MOVE_02",
        "equipment_id": "EQ_01",
        "source_lab_id": "LAB_A",
        "target_lab_id": "LAB_B",
        "reason": "controlled reason",
    }
    values[field] = value

    with pytest.raises(InvalidTransferInput):
        transfer_equipment(connection, **values, clock=lambda: FIXED_TIME)

    assert connection.trace == []
    assert connection.begin_count == connection.rollback_count == 0


def test_reconciliation_distinguishes_match_absence_and_id_conflict() -> None:
    config = DatabaseConfig("127.0.0.1", 33086, "runtime", "test-only", "labdb_d2")
    matching_row = {
        "移库记录编号": "MOVE_02",
        "设备编号": "EQ_01",
        "原实验室编号": "LAB_A",
        "目标实验室编号": "LAB_B",
        "移动时间": FIXED_TIME.replace(tzinfo=None),
        "移动原因": "controlled reason",
    }

    def reconcile(row: dict[str, object] | None):
        opened: list[FakeConnection] = []

        def factory(_config: DatabaseConfig):
            connection = FakeConnection(reconciliation_row=row)
            opened.append(connection)
            return connection

        result = reconcile_transfer_for_config(
            config,
            "MOVE_02",
            "EQ_01",
            "LAB_A",
            "LAB_B",
            "controlled reason",
            connect_factory=factory,
        )
        assert len(opened) == 1
        assert opened[0].close_count == 1
        assert opened[0].trace[0][0] == "USE `labdb_d2`"
        return result

    assert reconcile(matching_row).status is ReconciliationStatus.MATCHING_COMMITTED
    assert reconcile(None).status is ReconciliationStatus.NOT_FOUND
    conflicting_row = dict(matching_row, 目标实验室编号="LAB_OTHER")
    assert reconcile(conflicting_row).status is ReconciliationStatus.ID_CONFLICT


def test_database_selection_failure_is_mapped_and_connection_is_discarded() -> None:
    config = DatabaseConfig("127.0.0.1", 33086, "runtime", "test-only", "labdb_d2")
    connection = FakeConnection(
        use_error=pymysql.OperationalError(1049, "controlled missing database")
    )

    with pytest.raises(TransferDatabaseError) as captured:
        transfer_equipment_for_config(
            config,
            "MOVE_02",
            "EQ_01",
            "LAB_A",
            "LAB_B",
            "controlled reason",
            connect_factory=lambda _config: connection,
        )

    assert captured.value.code == "DATABASE_ERROR"
    assert connection.close_count == 1


def test_cli_transfer_exit_semantics(capsys) -> None:
    config = DatabaseConfig("127.0.0.1", 33086, "runtime", "test-only", "labdb_d2")
    arguments = [
        "transfer",
        "--transfer-id",
        "MOVE_02",
        "--equipment-id",
        "EQ_01",
        "--source-lab-id",
        "LAB_A",
        "--target-lab-id",
        "LAB_B",
        "--reason",
        "controlled reason",
    ]
    success = SimpleNamespace(
        transfer_id="MOVE_02", equipment_id="EQ_01", target_lab_id="LAB_B"
    )

    with patch("labdb.cli.load_config", return_value=config), patch(
        "labdb.cli.transfer_equipment_for_config", return_value=success
    ):
        assert cli.main(arguments) == 0
    assert "SUCCESS" in capsys.readouterr().out

    with patch("labdb.cli.load_config", return_value=config), patch(
        "labdb.cli.transfer_equipment_for_config",
        side_effect=StaleSource("controlled stale source"),
    ):
        assert cli.main(arguments) == 1
    assert "STALE_SOURCE" in capsys.readouterr().err

    with patch("labdb.cli.load_config", return_value=config), patch(
        "labdb.cli.transfer_equipment_for_config",
        side_effect=CommitOutcomeUnknown("MOVE_02"),
    ):
        assert cli.main(arguments) == 2
    error = capsys.readouterr().err
    assert "COMMIT_OUTCOME_UNKNOWN" in error
    assert "rolled back" not in error
