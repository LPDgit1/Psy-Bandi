from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Opportunity
from app.services.classifier import normalize_text
from app.services.dates import infer_status

AUTO_HIDE_EXPIRED_NOTE = "Nascosto automaticamente: scadenza superata."
AUTO_HIDE_UNDATED_REVIEW_NOTE = (
    "Nascosto automaticamente: scadenza assente da fonte di ricerca o atto non iniziale."
)
AUTO_HIDE_NON_OPPORTUNITY_NOTE = (
    "Nascosto automaticamente: atto non candidabile o graduatoria/revoca."
)
AUTO_HIDE_EXACT_URL_DUPLICATE_NOTE = (
    "Nascosto automaticamente: duplicato della stessa scheda ufficiale nella fonte."
)
SEARCH_QUERY_KEYS = {"combine", "q", "s", "search", "text"}
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
)
NON_OPPORTUNITY_TITLE_TERMS = (
    "affidamento diretto",
    "altre informazioni",
    "annullamento concorso",
    "centro di ascolto psicologico",
    "esaurita",
    "fornitura",
    "graduatorie vigenti",
    "revoca concorso",
    "risultati della ricerca",
    "scadenza graduatoria",
)
GENERIC_LISTING_TITLES = (
    "bandi di concorso",
    "concorsi",
    "concorsi e selezioni",
)
NON_OPPORTUNITY_CONTENT_TERMS = (
    "approvazione atti della commissione",
    "approvazione graduatoria",
    "conferimento incarico al dott",
    "graduatoria finale di merito",
    "presa atto dell esito",
)


def _notes_with_auto_hide(existing: str | None) -> str:
    if not existing:
        return AUTO_HIDE_EXPIRED_NOTE
    if AUTO_HIDE_EXPIRED_NOTE in existing:
        return existing
    return f"{existing}\n{AUTO_HIDE_EXPIRED_NOTE}"


def _notes_with_undated_auto_hide(existing: str | None) -> str:
    if not existing:
        return AUTO_HIDE_UNDATED_REVIEW_NOTE
    if AUTO_HIDE_UNDATED_REVIEW_NOTE in existing:
        return existing
    return f"{existing}\n{AUTO_HIDE_UNDATED_REVIEW_NOTE}"


def _notes_with_non_opportunity_auto_hide(existing: str | None) -> str:
    if not existing:
        return AUTO_HIDE_NON_OPPORTUNITY_NOTE
    if AUTO_HIDE_NON_OPPORTUNITY_NOTE in existing:
        return existing
    return f"{existing}\n{AUTO_HIDE_NON_OPPORTUNITY_NOTE}"


def _can_restore_after_deadline_change(opportunity: Opportunity) -> bool:
    if opportunity.editorial_status != "hidden":
        return False
    notes = {
        line.strip()
        for line in (opportunity.editorial_notes or "").splitlines()
        if line.strip()
    }
    return bool(notes) and notes.issubset(
        {AUTO_HIDE_EXPIRED_NOTE, AUTO_HIDE_UNDATED_REVIEW_NOTE}
    )


def _is_search_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    return any(key in SEARCH_QUERY_KEYS for key, _value in parse_qsl(parsed.query))


def _is_undated_review_to_hide(opportunity: Opportunity) -> bool:
    if opportunity.status != "review" or opportunity.deadline is not None:
        return False
    title = normalize_text(opportunity.title)
    official_url = normalize_text(opportunity.official_url)
    source_search_url = _is_search_url(
        opportunity.source.base_url if opportunity.source else None
    )
    if source_search_url:
        return True
    if _is_search_url(opportunity.official_url):
        return True
    if any(term in title for term in FOLLOWUP_TITLE_TERMS):
        return True
    if any(term in title for term in NON_OPPORTUNITY_TITLE_TERMS):
        return True
    if any(term in official_url for term in NON_OPPORTUNITY_TITLE_TERMS):
        return True
    return title in GENERIC_LISTING_TITLES or any(
        title.startswith(f"{term} ") for term in GENERIC_LISTING_TITLES
    )


def _is_non_opportunity_notice(opportunity: Opportunity) -> bool:
    title = normalize_text(opportunity.title)
    official_url = normalize_text(opportunity.official_url)
    description = normalize_text(opportunity.description)
    if any(term in title for term in NON_OPPORTUNITY_TITLE_TERMS):
        return True
    if any(term in official_url for term in NON_OPPORTUNITY_TITLE_TERMS):
        return True
    if any(term in description for term in NON_OPPORTUNITY_CONTENT_TERMS):
        return True
    return title in GENERIC_LISTING_TITLES or any(
        title.startswith(f"{term} ") for term in GENERIC_LISTING_TITLES
    )


def _normalized_url(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    return f"{parsed.netloc.lower()}{parsed.path.rstrip('/')}{parsed.query}"


def _hide_exact_url_duplicates(opportunities: list[Opportunity]) -> int:
    groups: dict[tuple[str, str], list[Opportunity]] = {}
    for opportunity in opportunities:
        if opportunity.editorial_status != "approved" or not opportunity.source_id:
            continue
        official_url = _normalized_url(opportunity.official_url)
        source_url = _normalized_url(
            opportunity.source.base_url if opportunity.source else None
        )
        if not official_url or official_url == source_url or _is_search_url(
            opportunity.official_url
        ):
            continue
        groups.setdefault((opportunity.source_id, official_url), []).append(opportunity)

    hidden = 0
    for duplicates in groups.values():
        if len(duplicates) < 2:
            continue
        keep = max(
            duplicates,
            key=lambda candidate: (
                candidate.status in {"open", "closing_soon"},
                candidate.deadline is not None,
                candidate.deadline or datetime.min.replace(tzinfo=UTC),
                len(candidate.description or ""),
            ),
        )
        for duplicate in duplicates:
            if duplicate.id == keep.id:
                continue
            duplicate.editorial_status = "hidden"
            duplicate.editorial_notes = AUTO_HIDE_EXACT_URL_DUPLICATE_NOTE
            hidden += 1
    return hidden


def refresh_deadline_statuses(db: Session, *, now: datetime | None = None) -> int:
    current = now or datetime.now(UTC)
    changed = 0
    opportunities = db.scalars(select(Opportunity)).all()
    for opportunity in opportunities:
        if opportunity.deadline is None:
            if (
                opportunity.editorial_status == "approved"
                and _is_undated_review_to_hide(opportunity)
            ):
                opportunity.editorial_status = "hidden"
                opportunity.editorial_notes = _notes_with_undated_auto_hide(
                    opportunity.editorial_notes
                )
                changed += 1
            continue
        status = infer_status(opportunity.deadline, now=current)
        if opportunity.status != status:
            opportunity.status = status
            changed += 1
        if status != "closed" and _can_restore_after_deadline_change(opportunity):
            opportunity.editorial_status = "approved"
            opportunity.editorial_notes = None
            changed += 1
        if (
            opportunity.editorial_status == "approved"
            and _is_non_opportunity_notice(opportunity)
        ):
            opportunity.editorial_status = "hidden"
            opportunity.editorial_notes = _notes_with_non_opportunity_auto_hide(
                opportunity.editorial_notes
            )
            changed += 1
            continue
        if status == "closed" and opportunity.editorial_status == "approved":
            opportunity.editorial_status = "hidden"
            opportunity.editorial_notes = _notes_with_auto_hide(
                opportunity.editorial_notes
            )
            changed += 1
    changed += _hide_exact_url_duplicates(opportunities)
    if changed:
        db.commit()
    return changed
