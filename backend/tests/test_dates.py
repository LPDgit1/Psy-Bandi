from datetime import UTC, datetime

from app.services.dates import infer_status, parse_date, parse_latest_date


def test_parse_italian_date_sets_end_of_day() -> None:
    parsed = parse_date("14/06/2026")

    assert parsed is not None
    assert parsed.day == 14
    assert parsed.month == 6
    assert parsed.hour == 23
    assert parsed.minute == 59


def test_parse_iso_date() -> None:
    parsed = parse_date("2026-06-14")

    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 6
    assert parsed.day == 14
    assert parsed.hour == 23
    assert parsed.minute == 59


def test_parse_latest_date_prefers_deadline_over_publication_date() -> None:
    parsed = parse_latest_date("Pubblicazione 10/06/2026 - termine 30/06/2026")

    assert parsed is not None
    assert parsed.date().isoformat() == "2026-06-30"


def test_parse_italian_dot_date() -> None:
    parsed = parse_date("30.06.2026 23:59:59")

    assert parsed is not None
    assert parsed.date().isoformat() == "2026-06-30"


def test_parse_italian_textual_date() -> None:
    parsed = parse_date("Scade il 17 giugno 2026 il termine.")

    assert parsed is not None
    assert parsed.date().isoformat() == "2026-06-17"


def test_infer_status_closing_soon() -> None:
    now = datetime(2026, 5, 29, 12, 0, tzinfo=UTC)
    deadline = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)

    assert infer_status(deadline, now=now) == "closing_soon"
