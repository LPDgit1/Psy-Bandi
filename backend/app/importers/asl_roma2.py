from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.importers.base import ImportResult
from app.importers.institutional import (
    PSYCHOLOGY_SEARCH_TERMS,
    direct_psychology_match,
    editorial_visibility,
    find_probable_duplicate,
    upsert_opportunity,
)
from app.models import ImportRun, Source
from app.services.classifier import build_search_text, classify_text, normalize_text
from app.services.dates import infer_status, parse_date
from app.services.dedupe import content_hash

ASL_ROMA2_SOURCE_NAME = "ASL Roma 2 - Concorsi"
ASL_ROMA2_BASE_URL = "https://www.aslroma2.it"
ASL_ROMA2_PATH = "/external/concorsi/index.php"
EXCLUDED_ATTACHMENT_TERMS = (
    "ammess",
    "autodichiarazione",
    "candidat",
    "commission",
    "esito",
    "graduatoria",
)


def _ensure_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == ASL_ROMA2_SOURCE_NAME))
    if source:
        return source

    source = Source(
        name=ASL_ROMA2_SOURCE_NAME,
        source_type="html-table",
        base_url=f"{ASL_ROMA2_BASE_URL}{ASL_ROMA2_PATH}",
        region="Lazio",
        organization="ASL Roma 2",
        import_method="html-table-post-filter",
        refresh_frequency="daily",
        status="active",
        technical_notes="Tabella pubblica con ricerca server-side per parola chiave.",
    )
    db.add(source)
    db.flush()
    return source


def _fetch_records(client: httpx.Client) -> list[dict[str, Any]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    for term in PSYCHOLOGY_SEARCH_TERMS:
        response = client.post(ASL_ROMA2_PATH, data={"NOM": term, "Cerca": "Cerca"})
        response.raise_for_status()
        for record in parse_records(response.text):
            records_by_id[record["external_id"]] = record
    return list(records_by_id.values())


def _attachment_id(url: str) -> str | None:
    values = parse_qs(urlparse(url).query).get("id")
    return values[0] if values else None


def _external_id(title: str, deadline_text: str, attachments: list[dict[str, str | None]]) -> str:
    for attachment in attachments:
        attachment_id = _attachment_id(str(attachment["url"]))
        if attachment_id:
            return attachment_id
    raw = f"{title}|{deadline_text}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _safe_attachments(cell: Any) -> list[dict[str, str | None]]:
    attachments: list[dict[str, str | None]] = []
    for link in cell.find_all("a", href=True):
        title = link.get_text(" ", strip=True) or "Documento ufficiale"
        if any(term in normalize_text(title) for term in EXCLUDED_ATTACHMENT_TERMS):
            continue
        attachments.append(
            {
                "title": title,
                "url": urljoin(f"{ASL_ROMA2_BASE_URL}{ASL_ROMA2_PATH}", link["href"]),
                "file_type": "pdf",
            }
        )
    return attachments


def parse_records(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    for row in soup.find_all("tr", attrs={"onmouseover": True}):
        cells = row.find_all("td", recursive=False)
        if len(cells) != 5:
            continue
        title = cells[1].get_text(" ", strip=True)
        if not title:
            continue
        deadline_text = cells[3].get_text(" ", strip=True)
        attachments = _safe_attachments(cells[2])
        records.append(
            {
                "external_id": _external_id(title, deadline_text, attachments),
                "title": title,
                "published_at": parse_date(cells[0].get_text(" ", strip=True)),
                "deadline": parse_date(deadline_text),
                "source_status": cells[4].get_text(" ", strip=True),
                "attachments": attachments,
            }
        )
    return records


def _official_url(raw: dict[str, Any]) -> str:
    attachments = raw["attachments"]
    preferred = [
        attachment
        for attachment in attachments
        if "bando" in normalize_text(str(attachment["title"]))
    ]
    return str((preferred or attachments)[0]["url"]) if attachments else (
        f"{ASL_ROMA2_BASE_URL}{ASL_ROMA2_PATH}"
    )


def _payload(db: Session, source: Source, raw: dict[str, Any]) -> dict[str, Any]:
    title = raw["title"]
    deadline = raw["deadline"]
    status = infer_status(deadline)
    classification = classify_text(title)
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=title,
        organization="ASL Roma 2",
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
        "short_description": title[:900],
        "description": title,
        "summary": title[:420],
        "category": classification.category,
        "areas": classification.areas,
        "psychology_relevance": classification.psychology_relevance,
        "relevance_score": classification.relevance_score,
        "organization": "ASL Roma 2",
        "entity_type": "azienda-sanitaria",
        "region": "Lazio",
        "province": "RM",
        "municipality": "Roma",
        "original_location": "Roma, RM, Lazio",
        "status": status,
        "published_at": raw["published_at"],
        "deadline": deadline,
        "last_seen_at": datetime.now(UTC),
        "requirements": classification.requirements,
        "application_mode": "Consultare il documento ufficiale ASL Roma 2.",
        "official_url": _official_url(raw),
        "organization_url": f"{ASL_ROMA2_BASE_URL}{ASL_ROMA2_PATH}",
        "content_hash": content_hash(title),
        "editorial_status": editorial_status,
        "editorial_notes": editorial_notes,
    }
    payload["search_text"] = build_search_text(
        payload["title"],
        payload["organization"],
        payload["region"],
        payload["province"],
        payload["category"],
        payload["areas"],
        payload["requirements"],
    )
    return payload


def run_asl_roma2_import(db: Session) -> ImportResult:
    source = _ensure_source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=ASL_ROMA2_BASE_URL,
            timeout=30,
            verify=settings.source_import_verify_tls,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            records = _fetch_records(client)
        for raw in records:
            if not direct_psychology_match(raw["title"]):
                skipped += 1
                continue
            payload = _payload(db, source, raw)
            if upsert_opportunity(db, payload=payload, attachments=raw["attachments"]):
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
