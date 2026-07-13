from __future__ import annotations

import hashlib
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

AZIENDA_ZERO_PIEMONTE_SOURCE_NAME = "Azienda Zero Piemonte - Concorsi pubblici"
AZIENDA_ZERO_PIEMONTE_BASE_URL = "https://www.aziendazero.piemonte.it"
AZIENDA_ZERO_PIEMONTE_PUBLIC_PATH = "/concorsiaz0/concorsi-pubblici/"
AZIENDA_ZERO_PIEMONTE_SECTIONS = (
    "/concorsiaz0/concorsi-pubblici/",
    "/concorsiaz0/avvisi-pubblici-a-tempo-determinato/",
    "/concorsiaz0/incarichi-di-collaborazione/",
    "/concorsiaz0/incarichi-direttore-struttura-complessa/",
    "/concorsiaz0/mobilita/",
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
    source = db.scalar(
        select(Source).where(Source.name == AZIENDA_ZERO_PIEMONTE_SOURCE_NAME)
    )
    if source:
        return source

    source = Source(
        name=AZIENDA_ZERO_PIEMONTE_SOURCE_NAME,
        source_type="html-list",
        base_url=f"{AZIENDA_ZERO_PIEMONTE_BASE_URL}{AZIENDA_ZERO_PIEMONTE_PUBLIC_PATH}",
        region="Piemonte",
        organization="Azienda Sanitaria Zero Piemonte",
        import_method="html-list-paginated",
        refresh_frequency="daily",
        status="active",
        technical_notes=(
            "Adapter sulle sezioni pubbliche WordPress e sulla paginazione pag_concorsi."
        ),
    )
    db.add(source)
    db.flush()
    return source


def _positions(title: str) -> int | None:
    match = re.search(
        r"\bn\.?\s*(\d+)\s+(?:post[oi]|incarich[io]|unita)\b",
        title,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def _attachment_file_type(url: str) -> str | None:
    normalized_url = url.lower()
    for extension in ("pdf", "docx", "doc", "odt", "zip"):
        if f".{extension}" in normalized_url:
            return extension
    return None


def _safe_attachments(card: Any) -> list[dict[str, str | None]]:
    attachments: list[dict[str, str | None]] = []
    for holder in card.select(".allegati-container"):
        link = holder.find("a", href=True)
        if link is None:
            continue
        label = holder.find("p")
        title = label.get_text(" ", strip=True) if label else "Documento ufficiale"
        normalized_title = normalize_text(title)
        if any(term in normalized_title for term in EXCLUDED_ATTACHMENT_TERMS):
            continue
        url = urljoin(AZIENDA_ZERO_PIEMONTE_BASE_URL, str(link["href"]))
        attachments.append(
            {
                "title": title,
                "url": url,
                "file_type": _attachment_file_type(url),
            }
        )
    return attachments[:6]


def _external_id(
    title: str,
    published_at: datetime | None,
    deadline: datetime | None,
    section_url: str,
) -> str:
    raw = "|".join(
        [
            normalize_text(title),
            published_at.date().isoformat() if published_at else "",
            deadline.date().isoformat() if deadline else "",
            section_url,
        ]
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def parse_records(html: str, section_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict[str, Any]] = []
    for card in soup.select(".dro-concorso-holder"):
        title_node = card.find("h2")
        if title_node is None:
            continue
        title = title_node.get_text(" ", strip=True)
        dates = [span.get_text(" ", strip=True) for span in card.select(".concorso-date span")]
        published_at = parse_date(dates[0]) if dates else None
        deadline = parse_date(dates[1]) if len(dates) > 1 else None
        attachments = _safe_attachments(card)
        records.append(
            {
                "external_id": _external_id(title, published_at, deadline, section_url),
                "title": title,
                "description": title,
                "published_at": published_at,
                "deadline": deadline,
                "section_url": section_url,
                "attachments": attachments,
            }
        )
    return records


def _has_next_page(html: str, next_page: int) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    marker = f"pag_concorsi={next_page}"
    return any(marker in str(link.get("href", "")) for link in soup.find_all("a", href=True))


def _fetch_records(client: httpx.Client) -> list[dict[str, Any]]:
    records_by_id: dict[str, dict[str, Any]] = {}
    for section_path in AZIENDA_ZERO_PIEMONTE_SECTIONS:
        for page in range(1, settings.azienda_zero_piemonte_max_pages + 1):
            path = section_path if page == 1 else f"{section_path}?pag_concorsi={page}"
            response = client.get(path)
            response.raise_for_status()
            section_url = urljoin(AZIENDA_ZERO_PIEMONTE_BASE_URL, section_path)
            for record in parse_records(response.text, section_url):
                records_by_id[record["external_id"]] = record
            if not _has_next_page(response.text, page + 1):
                break
    return list(records_by_id.values())


def _official_url(raw: dict[str, Any]) -> str:
    attachments = raw["attachments"]
    preferred = [
        attachment
        for attachment in attachments
        if "bando" in normalize_text(str(attachment["title"]))
    ]
    return str((preferred or attachments)[0]["url"]) if attachments else str(raw["section_url"])


def _payload(db: Session, source: Source, raw: dict[str, Any]) -> dict[str, Any]:
    title = raw["title"]
    description = raw["description"]
    deadline = raw["deadline"]
    status = infer_status(deadline)
    classification = classify_text(title, description)
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=title,
        organization="Azienda Sanitaria Zero Piemonte",
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
        "organization": "Azienda Sanitaria Zero Piemonte",
        "entity_type": "azienda-sanitaria",
        "region": "Piemonte",
        "original_location": "Piemonte",
        "status": status,
        "published_at": raw["published_at"],
        "deadline": deadline,
        "last_seen_at": datetime.now(UTC),
        "positions": _positions(title),
        "requirements": classification.requirements,
        "application_mode": "Consultare il bando ufficiale di Azienda Zero Piemonte.",
        "official_url": _official_url(raw),
        "organization_url": raw["section_url"],
        "content_hash": content_hash(title, description, raw["section_url"]),
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


def run_azienda_zero_piemonte_import(db: Session) -> ImportResult:
    source = _ensure_source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            base_url=AZIENDA_ZERO_PIEMONTE_BASE_URL,
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
                attachments=raw["attachments"],
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
