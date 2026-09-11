"""Deterministic, read-only structural and cross-table verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pymysql
from pymysql.connections import Connection

from .config import DatabaseConfig, validate_database_name
from .db import connect_server
from .initialize import StructuralValidationError, quote_validated_database_name, validate_structure


class VerificationError(RuntimeError):
    """Raised when verification cannot be executed safely."""


@dataclass(frozen=True, order=True)
class Violation:
    code: str
    table: str
    entity_id: str
    detail: str


@dataclass(frozen=True)
class VerificationResult:
    database: str
    violations: tuple[Violation, ...]

    @property
    def is_valid(self) -> bool:
        return not self.violations


BUSINESS_CHECKS: tuple[tuple[str, str, str, str], ...] = (
    ("V01_TERM_OVERLAP", "学期", "学期编号",
     "SELECT CONCAT(a.`学期编号`, '|', b.`学期编号`) AS `学期编号`, CONCAT('overlap: ', a.`学期编号`, ' and ', b.`学期编号`) AS detail FROM `学期` a JOIN `学期` b ON a.`学期编号` < b.`学期编号` AND a.`开始时间` < b.`结束时间` AND b.`开始时间` < a.`结束时间`"),
    ("V02_RESERVATION_OUTSIDE_TERM", "预约表", "预约表单号",
     "SELECT r.`预约表单号`, CONCAT('reservation interval is outside term ', r.`学期编号`) AS detail FROM `预约表` r JOIN `学期` t ON t.`学期编号` = r.`学期编号` WHERE r.`开始时间` < t.`开始时间` OR r.`结束时间` > t.`结束时间`"),
    ("V03_COURSE_RESERVATION_TEACHER_MISMATCH", "预约表", "预约表单号",
     "SELECT r.`预约表单号`, CONCAT('owner ', r.`用户id`, ' differs from instructor ', c.`授课教师用户id`) AS detail FROM `预约表` r JOIN `课程` c ON c.`课程编号` = r.`课程编号` WHERE r.`预约类型` = '课程' AND r.`用户id` <> c.`授课教师用户id`"),
    ("V04_RESERVATION_CAPACITY_EXCEEDED", "预约表", "预约表单号",
     "SELECT r.`预约表单号`, CONCAT('people ', r.`人数`, ' exceeds capacity ', l.`容纳人数`) AS detail FROM `预约表` r JOIN `实验室` l ON l.`实验室编号` = r.`实验室编号` WHERE r.`人数` > l.`容纳人数`"),
    ("V05_CHECKIN_RESERVATION_STATUS", "签到记录", "签到记录id",
     "SELECT c.`签到记录id`, CONCAT('reservation ', r.`预约表单号`, ' has status ', r.`预约状态`) AS detail FROM `签到记录` c JOIN `预约表` r ON r.`预约表单号` = c.`预约表单号` WHERE r.`预约状态` NOT IN ('已通过', '已结束')"),
    ("V06_CHECKIN_TIME_WINDOW", "签到记录", "签到记录id",
     "SELECT c.`签到记录id`, CONCAT('check-in outside window for ', r.`预约表单号`) AS detail FROM `签到记录` c JOIN `预约表` r ON r.`预约表单号` = c.`预约表单号` WHERE c.`签到时间` < r.`开始时间` - INTERVAL 30 MINUTE OR c.`签到时间` > r.`开始时间` + INTERVAL 15 MINUTE"),
    ("V07_NO_SHOW_WITH_CHECKIN", "预约表", "预约表单号",
     "SELECT r.`预约表单号`, 'no-show reservation has an actual check-in' AS detail FROM `预约表` r JOIN `签到记录` c ON c.`预约表单号` = r.`预约表单号` WHERE r.`预约状态` = '爽约'"),
    ("V08_NO_SHOW_TIME", "违规记录", "违规id",
     "SELECT v.`违规id`, CONCAT('no-show timestamp is too early for ', r.`预约表单号`) AS detail FROM `违规记录` v JOIN `预约表` r ON r.`预约表单号` = v.`预约表单号` WHERE v.`违规类型` = '爽约' AND v.`违规时间` < r.`开始时间` + INTERVAL 15 MINUTE"),
    ("V09_LATE_EVIDENCE", "违规记录", "违规id",
     "SELECT v.`违规id`, CONCAT('check-in does not prove lateness for ', r.`预约表单号`) AS detail FROM `违规记录` v JOIN `预约表` r ON r.`预约表单号` = v.`预约表单号` JOIN `签到记录` c ON c.`预约表单号` = v.`预约表单号` AND c.`签到记录id` = v.`签到记录id` WHERE v.`违规类型` = '迟到' AND c.`签到时间` <= r.`开始时间`"),
    ("V10_EARLY_LEAVE_EVIDENCE", "违规记录", "违规id",
     "SELECT v.`违规id`, CONCAT('check-out does not prove early leave for ', r.`预约表单号`) AS detail FROM `违规记录` v JOIN `预约表` r ON r.`预约表单号` = v.`预约表单号` JOIN `签到记录` c ON c.`预约表单号` = v.`预约表单号` AND c.`签到记录id` = v.`签到记录id` WHERE v.`违规类型` = '早退' AND (c.`签退时间` IS NULL OR c.`签退时间` >= r.`结束时间`)"),
    ("V11_OVERTIME_EVIDENCE", "违规记录", "违规id",
     "SELECT v.`违规id`, CONCAT('check-out does not prove overtime for ', r.`预约表单号`) AS detail FROM `违规记录` v JOIN `预约表` r ON r.`预约表单号` = v.`预约表单号` JOIN `签到记录` c ON c.`预约表单号` = v.`预约表单号` AND c.`签到记录id` = v.`签到记录id` WHERE v.`违规类型` = '超时使用' AND (c.`签退时间` IS NULL OR c.`签退时间` <= r.`结束时间`)"),
    ("V12_CANCELLED_WITHOUT_CHANGE", "预约表", "预约表单号",
     "SELECT r.`预约表单号`, 'cancelled reservation has no cancellation change' AS detail FROM `预约表` r WHERE r.`预约状态` = '已取消' AND NOT EXISTS (SELECT 1 FROM `预约变更` c WHERE c.`预约表单号` = r.`预约表单号` AND c.`变更类型` = '取消')"),
    ("V13_REPAIR_STARTED_BEFORE_REPORT", "执行维修", "维修记录编号",
     "SELECT e.`维修记录编号`, CONCAT('maintenance starts before report ', f.`报修单ID`) AS detail FROM `执行维修` e JOIN `故障报修单` f ON f.`报修单ID` = e.`报修单ID` WHERE e.`开始时间` < f.`报修时间`"),
    ("V14_INVALID_ACCEPTOR", "执行维修", "维修记录编号",
     "SELECT e.`维修记录编号`, CONCAT('acceptor is neither reporter nor manager for ', f.`报修单ID`) AS detail FROM `执行维修` e JOIN `故障报修单` f ON f.`报修单ID` = e.`报修单ID` WHERE e.`验收结果` IS NOT NULL AND e.`验收人用户id` NOT IN (f.`报修人用户id`, f.`责任负责人用户id`)"),
    ("V15_REPAIR_STATE_INCONSISTENCY", "故障报修单", "报修单ID",
     "SELECT f.`报修单ID`, CONCAT('execution history conflicts with state ', f.`单据状态`) AS detail FROM `故障报修单` f WHERE (f.`单据状态` IN ('待指派', '拒绝') AND EXISTS (SELECT 1 FROM `执行维修` e WHERE e.`报修单ID` = f.`报修单ID`)) OR (f.`单据状态` = '待验收' AND (NOT EXISTS (SELECT 1 FROM `执行维修` e WHERE e.`报修单ID` = f.`报修单ID` AND e.`完成时间` IS NOT NULL AND e.`验收结果` IS NULL) OR EXISTS (SELECT 1 FROM `执行维修` e WHERE e.`报修单ID` = f.`报修单ID` AND e.`完成时间` IS NULL))) OR (f.`单据状态` = '已完成' AND (NOT EXISTS (SELECT 1 FROM `执行维修` e WHERE e.`报修单ID` = f.`报修单ID` AND e.`验收结果` = '通过') OR EXISTS (SELECT 1 FROM `执行维修` e WHERE e.`报修单ID` = f.`报修单ID` AND e.`完成时间` IS NULL) OR EXISTS (SELECT 1 FROM `执行维修` e WHERE e.`报修单ID` = f.`报修单ID` AND e.`完成时间` IS NOT NULL AND e.`验收结果` IS NULL)))"),
    ("V16_TRANSFER_LOCATION_MISMATCH", "设备移库记录", "移库记录编号",
     "SELECT m.`移库记录编号`, CONCAT('latest transfer target ', m.`目标实验室编号`, ' differs from equipment location ', e.`实验室编号`) AS detail FROM `设备移库记录` m JOIN `实验设备` e ON e.`设备编号` = m.`设备编号` WHERE NOT EXISTS (SELECT 1 FROM `设备移库记录` n WHERE n.`设备编号` = m.`设备编号` AND (n.`移动时间` > m.`移动时间` OR (n.`移动时间` = m.`移动时间` AND n.`移库记录编号` > m.`移库记录编号`))) AND e.`实验室编号` <> m.`目标实验室编号`"),
)


def _structural_violations(connection: Connection, database: str) -> list[Violation]:
    try:
        validate_structure(connection, database)
        return []
    except StructuralValidationError as exc:
        message = str(exc)
        details = [line[2:] for line in message.splitlines() if line.startswith("- ")]
        if not details:
            details = [message]
        return [Violation("S01_SCHEMA_DRIFT", "INFORMATION_SCHEMA", database, detail) for detail in sorted(details)]


def run_business_checks(connection: Connection) -> tuple[Violation, ...]:
    violations: list[Violation] = []
    with connection.cursor() as cursor:
        for code, table, id_column, query in BUSINESS_CHECKS:
            cursor.execute(query)
            for row in cursor.fetchall():
                violations.append(Violation(code, table, str(row[id_column]), str(row["detail"])))
    return tuple(sorted(violations))


def run_all_checks(connection: Connection, database: str) -> tuple[Violation, ...]:
    structural = _structural_violations(connection, database)
    return tuple(sorted(structural)) if structural else run_business_checks(connection)


def verify_database(config: DatabaseConfig, connect_factory: Callable[[DatabaseConfig], Connection] | None = None) -> VerificationResult:
    validate_database_name(config.database)
    connection = (connect_server if connect_factory is None else connect_factory)(config)
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"USE {quote_validated_database_name(config.database)}")
            cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
        try:
            violations = run_all_checks(connection, config.database)
        finally:
            connection.rollback()
    except pymysql.MySQLError as exc:
        try:
            connection.rollback()
        except pymysql.MySQLError:
            pass
        raise VerificationError(f"Read-only verification failed: {exc}") from exc
    finally:
        connection.close()
    return VerificationResult(config.database, violations)
