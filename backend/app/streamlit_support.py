from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

LABELS: dict[str, str] = {
    "avviso-pubblico": "Avviso pubblico",
    "concorso-pubblico": "Concorso pubblico",
    "incarico-libero-professionale": "Incarico libero-professionale",
    "collaborazione-consulenza": "Collaborazione/consulenza",
    "mobilita": "Mobilità",
    "borsa-assegno-ricerca": "Borsa/assegno di ricerca",
    "graduatoria-elenco-idonei": "Graduatoria/elenco",
    "manifestazione-interesse": "Manifestazione di interesse",
    "docenza-formazione": "Docenza/formazione",
    "azienda-sanitaria": "Azienda sanitaria",
    "azienda-sanitaria-ospedaliera": "Azienda sanitaria/ospedaliera",
    "comune": "Comune",
    "unione-comuni-ambito-sociale": "Unione comuni/ambito sociale",
    "regione": "Regione",
    "regione-ente-regionale": "Regione/ente regionale",
    "universita": "Università",
    "ente-ricerca": "Ente di ricerca",
    "ente-nazionale": "Ente nazionale",
    "ministero-ente-nazionale": "Ministero/ente nazionale",
    "scuola-istituto-scolastico": "Scuola/istituto scolastico",
    "terzo-settore": "Terzo settore",
    "privato-sociale": "Privato sociale",
    "altro-ente-pubblico": "Altro ente pubblico",
    "psicologia-scolastica": "Psicologia scolastica",
    "psicologia-clinica": "Psicologia clinica",
    "psicodiagnostica": "Psicodiagnostica",
    "psicoterapia": "Psicoterapia",
    "neuropsicologia": "Neuropsicologia",
    "psicologia-del-lavoro": "Psicologia del lavoro",
    "psicologia-giuridica": "Psicologia giuridica",
    "psicologia-penitenziaria": "Psicologia penitenziaria",
    "psicologia-emergenza": "Psicologia dell'emergenza",
    "dipendenze": "Dipendenze",
    "minori-famiglia": "Minori e famiglia",
    "disabilita": "Disabilità",
    "anziani": "Anziani",
    "salute-mentale": "Salute mentale",
    "servizi-sociali": "Servizi sociali",
    "ricerca": "Ricerca",
    "formazione": "Formazione",
    "orientamento": "Orientamento",
    "prevenzione-promozione-salute": "Prevenzione e promozione della salute",
    "laurea-psicologia": "Laurea in psicologia",
    "abilitazione": "Abilitazione",
    "iscrizione-albo": "Iscrizione all'albo",
    "albo-sezione-a": "Albo sezione A",
    "esperienza-minima": "Esperienza minima",
    "formazione-specifica": "Formazione specifica",
    "non-determinato": "Non determinato",
    "open": "Aperta",
    "closing_soon": "In scadenza",
    "closed": "Chiusa",
    "review": "Da verificare",
    "alta": "Alta",
    "media": "Media",
    "bassa": "Bassa",
    "esclusa": "Esclusa",
}


def label_for(value: str | None) -> str:
    if not value:
        return ""
    return LABELS.get(value, value)


def format_date(value: datetime | None) -> str:
    if value is None:
        return "Non indicata"
    return value.strftime("%d/%m/%Y")


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "Non indicato"
    return value.strftime("%d/%m/%Y, %H:%M")


def format_compensation(
    minimum: int | None,
    maximum: int | None,
    period: str | None,
) -> str:
    if minimum is None and maximum is None:
        return "Non indicato"
    if minimum is not None and maximum is not None:
        amount = f"{minimum:,}–{maximum:,} €"
    else:
        amount = f"{minimum if minimum is not None else maximum:,} €"
    amount = amount.replace(",", ".")
    return f"{amount} ({period})" if period else amount


def safe_http_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.username or parsed.password:
        return None
    return value.strip()
