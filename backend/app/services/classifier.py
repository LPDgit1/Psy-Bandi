from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Classification:
    category: str
    areas: list[str]
    requirements: list[str]
    psychology_relevance: str
    relevance_score: int


PSYCHOLOGY_TERMS: dict[str, int] = {
    "psicolog": 35,
    "psicoterap": 35,
    "neuropsicolog": 35,
    "iscrizione albo psicolog": 35,
    "albo professionale degli psicolog": 35,
    "laurea in psicologia": 30,
    "lm 51": 30,
    "classe 58 s": 30,
    "abilitazione alla professione di psicolog": 30,
    "psicologia clinica": 25,
    "psicologia scolastica": 25,
    "psicologia del lavoro": 25,
    "psicologia di base": 25,
    "psicologo di base": 30,
    "psicologo cure primarie": 30,
    "psicologia delle cure primarie": 25,
    "psicologia della salute": 20,
    "psicologia di comunita": 20,
    "psicologia ospedaliera": 20,
    "psicodiagnostic": 25,
    "valutazione psicologica": 20,
    "valutazione neuropsicologica": 25,
    "test neuropsicologici": 25,
    "riabilitazione cognitiva": 25,
    "psicopedagog": 20,
    "psicoeduc": 20,
    "psicosocial": 15,
    "salute mentale": 15,
    "servizio psicologico": 25,
    "supporto psicologico": 25,
    "counseling psicologico": 20,
}

AREA_RULES: dict[str, tuple[str, ...]] = {
    "psicologia-scolastica": (
        "scuola",
        "scolastic",
        "student",
        "sportello ascolto",
        "sportello di ascolto",
    ),
    "psicologia-clinica": ("clinica", "diagnosi", "trattamento", "colloqui clinici"),
    "psicodiagnostica": (
        "psicodiagnostic",
        "test psicologici",
        "test neuropsicologici",
        "valutazione psicologica",
    ),
    "psicoterapia": ("psicoterap", "specializzazione in psicoterapia"),
    "neuropsicologia": (
        "neuropsicolog",
        "disturbi cognitivi",
        "riabilitazione cognitiva",
        "valutazione neuropsicologica",
    ),
    "psicologia-del-lavoro": ("benessere organizzativo", "risorse umane", "stress lavoro"),
    "psicologia-penitenziaria": ("istituto penitenziario", "area trattamentale", "uepe"),
    "psicologia-giuridica": ("tribunale", "ctu", "penale", "giudiziaria", "messa alla prova"),
    "psicologia-emergenza": ("emergenza", "protezione civile", "trauma"),
    "dipendenze": ("dipendenze", "serd", "tossicodipenden", "alcooldipenden"),
    "minori-famiglia": ("minori", "famiglia", "infanzia", "adolescen", "eta evolutiva"),
    "disabilita": ("disabil", "autismo", "handicap", "inclusione"),
    "anziani": ("anziani", "rsa", "demenza", "alzheimer"),
    "salute-mentale": (
        "salute mentale",
        "csm",
        "dsm",
        "psichiatria",
        "psicosocial",
        "psicoeduc",
    ),
    "cure-primarie": ("psicologo di base", "cure primarie", "psicologia di base"),
    "servizi-sociali": ("servizi sociali", "ambito territoriale", "welfare", "tutela"),
    "ricerca": ("assegno di ricerca", "borsa di ricerca", "progetto di ricerca"),
    "formazione": ("docenza", "formatore", "formazione"),
    "orientamento": ("orientamento", "career", "bilancio competenze"),
    "prevenzione-promozione-salute": ("prevenzione", "promozione salute", "screening"),
}

CATEGORY_RULES: dict[str, tuple[str, ...]] = {
    "concorso-pubblico": ("concorso pubblico", "selezione pubblica per titoli ed esami"),
    "avviso-pubblico": ("avviso pubblico", "avviso di selezione", "procedura comparativa"),
    "incarico-libero-professionale": (
        "libero professionale",
        "incarico professionale",
        "partita iva",
    ),
    "collaborazione-consulenza": ("collaborazione", "consulenza", "esperto esterno"),
    "mobilita": ("mobilita", "mobilita volontaria"),
    "borsa-assegno-ricerca": ("borsa di ricerca", "assegno di ricerca"),
    "graduatoria-elenco-idonei": ("graduatoria", "elenco idonei", "short list"),
    "manifestazione-interesse": ("manifestazione di interesse",),
    "docenza-formazione": ("docenza", "formatore", "corso di formazione"),
}

REQUIREMENT_RULES: dict[str, tuple[str, ...]] = {
    "laurea-psicologia": (
        "laurea in psicologia",
        "lm-51",
        "lm 51",
        "58/s",
        "classe 58 s",
        "classe lm 51",
        "vecchio ordinamento psicologia",
    ),
    "abilitazione": (
        "abilitazione alla professione",
        "abilitazione all esercizio",
        "abilitazione professionale",
        "abilitato alla professione",
        "abilitazione psicologo",
    ),
    "iscrizione-albo": (
        "iscrizione all'albo",
        "iscritto all'albo",
        "albo degli psicologi",
        "albo psicologi",
    ),
    "albo-sezione-a": ("sezione a", "albo a"),
    "psicoterapia": ("psicoterap", "specializzazione quadriennale"),
    "esperienza-minima": ("esperienza almeno", "esperienza minima", "comprovata esperienza"),
    "formazione-specifica": ("ecm", "master", "formazione specifica"),
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[^a-z0-9]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(normalize_text(pattern) in text for pattern in patterns)


def infer_category(text: str) -> str:
    normalized = normalize_text(text)
    for category, patterns in CATEGORY_RULES.items():
        if _contains_any(normalized, patterns):
            return category
    return "altro"


def detect_areas(text: str) -> list[str]:
    normalized = normalize_text(text)
    areas = [area for area, patterns in AREA_RULES.items() if _contains_any(normalized, patterns)]
    return areas or ["altro"]


def extract_requirements(text: str) -> list[str]:
    normalized = normalize_text(text)
    requirements = [
        requirement
        for requirement, patterns in REQUIREMENT_RULES.items()
        if _contains_any(normalized, patterns)
    ]
    return requirements or ["non-determinato"]


def relevance_score(text: str) -> int:
    normalized = normalize_text(text)
    score = 0
    for term, weight in PSYCHOLOGY_TERMS.items():
        if normalize_text(term) in normalized:
            score += weight

    if "psicolog" in normalized and "albo" in normalized:
        score += 20
    if "psicolog" in normalized and ("minori" in normalized or "salute mentale" in normalized):
        score += 10

    return min(score, 100)


def relevance_label(score: int) -> str:
    if score >= 70:
        return "alta"
    if score >= 35:
        return "media"
    if score >= 15:
        return "bassa"
    return "esclusa"


def classify_text(*parts: str | None) -> Classification:
    text = "\n".join(part for part in parts if part)
    score = relevance_score(text)
    return Classification(
        category=infer_category(text),
        areas=detect_areas(text),
        requirements=extract_requirements(text),
        psychology_relevance=relevance_label(score),
        relevance_score=score,
    )


def build_search_text(*parts: object) -> str:
    chunks: list[str] = []
    for part in parts:
        if part is None:
            continue
        if isinstance(part, list):
            chunks.extend(str(item) for item in part)
        else:
            chunks.append(str(part))
    return normalize_text(" ".join(chunks))
