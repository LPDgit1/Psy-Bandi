from __future__ import annotations

"""Regional administrations and Italian provincial-capital municipal sources.

The catalogue keeps one official landing page per administration.  The paired
adapter follows same-site links containing the usual public-recruitment terms
(``bandi``, ``concorsi``, ``selezioni`` and ``avvisi``) and retains only
psychology-relevant opportunities.  A few Sardinian municipalities are also
kept as territorial hubs: the 2026 Sardinian reorganisation has not yet
assigned every new province a formal capoluogo, while the municipalities are
the stable official sources used by applicants.
"""


def _regional(
    name: str,
    region: str,
    base_url: str,
) -> dict[str, str | None]:
    return {
        "name": name,
        "source_type": "regional-municipal-html",
        "base_url": base_url,
        "region": region,
        "organization": name,
        "import_method": "regional-municipal-detail",
        "technical_notes": (
            "Landing page ufficiale dell'amministrazione regionale. L'adapter "
            "segue le schede pubbliche di bandi, concorsi, selezioni e avvisi "
            "sullo stesso dominio e conserva il link originale."
        ),
    }


REGIONAL_SOURCE_DEFINITIONS = [
    _regional(
        "Regione Calabria",
        "Calabria",
        "https://www.regione.calabria.it/concorsi-e-selezioni/",
    ),
    _regional(
        "Regione Campania",
        "Campania",
        "https://www.territorio.regione.campania.it/portale-bandi-e-avvisi",
    ),
    _regional(
        "Regione Basilicata",
        "Basilicata",
        "https://portalebandi.regione.basilicata.it/",
    ),
    _regional(
        "Regione Lazio",
        "Lazio",
        "https://www.regione.lazio.it/bandi-di-concorso-avvisi",
    ),
    _regional(
        "Regione Molise",
        "Molise",
        "https://www.regione.molise.it/flex/cm/pages/ServeBLOB.php/L/IT/IDPagina/10675",
    ),
    _regional(
        "Regione Friuli-Venezia Giulia",
        "Friuli-Venezia Giulia",
        "https://www.regione.fvg.it/rafvg/concorsi/concorsiint.act",
    ),
    _regional(
        "Regione Trentino-Alto Adige",
        "Trentino-Alto Adige",
        "https://www.regione.taa.it/",
    ),
    _regional(
        "Regione Umbria",
        "Umbria",
        "https://www.regione.umbria.it/amministrazione-trasparente/bandi-di-concorso",
    ),
    _regional(
        "Regione Valle d'Aosta",
        "Valle d'Aosta",
        "https://www.regione.vda.it/amministrazione/concorsi/default_i.asp",
    ),
]


def _municipality(
    city: str,
    region: str,
    base_url: str,
    *,
    territorial_hub: bool = False,
) -> dict[str, str | None]:
    note = (
        "Sito ufficiale del Comune e presidio territoriale per bandi e concorsi. "
        "L'adapter segue le pagine pubbliche di reclutamento sul dominio ufficiale."
    )
    if territorial_hub:
        note += (
            " Il Comune è mantenuto anche come hub territoriale per la riforma "
            "delle circoscrizioni provinciali sarde."
        )
    return {
        "name": f"Comune di {city} - Bandi di concorso",
        "source_type": "regional-municipal-html",
        "base_url": base_url,
        "region": region,
        "organization": f"Comune di {city}",
        "import_method": "regional-municipal-detail",
        "technical_notes": note,
    }


# The existing catalogue already covers the other provincial capitals.  This
# list contains the 37 current capitals that were absent plus nine stable
# Sardinian/territorial co-capital hubs (and Cesena/Urbino, whose provincial
# administrations use the paired city names).  Keeping the latter avoids a
# blind spot while the 2026 Sardinian reform is being implemented locally.
_MUNICIPALITY_ROWS = (
    ("Arezzo", "Toscana", "https://www.comune.arezzo.it/", False),
    ("Ascoli Piceno", "Marche", "https://www.comune.ap.it/home", False),
    ("Carbonia", "Sardegna", "https://www.comune.carbonia.su.it/", False),
    ("Cesena", "Emilia-Romagna", "https://www.comune.cesena.fc.it/", True),
    ("Cosenza", "Calabria", "https://www.comune.cosenza.it/", False),
    ("Crotone", "Calabria", "https://www.comune.crotone.it/", False),
    ("Fermo", "Marche", "https://www.comune.fermo.it/", False),
    ("Ferrara", "Emilia-Romagna", "https://www.comune.ferrara.it/", False),
    ("Forlì", "Emilia-Romagna", "https://www.comune.forli.fc.it/it", False),
    ("Gorizia", "Friuli-Venezia Giulia", "https://www.comune.gorizia.it/", False),
    ("Grosseto", "Toscana", "https://www.comune.grosseto.it/", False),
    (
        "Iglesias",
        "Sardegna",
        "https://www.comune.iglesias.ca.it/it/amministrazione/voci-correlate/"
        "amministrazione-trasparente-00001/bandi-di-concorso/index.html",
        True,
    ),
    ("Imperia", "Liguria", "https://www.comune.imperia.it/it", False),
    ("Isernia", "Molise", "https://comune.isernia.it/", False),
    ("La Spezia", "Liguria", "https://www.comune.laspezia.it/", False),
    ("Lanusei", "Sardegna", "https://www.comune.lanusei.og.it/", True),
    ("Livorno", "Toscana", "https://www.comune.livorno.it/it", False),
    ("Lucca", "Toscana", "https://www.comune.lucca.it/", False),
    ("Macerata", "Marche", "https://www.comune.macerata.it/", False),
    ("Massa", "Toscana", "https://www.comune.massa.ms.it/", False),
    ("Modena", "Emilia-Romagna", "https://www.comune.modena.it/", False),
    ("Nuoro", "Sardegna", "https://www.comune.nuoro.it/", False),
    ("Olbia", "Sardegna", "https://www.comune.olbia.ot.it/it", True),
    ("Oristano", "Sardegna", "https://comune.oristano.it/it/", False),
    ("Parma", "Emilia-Romagna", "https://www.comune.parma.it/it", False),
    ("Pesaro", "Marche", "https://www.comune.pesaro.pu.it/", False),
    ("Piacenza", "Emilia-Romagna", "https://www.comune.piacenza.it/it", False),
    ("Pisa", "Toscana", "https://www.comune.pisa.it/", False),
    ("Pistoia", "Toscana", "https://www.comune.pistoia.it/it", False),
    ("Pordenone", "Friuli-Venezia Giulia", "https://www.comune.pordenone.it/it", False),
    ("Prato", "Toscana", "https://www.comune.prato.it/", False),
    ("Ravenna", "Emilia-Romagna", "https://comune.ravenna.it/", False),
    ("Reggio Calabria", "Calabria", "https://comune.reggio-calabria.it/", False),
    ("Reggio Emilia", "Emilia-Romagna", "https://www.comune.reggioemilia.it/", False),
    ("Rimini", "Emilia-Romagna", "https://www.comune.rimini.it/", False),
    ("Sanluri", "Sardegna", "https://www.comune.sanluri.su.it/", True),
    ("Sassari", "Sardegna", "https://www.comune.sassari.it/it/", False),
    ("Savona", "Liguria", "https://www.comune.savona.it/it", False),
    ("Siena", "Toscana", "https://www.comune.siena.it/", False),
    ("Tempio Pausania", "Sardegna", "https://comune.tempiopausania.ss.it/", True),
    ("Terni", "Umbria", "https://www.comune.terni.it/", False),
    ("Tortolì", "Sardegna", "https://www.comune.tortoli.nu.it/it", True),
    ("Udine", "Friuli-Venezia Giulia", "https://www.comune.udine.it/", False),
    ("Urbino", "Marche", "https://www.comune.urbino.pu.it/", True),
    ("Vibo Valentia", "Calabria", "https://www.comune.vibovalentia.vv.it/", False),
    ("Villacidro", "Sardegna", "https://www.comune.villacidro.su.it/", True),
)

MUNICIPAL_CAPITAL_SOURCE_DEFINITIONS = [
    _municipality(city, region, base_url, territorial_hub=territorial_hub)
    for city, region, base_url, territorial_hub in _MUNICIPALITY_ROWS
]

REGIONAL_MUNICIPAL_SOURCE_DEFINITIONS = [
    *REGIONAL_SOURCE_DEFINITIONS,
    *MUNICIPAL_CAPITAL_SOURCE_DEFINITIONS,
]

REGIONAL_MUNICIPAL_SOURCE_NAMES = {
    definition["name"] for definition in REGIONAL_MUNICIPAL_SOURCE_DEFINITIONS
}
