# Claim-bound ingest and media artifacts

`civiccore.tasks.artifacts` is the shared answer to one question: *may this derived file
become durable, and does the job that produced it still own the work?* It is the executable
part of the `C1.jobs` adapter gap ("consumers must enforce claim-bound artifact receipts"),
built on the queue contract in [job-leases.md](job-leases.md). It is **not** a media
subsystem, a transcription service or a second job engine.

## Trust boundary

The only admissible identity of an artifact's producer is the claimed
`LocalTaskEnvelope` a worker already holds. `accept_artifact(session, task, prepared)` copies
`task_id`, `module_id`, `task_type`, `attempt_count` and `claim_token` from it into the
receipt. None of these values has a parameter that a request body, query string, header,
filename, environment variable or model output could set.

Before any receipt is written or any file is published, `require_active_claim` locks the task
row and refuses a cancelled, expired or superseded claim with the queue's existing
`StaleTaskClaim`. The check runs *before* the idempotent shortcut, so a stale worker cannot
treat its own earlier receipt as licence to keep writing.

Attribution is mandatory: `recorded_by` is the job's `audit_subject_id`, or an actor an
already-authorized caller supplies. A blank recorder is refused rather than defaulted.

## Path handling

* A store root must exist and must not itself be a symlink; the adapter keeps its
  `realpath`.
* `resolve_inside_root` refuses absolute paths, UNC/drive/ADS prefixes, `.` and `..`
  components, symlinked components, and any path whose real resolution escapes the root.
* Relative paths are the only form accepted, and they are stored as
  `<module_id>/<kind>/<artifact_id>/<name>`. The stored path is re-checked on every publish,
  verify and idempotent hit, so a later link swap cannot relocate a recorded artifact.
* Names may not contain separators, a colon, control characters, leading/trailing spaces or a
  trailing dot.

## Hashes and publication

The sha256 in the receipt is computed from the bytes written to disk and re-verified after
`os.replace`. A caller-supplied hash is not accepted in either direction; a mismatch is
`artifact-hash-mismatch`, not a warning. The `source_sha256` and `source_label` bind the
derivative to what it came from.

Publication order is: verify claim → insert receipt → re-hash staged bytes → `os.replace`
into the final path → re-hash the final file → commit. Any failure rolls the transaction back
and unlinks both the staged and the final file, so **a durable file is always backed by a
committed, attributed, hash-verified receipt**, and a refused acceptance leaves no partial
artifact. A hard crash in the short window between `os.replace` and `commit` can leave an
unreferenced file; it can never leave a receipt pointing at a missing or different file.

## Supported scope

`SUPPORTED_ARTIFACT_KINDS = {text, chunks-json, media-metadata}`, capped at
`MAX_ARTIFACT_BYTES` (8 MiB).

This adapter performs no transcription, OCR, transcoding, embedding, provider call or native
media execution, and it claims none. Large originals are the handler's own storage receipt.

## Verified behaviour

Unit tests (`tests/test_job_artifacts.py`, 33 passed, 1 skipped — the skip is the Windows
symlink-privilege case) cover identity binding, every refusal reason, traversal and absolute
path refusal, idempotency, name conflict, staging cleanup and tamper detection.

Real PostgreSQL acceptance (`work/beta-foundations/core-job-adapters-01/harness.py`, 9/9
checks, 0 skips, head `civiccore_0009_job_artifacts`): a claimed synthetic job publishes
three derived artifacts (chunked text, chunks JSON, and metadata measured from a
stdlib-generated 0.25 s WAV), bound to the job identity, claim token, recorder and source
hashes. Expired-lease, superseded-token, cancelled and unattributed acceptances are refused
with no durable file. Traversal, absolute, drive-qualified, unsupported-kind, unbound-source
and unsafe-name proposals are refused without reaching a file outside the store. Three
concurrent acceptances of one artifact name produce one receipt and one file. PostgreSQL
triggers refuse UPDATE/DELETE of a receipt and CHECK constraints refuse malformed hashes,
unsupported kinds and an unattributed recorder. Receipts and files survive a cluster restart.

## What this does not do

No Core HTTP/CLI surface for artifact listing; no consumer wiring in Meetings, Records,
Inspections, Planning or Station; no large-original or object storage; no retention or
redaction workflow over accepted artifacts; no per-city commissioning of store roots; no
installed-city, legal, packaging or release acceptance. CivicCast/Station remain separate
products and are not imported here.
