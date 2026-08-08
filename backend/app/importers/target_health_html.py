from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.importers.base import ImportResult
from app.importers.institutional import (
    PSYCHOLOGY_QUERY_TERMS,
    direct_psychology_match,
    editorial_visibility,
    find_probable_duplicate,
    professional_role_match,
    upsert_opportunity,
)
from app.models import ImportRun, Opportunity, Source
from app.national_health_catalog import NATIONAL_HEALTH_SOURCE_DEFINITIONS
from app.services.classifier import build_search_text, classify_text, normalize_text
from app.services.dates import infer_status, parse_date
from app.services.dedupe import content_hash
from app.services.source_probe import (
    _probe_error_status,
    ensure_source_catalog,
    source_rotation_batch,
)
from app.services.source_telemetry import start_source_attempt
from app.target_health_catalog import TARGET_HEALTH_SOURCE_DEFINITIONS

VENETO_AULSS_SOURCE_NAMES = {
    definition["name"]
    for definition in NATIONAL_HEALTH_SOURCE_DEFINITIONS
    if str(definition.get("organization", "")).startswith("AULSS ")
}
TARGET_HEALTH_SOURCE_NAMES = {
    *(definition["name"] for definition in TARGET_HEALTH_SOURCE_DEFINITIONS),
    *VENETO_AULSS_SOURCE_NAMES,
}
AULSS4_SOURCE_NAME = "AULSS 4 Veneto Orientale - Concorsi"
AULSS4_API_URL = "https://www.aulss4.veneto.it/myportal/ASSL10VE/api/content"
AULSS4_DOWNLOAD_URL = (
    "https://www.aulss4.veneto.it/myportal/ASSL10VE/api/content/download?id={}"
)
AULSS4_CONTENT_PARENTS = (
    "/AmministrazioneTrasparente/05_Bandi_di_concorso/Concorsi Pubblici",
    "/AmministrazioneTrasparente/05_Bandi_di_concorso/Avvisi Pubblici/Lavoro autonomo",
    "/AmministrazioneTrasparente/05_Bandi_di_concorso/Avvisi Pubblici/Mobilità",
    (
        "/AmministrazioneTrasparente/05_Bandi_di_concorso/Avvisi Pubblici/"
        "Tempo determinato - DIRIGENZA"
    ),
    (
        "/AmministrazioneTrasparente/05_Bandi_di_concorso/Avvisi Pubblici/"
        "Tempo determinato - COMPARTO"
    ),
    "/AmministrazioneTrasparente/05_Bandi_di_concorso/Avvisi Pubblici/Direzione UOC",
)
MAX_DETAIL_URLS_PER_SOURCE = 20
MAX_RECORDS_PER_SOURCE = 25
MAX_AULSS_FILTER_URLS_PER_SOURCE = 40
SEARCH_QUERY_KEYS = {"combine", "q", "s", "search", "text"}
AULSS_FILTER_KEYS = {"area", "figura", "stato", "titolo"}

OPPORTUNITY_TERMS = (
    "avviso",
    "avvisi",
    "bando",
    "bandi",
    "collaborazione",
    "concorso",
    "concorsi",
    "graduatoria",
    "incarico",
    "incarichi",
    "contratti libero professionali",
    "contratto libero professionale",
    "libero professionale",
    "manifestazione di interesse",
    "manifestazione d interesse",
    "mobilita",
    "selezione",
    "selezioni",
    "stabilizzazione",
    "assegno di ricerca",
    "borsa di ricerca",
    "borsa di studio",
    "elenco idonei",
    "interpello",
    "short list",
)
SKIP_ATTACHMENT_TERMS = (
    "ammess",
    "commission",
    "convoc",
    "esito",
    "graduator",
    "nomina",
    "prova",
)
SKIP_RECORD_TERMS = (
    "ammess",
    "approvazione atti",
    "commission",
    "convoc",
    "diario",
    "esito",
    "graduator",
    "preselezione",
)
FOLLOWUP_TITLE_TERMS = (
    "ammissione candidati",
    "approvazione atti",
    "approvazione graduatoria",
    "conferimento incarico",
    "convocazione",
    "diario prova",
    "esito colloquio",
    "graduatoria finale",
    "nomina commissione",
    "presa atto",
    "prova orale",
    "prova pratica",
    "prova scritta",
)
FOLLOWUP_CONTENT_TERMS = (
    "approvazione atti della commissione",
    "approvazione graduatoria",
    "graduatoria finale di merito",
    "presa atto dell esito",
)
MULTI_PROFILE_TITLE_TERMS = (
    "figure professionali",
    "incarichi individuali",
    "profili professionali",
    "profili vari",
    "vari profili",
)
STRONG_OPPORTUNITY_TERMS = (
    "avviso pubblico",
    "bando",
    "concorso pubblico",
    "incarico libero",
    "manifestazione di interesse",
    "procedura comparativa",
    "selezione pubblica",
    "stabilizzazione",
)


@dataclass(frozen=True)
class TargetHealthRecord:
    external_id: str
    title: str
    description: str
    official_url: str
    published_at: datetime | None
    deadline: datetime | None
    attachments: tuple[dict[str, str | None], ...]


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()


def _is_textual_response(response: httpx.Response) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    return any(kind in content_type for kind in ("html", "text", "xml", "json"))


def _text_for(node: Any) -> str:
    return _clean_text(node.get_text(" ", strip=True))


def _has_opportunity_terms(text: str) -> bool:
    normalized = normalize_text(text)
    return any(term in normalized for term in OPPORTUNITY_TERMS)


def _is_relevant(text: str) -> bool:
    normalized = normalize_text(text)
    if any(term in normalized for term in FOLLOWUP_CONTENT_TERMS):
        return False
    if any(term in normalized for term in SKIP_RECORD_TERMS) and not any(
        term in normalized for term in STRONG_OPPORTUNITY_TERMS
    ):
        return False
    return (direct_psychology_match(text) or "neuropsicolog" in normalized) and (
        _has_opportunity_terms(text) or professional_role_match(text)
    )


def _source_search_urls(base_url: str) -> list[str]:
    parsed = urlparse(base_url)
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    search_indexes = [
        index
        for index, (key, value) in enumerate(query_items)
        if key in SEARCH_QUERY_KEYS
        and any(term in normalize_text(value) for term in ("psicolog", "psicoterap"))
    ]
    if not search_indexes:
        return [base_url]

    urls: list[str] = []
    for term in PSYCHOLOGY_QUERY_TERMS:
        next_items = [
            (key, term if index in search_indexes else value)
            for index, (key, value) in enumerate(query_items)
        ]
        urls.append(urlunparse(parsed._replace(query=urlencode(next_items))))
    return list(dict.fromkeys(urls))


def _query_url(url: str, updates: dict[str, str]) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.pop("p", None)
    for key in AULSS_FILTER_KEYS:
        query.pop(key, None)
    query.update(updates)
    return urlunparse(parsed._replace(query=urlencode(query)))


def collect_veneto_aulss_filter_urls(html: str, page_url: str) -> list[str]:
    """Discover the official server-side filters and their result pages."""

    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    parsed_page = urlparse(page_url)
    page_query = dict(parse_qsl(parsed_page.query, keep_blank_values=True))
    active_filters = {
        key: value
        for key, value in page_query.items()
        if key in AULSS_FILTER_KEYS and value
    }
    open_filter: dict[str, str] = {}
    state_select = soup.select_one('select[name="stato"]')
    if state_select is not None:
        for option in state_select.find_all("option"):
            if normalize_text(_text_for(option)) != "aperto":
                continue
            value = str(option.get("value") or "").strip()
            if value:
                open_filter = {"stato": value}
            break

    title_input = soup.select_one('input[name="titolo"]')
    if title_input is not None:
        urls.append(
            _query_url(page_url, {**open_filter, "titolo": "psicolog"})
        )

    for select_node in soup.select("select[name]"):
        key = str(select_node.get("name") or "")
        if key not in {"area", "figura"}:
            continue
        for option in select_node.find_all("option"):
            label = _text_for(option)
            value = str(option.get("value") or "").strip()
            normalized = normalize_text(label)
            if not value or not any(
                term in normalized for term in ("psicolog", "psicoterap", "neuropsicolog")
            ):
                continue
            urls.append(_query_url(page_url, {**open_filter, key: value}))

    if active_filters:
        for link in soup.find_all("a", href=True):
            candidate = urljoin(page_url, str(link["href"]))
            parsed_candidate = urlparse(candidate)
            if (
                parsed_candidate.netloc != parsed_page.netloc
                or parsed_candidate.path.rstrip("/") != parsed_page.path.rstrip("/")
            ):
                continue
            candidate_query = dict(
                parse_qsl(parsed_candidate.query, keep_blank_values=True)
            )
            if not candidate_query.get("p"):
                continue
            candidate_query.update(active_filters)
            urls.append(
                urlunparse(parsed_candidate._replace(query=urlencode(candidate_query)))
            )

    return list(dict.fromkeys(urls))[:MAX_AULSS_FILTER_URLS_PER_SOURCE]


def _deadline_from_text(text: str) -> datetime | None:
    normalized = normalize_text(text)
    if "scadenza graduatoria" in normalized:
        return None
    date_expression = (
        r"(?:[0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|"
        r"[0-9]{1,2}\s+[a-z]{3,12}\s+[0-9]{4})"
    )
    patterns = (
        rf"data\s+(?:e\s+ora\s+di\s+)?scadenza.{{0,80}}?({date_expression})",
        rf"scadenza(?:\s+domande)?.{{0,80}}?({date_expression})",
        rf"entro\s+il\s+({date_expression})",
        rf"termine.{{0,120}}?({date_expression})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_date(match.group(1))
    return None


def _publication_from_text(text: str) -> datetime | None:
    date_expression = (
        r"(?:[0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|"
        r"[0-9]{1,2}\s+[a-z]{3,12}\s+[0-9]{4})"
    )
    patterns = (
        rf"data\s+(?:di\s+)?pubblicazione.{{0,80}}?({date_expression})",
        rf"pubblicat[oa]\s+(?:il\s+)?({date_expression})",
        rf"data\s+inizio.{{0,80}}?({date_expression})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return parse_date(match.group(1))
    return None


def _title_supports_relevance(title: str, context: str) -> bool:
    if direct_psychology_match(title):
        return True
    normalized_title = normalize_text(title)
    return any(term in normalized_title for term in MULTI_PROFILE_TITLE_TERMS) and _is_relevant(
        context
    )


def _title_from_container(container: Any, fallback: str) -> str:
    if getattr(container, "name", None) == "a":
        title = _text_for(container)
        if len(title) >= 12:
            return title[:500]
    for selector in ("h1", "h2", "h3", "h4", "strong", "a[href]"):
        node = container.select_one(selector) if hasattr(container, "select_one") else None
        if node is None:
            continue
        title = _text_for(node)
        if len(title) >= 12:
            return title[:500]
    return fallback[:500]


def _first_useful_link(container: Any, page_url: str) -> str:
    if getattr(container, "name", None) == "a" and container.has_attr("href"):
        href = str(container["href"])
        if not href.startswith(("mailto:", "tel:", "javascript:", "#")):
            return urljoin(page_url, href)
    links = [
        link
        for link in container.find_all("a", href=True)
        if not str(link["href"]).startswith(("mailto:", "tel:", "javascript:", "#"))
    ]
    for link in links:
        href = str(link["href"])
        label = _text_for(link)
        if "/avvisi-e-concorsi/" in href or "/bandi-e-concorsi/" in href:
            return urljoin(page_url, href)
        if _is_relevant(label):
            return urljoin(page_url, href)
    for link in links:
        label = normalize_text(_text_for(link))
        href = str(link["href"])
        if label in {"news", "avvisi", "concorsi", "bandi"}:
            continue
        return urljoin(page_url, href)
    for link in container.find_all("a", href=True):
        href = str(link["href"])
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        return urljoin(page_url, href)
    return page_url


def _file_type(url: str, label: str) -> str | None:
    normalized = f"{url} {label}".lower()
    for extension in ("pdf", "docx", "doc", "odt", "zip"):
        if f".{extension}" in normalized or extension in normalized:
            return extension
    return None


def _looks_like_file(url: str) -> bool:
    lower = url.lower()
    return any(token in lower for token in (".pdf", ".doc", ".docx", ".odt", ".zip", "download"))


def _is_bad_detail_url(url: str) -> bool:
    lower = url.lower()
    parsed = urlparse(url)
    if any(key in SEARCH_QUERY_KEYS for key, _value in parse_qsl(parsed.query)):
        return True
    return any(
        token in lower
        for token in (
            "/page/",
            "/articoli/news/",
            "/articoli/news-avvisi/",
            "/category/",
            "facebook.com",
            "twitter.com",
            "whatsapp.com",
        )
    )


def _is_followup_title(title: str) -> bool:
    normalized = normalize_text(title)
    return any(term in normalized for term in FOLLOWUP_TITLE_TERMS)


def _external_id(source: Source, title: str, official_url: str) -> str:
    raw = "|".join([source.id, normalize_text(title), normalize_text(official_url)])
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _better_title(title: str, description: str, source: Source) -> str:
    normalized_title = normalize_text(title)
    normalized_org = normalize_text(source.organization or source.name)
    if (
        len(title) >= 16
        and normalized_title not in normalized_org
        and normalized_org not in normalized_title
    ):
        return title[:500]
    for sentence in re.split(r"(?<=[.!?])\s+|\s+Tipo\s+di\s+documento", description):
        clean = _clean_text(sentence)
        if len(clean) >= 24 and _is_relevant(clean):
            return clean[:500]
    return title[:500]


def _attachment_from_url(label: str, url: str) -> dict[str, str | None]:
    title = label or url.rsplit("/", 1)[-1]
    return {"title": title[:255], "url": url, "file_type": _file_type(url, title)}


def _html_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _clean_text(BeautifulSoup(value, "html.parser").get_text(" ", strip=True))


def _aulss4_attachments(attributes: dict[str, Any]) -> tuple[dict[str, str | None], ...]:
    attachments: list[dict[str, str | None]] = []
    raw_attachments = attributes.get("mul_association_allegati")
    if not isinstance(raw_attachments, list):
        return ()
    for item in raw_attachments:
        if not isinstance(item, dict):
            continue
        details = item.get("dyn_str_association_allegati_details")
        details = details if isinstance(details, dict) else {}
        attachment_id = item.get("dyn_str_association_allegati_uuid") or details.get(
            "sourceId"
        )
        if not attachment_id:
            continue
        label = str(
            item.get("dyn_str_autobind_allegati_name")
            or details.get("name")
            or "Allegato"
        )
        normalized = normalize_text(label)
        if any(term in normalized for term in SKIP_ATTACHMENT_TERMS):
            continue
        url = AULSS4_DOWNLOAD_URL.format(attachment_id)
        attachments.append(_attachment_from_url(label, url))
    unique = {str(attachment["url"]): attachment for attachment in attachments}
    return tuple(unique.values())[:6]


def parse_aulss4_api_records(
    source: Source,
    payload: dict[str, Any],
) -> list[TargetHealthRecord]:
    page = payload.get("page")
    entities = page.get("entities") if isinstance(page, dict) else None
    if not isinstance(entities, list):
        return []

    records_by_url: dict[str, TargetHealthRecord] = {}
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        attributes = entity.get("attributes")
        if not isinstance(attributes, dict):
            continue
        title = _clean_text(
            str(
                attributes.get("dyn_str_oggetto_bando")
                or attributes.get("sys_title")
                or entity.get("name")
                or ""
            )
        )
        description = _clean_text(
            " ".join(
                part
                for part in (
                    title,
                    _html_text(attributes.get("myp_noteinizio")),
                    _html_text(attributes.get("dyn_str_altri_collegamenti")),
                )
                if part
            )
        )[:2400]
        if not title or _is_followup_title(title) or not _is_relevant(description):
            continue

        canonical = attributes.get("sys_canonical_url")
        slug = attributes.get("sys_slug") or entity.get("slug")
        if canonical:
            official_url = urljoin("https://www.aulss4.veneto.it", str(canonical))
        elif slug:
            official_url = urljoin(
                "https://www.aulss4.veneto.it",
                f"/amministrazionetrasparente-info/{slug}",
            )
        else:
            continue

        records_by_url[official_url] = TargetHealthRecord(
            external_id=_external_id(source, title, official_url),
            title=title[:500],
            description=description,
            official_url=official_url,
            published_at=parse_date(entity.get("firstPublishedAt")),
            deadline=parse_date(attributes.get("def_date_scadenza_bando")),
            attachments=_aulss4_attachments(attributes),
        )
        if len(records_by_url) >= MAX_RECORDS_PER_SOURCE:
            break
    return list(records_by_url.values())


def _fetch_aulss4_api_records(
    client: httpx.Client,
    source: Source,
) -> list[TargetHealthRecord]:
    records_by_url: dict[str, TargetHealthRecord] = {}
    errors: list[Exception] = []
    successful_queries = 0
    for parent in AULSS4_CONTENT_PARENTS:
        try:
            response = client.get(
                AULSS4_API_URL,
                params={
                    "type": "AT_myp_bandi_concorso",
                    "pageIndex": "1",
                    "pageSize": "500",
                    "parent": parent,
                    "includeSubFolders": "true",
                    "showPublicationEnded": "true",
                    "resolveAttachments": "true",
                    "onlyNotHidden": "true",
                    "sortBy": "modifiedAt",
                    "desc": "true",
                },
            )
            response.raise_for_status()
            successful_queries += 1
            for record in parse_aulss4_api_records(source, response.json()):
                records_by_url[record.official_url] = record
        except Exception as exc:
            errors.append(exc)
    if not successful_queries and errors:
        raise errors[-1]
    return sorted(
        records_by_url.values(),
        key=lambda record: (
            record.published_at.timestamp() if record.published_at else 0.0,
            record.deadline.timestamp() if record.deadline else 0.0,
        ),
        reverse=True,
    )[:MAX_RECORDS_PER_SOURCE]


def _attachments_from_soup(
    soup: BeautifulSoup,
    detail_url: str,
) -> tuple[dict[str, str | None], ...]:
    attachments: list[dict[str, str | None]] = []
    for link in soup.find_all("a", href=True):
        href = urljoin(detail_url, str(link["href"]))
        label = _text_for(link)
        normalized = normalize_text(f"{label} {href}")
        if not _looks_like_file(href):
            continue
        if any(term in normalized for term in SKIP_ATTACHMENT_TERMS):
            continue
        attachments.append(_attachment_from_url(label, href))
    unique = {str(attachment["url"]): attachment for attachment in attachments}
    return tuple(unique.values())[:6]


def parse_target_health_records(
    source: Source,
    html: str,
    page_url: str,
) -> list[TargetHealthRecord]:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("script, style, noscript, nav, footer"):
        node.decompose()

    selectors = (
        "article",
        "tr",
        "li",
        ".card",
        ".scheda-sito",
        ".views-row",
        ".post",
        ".elementor-post",
        ".search-result",
        ".news-item",
        ".item",
        "a[href]",
    )
    records_by_url: dict[str, TargetHealthRecord] = {}
    for selector in selectors:
        for container in soup.select(selector):
            text = _text_for(container)
            if not (24 <= len(text) <= 3500):
                continue
            if not _is_relevant(text):
                continue
            official_url = _first_useful_link(container, page_url)
            if _is_bad_detail_url(official_url):
                continue
            title = _title_from_container(container, text)
            if _is_followup_title(title) or not _title_supports_relevance(title, text):
                continue
            attachments: tuple[dict[str, str | None], ...] = ()
            if _looks_like_file(official_url):
                attachments = (_attachment_from_url(title, official_url),)
            candidate = TargetHealthRecord(
                external_id=_external_id(source, title, official_url),
                title=title,
                description=text[:2400],
                official_url=official_url,
                published_at=_publication_from_text(text),
                deadline=_deadline_from_text(text),
                attachments=attachments,
            )
            existing = records_by_url.get(official_url)
            if existing is None or (
                candidate.deadline is not None,
                len(candidate.description),
            ) > (
                existing.deadline is not None,
                len(existing.description),
            ):
                records_by_url[official_url] = candidate
    return list(records_by_url.values())[:MAX_RECORDS_PER_SOURCE]


def collect_target_health_detail_urls(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = str(link["href"])
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        parent = link.parent
        context = _text_for(link)
        depth = 0
        while parent is not None and depth < 4:
            if not getattr(parent, "name", None) or parent.name in {
                "[document]",
                "body",
                "html",
            }:
                break
            context = f"{context} {_text_for(parent)}"
            if len(context) > 2500:
                break
            parent = parent.parent
            depth += 1
        if not _is_relevant(context):
            continue
        if _is_followup_title(context[:500]):
            continue
        url = urljoin(page_url, href)
        if _is_bad_detail_url(url):
            continue
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
        if len(urls) >= MAX_DETAIL_URLS_PER_SOURCE:
            break
    return urls


def parse_target_health_detail(
    source: Source,
    listing_record: TargetHealthRecord | None,
    html: str,
    detail_url: str,
) -> TargetHealthRecord | None:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("script, style, noscript, nav, footer"):
        node.decompose()
    body = soup.select_one("main, article, .entry-content, .content, .item-page") or soup
    description = _text_for(body)[:2400]
    title = ""
    for selector in ("h1", "h2", "h3", "title"):
        node = soup.select_one(selector)
        if node is not None:
            title = _text_for(node)
            break
    if not title and listing_record is not None:
        title = listing_record.title
    if not title:
        title = description[:240]
    title = _better_title(title, description, source)
    if _is_followup_title(title) or not _title_supports_relevance(title, description):
        return None
    combined = f"{title} {description}"
    if not _is_relevant(combined):
        return None
    return TargetHealthRecord(
        external_id=_external_id(source, title, detail_url),
        title=title[:500],
        description=description,
        official_url=detail_url,
        published_at=_publication_from_text(description)
        or (listing_record.published_at if listing_record else None),
        deadline=_deadline_from_text(description)
        or (listing_record.deadline if listing_record else None),
        attachments=_attachments_from_soup(soup, detail_url),
    )


def _align_existing_by_official_url(
    db: Session,
    source: Source,
    record: TargetHealthRecord,
) -> None:
    existing = db.scalar(
        select(Opportunity).where(
            Opportunity.source_id == source.id,
            Opportunity.official_url == record.official_url,
        )
    )
    if existing is not None:
        existing.external_id = record.external_id
        db.flush()


def _payload(db: Session, source: Source, record: TargetHealthRecord) -> dict[str, Any]:
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
        "region": source.region,
        "original_location": source.region,
        "status": status,
        "published_at": record.published_at,
        "deadline": record.deadline,
        "last_seen_at": datetime.now(UTC),
        "requirements": classification.requirements,
        "application_mode": f"Consultare la scheda ufficiale: {source.name}.",
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


def _sources(db: Session) -> list[Source]:
    ensure_source_catalog(db)
    sources = list(
        db.scalars(
            select(Source)
            .where(Source.name.in_(TARGET_HEALTH_SOURCE_NAMES))
            .order_by(Source.region, Source.name)
        )
    )
    return source_rotation_batch(
        sources,
        batch_size=max(settings.target_health_sources_per_run, len(sources)),
        group_name="fonti sanitarie mirate (tutte)",
    )


def run_target_health_html_import(db: Session) -> ImportResult:
    run = ImportRun(source_id=None, status="running")
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
            import_deadline = (
                time.monotonic() + settings.target_health_budget_seconds
                if settings.target_health_budget_seconds > 0
                else None
            )
            for source in _sources(db):
                attempt = start_source_attempt(db, source)
                try:
                    records_by_url: dict[str, TargetHealthRecord] = {}
                    if source.name == AULSS4_SOURCE_NAME:
                        records_by_url.update(
                            {
                                record.official_url: record
                                for record in _fetch_aulss4_api_records(client, source)
                            }
                        )
                    else:
                        source_urls = _source_search_urls(source.base_url)
                        seen_source_urls: set[str] = set()
                        source_index = 0
                        while source_index < len(source_urls):
                            source_url = source_urls[source_index]
                            source_index += 1
                            if source_url in seen_source_urls:
                                continue
                            seen_source_urls.add(source_url)
                            if (
                                source_index > 1
                                and source.name not in VENETO_AULSS_SOURCE_NAMES
                                and import_deadline is not None
                                and time.monotonic() > import_deadline
                            ):
                                break
                            response = client.get(source_url)
                            response.raise_for_status()
                            if not _is_textual_response(response):
                                skipped += 1
                                attempt.skipped()
                                continue

                            if source.name in VENETO_AULSS_SOURCE_NAMES:
                                for discovered_url in collect_veneto_aulss_filter_urls(
                                    response.text,
                                    str(response.url),
                                ):
                                    if (
                                        discovered_url not in seen_source_urls
                                        and discovered_url not in source_urls
                                        and len(source_urls)
                                        < MAX_AULSS_FILTER_URLS_PER_SOURCE
                                    ):
                                        source_urls.append(discovered_url)

                            records_by_url.update(
                                {
                                    record.official_url: record
                                    for record in parse_target_health_records(
                                        source,
                                        response.text,
                                        str(response.url),
                                    )
                                }
                            )
                            for detail_url in collect_target_health_detail_urls(
                                response.text,
                                str(response.url),
                            ):
                                if (
                                    import_deadline is not None
                                    and time.monotonic() > import_deadline
                                ):
                                    break
                                if _looks_like_file(detail_url):
                                    continue
                                try:
                                    detail = client.get(detail_url)
                                    detail.raise_for_status()
                                except Exception:
                                    skipped += 1
                                    attempt.skipped()
                                    continue
                                if not _is_textual_response(detail):
                                    skipped += 1
                                    attempt.skipped()
                                    continue
                                detail_record = parse_target_health_detail(
                                    source,
                                    records_by_url.get(detail_url),
                                    detail.text,
                                    str(detail.url),
                                )
                                if detail_record is not None:
                                    records_by_url[detail_record.official_url] = detail_record
                                if len(records_by_url) >= MAX_RECORDS_PER_SOURCE:
                                    break
                            if len(records_by_url) >= MAX_RECORDS_PER_SOURCE:
                                break

                    for record in records_by_url.values():
                        _align_existing_by_official_url(db, source, record)
                        if upsert_opportunity(
                            db,
                            payload=_payload(db, source, record),
                            attachments=list(record.attachments),
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
