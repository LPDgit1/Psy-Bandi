from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.importers.puglia_aol import (
    _attachment_url,
    _is_primary_opportunity,
    _official_url,
    _payload,
)
from app.models import Base, Source


def _source() -> Source:
    return Source(
        id="src_puglia",
        name="PugliaSalute AOL - ASL Bari concorsi",
        source_type="puglia-aol-api",
        base_url="https://sanita.puglia.it/aol/?path=listConcorso&aziendaParam=aslbari&act=def",
        organization="ASL Bari",
        region="Puglia",
    )


def test_puglia_aol_official_urls_point_to_public_app_routes() -> None:
    source = _source()

    assert _official_url(source, 123).endswith(
        "?path=dettaglioConcorso%2F123&aziendaParam=aslbari"
    )
    assert _attachment_url(source, 456).endswith(
        "?path=downloadAllegato%2F456&aziendaParam=aslbari"
    )


def test_puglia_aol_filters_primary_psychology_opportunities() -> None:
    assert _is_primary_opportunity(
        "Bando di concorso pubblico per n. 2 posti di Dirigente Psicologo"
    )
    assert _is_primary_opportunity(
        "Avviso pubblico per incarico libero professionale di psicoterapeuta"
    )
    assert _is_primary_opportunity(
        "Avviso pubblico per incarico di Psicologo - rettifica e riapertura termini"
    )
    assert not _is_primary_opportunity(
        "Convocazione prova colloquio avviso pubblico per psicologo"
    )
    assert not _is_primary_opportunity(
        "Avviso pubblico per Psicologo - data colloquio"
    )
    assert not _is_primary_opportunity(
        "Graduatoria finale concorso pubblico dirigente psicologo"
    )


def test_puglia_aol_payload_uses_application_deadline_when_present() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    item = {
        "id": 123,
        "oggetto": "Bando di concorso pubblico per Dirigente Psicologo",
        "dataPubblicazione": "2026-07-09T10:00:00",
        "dataScadenza": "2026-09-30T23:59:59",
        "metadata": {"dataScadenzaDomande": "2026-08-15T12:00:00"},
    }

    with Session(engine) as db:
        payload = _payload(db, _source(), item)

    assert payload["deadline"] is not None
    assert payload["deadline"].month == 8
    assert payload["organization"] == "ASL Bari"
    assert payload["official_url"].startswith("https://sanita.puglia.it/aol/")
