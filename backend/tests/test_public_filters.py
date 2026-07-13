from datetime import UTC, datetime

from app.api.public import _build_contextual_facets, _filter_items
from app.models import Opportunity


def _opportunity(
    *,
    title: str,
    region: str,
    province: str,
    entity_type: str = "azienda-sanitaria",
    category: str = "avviso-pubblico",
    areas: list[str] | None = None,
    status: str = "open",
    deadline: datetime | None = None,
) -> Opportunity:
    opportunity_areas = areas if areas is not None else ["psicoterapia"]
    search_text = f"{title} {region} {province} {entity_type} {' '.join(opportunity_areas)}"
    return Opportunity(
        id=f"opp_{region}_{province}_{title}".replace(" ", "_"),
        title=title,
        normalized_title=title.lower(),
        organization="Ente test",
        entity_type=entity_type,
        region=region,
        province=province,
        category=category,
        areas=opportunity_areas,
        status=status,
        deadline=deadline,
        psychology_relevance="alta",
        relevance_score=90,
        requirements=[],
        official_url=f"https://example.test/{province}/{title}",
        editorial_status="approved",
        search_text=search_text.lower(),
        updated_at=datetime.now(UTC),
    )


def test_default_public_filter_hides_review_items_without_deadline() -> None:
    open_item = _opportunity(
        title="Avviso psicologo aperto",
        region="Basilicata",
        province="PZ",
        status="open",
        deadline=datetime(2026, 10, 16, 21, 59, tzinfo=UTC),
    )
    review_item = _opportunity(
        title="Avviso psicologo da verificare",
        region="Basilicata",
        province="MT",
        status="review",
    )
    closed_item = _opportunity(
        title="Avviso psicologo chiuso",
        region="Basilicata",
        province="MT",
        status="closed",
        deadline=datetime(2024, 10, 16, 21, 59, tzinfo=UTC),
    )

    default_results = _filter_items(
        [open_item, review_item, closed_item],
        q=None,
        region="Basilicata",
        province=None,
        category=None,
        entity_type=None,
        area=None,
        status_filter=None,
        deadline=None,
        featured=None,
    )
    missing_deadline_results = _filter_items(
        [open_item, review_item, closed_item],
        q=None,
        region="Basilicata",
        province=None,
        category=None,
        entity_type=None,
        area=None,
        status_filter=None,
        deadline="missing",
        featured=None,
    )

    assert default_results == [open_item]
    assert missing_deadline_results == [review_item]


def test_region_filter_limits_province_facet_options() -> None:
    items = [
        _opportunity(title="Avviso psicologo Lazio", region="Lazio", province="RM"),
        _opportunity(title="Avviso psicologo Lombardia", region="Lombardia", province="MI"),
    ]

    facets = _build_contextual_facets(
        items,
        q=None,
        region="Lazio",
        province=None,
        selected_province=None,
        category=None,
        entity_type=None,
        area=None,
        status_filter=None,
        deadline=None,
        featured=None,
    )

    assert [facet.value for facet in facets.provinces] == ["RM"]


def test_incoherent_province_returns_no_region_results() -> None:
    items = [
        _opportunity(title="Avviso psicologo Lazio", region="Lazio", province="RM"),
        _opportunity(title="Avviso psicologo Lombardia", region="Lombardia", province="MI"),
    ]

    filtered = _filter_items(
        items,
        q=None,
        region="Lazio",
        province="MI",
        category=None,
        entity_type=None,
        area=None,
        status_filter=None,
        deadline=None,
        featured=None,
    )

    assert filtered == []


def test_incoherent_province_stays_visible_with_zero_count() -> None:
    items = [
        _opportunity(title="Avviso psicologo Lazio", region="Lazio", province="RM"),
        _opportunity(title="Avviso psicologo Lombardia", region="Lombardia", province="MI"),
    ]

    facets = _build_contextual_facets(
        items,
        q=None,
        region="Lazio",
        province=None,
        selected_province="MI",
        category=None,
        entity_type=None,
        area=None,
        status_filter=None,
        deadline=None,
        featured=None,
    )

    assert [(facet.value, facet.count) for facet in facets.provinces] == [
        ("RM", 1),
        ("MI", 0),
    ]


def test_region_facet_ignores_current_province_filter() -> None:
    items = [
        _opportunity(title="Avviso psicologo Sicilia", region="Sicilia", province="Trapani"),
        _opportunity(title="Avviso psicologo Lazio", region="Lazio", province="RM"),
    ]

    facets = _build_contextual_facets(
        items,
        q=None,
        region="Sicilia",
        province="Trapani",
        selected_province="Trapani",
        category=None,
        entity_type=None,
        area=None,
        status_filter=None,
        deadline=None,
        featured=None,
    )

    assert [(facet.value, facet.count) for facet in facets.regions] == [
        ("Lazio", 1),
        ("Sicilia", 1),
    ]
    assert [(facet.value, facet.count) for facet in facets.provinces] == [
        ("Trapani", 1),
    ]


def test_entity_type_facet_ignores_current_entity_filter() -> None:
    items = [
        _opportunity(
            title="Avviso psicologo Lazio",
            region="Lazio",
            province="RM",
            entity_type="azienda-sanitaria",
        ),
        _opportunity(
            title="Avviso psicologo Umbria",
            region="Umbria",
            province="PG",
            entity_type="altro-ente-pubblico",
        ),
    ]

    facets = _build_contextual_facets(
        items,
        q=None,
        region="Lazio",
        province=None,
        selected_province=None,
        category=None,
        entity_type="altro-ente-pubblico",
        area=None,
        status_filter=None,
        deadline=None,
        featured=None,
    )

    assert [(facet.value, facet.count) for facet in facets.entity_types] == [
        ("azienda-sanitaria", 1),
        ("altro-ente-pubblico", 0),
    ]
    assert [(facet.value, facet.count) for facet in facets.regions] == [
        ("Umbria", 1),
        ("Lazio", 0),
    ]


def test_area_facet_ignores_current_area_filter() -> None:
    items = [
        _opportunity(
            title="Avviso psicologo Lazio",
            region="Lazio",
            province="RM",
            areas=["psicoterapia"],
        ),
        _opportunity(
            title="Avviso neuropsicologo Lazio",
            region="Lazio",
            province="RM",
            areas=["neuropsicologia"],
        ),
    ]

    facets = _build_contextual_facets(
        items,
        q=None,
        region="Lazio",
        province=None,
        selected_province=None,
        category=None,
        entity_type=None,
        area="psicologia-del-lavoro",
        status_filter=None,
        deadline=None,
        featured=None,
    )

    assert [(facet.value, facet.count) for facet in facets.areas] == [
        ("neuropsicologia", 1),
        ("psicoterapia", 1),
        ("psicologia-del-lavoro", 0),
    ]
