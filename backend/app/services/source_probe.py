from __future__ import annotations

from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.importers.inail import INAIL_SOURCE_NAME, build_inail_ssl_context
from app.models import Source
from app.source_catalog import VERIFIED_SOURCE_CATALOG


def _probe_error_status(exc: Exception) -> str:
    if isinstance(exc, httpx.TimeoutException):
        return "timeout-review"
    error = str(exc).lower()
    if "certificate_verify_failed" in error or (
        "ssl" in error and ("handshake" in error or "tls" in error)
    ):
        return "tls-review"
    return "unreachable"


def _probe_success_status(source: Source) -> str:
    return "active" if source.status == "active" else "reachable"


def _probe_failure_status(source: Source, exc: Exception) -> str:
    return _probe_error_status(exc)


def source_refresh_order(sources: list[Source]) -> list[Source]:
    def key(source: Source) -> tuple[int, float, str]:
        if source.last_success_at is None:
            return (0, 0.0, source.name.lower())
        last_success = source.last_success_at
        if last_success.tzinfo is None:
            last_success = last_success.replace(tzinfo=UTC)
        return (1, last_success.timestamp(), source.name.lower())

    return sorted(sources, key=key)


def ensure_source_catalog(db: Session) -> list[Source]:
    sources: list[Source] = []
    for candidate in VERIFIED_SOURCE_CATALOG:
        source = db.scalar(select(Source).where(Source.name == candidate["name"]))
        if source is None:
            source = Source(**candidate, status="catalogued")
            db.add(source)
            db.flush()
        else:
            for field, value in candidate.items():
                setattr(source, field, value)
        sources.append(source)
    db.commit()
    return sources


def probe_source_catalog(db: Session) -> list[Source]:
    sources = ensure_source_catalog(db)
    common_options = {
        "timeout": 20,
        "follow_redirects": True,
        "headers": {"User-Agent": "BandiPsicologiaMVP/0.1 (+probe fonti pubbliche)"},
    }
    with httpx.Client(
        timeout=20,
        verify=settings.source_probe_verify_tls,
        follow_redirects=True,
        headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+probe fonti pubbliche)"},
    ) as client, httpx.Client(
        verify=(
            build_inail_ssl_context()
            if settings.source_probe_verify_tls
            else False
        ),
        **common_options,
    ) as inail_client:
        for source in sources:
            try:
                probe_client = inail_client if source.name == INAIL_SOURCE_NAME else client
                response = probe_client.get(source.base_url)
                response.raise_for_status()
                source.status = _probe_success_status(source)
                source.last_success_at = datetime.now(UTC)
                source.last_error = None
            except Exception as exc:
                source.status = _probe_failure_status(source, exc)
                source.last_error = str(exc)
    db.commit()
    return sources
