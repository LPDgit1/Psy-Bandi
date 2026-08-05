from __future__ import annotations

import hashlib
import re
import time
import warnings
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.importers.base import ImportResult
from app.importers.catalog_sources import (
    CatalogRecord,
    _fetch_text,
    _is_relevant_opportunity,
    _payload,
    align_existing_catalog_record,
    parse_catalog_records,
)
from app.importers.institutional import upsert_opportunity
from app.ministerial_catalog import MINISTERIAL_SOURCE_DEFINITIONS
from app.models import ImportRun, Source
from app.services.source_probe import _probe_error_status, ensure_source_catalog
from app.services.source_telemetry import start_source_attempt

MINISTERIAL_SOURCE_NAMES = {
    definition["name"]
    for definition in MINISTERIAL_SOURCE_DEFINITIONS
    if definition["source_type"] == "ministerial-html-hub"
}
MAX_DETAIL_LINKS_PER_SOURCE = 24
MAX_RECORDS_PER_SOURCE = 30
SKIP_LINK_TERMS = (
    "accessibilita",
    "cookie",
    "facebook",
    "instagram",
    "login",
    "newsletter",
    "privacy",
    "rss",
    "twitter",
    "youtube",
)
LINK_TERMS = (
    "avviso",
    "avvisi",
    "bando",
    "bandi",
    "concorso",
    "concorsi",
    "reclutamento",
    "selezione",
    "psicolog",
    "corpo sanitario",
    "tecnico-scientifico",
)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _same_site(base_url: str, candidate_url: str) -> bool:
    base = urlparse(base_url)
    candidate = urlparse(candidate_url)
    return not candidate.netloc or candidate.netloc.casefold() == base.netloc.casefold()


def _is_binary(href: str) -> bool:
    lower = href.casefold()
    return lower.startswith(("mailto:", "tel:", "javascript:")) or lower.endswith(
        (".pdf", ".doc", ".docx", ".odt", ".zip")
    )


def _link_score(label: str, href: str) -> int:
    normalized = _normalize(f"{label} {href}")
    if not normalized or any(term in normalized for term in SKIP_LINK_TERMS):
        return 0
    score = sum(2 for term in LINK_TERMS if term in normalized)
    if any(token in href.casefold() for token in ("/concor", "/bando", "/avvis", "/reclut")):
        score += 4
    return score


def collect_ministerial_detail_links(
    html: str,
    base_url: str,
    *,
    limit: int = MAX_DETAIL_LINKS_PER_SOURCE,
) -> list[str]:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html, "html.parser")
    candidates: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for index, link in enumerate(soup.find_all("a", href=True)):
        href = str(link["href"])
        if _is_binary(href):
            continue
        absolute = urljoin(base_url, href)
        if absolute in seen or not _same_site(base_url, absolute):
            continue
        score = _link_score(link.get_text(" ", strip=True), href)
        if score <= 0:
            continue
        seen.add(absolute)
        candidates.append((score, index, absolute))
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [url for _score, _index, url in candidates[: max(0, limit)]]


def parse_ministerial_records(
    source: Source,
    html: str,
    page_url: str,
) -> list[CatalogRecord]:
    """Parse only psychology-related opportunities from an official ministry page."""
    records = parse_catalog_records(source, html, page_url)
    if records:
        return records[:MAX_RECORDS_PER_SOURCE]

    # Some government portals expose a single useful card with generic markup.
    # Keep this fallback narrow so a whole hub page is never published as a band.
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("script, style, noscript, nav, footer"):
        node.decompose()
    candidates = soup.select("article, tr, li, .card, .views-row, .item")
    parsed: dict[str, CatalogRecord] = {}
    for container in candidates:
        text = re.sub(r"\s+", " ", container.get_text(" ", strip=True)).strip()
        if not (24 <= len(text) <= 2400) or not _is_relevant_opportunity(text):
            continue
        title_node = container.select_one("h1, h2, h3, h4, strong, a[href]")
        title = (
            title_node.get_text(" ", strip=True)
            if title_node is not None
            else text[:500]
        )
        if len(title) < 12:
            continue
        official_url = page_url
        link = container.select_one("a[href]")
        if link is not None:
            official_url = urljoin(page_url, str(link["href"]))
        external_id = hashlib.sha256(
            f"{source.id}|{title}|{official_url}".encode()
        ).hexdigest()[:24]
        parsed[external_id] = CatalogRecord(
            external_id=external_id,
            title=title[:500],
            description=text[:2400],
            official_url=official_url,
            published_at=None,
            deadline=None,
        )
        if len(parsed) >= MAX_RECORDS_PER_SOURCE:
            break
    return list(parsed.values())


def _sources(db: Session) -> list[Source]:
    ensure_source_catalog(db)
    return list(
        db.scalars(
            select(Source)
            .where(Source.name.in_(MINISTERIAL_SOURCE_NAMES))
            .order_by(Source.name)
        )
    )


def run_ministerial_sources_import(db: Session) -> ImportResult:
    run = ImportRun(source_id=None, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        import_deadline = time.monotonic() + settings.deep_adapter_budget_seconds
        with httpx.Client(
            timeout=httpx.Timeout(10, connect=5),
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+adapter ministeriali)"},
        ) as client:
            for source in _sources(db):
                if time.monotonic() > import_deadline:
                    skipped += 1
                    continue
                attempt = start_source_attempt(db, source)
                try:
                    html = _fetch_text(client, source.base_url)
                    if html is None:
                        skipped += 1
                        attempt.skipped()
                        continue

                    records_by_id: dict[str, CatalogRecord] = {
                        record.external_id: record
                        for record in parse_ministerial_records(
                            source,
                            html,
                            source.base_url,
                        )
                    }
                    visited = {source.base_url}
                    for detail_url in collect_ministerial_detail_links(
                        html,
                        source.base_url,
                    ):
                        if time.monotonic() > import_deadline:
                            break
                        if detail_url in visited:
                            continue
                        visited.add(detail_url)
                        try:
                            detail_html = _fetch_text(client, detail_url)
                        except Exception:
                            skipped += 1
                            attempt.skipped()
                            continue
                        if detail_html is None:
                            skipped += 1
                            attempt.skipped()
                            continue
                        records_by_id.update(
                            {
                                record.external_id: record
                                for record in parse_ministerial_records(
                                    source,
                                    detail_html,
                                    detail_url,
                                )
                            }
                        )
                        if len(records_by_id) >= MAX_RECORDS_PER_SOURCE:
                            break

                    for record in list(records_by_id.values())[:MAX_RECORDS_PER_SOURCE]:
                        align_existing_catalog_record(db, source, record)
                        if upsert_opportunity(
                            db,
                            payload=_payload(db, source, record),
                            attachments=[],
                        ):
                            created += 1
                            attempt.created()
                        else:
                            updated += 1
                            attempt.updated()
                    source.status = "active"
                    source.last_success_at = datetime.now(UTC)
                    source.last_error = None
                    db.flush()
                except Exception as exc:
                    skipped += 1
                    source.status = _probe_error_status(exc)
                    source.last_error = str(exc)
                    attempt.skipped()
                    attempt.fail(exc)
                finally:
                    attempt.finish()
        run.status = "success"
    except Exception as exc:
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
        source_id=None,
        created_count=created,
        updated_count=updated,
        skipped_count=skipped,
    )
