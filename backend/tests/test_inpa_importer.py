import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.importers.inpa import (
    AUTO_HIDE_DUPLICATE_NOTE,
    _fetch_pages,
    _fetch_records,
    _hide_duplicate_inpa_opportunities,
    _hide_inpa_records_no_longer_open,
    _payload,
    _professional_match,
    _professionally_relevant,
    strip_html,
)
from app.models import Base, Opportunity, Source


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FakeInpaClient:
    def __init__(self, payloads: dict[tuple[str, int], dict]) -> None:
        self.payloads = payloads
        self.calls: list[tuple[str, int]] = []

    def post(self, _path: str, *, params: dict, json: dict) -> FakeResponse:
        term = json["text"]
        page = params["page"]
        self.calls.append((term, page))
        return FakeResponse(self.payloads[(term, page)])


def test_fetch_records_full_open_scan_then_keyword_dedupe() -> None:
    client = FakeInpaClient(
        {
            ("", 0): {"totalPages": 2, "content": [{"id": "open-1"}]},
            ("", 1): {"totalPages": 2, "content": [{"id": "open-2"}]},
            ("psicolog", 0): {
                "totalPages": 1,
                "content": [{"id": "open-2"}, {"id": "term-1"}],
            },
        }
    )
    original_enabled = settings.inpa_open_scan_enabled
    original_open_pages = settings.inpa_open_scan_max_pages
    original_terms = settings.inpa_search_terms
    original_term_pages = settings.inpa_max_pages
    try:
        object.__setattr__(settings, "inpa_open_scan_enabled", True)
        object.__setattr__(settings, "inpa_open_scan_max_pages", 5)
        object.__setattr__(settings, "inpa_search_terms", ["psicolog"])
        object.__setattr__(settings, "inpa_max_pages", 2)

        records = _fetch_records(client)  # type: ignore[arg-type]
    finally:
        object.__setattr__(settings, "inpa_open_scan_enabled", original_enabled)
        object.__setattr__(settings, "inpa_open_scan_max_pages", original_open_pages)
        object.__setattr__(settings, "inpa_search_terms", original_terms)
        object.__setattr__(settings, "inpa_max_pages", original_term_pages)

    assert [record["id"] for record in records] == ["open-1", "open-2", "term-1"]
    assert client.calls == [("", 0), ("", 1), ("psicolog", 0)]


def test_fetch_pages_raises_when_full_open_scan_would_be_incomplete() -> None:
    client = FakeInpaClient(
        {
            ("", 0): {"totalPages": 3, "content": [{"id": "open-1"}]},
        }
    )

    with pytest.raises(RuntimeError, match="Scansione inPA incompleta"):
        _fetch_pages(
            client,  # type: ignore[arg-type]
            term="",
            max_pages=2,
            require_complete=True,
        )


def test_hide_duplicate_inpa_opportunities_keeps_one_record() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        source = Source(
            name="inPA - Portale del Reclutamento",
            source_type="api",
            base_url="https://www.inpa.gov.it/bandi-e-avvisi/",
        )
        first = Opportunity(
            source=source,
            external_id="same-id",
            title="Avviso per psicologo",
            normalized_title="avviso per psicologo",
            organization="Ente test",
            status="open",
            official_url="https://example.test/1",
            search_text="avviso psicologo",
            editorial_status="approved",
        )
        second = Opportunity(
            source=source,
            external_id="same-id",
            title="Avviso per psicologo",
            normalized_title="avviso per psicologo",
            organization="Ente test",
            status="open",
            official_url="https://example.test/1",
            search_text="avviso psicologo",
            editorial_status="pending",
        )
        db.add_all([source, first, second])
        db.commit()

        changed = _hide_duplicate_inpa_opportunities(db, source)

        assert changed == 1
        assert first.editorial_status == "approved"
        assert second.editorial_status == "hidden"
        assert second.editorial_notes == AUTO_HIDE_DUPLICATE_NOTE


def test_strip_html_keeps_readable_text() -> None:
    assert strip_html("<p>Psicologo <strong>clinico</strong></p>") == "Psicologo clinico"


def test_relevance_accepts_explicit_psychologist_title() -> None:
    raw = {
        "titolo": "Avviso pubblico per psicologo",
        "figuraRicercata": "Psicologo",
        "descrizione": "<p>Servizio tutela minori</p>",
        "descrizioneBreve": "",
    }

    assert _professionally_relevant(raw)


def test_relevance_rejects_generic_psychological_mention() -> None:
    raw = {
        "titolo": "Concorso per insegnante scuola infanzia",
        "figuraRicercata": "Insegnante",
        "descrizione": "<p>Richieste conoscenze pedagogiche e psicologiche.</p>",
        "descrizioneBreve": "",
    }

    assert not _professionally_relevant(raw)


def test_relevance_rejects_administrative_job_at_psychologists_order() -> None:
    raw = {
        "titolo": (
            "Mobilita presso il Consiglio Nazionale dell'Ordine degli Psicologi "
            "per funzionario amministrazione contabilita"
        ),
        "figuraRicercata": "Funzionario amministrativo",
        "descrizione": "<p>Attivita amministrativa e contabile.</p>",
        "descrizioneBreve": "",
    }

    assert not _professionally_relevant(raw)


def test_relevance_marks_degree_only_opportunity_for_review() -> None:
    raw = {
        "titolo": "Avviso formazione elenco educatori",
        "figuraRicercata": "Educatore",
        "descrizione": "<p>Ammessa laurea in psicologia con abilitazione.</p>",
        "descrizioneBreve": "",
    }

    assert _professional_match(raw) == "eligible"


def test_relevance_approves_multirole_notice_with_psychologist_in_description() -> None:
    raw = {
        "titolo": "Avviso pubblico per incarichi individuali vari profili",
        "figuraRicercata": "Esperti vari",
        "descrizione": "<p>N. 1 esperto psicologo per servizi socio-assistenziali.</p>",
        "descrizioneBreve": "",
    }

    assert _professional_match(raw) == "direct"


def test_relevance_keeps_generic_professional_mentions_for_review() -> None:
    raw = {
        "titolo": "Mobilita per educatore nidi d'infanzia",
        "figuraRicercata": "Educatore",
        "descrizione": (
            "<p>Collaborazione con professionisti che si occupano dello sviluppo "
            "0-6, inclusi pedagogisti, psicologi, pediatri e assistenti sociali.</p>"
        ),
        "descrizioneBreve": "",
    }

    assert _professional_match(raw) == "eligible"


def test_relevance_accepts_less_obvious_psychology_profiles() -> None:
    clinical = {
        "titolo": "Avviso pubblico per esperto in psicologia clinica",
        "figuraRicercata": "Esperto area psicologica",
        "descrizione": "<p>Richiesta classe LM-51 e iscrizione all'albo.</p>",
        "descrizioneBreve": "",
    }
    psychodiagnostic = {
        "titolo": "Selezione per attivita psicodiagnostica",
        "figuraRicercata": "Consulente",
        "descrizione": "<p>Valutazioni psicodiagnostiche e neuropsicologiche.</p>",
        "descrizioneBreve": "",
    }

    assert _professional_match(clinical) == "direct"
    assert _professional_match(psychodiagnostic) == "direct"


def test_relevance_accepts_cognitive_rehabilitation_and_psychoeducational_profiles() -> None:
    cognitive = {
        "titolo": "Avviso pubblico per riabilitazione cognitiva",
        "figuraRicercata": "Consulente",
        "descrizione": "<p>Test neuropsicologici e valutazione psicologica.</p>",
        "descrizioneBreve": "",
    }
    psychoeducational = {
        "titolo": "Selezione per interventi psicoeducativi",
        "figuraRicercata": "Esperto",
        "descrizione": "<p>Progetto psicosociale in salute mentale.</p>",
        "descrizioneBreve": "",
    }

    assert _professional_match(cognitive) == "direct"
    assert _professional_match(psychoeducational) == "direct"


def test_relevance_keeps_behavioral_mental_health_research_for_review() -> None:
    raw = {
        "titolo": "Borsa di studio in scienze comportamentali e salute mentale",
        "figuraRicercata": "Borsista",
        "descrizione": "<p>Ricerca in scienze comportamentali e salute mentale.</p>",
        "descrizioneBreve": "",
    }

    assert _professional_match(raw) == "eligible"


def test_relevance_excludes_revoked_psychologist_competition() -> None:
    raw = {
        "titolo": "Revoca concorso pubblico per n. 6 posti di Dirigente Psicologo",
        "figuraRicercata": "Dirigente Psicologo",
        "descrizione": "Procedura revocata dall'amministrazione.",
        "descrizioneBreve": "",
    }

    assert _professional_match(raw) is None


def test_full_open_scan_hides_inpa_record_no_longer_listed() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        source = Source(
            name="inPA - Portale del Reclutamento",
            source_type="api",
            base_url="https://www.inpa.gov.it/bandi-e-avvisi/",
        )
        opportunity = Opportunity(
            source=source,
            external_id="removed-id",
            title="Avviso per psicologo",
            normalized_title="avviso per psicologo",
            organization="Ente test",
            status="open",
            official_url="https://example.test/removed-id",
            search_text="avviso psicologo",
            editorial_status="approved",
        )
        db.add(opportunity)
        db.commit()

        changed = _hide_inpa_records_no_longer_open(db, source, {"still-open"})

        assert changed == 1
        assert opportunity.status == "closed"
        assert opportunity.editorial_status == "hidden"


def test_payload_builds_official_inpa_detail_url() -> None:
    source = Source(
        id="src_test",
        name="inPA",
        source_type="api",
        base_url="https://www.inpa.gov.it/bandi-e-avvisi/",
    )
    raw = {
        "id": "abc123",
        "titolo": "Concorso pubblico per psicologo",
        "figuraRicercata": "Psicologo",
        "descrizione": "<p>Richiesta laurea in psicologia e iscrizione albo.</p>",
        "descrizioneBreve": "<p>Un posto disponibile.</p>",
        "categorie": ["Concorso"],
        "sedi": ["Lazio", "Roma"],
        "entiRiferimento": ["Comune di Roma"],
        "calculatedStatus": "OPEN",
        "dataPubblicazione": "2026-05-29T12:00:00Z",
        "dataScadenza": "2026-06-30T10:00:00Z",
        "numPosti": 1,
    }

    payload = _payload(source, raw)

    assert payload["organization"] == "Comune di Roma"
    assert payload["region"] == "Lazio"
    assert payload["province"] == "Roma"
    assert payload["category"] == "concorso-pubblico"
    assert payload["official_url"].endswith("?concorso_id=abc123")


def test_payload_normalizes_inverted_inpa_location_order() -> None:
    source = Source(
        id="src_test",
        name="inPA",
        source_type="api",
        base_url="https://www.inpa.gov.it/bandi-e-avvisi/",
    )
    raw = {
        "id": "abc456",
        "titolo": "Avviso pubblico per psicologo",
        "figuraRicercata": "Psicologo",
        "descrizione": "<p>Richiesta laurea in psicologia e iscrizione albo.</p>",
        "descrizioneBreve": "<p>Un posto disponibile.</p>",
        "categorie": ["Avviso"],
        "sedi": ["Caserta", "Campania"],
        "entiRiferimento": ["Comune di Caserta"],
        "calculatedStatus": "OPEN",
        "dataPubblicazione": "2026-05-29T12:00:00Z",
        "dataScadenza": "2026-06-30T10:00:00Z",
        "numPosti": 1,
    }

    payload = _payload(source, raw)

    assert payload["region"] == "Campania"
    assert payload["province"] == "Caserta"
