from app.importers.inps import _official_url, _positions, _psychology_match


def test_psychology_match_accepts_specialists_in_psychological_areas() -> None:
    assert _psychology_match(
        {
            "titolo": (
                "Concorso per 781 unita di Specialisti delle aree psicologiche "
                "e sociali"
            )
        }
    )


def test_psychology_match_accepts_requirements_outside_title() -> None:
    assert _psychology_match(
        {
            "titolo": "Selezione per specialisti tecnici",
            "descrizione": "Richiesta laurea LM-51 e iscrizione albo psicologi.",
        }
    )


def test_positions_accepts_thousands_separator() -> None:
    assert _positions("Reclutamento di n. 3.997 unita di personale") == 3997


def test_official_url_uses_public_inps_detail_page() -> None:
    assert _official_url({"selectors": "bandi-fatturazione-concorsi.2024.12.test_1"}) == (
        "https://www.inps.it/it/it/avvisi-bandi-e-fatturazione/"
        "fatturazione-concorsi/dettaglio.bandi-fatturazione-concorsi.2024.12.test_1.html"
    )
