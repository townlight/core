"""Contract tests for the persisted installed-module inventory and recommendations.

No database is needed here: these cover admission, scoping, determinism and the explicit
separation between a declared inventory, available packages and installation evidence. The
persisted behaviour (append-only revisions, stale guard, concurrency, restart) is exercised
against a real PostgreSQL cluster by ``work/beta-foundations/module-inventory-01/harness.py``.
"""

from __future__ import annotations

import json

import pytest

from civiccore.platform import ModuleManifest
from civiccore.platform.inventory import (
    InventoryConflictError,
    ModuleInventory,
    ModuleInventoryEntry,
    ModuleInventoryError,
    StaleInventoryError,
    UnknownModuleError,
    module_recommendations,
    require_installed,
)


def manifest(name, *, version="1.0.0", **extra):
    return ModuleManifest(
        module_id=name,
        name=name.title(),
        version=version,
        package_name=name,
        civiccore_min_version="1.3.0",
        **extra,
    )


def entry(item, *, enabled=True):
    return ModuleInventoryEntry(
        module_id=item.module_id, version=item.version, enabled=enabled, manifest=item
    )


def inventory(*entries, scope="city-a", revision=1, version="1.3.0"):
    return ModuleInventory(
        scope_id=scope, revision=revision, civiccore_version=version, entries=list(entries)
    )


def test_entry_must_match_its_own_manifest():
    record = manifest("record")
    with pytest.raises(ValueError):
        ModuleInventoryEntry(module_id="meeting", version="1.0.0", enabled=True, manifest=record)
    with pytest.raises(ValueError):
        ModuleInventoryEntry(module_id="record", version="2.0.0", enabled=True, manifest=record)


def test_duplicate_and_blank_scope_are_refused():
    record = manifest("record")
    with pytest.raises(ValueError):
        inventory(entry(record), entry(record))
    # pydantic wraps the admission error into ValidationError, which is a ValueError.
    with pytest.raises(ValueError, match="lowercase identifier"):
        inventory(scope="City A")
    with pytest.raises(ValueError):
        inventory(scope="City-A")
    with pytest.raises(ValueError):
        inventory(scope="1city")


def test_fingerprint_is_stable_and_content_bound():
    record, meeting = manifest("record"), manifest("meeting")
    first = inventory(entry(record), entry(meeting))
    reordered = inventory(entry(meeting), entry(record))
    assert first.fingerprint() == reordered.fingerprint()
    changed = inventory(entry(record, enabled=False), entry(meeting))
    assert first.fingerprint() != changed.fingerprint()
    assert len(first.fingerprint()) == 64


def test_installed_and_enabled_sets_are_reported_separately():
    record, meeting = manifest("record"), manifest("meeting")
    item = inventory(entry(record), entry(meeting, enabled=False))
    assert item.installed_module_ids == ["meeting", "record"]
    assert item.enabled_module_ids == ["record"]


def test_unknown_module_ids_are_refused_not_ignored():
    item = inventory(entry(manifest("record")))
    require_installed(item, ["record"])
    with pytest.raises(UnknownModuleError):
        require_installed(item, ["record", "station"])
    with pytest.raises(UnknownModuleError):
        require_installed(item, ["record-catalog"])


def test_disabled_module_with_satisfied_dependencies_recommends_enable_only():
    record = manifest("record")
    item = inventory(entry(record, enabled=False))
    [recommendation] = module_recommendations(item)
    assert recommendation.module_id == "record"
    assert recommendation.action == "enable"
    assert recommendation.basis == "installed"
    assert "optional" in recommendation.operator_action


def test_disabled_module_with_missing_dependency_is_not_told_to_enable():
    meeting = manifest("meeting", dependencies=[{"module_id": "record"}])
    item = inventory(entry(meeting, enabled=False))
    [recommendation] = module_recommendations(item)
    assert recommendation.action == "resolve-dependency"
    assert "record" in recommendation.reasons[0]


def test_enabled_module_blocked_by_dependency_version_is_reported():
    record = manifest("record", version="1.0.0")
    meeting = manifest("meeting", dependencies=[{"module_id": "record", "min_version": "1.2.0"}])
    item = inventory(entry(record), entry(meeting))
    found = module_recommendations(item)
    # The healthy enabled dependency itself yields no recommendation: silence is not a claim.
    assert [row.module_id for row in found] == ["meeting"]
    assert found[0].action == "resolve-dependency"
    assert "1.2.0" in found[0].reasons[0]
    assert module_recommendations(inventory(entry(manifest("record")))) == []


def test_required_cycle_blocks_both_and_recommends_resolution():
    record = manifest("record", dependencies=[{"module_id": "meeting"}])
    meeting = manifest("meeting", dependencies=[{"module_id": "record"}])
    item = inventory(entry(record), entry(meeting))
    found = module_recommendations(item)
    assert [row.module_id for row in found] == ["meeting", "record"]
    assert all(row.action == "resolve-dependency" for row in found)


def test_core_too_old_is_reported_as_upgrade_core_not_dependency():
    meeting = manifest("meeting")
    item = inventory(entry(meeting), version="1.2.9")
    [recommendation] = module_recommendations(item)
    assert recommendation.action == "upgrade-core"
    assert "CivicCore" in recommendation.operator_action


def test_profile_mismatch_is_reported_as_not_supported():
    record = manifest("record", install_profiles=["server"])
    item = inventory(entry(record, enabled=False))
    [recommendation] = module_recommendations(item)
    assert recommendation.action == "not-supported"


def test_available_packages_are_never_discovered_and_never_installed():
    record = manifest("record")
    item = inventory(entry(record))
    assert module_recommendations(item, []) == []
    # An available package is only considered because the caller passed it in.
    [recommendation] = module_recommendations(item, [manifest("station")])
    assert recommendation.module_id == "station"
    assert recommendation.action == "install"
    assert recommendation.basis == "available"
    assert "Nothing is installed yet" in recommendation.operator_action
    # An available package that would not be admitted is still reported honestly.
    [blocked] = module_recommendations(item, [manifest("clerk", install_profiles=["developer"])])
    assert blocked.action == "not-supported"
    assert blocked.basis == "available"


def test_available_package_missing_its_dependency_is_not_recommended_for_install():
    item = inventory(entry(manifest("record")))
    [recommendation] = module_recommendations(
        item, [manifest("meeting", dependencies=[{"module_id": "station"}])]
    )
    assert recommendation.action == "resolve-dependency"
    assert "station" in recommendation.reasons[0]


def test_installed_package_outranks_a_stale_available_copy_of_the_same_module():
    installed = manifest("record", version="1.0.0")
    item = inventory(entry(installed, enabled=False))
    found = module_recommendations(item, [installed, manifest("record", version="1.0.0")])
    assert len(found) == 1 and found[0].basis == "installed"


def test_recommendations_are_deterministic_and_ordered():
    record = manifest("record")
    meeting = manifest("meeting", dependencies=[{"module_id": "record", "min_version": "2.0.0"}])
    item = inventory(entry(record, enabled=False), entry(meeting, enabled=False))
    available = [manifest("station"), manifest("clerk", install_profiles=["server"])]
    first = [row.model_dump() for row in module_recommendations(item, available)]
    second = [row.model_dump() for row in module_recommendations(item, available)]
    assert first == second
    assert [row["module_id"] for row in first] == ["clerk", "meeting", "record", "station"]
    json.dumps(first)  # serialisable for callers/persistence evidence


def test_recommendation_never_claims_installation_evidence():
    item = inventory(entry(manifest("record"), enabled=False))
    [recommendation] = module_recommendations(item)
    dumped = recommendation.model_dump()
    assert dumped["basis"] == "installed"
    with pytest.raises(ValueError):
        # A caller cannot smuggle a fabricated basis or extra evidence field in.
        type(recommendation)(**{**dumped, "basis": "verified"})


def test_stale_and_conflict_errors_are_distinct_and_named():
    assert issubclass(StaleInventoryError, ModuleInventoryError)
    assert issubclass(InventoryConflictError, ModuleInventoryError)
    assert not issubclass(StaleInventoryError, InventoryConflictError)
