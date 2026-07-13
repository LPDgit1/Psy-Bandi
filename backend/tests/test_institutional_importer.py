from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.importers.institutional import (
    direct_psychology_match,
    find_probable_duplicate,
    upsert_opportunity,
)
from app.models import Base, Opportunity, Source


def test_direct_psychology_match_requires_professional_term() -> None:
    assert direct_psychology_match("Avviso per n. 1 psicologo")
    assert direct_psychology_match("Dirigente psicologa disciplina psicoterapia")
    assert direct_psychology_match("Avviso per psicoterapeuta")
    assert direct_psychology_match("Incarico per specializzazione in psicoterapia")
    assert direct_psychology_match("Profilo con laurea in psicologia classe LM-51")
    assert direct_psychology_match("Profilo area psicologica classe 58/S")
    assert direct_psychology_match("Avviso per esperto in psicologia clinica")
    assert direct_psychology_match("Avviso per professionista in psicologia di base")
    assert direct_psychology_match("Incarico disciplina psicologia delle cure primarie")
    assert direct_psychology_match("Attivita di valutazione psicodiagnostica")
    assert direct_psychology_match("Richiesta iscrizione all'albo degli psicologi")
    assert direct_psychology_match("Avviso per esperto di supporto psicologico")
    assert direct_psychology_match("Incarico per sportello di ascolto psicologico")
    assert not direct_psychology_match("Supporto psicologico per il personale")


def test_direct_match_accepts_psychological_service_inside_public_notice() -> None:
    assert direct_psychology_match(
        "Avviso pubblico per un servizio di sostegno psicologico agli studenti"
    )


def test_duplicate_search_ignores_closed_canonical_record() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        old_source = Source(name="Fonte vecchia", source_type="html", base_url="https://old.test")
        new_source = Source(name="Fonte nuova", source_type="html", base_url="https://new.test")
        db.add_all([old_source, new_source])
        db.flush()
        db.add(
            Opportunity(
                source_id=old_source.id,
                title="Avviso pubblico per psicologo clinico",
                normalized_title="avviso pubblico per psicologo clinico",
                organization="ASL Test",
                status="closed",
                official_url="https://old.test/bando",
                search_text="avviso psicologo clinico",
                editorial_status="approved",
            )
        )
        db.commit()

        duplicate = find_probable_duplicate(
            db,
            source_id=new_source.id,
            title="Avviso pubblico per psicologo clinico",
            organization="ASL Test",
            deadline=None,
        )

        assert duplicate is None


def test_upsert_restores_automatically_hidden_record_after_extension() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        source = Source(name="Fonte", source_type="html", base_url="https://example.test")
        record = Opportunity(
            source=source,
            external_id="item-1",
            title="Avviso per psicologo",
            normalized_title="avviso per psicologo",
            organization="ASL Test",
            status="closed",
            official_url="https://example.test/item-1",
            search_text="avviso psicologo",
            editorial_status="hidden",
            editorial_notes="Nascosto automaticamente: scadenza superata.",
        )
        db.add(record)
        db.commit()

        created = upsert_opportunity(
            db,
            payload={
                "source_id": source.id,
                "external_id": "item-1",
                "status": "open",
                "editorial_status": "approved",
                "editorial_notes": None,
            },
            attachments=[],
        )

        assert not created
        assert record.editorial_status == "approved"
        assert record.editorial_notes is None
