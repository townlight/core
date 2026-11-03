<a id="civiccore-tier-1-retrofit-ledger"></a>

# Townlight Core Tier 1 Retrofit Ledger

Status: CO-3 ledger, live-release scan current as of 2026-05-05.

This ledger covers every public Townlight Core GitHub Release visible during the
CO-3 live scan. It does not rewrite history and does not alter any pre-baseline
release notes, tags, or assets. The correction action taken here is a
repo-controlled ledger plus documentation truth update.

## Rules

- `v0.22.1` is the first Townlight Core Sigstore-attested baseline release.
- `v0.22.0` and earlier releases are retained for historical installs, but are
  not provenance baselines.
- A pre-baseline release may become attested only through a future additive
  attestation operation with explicit per-release or explicit batch
  authorization.
- Downstream modules requiring procurement-grade provenance should pin to
  `v0.22.1` or a later Sigstore-attested release when their compatibility
  matrix permits it.

Structured source of truth:
[`docs/ops/civiccore-tier1-retrofit-ledger.json`](civiccore-tier1-retrofit-ledger.json).

Verification:

```bash
python scripts/check-tier1-ledger.py
python scripts/check-tier1-ledger.py --live
```

The live check requires every historical/pre-baseline release in this ledger to
remain visible. Newer post-baseline releases do not need retroactive CO-3 rows,
but the live check permits them only when the GitHub release exposes both
`release-attestation.json` and `release-attestation.json.bundle`.

## Live Scan Summary

- Repo: `townlight/core`
- Live releases scanned: 25
- Latest release: `v0.22.1`
- Baseline release:
  [`v0.22.1`](https://github.com/CivicSuite/civiccore/releases/tag/v0.22.1)
- Baseline target commit:
  `46c99854adbce6dc8a056ae5215278bb1eba9a19`
- Baseline Sigstore identity:
  `https://github.com/CivicSuite/civiccore/.github/workflows/release.yml@refs/tags/v0.22.1`

## Entries

| Tag | Published | Git ref type | Target commit | Ledger status | Attestation | Rule |
| --- | --- | --- | --- | --- | --- | --- |
| `v0.22.1` | 2026-05-05T16:23:36Z | lightweight tag | `46c99854adbce6dc8a056ae5215278bb1eba9a19` | Attested baseline | Sigstore verified | Use as Townlight Core baseline. |
| `v0.22.0` | 2026-05-03T06:39:51Z | lightweight tag | `483a224aaf2ae08868bd4cd4caf842bfda97db94` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.21.0` | 2026-05-02T17:00:33Z | annotated tag object | `4a1eb718ee9565a9a1911da9eff71a5c9f0b3e3e` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.20.0` | 2026-05-02T15:06:14Z | lightweight tag | `ad66681132c28bf17c48681c82943d153897b099` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.19.0` | 2026-05-02T10:26:56Z | annotated tag object | `7ae2acbe01568b8f1397975286754179f9836a52` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.18.1` | 2026-05-02T06:37:09Z | lightweight tag | `fd068e72767901a9541185fe782071ec2ffddc3b` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.18.0` | 2026-05-02T06:25:30Z | lightweight tag | `0785e34b65470803299273acef8f033570071b41` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.17.0` | 2026-05-01T23:40:12Z | annotated tag object | `e9dca05ad2b45c6b19cf97fb829cb7c8e1946343` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.16.0` | 2026-04-30T05:23:09Z | lightweight tag | `a8d287e40d2c9ded183f0d3e35c6c5fb4d89137c` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.15.0` | 2026-04-30T03:51:46Z | lightweight tag | `27702e2fe3ddb659a224f9c57f86b960da1792a7` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.14.1` | 2026-04-30T03:16:15Z | annotated tag object | `36080f75c372c62e27e0407ec3f6cbb2dbbd4012` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.14.0` | 2026-04-30T02:42:46Z | annotated tag object | `09bfe262f91b897799c49a0c7708feabfa067239` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.13.0` | 2026-04-29T23:45:49Z | annotated tag object | `5657806c9b583a2426b5cd028726fd5fda77963e` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.12.0` | 2026-04-29T22:36:17Z | lightweight tag | `d2f24b28ba05cc0b3c601babf389cea2713c11d0` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.11.0` | 2026-04-29T21:09:30Z | lightweight tag | `b21001b1cebd7de01ac8011d4ec342ab99d9bf86` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.10.0` | 2026-04-29T20:08:51Z | annotated tag object | `8db660e546f002352b3df5f2519bb2a92d3282e7` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.9.0` | 2026-04-29T18:32:51Z | annotated tag object | `8010e9fd9b5ab599f579c257f24f3c1ae3cea3e2` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.8.0` | 2026-04-29T17:48:23Z | annotated tag object | `b7cfaeb9d9490ff0c68aad255df6f69da912d6be` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.7.0` | 2026-04-29T16:43:12Z | annotated tag object | `943da60abd6ef4e906b63eecbf7dcbc8de77550d` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.6.0` | 2026-04-29T16:07:58Z | annotated tag object | `95890075c7886e66c9711e0e8e84517a705e3530` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.5.0` | 2026-04-29T15:23:28Z | lightweight tag | `bcb9b7852ba200302371bec3f425726230c435b3` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.4.0` | 2026-04-29T04:38:47Z | annotated tag object | `fab33a41f1c4c3ef3684dee1069f7069d31ac115` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.3.0` | 2026-04-28T06:28:20Z | lightweight tag | `7b3fbbf79b6c71513fac399658fe47195722b5e5` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.2.0` | 2026-04-25T18:11:21Z | annotated tag object | `a8246ed34405d97be1e20adabd7dc8536e1246eb` | Pre-gate, no attestation | None | Do not promote as baseline. |
| `v0.1.0` | 2026-04-24T23:30:45Z | annotated tag object | `9ac20f0274fbe6fc9730bdc509d5e6d4cedf6231` | Pre-gate, no attestation | None | Do not promote as baseline. |

## Auditor Interpretation

Zero CO-3 historical Townlight Core release tags are intentionally left unledgered.
The pre-baseline entries are explicit no-attestation decisions, not implied
backfills. Later post-baseline releases are governed by their own release
attestation and closeout evidence. If a future sprint publishes additive attestations for any
pre-baseline release, that release must be moved out of
`pre_gate_no_attestation_do_not_promote` in the JSON ledger and verified with
`python scripts/check-tier1-ledger.py --live`.
