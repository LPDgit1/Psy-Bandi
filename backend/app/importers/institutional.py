from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Attachment, Opportunity
from app.services.classifier import normalize_text
from app.services.dedupe import is_probable_duplicate

AUTO_EXCLUSION_PREFIX = "Escluso automaticamente:"
AUTOMATIC_EDITORIAL_PREFIXES = (
    AUTO_EXCLUSION_PREFIX,
    "Nascosto automaticamente:",
)
PSYCHOLOGY_SEARCH_TERMS = (
    "psicolog",
    "psicoterap",
    "neuropsicolog",
    "psicoterapia",
    "psicologo di base",
    "psicologo cure primarie",
    "psicologia di base",
    "psicologia cure primarie",
    "sportello ascolto",
    "supporto psicologico",
    "sostegno psicologico",
    "consulenza psicologica",
    "servizio psicologico",
    "lm-51",
    "lm 51",
    "58/s",
    "albo psicologi",
    "psicologia clinica",
    "psicodiagnostic",
    "valutazione psicologica",
    "test neuropsicologici",
    "riabilitazione cognitiva",
    "psicopedagog",
    "psicoeduc",
    "psicosocial",
    "salute mentale",
)
PSYCHOLOGY_QUERY_TERMS = (
    "psicolog",
    "psicoterap",
    "neuropsicolog",
    "lm-51",
    "psicodiagnostic",
    "psicoeduc",
    "psicosocial",
    "riabilitazione cognitiva",
    "salute mentale",
)
PROFESSIONAL_PATTERN = re.compile(
    r"\bpsicolog(?:o|a|i|he|e)\b|"
    r"\bpsicoterapeut(?:a|e|i)\b|"
    r"\bneuropsicolog(?:o|a|i|he|e)\b"
)
QUALIFYING_PSYCHOLOGY_PATTERN = re.compile(
    r"\blaurea(?: magistrale)? in psicologia\b|"
    r"\blaure[ae][^.]{0,80}\bpsicolog|"
    r"\blm\s*[- ]?\s*51\b|"
    r"\bclasse\s*(?:lm\s*[- ]?\s*51|58\s*/?\s*s)\b|"
    r"\bspecializzazione (?:in )?psicoterapia\b|"
    r"\bdisciplina psicoterapia\b|"
    r"\bdisciplina (?:psicologia|neuropsicologia)\b|"
    r"\bpsicologia (?:clinica|dello sviluppo|del lavoro|scolastica|giuridica|"
    r"di base|delle cure primarie|ospedaliera|della salute|di comunita|"
    r"dell emergenza)\b|"
    r"\bpsicodiagnostic\w*\b|"
    r"\bvalutazion[ei] psicologic\w*\b|"
    r"\btest neuropsicologic\w*\b|"
    r"\bvalutazione neuropsicologic\w*\b|"
    r"\briabilitazione cognitiv\w*\b|"
    r"\bpsicopedagogic\w*\b|"
    r"\bpsicoeducativ\w*\b|"
    r"\bpsicosocial\w*\b|"
    r"\b(?:espert[oaie]|professionist[ai]|consulent[ei])[^.]{0,80}\bpsicologic\w*\b|"
    r"\b(?:avviso|bando|incarico|collaborazione|procedura|progetto|selezione)"
    r"[^.]{0,120}\b(?:assistenza|consulenza|sostegno|supporto|sportello|servizio|intervento)"
    r"[^.]{0,100}\bpsicologic\w*\b|"
    r"\babilitazion[ea][^.]{0,80}\bpsicolog|"
    r"\balbo (?:professionale )?degli psicologi\b|"
    r"\biscrizione all albo[^.]{0,80}\bpsicolog"
)


def direct_psychology_match(*parts: str | None) -> bool:
    normalized = normalize_text(" ".join(part or "" for part in parts))
    return bool(
        PROFESSIONAL_PATTERN.search(normalized)
        or QUALIFYING_PSYCHOLOGY_PATTERN.search(normalized)
    )


def professional_role_match(*parts: str | None) -> bool:
    normalized = normalize_text(" ".join(part or "" for part in parts))
    return bool(PROFESSIONAL_PATTERN.search(normalized))


def is_manually_hidden(opportunity: Opportunity) -> bool:
    if opportunity.editorial_status != "hidden":
        return False
    notes = (opportunity.editorial_notes or "").lstrip()
    return not notes.startswith(AUTOMATIC_EDITORIAL_PREFIXES)


def find_probable_duplicate(
    db: Session,
    *,
    source_id: str,
    title: str,
    organization: str,
    deadline: datetime | None,
) -> Opportunity | None:
    candidates = db.scalars(
        select(Opportunity).where(
            Opportunity.source_id != source_id,
            Opportunity.editorial_status == "approved",
            Opportunity.status != "closed",
        )
    ).all()
    for candidate in candidates:
        if deadline and candidate.deadline and deadline.date() != candidate.deadline.date():
            continue
        if is_probable_duplicate(
            title,
            organization,
            candidate.title,
            candidate.organization,
        ):
            return candidate
    return None


def editorial_visibility(
    *,
    status: str,
    duplicate: Opportunity | None,
) -> tuple[str, str | None]:
    if duplicate:
        return (
            "hidden",
            f"{AUTO_EXCLUSION_PREFIX} probabile duplicato di {duplicate.official_url}",
        )
    if status == "closed":
        return ("hidden", f"{AUTO_EXCLUSION_PREFIX} procedura scaduta.")
    return ("approved", None)


def upsert_opportunity(
    db: Session,
    *,
    payload: dict[str, Any],
    attachments: list[dict[str, str | None]],
) -> bool:
    existing = db.scalar(
        select(Opportunity).where(
            Opportunity.source_id == payload["source_id"],
            Opportunity.external_id == payload["external_id"],
        )
    )
    manually_hidden = existing is not None and is_manually_hidden(existing)
    previous_notes = existing.editorial_notes if existing else None

    if existing is None:
        existing = Opportunity(**payload)
        db.add(existing)
        created = True
    else:
        for key, value in payload.items():
            setattr(existing, key, value)
        created = False

    if manually_hidden:
        existing.editorial_status = "hidden"
        existing.editorial_notes = previous_notes

    existing.attachments.clear()
    existing.attachments.extend(
        Attachment(
            title=str(attachment["title"]),
            url=str(attachment["url"]),
            file_type=attachment.get("file_type"),
        )
        for attachment in attachments
    )
    return created
