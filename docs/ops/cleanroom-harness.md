<a id="civiccore-cleanroom-harness"></a>

# Townlight Core Cleanroom Harness

Status: CO-6 harness, added for outside-auditor reproduction.

The offline smoke compares the installed candidate's package version with the
version declared in that candidate's `pyproject.toml`. A mismatch fails the
smoke. The historical `v0.22.1` release checksum and Sigstore attestation checks
remain separate and continue to verify their original release assets and
workflow identity.

The cleanroom harness proves the Townlight Core release gate and the public
install-and-verify path from a pinned container with no inherited maintainer
state. It provisions Townlight Core from an explicit commit SHA, runs the release
gate, verifies the release-provenance fixtures, verifies the live `v0.22.1`
Sigstore attestation, verifies the `SHA256SUMS.txt` release-asset path, and
then runs an offline smoke with Docker networking disabled.

## Run

From a fresh clone:

```bash
bash scripts/run-civiccore-cleanroom.sh <commit-sha>
```

The host must have Docker and a usable Python interpreter on `PATH`. The
orchestrator probes `python`, `python3`, `python.exe`, and `py -3` by executing
a short Python import before it uses an interpreter for the final manifest
comparison.

The script defaults to two runs so auditors can compare stable manifests:

```bash
CLEANROOM_RUN_COUNT=2 bash scripts/run-civiccore-cleanroom.sh <commit-sha>
```

Evidence is written to:

```text
docs/evidence/co6-civiccore-cleanroom-<commit-prefix>/
```

## Pinned Inputs

- Base image: `python:3.13-slim-bookworm@sha256:bb73517d48bd32016e15eade0c009b2724ec3a025a9975b5cd9b251d0dcadb33`
- Cosign: `v3.0.6`
- Cosign Linux amd64 SHA256:
  `c956e5dfcac53d52bcf058360d579472f0c1d2d9b69f55209e256fe7783f4c74`
- Baseline release under test: `v0.22.1`

## Evidence

Each run directory contains:

- `cleanroom-manifest.json` - stable manifest used for cross-machine
  comparison.
- `cleanroom-manifest.sha256` - SHA256 for the stable manifest.
- `cleanroom-manifest.json.sig` and `evidence-signing-public.pem` - per-run
  OpenSSL signature and verification key for the stable manifest.
- `files.sha256` - hashes for evidence files in the run directory.
- `cleanroom-evidence.tar.gz` and `.sha256` - compressed evidence bundle and
  checksum.
- `logs/` - command logs for each verification path.
- `release-assets/` - downloaded `v0.22.1` release assets used by the live
  verification paths.

`run-metadata.json`, signatures, and compressed bundles are run-specific. The
cross-machine comparison surface is `cleanroom-manifest.json`; two independent
runs pass when those stable manifest hashes match.

## Network Boundary

Network is allowed only for provisioning and verification endpoints:

- `https://github.com/CivicSuite/civiccore.git`
- `https://github.com/CivicSuite/civiccore/releases/download/v0.22.1/*`
- `https://api.github.com/repos/CivicSuite/civiccore/*`
- `https://github.com/sigstore/cosign/releases/download/v3.0.6/cosign-linux-amd64`
- `https://pypi.org/*`
- `https://files.pythonhosted.org/*`
- Sigstore transparency and certificate endpoints used by
  `cosign verify-blob`

After provisioning, the orchestrator runs the offline smoke and offline fixture
verification through `docker run --network none`. Failure of that phase is a
cleanroom failure.
