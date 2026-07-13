from datetime import UTC, datetime

from app.importers.azienda_zero import (
    AZIENDA_ZERO_DETAIL_URL,
    _datetime_from_millis,
    _essential_attachments,
    _positions,
)


def test_datetime_from_millis_uses_epoch_timestamp() -> None:
    assert _datetime_from_millis(0) == datetime(1970, 1, 1, tzinfo=UTC)


def test_positions_extracts_number_of_posts() -> None:
    assert _positions("Concorso pubblico per n. 24 posti di Dirigente Psicologo") == 24
    assert _positions("Avviso per il conferimento di n. 2 incarichi") == 2
    assert _positions("Avviso senza quantità dichiarata") is None


def test_essential_attachments_avoids_candidate_lists() -> None:
    records = [
        {"nomeFile": "bando", "link": "https://example.test/bando", "estensione": "pdf"},
        {
            "nomeFile": "elenco candidati ammessi",
            "link": "https://example.test/candidati",
            "estensione": "pdf",
        },
        {
            "nomeFile": "istruzioni compilazione delle domande",
            "link": "https://example.test/istruzioni",
            "estensione": "pdf",
        },
    ]

    assert [item["title"] for item in _essential_attachments(records)] == [
        "bando",
        "istruzioni compilazione delle domande",
    ]


def test_official_detail_url_is_linked_platform_page() -> None:
    assert AZIENDA_ZERO_DETAIL_URL.format(external_id="854").endswith(
        "action=trasparenza.concorso&id=854"
    )
