from __future__ import annotations

import re
import ssl
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

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

INAIL_SOURCE_NAME = "INAIL - Avvisi"
INAIL_BASE_URL = "https://www.inail.it"
INAIL_LIST_PATH = "/portale/it/inail-comunica/avvisi.html"


def build_inail_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers("AES256-GCM-SHA384")
    return context


def _ensure_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == INAIL_SOURCE_NAME))
    if source:
        return source

    source = Source(
        name=INAIL_SOURCE_NAME,
        source_type="html-archive",
        base_url=f"{INAIL_BASE_URL}{INAIL_LIST_PATH}",
        organization="INAIL",
        import_method="html-archive-recent-pages",
        refresh_frequency="daily",
        status="active",
        technical_notes="Archivio pubblico generale: scansione limitata alle pagine recenti.",
    )
    db.add(source)
    db.flush()
    return source


def _external_id(official_url: str) -> str:
    return urlparse(official_url).path.rsplit("/", 1)[-1].removesuffix(".html")


def parse_records(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    for card in soup.select("section.listCardPadre .card"):
        link = card.select_one(".card-title a[href]")
        if link is None:
            continue
        title = link.get_text(" ", strip=True)
        official_url = str(link["href"])
        summary_node = card.select_one(".card-text")
        summary = summary_node.get_text(" ", strip=True) if summary_node else ""
        label = str(link.get("aria-label") or "")
        published_match = re.search(r"pubblicato il\s+(.+)$", label, flags=re.IGNORECASE)
        records.append(
            {
                "external_id": _external_id(official_url),
                "title": title,
                "summary": summary,
                "published_at": parse_date(published_match.group(1))
                if published_match
                else None,
                "deadline": parse_date(summary),
                "official_url": official_url,
            }
        )
    return records


def _fetch_records(client: httpx.Client) -> list[dict[str, Any]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    for page in range(1, settings.inail_max_pages + 1):
        response = client.get(INAIL_LIST_PATH, params={"page": page})
        response.raise_for_status()
        for record in parse_records(response.text):
            records_by_id[record["external_id"]] = record
    return list(records_by_id.values())


def _payload(db: Session, source: Source, raw: dict[str, Any]) -> dict[str, Any]:
    title = raw["title"]
    summary = raw["summary"]
    deadline = raw["deadline"]
    status = infer_status(deadline)
    classification = classify_text(title, summary)
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=title,
        organization="INAIL",
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
        "short_description": summary[:900],
        "description": summary,
        "summary": summary[:420],
        "category": classification.category,
        "areas": classification.areas,
        "psychology_relevance": classification.psychology_relevance,
        "relevance_score": classification.relevance_score,
        "organization": "INAIL",
        "entity_type": "ente-nazionale",
        "status": status,
        "published_at": raw["published_at"],
        "deadline": deadline,
        "last_seen_at": datetime.now(UTC),
        "requirements": classification.requirements,
        "application_mode": "Consultare la scheda ufficiale INAIL.",
        "official_url": raw["official_url"],
        "organization_url": f"{INAIL_BASE_URL}{INAIL_LIST_PATH}",
        "content_hash": content_hash(title, summary),
        "editorial_status": editorial_status,
        "editorial_notes": editorial_notes,
    }
    payload["search_text"] = build_search_text(
        payload["title"],
        payload["description"],
        payload["organization"],
        payload["category"],
        payload["areas"],
        payload["requirements"],
    )
    return payload


def run_inail_import(db: Session) -> ImportResult:
    source = _ensure_source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=INAIL_BASE_URL,
            timeout=30,
            verify=(
                build_inail_ssl_context()
                if settings.source_import_verify_tls
                else False
            ),
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            records = _fetch_records(client)
        for raw in records:
            if not direct_psychology_match(raw["title"]):
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
