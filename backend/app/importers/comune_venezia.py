from __future__ import annotations

import re
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

COMUNE_VENEZIA_SOURCE_NAME = "Comune di Venezia - Bandi di concorso"
COMUNE_VENEZIA_BASE_URL = "https://www.comune.venezia.it"
COMUNE_VENEZIA_PATH = "/node/6313"


def _ensure_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == COMUNE_VENEZIA_SOURCE_NAME))
    if source:
        return source

    source = Source(
        name=COMUNE_VENEZIA_SOURCE_NAME,
        source_type="html-table",
        base_url=f"{COMUNE_VENEZIA_BASE_URL}{COMUNE_VENEZIA_PATH}",
        region="Veneto",
        organization="Comune di Venezia",
        import_method="html-table",
        refresh_frequency="daily",
        status="active",
        technical_notes="Tabella HTML pubblica di concorsi, selezioni e mobilita.",
    )
    db.add(source)
    db.flush()
    return source


def _fetch_html(client: httpx.Client) -> str:
    response = client.get(COMUNE_VENEZIA_PATH)
    response.raise_for_status()
    return response.text


def _positions(value: str) -> int | None:
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def _status(section: str, deadline_text: str, deadline: datetime | None) -> str:
    normalized = normalize_text(f"{section} {deadline_text}")
    if any(term in normalized for term in ("in corso", "concluse", "scadut", "esaurit", "revocat")):
        return "closed"
    return infer_status(deadline)


def parse_records(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        return []

    records: list[dict[str, Any]] = []
    section = ""
    for row in table.find_all("tr"):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 3:
            continue

        title_cell = cells[2]
        title = title_cell.get_text(" ", strip=True)
        normalized_title = normalize_text(title)
        if normalized_title.startswith("procedure "):
            section = normalized_title
            continue

        link = title_cell.find("a", href=True)
        code = cells[1].get_text(" ", strip=True)
        if link is None or not code or not title:
            continue

        deadline_text = cells[4].get_text(" ", strip=True) if len(cells) >= 5 else ""
        deadline = parse_date(deadline_text)
        records.append(
            {
                "external_id": code,
                "title": title,
                "positions": _positions(cells[3].get_text(" ", strip=True))
                if len(cells) >= 4
                else None,
                "deadline": deadline,
                "status": _status(section, deadline_text, deadline),
                "official_url": urljoin(COMUNE_VENEZIA_BASE_URL, link["href"]),
            }
        )
    return records


def _payload(db: Session, source: Source, raw: dict[str, Any]) -> dict[str, Any]:
    title = raw["title"]
    status = raw["status"]
    classification = classify_text(title)
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=title,
        organization="Comune di Venezia",
        deadline=raw["deadline"],
    )
    editorial_status, editorial_notes = editorial_visibility(
        status=status,
        duplicate=duplicate,
    )
    description = f"{raw['external_id']} - {title}"
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
        "organization": "Comune di Venezia",
        "entity_type": "comune",
        "region": "Veneto",
        "province": "VE",
        "municipality": "Venezia",
        "original_location": "Venezia, VE, Veneto",
        "status": status,
        "deadline": raw["deadline"],
        "last_seen_at": datetime.now(UTC),
        "positions": raw["positions"],
        "requirements": classification.requirements,
        "application_mode": "Consultare la scheda ufficiale del Comune di Venezia.",
        "official_url": raw["official_url"],
        "organization_url": f"{COMUNE_VENEZIA_BASE_URL}{COMUNE_VENEZIA_PATH}",
        "content_hash": content_hash(title, raw["external_id"]),
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
    return payload


def run_comune_venezia_import(db: Session) -> ImportResult:
    source = _ensure_source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=COMUNE_VENEZIA_BASE_URL,
            timeout=30,
            verify=settings.source_import_verify_tls,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            records = parse_records(_fetch_html(client))
        for raw in records:
            if not direct_psychology_match(raw["title"]):
                skipped += 1
                continue
            payload = _payload(db, source, raw)
            if upsert_opportunity(db, payload=payload, attachments=[]):
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
