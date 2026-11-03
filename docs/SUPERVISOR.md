<!-- supervisor-card: generated (safe to overwrite; delete this line if you hand-edit) -->
# Townlight Core Supervisor Card

One-page operating card for Scott. Keep this open when you supervise a session.
Everything here is grounded in what actually exists in this repo today.

Current state at the time this card was written:
- Branch: `docs/phase2-closeout-standardization` (Phase 1 complete, Phase 2 closeout / standardization in flight)
- Version: `townlight_core 0.2.0` (pyproject.toml + townlight_core/__init__.py agree)
- Rule 11 hook wired locally in `.claude/hooks/` (untracked in git after 6fb2c6f)
- townlight_core is the validation project for Hard Rule 11 (Commit-Size Acknowledgment Gate)

---

## 1. Before every session (30 seconds)

Skim in this order, top-down:

1. `README.md` — Status section tells you what phase Townlight Core is in today.
2. `CHANGELOG.md` — look at `## [Unreleased]` to see what's accumulated since last tag.
3. `git log --oneline -10` — last 10 commits, note the current branch.
4. `docs/` — this card plus `index.html` (landing page); nothing else should live here yet.
5. `.claude/settings.json` + `.claude/hooks/commit-size-gate.py` — confirm the Rule 11 hook is still wired (PreToolUse on Bash) and THRESHOLD is still `800`. This is the validation surface; if it's gone or mutated, the session's first job is to say so.

If any of those five shows drift you didn't expect, stop and ask the agent to explain before giving it a task.

---

## 2. During the session — what you actually do

Five things, in order of how often you'll need them:

1. **Run the tests** — from repo root: `pytest` (configured in pyproject.toml `[tool.pytest.ini_options]`, `testpaths = ["tests"]`, asyncio mode auto). Current suite: `tests/test_smoke.py`, `tests/test_baseline_idempotency.py`. Any logic change must either update these or add a new test.
2. **Lint + type check** — `ruff check .` (configured, `target-version = py311`, `line-length = 100`). No mypy in pyproject today; don't let the agent pretend there is.
3. **Verify before push** — there's no `verify-release.sh` yet; `scripts/verify/` exists as a directory placeholder. When the agent says "ran verify", ask which command. Until the script is written, manual pre-push is: tests green + ruff clean + CHANGELOG updated + version consistent (pyproject.toml line 7, townlight_core/__init__.py line 13).
4. **Watch Rule 11 behavior** — this project's job is to validate the gate. Every time the agent runs a `git commit` via Bash, the PreToolUse hook (`.claude/hooks/commit-size-gate.sh` → `.py`, THRESHOLD=800) fires. Expected behavior:
   - <800 staged lines → silent pass
   - ≥800 staged lines with a literal bracketed tag (`[MVP]`, `[LARGE-CHANGE]`, `[REFACTOR]`, `[INITIAL]`, `[MERGE]`, `[REVERT]`, `[SCOPE-EXPANSION: reason]`) → pass
   - ≥800 staged lines with no tag → blocked (exit 2)
   - `--amend`, `-F`, editor commits → fail-open (bypass). This is intentional.
   - You say the literal phrase `override rule 11` → 60-second one-shot bypass.
   If you see a false positive (small commit blocked, or tag-present commit blocked), that's the bug you're hunting. Save the stderr output.
5. **Keep townlight_core and townlight_core-ui aligned** — if a schema, token, or shell component changes in `townlight_core/` (models, auth, catalog) or `townlight_core-ui/` (components, shell, tokens), make sure the agent touches both sides in the same commit. Extraction-in-sync was the Phase 1 contract and still applies through Phase 2 closeout.

---

## 3. Hard rules active on this project

All eleven from `~/.claude/CLAUDE.md` apply. One-liners:

1. **Read before you write** — read every file you'll modify before modifying it.
2. **Run before you declare done** — paste actual terminal output, not "should work".
3. **Tests for logic changes** — every logic change adds or updates a test.
4a. **Never skip tests** — no `@pytest.mark.skip`, no `pytest.skip()`, ever.
4. **No secrets in client code** — .gitignore already covers env; don't bypass.
5. **Challenge bad requirements** — push back on specs that degrade UX.
6. **Work incrementally** — small verified steps, not one giant end-to-end build.
7. **No wasteful operations** — don't reread or reinstall for no reason.
8. **Stay in scope** — report adjacent issues, don't fix them unless asked.
9. **Documentation Gate** — 6 artifacts must exist before any push: `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE`, `.gitignore`, `docs/index.html`. All six are present here today.
10. **Subagent Obligation** — 2+ non-overlapping scopes → parallel subagents, not serial-inline. 3rd distinct inline Edit per turn is blocked by the global gate.
11. **Commit-Size Acknowledgment Gate — ACTIVE HERE, validation project.** Staged diff >800 lines needs a literal bracketed tag in the commit message: `[MVP]`, `[LARGE-CHANGE]`, `[REFACTOR]`, `[INITIAL]`, `[MERGE]`, `[REVERT]`, or `[SCOPE-EXPANSION: reason]`. Substring matches don't count — it must be the literal bracketed token. Bypass surfaces (fail-open by design): `git commit --amend`, `git commit -F <file>`, editor commits without `-m`. Pressure valve: say the literal phrase `override rule 11` and the next commit within 60 seconds is waved through once.

---

## 4. Four-pass gate

See `coder-ui-qa-test` skill.

---

## 5. Good session ending — project-specific checklist

A session on townlight_core is done when all of these are true:

- `pytest` green from repo root (no skips, no xfails added).
- `ruff check .` clean.
- Version matches across `pyproject.toml` (line 7) and `townlight_core/__init__.py` (line 13). Bump both together or neither.
- `CHANGELOG.md` `## [Unreleased]` has an entry for every user-visible change made this session.
- No false-positive Rule 11 blocks during the session. If the gate blocked a commit, one of three things is true and you can say which: (a) the commit genuinely was ≥800 lines and deserved a tag, (b) it was a known bypass surface, (c) it's a bug and you've captured stderr + the staged diff size for the post-mortem.
- If the session touched anything in both `townlight_core/` and `townlight_core-ui/`, the two sides agree — shared schemas, tokens, or interfaces are in sync. Extraction-in-sync remains the contract through Phase 2 closeout; drift between core and UI is a regression.
- Branch is still `docs/phase2-closeout-standardization` (or a child of it) unless we explicitly cut a new one. No surprise branch moves.
- No files created outside scope: no `tasks.md`, no `lessons-learned.md`, no `handoff.md`, no `tests/uat/`, no `private/`, no new hook scripts. If the agent wrote any of those, delete them before closing.
