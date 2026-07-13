from __future__ import annotations

import hashlib
from difflib import SequenceMatcher

from app.services.classifier import normalize_text


def content_hash(*parts: str | None) -> str:
    payload = "\n".join(part or "" for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def external_key(source_key: str, external_id: str | None, official_url: str | None) -> str:
    raw = "|".join([source_key, external_id or "", official_url or ""])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def opportunity_fingerprint(title: str, organization: str, deadline: str | None) -> str:
    normalized = "|".join(
        [
            normalize_text(title),
            normalize_text(organization),
            normalize_text(deadline),
        ]
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


def is_probable_duplicate(
    left_title: str,
    left_organization: str,
    right_title: str,
    right_organization: str,
    threshold: float = 0.88,
) -> bool:
    title_similarity = similarity(left_title, right_title)
    organization_similarity = similarity(left_organization, right_organization)
    return title_similarity >= threshold and organization_similarity >= 0.75

