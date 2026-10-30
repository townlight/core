# SPDX-License-Identifier: AGPL-3.0-only
"""Command-line entry point for generating one Townlight module project.

``python -m civiccore.scaffold generate ...`` writes a complete module skeleton
(manifest, package, staff app, own migrations, contract tests, docs). It never
overwrites, never installs, never runs a network call, and never emits a
credential: the generated app fails closed until the operator sets its token map.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from civiccore.scaffold.project import (
    ProjectPlan,
    generate_module_project,
    plan_module_project,
)
from civiccore.scaffold.spec import (
    ModuleSpec,
    ScaffoldError,
    ScaffoldOptions,
)

EXIT_OK = 0
EXIT_REFUSED = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m civiccore.scaffold",
        description="Generate one Townlight module project (no install, no network).",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    generate = subcommands.add_parser("generate", help="Create a module project skeleton.")
    generate.add_argument("module_id", help="Lower-case module id, e.g. civicnotes.")
    generate.add_argument("--name", required=True, help="Human-readable module name.")
    generate.add_argument("--description", required=True, help="One-line module description.")
    generate.add_argument("--version", default="0.1.0", help="Module version (PEP 440).")
    generate.add_argument(
        "--civiccore-min-version",
        default="1.3.0.dev1",
        help="Minimum CivicCore version the module declares.",
    )
    generate.add_argument("--permission-key", default=None, help="Permission key (slug).")
    generate.add_argument(
        "--staff-role",
        action="append",
        default=None,
        help="Staff role admitted by the module route (repeatable).",
    )
    generate.add_argument("--route-path", default=None, help="Staff route prefix, e.g. /notes.")
    generate.add_argument(
        "--target",
        default=".",
        help="Existing parent directory in which to create the project directory.",
    )
    generate.add_argument(
        "--dry-run", action="store_true", help="Print the plan; write nothing."
    )

    plan = subcommands.add_parser("plan", help="Print the file plan as JSON; write nothing.")
    plan.add_argument("module_id")
    plan.add_argument("--name", required=True)
    plan.add_argument("--description", required=True)
    plan.add_argument("--version", default="0.1.0")
    plan.add_argument("--civiccore-min-version", default="1.3.0.dev1")
    plan.add_argument("--permission-key", default=None)
    plan.add_argument("--staff-role", action="append", default=None)
    plan.add_argument("--route-path", default=None)
    return parser


def _spec_from_args(args: argparse.Namespace) -> ModuleSpec:
    payload: dict[str, object] = {
        "module_id": args.module_id,
        "name": args.name,
        "description": args.description,
        "version": args.version,
        "civiccore_min_version": args.civiccore_min_version,
    }
    if args.permission_key:
        payload["permission_key"] = args.permission_key
    if args.staff_role:
        payload["staff_roles"] = tuple(args.staff_role)
    if args.route_path:
        payload["route_path"] = args.route_path
    return ModuleSpec.model_validate(payload)


def _plan_payload(plan: ProjectPlan) -> dict[str, object]:
    spec = plan.spec
    return {
        "module_id": spec.module_id,
        "package_name": spec.package_name,
        "project_root": plan.project_root_name,
        "permission": spec.permission,
        "route": spec.route,
        "token_roles_env_var": spec.token_roles_env_var,
        "baseline_revision": spec.baseline_revision,
        "files": [
            {"path": item.relative_path, "bytes": item.size_bytes} for item in plan.files
        ],
    }


def _print_refusal(message: str) -> None:
    print(f"refused: {message}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        spec = _spec_from_args(args)
    except ValidationError as exc:
        _print_refusal("invalid module specification: " + "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ))
        return EXIT_REFUSED
    except ScaffoldError as exc:
        _print_refusal(str(exc))
        return EXIT_REFUSED

    if args.command == "plan":
        print(json.dumps(_plan_payload(plan_module_project(spec)), indent=2))
        return EXIT_OK

    try:
        result = generate_module_project(
            spec,
            Path(args.target),
            options=ScaffoldOptions(dry_run=bool(args.dry_run)),
        )
    except ScaffoldError as exc:
        _print_refusal(str(exc))
        return EXIT_REFUSED

    payload = {
        "project_root": str(result.project_root),
        "dry_run": result.dry_run,
        "created": list(result.created),
    }
    print(json.dumps(payload, indent=2))
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - exercised through subprocess smoke
    raise SystemExit(main())
