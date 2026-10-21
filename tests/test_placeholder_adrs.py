from __future__ import annotations

from pathlib import Path

import civiccore.catalog
import civiccore.exemptions
import civiccore.scaffold


REPO_ROOT = Path(__file__).resolve().parents[1]

PLACEHOLDER_ADRS = {
    "civiccore.catalog": REPO_ROOT / "docs/adr/ADR-0001-defer-civiccore-catalog.md",
    "civiccore.exemptions": REPO_ROOT / "docs/adr/ADR-0002-defer-civiccore-exemptions.md",
    "civiccore.scaffold": REPO_ROOT / "docs/adr/ADR-0003-defer-civiccore-scaffold.md",
}

PLACEHOLDER_MODULES = {
    "civiccore.catalog": civiccore.catalog,
    "civiccore.exemptions": civiccore.exemptions,
    "civiccore.scaffold": civiccore.scaffold,
}


def test_placeholder_namespaces_have_freeze_line_adrs() -> None:
    for namespace, path in PLACEHOLDER_ADRS.items():
        text = path.read_text(encoding="utf-8")

        assert namespace in text
        assert "Status: Accepted" in text
        assert "Explicit downstream consumption rule" in text
        assert "no module depends" in text
        assert "versioned Townlight Core release artifact" in text


def test_placeholder_adr_index_lists_all_placeholder_namespaces() -> None:
    index = (REPO_ROOT / "docs/adr/index.md").read_text(encoding="utf-8")

    for namespace, path in PLACEHOLDER_ADRS.items():
        assert namespace in index
        assert path.name in index


def test_placeholder_package_docstrings_point_to_adrs() -> None:
    for namespace, module in PLACEHOLDER_MODULES.items():
        docstring = module.__doc__ or ""
        normalized_docstring = " ".join(docstring.split())
        adr = PLACEHOLDER_ADRS[namespace]

        assert "Reserved placeholder" in normalized_docstring
        assert adr.name in normalized_docstring
        assert "No downstream module may" in normalized_docstring
        assert "versioned CivicCore release artifact" in normalized_docstring
