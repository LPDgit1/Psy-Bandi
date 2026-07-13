import ssl

from app.importers.inail import build_inail_ssl_context, parse_records

HTML = """
<html><body>
  <section class="listCardPadre">
    <div class="card">
      <h3 class="card-title h3">
        <a href="https://www.inail.it/portale/it/inail-comunica/avvisi/avviso.2026.05.psicologo.html"
           aria-label="Avviso pubblico per psicologo - pubblicato il 29 mag 2026">
          Avviso pubblico per psicologo
        </a>
      </h3>
      <p class="card-text">Scade il 17 giugno 2026 il termine per la domanda.</p>
    </div>
  </section>
</body></html>
"""


def test_parse_records_extracts_recent_inail_card() -> None:
    records = parse_records(HTML)

    assert records == [
        {
            "external_id": "avviso.2026.05.psicologo",
            "title": "Avviso pubblico per psicologo",
            "summary": "Scade il 17 giugno 2026 il termine per la domanda.",
            "published_at": records[0]["published_at"],
            "deadline": records[0]["deadline"],
            "official_url": (
                "https://www.inail.it/portale/it/inail-comunica/avvisi/"
                "avviso.2026.05.psicologo.html"
            ),
        }
    ]
    assert records[0]["published_at"].date().isoformat() == "2026-05-29"
    assert records[0]["deadline"].date().isoformat() == "2026-06-17"


def test_ssl_context_keeps_verification_and_limits_inail_compatibility() -> None:
    context = build_inail_ssl_context()

    assert context.check_hostname
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.maximum_version == ssl.TLSVersion.TLSv1_2
