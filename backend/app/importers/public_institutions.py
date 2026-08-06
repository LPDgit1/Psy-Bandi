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
from app.models import ImportRun, Source
from app.public_institution_catalog import PUBLIC_INSTITUTION_SOURCE_NAMES
from app.services.dates import parse_date
from app.services.source_probe import _probe_error_status, ensure_source_catalog
from app.services.source_telemetry import start_source_attempt


MAX_DETAIL_LINKS_PER_SOURCE = 18
MAX_RECORDS_PER_SOURCE = 30
MAX_RECORD_TEXT = 2400
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
OPPORTUNITY_LINK_TERMS = (
    "avvis",
    "band",
    "concors",
    "incaric",
    "opportun",
    "posizion",
    "reclut",
    "selezion",
    "career",
    "opening",
    "job",
    "research",
    "lavora",
)
DATE_RE = r"(?:[0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|[0-9]{1,2}\s+[a-z]{3,12}\s+[0-9]{4})"


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()


def _text_for(node: object) -> str:
    return _clean_text(node.get_text(" ", strip=True))  # type: ignore[union-attr]


def _same_site(base_url: str, candidate_url: str) -> bool:
    base_host = (urlparse(base_url).hostname or "").casefold()
    candidate_host = (urlparse(candidate_url).hostname or "").casefold()
    if not candidate_host or candidate_host == base_host:
        return True
    # MIM/MIUR pages and their current regional mirrors legitimately link across
    # these official education domains. Keep all other cross-site links out.
    education_hosts = ("mim.gov.it", "miur.gov.it", "istruzione.gov.it")
    if any(base_host.endswith(domain) for domain in education_hosts) and any(
        candidate_host.endswith(domain) for domain in education_hosts
    ):
        return True
    return False


def _is_binary(url: str) -> bool:
    return url.casefold().split("?", 1)[0].endswith(
        (".pdf", ".doc", ".docx", ".odt", ".zip", ".xlsx", ".xls")
    )


def _link_score(label: str, href: str) -> int:
    normalized = _clean_text(f"{label} {href}").casefold()
    if not normalized or any(term in normalized for term in SKIP_LINK_TERMS):
        return 0
    score = sum(2 for term in OPPORTUNITY_LINK_TERMS if term in normalized)
    if any(
        token in href.casefold()
        for token in ("/bando", "/avvis", "/concor", "/selez", "/opening", "/career")
    ):
        score += 4
    return score


def collect_public_detail_links(
    html: str,
    base_url: str,
    *,
    limit: int = MAX_DETAIL_LINKS_PER_SOURCE,
) -> list[str]:
    """Find likely detail pages across government and research portal layouts."""

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html, "html.parser")
    candidates: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for index, link in enumerate(soup.find_all("a", href=True)):
        href = str(link["href"])
        if href.startswith(("mailto:", "tel:", "javascript:", "#")) or _is_binary(href):
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


def _deadline_from_text(text: str):
    patterns = (
        rf"data\s+(?:e\s+ora\s+di\s+)?scadenza.{{0,100}}?({DATE_RE})",
        rf"scadenza(?:\s+domande)?.{{0,100}}?({DATE_RE})",
        rf"entro\s+il\s+({DATE_RE})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_date(match.group(1))
    return None


def _title_from_container(container: object, fallback: str) -> str:
    if getattr(container, "name", None) == "a":
        title = _text_for(container)
        if len(title) >= 12:
            return title[:500]
    for selector in ("h1", "h2", "h3", "h4", "h5", "strong", "a[href]"):
        node = (
            container.select_one(selector)
            if hasattr(container, "select_one")
            else None
        )  # type: ignore[union-attr]
        if node is None:
            continue
        title = _text_for(node)
        if len(title) >= 12 and not title.casefold().startswith(("menu", "home")):
            return title[:500]
    return fallback[:500]


def _first_link(container: object, page_url: str) -> str:
    if getattr(container, "name", None) == "a" and container.has_attr(
        "href"
    ):  # type: ignore[union-attr]
        return urljoin(page_url, str(container["href"]))  # type: ignore[index]
    link = (
        container.select_one("a[href]")
        if hasattr(container, "select_one")
        else None
    )  # type: ignore[union-attr]
    return (
        urljoin(page_url, str(link["href"])) if link is not None else page_url
    )  # type: ignore[index]


def _is_source_page(source: Source, page_url: str) -> bool:
    source_parsed = urlparse(source.base_url)
    page_parsed = urlparse(page_url)
    return (
        source_parsed.scheme,
        source_parsed.netloc.casefold(),
        source_parsed.path.rstrip("/"),
        source_parsed.query,
    ) == (
        page_parsed.scheme,
        page_parsed.netloc.casefold(),
        page_parsed.path.rstrip("/"),
        page_parsed.query,
    )


def _record(source: Source, title: str, text: str, official_url: str) -> CatalogRecord:
    external_id = hashlib.sha256(
        f"{source.id}|{official_url.casefold()}".encode("utf-8")
    ).hexdigest()[:24]
    if _is_source_page(source, official_url):
        external_id = hashlib.sha256(
            f"{source.id}|{official_url.casefold()}|{title.casefold()}".encode("utf-8")
        ).hexdigest()[:24]
    return CatalogRecord(
        external_id=external_id,
        title=title[:500],
        description=text[:MAX_RECORD_TEXT],
        official_url=official_url,
        published_at=None,
        deadline=_deadline_from_text(text),
    )


def parse_public_institution_records(
    source: Source,
    html: str,
    page_url: str,
) -> list[CatalogRecord]:
    """Parse psychology-relevant records from heterogeneous institutional HTML."""

    parsed = parse_catalog_records(source, html, page_url)
    if parsed:
        return parsed[:MAX_RECORDS_PER_SOURCE]

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("script, style, noscript, nav, footer, header"):
        node.decompose()

    selectors = (
        "article",
        "tr",
        "li",
        ".card",
        ".card-body",
        ".views-row",
        ".node",
        ".item",
        ".opening",
        ".job",
        ".job-card",
        ".result",
        ".list-group-item",
        "main > div",
    )
    records: dict[str, CatalogRecord] = {}
    for selector in selectors:
        for container in soup.select(selector):
            text = _text_for(container)
            if not (24 <= len(text) <= MAX_RECORD_TEXT) or not _is_relevant_opportunity(text):
                continue
            title = _title_from_container(container, text)
            if len(title) < 12:
                continue
            official_url = _first_link(container, page_url)
            record = _record(source, title, text, official_url)
            records[record.external_id] = record
            if len(records) >= MAX_RECORDS_PER_SOURCE:
                break
        if len(records) >= MAX_RECORDS_PER_SOURCE:
            break

    # A detail page can use a single content wrapper without article/card markup.
    page_text = _text_for(soup)
    if (
        not records
        and not _is_source_page(source, page_url)
        and len(page_text) <= 7000
        and _is_relevant_opportunity(page_text)
    ):
        title = soup.title.get_text(" ", strip=True) if soup.title else source.name
        if len(title) >= 12:
            record = _record(source, title, page_text, page_url)
            records[record.external_id] = record
    return list(records.values())[:MAX_RECORDS_PER_SOURCE]


def _sources(db: Session) -> list[Source]:
    ensure_source_catalog(db)
    return list(
        db.scalars(
            select(Source)
            .where(Source.name.in_(PUBLIC_INSTITUTION_SOURCE_NAMES))
            .order_by(Source.name)
        )
    )


def run_public_institution_sources_import(db: Session) -> ImportResult:
    """Refresh Salute, research, justice, MUR, family and all official USRs."""

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
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+adapter istituzioni pubbliche)"},
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

                    records_by_id = {
                        record.external_id: record
                        for record in parse_public_institution_records(
                            source, html, source.base_url
                        )
                    }
                    for detail_url in collect_public_detail_links(html, source.base_url):
                        if time.monotonic() > import_deadline:
                            break
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
                                for record in parse_public_institution_records(
                                    source, detail_html, detail_url
                                )
                            }
                        )
                        if len(records_by_id) >= MAX_RECORDS_PER_SOURCE:
                            break

                    if not records_by_id:
                        attempt.skipped()
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
