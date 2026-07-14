from datetime import UTC, datetime
from pathlib import Path

from app.streamlit_support import (
    cache_revision,
    format_compensation,
    format_date,
    label_for,
    safe_http_url,
)


def test_cache_revision_tracks_snapshot_and_dependency_changes(tmp_path: Path) -> None:
    snapshot = tmp_path / "bandi.sqlite"
    dependency = tmp_path / "public.py"
    dependency.write_text("version-one", encoding="utf-8")

    without_snapshot = cache_revision(snapshot, (dependency,))
    snapshot.write_bytes(b"snapshot-one")
    first_revision = cache_revision(snapshot, (dependency,))
    dependency.write_text("version-two", encoding="utf-8")
    code_revision = cache_revision(snapshot, (dependency,))
    snapshot.write_bytes(b"snapshot-two-with-different-size")
    snapshot_revision = cache_revision(snapshot, (dependency,))

    assert len({without_snapshot, first_revision, code_revision, snapshot_revision}) == 4


def test_streamlit_labels_and_formats_are_human_readable() -> None:
    assert label_for("concorso-pubblico") == "Concorso pubblico"
    assert label_for("valore-nuovo") == "valore-nuovo"
    assert format_date(datetime(2026, 7, 13, 12, 0, tzinfo=UTC)) == "13/07/2026"
    assert format_compensation(12000, 18000, "annui") == "12.000–18.000 € (annui)"


def test_safe_http_url_rejects_non_web_and_credential_urls() -> None:
    assert safe_http_url("https://example.test/bando") == "https://example.test/bando"
    assert safe_http_url("javascript:alert(1)") is None
    assert safe_http_url("data:text/html,hello") is None
    assert safe_http_url("https://user:password@example.test/bando") is None
    assert safe_http_url("/bando/locale") is None
