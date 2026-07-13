from app.importers.azienda_zero_piemonte import (
    _has_next_page,
    _positions,
    parse_records,
)

HTML = """
<html><body>
<div class="dro-concorso-holder">
  <h2>Avviso pubblico per n. 2 incarichi di PSICOLOGI SPECIALISTI IN PSICOTERAPIA</h2>
  <div class="dro-concorso-container">
    <p class="concorso-date"><strong>Data pubblicazione:</strong><span>01/08/2025</span></p>
    <p class="concorso-date"><strong>Data scadenza:</strong><span>16/08/2025</span></p>
    <div class="allegati-container">
      <p>Bando</p><a href="/uploads/bando-psicologi.pdf">Scarica</a>
    </div>
    <div class="allegati-container">
      <p>Elenco candidati ammessi</p><a href="/uploads/ammessi.pdf">Scarica</a>
    </div>
    <div class="allegati-container">
      <p>Graduatorie finali</p><a href="/uploads/graduatorie.pdf">Scarica</a>
    </div>
  </div>
</div>
<a href="?pag_concorsi=2">Successiva</a>
</body></html>
"""


def test_parse_records_extracts_dates_and_safe_attachments() -> None:
    records = parse_records(
        HTML,
        "https://www.aziendazero.piemonte.it/concorsiaz0/incarichi-di-collaborazione/",
    )

    assert len(records) == 1
    assert records[0]["deadline"].date().isoformat() == "2025-08-16"
    assert records[0]["published_at"].date().isoformat() == "2025-08-01"
    assert records[0]["attachments"] == [
        {
            "title": "Bando",
            "url": "https://www.aziendazero.piemonte.it/uploads/bando-psicologi.pdf",
            "file_type": "pdf",
        }
    ]


def test_pagination_and_positions_are_detected() -> None:
    assert _has_next_page(HTML, 2)
    assert not _has_next_page(HTML, 3)
    assert _positions("Avviso pubblico per n. 2 incarichi di Psicologi") == 2
