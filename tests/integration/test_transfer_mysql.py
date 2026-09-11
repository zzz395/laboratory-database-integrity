from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pymysql
import pytest
from pymysql.constants.SERVER_STATUS import SERVER_STATUS_IN_TRANS

from labdb.config import DatabaseConfig, load_config
from labdb.db import connect_server
from labdb.errors import (
    CommitOutcomeUnknown,
    EquipmentNotFound,
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
from labdb.verify import verify_database


pytestmark = pytest.mark.integration


def _admin_config() -> DatabaseConfig:
    if os.environ.get("LABDB_RUN_INTEGRATION") != "1":
        pytest.skip("set LABDB_RUN_INTEGRATION=1 only for the disposable D2 database")
    return load_config()


def _transfer_config() -> DatabaseConfig:
    admin = _admin_config()
    user = os.environ.get("LABDB_TRANSFER_USER")
    password = os.environ.get("LABDB_TRANSFER_PASSWORD")
    if not user or not password:
        pytest.fail(
            "LABDB_TRANSFER_USER and LABDB_TRANSFER_PASSWORD are required"
        )
    return DatabaseConfig(admin.host, admin.port, user, password, admin.database)


def _test_config() -> DatabaseConfig:
    admin = _admin_config()
    user = os.environ.get("LABDB_TEST_USER")
    password = os.environ.get("LABDB_TEST_PASSWORD")
    if not user or not password:
        pytest.fail("LABDB_TEST_USER and LABDB_TEST_PASSWORD are required")
    return DatabaseConfig(admin.host, admin.port, user, password, admin.database)


def _select_database(connection, config: DatabaseConfig) -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"USE `{config.database}`")


def _read_one(query: str, parameters: tuple[object, ...] = ()):
    config = _transfer_config()
    connection = connect_server(config)
    try:
        _select_database(connection, config)
        with connection.cursor() as cursor:
            cursor.execute(query, parameters)
            return cursor.fetchone()
    finally:
        connection.close()


def _transfer_count() -> int:
    row = _read_one("SELECT COUNT(*) AS count FROM `设备移库记录`")
    return int(row["count"])


def _equipment_location(equipment_id: str) -> str:
    row = _read_one(
        "SELECT `实验室编号` FROM `实验设备` WHERE `设备编号` = %s",
        (equipment_id,),
    )
    return row["实验室编号"]


class RecordingCursor:
    def __init__(self, owner: "ConnectionProxy", delegate) -> None:
        self._owner = owner
        self._delegate = delegate

    def __enter__(self) -> "RecordingCursor":
        self._delegate.__enter__()
        return self

    def __exit__(self, *args: object):
        return self._delegate.__exit__(*args)

    @property
    def rowcount(self) -> int:
        return self._delegate.rowcount

    def execute(self, query: str, parameters=None):
        self._owner.trace.append(" ".join(query.split()))
        return self._delegate.execute(query, parameters)

    def fetchone(self):
        return self._delegate.fetchone()


class ConnectionProxy:
    def __init__(self, delegate, commit_mode: str = "normal") -> None:
        self._delegate = delegate
        self.commit_mode = commit_mode
        self.trace: list[str] = []
        self.begin_calls = 0
        self.commit_calls = 0
        self.rollback_calls = 0
        self.close_calls = 0

    def cursor(self) -> RecordingCursor:
        return RecordingCursor(self, self._delegate.cursor())

    @property
    def server_status(self) -> int:
        return self._delegate.server_status

    def begin(self) -> None:
        self.begin_calls += 1
        self._delegate.begin()

    def commit(self) -> None:
        self.commit_calls += 1
        if self.commit_mode == "before-server":
            raise pymysql.OperationalError(
                2013, "controlled acknowledgement loss before server commit"
            )
        self._delegate.commit()
        if self.commit_mode == "after-server":
            raise pymysql.OperationalError(
                2013, "controlled acknowledgement loss after server commit"
            )

    def rollback(self) -> None:
        self.rollback_calls += 1
        self._delegate.rollback()

    def close(self) -> None:
        self.close_calls += 1
        self._delegate.close()


def _open_transfer_proxy(*, commit_mode: str = "normal") -> ConnectionProxy:
    config = _transfer_config()
    connection = connect_server(config)
    _select_database(connection, config)
    return ConnectionProxy(connection, commit_mode)


def test_01_mysql_version_and_transfer_runtime_privileges() -> None:
    config = _transfer_config()
    connection = connect_server(config)
    try:
        _select_database(connection, config)
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION() AS version")
            assert cursor.fetchone()["version"] == "8.4.11"
            cursor.execute("SHOW GRANTS FOR CURRENT_USER")
            grants = [next(iter(row.values())).upper() for row in cursor.fetchall()]
    finally:
        connection.close()

    business_grants = [grant for grant in grants if " GRANT USAGE " not in f" {grant} "]
    assert business_grants
    assert any("SELECT" in grant and "INSERT" in grant and "UPDATE" in grant for grant in business_grants)
    for forbidden in ("ALL PRIVILEGES", "DELETE", "DROP", "ALTER", "CREATE", "SUPER"):
        assert all(forbidden not in grant for grant in business_grants)


def test_02_success_is_atomic_utc_visible_and_verify_clean() -> None:
    before_count = _transfer_count()
    before_time = datetime.now(timezone.utc)
    result = transfer_equipment_for_config(
        _transfer_config(),
        "D2_SUCCESS_01",
        "EQ_TEST_01",
        "LAB_TEST_A2",
        "LAB_TEST_A1",
        "D2 synthetic successful transfer",
    )
    after_time = datetime.now(timezone.utc)

    assert before_time <= result.transferred_at <= after_time
    assert result.transferred_at.tzinfo is timezone.utc
    assert _equipment_location("EQ_TEST_01") == "LAB_TEST_A1"
    record = _read_one(
        "SELECT * FROM `设备移库记录` WHERE `移库记录编号` = %s",
        ("D2_SUCCESS_01",),
    )
    assert record["设备编号"] == "EQ_TEST_01"
    assert record["原实验室编号"] == "LAB_TEST_A2"
    assert record["目标实验室编号"] == "LAB_TEST_A1"
    assert record["移动原因"] == "D2 synthetic successful transfer"
    assert record["移动时间"].replace(tzinfo=timezone.utc) == result.transferred_at
    assert _transfer_count() == before_count + 1
    assert verify_database(_transfer_config()).violations == ()


def test_03_domain_refusals_have_no_persistent_side_effects() -> None:
    cases = (
        (
            EquipmentNotFound,
            "D2_MISSING_EQUIPMENT",
            "EQ_DOES_NOT_EXIST",
            "LAB_TEST_A1",
            "LAB_TEST_A2",
        ),
        (
            TargetNotFound,
            "D2_MISSING_TARGET",
            "EQ_TEST_02",
            "LAB_TEST_A1",
            "LAB_DOES_NOT_EXIST",
        ),
        (
            StaleSource,
            "D2_STALE_SOURCE",
            "EQ_TEST_02",
            "LAB_TEST_A2",
            "LAB_TEST_B1",
        ),
        (
            SameSourceTarget,
            "D2_SAME_SOURCE_TARGET",
            "EQ_TEST_02",
            "LAB_TEST_A1",
            "LAB_TEST_A1",
        ),
    )
    before_count = _transfer_count()

    for error_type, transfer_id, equipment_id, source, target in cases:
        with pytest.raises(error_type):
            transfer_equipment_for_config(
                _transfer_config(),
                transfer_id,
                equipment_id,
                source,
                target,
                "D2 synthetic refusal",
            )
        assert _read_one(
            "SELECT * FROM `设备移库记录` WHERE `移库记录编号` = %s",
            (transfer_id,),
        ) is None

    assert _equipment_location("EQ_TEST_02") == "LAB_TEST_A1"
    assert _transfer_count() == before_count


def test_04_duplicate_history_id_fails_after_update_and_rolls_back() -> None:
    connection = _open_transfer_proxy()
    try:
        with pytest.raises(TransferIdConflict):
            transfer_equipment(
                connection,
                "MOVE_TEST_01",
                "EQ_TEST_02",
                "LAB_TEST_A1",
                "LAB_TEST_A2",
                "D2 controlled duplicate transfer ID",
            )
    finally:
        connection.close()

    update_index = next(
        index for index, query in enumerate(connection.trace)
        if query.startswith("UPDATE `实验设备`")
    )
    insert_index = next(
        index for index, query in enumerate(connection.trace)
        if query.startswith("INSERT INTO `设备移库记录`")
    )
    assert update_index < insert_index
    assert connection.rollback_calls == 1
    assert connection.commit_calls == 0
    assert _equipment_location("EQ_TEST_02") == "LAB_TEST_A1"
    existing = _read_one(
        "SELECT COUNT(*) AS count FROM `设备移库记录` "
        "WHERE `移库记录编号` = 'MOVE_TEST_01'"
    )
    assert existing["count"] == 1


def test_05_preexisting_transaction_is_preserved_for_its_caller() -> None:
    config = _test_config()
    connection = connect_server(config)
    try:
        _select_database(connection, config)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT `规格` FROM `实验设备` WHERE `设备编号` = 'EQ_TEST_02'"
            )
            original_specification = cursor.fetchone()["规格"]
        connection.begin()
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE `实验设备` SET `规格` = 'D2_PENDING_CALLER_WORK' "
                "WHERE `设备编号` = 'EQ_TEST_02'"
            )

        with pytest.raises(TransactionAlreadyActive):
            transfer_equipment(
                connection,
                "D2_PREEXISTING_TX",
                "EQ_TEST_02",
                "LAB_TEST_A1",
                "LAB_TEST_A2",
                "D2 must not absorb caller transaction",
            )

        assert connection.server_status & SERVER_STATUS_IN_TRANS
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT `规格` FROM `实验设备` WHERE `设备编号` = 'EQ_TEST_02'"
            )
            pending = cursor.fetchone()
        assert pending == {"规格": "D2_PENDING_CALLER_WORK"}
        independently_visible = _read_one(
            "SELECT `规格` FROM `实验设备` WHERE `设备编号` = 'EQ_TEST_02'"
        )
        assert independently_visible["规格"] == original_specification
        connection.rollback()
    finally:
        connection.rollback()
        connection.close()

    assert _read_one(
        "SELECT * FROM `设备移库记录` WHERE `移库记录编号` = 'D2_PREEXISTING_TX'"
    ) is None


def test_06_concurrent_same_source_has_one_winner_and_one_stale_loser() -> None:
    barrier = threading.Barrier(3)
    outcomes: list[object] = []
    outcome_lock = threading.Lock()

    def move(transfer_id: str, target: str) -> None:
        barrier.wait(timeout=10)
        try:
            outcome: object = transfer_equipment_for_config(
                _transfer_config(),
                transfer_id,
                "EQ_TEST_04",
                "LAB_TEST_A2",
                target,
                "D2 synthetic concurrent transfer",
            )
        except Exception as exc:
            outcome = exc
        with outcome_lock:
            outcomes.append(outcome)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(move, "D2_RACE_TO_A1", "LAB_TEST_A1"),
            executor.submit(move, "D2_RACE_TO_B1", "LAB_TEST_B1"),
        )
        barrier.wait(timeout=10)
        for future in futures:
            future.result(timeout=20)

    successes = [item for item in outcomes if not isinstance(item, Exception)]
    failures = [item for item in outcomes if isinstance(item, Exception)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], StaleSource)
    winner = successes[0]
    assert _equipment_location("EQ_TEST_04") == winner.target_lab_id
    rows = _read_one(
        "SELECT COUNT(*) AS count FROM `设备移库记录` "
        "WHERE `移库记录编号` IN ('D2_RACE_TO_A1', 'D2_RACE_TO_B1')"
    )
    assert rows["count"] == 1
    loser_id = (
        "D2_RACE_TO_B1"
        if winner.transfer_id == "D2_RACE_TO_A1"
        else "D2_RACE_TO_A1"
    )
    assert _read_one(
        "SELECT * FROM `设备移库记录` WHERE `移库记录编号` = %s",
        (loser_id,),
    ) is None
    assert verify_database(_transfer_config()).violations == ()


def test_07_lock_wait_timeout_has_no_retry_or_side_effect() -> None:
    locker_config = _test_config()
    locker = connect_server(locker_config)
    transfer = _open_transfer_proxy()
    try:
        _select_database(locker, locker_config)
        locker.begin()
        with locker.cursor() as cursor:
            cursor.execute(
                "SELECT `设备编号` FROM `实验设备` "
                "WHERE `设备编号` = 'EQ_TEST_03' FOR UPDATE"
            )
        with transfer.cursor() as cursor:
            cursor.execute("SET SESSION innodb_lock_wait_timeout = %s", (1,))

        with pytest.raises(TransferDatabaseError) as captured:
            transfer_equipment(
                transfer,
                "D2_LOCK_WAIT",
                "EQ_TEST_03",
                "LAB_TEST_B1",
                "LAB_TEST_A1",
                "D2 controlled lock wait timeout",
            )
        assert captured.value.code == "DATABASE_ERROR"
        locking_reads = [query for query in transfer.trace if query.endswith("FOR UPDATE")]
        assert len(locking_reads) == 1
        assert transfer.begin_calls == 1
        assert transfer.rollback_calls == 1
        assert transfer.commit_calls == 0
        assert _equipment_location("EQ_TEST_03") == "LAB_TEST_B1"
        assert _read_one(
            "SELECT * FROM `设备移库记录` WHERE `移库记录编号` = 'D2_LOCK_WAIT'"
        ) is None
    finally:
        locker.rollback()
        locker.close()
        transfer.close()

    assert _equipment_location("EQ_TEST_03") == "LAB_TEST_B1"


def test_08_commit_ack_loss_after_server_commit_reconciles_matching_record() -> None:
    connection = _open_transfer_proxy(commit_mode="after-server")
    with pytest.raises(CommitOutcomeUnknown) as captured:
        transfer_equipment(
            connection,
            "D2_UNKNOWN_COMMITTED",
            "EQ_TEST_02",
            "LAB_TEST_A1",
            "LAB_TEST_A2",
            "D2 synthetic acknowledged-lost commit",
        )

    assert captured.value.transfer_id == "D2_UNKNOWN_COMMITTED"
    assert connection.commit_calls == 1
    assert connection.rollback_calls == 0
    assert connection.close_calls == 1
    reconciliation = reconcile_transfer_for_config(
        _transfer_config(),
        "D2_UNKNOWN_COMMITTED",
        "EQ_TEST_02",
        "LAB_TEST_A1",
        "LAB_TEST_A2",
        "D2 synthetic acknowledged-lost commit",
    )
    assert reconciliation.status is ReconciliationStatus.MATCHING_COMMITTED
    assert _equipment_location("EQ_TEST_02") == "LAB_TEST_A2"


def test_09_unacknowledged_absent_commit_is_not_replayed() -> None:
    connection = _open_transfer_proxy(commit_mode="before-server")
    with pytest.raises(CommitOutcomeUnknown):
        transfer_equipment(
            connection,
            "D2_UNKNOWN_ABSENT",
            "EQ_TEST_03",
            "LAB_TEST_B1",
            "LAB_TEST_A1",
            "D2 synthetic absent uncertain commit",
        )

    assert connection.begin_calls == 1
    assert connection.commit_calls == 1
    assert connection.rollback_calls == 0
    assert connection.close_calls == 1
    reconciliation = reconcile_transfer_for_config(
        _transfer_config(),
        "D2_UNKNOWN_ABSENT",
        "EQ_TEST_03",
        "LAB_TEST_B1",
        "LAB_TEST_A1",
        "D2 synthetic absent uncertain commit",
    )
    assert reconciliation.status is ReconciliationStatus.NOT_FOUND
    assert _equipment_location("EQ_TEST_03") == "LAB_TEST_B1"
    assert verify_database(_transfer_config()).violations == ()
