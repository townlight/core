# SPDX-License-Identifier: AGPL-3.0-only
"""Shared, transaction-owned municipal systems catalog.

The application authenticates the caller and owns commit/rollback. This library
never discovers endpoints, connects to a vendor, or claims a connector is installed.
"""

from __future__ import annotations
import hashlib
import json
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SystemInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    vendor_name: str = Field(min_length=1, max_length=200)
    access_protocol: str = Field(min_length=1, max_length=50)
    data_shape: str = Field(min_length=1, max_length=50)
    common_record_types: list[str] = Field(max_length=100)
    redaction_tier: int = Field(ge=1, le=3)
    discovery_hints: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def bound_hints(self):
        if len(json.dumps(self.discovery_hints)) > 16000:
            raise ValueError("Discovery hints exceed the catalog limit")
        if set(self.discovery_hints) - {"ports", "db_patterns", "service_accounts"}:
            raise ValueError(
                "Discovery hints cannot contain connection credentials or arbitrary fields"
            )
        if any(not value.strip() or len(value) > 200 for value in self.common_record_types):
            raise ValueError("Invalid record type")
        return self


class DomainInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    domain: str = Field(min_length=1, max_length=100)
    systems: list[SystemInput] = Field(max_length=500)


class CatalogInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    catalog_version: str = Field(min_length=1, max_length=20)
    domains: list[DomainInput] = Field(max_length=100)

    @model_validator(mode="after")
    def unique_entries(self):
        keys = set()
        names = set()
        count = 0
        for domain in self.domains:
            if domain.domain in names:
                raise ValueError("Duplicate domain")
            names.add(domain.domain)
            for system in domain.systems:
                key = (domain.domain, system.vendor_name, system.access_protocol)
                if key in keys:
                    raise ValueError("Duplicate catalog system")
                keys.add(key)
                count += 1
        if count > 10000:
            raise ValueError("Catalog is too large")
        return self


def normalized_rows(bundle: CatalogInput):
    return sorted(
        [
            {"domain": domain.domain, **system.model_dump()}
            for domain in bundle.domains
            for system in domain.systems
        ],
        key=lambda r: (r["domain"], r["vendor_name"], r["access_protocol"]),
    )


def fingerprint(rows):
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


async def import_catalog(session: AsyncSession, value: dict, *, actor_id: str) -> int:
    """Atomically import a complete immutable version, or verify an exact repeat.

    Existing pre-extraction data is adopted only when the complete row set matches.
    Changed or partial versions are never silently accepted, replaced or deleted.
    """
    if not actor_id.strip() or len(actor_id) > 128:
        raise ValueError("Attributed catalog import required")
    bundle = CatalogInput.model_validate(value)
    rows = normalized_rows(bundle)
    digest = fingerprint(rows)
    await session.execute(text("SELECT pg_advisory_xact_lock(1953721801)"))
    prior = (
        (
            await session.execute(
                text("SELECT source_sha256 FROM civiccore_catalog_imports WHERE version=:version"),
                {"version": bundle.catalog_version},
            )
        )
        .mappings()
        .first()
    )
    existing = (
        (
            await session.execute(
                text(
                    "SELECT domain,vendor_name,access_protocol,data_shape,common_record_types,redaction_tier,discovery_hints FROM system_catalog WHERE catalog_version=:version ORDER BY domain,vendor_name,access_protocol"
                ),
                {"version": bundle.catalog_version},
            )
        )
        .mappings()
        .all()
    )
    actual = [{**dict(row), "discovery_hints": row["discovery_hints"] or {}} for row in existing]
    if prior and (prior["source_sha256"] != digest or fingerprint(actual) != digest):
        raise ValueError("Catalog version differs or is incomplete; use a new reviewed version")
    if prior:
        return 0
    if existing and fingerprint(actual) != digest:
        raise ValueError("Existing catalog version differs or is incomplete; no data overwritten")
    if not existing:
        for row in rows:
            await session.execute(
                text(
                    "INSERT INTO system_catalog (domain,function,vendor_name,access_protocol,data_shape,common_record_types,redaction_tier,discovery_hints,catalog_version) VALUES (:domain,:domain,:vendor_name,:access_protocol,:data_shape,CAST(:common_record_types AS jsonb),:redaction_tier,CAST(:discovery_hints AS jsonb),:version)"
                ),
                {
                    **row,
                    "common_record_types": json.dumps(row["common_record_types"]),
                    "discovery_hints": json.dumps(row["discovery_hints"]),
                    "version": bundle.catalog_version,
                },
            )
    await session.execute(
        text(
            "INSERT INTO civiccore_catalog_imports (version,source_sha256,entry_count,actor_id) VALUES (:version,:digest,:count,:actor)"
        ),
        {
            "version": bundle.catalog_version,
            "digest": digest,
            "count": len(rows),
            "actor": actor_id,
        },
    )
    return len(rows) if not existing else 0


async def domains(session: AsyncSession) -> list[str]:
    return list(
        (
            await session.execute(
                text("SELECT DISTINCT domain FROM system_catalog ORDER BY domain")
            )
        ).scalars()
    )


async def system_catalog(session: AsyncSession, domain: str | None = None) -> list[dict]:
    # Preserve the existing Records projection and history semantics during extraction.
    query = "SELECT id,domain,vendor_name,access_protocol,data_shape,common_record_types,redaction_tier FROM system_catalog"
    if domain is not None:
        query += " WHERE domain=:domain"
    query += " ORDER BY domain,vendor_name,id"
    return [
        dict(row) for row in (await session.execute(text(query), {"domain": domain})).mappings()
    ]


async def connectors_for(session: AsyncSession, domain: str) -> list[dict]:
    rows = await session.execute(
        text(
            "SELECT DISTINCT t.id,t.vendor_name,t.protocol,t.auth_method,t.setup_instructions,t.catalog_version FROM connector_templates t JOIN system_catalog s ON s.vendor_name=t.vendor_name WHERE s.domain=:domain ORDER BY t.vendor_name,t.id"
        ),
        {"domain": domain},
    )
    return [
        {**dict(row), "availability": "template-only; deployment not verified"}
        for row in rows.mappings()
    ]


__all__ = ["CatalogInput", "import_catalog", "domains", "system_catalog", "connectors_for"]
