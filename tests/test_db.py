from __future__ import annotations

from unittest.mock import patch

import pytest

from labdb.config import DatabaseConfig
from labdb.db import DatabaseConnectionError, connect_server


def test_connection_enables_tls_for_caching_sha2_authentication() -> None:
    config = DatabaseConfig("127.0.0.1", 3306, "test_user", "test-secret", "labdb_test")

    with patch("labdb.db.pymysql.connect", side_effect=RuntimeError("auth helper missing")) as connect:
        with pytest.raises(DatabaseConnectionError, match="connection or session setup failed") as captured:
            connect_server(config)

    assert connect.call_args.kwargs["ssl"] == {"check_hostname": False}
    assert config.password not in str(captured.value)
