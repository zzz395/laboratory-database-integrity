# Design decisions

[README](../README.md) · [Schema reference](schema-reference.md) · [Limitations](limitations.md)

## Shared identity and roles

`用户` owns the shared ID, name and status. `学生` and `教师` use that ID as both PK and FK, so a person can have either role or both without duplicating identity. There is no exclusive-role discriminator, and a user need not have either extension. `实验室负责人` extends `教师` through another shared PK/FK: every laboratory manager must be a teacher. These are relational roles, not authentication or access-control accounts.

Student-term points include every student role, including dual-role users. A teacher without a student row is excluded. A user's teacher role does not cancel deductions associated with that same user's student identity.

## Resource identity and normalization

`供应商编号` is the supplier's single stable PK. Name and optional phone are descriptive attributes, not identity components or uniqueness guarantees. `设备类别` owns category codes and names; `实验设备` references the code instead of repeating category names. College, laboratory, equipment and course facts likewise live in their own records, reducing redundant descriptions across operational records.

`预约设备` represents a reservation/equipment association with a stable record ID and a UNIQUE pair. Repair attempts and transfer events have their own IDs because several records can belong to one parent. These repeated facts are separate records rather than multi-value columns.

## Reservation time, check-in and evidence

Reservations store explicit `开始时间` and `结束时间` as `DATETIME(6)`—the physical equivalents of starts_at and ends_at. A CHECK requires start < end. Term containment and capacity are cross-table rules evaluated by the verifier. Explicit intervals support these comparisons without parsing human-readable time slots; the project does not implement reservation conflict scheduling.

`签到记录.预约表单号` is a required FK and is UNIQUE, allowing zero or one check-in per reservation. The reservation does not point back to a check-in. A separate composite UNIQUE on reservation ID and check-in ID supplies the exact parent key used by violation evidence.

Every `违规记录` references a reservation directly. Check-in evidence is optional at the column level and conditional on violation type: 爽约 has no check-in and deducts 2; 迟到, 早退 and 超时使用 require check-in evidence and deduct 1. The composite FK `(预约表单号, 签到记录id)` prevents evidence from another reservation. If the check-in ID is NULL, the separate reservation FK still guarantees the reservation exists. V08–V11 validate applicable time evidence; V07 detects no-show reservations that nevertheless have check-ins.

## Repair responsibility and execution

A fault report records three distinct facts: its reporting user, its responsible laboratory manager and its optional assigned maintenance worker. The worker is a separate entity, without a user-account FK. The responsible manager is stored explicitly on the report rather than inferred from a laboratory's current manager.

One report can have multiple `执行维修` records. Each records the worker who performed that attempt, start/completion, cost and optional acceptance. This permits repeated execution and rework without replacing prior attempts. Acceptance references a user; V14 additionally requires the acceptor to be the report's reporter or responsible manager. The FKs do not equate assigned and executing workers, or a report's responsible manager with the equipment's current laboratory manager.

Row-local CHECK predicates tie report state to assignment, schedule and rejection fields, and execution completion to cost and acceptance fields. V13 checks chronology and V15 checks selected report/history consistency conditions. No service automatically advances this workflow.

## Numeric values and derived points

Prices, repair costs and compensation use `DECIMAL(12,2)` with nonnegative CHECK predicates where present. Points use integers. Unknown or not-yet-applicable amounts remain NULL where permitted; zero is a known numeric value and has a different meaning.

[`sql/queries.sql`](../sql/queries.sql) crosses student roles with terms, aggregates deductions via reservation ownership and term, and calculates `GREATEST(0, initial points - deductions)`. A LEFT JOIN and COALESCE preserve students with no violations. The initial allowance belongs to the term with DEFAULT 12; there is no stored remaining-points balance to synchronize.

## Referential and row-local integrity

All foreign keys use RESTRICT for update and delete. This prevents automatic cascades from erasing related operational facts or propagating changed identity keys. It does not forbid all direct row updates or deletes. Database privileges and controlled write paths remain operational responsibilities.

NOT NULL, explicit NULL branches and CHECK predicates distinguish absent evidence from empty text. InnoDB supplies transactions and row locks. utf8mb4_0900_as_cs gives character columns a shared case-sensitive, accent-sensitive comparison policy. The [schema dictionary](schema-reference.md) records actual types, nullability and constraint groups.

## Initialization and deterministic seeding

Initialization validates the database-name allowlist and checks that the database already exists with no tables or views before executing the schema. The independent metadata contract checks the resulting structure. This avoids reset/drop convenience paths. Because MySQL DDL may commit implicitly, partial execution is reported and left for an explicit operator decision; initialization is not one atomic DDL transaction.

The seed contains only deterministic INSERT statements and synthetic identities. It requires matching structure and empty business tables, executes inserts in a transaction, and checks exact per-table counts and V01–V16 before commit. Fixed IDs and timestamps make tests reproducible. Repeat runs refuse populated targets. The rollback guarantee demonstrated by the suite concerns controlled failures before commit; the transfer-specific commit-reconciliation protocol is not implemented for seeding.

## Read-only consistency verification

`verify_database` starts `START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY`, validates structure, and runs V01–V16 only if structure matches. It closes the read transaction with rollback and returns sorted findings without writes. Structure is compared to [`metadata.py`](../src/labdb/metadata.py), independently of parsing the schema at runtime.

The structural contract covers table/column sets and order, types, nullability, collation, engine, primary keys, UNIQUE groups, ordered FKs and actions, CHECK names/enforcement, and the term-points default. It does not compare CHECK predicate bodies or every secondary-index definition. Byte-level schema review remains a separate activity. The [rule catalog](testing.md#verification-rule-catalog) defines the business scope.

## Equipment transfer and reconciliation

Current location belongs to `实验设备`; each `设备移库记录` captures source, target, UTC event time and reason. The transfer operation treats history as immutable: it appends one record and never revises existing history. This is an operation-level guarantee; there are no append-only triggers or schema-level bans on privileged history changes.

The operation refuses an already-active caller transaction. It starts its own transaction, locks equipment with `FOR UPDATE`, verifies the supplied source against the locked current location, rejects identical source/target, and locks the existing target with `FOR SHARE`. It updates exactly one equipment row and inserts the transfer record before committing once. Bound parameters carry business values.

Two transfers expecting the same original source serialize on the equipment lock: after one commits, the other sees the new location and is refused as stale. A duplicate transfer ID encountered after the location UPDATE causes rollback of both effects. Lock-wait and other pre-commit failures are not retried automatically. If rollback cannot be confirmed, the connection is discarded and a database error is returned.

A commit exception is different: the server may already have committed. The connection is discarded, `COMMIT_OUTCOME_UNKNOWN` is returned and no rollback or replay is attempted. `reconcile_transfer_for_config(config, transfer_id, equipment_id, source_lab_id, target_lab_id, reason)` uses a new connection to read the stable ID and compare its payload:

| Result | Meaning |
|---|---|
| `MATCHING_COMMITTED` | A durable record with the expected ID, equipment, source, target and reason is visible. |
| `NOT_FOUND` | No record is visible at lookup time; this alone does not settle a still-pending outcome or authorize retry. |
| `TRANSFER_ID_CONFLICT` | The ID exists with a different payload; do not treat it as this transfer's success. |

Reconciliation confirms the historical operation, not equipment location after possible later transfers. The helper issues a SELECT and does not modify data; it is not a distributed transaction coordinator. V16 compares current location with the latest history by `移动时间`, breaking timestamp ties by `移库记录编号`. It does not prove the complete historical chain. See [limitations](limitations.md) for timestamp and operational assumptions.
