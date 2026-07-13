from app.importers.usl_umbria2 import parse_detail, parse_listing

LIST_HTML = """
<html><body>
<table class="table-atti">
  <tr>
    <th>OGGETTO</th><th>SCADENZA</th><th>TIPOLOGIA</th><th>IMPORTO</th><th></th>
  </tr>
  <tr>
    <td><span>Avviso pubblico per incarichi professionali di psicologo</span></td>
    <td>2.12.2022</td>
    <td>Avviso pubblico</td>
    <td></td>
    <td class="leggi-tutto"><a href="../atti/avviso-psicologo">Leggi tutto</a></td>
  </tr>
</table>
</body></html>
"""

DETAIL_HTML = """
<html><body>
  <a href="../MC-API/Risorse/StreamAttributoMediaOriginale.ashx?guid=1">
    avviso protocollo n. 240510.pdf
  </a>
  <a href="../MC-API/Risorse/StreamAttributoMediaOriginale.ashx?guid=2">
    Allegato n. 1 - schema di domanda.doc
  </a>
  <a href="../MC-API/Risorse/StreamAttributoMediaOriginale.ashx?guid=3">
    ELENCO CANDIDATI AMMESSI.pdf
  </a>
</body></html>
"""


def test_parse_listing_extracts_public_table_row_and_dot_date() -> None:
    records = parse_listing(
        LIST_HTML,
        "https://www.uslumbria2.it/amministrazione-trasparente/incarichi",
    )

    assert len(records) == 1
    assert records[0]["title"].endswith("psicologo")
    assert records[0]["deadline"].date().isoformat() == "2022-12-02"
    assert records[0]["detail_url"] == "https://www.uslumbria2.it/atti/avviso-psicologo"


def test_parse_detail_keeps_only_essential_documents() -> None:
    detail = parse_detail(
        DETAIL_HTML,
        "https://www.uslumbria2.it/atti/avviso-psicologo",
    )

    assert detail["attachments"] == [
        {
            "title": "avviso protocollo n. 240510.pdf",
            "url": (
                "https://www.uslumbria2.it/MC-API/Risorse/"
                "StreamAttributoMediaOriginale.ashx?guid=1"
            ),
            "file_type": "pdf",
        },
        {
            "title": "Allegato n. 1 - schema di domanda.doc",
            "url": (
                "https://www.uslumbria2.it/MC-API/Risorse/"
                "StreamAttributoMediaOriginale.ashx?guid=2"
            ),
            "file_type": "doc",
        },
    ]
