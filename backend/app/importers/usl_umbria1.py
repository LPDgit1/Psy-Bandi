from __future__ import annotations

import hashlib
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
from app.services.source_probe import _probe_error_status, ensure_source_catalog

USL_UMBRIA1_SOURCE_NAME = "USL Umbria 1 - Bandi di concorso"
USL_UMBRIA1_CATEGORY_PATHS = (
    "/cat_bando_concorso/avvisi/",
    "/cat_bando_concorso/concorsi/",
    "/cat_bando_concorso/mobilita/",
    "/cat_bando_concorso/incarichi-direzione-strutture-complesse/",
)
MAX_PAGES_PER_CATEGORY = 4


@dataclass(frozen=True)
class Umbria1Record:
    external_id: str
    title: str
    description: str
    official_url: str
    deadline: datetime | None
    attachments: tuple[dict[str, str | None], ...]


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _external_id(official_url: str) -> str:
    return hashlib.sha256(official_url.encode()).hexdigest()[:24]


def _deadline_from_text(text: str) -> datetime | None:
    patterns = (
        r"data\s+scadenza[:\s]+([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
        r"scadenza(?:\s+domande)?[:\s]+([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
        r"entro\s+il\s+([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_date(match.group(1))
    return None


def _file_type(url: str, title: str) -> str | None:
    normalized = f"{url} {title}".lower()
    for extension in ("pdf", "docx", "doc", "odt", "zip"):
        if f".{extension}" in normalized:
            return extension
    return None


def _attachments_from_detail(html: str, detail_url: str) -> tuple[dict[str, str | None], ...]:
    soup = BeautifulSoup(html, "html.parser")
    attachments: list[dict[str, str | None]] = []
    for link in soup.find_all("a", href=True):
        href = urljoin(detail_url, str(link["href"]))
        label = _clean_text(link.get_text(" ", strip=True))
        combined = normalize_text(f"{label} {href}")
        raw_combined = f"{label} {href}".lower()
        if not any(
            extension in raw_combined
            for extension in (".pdf", ".doc", ".docx", ".odt", ".zip")
        ):
            continue
        if any(term in combined for term in ("commissione", "graduatoria", "ammessi", "esito")):
            continue
        title = label or href.rsplit("/", 1)[-1]
        attachments.append(
            {
                "title": title[:255],
                "url": href,
                "file_type": _file_type(href, title),
            }
        )
    unique = {str(attachment["url"]): attachment for attachment in attachments}
    return tuple(unique.values())[:6]


def parse_usl_umbria1_listing(html: str, page_url: str) -> list[Umbria1Record]:
    soup = BeautifulSoup(html, "html.parser")
    records: list[Umbria1Record] = []
    for card in soup.select(".scheda-sito"):
        link = card.find("a", href=True)
        if link is None:
            continue
        text = _clean_text(card.get_text(" ", strip=True))
        title = _clean_text(link.get_text(" ", strip=True)) or text[:240]
        if not title:
            continue
        official_url = urljoin(page_url, str(link["href"]))
        records.append(
            Umbria1Record(
                external_id=_external_id(official_url),
                title=title[:500],
                description=text[:2400],
                official_url=official_url,
                deadline=_deadline_from_text(text),
                attachments=(),
            )
        )
    return records


def parse_usl_umbria1_detail(
    listing_record: Umbria1Record,
    html: str,
    detail_url: str,
) -> Umbria1Record:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main, article, .entry-content, .container")
    detail_text = _clean_text((main or soup).get_text(" ", strip=True))
    description = detail_text[:2400] if detail_text else listing_record.description
    return Umbria1Record(
        external_id=listing_record.external_id,
        title=listing_record.title,
        description=description,
        official_url=detail_url,
        deadline=_deadline_from_text(description) or listing_record.deadline,
        attachments=_attachments_from_detail(html, detail_url),
    )


def _source(db: Session) -> Source:
    ensure_source_catalog(db)
    return db.scalar(select(Source).where(Source.name == USL_UMBRIA1_SOURCE_NAME))  # type: ignore[return-value]


def _payload(db: Session, source: Source, record: Umbria1Record) -> dict[str, Any]:
    status = infer_status(record.deadline)
    classification = classify_text(record.title, record.description)
    duplicate = find_probable_duplicate(
        db,
        source_id=source.id,
        title=record.title,
        organization=source.organization or source.name,
        deadline=record.deadline,
    )
    editorial_status, editorial_notes = editorial_visibility(
        status=status,
        duplicate=duplicate,
    )
    payload: dict[str, Any] = {
        "external_id": record.external_id,
        "source_id": source.id,
        "title": record.title,
        "normalized_title": normalize_text(record.title),
        "short_description": record.description[:900],
        "description": record.description,
        "summary": record.description[:420],
        "category": classification.category,
        "areas": classification.areas,
        "psychology_relevance": classification.psychology_relevance,
        "relevance_score": classification.relevance_score,
        "organization": source.organization or source.name,
        "entity_type": "azienda-sanitaria",
        "region": "Umbria",
        "original_location": "Umbria",
        "status": status,
        "deadline": record.deadline,
        "last_seen_at": datetime.now(UTC),
        "requirements": classification.requirements,
        "application_mode": "Consultare la scheda ufficiale USL Umbria 1.",
        "official_url": record.official_url,
        "organization_url": source.base_url,
        "content_hash": content_hash(record.title, record.description, record.official_url),
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


def _listing_urls(source: Source) -> list[str]:
    urls: list[str] = []
    base = source.base_url
    for path in USL_UMBRIA1_CATEGORY_PATHS:
        category_url = urljoin(base, path)
        urls.append(category_url)
        for page in range(2, MAX_PAGES_PER_CATEGORY + 1):
            urls.append(urljoin(category_url, f"page/{page}/"))
    return urls


def run_usl_umbria1_import(db: Session) -> ImportResult:
    source = _source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        with httpx.Client(
            timeout=httpx.Timeout(12, connect=5),
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+fonti pubbliche)"},
        ) as client:
            records_by_id: dict[str, Umbria1Record] = {}
            for url in _listing_urls(source):
                try:
                    response = client.get(url)
                    if response.status_code == 404:
                        continue
                    response.raise_for_status()
                except Exception:
                    skipped += 1
                    continue
                for record in parse_usl_umbria1_listing(response.text, str(response.url)):
                    if not direct_psychology_match(record.title, record.description):
                        skipped += 1
                        continue
                    detail = client.get(record.official_url)
                    detail.raise_for_status()
                    full_record = parse_usl_umbria1_detail(record, detail.text, str(detail.url))
                    records_by_id[full_record.external_id] = full_record

            for record in records_by_id.values():
                if upsert_opportunity(
                    db,
                    payload=_payload(db, source, record),
                    attachments=list(record.attachments),
                ):
                    created += 1
                else:
                    updated += 1

        source.status = "active"
        source.last_success_at = datetime.now(UTC)
        source.last_error = None
        run.status = "success"
    except Exception as exc:
        source.status = _probe_error_status(exc)
        source.last_error = str(exc)
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
