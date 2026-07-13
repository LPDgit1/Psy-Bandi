from app.importers.ausl_romagna import parse_detail, parse_listing

LIST_DATA = {
    "items": [
        {
            "@id": "https://www.auslromagna.it/selezioni/dirigente-psicologo",
            "title": "Dirigente Psicologo di PSICOLOGIA",
            "description": "Avviso pubblico",
        }
    ]
}

DETAIL_DATA = {
    "@id": "https://www.auslromagna.it/selezioni/dirigente-psicologo",
    "UID": "detail-uid",
    "title": "Dirigente Psicologo di PSICOLOGIA",
    "effective": "2026-03-18T10:32:00+00:00",
    "scadenza_bando": "2026-04-02T21:59:00+00:00",
    "text": {
        "blocks": {
            "intro": {
                "@type": "text",
                "text": {
                    "blocks": [
                        {
                            "text": (
                                "Avviso pubblico per assunzioni a tempo "
                                "determinato di Dirigente Psicologo."
                            )
                        }
                    ]
                },
            }
        }
    },
    "approfondimento": [
        {
            "title": "Documenti",
            "children": [
                {
                    "title": "Bando",
                    "url": "https://www.auslromagna.it/files/bando.pdf",
                    "content-type": "application/pdf",
                },
                {
                    "title": "Modello di curriculum",
                    "url": "https://www.auslromagna.it/files/cv.doc",
                    "content-type": "application/msword",
                },
            ],
        },
        {
            "title": "Comunicazioni",
            "children": [
                {
                    "title": "Esito colloquio",
                    "url": "https://www.auslromagna.it/files/esito.pdf",
                    "content-type": "application/pdf",
                }
            ],
        },
    ],
}


def test_parse_listing_extracts_public_feed_item() -> None:
    records = parse_listing(LIST_DATA, "avvisi-tempo-determinato")

    assert len(records) == 1
    assert records[0]["title"] == "Dirigente Psicologo di PSICOLOGIA"
    assert records[0]["source_category"] == "avvisi-tempo-determinato"


def test_parse_detail_extracts_draft_text_dates_and_essential_documents() -> None:
    detail = parse_detail(DETAIL_DATA)

    assert detail["external_id"] == "detail-uid"
    assert detail["published_at"].date().isoformat() == "2026-03-18"
    assert detail["deadline"].date().isoformat() == "2026-04-02"
    assert detail["description"].startswith("Avviso pubblico per assunzioni")
    assert detail["attachments"] == [
        {
            "title": "Bando",
            "url": "https://www.auslromagna.it/files/bando.pdf",
            "file_type": "pdf",
        },
        {
            "title": "Modello di curriculum",
            "url": "https://www.auslromagna.it/files/cv.doc",
            "file_type": "doc",
        },
    ]
