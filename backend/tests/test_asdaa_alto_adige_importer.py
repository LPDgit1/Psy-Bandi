from app.importers.asdaa_alto_adige import parse_records

HTML = """
<html><body>
<table><tbody>
  <tr>
    <td>Concorso pubblico per dirigente psicologo</td>
    <td>Prove d'esame: 28.07.2026</td>
    <td><a href="/cv/bando.pdf">Documenti</a></td>
  </tr>
  <tr>
    <td>Concorso pubblico per collaboratore amministrativo</td>
    <td>Graduatoria pubblicata</td>
    <td><a href="/cv/graduatoria.pdf">Documenti</a></td>
  </tr>
</tbody></table>
</body></html>
"""


def test_parse_records_keeps_metadata_without_cv_documents() -> None:
    records = parse_records(HTML)

    assert len(records) == 2
    assert records[0]["title"] == "Concorso pubblico per dirigente psicologo"
    assert records[0]["description"] == "Prove d'esame: 28.07.2026"
    assert "attachments" not in records[0]
