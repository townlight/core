from __future__ import annotations

from pathlib import Path

import townlight_core.catalog
import townlight_core.exemptions
import townlight_core.scaffold


REPO_ROOT = Path(__file__).resolve().parents[1]

HISTORICAL_DEFERRAL_ADRS = {
    "townlight_core.scaffold": REPO_ROOT / "docs/adr/ADR-0003-defer-civiccore-scaffold.md",
}

RESUMPTION_ADRS = {
    "townlight_core.scaffold": REPO_ROOT / "docs/adr/ADR-0007-beta-module-scaffold.md",
}


def test_placeholder_namespaces_have_freeze_line_adrs() -> None:
    for namespace, path in HISTORICAL_DEFERRAL_ADRS.items():
        text = path.read_text(encoding="utf-8")

        assert namespace.replace("townlight_core", "civiccore") in text
        assert "Status: Accepted" in text
        assert "Explicit downstream consumption rule" in text
        assert "no module depends" in text
        assert "versioned CivicCore release artifact" in text  # Exact historical decision.


def test_placeholder_adr_index_lists_all_placeholder_namespaces() -> None:
    index = (REPO_ROOT / "docs/adr/index.md").read_text(encoding="utf-8")

    for namespace, path in HISTORICAL_DEFERRAL_ADRS.items():
        assert namespace in index
        assert path.name in index


def test_scaffold_resumption_retains_historical_deferral_and_names_new_contract() -> None:
    # Historical ADR-0003 keeps its accepted deferral text; ADR-0007 records the
    # actual candidate contract, exactly like ADR-0004 did for the catalog.
    historical = (REPO_ROOT / "docs/adr/ADR-0003-defer-civiccore-scaffold.md").read_text(
        encoding="utf-8"
    )
    current = RESUMPTION_ADRS["townlight_core.scaffold"].read_text(encoding="utf-8")

    assert "Status: Accepted" in historical
    assert "Defer" in historical
    assert "Supersedes: ADR-0003" in current
    assert "not released" in current
    assert "generate_module_project" in current
    assert callable(townlight_core.scaffold.generate_module_project)
    assert callable(townlight_core.scaffold.plan_module_project)
    assert callable(townlight_core.scaffold.main)

    index = (REPO_ROOT / "docs/adr/index.md").read_text(encoding="utf-8")
    assert RESUMPTION_ADRS["townlight_core.scaffold"].name in index


def test_scaffold_package_still_withholds_downstream_dependency() -> None:
    docstring = " ".join((townlight_core.scaffold.__doc__ or "").split())

    assert "ADR-0003-defer-civiccore-scaffold.md" in docstring
    assert "No downstream module may" in docstring
    assert "versioned Townlight Core release artifact" in docstring
    assert "not a release artifact" in docstring


def test_catalog_resumption_retains_historical_deferral_and_names_open_scope():
    historical = (REPO_ROOT / "docs/adr/ADR-0001-defer-civiccore-catalog.md").read_text(
        encoding="utf-8"
    )
    current = (REPO_ROOT / "docs/adr/ADR-0004-beta-shared-catalog.md").read_text(encoding="utf-8")
    assert "Status: Accepted" in historical
    assert "installed-module inventory" in current
    assert callable(townlight_core.catalog.import_catalog)
    assert callable(townlight_core.catalog.connectors_for)
