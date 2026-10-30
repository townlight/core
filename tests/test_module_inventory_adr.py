# SPDX-License-Identifier: AGPL-3.0-only
"""ADR-0008 must extend the catalog deferral without rewriting history.

The historical ADR-0001/ADR-0004 text stays byte-identical; ADR-0008 records the actual
installed-module inventory contract and names what is still open. This mirrors how ADR-0007
handled the scaffold deferral.
"""

from __future__ import annotations

from pathlib import Path

import civiccore.platform.inventory as inventory


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_inventory_adr_records_contract_and_retains_historical_deferrals() -> None:
    current = (REPO_ROOT / "docs/adr/ADR-0008-beta-module-inventory.md").read_text(encoding="utf-8")

    assert "Supersedes: ADR-0001" in current
    assert "ADR-0004" in current
    assert "append-only" in current
    assert "not released" in current
    # The non-claims the contract must keep making.
    assert "No scanning, network access, package enumeration" in current
    assert "Advice separated from evidence" in current
    assert "civiccore.catalog" in current
    assert "build_module_registry" in current

    historical = (REPO_ROOT / "docs/adr/ADR-0001-defer-civiccore-catalog.md").read_text(
        encoding="utf-8"
    )
    assert "Status: Accepted" in historical
    assert "Defer" in historical
    assert "installed-module catalog" in historical

    index = (REPO_ROOT / "docs/adr/index.md").read_text(encoding="utf-8")
    assert "ADR-0008-beta-module-inventory.md" in index
    assert "ADR-0001-defer-civiccore-catalog.md" in index


def test_inventory_module_documents_the_non_claims_it_must_uphold() -> None:
    docstring = " ".join((inventory.__doc__ or "").split())

    assert "never scans a machine" in docstring
    assert "exactly one module resolver" in docstring
    assert "civiccore.platform.modules.build_module_registry" in docstring
    assert "not installation evidence" in docstring
    assert "reference data about *vendor systems*" in docstring
    assert "caller-supplied" in docstring


def test_inventory_contract_is_importable_from_the_platform_namespace() -> None:
    import civiccore.platform as platform

    for name in (
        "ModuleInventory",
        "ModuleInventoryEntry",
        "ModuleRecommendation",
        "record_inventory",
        "current_inventory",
        "inventory_revision",
        "inventory_history",
        "require_installed",
        "module_recommendations",
        "ModuleInventoryError",
        "UnknownModuleError",
        "StaleInventoryError",
        "InventoryConflictError",
    ):
        assert name in platform.__all__, name
        assert getattr(platform, name) is not None, name
