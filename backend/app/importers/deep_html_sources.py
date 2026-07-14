from __future__ import annotations

import re
import time
import warnings
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urljoin, urlparse

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
from app.services.source_probe import (
    _probe_error_status,
    ensure_source_catalog,
    source_rotation_batch,
)
from app.services.source_telemetry import start_source_attempt

DEEP_SOURCE_TYPES = {
    "external-transparency",
    "pat-html",
    "hospital-html-hub",
}
MAX_DEEP_LINK_DEPTH = 2

SKIP_DEEP_LINK_TERMS = (
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

DEEP_OPPORTUNITY_TERMS = (
    "avviso",
    "avvisi",
    "bando",
    "bandi",
    "collaborazione",
    "concorso",
    "concorsi",
    "incarico",
    "incarichi",
    "mobilita",
    "procedura",
    "procedure",
    "selezione",
    "selezioni",
    "assegno",
    "borsa",
    "elenco idonei",
    "interpello",
    "short list",
)

DEEP_PSYCHOLOGY_TERMS = (
    "psicolog",
    "psicoterap",
    "neuropsicolog",
    "lm-51",
    "lm 51",
    "l-24",
    "l 24",
    "scienze e tecniche psicologiche",
    "psicodiagnostic",
    "valutazione psicologica",
    "test neuropsicologici",
    "riabilitazione cognitiva",
    "psicopedagog",
    "psicoeduc",
    "psicosocial",
    "salute mentale",
    "benessere psicologico",
)

DEEP_DETAIL_PATTERNS = (
    r"/ap/",
    r"/competition/",
    r"/concorsi?/",
    r"/bandi?/",
    r"/avvisi?/",
    r"/dettaglio",
    r"/procedure/",
    r"/trasparenza/",
    r"/amministrazione-trasparente/",
    r"categoria\.php",
    r"dettaglio",
    r"idsezione",
    r"activepage",
    r"serveblob",
)

PAGINATION_TERMS = (
    "next",
    "successiva",
    "seguente",
    "pagina",
)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def _same_site(left_url: str, right_url: str) -> bool:
    left = urlparse(left_url)
    right = urlparse(right_url)
    return not right.netloc or left.netloc == right.netloc


def _is_binary_or_mail_link(href: str) -> bool:
    lower = href.lower()
    if lower.startswith(("mailto:", "tel:", "javascript:")):
        return True
    return lower.endswith((".pdf", ".doc", ".docx", ".odt", ".zip", ".rar", ".7z"))


def _pagination_score(label: str, href: str, rel: str) -> int:
    normalized = _normalize(f"{label} {href} {rel}")
    query_keys = {key.lower() for key, _value in parse_qsl(urlparse(href).query)}
    if "next" in rel.lower():
        return 6
    if query_keys.intersection({"page", "p", "pagina", "activepage", "active-page"}):
        return 5
    if any(term in normalized for term in PAGINATION_TERMS):
        return 3
    return 0


def _deep_link_score(label: str, href: str, rel: str = "") -> int:
    normalized = _normalize(f"{label} {href}")
    if not normalized or any(term in normalized for term in SKIP_DEEP_LINK_TERMS):
        return 0

    href_lower = href.lower()
    pagination_score = _pagination_score(label, href, rel)
    score = pagination_score
    if any(term in normalized for term in DEEP_PSYCHOLOGY_TERMS):
        score += 10
    if pagination_score:
        return score
    if any(term in normalized for term in DEEP_OPPORTUNITY_TERMS):
        score += 7
    if any(re.search(pattern, href_lower) for pattern in DEEP_DETAIL_PATTERNS):
        score += 6
    if any(term in normalized for term in ("scheda", "dettaglio", "visualizza", "leggi")):
        score += 2
    return score


def collect_deep_links(html: str, base_url: str, *, limit: int | None = None) -> list[str]:
    max_links = settings.deep_adapter_max_links_per_source if limit is None else limit
    if max_links <= 0:
        return []
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html, "html.parser")

    candidates: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for index, link in enumerate(soup.find_all("a", href=True)):
        href = str(link["href"])
        if _is_binary_or_mail_link(href):
            continue
        absolute = urljoin(base_url, href)
        if absolute in seen or not _same_site(base_url, absolute):
            continue
        label = link.get_text(" ", strip=True)
        rel = " ".join(str(item) for item in (link.get("rel") or []))
        score = _deep_link_score(label, href, rel)
        if score <= 0:
            continue
        seen.add(absolute)
        candidates.append((score, index, absolute))

    candidates.sort(key=lambda item: (-item[0], item[1]))
    return [absolute for _score, _index, absolute in candidates[:max_links]]


def _sources_for_deep_import(db: Session) -> list[Source]:
    ensure_source_catalog(db)
    sources = list(db.scalars(select(Source).where(Source.source_type.in_(DEEP_SOURCE_TYPES))))
    return source_rotation_batch(
        sources,
        batch_size=settings.deep_adapter_sources_per_run,
        group_name="adapter profondi",
    )


def _upsert_records(
    db: Session,
    source: Source,
    records_by_id: dict[str, CatalogRecord],
) -> tuple[int, int, int]:
    created = 0
    updated = 0
    skipped = 0
    for record in records_by_id.values():
        if not _is_relevant_opportunity(f"{record.title} {record.description}"):
            skipped += 1
            continue
        align_existing_catalog_record(db, source, record)
        if upsert_opportunity(
            db,
            payload=_payload(db, source, record),
            attachments=[],
        ):
            created += 1
        else:
            updated += 1
    return created, updated, skipped


def run_deep_html_sources_import(db: Session) -> ImportResult:
    run = ImportRun(source_id=None, status="running")
    db.add(run)
    db.flush()
    created = 0
    updated = 0
    skipped = 0

    try:
        import_deadline = time.monotonic() + settings.deep_adapter_budget_seconds
        with httpx.Client(
            timeout=httpx.Timeout(8, connect=4),
            verify=settings.source_import_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+adapter profondi)"},
        ) as client:
            for source in _sources_for_deep_import(db):
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
                        for record in parse_catalog_records(source, html, source.base_url)
                    }
                    seen_urls = {source.base_url}
                    pages_to_visit = [
                        (url, 1)
                        for url in collect_deep_links(html, source.base_url)
                        if url not in seen_urls
                    ]
                    visited_pages = 0
                    while (
                        pages_to_visit
                        and visited_pages < settings.deep_adapter_max_links_per_source
                    ):
                        if time.monotonic() > import_deadline:
                            break
                        url, depth = pages_to_visit.pop(0)
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)
                        try:
                            page_html = _fetch_text(client, url)
                        except Exception:
                            skipped += 1
                            attempt.skipped()
                            continue
                        if page_html is None:
                            skipped += 1
                            attempt.skipped()
                            continue
                        visited_pages += 1
                        for record in parse_catalog_records(source, page_html, url):
                            records_by_id[record.external_id] = record
                        if depth >= MAX_DEEP_LINK_DEPTH:
                            continue
                        remaining = settings.deep_adapter_max_links_per_source - visited_pages
                        for nested_url in collect_deep_links(
                            page_html,
                            url,
                            limit=remaining,
                        ):
                            if nested_url not in seen_urls:
                                pages_to_visit.append((nested_url, depth + 1))

                    source_created, source_updated, source_skipped = _upsert_records(
                        db,
                        source,
                        records_by_id,
                    )
                    created += source_created
                    updated += source_updated
                    skipped += source_skipped
                    attempt.created(source_created)
                    attempt.updated(source_updated)
                    attempt.skipped(source_skipped)
                    source.status = "active"
                    source.last_success_at = datetime.now(UTC)
                    source.last_error = None
                    db.flush()
                except Exception as exc:
                    source.status = _probe_error_status(exc)
                    source.last_error = str(exc)
                    skipped += 1
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
