from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from typing import Any

import httpx
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.importers.catalog_sources import (
    CATALOG_SOURCE_TYPES,
    DEEP_ADAPTER_SOURCE_TYPES,
    SPECIFIC_ADAPTER_SOURCE_NAMES,
)
from app.importers.inpa import INPA_SOURCE_NAME
from app.importers.target_health_html import TARGET_HEALTH_SOURCE_NAMES
from app.models import Opportunity, Source

CHALLENGE_MARKERS = (
    "botmanager_support@radware.com",
    "captcha",
    "enable javascript and cookies",
    "perfdrive.com",
)
OPPORTUNITY_MARKERS = ("avviso", "bando", "concorso", "incarico", "selezione")
PSYCHOLOGY_MARKERS = ("psicolog", "psicoterap", "neuropsicolog", "lm-51")


@dataclass(frozen=True)
class ProbeResult:
    source_id: str
    name: str
    adapter_family: str
    status: str
    http_status: int | None
    final_url: str | None
    has_opportunity_markers: bool
    has_psychology_markers: bool
    error: str | None = None


def adapter_family(source: Source) -> str:
    if source.status == "retired":
        return "retired"
    if source.name == INPA_SOURCE_NAME:
        return "inpa-api"
    if source.source_type == "puglia-aol-api":
        return "puglia-aol-api"
    if source.name in TARGET_HEALTH_SOURCE_NAMES:
        return "target-health-html"
    if source.name in SPECIFIC_ADAPTER_SOURCE_NAMES:
        return "dedicated"
    if source.source_type in DEEP_ADAPTER_SOURCE_TYPES:
        return "deep-html"
    if source.source_type in CATALOG_SOURCE_TYPES:
        return "catalog-html"
    if "review" in source.source_type or "review" in source.import_method:
        return "access-review"
    return "unassigned"


def _probe(source: Source, *, timeout: float) -> ProbeResult:
    family = adapter_family(source)
    try:
        response = httpx.get(
            source.base_url,
            timeout=httpx.Timeout(timeout, connect=min(timeout, 5)),
            verify=settings.source_probe_verify_tls,
            follow_redirects=True,
            headers={"User-Agent": "BandiPsicologiaAudit/1.0 (+fonti pubbliche)"},
        )
        content_type = response.headers.get("content-type", "").lower()
        text = response.text[:250_000].lower() if "text" in content_type else ""
        final_url = str(response.url)
        challenge_text = f"{final_url.lower()} {text[:30_000]}"
        challenged = any(marker in challenge_text for marker in CHALLENGE_MARKERS)
        if challenged:
            status = "access-challenge"
        elif response.is_error:
            status = "http-error"
        else:
            status = "reachable"
        return ProbeResult(
            source_id=source.id,
            name=source.name,
            adapter_family=family,
            status=status,
            http_status=response.status_code,
            final_url=final_url,
            has_opportunity_markers=any(marker in text for marker in OPPORTUNITY_MARKERS),
            has_psychology_markers=any(marker in text for marker in PSYCHOLOGY_MARKERS),
        )
    except Exception as exc:
        return ProbeResult(
            source_id=source.id,
            name=source.name,
            adapter_family=family,
            status="connection-error",
            http_status=None,
            final_url=None,
            has_opportunity_markers=False,
            has_psychology_markers=False,
            error=str(exc)[:500],
        )


def run_audit(*, workers: int, timeout: float) -> dict[str, Any]:
    with SessionLocal() as db:
        sources = list(db.scalars(select(Source).order_by(Source.name)))
        opportunity_counts = dict(
            db.execute(
                select(Opportunity.source_id, func.count(Opportunity.id)).group_by(
                    Opportunity.source_id
                )
            ).all()
        )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(lambda source: _probe(source, timeout=timeout), sources))

    failures = [result for result in results if result.status != "reachable"]
    zero_result_sources = [
        source.name for source in sources if opportunity_counts.get(source.id, 0) == 0
    ]
    return {
        "source_count": len(sources),
        "adapter_families": dict(Counter(result.adapter_family for result in results)),
        "probe_statuses": dict(Counter(result.status for result in results)),
        "sources_with_opportunities": len(sources) - len(zero_result_sources),
        "sources_without_opportunities": len(zero_result_sources),
        "unassigned_sources": [
            result.name for result in results if result.adapter_family == "unassigned"
        ],
        "failures": [asdict(result) for result in failures],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit read-only delle fonti catalogate.")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    report = run_audit(
        workers=max(1, min(args.workers, 32)),
        timeout=max(2, min(args.timeout, 30)),
    )
    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
