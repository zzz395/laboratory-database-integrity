from __future__ import annotations

import os
from pathlib import Path

import pytest

from labdb import cli
from labdb.config import DatabaseConfig, load_config
from labdb.db import connect_server
from labdb.initialize import split_sql_statements
from labdb.metadata import EXPECTED_COLUMNS, EXPECTED_PRIMARY_KEYS
from labdb.seed import EXPECTED_SEED_COUNTS, SeedExecutionError, SeedRefused, default_seed_path, seed_database, table_row_counts
from labdb.verify import run_business_checks, verify_database


pytestmark = pytest.mark.integration


def _runtime_config() -> DatabaseConfig:
    if os.environ.get("LABDB_RUN_INTEGRATION") != "1":
        pytest.skip("set LABDB_RUN_INTEGRATION=1 only for the disposable D1B database")
    return load_config()


def _test_config() -> DatabaseConfig:
    runtime = _runtime_config()
    user = os.environ.get("LABDB_TEST_USER")
    password = os.environ.get("LABDB_TEST_PASSWORD")
    if not user or not password:
        pytest.fail("LABDB_TEST_USER and LABDB_TEST_PASSWORD are required for isolated negative fixtures")
    return DatabaseConfig(runtime.host, runtime.port, user, password, runtime.database)


def _data_fingerprint(config: DatabaseConfig) -> tuple[tuple[object, ...], ...]:
    connection = connect_server(config)
    result: list[tuple[object, ...]] = []
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"USE `{config.database}`")
            for table in sorted(EXPECTED_COLUMNS):
                order = ", ".join(f"`{column}`" for column in EXPECTED_PRIMARY_KEYS[table])
                cursor.execute(f"SELECT * FROM `{table}` ORDER BY {order}")
                rows = tuple(tuple((key, str(value)) for key, value in row.items()) for row in cursor.fetchall())
                result.append((table, len(rows), rows))
    finally:
        connection.close()
    return tuple(result)


def _points(connection) -> dict[tuple[str, str], tuple[int, int, int]]:
    path = Path(__file__).resolve().parents[2] / "sql" / "queries.sql"
    statements = split_sql_statements(path.read_text(encoding="utf-8"))
    assert len(statements) == 1
    with connection.cursor() as cursor:
        cursor.execute(statements[0])
        return {
            (row["学生用户id"], row["学期编号"]):
            (int(row["初始积分"]), int(row["扣分合计"]), int(row["剩余积分"]))
            for row in cursor.fetchall()
        }


def test_01_controlled_seed_failure_rolls_back_every_table(tmp_path: Path) -> None:
    config = _runtime_config()
    fixture = tmp_path / "controlled-seed-failure.sql"
    fixture.write_text(
        default_seed_path().read_text(encoding="utf-8")
        + "\nINSERT INTO `学院` (`学院编号`, `学院名称`) VALUES ('COL_TEST_A', 'controlled duplicate');\n",
        encoding="utf-8",
    )

    with pytest.raises(SeedExecutionError, match="complete seed transaction was rolled back"):
        seed_database(config, fixture)

    connection = connect_server(config)
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"USE `{config.database}`")
        assert table_row_counts(connection) == dict.fromkeys(EXPECTED_SEED_COUNTS, 0)
    finally:
        connection.close()


def test_02_seed_success_repeat_refusal_and_canonical_counts() -> None:
    config = _runtime_config()
    result = seed_database(config)
    assert dict(result.row_counts) == EXPECTED_SEED_COUNTS
    assert result.total_rows == 68
    before = _data_fingerprint(config)

    with pytest.raises(SeedRefused, match="all 22 business tables to be empty"):
        seed_database(config)

    assert _data_fingerprint(config) == before


def test_03_valid_seed_verify_and_read_only_fingerprint() -> None:
    config = _runtime_config()
    before = _data_fingerprint(config)
    result = verify_database(config)
    after = _data_fingerprint(config)
    assert result.violations == ()
    assert after == before


NEGATIVE_CASES = (
    ("V01_TERM_OVERLAP", "TERM_TEST_1|TERM_TEST_OVERLAP", "INSERT INTO `学期` (`学期编号`, `学期名称`, `开始时间`, `结束时间`, `初始积分`) VALUES ('TERM_TEST_OVERLAP', '合成重叠学期', '2026-03-01 00:00:00.000000', '2026-04-01 00:00:00.000000', 12)"),
    ("V02_RESERVATION_OUTSIDE_TERM", "RES_TEST_01", "UPDATE `预约表` SET `开始时间` = '2025-12-31 23:00:00.000000' WHERE `预约表单号` = 'RES_TEST_01'"),
    ("V03_COURSE_RESERVATION_TEACHER_MISMATCH", "RES_TEST_04", "UPDATE `预约表` SET `用户id` = 'USR_MANAGER_A' WHERE `预约表单号` = 'RES_TEST_04'"),
    ("V04_RESERVATION_CAPACITY_EXCEEDED", "RES_TEST_01", "UPDATE `预约表` SET `人数` = 21 WHERE `预约表单号` = 'RES_TEST_01'"),
    ("V05_CHECKIN_RESERVATION_STATUS", "CHECKIN_TEST_01", "UPDATE `预约表` SET `预约状态` = '待审核', `审核人用户id` = NULL WHERE `预约表单号` = 'RES_TEST_01'"),
    ("V06_CHECKIN_TIME_WINDOW", "CHECKIN_TEST_01", "UPDATE `签到记录` SET `签到时间` = '2026-03-01 09:29:00.000000' WHERE `签到记录id` = 'CHECKIN_TEST_01'"),
    ("V07_NO_SHOW_WITH_CHECKIN", "RES_TEST_01", "UPDATE `预约表` SET `预约状态` = '爽约' WHERE `预约表单号` = 'RES_TEST_01'"),
    ("V08_NO_SHOW_TIME", "VIOL_TEST_01", "UPDATE `违规记录` SET `违规时间` = '2026-03-03 14:14:00.000000' WHERE `违规id` = 'VIOL_TEST_01'"),
    ("V09_LATE_EVIDENCE", "VIOL_TEST_02", "UPDATE `签到记录` SET `签到时间` = '2026-03-02 12:00:00.000000' WHERE `签到记录id` = 'CHECKIN_TEST_02'"),
    ("V10_EARLY_LEAVE_EVIDENCE", "VIOL_TEST_03", "UPDATE `签到记录` SET `签退时间` = '2026-03-02 13:00:00.000000' WHERE `签到记录id` = 'CHECKIN_TEST_02'"),
    ("V11_OVERTIME_EVIDENCE", "VIOL_TEST_04", "UPDATE `签到记录` SET `签退时间` = '2026-10-01 11:00:00.000000' WHERE `签到记录id` = 'CHECKIN_TEST_03'"),
    ("V12_CANCELLED_WITHOUT_CHANGE", "RES_TEST_01", "UPDATE `预约表` SET `预约状态` = '已取消' WHERE `预约表单号` = 'RES_TEST_01'"),
    ("V13_REPAIR_STARTED_BEFORE_REPORT", "EXEC_TEST_02", "UPDATE `执行维修` SET `开始时间` = '2026-04-03 07:00:00.000000' WHERE `维修记录编号` = 'EXEC_TEST_02'"),
    ("V14_INVALID_ACCEPTOR", "EXEC_TEST_03", "UPDATE `执行维修` SET `验收人用户id` = 'USR_STUDENT_ONLY' WHERE `维修记录编号` = 'EXEC_TEST_03'"),
    ("V15_REPAIR_STATE_INCONSISTENCY", "REPAIR_TEST_01", "INSERT INTO `执行维修` (`维修记录编号`, `报修单ID`, `维修人员工号`, `维修内容`, `开始时间`, `完成时间`, `维修费用`, `验收结果`, `验收人用户id`, `验收时间`) VALUES ('EXEC_TEST_BAD', 'REPAIR_TEST_01', 'WORKER_TEST_01', '合成状态负例', '2026-04-01 09:00:00.000000', NULL, NULL, NULL, NULL, NULL)"),
    ("V16_TRANSFER_LOCATION_MISMATCH", "MOVE_TEST_01", "UPDATE `实验设备` SET `实验室编号` = 'LAB_TEST_A1' WHERE `设备编号` = 'EQ_TEST_01'"),
)


@pytest.mark.parametrize(("expected_code", "expected_id", "mutation"), NEGATIVE_CASES)
def test_04_each_consistency_violation_is_detected_and_rolled_back(expected_code: str, expected_id: str, mutation: str) -> None:
    connection = connect_server(_test_config())
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"USE `{_test_config().database}`")
        connection.begin()
        with connection.cursor() as cursor:
            cursor.execute(mutation)
        found = run_business_checks(connection)
        assert any(item.code == expected_code and item.entity_id == expected_id for item in found)
        connection.rollback()
        assert run_business_checks(connection) == ()
    finally:
        connection.rollback()
        connection.close()


def test_05_student_term_points_and_floor_at_zero() -> None:
    connection = connect_server(_test_config())
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"USE `{_test_config().database}`")
        points = _points(connection)
        assert points == {
            ("USR_DUAL_ROLE", "TERM_TEST_1"): (12, 4, 8),
            ("USR_DUAL_ROLE", "TERM_TEST_2"): (12, 1, 11),
            ("USR_STUDENT_ONLY", "TERM_TEST_1"): (12, 0, 12),
            ("USR_STUDENT_ONLY", "TERM_TEST_2"): (12, 0, 12),
        }
        assert all(user != "USR_MANAGER_A" for user, _ in points)

        connection.begin()
        with connection.cursor() as cursor:
            for number in range(1, 6):
                reservation = f"RES_FLOOR_{number}"
                violation = f"VIOL_FLOOR_{number}"
                day = 10 + number
                cursor.execute(
                    "INSERT INTO `预约表` (`预约表单号`, `实验室编号`, `用户id`, `学期编号`, `课程编号`, `审核人用户id`, `预约类型`, `开始时间`, `结束时间`, `人数`, `用途`, `预约状态`, `驳回原因`) VALUES (%s, 'LAB_TEST_A1', 'USR_DUAL_ROLE', 'TERM_TEST_1', NULL, 'USR_MANAGER_A', '个人', %s, %s, 1, '合成积分下限负载', '爽约', NULL)",
                    (reservation, f"2026-06-{day:02d} 10:00:00.000000", f"2026-06-{day:02d} 11:00:00.000000"),
                )
                cursor.execute(
                    "INSERT INTO `违规记录` (`违规id`, `预约表单号`, `签到记录id`, `违规类型`, `扣分值`, `违规时间`) VALUES (%s, %s, NULL, '爽约', 2, %s)",
                    (violation, reservation, f"2026-06-{day:02d} 10:20:00.000000"),
                )
        assert _points(connection)[("USR_DUAL_ROLE", "TERM_TEST_1")] == (12, 14, 0)
        connection.rollback()
    finally:
        connection.rollback()
        connection.close()


def test_06_verify_mysql_connection_error_path_returns_two(monkeypatch, capsys) -> None:
    config = _runtime_config()
    monkeypatch.setenv("LABDB_HOST", config.host)
    monkeypatch.setenv("LABDB_PORT", str(config.port))
    monkeypatch.setenv("LABDB_USER", config.user)
    monkeypatch.setenv("LABDB_PASSWORD", "controlled-wrong-password")
    monkeypatch.setenv("LABDB_DATABASE", config.database)
    assert cli.main(["verify"]) == 2
    assert "Verification execution failed" in capsys.readouterr().err
