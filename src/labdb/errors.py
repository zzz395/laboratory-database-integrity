"""Stable domain and database errors for equipment transfers."""

from __future__ import annotations

from typing import ClassVar


class TransferError(RuntimeError):
    """Base class carrying a stable machine-readable transfer error code."""

    code: ClassVar[str] = "TRANSFER_ERROR"


class TransferRefused(TransferError):
    """Base class for a safe business or transaction-boundary refusal."""


class InvalidTransferInput(TransferRefused):
    code = "INVALID_INPUT"


class EquipmentNotFound(TransferRefused):
    code = "EQUIPMENT_NOT_FOUND"


class TargetNotFound(TransferRefused):
    code = "TARGET_NOT_FOUND"


class StaleSource(TransferRefused):
    code = "STALE_SOURCE"


class SameSourceTarget(TransferRefused):
    code = "SAME_SOURCE_TARGET"


class TransferIdConflict(TransferRefused):
    code = "TRANSFER_ID_CONFLICT"


class TransactionAlreadyActive(TransferRefused):
    code = "TRANSACTION_ALREADY_ACTIVE"


class TransferDatabaseError(TransferError):
    code = "DATABASE_ERROR"


class CommitOutcomeUnknown(TransferDatabaseError):
    """Raised when the server's COMMIT result was not acknowledged."""

    code = "COMMIT_OUTCOME_UNKNOWN"

    def __init__(self, transfer_id: str) -> None:
        self.transfer_id = transfer_id
        super().__init__(
            "commit acknowledgement was not received; the transfer may or may not "
            f"have committed; do not retry and reconcile transfer ID {transfer_id!r}"
        )
