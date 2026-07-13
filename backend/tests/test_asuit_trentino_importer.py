from app.importers.asuit_trentino import (
    _has_next_page,
    _positions,
    _status,
    parse_detail,
    parse_listing,
)

LIST_HTML = """
<html><body>
<article class="node node--type-bando node--view-mode-teaser" data-history-node-id="10872">
  <h5 class="card-title"><a href="/bandi-concorsi/dirigente-psicologo">
    Concorso pubblico per n. 1 posto di dirigente psicologo
  </a></h5>
  <div class="mb-2">
    <span class="badge"><div>Concluso</div></span>
    <span class="badge"><div>CP 01/26</div></span>
  </div>
  <div class="node--teaser-text-truncate">Profilo professionale di psicologo.</div>
</article>
<a href="?combine=psicolog&amp;page=1">Successiva</a>
</body></html>
"""

DETAIL_HTML = """
<html><body>
<section id="date-scadenze">
  <div class="badge-meta-date-box">
    <div class="badge-meta-date-label">Data pubblicazione</div>
    <time class="badge-meta-date-time">02 febbraio 2026</time>
  </div>
  <div class="badge-meta-date-box">
    <div class="badge-meta-date-label">Scadenza</div>
    <time class="badge-meta-date-time">19 febbraio 2026</time>
  </div>
</section>
<section id="cosa-e"><p>Selezione per dirigente psicologo.</p></section>
<section id="documenti">
  <a href="/files/bando-dirigente-psicologo.pdf">Bando di concorso</a>
  <a href="/files/bando-dirigente-psicologo.pdf">DOWNLOAD</a>
  <a href="/files/elenco-candidati.pdf">Elenco candidati ammessi</a>
</section>
</body></html>
"""


def test_parse_listing_extracts_filtered_drupal_card() -> None:
    records = parse_listing(LIST_HTML)

    assert len(records) == 1
    assert records[0]["external_id"] == "10872"
    assert records[0]["list_status"] == "Concluso"
    assert _has_next_page(LIST_HTML, 0)
    assert not _has_next_page(LIST_HTML, 1)


def test_parse_detail_extracts_dates_and_safe_documents() -> None:
    detail = parse_detail(DETAIL_HTML)

    assert detail["published_at"].date().isoformat() == "2026-02-02"
    assert detail["deadline"].date().isoformat() == "2026-02-19"
    assert detail["description"] == "Selezione per dirigente psicologo."
    assert detail["attachments"] == [
        {
            "title": "Bando di concorso",
            "url": "https://www.asuit.tn.it/files/bando-dirigente-psicologo.pdf",
            "file_type": "pdf",
        }
    ]


def test_closed_badge_and_positions_are_detected() -> None:
    assert _status({"list_status": "Bando concluso", "deadline": None}) == "closed"
    assert _positions("Concorso pubblico per n. 1 posto di dirigente psicologo") == 1
