import json

from app.importers.ast_marche import parse_ast_marche_records
from app.models import Source


def test_parse_ast_marche_records_extracts_psychology_announcement() -> None:
    source = Source(
        id="src_ast",
        name="AST Ancona - Concorsi",
        source_type="nextjs-public-list",
        base_url="https://example.test/ast-comunica/concorsi",
        organization="AST Ancona",
        region="Marche",
    )
    payload = '"announcements":' + json.dumps(
        [
            {
                "_id": "abc123",
                "object": "Avviso pubblico per Dirigente Psicologo psicoterapia",
                "publishedDate": "2026-07-01T10:00:00.000Z",
                "expirationDate": "2026-08-03T21:59:00.000Z",
                "whatIs": "<p>Incarico per psicologo presso servizio territoriale</p>",
                "pageUrl": "avviso-dirigente-psicologo",
                "file": {
                    "full": "https://example.test/bando.pdf",
                    "additionalInfo": {
                        "fullName": "Bando psicologo.pdf",
                        "format": "pdf",
                    },
                },
            },
            {
                "_id": "def456",
                "object": "Bando per Dirigente Medico",
                "expirationDate": "2026-08-03T21:59:00.000Z",
                "whatIs": "<p>Medicina interna</p>",
                "pageUrl": "bando-medico",
            },
        ]
    )
    escaped_payload = (
        payload.replace('"', r"\"")
        .replace("<", r"\u003c")
        .replace(">", r"\u003e")
    )
    html = f"<script>self.__next_f.push([1,\"{escaped_payload}\"])</script>"

    records = parse_ast_marche_records(source, html, source.base_url)

    assert len(records) == 1
    assert records[0].title == "Avviso pubblico per Dirigente Psicologo psicoterapia"
    assert records[0].deadline is not None
    assert records[0].official_url == (
        "https://example.test/ast-comunica/concorsi/avviso-dirigente-psicologo"
    )
    assert records[0].attachments[0]["url"] == "https://example.test/bando.pdf"


def test_parse_ast_marche_records_returns_empty_without_data_payload() -> None:
    source = Source(
        id="src_ast",
        name="AST Fermo - Concorsi",
        source_type="nextjs-public-list",
        base_url="https://example.test/ast-comunica/concorsi",
        organization="AST Fermo",
        region="Marche",
    )

    assert parse_ast_marche_records(source, "<html></html>", source.base_url) == []
