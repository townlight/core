# SPDX-License-Identifier: AGPL-3.0-only
"""``python -m townlight_core.scaffold`` → ``townlight_core.scaffold.cli.main``."""

from __future__ import annotations

from townlight_core.scaffold.cli import main

if __name__ == "__main__":  # pragma: no cover - exercised through subprocess smoke
    raise SystemExit(main())
