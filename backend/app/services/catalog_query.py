from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta

from app.models import Opportunity
from app.schemas import (
    Facets,
    FacetValue,
    OpportunityDetail,
    OpportunityListItem,
)
from app.services.classifier import normalize_text

DEFAULT_PUBLIC_STATUSES = {"open", "closing_soon"}


def source_name(opportunity: Opportunity) -> str | None:
    return opportunity.source.name if opportunity.source else None


def list_item(opportunity: Opportunity) -> OpportunityListItem:
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
        source_name=source_name(opportunity),
        official_url=opportunity.official_url,
        is_featured=opportunity.is_featured,
        summary=opportunity.summary,
        updated_at=opportunity.updated_at,
    )


def detail(opportunity: Opportunity) -> OpportunityDetail:
    base = list_item(opportunity).model_dump()
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


def filter_items(
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
    include_review: bool = False,
    apply_default_status: bool = True,
) -> list[Opportunity]:
    default_statuses = DEFAULT_PUBLIC_STATUSES | ({"review"} if include_review else set())
    filtered: list[Opportunity] = []
    for item in items:
        if item.editorial_status != "approved":
            continue
        if (
            apply_default_status
            and not status_filter
            and deadline not in {"missing", "past"}
            and item.status not in default_statuses
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


def sort_items(items: list[Opportunity], sort: str) -> list[Opportunity]:
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


def build_facets(items: list[Opportunity]) -> Facets:
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


def build_contextual_facets(
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
    include_review: bool = False,
) -> Facets:
    region_items = filter_items(
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
        include_review=include_review,
    )
    province_items = filter_items(
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
        include_review=include_review,
    )
    category_items = filter_items(
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
        include_review=include_review,
    )
    entity_type_items = filter_items(
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
        include_review=include_review,
    )
    area_items = filter_items(
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
        include_review=include_review,
    )
    status_items = filter_items(
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
        include_review=include_review,
        apply_default_status=False,
    )

    return Facets(
        regions=_with_selected_facet(
            _counter_to_facets(Counter(item.region for item in region_items if item.region)),
            region,
        ),
        provinces=_with_selected_facet(
            _counter_to_facets(Counter(item.province for item in province_items if item.province)),
            selected_province,
        ),
        categories=_with_selected_facet(
            _counter_to_facets(Counter(item.category for item in category_items if item.category)),
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
