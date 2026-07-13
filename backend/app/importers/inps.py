from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

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

INPS_SOURCE_NAME = "INPS - Concorsi e mobilita"
INPS_BASE_URL = "https://www.inps.it"
INPS_LIST_PATH = "/it/it/avvisi-bandi-e-fatturazione/fatturazione-concorsi.html"
INPS_SEARCH_PATH = "/content/scorporati/search/jcr:content.search"
INPS_DETAIL_PATH = "/it/it/avvisi-bandi-e-fatturazione/fatturazione-concorsi/dettaglio"
INPS_PARENT_PATH = "/content/dam/inps-site/it/scorporati/bandi-fatturazione-concorsi"
INPS_MODEL = "bandi-fatturazione-concorsi"
INPS_ARCHIVING_DATE = "1514761200000"


def _ensure_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == INPS_SOURCE_NAME))
    if source:
        return source

    source = Source(
        name=INPS_SOURCE_NAME,
        source_type="public-json-api",
        base_url=f"{INPS_BASE_URL}{INPS_LIST_PATH}",
        organization="INPS",
        import_method="public-json-api",
        refresh_frequency="daily",
        status="active",
        technical_notes="Endpoint JSON pubblico richiamato dalla lista Concorsi e Mobilita.",
    )
    db.add(source)
    db.flush()
    return source


def _hex_encode(value: str) -> str:
    normalized = value.replace("\u2019", " ").replace("'", " ")
    return "".join(f"{ord(char):02x}" for char in normalized)


def _selectors(page: int, term: str) -> str:
    values = [
        INPS_PARENT_PATH,
        str(page),
        str(settings.inps_page_size),
        "dataPubblicazione",
        "DESC",
        INPS_MODEL,
        INPS_ARCHIVING_DATE,
        f"t_{term}",
    ]
    return ".".join(_hex_encode(value) for value in values)


def _fetch_records(client: httpx.Client) -> list[dict[str, Any]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    for term in settings.inps_search_terms:
        for page in range(settings.inps_max_pages):
            response = client.get(f"{INPS_SEARCH_PATH}.{_selectors(page, term)}.json")
            response.raise_for_status()
            payload = response.json()
            records = payload.get("data", {}).get("results", [])
            for record in records:
                external_id = record.get("selectors")
                if external_id:
                    records_by_id[external_id] = record
            if len(records) < settings.inps_page_size:
                break
    return list(records_by_id.values())


def _psychology_match(raw: dict[str, Any]) -> bool:
    text = " ".join(str(value) for value in raw.values() if isinstance(value, str))
    normalized = normalize_text(text)
    area_profile = "aree psicologiche" in normalized and (
        "specialist" in normalized or "profil" in normalized
    )
    return (
        direct_psychology_match(text)
        or "neuropsicolog" in normalized
        or area_profile
    )


def _positions(title: str) -> int | None:
    searchable_title = normalize_text(title.replace(".", "").replace(",", ""))
    match = re.search(r"\b(?:n\s*)?(\d+)\s+(?:unita|posti)\b", searchable_title)
    return int(match.group(1)) if match else None


def _official_url(raw: dict[str, Any]) -> str:
    return f"{INPS_BASE_URL}{INPS_DETAIL_PATH}.{raw['selectors']}.html"


def _payload(db: Session, source: Source, raw: dict[str, Any]) -> dict[str, Any]:
    title = raw["titolo"]
    deadline = parse_date(raw.get("dataScadenza"))
    published_at = parse_date(raw.get("dataPubblicazione"))
    status = infer_status(deadline)
    classification = classify_text(title)
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=title,
        organization="INPS",
        deadline=deadline,
    )
    editorial_status, editorial_notes = editorial_visibility(
        status=status,
        duplicate=duplicate,
    )
    payload: dict[str, Any] = {
        "external_id": raw["selectors"],
        "source_id": source.id,
        "title": title,
        "normalized_title": normalize_text(title),
        "short_description": title[:900],
        "description": title,
        "summary": title[:420],
        "category": classification.category,
        "areas": classification.areas,
        "psychology_relevance": classification.psychology_relevance,
        "relevance_score": classification.relevance_score,
        "organization": "INPS",
        "entity_type": "ente-nazionale",
        "status": status,
        "published_at": published_at,
        "deadline": deadline,
        "last_seen_at": datetime.now(UTC),
        "positions": _positions(title),
        "requirements": classification.requirements,
        "application_mode": "Consultare la scheda ufficiale INPS.",
        "official_url": _official_url(raw),
        "organization_url": f"{INPS_BASE_URL}{INPS_LIST_PATH}",
        "content_hash": content_hash(title, raw.get("dataPubblicazione"), raw.get("dataScadenza")),
        "editorial_status": editorial_status,
        "editorial_notes": editorial_notes,
    }
    payload["search_text"] = build_search_text(
        payload["title"],
        payload["organization"],
        payload["category"],
        payload["areas"],
        payload["requirements"],
    )
    return payload


def run_inps_import(db: Session) -> ImportResult:
    source = _ensure_source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=INPS_BASE_URL,
            timeout=30,
            verify=settings.source_import_verify_tls,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            records = _fetch_records(client)
        for raw in records:
            if not _psychology_match(raw):
                skipped += 1
                continue
            if upsert_opportunity(db, payload=_payload(db, source, raw), attachments=[]):
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
