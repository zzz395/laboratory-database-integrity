"""Command-line interface for database integrity operations."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .config import ConfigurationError, load_config
from .db import DatabaseConnectionError
from .initialize import InitializationError, initialize_database
from .seed import SeedError, seed_database
from .errors import CommitOutcomeUnknown, TransferDatabaseError, TransferRefused
from .transactions import transfer_equipment_for_config
from .verify import VerificationError, verify_database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="labdb")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "init",
        help="initialize an existing, empty, dedicated labdb_* database",
    )
    subparsers.add_parser(
        "seed",
        help="seed an exact, empty schema with deterministic synthetic data",
    )
    subparsers.add_parser(
        "verify",
        help="read-only verification of schema and cross-table consistency",
    )
    transfer = subparsers.add_parser(
        "transfer",
        help="atomically move equipment and append its transfer history",
    )
    transfer.add_argument("--transfer-id", required=True)
    transfer.add_argument("--equipment-id", required=True)
    transfer.add_argument("--source-lab-id", required=True)
    transfer.add_argument("--target-lab-id", required=True)
    transfer.add_argument("--reason", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        try:
            result = initialize_database(load_config())
        except (ConfigurationError, DatabaseConnectionError, InitializationError) as exc:
            print(f"Initialization refused or failed: {exc}", file=sys.stderr)
            return 1
        print(
            f"Initialized {result.database}: {result.tables} tables, "
            f"{result.foreign_keys} foreign keys, {result.unique_constraints} unique constraints, "
            f"and {result.check_constraints} enforced check constraints."
        )
        return 0
    if args.command == "seed":
        try:
            result = seed_database(load_config())
        except (ConfigurationError, DatabaseConnectionError, SeedError) as exc:
            print(f"Seed refused or failed: {exc}", file=sys.stderr)
            return 1
        print(
            f"Seeded {result.database}: {result.total_rows} deterministic synthetic rows "
            f"across {len(result.row_counts)} tables."
        )
        return 0
    if args.command == "verify":
        try:
            result = verify_database(load_config())
        except (ConfigurationError, DatabaseConnectionError, VerificationError) as exc:
            print(f"Verification execution failed: {exc}", file=sys.stderr)
            return 2
        for item in result.violations:
            print(f"{item.code}\t{item.table}\t{item.entity_id}\t{item.detail}")
        if result.violations:
            print(f"Verification found {len(result.violations)} violation(s).")
            return 1
        print("Verification found 0 violations.")
        return 0
    if args.command == "transfer":
        try:
            result = transfer_equipment_for_config(
                load_config(),
                args.transfer_id,
                args.equipment_id,
                args.source_lab_id,
                args.target_lab_id,
                args.reason,
            )
        except CommitOutcomeUnknown as exc:
            print(f"{exc.code}: {exc}", file=sys.stderr)
            return 2
        except TransferRefused as exc:
            print(f"{exc.code}: {exc}", file=sys.stderr)
            return 1
        except (ConfigurationError, DatabaseConnectionError, TransferDatabaseError) as exc:
            code = getattr(exc, "code", "DATABASE_ERROR")
            print(f"{code}: {exc}", file=sys.stderr)
            return 2
        print(
            f"SUCCESS: transfer {result.transfer_id!r} committed; "
            f"equipment {result.equipment_id!r} is now in {result.target_lab_id!r}."
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
