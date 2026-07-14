from __future__ import annotations

import math
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.importers.inail import INAIL_SOURCE_NAME, build_inail_ssl_context
from app.models import Source
from app.source_catalog import VERIFIED_SOURCE_CATALOG

ROTATION_WINDOW_SECONDS = 12 * 60 * 60


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


def source_rotation_slot(now: datetime | None = None) -> int:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return int(current.timestamp()) // ROTATION_WINDOW_SECONDS


def source_rotation_batch(
    sources: list[Source],
    *,
    batch_size: int,
    group_name: str,
    slot: int | None = None,
) -> list[Source]:
    ordered = sorted(sources, key=lambda source: source.name.casefold())
    total = len(ordered)
    selected_slot = source_rotation_slot() if slot is None else slot
    effective_size = min(max(batch_size, 0), total)

    if not total or not effective_size:
        selected: list[Source] = []
        start = 0
    elif effective_size == total:
        selected = ordered
        start = 0
    else:
        start = (selected_slot * effective_size) % total
        selected = [ordered[(start + offset) % total] for offset in range(effective_size)]

    cycle_runs = math.ceil(total / effective_size) if effective_size else 0
    message = (
        f"Rotazione {group_name}: slot={selected_slot}, "
        f"selezionate={len(selected)}/{total}, partenza={start}, "
        f"copertura_teorica={cycle_runs} esecuzioni."
    )
    print(message)

    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        path = Path(summary_path)
        try:
            with path.open("a", encoding="utf-8") as summary:
                summary.write(
                    f"### Rotazione {group_name}\n\n"
                    f"Selezionate **{len(selected)}** fonti su **{total}** nello slot "
                    f"`{selected_slot}`; copertura teorica entro "
                    f"**{cycle_runs} esecuzioni**.\n\n"
                )
        except OSError as exc:
            print(f"Riepilogo GitHub non scrivibile per {group_name}: {exc}")

    return selected


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
    with (
        httpx.Client(
            timeout=20,
            verify=settings.source_probe_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": "BandiPsicologiaMVP/0.1 (+probe fonti pubbliche)"},
        ) as client,
        httpx.Client(
            verify=(build_inail_ssl_context() if settings.source_probe_verify_tls else False),
            **common_options,
        ) as inail_client,
    ):
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
