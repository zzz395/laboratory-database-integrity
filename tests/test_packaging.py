from __future__ import annotations

from pathlib import Path
import tomllib

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version


ROOT = Path(__file__).resolve().parents[1]


def test_lock_contains_every_declared_dependency_at_the_exact_version() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    locked = {
        Requirement(line)
        for line in (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    }
    declared = {
        Requirement(item)
        for item in (
            *metadata["build-system"]["requires"],
            *metadata["project"]["dependencies"],
            *metadata["project"]["optional-dependencies"]["test"],
        )
    }

    assert declared <= locked
    assert all(str(requirement.specifier).startswith("==") for requirement in locked)


def test_python_metadata_matches_the_validated_version_policy() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    supported = SpecifierSet(metadata["project"]["requires-python"])

    assert Version("3.12") in supported
    assert Version("3.13") in supported
    assert Version("3.11") not in supported
    assert Version("3.14") not in supported
