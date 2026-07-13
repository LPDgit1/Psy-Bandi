from app.services.classifier import classify_text, normalize_text


def test_normalize_text_removes_accents_and_punctuation() -> None:
    assert normalize_text("Psicologia dell'eta evolutiva!") == "psicologia dell eta evolutiva"


def test_classifies_high_relevance_psychologist_notice() -> None:
    result = classify_text(
        "Avviso pubblico per psicologo",
        "Richiesta laurea in psicologia e iscrizione all'albo degli psicologi.",
    )

    assert result.psychology_relevance == "alta"
    assert result.relevance_score >= 70
    assert "iscrizione-albo" in result.requirements
    assert result.category == "avviso-pubblico"


def test_detects_school_and_family_areas() -> None:
    result = classify_text(
        "Sportello ascolto scolastico",
        "Supporto psicologico per studenti, minori e famiglie.",
    )

    assert "psicologia-scolastica" in result.areas
    assert "minori-famiglia" in result.areas


def test_detects_primary_care_and_psychosocial_terms() -> None:
    result = classify_text(
        "Avviso per psicologo di base",
        "Servizio psicologico nelle cure primarie e interventi psicosociali.",
    )

    assert result.psychology_relevance in {"alta", "media"}
    assert "cure-primarie" in result.areas
    assert "salute-mentale" in result.areas


def test_detects_less_obvious_psychology_requirements_and_areas() -> None:
    result = classify_text(
        "Selezione esperto area trattamentale",
        (
            "Richiesta laurea magistrale LM-51 o classe 58/S, iscrizione "
            "all'albo psicologi e competenze psicodiagnostiche in istituto "
            "penitenziario."
        ),
    )

    assert result.psychology_relevance in {"alta", "media"}
    assert "laurea-psicologia" in result.requirements
    assert "iscrizione-albo" in result.requirements
    assert "psicodiagnostica" in result.areas
    assert "psicologia-penitenziaria" in result.areas


def test_detects_psychoeducational_and_cognitive_rehabilitation_terms() -> None:
    result = classify_text(
        "Avviso per interventi psicoeducativi",
        "Attivita psicosociali in salute mentale e riabilitazione cognitiva.",
    )

    assert result.psychology_relevance in {"alta", "media", "bassa"}
    assert "salute-mentale" in result.areas
    assert "neuropsicologia" in result.areas
    assert "abilitazione" not in result.requirements


def test_excludes_unrelated_notice() -> None:
    result = classify_text("Concorso istruttore amministrativo", "Gestione protocollo e atti.")

    assert result.psychology_relevance == "esclusa"
    assert result.relevance_score == 0
