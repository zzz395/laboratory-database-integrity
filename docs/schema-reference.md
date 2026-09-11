# Schema reference

[README](../README.md) · [ER diagram](../assets/er-diagram.svg) · [Design decisions](design-decisions.md)

The physical authority is [`sql/schema.sql`](../sql/schema.sql). This dictionary covers all **22 tables, 124 columns, 22 primary keys, 38 foreign keys, 4 additional UNIQUE constraints and 68 CHECK constraints**. SQL identifiers are retained verbatim; English headings explain their purpose.

Every table uses InnoDB, utf8mb4 and utf8mb4_0900_as_cs. Every FK uses `ON UPDATE RESTRICT ON DELETE RESTRICT`. `NULL` below means the column permits SQL NULL; `NOT NULL` means it does not. Optional text, when supplied, must be nonblank where its CHECK requires it. Every standalone entity ID has a nonblank CHECK; the shared role IDs are constrained through their parent identity.

## Reading the ER

Each edge is one named FK, with the referenced parent on the left and referencing child on the right. `||` means exactly one; `|o` / `o|` means zero or one; `o{` means zero or many. Solid edges identify shared-PK role extensions; dashed edges are non-identifying FKs. A parent is not required to have any child rows. Nullable FK participation is optional at the column level; CHECK predicates can make it conditional on state or type.

Attribute comments contain exact SQL type and nullability. PK and FK markers may overlap. UK marks a single-column UNIQUE; composite UNIQUE groups are listed below rather than implying each member is independently unique. The optional composite violation/check-in FK is one relationship, not two.

## Table dictionary

### 学院 — College

Organizational ownership for student, teacher and laboratory records.

Primary key: `pk_college` on `学院编号`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `学院编号` | `VARCHAR(32)` | `NOT NULL` | PK |
| `学院名称` | `VARCHAR(100)` | `NOT NULL` | — |

Constraints and semantics: Identifiers and names must be nonblank.

### 用户 — User

Shared identity for reservations and other user-linked facts; contains no login credentials.

Primary key: `pk_user` on `用户id`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `用户id` | `VARCHAR(32)` | `NOT NULL` | PK |
| `姓名` | `VARCHAR(100)` | `NOT NULL` | — |
| `用户状态` | `VARCHAR(16)` | `NOT NULL` | — |

Constraints and semantics: Identifiers and names must be nonblank; status is 有效 or 停用.

### 学生 — Student

Student role extension of a user, with college membership.

Primary key: `pk_student` on `用户id`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `用户id` | `VARCHAR(32)` | `NOT NULL` | PK, FK |
| `学院编号` | `VARCHAR(32)` | `NOT NULL` | FK |

Constraints and semantics: The user ID is both PK and FK. Student and teacher roles may coexist.

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_student_user` | `用户id` → `用户` (`用户id`) |
| `fk_student_college` | `学院编号` → `学院` (`学院编号`) |

### 教师 — Teacher

Teacher role extension of a user, with college membership.

Primary key: `pk_teacher` on `用户id`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `用户id` | `VARCHAR(32)` | `NOT NULL` | PK, FK |
| `学院编号` | `VARCHAR(32)` | `NOT NULL` | FK |

Constraints and semantics: The user ID is both PK and FK. No constraint makes this role exclusive of 学生.

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_teacher_user` | `用户id` → `用户` (`用户id`) |
| `fk_teacher_college` | `学院编号` → `学院` (`学院编号`) |

### 实验室负责人 — Laboratory manager

Manager role extension of a teacher.

Primary key: `pk_manager` on `用户id`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `用户id` | `VARCHAR(32)` | `NOT NULL` | PK, FK |

Constraints and semantics: The PK references 教师 directly; it is not a separate identity.

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_manager_teacher` | `用户id` → `教师` (`用户id`) |

### 实验室 — Laboratory

A college-owned room and its responsible manager.

Primary key: `pk_laboratory` on `实验室编号`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `实验室编号` | `VARCHAR(32)` | `NOT NULL` | PK |
| `学院编号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `负责人用户id` | `VARCHAR(32)` | `NOT NULL` | FK |
| `实验室名称` | `VARCHAR(100)` | `NOT NULL` | — |
| `容纳人数` | `INT` | `NOT NULL` | — |
| `使用状态` | `VARCHAR(16)` | `NOT NULL` | — |
| `实验室照片` | `VARCHAR(512)` | `NULL` | — |

Constraints and semantics: Capacity > 0; state is 可用, 停用 or 维修中. A supplied photo reference must be nonblank.

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_laboratory_college` | `学院编号` → `学院` (`学院编号`) |
| `fk_laboratory_manager` | `负责人用户id` → `实验室负责人` (`用户id`) |

### 设备类别 — Equipment category

Authoritative category code and display name.

Primary key: `pk_equipment_category` on `类别码`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `类别码` | `VARCHAR(32)` | `NOT NULL` | PK |
| `类别名称` | `VARCHAR(100)` | `NOT NULL` | — |

Constraints and semantics: Code and name must be nonblank; equipment references the code.

### 供应商 — Supplier

Stable supplier identity independent of its name and contact details.

Primary key: `pk_supplier` on `供应商编号`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `供应商编号` | `VARCHAR(32)` | `NOT NULL` | PK |
| `供应商名称` | `VARCHAR(100)` | `NOT NULL` | — |
| `电话` | `VARCHAR(30)` | `NULL` | — |

Constraints and semantics: The supplier ID alone is the PK. A supplied phone must be nonblank; names and phones are not UNIQUE.

### 实验设备 — Equipment

Equipment identity, classification, supplier, current laboratory and purchase facts.

Primary key: `pk_equipment` on `设备编号`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `设备编号` | `VARCHAR(32)` | `NOT NULL` | PK |
| `类别码` | `VARCHAR(32)` | `NOT NULL` | FK |
| `供应商编号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `实验室编号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `型号` | `VARCHAR(100)` | `NOT NULL` | — |
| `规格` | `VARCHAR(100)` | `NOT NULL` | — |
| `购置日期` | `DATE` | `NOT NULL` | — |
| `单价` | `DECIMAL(12,2)` | `NOT NULL` | — |
| `保修到期日` | `DATE` | `NOT NULL` | — |
| `设备状态` | `VARCHAR(16)` | `NOT NULL` | — |

Constraints and semantics: Price >= 0; warranty expiry >= purchase date; state is 在用, 维修 or 报废. Model and specification must be nonblank.

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_equipment_category` | `类别码` → `设备类别` (`类别码`) |
| `fk_equipment_supplier` | `供应商编号` → `供应商` (`供应商编号`) |
| `fk_equipment_laboratory` | `实验室编号` → `实验室` (`实验室编号`) |

### 维修人员 — Maintenance worker

Worker identity and contact details for assignment and execution.

Primary key: `pk_maintenance_worker` on `维修人员工号`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `维修人员工号` | `VARCHAR(32)` | `NOT NULL` | PK |
| `姓名` | `VARCHAR(100)` | `NOT NULL` | — |
| `电话` | `VARCHAR(30)` | `NOT NULL` | — |

Constraints and semantics: ID, name and phone must be nonblank. This table has no FK to 用户.

### 学期 — Term

Explicit term interval and initial points allowance.

Primary key: `pk_term` on `学期编号`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `学期编号` | `VARCHAR(32)` | `NOT NULL` | PK |
| `学期名称` | `VARCHAR(100)` | `NOT NULL` | — |
| `开始时间` | `DATETIME(6)` | `NOT NULL` | — |
| `结束时间` | `DATETIME(6)` | `NOT NULL` | — |
| `初始积分` | `INT` | `NOT NULL` | DEFAULT 12 |

Constraints and semantics: Start < end; initial points >= 0, with DEFAULT 12. Term overlap is checked by V01.

### 课程 — Course

Course identity and its instructor.

Primary key: `pk_course` on `课程编号`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `课程编号` | `VARCHAR(32)` | `NOT NULL` | PK |
| `授课教师用户id` | `VARCHAR(32)` | `NOT NULL` | FK |
| `课程名称` | `VARCHAR(100)` | `NOT NULL` | — |

Constraints and semantics: Course ID and name must be nonblank; instructor must have a 教师 row.

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_course_teacher` | `授课教师用户id` → `教师` (`用户id`) |

### 预约表 — Reservation

A user reservation for a laboratory within a term, optionally for a course.

Primary key: `pk_reservation` on `预约表单号`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `预约表单号` | `VARCHAR(32)` | `NOT NULL` | PK |
| `实验室编号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `用户id` | `VARCHAR(32)` | `NOT NULL` | FK |
| `学期编号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `课程编号` | `VARCHAR(32)` | `NULL` | FK |
| `审核人用户id` | `VARCHAR(32)` | `NULL` | FK |
| `预约类型` | `VARCHAR(16)` | `NOT NULL` | — |
| `开始时间` | `DATETIME(6)` | `NOT NULL` | — |
| `结束时间` | `DATETIME(6)` | `NOT NULL` | — |
| `人数` | `INT` | `NOT NULL` | — |
| `用途` | `VARCHAR(100)` | `NOT NULL` | — |
| `预约状态` | `VARCHAR(16)` | `NOT NULL` | — |
| `驳回原因` | `VARCHAR(1000)` | `NULL` | — |

Constraints and semantics: Start < end; people > 0; purpose must be nonblank. 个人 requires NULL course; 课程 requires a course. 待审核 requires NULL reviewer/rejection; 已驳回 requires reviewer and nonblank rejection; 已通过, 已结束 and 爽约 require reviewer and NULL rejection; 已取消 requires NULL rejection but permits a NULL or non-NULL reviewer.

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_reservation_laboratory` | `实验室编号` → `实验室` (`实验室编号`) |
| `fk_reservation_user` | `用户id` → `用户` (`用户id`) |
| `fk_reservation_term` | `学期编号` → `学期` (`学期编号`) |
| `fk_reservation_course` | `课程编号` → `课程` (`课程编号`) |
| `fk_reservation_reviewer` | `审核人用户id` → `实验室负责人` (`用户id`) |

### 签到记录 — Check-in

At most one attendance record for a reservation, with optional sign-out.

Primary key: `pk_checkin` on `签到记录id`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `签到记录id` | `VARCHAR(32)` | `NOT NULL` | PK |
| `预约表单号` | `VARCHAR(32)` | `NOT NULL` | FK, UNIQUE |
| `签到方式` | `VARCHAR(16)` | `NOT NULL` | — |
| `签到时间` | `DATETIME(6)` | `NOT NULL` | — |
| `签退时间` | `DATETIME(6)` | `NULL` | — |
| `超时备注` | `VARCHAR(1000)` | `NULL` | — |

Constraints and semantics: Method is 手工 or 扫码; sign-out is NULL or >= sign-in. A supplied overtime note must be nonblank.

- `uq_checkin_reservation`: UNIQUE (`预约表单号`).
- `uq_checkin_reservation_id`: UNIQUE (`预约表单号`, `签到记录id`).

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_checkin_reservation` | `预约表单号` → `预约表` (`预约表单号`) |

### 违规记录 — Violation

A reservation-linked deduction, with check-in evidence when required.

Primary key: `pk_violation` on `违规id`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `违规id` | `VARCHAR(32)` | `NOT NULL` | PK |
| `预约表单号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `签到记录id` | `VARCHAR(32)` | `NULL` | FK |
| `违规类型` | `VARCHAR(16)` | `NOT NULL` | — |
| `扣分值` | `INT` | `NOT NULL` | — |
| `违规时间` | `DATETIME(6)` | `NOT NULL` | — |

Constraints and semantics: 爽约 deducts 2 and requires NULL check-in; 迟到, 早退 and 超时使用 deduct 1 and require check-in. The composite FK ties evidence to the same reservation.

- `uq_violation_reservation_type`: UNIQUE (`预约表单号`, `违规类型`).

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_violation_reservation` | `预约表单号` → `预约表` (`预约表单号`) |
| `fk_violation_checkin` | `预约表单号`, `签到记录id` → `签到记录` (`预约表单号`, `签到记录id`) |

### 预约设备 — Reservation equipment

Association between a reservation and an equipment item.

Primary key: `pk_reservation_equipment` on `使用记录编号`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `使用记录编号` | `VARCHAR(32)` | `NOT NULL` | PK |
| `预约表单号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `设备编号` | `VARCHAR(32)` | `NOT NULL` | FK |

Constraints and semantics: The reservation/equipment pair is unique; the association has its own stable PK.

- `uq_reservation_equipment_pair`: UNIQUE (`预约表单号`, `设备编号`).

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_reservation_equipment_reservation` | `预约表单号` → `预约表` (`预约表单号`) |
| `fk_reservation_equipment_device` | `设备编号` → `实验设备` (`设备编号`) |

### 预约变更 — Reservation change

A reservation change fact with actor, reason and timestamp.

Primary key: `pk_reservation_change` on `变更记录编号`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `变更记录编号` | `VARCHAR(32)` | `NOT NULL` | PK |
| `预约表单号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `操作人用户id` | `VARCHAR(32)` | `NOT NULL` | FK |
| `变更类型` | `VARCHAR(16)` | `NOT NULL` | — |
| `变更原因` | `VARCHAR(1000)` | `NOT NULL` | — |
| `变更时间` | `DATETIME(6)` | `NOT NULL` | — |

Constraints and semantics: Type is 取消 or 改期; reason must be nonblank. A cancelled reservation needs a cancellation record under V12.

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_reservation_change_reservation` | `预约表单号` → `预约表` (`预约表单号`) |
| `fk_reservation_change_actor` | `操作人用户id` → `用户` (`用户id`) |

### 故障报修单 — Fault report

Equipment fault with separate reporter, responsible manager and optional assigned worker.

Primary key: `pk_fault_report` on `报修单ID`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `报修单ID` | `VARCHAR(32)` | `NOT NULL` | PK |
| `设备编号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `报修人用户id` | `VARCHAR(32)` | `NOT NULL` | FK |
| `责任负责人用户id` | `VARCHAR(32)` | `NOT NULL` | FK |
| `指派维修人员工号` | `VARCHAR(32)` | `NULL` | FK |
| `故障描述` | `VARCHAR(1000)` | `NOT NULL` | — |
| `故障图片` | `VARCHAR(512)` | `NULL` | — |
| `紧急程度` | `VARCHAR(16)` | `NOT NULL` | — |
| `单据状态` | `VARCHAR(16)` | `NOT NULL` | — |
| `报修时间` | `DATETIME(6)` | `NOT NULL` | — |
| `计划维修时间` | `DATETIME(6)` | `NULL` | — |
| `拒绝原因` | `VARCHAR(1000)` | `NULL` | — |

Constraints and semantics: Urgency is 一般 or 紧急; planned repair is NULL or >= report time. 待指派 requires NULL worker/schedule/rejection; 维修中, 待验收 and 已完成 require worker and schedule with NULL rejection; 拒绝 requires NULL worker/schedule and a nonblank rejection. Supplied image references must be nonblank.

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_fault_report_equipment` | `设备编号` → `实验设备` (`设备编号`) |
| `fk_fault_report_reporter` | `报修人用户id` → `用户` (`用户id`) |
| `fk_fault_report_manager` | `责任负责人用户id` → `实验室负责人` (`用户id`) |
| `fk_fault_report_assignee` | `指派维修人员工号` → `维修人员` (`维修人员工号`) |

### 执行维修 — Maintenance execution

One execution attempt for a fault report; a report may have multiple attempts.

Primary key: `pk_maintenance_execution` on `维修记录编号`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `维修记录编号` | `VARCHAR(32)` | `NOT NULL` | PK |
| `报修单ID` | `VARCHAR(32)` | `NOT NULL` | FK |
| `维修人员工号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `维修内容` | `VARCHAR(1000)` | `NOT NULL` | — |
| `开始时间` | `DATETIME(6)` | `NOT NULL` | — |
| `完成时间` | `DATETIME(6)` | `NULL` | — |
| `维修费用` | `DECIMAL(12,2)` | `NULL` | — |
| `验收结果` | `VARCHAR(16)` | `NULL` | — |
| `验收人用户id` | `VARCHAR(32)` | `NULL` | FK |
| `验收时间` | `DATETIME(6)` | `NULL` | — |

Constraints and semantics: Completion and cost are both NULL or both present with completion >= start and cost >= 0. Acceptance fields are all NULL, or result is 通过/返修 with acceptor and time present, completion present, and acceptance >= completion.

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_maintenance_execution_report` | `报修单ID` → `故障报修单` (`报修单ID`) |
| `fk_maintenance_execution_worker` | `维修人员工号` → `维修人员` (`维修人员工号`) |
| `fk_maintenance_execution_acceptor` | `验收人用户id` → `用户` (`用户id`) |

### 安全检查表 — Safety inspection

Manager inspection of a laboratory and its safety findings.

Primary key: `pk_safety_inspection` on `检查记录id`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `检查记录id` | `VARCHAR(32)` | `NOT NULL` | PK |
| `实验室编号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `检查人用户id` | `VARCHAR(32)` | `NOT NULL` | FK |
| `检查日期` | `DATE` | `NOT NULL` | — |
| `水电状态` | `VARCHAR(16)` | `NOT NULL` | — |
| `消防状态` | `VARCHAR(16)` | `NOT NULL` | — |
| `设备状态` | `VARCHAR(16)` | `NOT NULL` | — |
| `门窗状态` | `VARCHAR(16)` | `NOT NULL` | — |
| `隐患记录` | `VARCHAR(1000)` | `NULL` | — |
| `整改结果` | `VARCHAR(1000)` | `NULL` | — |

Constraints and semantics: Each of four inspection states is 合格 or 不合格. All passing requires NULL findings and correction; any failure requires nonblank findings, with correction NULL or nonblank.

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_safety_inspection_laboratory` | `实验室编号` → `实验室` (`实验室编号`) |
| `fk_safety_inspection_inspector` | `检查人用户id` → `实验室负责人` (`用户id`) |

### 借用 — Loan

Equipment loan with handling manager, borrower, return and compensation facts.

Primary key: `pk_loan` on `借用记录编号`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `借用记录编号` | `VARCHAR(32)` | `NOT NULL` | PK |
| `经办负责人用户id` | `VARCHAR(32)` | `NOT NULL` | FK |
| `借用人用户id` | `VARCHAR(32)` | `NOT NULL` | FK |
| `设备编号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `借出时间` | `DATETIME(6)` | `NOT NULL` | — |
| `计划归还时间` | `DATETIME(6)` | `NOT NULL` | — |
| `实际归还时间` | `DATETIME(6)` | `NULL` | — |
| `损坏描述` | `VARCHAR(1000)` | `NULL` | — |
| `赔偿金额` | `DECIMAL(12,2)` | `NULL` | — |

Constraints and semantics: Planned return >= loan time; actual return is NULL or >= loan time. Damage is NULL or nonblank; compensation is NULL or >= 0.

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_loan_manager` | `经办负责人用户id` → `实验室负责人` (`用户id`) |
| `fk_loan_borrower` | `借用人用户id` → `用户` (`用户id`) |
| `fk_loan_equipment` | `设备编号` → `实验设备` (`设备编号`) |

### 设备移库记录 — Equipment transfer

Append-only history in the transfer operation, alongside equipment current location.

Primary key: `pk_equipment_transfer` on `移库记录编号`.

| Column | SQL type | Nullability | Key / default |
|---|---|---|---|
| `移库记录编号` | `VARCHAR(32)` | `NOT NULL` | PK |
| `设备编号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `原实验室编号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `目标实验室编号` | `VARCHAR(32)` | `NOT NULL` | FK |
| `移动时间` | `DATETIME(6)` | `NOT NULL` | — |
| `移动原因` | `VARCHAR(1000)` | `NOT NULL` | — |

Constraints and semantics: Source and target must differ; reason must be nonblank. Schema constraints do not themselves forbid UPDATE or DELETE of history by privileged writers.

| Foreign key | Child columns → parent columns |
|---|---|
| `fk_equipment_transfer_device` | `设备编号` → `实验设备` (`设备编号`) |
| `fk_equipment_transfer_source` | `原实验室编号` → `实验室` (`实验室编号`) |
| `fk_equipment_transfer_target` | `目标实验室编号` → `实验室` (`实验室编号`) |

## UNIQUE groups and NULL semantics

The four additional UNIQUE constraints are `uq_checkin_reservation`, `uq_checkin_reservation_id`, `uq_violation_reservation_type` and `uq_reservation_equipment_pair`. The check-in composite key is an explicit referenced key for evidence matching; its reservation member is already unique. A violation always references a reservation. If its check-in ID is NULL, MySQL does not require the composite FK to match a check-in; the separate reservation FK still applies. CHECK predicates permit this only for 爽约.

## Cross-table verification boundary

CHECK constraints enforce row-local conditions. [`verify.py`](../src/labdb/verify.py) checks the additional cross-table rules V01–V16; the [testing guide](testing.md#verification-rule-catalog) lists their scope. Verification reports findings and performs no repairs. Structural verification compares the independent [metadata contract](../src/labdb/metadata.py), including CHECK names and enforcement; it does not compare CHECK predicate text.

## Maintaining the diagram

The [Mermaid ER syntax](https://mermaid.js.org/syntax/entityRelationshipDiagram) defines the notation. The source uses Unicode SQL identifiers and includes its layout/style configuration. The SVG uses **Mermaid 11.12.0** with HTML labels disabled so its text is native SVG. No renderer dependency is required to run the database project.

To reproduce the export, load the fixed `mermaid@11.12.0/dist/mermaid.min.js` browser bundle in a temporary rendering environment, read `assets/er-diagram.mmd` as UTF-8 into `source`, and use:

```javascript
mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
const { svg } = await mermaid.render("labdb-er", source);
```

Save the returned SVG as `assets/er-diagram.svg`. The source's frontmatter supplies the theme, font, spacing and left-to-right layout. Microsoft YaHei was available for the accepted render; another font environment can change geometry without changing relationships. Keep the fixed bundle and rendering environment outside the project.

Validate 22 entity groups, 22 PK markers, all 124 attributes and 38 uniquely named relationship labels against the schema. Check optionality, identifying lines, endpoint entities and ordered composite-key mappings against this dictionary and the FK definitions. Render at full scale to check text clipping. Changing SQL requires reconciling the source, dictionary and SVG together.
