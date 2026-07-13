from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.importers.base import ImportResult
from app.models import ImportRun, Opportunity, Source
from app.seed_data import SAMPLE_OPPORTUNITIES, SAMPLE_SOURCE
from app.services.classifier import build_search_text, classify_text, normalize_text
from app.services.dates import infer_status, parse_date
from app.services.dedupe import content_hash


def _ensure_source(db: Session) -> Source:
    source = db.scalar(select(Source).where(Source.name == SAMPLE_SOURCE["name"]))
    if source:
        return source

    source = Source(**SAMPLE_SOURCE)
    db.add(source)
    db.flush()
    return source


def run_sample_import(db: Session) -> ImportResult:
    source = _ensure_source(db)
    run = ImportRun(source_id=source.id, status="running")
    db.add(run)
    db.flush()

    created = 0
    updated = 0
    skipped = 0

    try:
        for raw in SAMPLE_OPPORTUNITIES:
            classification = classify_text(raw.get("title"), raw.get("description"))
            deadline = parse_date(raw.get("deadline"))
            published_at = parse_date(raw.get("published_at"))
            status = infer_status(deadline)
            existing = db.scalar(
                select(Opportunity).where(
                    Opportunity.source_id == source.id,
                    Opportunity.external_id == raw["external_id"],
                )
            )

            payload = {
                "external_id": raw["external_id"],
                "source_id": source.id,
                "title": raw["title"],
                "normalized_title": normalize_text(raw["title"]),
                "short_description": raw["description"][:240],
                "description": raw["description"],
                "summary": raw["description"][:320],
                "category": classification.category,
                "areas": classification.areas,
                "psychology_relevance": classification.psychology_relevance,
                "relevance_score": classification.relevance_score,
                "organization": raw["organization"],
                "entity_type": raw["entity_type"],
                "region": raw.get("region"),
                "province": raw.get("province"),
                "municipality": raw.get("municipality"),
                "original_location": ", ".join(
                    part
                    for part in [
                        raw.get("municipality"),
                        raw.get("province"),
                        raw.get("region"),
                    ]
                    if part
                ),
                "status": status,
                "published_at": published_at,
                "deadline": deadline,
                "last_seen_at": datetime.now(UTC),
                "positions": raw.get("positions"),
                "compensation_min": raw.get("compensation_min"),
                "compensation_max": raw.get("compensation_max"),
                "compensation_period": raw.get("compensation_period"),
                "duration": raw.get("duration"),
                "contract_type": raw.get("contract_type"),
                "requirements": classification.requirements,
                "application_mode": "Consultare la fonte ufficiale.",
                "official_url": raw["official_url"],
                "content_hash": content_hash(raw.get("title"), raw.get("description")),
                "editorial_status": "approved"
                if classification.psychology_relevance in {"alta", "media"}
                else "pending",
                "is_featured": raw["external_id"] in {"demo-001", "demo-002"},
            }
            payload["search_text"] = build_search_text(
                payload["title"],
                payload["description"],
                payload["organization"],
                payload["region"],
                payload["province"],
                payload["category"],
                payload["areas"],
                payload["requirements"],
            )

            if existing:
                for key, value in payload.items():
                    setattr(existing, key, value)
                updated += 1
            else:
                db.add(Opportunity(**payload))
                created += 1

        source.last_success_at = datetime.now(UTC)
        source.last_error = None
        run.status = "success"
    except Exception as exc:  # pragma: no cover - exercised in integration
        run.status = "failed"
        run.error_message = str(exc)
        source.last_error = str(exc)
        skipped += 1
        raise
    finally:
        run.finished_at = datetime.now(UTC)
        run.created_count = created
        run.updated_count = updated
        run.skipped_count = skipped

    db.commit()
    return ImportResult(
        source_id=source.id,
        created_count=created,
        updated_count=updated,
        skipped_count=skipped,
    )

