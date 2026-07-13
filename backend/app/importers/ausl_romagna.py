from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
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

AUSL_ROMAGNA_SOURCE_NAME = "AUSL Romagna - Bandi di concorso e avvisi"
AUSL_ROMAGNA_BASE_URL = "https://www.auslromagna.it"
AUSL_ROMAGNA_HUB_PATH = (
    "/pubblicita-legale/selezioni-del-personale/concorsi-selezioni-romagna"
)
AUSL_ROMAGNA_CATEGORY_PATHS = (
    "concorsi-pubblici-assunzioni-tempo-indeterminato",
    "avvisi-pubblici-assunzioni-tempo-determinato",
    "avvisi-pubblici-incarichi-ex-art-15-septies-art-15-octies",
    "incarichi-per-struttura-complessa",
    "avvisi-per-mobilita-in-entrata",
    "incarichi-lavoro-autonomo",
    "borse-di-studio",
)
ESSENTIAL_ATTACHMENT_TERMS = (
    "avviso",
    "bando",
    "curriculum",
    "domanda",
    "istruzion",
    "modello",
)


def _ensure_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == AUSL_ROMAGNA_SOURCE_NAME))
    if source:
        return source

    source = Source(
        name=AUSL_ROMAGNA_SOURCE_NAME,
        source_type="public-json-api",
        base_url=f"{AUSL_ROMAGNA_BASE_URL}{AUSL_ROMAGNA_HUB_PATH}",
        region="Emilia-Romagna",
        organization="AUSL Romagna",
        import_method="public-json-api-recent-pages",
        refresh_frequency="daily",
        status="active",
        technical_notes=(
            "Adapter sui feed JSON pubblici Plone delle selezioni. Scansiona "
            "solo pagine recenti e apre i dettagli dei profili psicologici espliciti."
        ),
    )
    db.add(source)
    db.flush()
    return source


def _positions(title: str) -> int | None:
    searchable_title = title.replace(".", "").replace(",", "")
    match = re.search(
        r"\bn\s*(\d+)\s+(?:post[oi]|incarich[io]|unita|bors[ae])\b",
        searchable_title,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def _external_id(detail_url: str) -> str:
    return hashlib.sha256(detail_url.encode()).hexdigest()[:24]


def _api_detail_url(detail_url: str) -> str:
    return f"/++api++{urlparse(detail_url).path}"


def parse_listing(data: dict[str, Any], source_category: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for item in data.get("items", []):
        detail_url = str(item.get("@id", ""))
        title = str(item.get("title", "")).strip()
        if not detail_url or not title:
            continue
        records.append(
            {
                "external_id": _external_id(detail_url),
                "title": title,
                "description": str(item.get("description", "")).strip(),
                "detail_url": detail_url,
                "source_category": source_category,
            }
        )
    return records


def _draft_text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(filter(None, (_draft_text(item) for item in value)))
    if not isinstance(value, dict):
        return ""
    if isinstance(value.get("blocks"), list):
        return " ".join(
            str(block.get("text", "")).strip()
            for block in value["blocks"]
            if isinstance(block, dict) and block.get("text")
        )
    return " ".join(filter(None, (_draft_text(item) for item in value.values())))


def _attachment_file_type(item: dict[str, Any]) -> str | None:
    content_type = str(item.get("content-type", "")).lower()
    if content_type == "application/pdf":
        return "pdf"
    if "wordprocessingml" in content_type:
        return "docx"
    if content_type == "application/msword":
        return "doc"
    return None


def _safe_attachments(data: dict[str, Any]) -> list[dict[str, str | None]]:
    attachments: list[dict[str, str | None]] = []
    for group in data.get("approfondimento") or []:
        if normalize_text(str(group.get("title", ""))) != "documenti":
            continue
        for item in group.get("children") or []:
            title = str(item.get("title", "")).strip() or "Documento ufficiale"
            url = str(item.get("url", "")).strip()
            if not url or not any(
                term in normalize_text(title) for term in ESSENTIAL_ATTACHMENT_TERMS
            ):
                continue
            attachments.append(
                {
                    "title": title,
                    "url": url,
                    "file_type": _attachment_file_type(item),
                }
            )
    return attachments[:6]


def parse_detail(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "external_id": str(data.get("UID", "")).strip()
        or _external_id(str(data.get("@id", ""))),
        "title": str(data.get("title", "")).strip(),
        "description": _draft_text(data.get("text"))
        or str(data.get("description", "")).strip(),
        "detail_url": str(data.get("@id", "")).strip(),
        "published_at": parse_date(data.get("effective")),
        "deadline": parse_date(data.get("scadenza_bando")),
        "attachments": _safe_attachments(data),
    }


def _fetch_records(client: httpx.Client) -> list[dict[str, Any]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    for category_path in AUSL_ROMAGNA_CATEGORY_PATHS:
        next_url: str | None = (
            f"/++api++{AUSL_ROMAGNA_HUB_PATH}/{category_path}/feed"
        )
        for _ in range(settings.ausl_romagna_max_pages):
            if next_url is None:
                break
            response = client.get(next_url, params={"expand": "subsite"})
            response.raise_for_status()
            data = response.json()
            for record in parse_listing(data, category_path):
                records_by_id[record["external_id"]] = record
            next_url = data.get("batching", {}).get("next")

    for record in records_by_id.values():
        if not direct_psychology_match(record["title"], record["description"]):
            continue
        response = client.get(_api_detail_url(record["detail_url"]))
        response.raise_for_status()
        record.update(parse_detail(response.json()))
    return list(records_by_id.values())


def _payload(db: Session, source: Source, raw: dict[str, Any]) -> dict[str, Any]:
    title = raw["title"]
    description = raw.get("description") or title
    deadline = raw.get("deadline")
    status = infer_status(deadline)
    classification = classify_text(title, description, raw["source_category"])
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=title,
        organization="AUSL Romagna",
        deadline=deadline,
    )
    editorial_status, editorial_notes = editorial_visibility(
        status=status,
        duplicate=duplicate,
    )
    payload: dict[str, Any] = {
        "external_id": raw["external_id"],
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
        "organization": "AUSL Romagna",
        "entity_type": "azienda-sanitaria",
        "region": "Emilia-Romagna",
        "original_location": "Romagna",
        "status": status,
        "published_at": raw.get("published_at"),
        "deadline": deadline,
        "last_seen_at": datetime.now(UTC),
        "positions": _positions(title),
        "requirements": classification.requirements,
        "application_mode": "Consultare la scheda ufficiale AUSL Romagna.",
        "official_url": raw["detail_url"],
        "organization_url": f"{AUSL_ROMAGNA_BASE_URL}{AUSL_ROMAGNA_HUB_PATH}",
        "content_hash": content_hash(title, description, raw["source_category"]),
        "editorial_status": editorial_status,
        "editorial_notes": editorial_notes,
    }
    payload["search_text"] = build_search_text(
        payload["title"],
        payload["description"],
        payload["organization"],
        payload["region"],
        payload["category"],
        payload["areas"],
        payload["requirements"],
    )
    return payload


def run_ausl_romagna_import(db: Session) -> ImportResult:
    source = _ensure_source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=AUSL_ROMAGNA_BASE_URL,
            timeout=30,
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            records = _fetch_records(client)
        for raw in records:
            if not direct_psychology_match(raw["title"], raw["description"]):
                skipped += 1
                continue
            if upsert_opportunity(
                db,
                payload=_payload(db, source, raw),
                attachments=raw.get("attachments", []),
            ):
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
