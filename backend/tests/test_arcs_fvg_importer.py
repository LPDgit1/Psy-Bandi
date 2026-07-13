from app.importers.arcs_fvg import _positions, parse_detail, parse_listing

LIST_HTML = """
<html><body>
<article class="oa-simple-card">
  <h3 class="it-card-title"><a href="/it/concorsi/dirigente-psicologo-12400">
    Concorso pubblico per n. 1 posto di Dirigente Psicologo
  </a></h3>
  <div class="it-card-category"><span>Concorsi pubblici</span></div>
  <p><span>Data inizio</span> 05/05/2026</p>
  <p><span>Data fine</span> 04/06/2026</p>
</article>
</body></html>
"""

DETAIL_HTML = """
<html><body>
<div id="section-descrizione"><p>Profilo di dirigente psicologo.</p></div>
<div id="section-allegati">
  <div class="file-title"><a href="/files/bando-psicologo.pdf">Bando dirigente psicologo</a></div>
  <div class="file-title"><a href="/files/commissione.pdf">Nomina commissione</a></div>
</div>
</body></html>
"""


def test_parse_listing_extracts_open_card() -> None:
    records = parse_listing(LIST_HTML)

    assert len(records) == 1
    assert records[0]["external_id"] == "12400"
    assert records[0]["source_category"] == "Concorsi pubblici"
    assert records[0]["published_at"].date().isoformat() == "2026-05-05"
    assert records[0]["deadline"].date().isoformat() == "2026-06-04"


def test_parse_detail_keeps_only_essential_documents() -> None:
    detail = parse_detail(DETAIL_HTML)

    assert detail["description"] == "Profilo di dirigente psicologo."
    assert detail["attachments"] == [
        {
            "title": "Bando dirigente psicologo",
            "url": "https://arcs.sanita.fvg.it/files/bando-psicologo.pdf",
            "file_type": "pdf",
        }
    ]
    assert _positions("Concorso pubblico per n. 1 posto di Dirigente Psicologo") == 1
