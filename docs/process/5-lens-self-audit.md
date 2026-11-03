# 5-lens self-audit (before every push)

This is the implementation-side counterpart to the verification-side audit protocol at `C:\Users\scott\OneDrive\Desktop\Claude\TOWNLIGHT_AUDIT_PROTOCOL.md`. The verification protocol governs how the auditing agent (Claude) audits work that has already landed. This document governs how the implementing agent (Codex) audits its own work *before* a push, so the verification turn finds less to fix.

Both Codex and Claude read this file. The rule body, the artifact-state checklist, and the report format below are shared. The implementing-agent-side discipline (chat-promise rejection) and the verifier-side discipline (mandatory 10-section output) live in their respective files.

## Roles in this project

- **Implementing agent:** Codex. Writes code, docs, status artifacts across 26 module repos. Runs this 5-lens self-audit before every push.
- **Auditing agent:** Claude. Verifies Codex's claims against actual artifacts. Produces the mandatory 10-section output defined in `TOWNLIGHT_AUDIT_PROTOCOL.md`.

## The rule

**HARD RULE.** Before any `git push` that touches code, docs, or status artifacts, run a hostile 5-lens self-audit on the actual diff. The audit result is part of the report. No exceptions even when the change "feels small" or "is just a typo fix."

## Why this rule exists

The failure mode it prevents: an implementation commit lands, CI is green, Codex declares "done," and then Claude finds a list of real drift items Codex should have caught — wrong endpoint paths, stale totals, contradictory sign-off blocks, overclaims, "zero skips" without qualification, "Closed" without cited evidence, and durable docs (README, CHANGELOG, HANDOFF, PR body, verification log) drifting in parallel because they're treated as artifacts to update sometimes rather than as state to maintain.

The drift isn't in features. It's in the surrounding durable artifacts that should move with every code commit but don't because the implementing agent treats them as artifacts instead of state.

## The five lenses

Each lens is *hostile* — assume the diff lies until evidence proves otherwise.

1. **Engineering.** Read the diff. For every claim, name, path, version, or API in the changes: grep the actual code/config to verify it matches reality. If the diff names a pin URL or wheel SHA, grep for it across consuming modules. If it names a SHA or run ID, verify it against `gh run view`. If it names a function or symbol, verify it's exported. If it names a `verify-suite-state.py` output line, run the verifier and read the line. Hostile means: assume the diff lies until grep proves otherwise.

2. **UX.** For any user-visible string, message, label, or workflow change: read it cold as if you'd never seen the feature. Does it make sense to a first-time operator? Does it match the copy in adjacent module READMEs (terminology, voice, formality)? Does an error path have a "Next step" line? Does the install script's "Generated secrets visible via docker exec env" warning actually appear in the doc's table of contents? Hostile means: assume the user is confused until the copy proves it doesn't confuse them.

3. **Tests.** For any logic / data-flow / public-interface change: is there a test? Does it run? Does it lock the behavior, or does it merely *exercise* the code path? Does it actually execute in CI, or does it skip? Townlight-specific: does the test cover the LIVE-STATE classification path AND the SHAPE-GUARD negative-assertion path? Hostile means: a green check is not a real assertion; "passes" is not "covers." Skip predicates lie by default — verify they don't apply.

4. **Docs.** For every code change: did the umbrella CHANGELOG move with it? The per-module CHANGELOG? The `.agent-workflows/HANDOFF_<latest>.md` (per-module if applicable, umbrella always)? The umbrella PR body? The `docs/release-recovery-status.md`? The audit punchlist row in `audit-townlight-2026-05-09/sprint-punchlist.md`? Hostile means: a doc that's silent about a change you just made is wrong, not "OK because the code is right."

5. **QA.** Read the final state, not the diff. Open the changed files as the next agent walking in cold. Are there contradictions across files? Does the umbrella CHANGELOG say one thing while the module CHANGELOG says another? Does the audit punchlist top-totals row reconcile with the row count? Are status words used per the audit protocol (`Closed` / `Implemented` / `Open` / `Deferred by Scott` / `Blocked`, never `done` / `ready` / `taggable` / `shippable`)? Does `verify-suite-state.py --remote-only` show what the CHANGELOG claims? Hostile means: assume drift until cross-file reading proves there is none.

## Artifact-state checklist

This is the specific drift that has bitten Townlight most. Run every item before push.

- [ ] Audit punchlist (`audit-townlight-2026-05-09/sprint-punchlist.md`) top-totals row matches the actual row count by severity. Every `[x]` row has a `Cross-ref: <finding-id>` AND a proof citation (commit SHA, PR number, file path, or verifier output).
- [ ] No row says `(this commit)` — replace with the actual SHA before pushing.
- [ ] Umbrella PR body matches branch state: no stale `N of M` counts, no checkbox left unchecked for an item now Closed, no missing run IDs. Has `release-tag` label if and only if the PR includes truth artifacts (spec, verifier, modules.json, CHANGELOG, release-recovery-status, downstream-pins).
- [ ] Umbrella CHANGELOG matches what shipped — no "All exit criteria met" if there was a carve-out, no stale test counts. Per-module CHANGELOG also updated for module-level changes.
- [ ] `.agent-workflows/HANDOFF_<latest>.md` names the current branch, current HEAD, current PR, current tag (if any), and the Townlight-wide verifier output (`VERIFY-SUITE-STATE: PASSED` or named failures).
- [ ] Verification log on tag candidates: no "Ready to tag" claim without the tag-blocking gates Closed with proof. The release-lockstep-gate green status is captured.
- [ ] Status words: no `done`, `green`, `ready`, `taggable`, `shippable`, `complete` unless the release gate actually supports them (`VERIFY-SUITE-STATE: PASSED` + `release-lockstep-gate` green + release object exists with all artifacts).
- [ ] Working tree clean except intentional/declared uncommitted work. The pre-existing dirty `installer/dist/` and `installer/generated/` files predate the recovery sweep — state this explicitly in the report rather than silently accepting them.
- [ ] Cleanroom claims qualified: CI cleanroom skips are CI-only; local cleanroom skips are local-only; never collapse them.
- [ ] Whole-PR diff scope check: `git diff --name-status main..HEAD` must contain only the slice's intended file set. `git status --short` is not sufficient; sibling commits can land unrelated files.
- [ ] Non-ASCII scan on every new/modified durable doc: em-dashes, arrows, section signs should be ASCII unless intentional. Run `LC_ALL=C.UTF-8 grep -P '[^\x00-\x7F]' <files>` before push.
- [ ] **SHA citations are full-length.** Every SHA256 citation is exactly 64 hex characters; every SHA1 citation is exactly 40. Run `grep -E '[a-f0-9]{56,63}\b' <docs>` and inspect any hits as candidates for truncation. Origin receipt: Townlight Meetings B1 handoff 2026-05-10 required PR #119 to correct.
- [ ] **release-lockstep-gate alignment.** If the umbrella PR has the `release-tag` label, verify every required truth artifact path appears in `gh pr diff <n>`: spec §18 truth table, `scripts/verify-suite-state.py` (if version constants changed), `installer/modules.json`, `CHANGELOG.md`, `docs/release-recovery-status.md`, `docs/release-lockstep/downstream-pins.md`. Origin receipt: release-lockstep-gate exists because Sprint A landed 7 false v1.0 tags that bypassed truth coordination.
- [ ] **Tag-move record present if any tag moves happened.** Completion handoff includes a tag-move table (Tag / Initial SHA / Final SHA / Moves / Notes) for every tag that moved during the sprint. Origin receipt: Townlight Records v1.5.0 — 4 tag moves recorded.

## Post-push SHA-propagation step

Separate post-push pass, not optional. After `git push` succeeds:

1. Capture the new HEAD SHA (`git rev-parse HEAD`).
2. Wait for CI to complete on that SHA, then capture the new run IDs (`gh run list --branch <branch> --limit 8`).
3. Update PR body via `gh pr edit` so:
   - Every "Branch state on `<SHA>`" header names the new HEAD.
   - Every CI run ID link in the body matches `gh run list` for the new SHA.
   - The `release-lockstep-gate` row in the umbrella PR body shows current status, not the prior run's status.
4. Update `.agent-workflows/HANDOFF_<latest>.md` so:
   - The current branch / HEAD / tag / PR fields match the new SHA.
   - Last-updated date is today.
   - CI run IDs cited match the new SHA.
   - The verifier output captured matches the post-push state.
5. If the audit punchlist cites SHAs/run IDs as proof of Closed status, decide explicitly whether to update them to the new SHA or leave them as historical proof anchors. Either is defensible. What is NOT defensible: mixing without an explanation.
6. Re-run `python scripts/verify-suite-state.py --remote-only` and verify the output matches what was claimed pre-push.

Your push report cannot honestly say "Artifact-state: pass" until this post-push pass completes.

## The proof-anchor vs release-target distinction

A tracked file cannot self-cite its own commit SHA: adding or amending the file changes the SHA. Verification logs, the audit punchlist, and release notes must distinguish:

- **Proof-anchor SHA** — the SHA whose tree contains the first green-CI-and-cleanroom evidence. Row-level proof citations pin here.
- **Release/tag target** — the final branch or merge commit after Scott confirms release. Tags go here, not at the proof anchor.

Collapsing them produces an infinite-regress loop: every amend-to-cite-the-new-SHA commit moves the SHA.

## Report format

After every push, include this block in your report:

```text
5-lens self-audit:
- Engineering: [pass | findings: ...]
- UX:          [pass | findings: ...]
- Tests:       [pass | findings: ...]
- Docs:        [pass | findings: ...]
- QA:          [pass | findings: ...]
Artifact-state: [pass | findings: ...]
Post-push propagation: [pass | findings: ...]
```

If any lens has findings, fix before push. If after a push Claude (auditor) still finds drift, that is direct evidence this rule isn't sticking; Claude's directive will add a new artifact-state check to this document or a new entry to section 22 of `TOWNLIGHT_AUDIT_PROTOCOL.md`.

## Chat-promise rejection

A chat-side promise ("I will keep this in mind") is not a behavior change. The behavior change is the durable artifact: the artifact-state checklist item in this file, the report block, the section 22 entry in the protocol. When Codex commits to a new discipline, the discipline goes into this file or section 22 of the protocol so it survives compaction.

## Cross-references

- `C:\Users\scott\OneDrive\Desktop\Claude\TOWNLIGHT_AUDIT_PROTOCOL.md` — the verification-side audit protocol (Claude reads this). The mandatory 10-section output shape and the verifier's evidence-pass rules live there. Section 21 ("Implementation-side rule pointer") and section 22 ("Known drift patterns") pair with this document.
- `C:\Users\scott\OneDrive\Desktop\Claude\TOWNLIGHT_AUDIT_GATE.md` — the short mandatory gate Claude reads every turn.
- `~/.codex/skills/project-control-plane/SKILL.md` — Codex's skill that points at this file as the before-every-push discipline.
- `C:\Users\scott\OneDrive\Desktop\Claude\agentic-pipeline\` — the agentic-pipeline plugin. v0.2 governs execution (4-phase module-release). v0.3 governs audit handoff (this document + the protocol + the gate).
