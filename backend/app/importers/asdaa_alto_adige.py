from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

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
from app.services.dedupe import content_hash

ASDAA_SOURCE_NAME = "ASDAA Alto Adige - Bandi di concorso"
ASDAA_BASE_URL = "https://home.asdaa.it"
ASDAA_LIST_PATH = "/it/amministrazione-trasparente/info-concorsi.asp"


def _ensure_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == ASDAA_SOURCE_NAME))
    if source:
        return source

    source = Source(
        name=ASDAA_SOURCE_NAME,
        source_type="html-table",
        base_url=f"{ASDAA_BASE_URL}{ASDAA_LIST_PATH}",
        region="Trentino-Alto Adige",
        organization="Azienda Sanitaria dell'Alto Adige",
        import_method="html-table-metadata-only",
        refresh_frequency="daily",
        status="active",
        technical_notes=(
            "Adapter sulla tabella pubblica consentita da robots.txt. "
            "Non visita e non ripubblica i documenti dell'area /cv/ esclusa."
        ),
    )
    db.add(source)
    db.flush()
    return source


def _external_id(title: str) -> str:
    return hashlib.sha256(normalize_text(title).encode()).hexdigest()[:24]


def parse_records(html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, str]] = []
    for row in soup.select("table tbody tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        title = cells[0].get_text(" ", strip=True)
        situation = cells[1].get_text(" ", strip=True)
        if not title:
            continue
        records.append(
            {
                "external_id": _external_id(title),
                "title": title,
                "description": situation or title,
            }
        )
    return records


def _payload(db: Session, source: Source, raw: dict[str, str]) -> dict[str, Any]:
    title = raw["title"]
    description = raw["description"]
    status = "review"
    classification = classify_text(title, description)
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=title,
        organization="Azienda Sanitaria dell'Alto Adige",
        deadline=None,
    )
    editorial_status, editorial_notes = editorial_visibility(
        status=status,
        duplicate=duplicate,
    )
    official_url = f"{ASDAA_BASE_URL}{ASDAA_LIST_PATH}"
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
        "organization": "Azienda Sanitaria dell'Alto Adige",
        "entity_type": "azienda-sanitaria",
        "region": "Trentino-Alto Adige",
        "original_location": "Alto Adige",
        "status": status,
        "last_seen_at": datetime.now(UTC),
        "requirements": classification.requirements,
        "application_mode": "Consultare l'elenco ufficiale ASDAA.",
        "official_url": official_url,
        "organization_url": official_url,
        "content_hash": content_hash(title, description, official_url),
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


def run_asdaa_alto_adige_import(db: Session) -> ImportResult:
    source = _ensure_source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=ASDAA_BASE_URL,
            timeout=30,
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            response = client.get(ASDAA_LIST_PATH)
            response.raise_for_status()
        for raw in parse_records(response.text):
            if not direct_psychology_match(raw["title"]):
                skipped += 1
                continue
            if upsert_opportunity(
                db,
                payload=_payload(db, source, raw),
                attachments=[],
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
