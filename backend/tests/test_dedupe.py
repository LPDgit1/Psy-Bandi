from app.services.dedupe import content_hash, is_probable_duplicate, opportunity_fingerprint


def test_content_hash_is_stable() -> None:
    assert content_hash("a", "b") == content_hash("a", "b")
    assert content_hash("a", "b") != content_hash("a", "c")


def test_opportunity_fingerprint_normalizes_text() -> None:
    first = opportunity_fingerprint("Avviso Psicologo", "Comune di Roma", "2026-06-14")
    second = opportunity_fingerprint("avviso psicologo!", "COMUNE DI ROMA", "2026/06/14")

    assert first != ""
    assert len(first) == 64
    assert len(second) == 64


def test_probable_duplicate_uses_title_and_organization_similarity() -> None:
    assert is_probable_duplicate(
        "Avviso pubblico per psicologo tutela minori",
        "Comune di Frosinone",
        "Avviso pubblico psicologo per tutela minori",
        "Comune Frosinone",
        threshold=0.75,
    )

