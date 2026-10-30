"""Dependency admission must not enable a module whose prerequisites cannot run."""

import pytest
from civiccore.platform import ModuleManifest, build_module_registry


def module(name, **extra):
    return ModuleManifest(
        module_id=name,
        name=name,
        version="1.0.0",
        package_name=name,
        civiccore_min_version="1.2.0",
        **extra,
    )


def resolve(*modules, version="1.3.0.dev1"):
    return {
        entry.module_id: entry
        for entry in build_module_registry(list(modules), civiccore_version=version).entries
    }


def test_minimum_core_version_blocks_older_and_prerelease_core():
    for version in ("1.1.9", "1.2.0.dev1"):
        assert resolve(module("meeting"), version=version)["meeting"].status == "blocked"


def test_incompatible_dependency_blocks_transitive_dependants():
    entries = resolve(
        module("record", install_profiles=["server"]),
        module("meeting", dependencies=[{"module_id": "record"}]),
        module("station", dependencies=[{"module_id": "meeting"}]),
    )
    assert all(not entry.enabled for entry in entries.values())


def test_dependency_version_is_enforced():
    entries = resolve(
        module("record"),
        module("meeting", dependencies=[{"module_id": "record", "min_version": "1.1.0"}]),
    )
    assert entries["record"].enabled
    assert not entries["meeting"].enabled


def test_required_cycle_is_blocked_but_unrelated_module_runs():
    entries = resolve(
        module("record", dependencies=[{"module_id": "meeting"}]),
        module("meeting", dependencies=[{"module_id": "record"}]),
        module("station"),
    )
    assert not entries["record"].enabled and not entries["meeting"].enabled
    assert entries["station"].enabled


def test_optional_absent_dependency_does_not_block():
    assert resolve(module("meeting", dependencies=[{"module_id": "absent", "required": False}]))[
        "meeting"
    ].enabled


def test_invalid_version_is_rejected():
    with pytest.raises(ValueError):
        resolve(module("meeting"), version="unknown")
