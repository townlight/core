from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "tag",
    "published_at",
    "release_url",
    "tag_ref_type",
    "tag_ref_sha",
    "target_commit",
    "release_assets",
    "ledger_status",
    "attestation_status",
    "rationale",
    "downstream_rule",
}

ATTESTATION_ASSETS = {"release-attestation.json", "release-attestation.json.bundle"}


class LedgerError(Exception):
    pass


def load_ledger(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        ledger = json.load(handle)
    if not isinstance(ledger, dict):
        raise LedgerError("ledger root must be a JSON object")
    return ledger


def _entry_tags(entries: list[dict[str, Any]]) -> list[str]:
    return [str(entry.get("tag", "")) for entry in entries]


def validate_ledger(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    if ledger.get("schema_version") != 1:
        raise LedgerError("schema_version must be 1")
    if ledger.get("repo") != "CivicSuite/civiccore":
        raise LedgerError("repo must be CivicSuite/civiccore")
    if ledger.get("baseline_tag") != "v0.22.1":
        raise LedgerError("baseline_tag must be v0.22.1")

    entries = ledger.get("entries")
    if not isinstance(entries, list) or not entries:
        raise LedgerError("entries must be a non-empty list")

    tags = _entry_tags(entries)
    if len(tags) != len(set(tags)):
        raise LedgerError("entries contain duplicate tags")

    release_count = ledger.get("live_release_scan", {}).get("release_count")
    if release_count != len(entries):
        raise LedgerError(
            f"live_release_scan.release_count {release_count!r} does not match "
            f"{len(entries)} ledger entries"
        )

    baseline_entries = [entry for entry in entries if entry.get("tag") == ledger["baseline_tag"]]
    if len(baseline_entries) != 1:
        raise LedgerError("ledger must contain exactly one baseline entry")

    for entry in entries:
        missing = sorted(REQUIRED_FIELDS - set(entry))
        if missing:
            raise LedgerError(f"{entry.get('tag', '<unknown>')} missing fields: {missing}")
        assets = set(entry["release_assets"])
        if entry["ledger_status"] == "attested_baseline":
            if not ATTESTATION_ASSETS.issubset(assets):
                raise LedgerError(f"{entry['tag']} baseline entry lacks attestation assets")
            if entry["attestation_status"] != "sigstore_verified":
                raise LedgerError(f"{entry['tag']} baseline attestation status is not verified")
        elif entry["ledger_status"] == "pre_gate_no_attestation_do_not_promote":
            if ATTESTATION_ASSETS & assets:
                raise LedgerError(f"{entry['tag']} is pre-gate but lists attestation assets")
            if entry["attestation_status"] != "none_pre_gate":
                raise LedgerError(f"{entry['tag']} pre-gate attestation status is not none_pre_gate")
        else:
            raise LedgerError(f"{entry['tag']} has unknown ledger_status {entry['ledger_status']!r}")

    return entries


def fetch_live_releases(repo: str) -> dict[str, set[str]]:
    result = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{repo}/releases",
            "--paginate",
            "--jq",
            '.[] | {tag_name, assets: [.assets[].name]} | @json',
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    releases: dict[str, set[str]] = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        release = json.loads(line)
        releases[str(release["tag_name"])] = {str(asset) for asset in release.get("assets", [])}
    return releases


def validate_live_release_parity(
    entries: list[dict[str, Any]], live_releases: dict[str, set[str]]
) -> list[str]:
    ledger_tags = set(_entry_tags(entries))
    live_tags = set(live_releases)
    missing = sorted(live_tags - ledger_tags)
    stale = sorted(ledger_tags - live_tags)
    unattested_missing = [
        tag for tag in missing if not ATTESTATION_ASSETS.issubset(live_releases[tag])
    ]

    if stale or unattested_missing:
        raise LedgerError(
            f"live release parity failed; missing={unattested_missing or 'none'} "
            f"stale={stale or 'none'}"
        )
    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("docs/ops/civiccore-tier1-retrofit-ledger.json"),
    )
    parser.add_argument("--repo", default="CivicSuite/civiccore")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Compare ledger entries with the live GitHub Releases page via gh.",
    )
    args = parser.parse_args(argv)

    try:
        ledger = load_ledger(args.ledger)
        entries = validate_ledger(ledger)
        post_baseline_attested: list[str] = []
        if args.live:
            live_releases = fetch_live_releases(args.repo)
            post_baseline_attested = validate_live_release_parity(entries, live_releases)
        print(f"PASS: {len(entries)} Townlight Core release tags are ledgered")
        if post_baseline_attested:
            print(
                "PASS: post-baseline attested release tags verified live: "
                + ", ".join(post_baseline_attested)
            )
        return 0
    except (LedgerError, subprocess.CalledProcessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
