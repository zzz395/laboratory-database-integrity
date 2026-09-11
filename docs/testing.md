# Testing

[README](../README.md) · [Schema reference](schema-reference.md) · [Limitations](limitations.md)

## Validated results

Python 3.12 is the primary validated runtime. Python 3.13 is a validated compatibility target.

| Validation run | Python | MySQL | Collected | Passed | Failed | Skipped |
|---|---|---|---:|---:|---:|---:|
| Accepted local CI-equivalent, primary | 3.12.10 | 8.4.11 | 120 | 120 | 0 | 0 |
| Accepted local CI-equivalent, compatibility | 3.13.5 | 8.4.11 | 120 | 120 | 0 | 0 |
| Documentation acceptance rerun | 3.12.10 | 8.4.11 | 120 | 120 | 0 | 0 |

These results were validated locally on 2026-09-11. The documentation rerun used the existing validated Python 3.12.10 environment, a fresh isolated MySQL 8.4.11 instance, the complete suite with `--fail-on-skip`, and an independent CLI smoke database. No tests or business semantics were changed for documentation acceptance. Python 3.13.5 and clean-install/build results refer to the accepted local CI-equivalent runs, not a new compatibility run during documentation review.

**Local CI-equivalent: PASS. Hosted GitHub Actions has not yet been executed.** There is no hosted-CI pass claim or badge.

## Coverage matrix

The suite has 89 non-integration cases and 31 MySQL integration cases, including parametrized cases. This is behavioral and contract coverage; no line-coverage percentage is claimed.

| Area | Evidence and scope |
|---|---|
| Configuration and sessions | [test_config.py](../tests/test_config.py), [test_database_name.py](../tests/test_database_name.py), [test_db.py](../tests/test_db.py): required environment values, port/name boundaries, unsafe names, password omission from tested errors and TLS/session configuration. |
| Initialization and schema | [test_database_name.py](../tests/test_database_name.py), [test_initialize_mysql.py](../tests/integration/test_initialize_mysql.py): empty-existing target, missing/non-empty refusals, controlled partial-DDL failure, schema inventory and metadata validation against real MySQL; repeat initialization preserves the metadata fingerprint. |
| Seed and derived query | [test_seed.py](../tests/test_seed.py), [test_seed_verify_mysql.py](../tests/integration/test_seed_verify_mysql.py): INSERT-only deterministic seed, exact schema/empty-table preconditions, rollback after an injected duplicate, 68-row inventory, repeat refusal, student/term isolation, dual roles, zero deductions and the points floor. |
| Verification | [test_verify.py](../tests/test_verify.py), [test_seed_verify_mysql.py](../tests/integration/test_seed_verify_mysql.py): mocked structural drift maps to S01; all V01–V16 have controlled MySQL negative fixtures with expected IDs and rollback; valid-seed verification preserves a full data fingerprint. |
| Transfers | [test_transactions.py](../tests/test_transactions.py), [test_transfer_mysql.py](../tests/integration/test_transfer_mysql.py): success/visibility, input/domain refusals, update-then-insert rollback, caller transaction preservation, row locks, two-session same-source concurrency, lock-wait failure, no retry and commit-uncertainty reconciliation. |
| CLI | [test_cli.py](../tests/test_cli.py), verification and transaction tests: help, init/seed success and refusal, verify/transfer exit codes, missing/invalid arguments and output identifiers. Separate database smoke exercises init → seed → verify → transfer → verify. |
| Packaging and validation policy | [test_packaging.py](../tests/test_packaging.py): exact locked declarations and Python version range. [test_zero_skip.py](../tests/test_zero_skip.py) checks that [conftest.py](../tests/conftest.py) turns a skipped session into failure when requested. |

The concurrency test demonstrates one success and one stale-source refusal when two sessions start from the same source. Commit-uncertainty tests inject acknowledgement loss before and after a real server commit through a connection proxy; they do not claim a network-chaos test. Reconciliation covers matching records, absence and conflicting IDs.

The real-MySQL initialization path exercises `validate_structure`. The specific S01 mapping test injects a structural error; it is not a live ALTER-and-detect test for every possible drift. CHECK predicate text and every secondary-index definition are outside the current metadata comparison. See [limitations](limitations.md).

## Verification rule catalog

[S01_SCHEMA_DRIFT and the business checks](../src/labdb/verify.py) produce diagnostics, not write-time workflow automation. Business checks run only when structural validation succeeds.

| Code | Finding |
|---|---|
| `S01_SCHEMA_DRIFT` | Live metadata differs from the independent structural contract. |
| `V01_TERM_OVERLAP` | Two term intervals overlap; touching boundaries do not overlap. |
| `V02_RESERVATION_OUTSIDE_TERM` | Reservation starts before its term or ends after it. |
| `V03_COURSE_RESERVATION_TEACHER_MISMATCH` | Course reservation owner differs from the course instructor. |
| `V04_RESERVATION_CAPACITY_EXCEEDED` | Reservation headcount exceeds laboratory capacity. |
| `V05_CHECKIN_RESERVATION_STATUS` | Check-in belongs to a reservation outside 已通过 / 已结束. |
| `V06_CHECKIN_TIME_WINDOW` | Check-in is outside the inclusive window from 30 minutes before to 15 minutes after reservation start. |
| `V07_NO_SHOW_WITH_CHECKIN` | A 爽约 reservation has a check-in. |
| `V08_NO_SHOW_TIME` | A no-show violation timestamp is earlier than start + 15 minutes. |
| `V09_LATE_EVIDENCE` | A 迟到 violation's check-in is at or before reservation start. |
| `V10_EARLY_LEAVE_EVIDENCE` | A 早退 violation has no sign-out or sign-out is at/after reservation end. |
| `V11_OVERTIME_EVIDENCE` | A 超时使用 violation has no sign-out or sign-out is at/before reservation end. |
| `V12_CANCELLED_WITHOUT_CHANGE` | An 已取消 reservation has no 取消 change record. |
| `V13_REPAIR_STARTED_BEFORE_REPORT` | An execution starts before the fault report. |
| `V14_INVALID_ACCEPTOR` | An accepted/rework execution names neither the reporter nor responsible manager as acceptor. |
| `V15_REPAIR_STATE_INCONSISTENCY` | Execution history violates the report-state conditions below. |
| `V16_TRANSFER_LOCATION_MISMATCH` | Equipment location differs from the latest transfer target; latest is ordered by time then transfer ID. |

V15 detects executions on 待指派 / 拒绝 reports. For 待验收, it requires at least one completed, unaccepted execution and no incomplete execution. For 已完成, it requires at least one 通过 execution, no incomplete execution and no completed execution awaiting acceptance. It does not add a condition for 维修中 or require every prior acceptance to be 通过.

## Database preparation

Use a dedicated, **fresh empty** `labdb_*` database on MySQL 8.4.11, provisioned outside the application with utf8mb4 / utf8mb4_0900_as_cs. The full suite initializes and seeds it in sequence. Do not pre-run the quick start against that database. A subsequent full run needs another empty target; the application does not clear one for you. Run the suite serially in its default order; it is not designed for shuffled or parallel test execution.

Use separately provisioned accounts scoped to the disposable database:

| Account | Environment | Privileges used in accepted validation |
|---|---|---|
| Schema/seed runtime | `LABDB_USER`, `LABDB_PASSWORD` | CREATE, REFERENCES, INDEX, SELECT, INSERT, UPDATE |
| Transfer runtime | `LABDB_TRANSFER_USER`, `LABDB_TRANSFER_PASSWORD` | SELECT, INSERT, UPDATE |
| Negative-fixture writer | `LABDB_TEST_USER`, `LABDB_TEST_PASSWORD` | SELECT, INSERT, UPDATE |

Also set `LABDB_HOST`, `LABDB_PORT`, `LABDB_DATABASE` and explicitly opt in with `LABDB_RUN_INTEGRATION=1`. Set secrets through the environment; `.env.example` is only a variable template. Database/account bootstrap administration is separate from runtime accounts. The transfer integration test rejects grants including ALL PRIVILEGES, DELETE, DROP, ALTER, CREATE or SUPER.

A separate empty database is needed for CLI smoke. Grant its schema/seed runtime the same scoped setup privileges. [.github/workflows/ci.yml](../.github/workflows/ci.yml) contains the concrete isolated bootstrap recipe: four ephemeral credentials, localhost binding, authenticated readiness checks and exact server-version verification. Docker is used for validation isolation and is not a product runtime requirement.

## Reproduce the checks

Use the source checkout and the selected validated Python version:

```text
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m pip check
python -m labdb.cli --help
labdb --help
python -m pytest -p no:cacheprovider --collect-only
python -m pytest -p no:cacheprovider --fail-on-skip
```

Set all database variables and the integration opt-in before the full run. Without the opt-in, integration tests skip; `--fail-on-skip` deliberately turns that into a failed acceptance run. The hook's unit test constructs stand-in session, configuration and terminal-reporter state with `--fail-on-skip` enabled and one reported skip, invokes `pytest_sessionfinish` directly, and asserts that the session exit status becomes `pytest.ExitCode.TESTS_FAILED` and that the reporter receives the expected one-skip diagnostic call.

For a quick check with no database, `python -m pytest -m "not integration" -p no:cacheprovider` runs the 89 non-integration cases. It is not full acceptance.

The accepted local CI-equivalent validation additionally used fresh virtual environments for both Python targets, installed the lock and editable project, ran `pip check`, compiled sources/tests, built a wheel and ran both CLI entry-point help forms. The workflow contains these commands, including `python -m compileall -q src tests` and `python -m pip wheel . --no-deps --no-build-isolation --wheel-dir <temporary-output-directory>`. Keep build output and temporary environments outside the public candidate. A wheel build does not establish standalone SQL-resource packaging; see [packaging limitations](limitations.md#packaging-boundary).

For database smoke, point `LABDB_DATABASE` at its separate empty database and execute the [quick-start sequence](../README.md#quick-start). Expected results are 22 initialized tables, 38 FKs, 4 additional UNIQUEs, 68 enforced CHECKs, 68 seeded rows, and zero verification findings both before and after the example transfer.

## CI status

The workflow is configured for `push` and `pull_request` on `ubuntu-24.04`, with Python 3.12/3.13 and `mysql:8.4.11@sha256:3466ba4a4828aa8d46fb7c3bc16b67b781c98413cf4ea0fac6feaa6e881faa26`. Credentials are generated ephemerally and masked. The full suite uses `--fail-on-skip`, then CLI smoke runs against a different database.

The local validation results above are available; hosted execution remains pending. **Hosted GitHub Actions has not yet been executed.**
