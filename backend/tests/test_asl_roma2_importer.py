from app.importers.asl_roma2 import parse_records

HTML = """
<html><body>
<table class="elenco"><thead><tr>
<th>Concorso</th><th>Oggetto</th><th>Documenti</th><th>Scadenza</th><th>Stato</th>
</tr></thead>
<tr onMouseover="setPointer(this,'#FFFFEE')">
<td>Inserimento<br>15/05/2026<hr>Ultima modifica<br>15/05/2026</td>
<td>AVVISO PUBBLICO PER N. 1 PSICOLOGO PER IL BENESSERE MATERNO</td>
<td>
  <a href="allegato.php?id=3368">Deliberazione indizione bando</a>
  <a href="allegato.php?id=3371">Domanda</a>
  <a href="allegato.php?id=3372">Elenco candidati ammessi</a>
</td>
<td>Ore 23:59 del<br>22/06/2026</td>
<td>In Corso</td>
</tr>
</table>
</body></html>
"""


def test_parse_records_extracts_public_row_and_safe_attachments() -> None:
    records = parse_records(HTML)

    assert len(records) == 1
    assert records[0]["external_id"] == "3368"
    assert records[0]["deadline"].date().isoformat() == "2026-06-22"
    assert [item["title"] for item in records[0]["attachments"]] == [
        "Deliberazione indizione bando",
        "Domanda",
    ]
    assert records[0]["attachments"][0]["url"] == (
        "https://www.aslroma2.it/external/concorsi/allegato.php?id=3368"
    )
