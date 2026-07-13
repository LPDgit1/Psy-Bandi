from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import AlertSubscription, Opportunity
from app.schemas import (
    AlertCreate,
    AlertReportResponse,
    AlertResponse,
    Facets,
    FacetValue,
    OpportunityDetail,
    OpportunityListItem,
    OpportunityListResponse,
    RefreshResponse,
    ReportCreate,
)
from app.services.alert_notifications import send_alert_report, send_confirmation_email
from app.services.classifier import normalize_text
from app.services.deadline_status import refresh_deadline_statuses
from app.services.public_refresh import get_public_refresh_status, queue_public_refresh

router = APIRouter(prefix="/api/public", tags=["public"])
DEFAULT_PUBLIC_STATUSES = {"open", "closing_soon"}


def _source_name(opportunity: Opportunity) -> str | None:
    return opportunity.source.name if opportunity.source else None


def _list_item(opportunity: Opportunity) -> OpportunityListItem:
    return OpportunityListItem(
        id=opportunity.id,
        title=opportunity.title,
        organization=opportunity.organization,
        entity_type=opportunity.entity_type,
        region=opportunity.region,
        province=opportunity.province,
        municipality=opportunity.municipality,
        category=opportunity.category,
        areas=opportunity.areas or [],
        status=opportunity.status,
        deadline=opportunity.deadline,
        psychology_relevance=opportunity.psychology_relevance,
        relevance_score=opportunity.relevance_score,
        requirements=opportunity.requirements or [],
        source_name=_source_name(opportunity),
        official_url=opportunity.official_url,
        is_featured=opportunity.is_featured,
        summary=opportunity.summary,
        updated_at=opportunity.updated_at,
    )


def _detail(opportunity: Opportunity) -> OpportunityDetail:
    base = _list_item(opportunity).model_dump()
    base.update(
        {
            "short_description": opportunity.short_description,
            "description": opportunity.description,
            "published_at": opportunity.published_at,
            "opens_at": opportunity.opens_at,
            "positions": opportunity.positions,
            "compensation_min": opportunity.compensation_min,
            "compensation_max": opportunity.compensation_max,
            "compensation_period": opportunity.compensation_period,
            "duration": opportunity.duration,
            "contract_type": opportunity.contract_type,
            "application_mode": opportunity.application_mode,
            "organization_url": opportunity.organization_url,
            "attachments": [
                {
                    "id": attachment.id,
                    "title": attachment.title,
                    "url": attachment.url,
                    "file_type": attachment.file_type,
                }
                for attachment in opportunity.attachments
            ],
        }
    )
    return OpportunityDetail(**base)


def _deadline_matches(opportunity: Opportunity, deadline_filter: str | None) -> bool:
    if not deadline_filter:
        return True
    if opportunity.deadline is None:
        return deadline_filter == "missing"

    now = datetime.now(UTC)
    deadline = opportunity.deadline.astimezone(UTC)

    if deadline_filter == "missing":
        return False
    if deadline_filter == "7d":
        return now <= deadline <= now + timedelta(days=7)
    if deadline_filter == "30d":
        return now <= deadline <= now + timedelta(days=30)
    if deadline_filter == "future":
        return deadline >= now
    if deadline_filter == "past":
        return deadline < now
    return True


def _matches_query(opportunity: Opportunity, query: str | None) -> bool:
    if not query:
        return True
    terms = normalize_text(query).split()
    return all(term in opportunity.search_text for term in terms)


def _filter_items(
    items: list[Opportunity],
    q: str | None,
    region: str | None,
    province: str | None,
    category: str | None,
    entity_type: str | None,
    area: str | None,
    status_filter: str | None,
    deadline: str | None,
    featured: bool | None,
) -> list[Opportunity]:
    filtered: list[Opportunity] = []
    for item in items:
        if item.editorial_status != "approved":
            continue
        if (
            not status_filter
            and deadline not in {"missing", "past"}
            and item.status not in DEFAULT_PUBLIC_STATUSES
        ):
            continue
        if not _matches_query(item, q):
            continue
        if region and item.region != region:
            continue
        if province and item.province != province:
            continue
        if category and item.category != category:
            continue
        if entity_type and item.entity_type != entity_type:
            continue
        if area and area not in (item.areas or []):
            continue
        if status_filter and item.status != status_filter:
            continue
        if featured is not None and item.is_featured is not featured:
            continue
        if not _deadline_matches(item, deadline):
            continue
        filtered.append(item)
    return filtered


def _sort_items(items: list[Opportunity], sort: str) -> list[Opportunity]:
    if sort == "recent":
        return sorted(items, key=lambda item: item.published_at or item.created_at, reverse=True)
    if sort == "relevance":
        return sorted(
            items,
            key=lambda item: (item.relevance_score, item.is_featured),
            reverse=True,
        )
    if sort == "organization":
        return sorted(items, key=lambda item: item.organization.lower())
    if sort == "region":
        return sorted(items, key=lambda item: (item.region or "").lower())
    return sorted(
        items,
        key=lambda item: (
            item.deadline is None,
            item.deadline or datetime.max.replace(tzinfo=UTC),
        ),
    )


def _counter_to_facets(counter: Counter[str]) -> list[FacetValue]:
    return [
        FacetValue(value=value, count=count)
        for value, count in sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))
        if value
    ]


def _area_facets(items: list[Opportunity]) -> list[FacetValue]:
    area_counter: Counter[str] = Counter()
    for item in items:
        area_counter.update(item.areas or [])
    return _counter_to_facets(area_counter)


def _with_selected_facet(
    facets: list[FacetValue],
    selected: str | None,
) -> list[FacetValue]:
    if not selected or any(facet.value == selected for facet in facets):
        return facets
    return [*facets, FacetValue(value=selected, count=0)]


def _build_facets(items: list[Opportunity]) -> Facets:
    return Facets(
        regions=_counter_to_facets(Counter(item.region for item in items if item.region)),
        provinces=_counter_to_facets(Counter(item.province for item in items if item.province)),
        categories=_counter_to_facets(Counter(item.category for item in items if item.category)),
        entity_types=_counter_to_facets(
            Counter(item.entity_type for item in items if item.entity_type)
        ),
        areas=_area_facets(items),
        statuses=_counter_to_facets(Counter(item.status for item in items if item.status)),
    )


def _build_contextual_facets(
    items: list[Opportunity],
    *,
    q: str | None,
    region: str | None,
    province: str | None,
    selected_province: str | None,
    category: str | None,
    entity_type: str | None,
    area: str | None,
    status_filter: str | None,
    deadline: str | None,
    featured: bool | None,
) -> Facets:
    region_items = _filter_items(
        items,
        q=q,
        region=None,
        province=None,
        category=category,
        entity_type=entity_type,
        area=area,
        status_filter=status_filter,
        deadline=deadline,
        featured=featured,
    )
    province_items = _filter_items(
        items,
        q=q,
        region=region,
        province=None,
        category=category,
        entity_type=entity_type,
        area=area,
        status_filter=status_filter,
        deadline=deadline,
        featured=featured,
    )
    category_items = _filter_items(
        items,
        q=q,
        region=region,
        province=province,
        category=None,
        entity_type=entity_type,
        area=area,
        status_filter=status_filter,
        deadline=deadline,
        featured=featured,
    )
    entity_type_items = _filter_items(
        items,
        q=q,
        region=region,
        province=province,
        category=category,
        entity_type=None,
        area=area,
        status_filter=status_filter,
        deadline=deadline,
        featured=featured,
    )
    area_items = _filter_items(
        items,
        q=q,
        region=region,
        province=province,
        category=category,
        entity_type=entity_type,
        area=None,
        status_filter=status_filter,
        deadline=deadline,
        featured=featured,
    )
    status_items = _filter_items(
        items,
        q=q,
        region=region,
        province=province,
        category=category,
        entity_type=entity_type,
        area=area,
        status_filter=None,
        deadline=deadline,
        featured=featured,
    )

    return Facets(
        regions=_with_selected_facet(
            _counter_to_facets(Counter(item.region for item in region_items if item.region)),
            region,
        ),
        provinces=_with_selected_facet(
            _counter_to_facets(
                Counter(item.province for item in province_items if item.province)
            ),
            selected_province,
        ),
        categories=_with_selected_facet(
            _counter_to_facets(
                Counter(item.category for item in category_items if item.category)
            ),
            category,
        ),
        entity_types=_with_selected_facet(
            _counter_to_facets(
                Counter(item.entity_type for item in entity_type_items if item.entity_type)
            ),
            entity_type,
        ),
        areas=_with_selected_facet(_area_facets(area_items), area),
        statuses=_with_selected_facet(
            _counter_to_facets(Counter(item.status for item in status_items if item.status)),
            status_filter,
        ),
    )


@router.get("/opportunities", response_model=OpportunityListResponse)
def list_opportunities(
    q: str | None = None,
    region: str | None = None,
    province: str | None = None,
    category: str | None = None,
    entity_type: str | None = None,
    area: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    deadline: str | None = None,
    featured: bool | None = None,
    sort: str = "deadline",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> OpportunityListResponse:
    refresh_deadline_statuses(db)
    all_items = list(db.scalars(select(Opportunity)).all())
    public_items = [item for item in all_items if item.editorial_status == "approved"]
    filtered = _filter_items(
        public_items,
        q=q,
        region=region,
        province=province,
        category=category,
        entity_type=entity_type,
        area=area,
        status_filter=status_filter,
        deadline=deadline,
        featured=featured,
    )
    sorted_items = _sort_items(filtered, sort)
    paginated = sorted_items[offset : offset + limit]

    return OpportunityListResponse(
        items=[_list_item(item) for item in paginated],
        total=len(filtered),
        limit=limit,
        offset=offset,
        facets=_build_contextual_facets(
            public_items,
            q=q,
            region=region,
            province=province,
            selected_province=province,
            category=category,
            entity_type=entity_type,
            area=area,
            status_filter=status_filter,
            deadline=deadline,
            featured=featured,
        ),
    )


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityDetail)
def get_opportunity(opportunity_id: str, db: Session = Depends(get_db)) -> OpportunityDetail:
    refresh_deadline_statuses(db)
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None or opportunity.editorial_status != "approved":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return _detail(opportunity)


@router.get("/facets", response_model=Facets)
def get_facets(db: Session = Depends(get_db)) -> Facets:
    refresh_deadline_statuses(db)
    items = list(
        db.scalars(select(Opportunity).where(Opportunity.editorial_status == "approved")).all()
    )
    return _build_facets(items)


@router.post("/refresh", response_model=RefreshResponse)
def refresh_sources() -> RefreshResponse:
    return RefreshResponse(**queue_public_refresh())


@router.get("/refresh/status", response_model=RefreshResponse)
def refresh_sources_status() -> RefreshResponse:
    return RefreshResponse(**get_public_refresh_status())


@router.post("/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
def create_alert(
    payload: AlertCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> AlertResponse:
    subscription = AlertSubscription(
        email=str(payload.email),
        regions=payload.regions,
        categories=payload.categories,
        areas=payload.areas,
        keywords=payload.keywords,
        frequency=payload.frequency,
        consent_ip=request.client.host if request.client else None,
    )
    db.add(subscription)
    db.flush()
    email_log = send_confirmation_email(db, subscription)
    db.commit()
    db.refresh(subscription)
    email_message = (
        "Ti abbiamo inviato una email di conferma."
        if email_log.status == "sent"
        else "Alert salvato, ma l'invio email richiede verifica tecnica."
    )
    return AlertResponse(
        id=subscription.id,
        status=subscription.status,
        message=f"Alert creato. {email_message}",
        confirm_token=subscription.confirm_token,
    )


def _alert_by_token(db: Session, token: str) -> AlertSubscription:
    subscription = db.scalar(
        select(AlertSubscription).where(AlertSubscription.confirm_token == token)
    )
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return subscription


def _confirm_alert(db: Session, token: str) -> AlertResponse:
    subscription = _alert_by_token(db, token)
    if subscription.status == "unsubscribed":
        return AlertResponse(
            id=subscription.id,
            status=subscription.status,
            message="Alert gia disattivato. Per riattivarlo crea un nuovo alert.",
        )
    subscription.status = "active"
    subscription.consent_at = datetime.now(UTC)
    db.commit()
    return AlertResponse(id=subscription.id, status=subscription.status, message="Alert attivato.")


@router.post("/alerts/confirm", response_model=AlertResponse)
def confirm_alert(token: str, db: Session = Depends(get_db)) -> AlertResponse:
    return _confirm_alert(db, token)


@router.get("/alerts/confirm", response_model=AlertResponse)
def confirm_alert_link(token: str, db: Session = Depends(get_db)) -> AlertResponse:
    return _confirm_alert(db, token)


def _unsubscribe_alert(db: Session, token: str) -> AlertResponse:
    subscription = _alert_by_token(db, token)
    subscription.status = "unsubscribed"
    db.commit()
    return AlertResponse(
        id=subscription.id,
        status=subscription.status,
        message="Iscrizione disattivata.",
    )


@router.post("/alerts/unsubscribe", response_model=AlertResponse)
def unsubscribe_alert(token: str, db: Session = Depends(get_db)) -> AlertResponse:
    return _unsubscribe_alert(db, token)


@router.get("/alerts/unsubscribe", response_model=AlertResponse)
def unsubscribe_alert_link(token: str, db: Session = Depends(get_db)) -> AlertResponse:
    return _unsubscribe_alert(db, token)


@router.post("/alerts/send-report", response_model=AlertReportResponse)
def send_alert_report_now(token: str, db: Session = Depends(get_db)) -> AlertReportResponse:
    subscription = _alert_by_token(db, token)
    if subscription.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Alert not active")
    result = send_alert_report(db, subscription)
    db.commit()
    return AlertReportResponse(
        id=subscription.id,
        status=result.status,
        matched_count=result.matched_count,
        email_log_id=result.email_log_id,
        message=f"Report inviato con {result.matched_count} risultato/i.",
    )


@router.post("/reports", status_code=status.HTTP_202_ACCEPTED)
def create_report(payload: ReportCreate) -> dict[str, str]:
    return {
        "status": "received",
        "message": (
            "Segnalazione acquisita. Nel prossimo step verra collegata "
            "a una coda redazionale."
        ),
    }
