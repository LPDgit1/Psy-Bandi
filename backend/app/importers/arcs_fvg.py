from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

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

ARCS_FVG_SOURCE_NAME = "ARCS FVG - Concorsi avvisi incarichi"
ARCS_FVG_BASE_URL = "https://arcs.sanita.fvg.it"
ARCS_FVG_LIST_PATH = (
    "/it/professionisti-e-fornitori/concorsi-avvisi-incarichi/concorsi-e-avvisi"
)
EXCLUDED_ATTACHMENT_TERMS = (
    "ammess",
    "candidat",
    "commission",
    "convocaz",
    "esito",
    "graduator",
    "prova",
)


def _ensure_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == ARCS_FVG_SOURCE_NAME))
    if source:
        return source

    source = Source(
        name=ARCS_FVG_SOURCE_NAME,
        source_type="html-list-detail",
        base_url=f"{ARCS_FVG_BASE_URL}{ARCS_FVG_LIST_PATH}",
        region="Friuli-Venezia Giulia",
        organization="ARCS Friuli-Venezia Giulia",
        import_method="html-list-detail",
        refresh_frequency="daily",
        status="active",
        technical_notes=(
            "Adapter sulla lista pubblica Drupal. Apre il dettaglio solo per i "
            "profili psicologici espliciti."
        ),
    )
    db.add(source)
    db.flush()
    return source


def _positions(title: str) -> int | None:
    searchable_title = title.replace(".", "").replace(",", "")
    match = re.search(
        r"\bn\s*(\d+)\s+(?:post[oi]|incarich[io]|unita)\b",
        searchable_title,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def _external_id(detail_url: str) -> str:
    match = re.search(r"-(\d+)$", urlparse(detail_url).path)
    if match:
        return match.group(1)
    return hashlib.sha256(detail_url.encode()).hexdigest()[:24]


def _card_date(card: Any, label: str) -> datetime | None:
    for paragraph in card.find_all("p"):
        text = paragraph.get_text(" ", strip=True)
        if text.lower().startswith(label.lower()):
            return parse_date(text)
    return None


def parse_listing(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    for card in soup.select("article.oa-simple-card"):
        title_link = card.select_one("h3.it-card-title a[href]")
        if title_link is None:
            continue
        title = title_link.get_text(" ", strip=True)
        detail_url = urljoin(ARCS_FVG_BASE_URL, str(title_link["href"]))
        category = card.select_one(".it-card-category")
        records.append(
            {
                "external_id": _external_id(detail_url),
                "title": title,
                "detail_url": detail_url,
                "source_category": category.get_text(" ", strip=True) if category else "",
                "published_at": _card_date(card, "Data inizio"),
                "deadline": _card_date(card, "Data fine"),
            }
        )
    return records


def _attachment_file_type(url: str) -> str | None:
    normalized_url = url.lower()
    for extension in ("pdf", "docx", "doc", "odt", "zip"):
        if f".{extension}" in normalized_url:
            return extension
    return None


def parse_detail(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    description_node = soup.select_one("#section-descrizione")
    description = description_node.get_text(" ", strip=True) if description_node else ""
    attachments: list[dict[str, str | None]] = []
    for link in soup.select("#section-allegati .file-title a[href]"):
        title = link.get_text(" ", strip=True) or "Documento ufficiale"
        if any(term in normalize_text(title) for term in EXCLUDED_ATTACHMENT_TERMS):
            continue
        url = urljoin(ARCS_FVG_BASE_URL, str(link["href"]))
        attachments.append(
            {
                "title": title,
                "url": url,
                "file_type": _attachment_file_type(url),
            }
        )
    return {"description": description, "attachments": attachments[:6]}


def _fetch_records(client: httpx.Client) -> list[dict[str, Any]]:
    response = client.get(ARCS_FVG_LIST_PATH)
    response.raise_for_status()
    records = parse_listing(response.text)
    for record in records:
        if not direct_psychology_match(record["title"]):
            continue
        detail_response = client.get(record["detail_url"])
        detail_response.raise_for_status()
        record.update(parse_detail(detail_response.text))
    return records


def _payload(db: Session, source: Source, raw: dict[str, Any]) -> dict[str, Any]:
    title = raw["title"]
    description = raw.get("description") or title
    deadline = raw["deadline"]
    status = infer_status(deadline)
    classification = classify_text(title, description, raw["source_category"])
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=title,
        organization="ARCS Friuli-Venezia Giulia",
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
        "organization": "ARCS Friuli-Venezia Giulia",
        "entity_type": "azienda-sanitaria",
        "region": "Friuli-Venezia Giulia",
        "original_location": "Friuli-Venezia Giulia",
        "status": status,
        "published_at": raw["published_at"],
        "deadline": deadline,
        "last_seen_at": datetime.now(UTC),
        "positions": _positions(title),
        "requirements": classification.requirements,
        "application_mode": "Consultare la scheda ufficiale ARCS.",
        "official_url": raw["detail_url"],
        "organization_url": f"{ARCS_FVG_BASE_URL}{ARCS_FVG_LIST_PATH}",
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


def run_arcs_fvg_import(db: Session) -> ImportResult:
    source = _ensure_source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=ARCS_FVG_BASE_URL,
            timeout=30,
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            records = _fetch_records(client)
        for raw in records:
            if not direct_psychology_match(raw["title"]):
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
