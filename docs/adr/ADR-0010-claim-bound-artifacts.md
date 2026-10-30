# ADR-0010: Claim-bound acceptance of ingest and media artifacts

Status: Implemented in the private beta candidate (`civiccore.tasks.artifacts`,
migration `civiccore_0009_job_artifacts`); Accepted; not released.
Supersedes nothing. Extends the queue contract recorded in [job-leases.md](../job-leases.md)
and the `C1.jobs` clause.

## Context

`C1.jobs` already ships a fenced queue: `civiccore_local_tasks` with `claim_token`,
`lease_expires_at`, attributed cancellation and heartbeat renewal through
`civiccore.platform.task_queue` and `civiccore.tasks.leased.run_leased_task`. Its documented
gap was that consumers still had to enforce *claim-bound artifact/effect receipts*
themselves. Without a shared contract, each ingest/media adapter would invent its own
version of "did the worker that produced this file still own the job?", and a superseded or
cancelled worker could publish a derivative that the new owner does not know about.

The shipped ingest pipeline (`civiccore.ingest.pipeline`) writes `documents` rows and
derivatives, but it has no job identity at all: it cannot say which claim produced a
document, and its `ingest_bytes` path deletes its temporary file after the session commit
without an acceptance receipt.

## Decision

Add one small adapter, `civiccore.tasks.artifacts`, plus one additive migration
`civiccore_0009_job_artifacts` (`civiccore_job_artifacts`). It is an adapter, not a job
engine and not a media subsystem.

1. **Identity comes from the claimed envelope.** `accept_artifact(session, task, prepared)`
   takes the `LocalTaskEnvelope` a worker already holds and copies `task_id`, `module_id`,
   `task_type`, `attempt_count` and `claim_token` into the receipt. None of these values can
   be supplied by a request body, a filename, an environment variable or a model output.
2. **The claim must still be live at the moment of the authoritative write.** A new
   read-only `civiccore.platform.task_queue.require_active_claim` locks the task row
   (`SELECT ... FOR UPDATE`) and raises the existing `StaleTaskClaim` for a cancelled,
   expired or superseded claim. The adapter calls it *before* the idempotent shortcut, so a
   stale worker cannot read its own earlier receipt as a success signal.
3. **Publication is all-or-nothing with the receipt.** Order: verify claim → insert receipt
   → verify the staged bytes again → `os.replace` into the final path → re-hash the final
   file → commit. Any failure rolls back and unlinks both staged and final files. A durable
   file is therefore always backed by a committed, attributed receipt. A hard crash in the
   short window between `os.replace` and `commit` can leave an unreferenced file; it can
   never leave a receipt pointing at a missing or different file.
4. **Paths stay inside a configured root.** `ArtifactStore.open(root)` refuses a symlinked
   or missing root and stores the realpath-resolved path. `resolve_inside_root` refuses absolute
   paths, UNC/drive/ADS prefixes, `.`/`..` components, symlinked components and anything
   whose real path escapes the root. Re-raising the check on every publish, verify and
   idempotent hit means a later link swap cannot move a recorded artifact out of the root.
5. **Hashes are computed, never trusted.** The sha256 recorded is computed from the bytes
   written to disk and re-verified after `os.replace`. A caller-declared hash is not part of
   the API in either direction.
6. **Every artifact is attributed and source-bound.** `recorded_by` is the job's
   `audit_subject_id` or an explicitly supplied actor; a blank one is refused. Each receipt
   carries the source `sha256` and a source label, so a derivative cannot be recorded as
   floating free of what it came from.
7. **Receipts are append-only.** PostgreSQL triggers refuse UPDATE and DELETE, and CHECK
   constraints refuse a malformed hash, an unsupported kind and an unattributed recorder.
   Downgrade is a no-op: recovery is restore-from-backup, because the record of which owner
   produced which bytes is not something a later writer may rewrite.

## Supported scope (deliberately narrow)

`SUPPORTED_ARTIFACT_KINDS` is `text`, `chunks-json` and `media-metadata`, capped at
`MAX_ARTIFACT_BYTES` (8 MiB). These are the derivative shapes a synthetic or real ingest /
media step can produce without Core owning storage of large originals.

This adapter performs **no** transcription, OCR, transcoding, embedding, provider call or
native media execution, and it claims none. A handler owns its native subprocess
containment and its own large-original storage receipt; this adapter only refuses to make an
unowned or unverified file durable. CivicCast/Station remain separate products and are not
imported here.

## Consequences

* A consumer can now answer "which claimed job produced this file, from which source, under
  which owner, and is it still the bytes we recorded?" from one table plus the file hash.
* A cancelled, expired or superseded worker cannot add a derivative even if its handler had
  already computed one; the staged file is discarded.
* The idempotent path costs one row lock per re-acceptance. That is the intended trade: the
  fence is checked before the shortcut.
* The queue can still not promise exactly-once semantics for effects outside the
  transaction (a remote system, a native recorder). This remains a fenced receipt contract.

## What this does not close

No Core HTTP/CLI surface for artifact listing; no consumer wiring in Meetings, Records,
Inspections, Planning or Station; no large-original or object storage; no retention/redaction
workflow over accepted artifacts; no per-city commissioning of store roots; no installed-city,
legal, packaging or release acceptance. The pre-existing wheel/sdist under
`outputs/beta-plan/core-dist/` predate this source and were not rebuilt.

## Verification

* `tests/test_job_artifacts.py`: 33 passed, 1 skipped (the skip is the Windows symlink
  privilege case, reported by name). Identity binding, all refusal reasons, traversal and
  drive/absolute path refusal, idempotency, name conflict, staging cleanup, tamper detection.
* Real disposable PostgreSQL (own cluster, single start/test/stop):
  `work/beta-foundations/core-job-adapters-01/harness.py`, **9/9 checks, 0 skips**, head
  `civiccore_0009_job_artifacts`. A synthetic source is chunked and a stdlib-generated
  0.25 s WAV is measured; three artifacts are published, hash-verified and bound to the
  producing job. Expired-lease, superseded-token, cancelled and unattributed acceptances are
  refused with no durable file; traversal/absolute/drive/unsupported/unbound/unsafe-name
  proposals are refused; three concurrent acceptances of one name yield one receipt and one
  file; database triggers and CHECK constraints refuse rewriting or forging a receipt; and
  receipts plus files survive a cluster restart.
