from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base, Opportunity, Source
from app.services.deadline_status import (
    AUTO_HIDE_EXPIRED_NOTE,
    AUTO_HIDE_NON_OPPORTUNITY_NOTE,
    AUTO_HIDE_UNDATED_REVIEW_NOTE,
    refresh_deadline_statuses,
)


def test_refresh_deadline_statuses_hides_expired_public_opportunity() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        opportunity = Opportunity(
            title="Avviso per psicologo",
            normalized_title="avviso per psicologo",
            organization="Ente test",
            status="open",
            deadline=datetime(2026, 5, 31, 21, 59, tzinfo=UTC),
            official_url="https://example.test/bando",
            search_text="avviso psicologo",
            editorial_status="approved",
        )
        db.add(opportunity)
        db.commit()

        changed = refresh_deadline_statuses(
            db,
            now=datetime(2026, 7, 9, 12, 0, tzinfo=UTC),
        )

        db.refresh(opportunity)
        assert changed == 2
        assert opportunity.status == "closed"
        assert opportunity.editorial_status == "hidden"
        assert opportunity.editorial_notes == AUTO_HIDE_EXPIRED_NOTE


def test_refresh_deadline_statuses_keeps_future_public_opportunity_visible() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        opportunity = Opportunity(
            title="Avviso per psicologo",
            normalized_title="avviso per psicologo",
            organization="Ente test",
            status="closing_soon",
            deadline=datetime(2026, 7, 20, 21, 59, tzinfo=UTC),
            official_url="https://example.test/bando",
            search_text="avviso psicologo",
            editorial_status="approved",
        )
        db.add(opportunity)
        db.commit()

        changed = refresh_deadline_statuses(
            db,
            now=datetime(2026, 7, 9, 12, 0, tzinfo=UTC),
        )

        db.refresh(opportunity)
        assert changed == 1
        assert opportunity.status == "open"
        assert opportunity.editorial_status == "approved"


def test_refresh_deadline_statuses_restores_opportunity_after_extension() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    now = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)

    with Session(engine) as db:
        opportunity = Opportunity(
            title="Avviso pubblico per psicologo",
            normalized_title="avviso pubblico per psicologo",
            organization="ASL Test",
            status="closed",
            deadline=now + timedelta(days=10),
            official_url="https://example.test/proroga",
            search_text="avviso psicologo",
            editorial_status="hidden",
            editorial_notes="Nascosto automaticamente: scadenza superata.",
        )
        db.add(opportunity)
        db.commit()

        changed = refresh_deadline_statuses(db, now=now)

        assert changed == 2
        assert opportunity.status == "open"
        assert opportunity.editorial_status == "approved"
        assert opportunity.editorial_notes is None


def test_refresh_deadline_statuses_hides_undated_search_source_review() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        source = Source(
            name="ASM Test - Ricerca",
            source_type="html-list",
            base_url="https://example.test/?s=psicolog",
        )
        opportunity = Opportunity(
            source=source,
            title="Avviso pubblico di selezione. Dirigente psicologo",
            normalized_title="avviso pubblico di selezione dirigente psicologo",
            organization="ASM Test",
            status="review",
            deadline=None,
            official_url="https://example.test/avviso",
            search_text="avviso pubblico psicologo",
            editorial_status="approved",
        )
        db.add_all([source, opportunity])
        db.commit()

        changed = refresh_deadline_statuses(
            db,
            now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )

        db.refresh(opportunity)
        assert changed == 1
        assert opportunity.status == "review"
        assert opportunity.editorial_status == "hidden"
        assert opportunity.editorial_notes == AUTO_HIDE_UNDATED_REVIEW_NOTE


def test_refresh_deadline_statuses_hides_revocation_and_graduation_deadline() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        revocation = Opportunity(
            title="Revoca concorso pubblico per n. 6 posti di Dirigente Psicologo",
            normalized_title="revoca concorso pubblico dirigente psicologo",
            organization="Ente test",
            status="open",
            deadline=datetime(2027, 8, 5, 21, 59, tzinfo=UTC),
            official_url="https://example.test/revoca",
            search_text="revoca concorso pubblico psicologo",
            editorial_status="approved",
        )
        graduation = Opportunity(
            title=(
                "Concorso pubblico Neuropsicologo - Scadenza graduatoria "
                "26/06/2027"
            ),
            normalized_title="concorso pubblico neuropsicologo scadenza graduatoria",
            organization="Ente test",
            status="open",
            deadline=datetime(2027, 6, 26, 21, 59, tzinfo=UTC),
            official_url="https://example.test/graduatoria",
            search_text="concorso pubblico neuropsicologo scadenza graduatoria",
            editorial_status="approved",
        )
        db.add_all([revocation, graduation])
        db.commit()

        changed = refresh_deadline_statuses(
            db,
            now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )

        db.refresh(revocation)
        db.refresh(graduation)
        assert changed == 2
        assert revocation.editorial_status == "hidden"
        assert graduation.editorial_status == "hidden"
        assert revocation.editorial_notes == AUTO_HIDE_NON_OPPORTUNITY_NOTE
        assert graduation.editorial_notes == AUTO_HIDE_NON_OPPORTUNITY_NOTE


def test_refresh_deadline_statuses_hides_generic_listing_titles() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        source = Source(
            name="ASL Test - Bandi",
            source_type="html-list",
            base_url="https://example.test/BandiConcorsi.jsp",
        )
        opportunity = Opportunity(
            source=source,
            title="Bandi di concorso - Azienda USL Test",
            normalized_title="bandi di concorso azienda usl test",
            organization="ASL Test",
            status="open",
            deadline=datetime(2026, 7, 20, 21, 59, tzinfo=UTC),
            official_url="https://example.test/BandiConcorsi.jsp",
            organization_url="https://example.test/BandiConcorsi.jsp",
            search_text="bandi di concorso",
            editorial_status="approved",
        )
        db.add_all([source, opportunity])
        db.commit()

        changed = refresh_deadline_statuses(
            db,
            now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )

        db.refresh(opportunity)
        assert changed == 1
        assert opportunity.editorial_status == "hidden"


def test_refresh_deadline_statuses_hides_completed_selection_with_future_reference_date() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    now = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)

    with Session(engine) as db:
        opportunity = Opportunity(
            title="Avviso pubblico per dirigente psicologo",
            normalized_title="avviso pubblico per dirigente psicologo",
            description=(
                "Approvazione atti della Commissione Esaminatrice e graduatoria "
                "finale di merito."
            ),
            organization="ASP Test",
            status="open",
            deadline=now + timedelta(days=100),
            official_url="https://example.test/approvazione",
            search_text="avviso dirigente psicologo",
            editorial_status="approved",
        )
        db.add(opportunity)
        db.commit()

        changed = refresh_deadline_statuses(db, now=now)

        assert changed == 1
        assert opportunity.editorial_status == "hidden"
        assert opportunity.editorial_notes == AUTO_HIDE_NON_OPPORTUNITY_NOTE


def test_refresh_deadline_statuses_hides_exact_official_url_duplicate() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        source = Source(
            name="Fonte test",
            source_type="html-list",
            base_url="https://example.test/bandi",
        )
        summary = Opportunity(
            source=source,
            external_id="summary",
            title="Ricerca di Psicologo per...",
            normalized_title="ricerca di psicologo per",
            organization="Ente test",
            status="closing_soon",
            deadline=datetime.now(UTC) + timedelta(days=1),
            official_url="https://example.test/bandi/psicologo",
            search_text="ricerca psicologo",
            editorial_status="approved",
        )
        detail = Opportunity(
            source=source,
            external_id="detail",
            title="Ricerca di Psicologo per attivita riabilitativa",
            normalized_title="ricerca di psicologo per attivita riabilitativa",
            organization="Ente test",
            status="open",
            deadline=datetime.now(UTC) + timedelta(days=20),
            official_url="https://example.test/bandi/psicologo",
            search_text="ricerca psicologo riabilitativa",
            editorial_status="approved",
        )
        db.add_all([summary, detail])
        db.commit()

        changed = refresh_deadline_statuses(db)

        assert changed == 1
        assert summary.editorial_status == "hidden"
        assert detail.editorial_status == "approved"


def test_refresh_deadline_statuses_hides_generic_concours_and_service_pages() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        listing = Opportunity(
            title="Concorsi e Selezioni",
            normalized_title="concorsi e selezioni",
            organization="AO Test",
            status="review",
            deadline=None,
            official_url="https://example.test/concorsi-e-selezioni",
            search_text="concorsi e selezioni psicologo",
            editorial_status="approved",
        )
        service = Opportunity(
            title="In tutti i casi in cui si ravvisi un disagio psicologico",
            normalized_title="in tutti i casi disagio psicologico",
            organization="AO Test",
            status="review",
            deadline=None,
            official_url="https://example.test/servizi/centro-di-ascolto-psicologico/",
            search_text="centro ascolto psicologico",
            editorial_status="approved",
        )
        db.add_all([listing, service])
        db.commit()

        changed = refresh_deadline_statuses(
            db,
            now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )

        db.refresh(listing)
        db.refresh(service)
        assert changed == 2
        assert listing.editorial_status == "hidden"
        assert service.editorial_status == "hidden"
