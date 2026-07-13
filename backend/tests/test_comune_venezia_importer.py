from app.importers.comune_venezia import parse_records

HTML = """
<html><body><table><tbody>
<tr>
  <td>ANNO</td><td>CODICE</td><td>PROCEDURE IN SCADENZA</td>
  <td>POSTI BANDITI</td><td>SCADENZA CANDIDATURE</td>
</tr>
<tr>
  <td>2026</td><td>01PSI/2026</td>
  <td><a href="/it/content/01psi2026">Avviso pubblico per n. 2 psicologi</a></td>
  <td>2</td><td>22/06/2026 ore 12:00 su portale INPA</td>
</tr>
<tr>
  <td>ANNO</td><td>CODICE</td><td>PROCEDURE IN CORSO</td>
  <td>POSTI BANDITI</td><td>CANDIDATURE SCADUTE IL</td>
</tr>
<tr>
  <td>2025</td><td>02PSI/2025</td>
  <td><a href="/it/content/02psi2025">Concorso per n. 1 psicologo</a></td>
  <td>1</td><td>20/01/2026 ore 12:00 su portale INPA</td>
</tr>
</tbody></table></body></html>
"""


def test_parse_records_extracts_rows_and_section_status() -> None:
    records = parse_records(HTML)

    assert len(records) == 2
    assert records[0]["external_id"] == "01PSI/2026"
    assert records[0]["positions"] == 2
    assert records[0]["deadline"].date().isoformat() == "2026-06-22"
    assert records[0]["official_url"] == "https://www.comune.venezia.it/it/content/01psi2026"
    assert records[1]["status"] == "closed"
