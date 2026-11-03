## Summary

<!-- One sentence describing what this PR changes and why. -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactor / cleanup
- [ ] Build / CI / tooling
- [ ] Release / version bump

## Test plan

- [ ] `python -m pytest -q` passes
- [ ] `python -m ruff check townlight_core tests` passes
- [ ] If touching migrations: idempotency tests pass and Gate 1/2/3 logic still holds for downstream consumers
- [ ] If touching public API in `townlight_core.llm`: smoke test verifies symbols still importable

## Checklist

- [ ] CHANGELOG.md updated under `[Unreleased]`
- [ ] If version bumped: pyproject.toml, townlight_core/__init__.py, scripts/verify-release.sh fresh-venv asserts all aligned
- [ ] No secrets committed
- [ ] Linked issue: <!-- #N -->
