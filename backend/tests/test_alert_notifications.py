from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.public import _confirm_alert, _unsubscribe_alert
from app.core.config import settings
from app.models import AlertSubscription, Base, EmailLog, Opportunity
from app.services.alert_notifications import (
    matching_opportunities,
    send_alert_report,
    send_confirmation_email,
    send_due_alert_reports,
)
from app.services.classifier import normalize_text


@pytest.fixture()
def db() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session


@pytest.fixture()
def email_outbox(tmp_path: Path) -> Iterator[Path]:
    original_mode = settings.email_delivery_mode
    original_dir = settings.email_outbox_dir
    original_api_url = settings.public_api_base_url
    object.__setattr__(settings, "email_delivery_mode", "file")
    object.__setattr__(settings, "email_outbox_dir", str(tmp_path))
    object.__setattr__(
        settings,
        "public_api_base_url",
        "http://localhost:8000/api/public",
    )
    yield tmp_path
    object.__setattr__(settings, "email_delivery_mode", original_mode)
    object.__setattr__(settings, "email_outbox_dir", original_dir)
    object.__setattr__(settings, "public_api_base_url", original_api_url)


def _opportunity(
    *,
    title: str,
    description: str = "",
    region: str = "Lazio",
    category: str = "avviso-pubblico",
    areas: list[str] | None = None,
    editorial_status: str = "approved",
    status: str = "open",
    deadline: datetime | None = None,
) -> Opportunity:
    text = f"{title} {description}"
    return Opportunity(
        title=title,
        normalized_title=normalize_text(title),
        description=description,
        summary=description,
        category=category,
        areas=areas or ["psicoterapia"],
        psychology_relevance="alta",
        relevance_score=90,
        organization="ASL Test",
        entity_type="azienda-sanitaria",
        region=region,
        province="RM",
        status=status,
        deadline=deadline,
        official_url=f"https://example.test/{normalize_text(title).replace(' ', '-')}",
        search_text=normalize_text(text),
        editorial_status=editorial_status,
    )


def test_send_confirmation_email_writes_outbox_and_email_log(
    db: Session,
    email_outbox: Path,
) -> None:
    subscription = AlertSubscription(
        email="utente@example.test",
        regions=["Lazio"],
        categories=["avviso-pubblico"],
        areas=["psicoterapia"],
        keywords=["minori"],
        frequency="weekly",
    )
    db.add(subscription)
    db.flush()

    log = send_confirmation_email(db, subscription)
    db.commit()

    files = list(email_outbox.glob("*.eml"))
    saved_log = db.scalar(select(EmailLog).where(EmailLog.id == log.id))

    assert log.status == "sent"
    assert saved_log is not None
    assert saved_log.delivery_mode == "file"
    assert len(files) == 1
    email_text = files[0].read_text(encoding="utf-8")
    assert "Conferma alert Ricerca Bandi Psicologi" in email_text
    assert "http://localhost:8000/api/public/alerts/confirm" in saved_log.body_text
    assert "http://localhost:8000/api/public/alerts/unsubscribe" in saved_log.body_text
    assert subscription.confirm_token in saved_log.body_text


def test_matching_opportunities_respects_filters_and_keywords(db: Session) -> None:
    subscription = AlertSubscription(
        email="utente@example.test",
        status="active",
        regions=["Lazio"],
        categories=["avviso-pubblico"],
        areas=["psicoterapia"],
        keywords=["minori"],
    )
    matching = _opportunity(
        title="Avviso per psicoterapeuta",
        description="Intervento clinico per minori e famiglie.",
        region="Lazio",
        areas=["psicoterapia", "minori-famiglia"],
    )
    wrong_region = _opportunity(
        title="Avviso per psicoterapeuta minori",
        description="Intervento clinico per minori.",
        region="Campania",
    )
    wrong_keyword = _opportunity(
        title="Avviso per psicoterapeuta adulti",
        description="Intervento clinico per adulti.",
        region="Lazio",
    )
    db.add_all([subscription, matching, wrong_region, wrong_keyword])
    db.flush()

    assert matching_opportunities(db, subscription) == [matching]


def test_send_alert_report_logs_items_and_updates_last_sent(
    db: Session,
    email_outbox: Path,
) -> None:
    now = datetime.now(UTC)
    subscription = AlertSubscription(
        email="utente@example.test",
        status="active",
        regions=["Lazio"],
        areas=["psicoterapia"],
        frequency="weekly",
        last_sent_at=now - timedelta(days=8),
    )
    opportunity = _opportunity(
        title="Incarico psicoterapeuta per servizio minori",
        description="Supporto clinico e psicoterapia per minori.",
        deadline=now + timedelta(days=10),
    )
    db.add_all([subscription, opportunity])
    db.flush()

    result = send_alert_report(db, subscription, since=subscription.last_sent_at)
    db.commit()
    saved_log = db.scalar(select(EmailLog).where(EmailLog.id == result.email_log_id))

    assert result.status == "sent"
    assert result.matched_count == 1
    assert subscription.last_sent_at is not None
    assert saved_log is not None
    assert "Incarico psicoterapeuta per servizio minori" in saved_log.body_text
    assert opportunity.official_url in saved_log.body_text
    assert "http://localhost:8000/api/public/alerts/unsubscribe" in saved_log.body_text
    assert len(list(email_outbox.glob("*.eml"))) == 1


def test_send_due_alert_reports_only_sends_active_due_alerts(
    db: Session,
    email_outbox: Path,
) -> None:
    now = datetime.now(UTC)
    due = AlertSubscription(
        email="due@example.test",
        status="active",
        regions=["Lazio"],
        areas=["psicoterapia"],
        frequency="weekly",
        last_sent_at=now - timedelta(days=8),
    )
    not_due = AlertSubscription(
        email="notdue@example.test",
        status="active",
        regions=["Lazio"],
        areas=["psicoterapia"],
        frequency="weekly",
        last_sent_at=now - timedelta(days=1),
    )
    pending = AlertSubscription(
        email="pending@example.test",
        status="pending",
        regions=["Lazio"],
        areas=["psicoterapia"],
        frequency="weekly",
    )
    db.add_all(
        [
            due,
            not_due,
            pending,
            _opportunity(
                title="Bando psicoterapeuta minori",
                description="Psicoterapia e sostegno a minori.",
            ),
        ]
    )
    db.flush()

    reports = send_due_alert_reports(db, now=now)

    assert [report.recipient for report in reports] == ["due@example.test"]
    assert reports[0].matched_count == 1
    assert due.last_sent_at is not None
    assert len(list(email_outbox.glob("*.eml"))) == 1


def test_failed_delivery_does_not_advance_last_sent_at(db: Session, monkeypatch) -> None:
    subscription = AlertSubscription(
        email="alerts@example.test",
        status="active",
        frequency="daily",
    )
    db.add(subscription)
    db.commit()
    monkeypatch.setattr(
        "app.services.alert_notifications.send_email",
        lambda **_kwargs: SimpleNamespace(
            status="failed",
            delivery_mode="smtp",
            provider_message_id=None,
            error_message="SMTP unavailable",
        ),
    )

    result = send_alert_report(db, subscription)

    assert result.status == "failed"
    assert subscription.last_sent_at is None


def test_unsubscribe_disables_alert_and_prevents_old_confirm_reactivation(
    db: Session,
) -> None:
    subscription = AlertSubscription(
        email="utente@example.test",
        status="active",
        regions=["Lazio"],
        areas=["psicoterapia"],
        frequency="weekly",
    )
    db.add(subscription)
    db.commit()

    unsubscribe_response = _unsubscribe_alert(db, subscription.confirm_token)
    confirm_response = _confirm_alert(db, subscription.confirm_token)

    db.refresh(subscription)
    assert unsubscribe_response.status == "unsubscribed"
    assert confirm_response.status == "unsubscribed"
    assert subscription.status == "unsubscribed"


def test_unsubscribed_alerts_are_not_due(db: Session, email_outbox: Path) -> None:
    now = datetime.now(UTC)
    unsubscribed = AlertSubscription(
        email="unsubscribed@example.test",
        status="unsubscribed",
        regions=["Lazio"],
        areas=["psicoterapia"],
        frequency="weekly",
        last_sent_at=now - timedelta(days=30),
    )
    db.add_all(
        [
            unsubscribed,
            _opportunity(
                title="Bando psicoterapeuta minori",
                description="Psicoterapia e sostegno a minori.",
            ),
        ]
    )
    db.flush()

    reports = send_due_alert_reports(db, now=now)

    assert reports == []
    assert list(email_outbox.glob("*.eml")) == []
