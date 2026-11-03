# Historical Provenance Disclosure Policy

Status: operative CivicSuite policy, effective 2026-05-05.

Baseline: `civiccore v0.22.1`, released 2026-05-05 at 16:23:36Z, is the
baseline release under the attested provenance model. The live release and trust
artifacts are:

- Release: [`v0.22.1`](https://github.com/CivicSuite/civiccore/releases/tag/v0.22.1)
- Attestation:
  [`release-attestation.json`](https://github.com/CivicSuite/civiccore/releases/download/v0.22.1/release-attestation.json)
- Cosign bundle:
  [`release-attestation.json.bundle`](https://github.com/CivicSuite/civiccore/releases/download/v0.22.1/release-attestation.json.bundle)
- Checksums:
  [`SHA256SUMS.txt`](https://github.com/CivicSuite/civiccore/releases/download/v0.22.1/SHA256SUMS.txt)

## Summary

CivicSuite strengthened its release provenance model during the synthetic
development phase. The prior model relied on GitHub-native release pages and
tag references. A backfill scan found that historical releases were either
lightweight tags or unsigned annotated tag objects. GitHub's release UI can show
a "Verified" badge for the target commit, but that visual signal does not mean
the tag object itself is signed or verified.

The new model treats tags as release pointers and makes a Sigstore-signed
`release-attestation.json` the trust artifact. Releases after the baseline date
must include the attestation, cosign bundle, artifact checksums, evidence bundle
hashes, and an exact per-repo/per-tag verification command.

This model shift was driven by the CivicSuite synthetic-phase adversarial audit
contract. The external auditor flagged that the release-page "Verified" signal
was misleading for release provenance, the development team built a
fixture-driven gate, the gate surfaced an organization-wide historical baseline
issue, and the project chose transparent disclosure and forward correction over
rewriting release history.

## Promotion Evidence

The 2026-05-05 policy promotion is anchored to the following evidence:

- The live `v0.22.1` release attestation URL listed above.
- CivicCore's Tier 1 retrofit ledger:
  [`docs/ops/civiccore-tier1-retrofit-ledger.md`](civiccore-tier1-retrofit-ledger.md)
- The cross-module retrofit closeout report:
  [`docs/ops/co-4-cross-module-retrofit-report.md`](co-4-cross-module-retrofit-report.md)
- Release verification command and result: `bash scripts/verify-release.sh`,
  result `VERIFY-RELEASE: PASSED` on 2026-05-05.
- No historical public release notes, tags, release assets, checksums, or
  attestations were edited. CO-3 and CO-4 used additive current documentation,
  ledgers, QA evidence, and dependency alignment only.

## Historical State

- Historical releases before 2026-05-05 were produced under a weaker
  GitHub-native provenance model.
- The backfill scan covered CivicSuite release tags across the organization as
  of 2026-05-04 and found 119 historical releases failing the strengthened
  gate: 83 lightweight tags and 36 unsigned annotated tag objects.
- Those releases are not retroactively deleted or rewritten.
- Current/latest live-surface releases receive additive attestations only after
  per-release authorization.
- Cities and procurement reviewers should pin to post-baseline releases when
  procurement-grade provenance is required.

## New Baseline

A post-baseline release is independently verifiable when:

- the target commit is GitHub-verified,
- the tag ref points at the attested commit/tree,
- the release assets match `SHA256SUMS.txt`,
- `release-attestation.json` follows schema version 1,
- the attestation is signed by the exact expected GitHub Actions OIDC workflow
  identity for the repo and tag,
- the cosign bundle verifies with the documented issuer and trust roots, and
- release notes include the exact verification command.

Worked example for the first attested Townlight Core baseline release:

```bash
cosign verify-blob release-attestation.json \
  --bundle release-attestation.json.bundle \
  --certificate-identity "https://github.com/CivicSuite/civiccore/.github/workflows/release.yml@refs/tags/v0.22.1" \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

sha256sum -c SHA256SUMS.txt
python scripts/verify-release-provenance.py v0.22.1 \
  --repo CivicSuite/civiccore \
  --attestation release-attestation.json \
  --bundle release-attestation.json.bundle \
  --artifacts-dir .
```

## Canonical Sources

- Live attested baseline release:
  [`v0.22.1`](https://github.com/CivicSuite/civiccore/releases/tag/v0.22.1)
- Gate implementation:
  [`civiccore/release_provenance.py`](../../civiccore/release_provenance.py)
- Thin CLI wrapper:
  [`scripts/verify-release-provenance.py`](../../scripts/verify-release-provenance.py)
- Versioned attestation schema:
  [`docs/ops/release-attestation.schema.json`](release-attestation.schema.json)
- Townlight Core Tier 1 retrofit ledger:
  [`docs/ops/civiccore-tier1-retrofit-ledger.md`](civiccore-tier1-retrofit-ledger.md)
- CO-4 cross-module retrofit report:
  [`docs/ops/co-4-cross-module-retrofit-report.md`](co-4-cross-module-retrofit-report.md)
- Adversarial fixture suite:
  [`tests/fixtures/release_provenance/`](../../tests/fixtures/release_provenance/)
- Release-signing runbook:
  [`docs/ops/release-signing.md`](release-signing.md)

## Verification Support

If a procurement reviewer or city IT reviewer cannot verify a post-baseline
release with the documented commands, report it through
[`SECURITY.md`](../../SECURITY.md). Treat unverifiable provenance as a release
verification failure until the project provides a corrected evidence bundle or
a documented explanation.

## Audit Interpretation

This disclosure does not minimize the prior state. It records a baseline shift:
the project found that its previous release-page verification signal was
insufficient, stopped destructive corrections, adopted a verifiable attestation
model, and preserved historical releases instead of rewriting the record.
