from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AlertSubscription, EmailLog, Opportunity
from app.services.classifier import normalize_text
from app.services.email_delivery import send_email

MAX_ALERT_ITEMS = 12


@dataclass(frozen=True)
class AlertReportResult:
    subscription_id: str
    recipient: str
    matched_count: int
    email_log_id: str | None
    status: str


def _public_api_url(path: str, **params: str) -> str:
    base = settings.public_api_base_url.rstrip("/")
    query = f"?{urlencode(params)}" if params else ""
    return f"{base}{path}{query}"


def _matches_subscription(opportunity: Opportunity, subscription: AlertSubscription) -> bool:
    if opportunity.editorial_status != "approved":
        return False
    if opportunity.status == "closed":
        return False
    if subscription.regions and opportunity.region not in subscription.regions:
        return False
    if subscription.categories and opportunity.category not in subscription.categories:
        return False
    if subscription.areas and not set(subscription.areas).intersection(opportunity.areas or []):
        return False
    if subscription.keywords:
        search_text = normalize_text(opportunity.search_text or opportunity.title)
        if not all(normalize_text(keyword) in search_text for keyword in subscription.keywords):
            return False
    return True


def matching_opportunities(
    db: Session,
    subscription: AlertSubscription,
    *,
    since: datetime | None = None,
) -> list[Opportunity]:
    statement = select(Opportunity).where(Opportunity.editorial_status == "approved")
    if since is not None:
        statement = statement.where(Opportunity.updated_at >= since)
    items = [
        item
        for item in db.scalars(statement).all()
        if _matches_subscription(item, subscription)
    ]
    return sorted(
        items,
        key=lambda item: (
            item.deadline is None,
            item.deadline or datetime.max.replace(tzinfo=UTC),
            item.title.lower(),
        ),
    )[:MAX_ALERT_ITEMS]


def render_confirmation_email(subscription: AlertSubscription) -> tuple[str, str]:
    confirm_url = _public_api_url("/alerts/confirm", token=subscription.confirm_token)
    unsubscribe_url = _public_api_url("/alerts/unsubscribe", token=subscription.confirm_token)
    subject = "Conferma alert Ricerca Bandi Psicologi"
    region_label = ", ".join(subscription.regions) if subscription.regions else "tutte"
    category_label = (
        ", ".join(subscription.categories) if subscription.categories else "tutte"
    )
    area_label = ", ".join(subscription.areas) if subscription.areas else "tutti"
    keyword_label = (
        ", ".join(subscription.keywords) if subscription.keywords else "nessuna"
    )
    body = "\n".join(
        [
            "Hai richiesto un alert per Ricerca Bandi Psicologi.",
            "",
            "Per attivarlo conferma l'iscrizione aprendo questo link:",
            confirm_url,
            "",
            "Filtri salvati:",
            f"- Regioni: {region_label}",
            f"- Tipologie: {category_label}",
            f"- Ambiti: {area_label}",
            f"- Parole chiave: {keyword_label}",
            f"- Frequenza: {subscription.frequency}",
            "",
            (
                "Se non hai richiesto tu questo alert, puoi ignorare questa email "
                "oppure disiscriverti:"
            ),
            unsubscribe_url,
        ]
    )
    return subject, body


def render_alert_report(
    subscription: AlertSubscription,
    opportunities: list[Opportunity],
) -> tuple[str, str]:
    subject = f"Alert bandi psicologi: {len(opportunities)} risultato/i"
    lines = [
        "Report aggiornato Ricerca Bandi Psicologi",
        "",
        f"Risultati trovati: {len(opportunities)}",
        "",
    ]
    if not opportunities:
        lines.append("Nessun nuovo bando corrisponde ai filtri salvati.")
    for index, opportunity in enumerate(opportunities, start=1):
        deadline = (
            opportunity.deadline.strftime("%d/%m/%Y")
            if opportunity.deadline
            else "da verificare"
        )
        lines.extend(
            [
                f"{index}. {opportunity.title}",
                f"   Ente: {opportunity.organization}",
                f"   Regione: {opportunity.region or 'non indicata'}",
                f"   Scadenza: {deadline}",
                f"   Fonte: {opportunity.official_url}",
                "",
            ]
        )
    lines.extend(
        [
            "Gestione alert:",
            _public_api_url("/alerts/unsubscribe", token=subscription.confirm_token),
        ]
    )
    return subject, "\n".join(lines)


def _log_email(
    db: Session,
    *,
    subscription: AlertSubscription,
    subject: str,
    body_text: str,
) -> EmailLog:
    result = send_email(
        recipient=subscription.email,
        subject=subject,
        body_text=body_text,
    )
    log = EmailLog(
        alert_subscription_id=subscription.id,
        recipient=subscription.email,
        subject=subject,
        body_text=body_text,
        status=result.status,
        delivery_mode=result.delivery_mode,
        provider_message_id=result.provider_message_id,
        error_message=result.error_message,
        sent_at=datetime.now(UTC) if result.status == "sent" else None,
    )
    db.add(log)
    db.flush()
    return log


def send_confirmation_email(db: Session, subscription: AlertSubscription) -> EmailLog:
    subject, body = render_confirmation_email(subscription)
    return _log_email(db, subscription=subscription, subject=subject, body_text=body)


def send_alert_report(
    db: Session,
    subscription: AlertSubscription,
    *,
    since: datetime | None = None,
) -> AlertReportResult:
    opportunities = matching_opportunities(db, subscription, since=since)
    subject, body = render_alert_report(subscription, opportunities)
    log = _log_email(db, subscription=subscription, subject=subject, body_text=body)
    if log.status == "sent":
        subscription.last_sent_at = datetime.now(UTC)
    db.flush()
    return AlertReportResult(
        subscription_id=subscription.id,
        recipient=subscription.email,
        matched_count=len(opportunities),
        email_log_id=log.id,
        status=log.status,
    )


def _is_due(subscription: AlertSubscription, now: datetime) -> bool:
    if subscription.status != "active":
        return False
    if subscription.last_sent_at is None:
        return True
    interval = timedelta(days=1 if subscription.frequency == "daily" else 7)
    return subscription.last_sent_at <= now - interval


def send_due_alert_reports(db: Session, *, now: datetime | None = None) -> list[AlertReportResult]:
    current = now or datetime.now(UTC)
    reports: list[AlertReportResult] = []
    subscriptions = db.scalars(select(AlertSubscription)).all()
    for subscription in subscriptions:
        if not _is_due(subscription, current):
            continue
        reports.append(
            send_alert_report(
                db,
                subscription,
                since=subscription.last_sent_at,
            )
        )
    db.commit()
    return reports
