from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--fail-on-skip",
        action="store_true",
        help="fail the test session when any test is skipped",
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not session.config.getoption("--fail-on-skip"):
        return

    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    skipped = () if reporter is None else reporter.stats.get("skipped", ())
    if skipped:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
        reporter.write_sep(
            "=",
            f"zero-skip enforcement failed: {len(skipped)} test(s) skipped",
            red=True,
        )
