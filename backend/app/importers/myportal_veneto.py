from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.importers.base import ImportResult
from app.importers.institutional import (
    direct_psychology_match,
    editorial_visibility,
    find_probable_duplicate,
    upsert_opportunity,
)
from app.models import ImportRun, Source
from app.services.classifier import build_search_text, classify_text, normalize_text
from app.services.dates import infer_status, parse_date
from app.services.dedupe import content_hash

MYPORTAL_CONTENT_TYPE = "AT_myp_bandi_concorso"
EXCLUDED_ATTACHMENT_TERMS = (
    "ammess",
    "candidat",
    "commission",
    "esito",
    "graduatoria",
    "tracce",
    "verbale",
)


@dataclass(frozen=True)
class MyPortalTenant:
    source_name: str
    organization: str
    base_url: str
    ipa: str
    page_path: str
    parent: str
    province: str
    municipality: str


TREVISO = MyPortalTenant(
    source_name="Comune di Treviso - Bandi di concorso",
    organization="Comune di Treviso",
    base_url="https://www.comune.treviso.it",
    ipa="C_L407",
    page_path="/amministrazionetrasparente/_05_bandi_di_concorso",
    parent="/AmministrazioneTrasparente/05_Bandi_di_concorso/InAtto",
    province="TV",
    municipality="Treviso",
)


def _ensure_source(db: Session, tenant: MyPortalTenant) -> Source:
    source = db.scalar(select(Source).where(Source.name == tenant.source_name))
    if source:
        return source

    source = Source(
        name=tenant.source_name,
        source_type="public-json-api",
        base_url=f"{tenant.base_url}{tenant.page_path}",
        region="Veneto",
        organization=tenant.organization,
        import_method="myportal-public-json-api",
        refresh_frequency="daily",
        status="active",
        technical_notes="Catalogo JSON pubblico MyPortal di Amministrazione Trasparente.",
    )
    db.add(source)
    db.flush()
    return source


def _fetch_records(client: httpx.Client, tenant: MyPortalTenant) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for page_index in range(1, 51):
        response = client.get(
            f"/myportal/{tenant.ipa}/api/content",
            params={
                "type": MYPORTAL_CONTENT_TYPE,
                "parent": tenant.parent,
                "includeSubFolders": "true",
                "onlyNotHidden": "true",
                "sortBy": "attributes.def_date_scadenza_bando",
                "desc": "true",
                "pageIndex": str(page_index),
            },
        )
        response.raise_for_status()
        page = response.json()["page"]
        entities = list(page.get("entities") or [])
        if not entities:
            break

        new_records = [item for item in entities if str(item["id"]) not in seen_ids]
        if not new_records:
            break
        records.extend(new_records)
        seen_ids.update(str(item["id"]) for item in new_records)

        total = int(page.get("entitiesCount") or 0)
        if total and len(records) >= total:
            break
    return records


def _clean_html(value: str | None) -> str:
    return BeautifulSoup(value or "", "html.parser").get_text(" ", strip=True)


def _positions(title: str) -> int | None:
    match = re.search(r"\bn\.?\s*(\d+)\s+posti?\b", title, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _attachment_refs(
    tenant: MyPortalTenant,
    raw_attachments: list[dict[str, Any]],
) -> list[dict[str, str | None]]:
    attachments: list[dict[str, str | None]] = []
    for record in raw_attachments:
        title = str(record.get("dyn_str_autobind_allegati_name") or "Documento ufficiale")
        if any(term in normalize_text(title) for term in EXCLUDED_ATTACHMENT_TERMS):
            continue
        attachment_id = record.get("dyn_str_association_allegati_uuid")
        if not attachment_id:
            continue
        attachments.append(
            {
                "title": title,
                "url": (
                    f"{tenant.base_url}/myportal/{tenant.ipa}/api/content/download"
                    f"?id={attachment_id}"
                ),
                "file_type": "pdf",
            }
        )
    return attachments[:6]


def _official_url(tenant: MyPortalTenant, attributes: dict[str, Any]) -> str:
    canonical_url = attributes.get("sys_canonical_url")
    return urljoin(tenant.base_url, canonical_url) if canonical_url else (
        f"{tenant.base_url}{tenant.page_path}"
    )


def _payload(
    db: Session,
    source: Source,
    tenant: MyPortalTenant,
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, str | None]]]:
    attributes = raw["attributes"]
    title = str(
        attributes.get("dyn_str_oggetto_bando") or attributes.get("sys_title") or raw["name"]
    )
    notes = _clean_html(attributes.get("myp_noteinizio"))
    deadline = parse_date(attributes.get("def_date_scadenza_bando"))
    status = infer_status(deadline)
    classification = classify_text(title, notes)
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=title,
        organization=tenant.organization,
        deadline=deadline,
    )
    editorial_status, editorial_notes = editorial_visibility(
        status=status,
        duplicate=duplicate,
    )
    description = " - ".join(part for part in [title, notes] if part)
    attachments = _attachment_refs(
        tenant,
        list(attributes.get("mul_association_allegati") or []),
    )
    payload: dict[str, Any] = {
        "external_id": str(raw["id"]),
        "source_id": source.id,
        "title": title,
        "normalized_title": normalize_text(title),
        "short_description": description[:900],
        "description": description,
        "summary": description[:420],
        "category": classification.category,
        "areas": classification.areas,
        "psychology_relevance": classification.psychology_relevance,
        "relevance_score": classification.relevance_score,
        "organization": tenant.organization,
        "entity_type": "comune",
        "region": "Veneto",
        "province": tenant.province,
        "municipality": tenant.municipality,
        "original_location": f"{tenant.municipality}, {tenant.province}, Veneto",
        "status": status,
        "published_at": parse_date(raw.get("firstPublishedAt")),
        "deadline": deadline,
        "last_seen_at": datetime.now(UTC),
        "positions": _positions(title),
        "requirements": classification.requirements,
        "application_mode": f"Consultare la scheda ufficiale di {tenant.organization}.",
        "official_url": _official_url(tenant, attributes),
        "organization_url": f"{tenant.base_url}{tenant.page_path}",
        "content_hash": content_hash(title, notes),
        "editorial_status": editorial_status,
        "editorial_notes": editorial_notes,
    }
    payload["search_text"] = build_search_text(
        payload["title"],
        payload["description"],
        payload["organization"],
        payload["region"],
        payload["province"],
        payload["category"],
        payload["areas"],
        payload["requirements"],
    )
    return payload, attachments


def _run_tenant_import(db: Session, tenant: MyPortalTenant) -> ImportResult:
    source = _ensure_source(db, tenant)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=tenant.base_url,
            timeout=30,
            verify=settings.source_import_verify_tls,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            records = _fetch_records(client, tenant)
        for raw in records:
            attributes = raw["attributes"]
            title = str(
                attributes.get("dyn_str_oggetto_bando") or attributes.get("sys_title") or ""
            )
            if not direct_psychology_match(title):
                skipped += 1
                continue
            payload, attachments = _payload(db, source, tenant, raw)
            if upsert_opportunity(db, payload=payload, attachments=attachments):
                created += 1
            else:
                updated += 1

        source.last_success_at = datetime.now(UTC)
        source.last_error = None
        source.status = "active"
        run.status = "success"
    except Exception as exc:
        source.last_error = str(exc)
        source.status = "error"
        run.status = "failed"
        run.error_message = str(exc)
        raise
    finally:
        run.finished_at = datetime.now(UTC)
        run.created_count = created
        run.updated_count = updated
        run.skipped_count = skipped
        db.commit()

    return ImportResult(
        source_id=source.id,
        created_count=created,
        updated_count=updated,
        skipped_count=skipped,
    )


def run_myportal_treviso_import(db: Session) -> ImportResult:
    return _run_tenant_import(db, TREVISO)
