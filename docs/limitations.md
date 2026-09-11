# Limitations

[README](../README.md) · [Design decisions](design-decisions.md) · [Testing](testing.md)

## Project scope

The deliverable is a relational schema, SQL data/query examples, a Python integrity CLI and automated database tests. It has no Web UI, REST API, authentication system, scheduling service, distributed transaction layer, migration framework or production deployment automation. User and teacher/student/manager records model data roles; they do not implement permissions or login sessions.

Reservations have explicit intervals, but the project does not prevent all booking conflicts or manage a calendar. Repair records capture state and execution history without an automated workflow. Laboratory and equipment status fields are data constraints, not a complete policy engine for every operation.

## Validation scope

Python 3.12 is the primary validated runtime. Python 3.13 is a validated compatibility target. Exact tested versions are Python 3.12.10, Python 3.13.5 and MySQL 8.4.11. Package metadata allows Python 3.12/3.13; this is not a guarantee for every patch release or all Python 3.x versions. No compatibility result is claimed for other MySQL versions or database engines.

The 120-test suite and local CI-equivalent checks cover behaviors listed in [testing.md](testing.md). They are not a performance benchmark, scale test or general proof of correctness. Hosted GitHub Actions has not yet been executed. Its Ubuntu matrix is configured, but a hosted execution result is not available.

The seed is a compact set of 68 deterministic synthetic rows. It exercises selected scenarios rather than representing real institutional records, operational volume or a production distribution.

## Integrity boundaries

Verification reports a defined structural contract and V01–V16. It does not repair data, prevent every concurrent business write, detect every possible inconsistency or enforce rules absent from that catalog. Structure checks compare CHECK names and enforcement, not predicate text, and do not compare every secondary index. Changes to SQL require direct schema review in addition to `verify`.

The consistent read transaction is intended for a stable schema, not a concurrent-DDL auditing protocol. Cross-table rules are diagnostic checks rather than universal write-time constraints; ordinary SQL writers can create a business-rule violation that only subsequent verification detects.

History is append-only in the supplied transfer operation. Privileged SQL access can still modify or delete history. V16 checks the latest target against current location, not every source-to-target link. The transfer validates identity, source state and target existence; it does not enforce borrowing, repair, reservation or laboratory-availability policies.

## Operational assumptions

Initialization and seeding are controlled setup operations for dedicated targets with no competing setup writers. Initialization never resets a database. Failed DDL may leave partial structure because MySQL DDL can commit implicitly; recovery requires an operator decision outside the CLI.

The transfer has explicit unknown-commit handling and reconciliation. That protocol is not generalized to seeding or every database operation. A reconciliation lookup returning no record is not a guarantee that a pending commit can never appear. Recovery and any retry decision remain explicit.

`DATETIME(6)` does not store a time-zone offset. Database sessions are configured to UTC; the transfer converts its aware clock value to UTC before storing it. Other data producers must use a consistent convention. The latest-transfer check orders by event time and then transfer ID; it assumes sensible event ordering and is not a monotonic sequence or clock-skew correction mechanism.

The connection enables TLS for the validated MySQL authentication path, but does not implement production certificate identity verification. Secret provisioning, restricted grants, certificate policy, backups, monitoring and deployment are environment responsibilities. No credentials are bundled; `.env` files are not loaded automatically.

## Packaging boundary

The validated working setup is a source checkout installed in editable mode, with the sibling `sql/` directory present. A wheel build is checked as packaging validation; the wheel does not bundle SQL assets. Installing a wheel alone does not provide the complete default `init`/`seed` setup. The repository is not a standalone packaged database deployment product.
