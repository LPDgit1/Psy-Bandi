from __future__ import annotations

import re
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
ITALIAN_MONTHS = {
    "gen": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "mag": 5,
    "giu": 6,
    "lug": 7,
    "ago": 8,
    "set": 9,
    "ott": 10,
    "nov": 11,
    "dic": 12,
}
DATE_TOKEN_PATTERN = re.compile(
    r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}\s+[a-z]{3,12}\s+\d{4}",
    flags=re.IGNORECASE,
)


def parse_date(value: str | datetime | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=ROME)

    text = value.strip()
    date_only_iso_match = re.fullmatch(r"\d{4}-\d{2}-\d{2}", text)
    if date_only_iso_match:
        return datetime.combine(
            datetime.fromisoformat(text).date(),
            time(23, 59),
            tzinfo=ROME,
        )

    iso_match = re.match(r"^\d{4}-\d{2}-\d{2}", text)
    if iso_match:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=ROME)

    numeric_match = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", text)
    textual_match = re.search(r"(\d{1,2})\s+([a-z]{3,9})\s+(\d{4})", text.lower())
    if numeric_match:
        day, month, year = numeric_match.groups()
        month_number = int(month)
    elif textual_match and textual_match.group(2)[:3] in ITALIAN_MONTHS:
        day, month, year = textual_match.groups()
        month_number = ITALIAN_MONTHS[month[:3]]
    else:
        return None

    full_year = int(year)
    if full_year < 100:
        full_year += 2000

    return datetime.combine(
        datetime(full_year, month_number, int(day)).date(),
        time(23, 59),
        tzinfo=ROME,
    )


def parse_latest_date(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = [parse_date(match.group(0)) for match in DATE_TOKEN_PATTERN.finditer(value)]
    dates = [candidate for candidate in parsed if candidate is not None]
    return max(dates) if dates else None


def infer_status(deadline: datetime | None, now: datetime | None = None) -> str:
    if deadline is None:
        return "review"
    current = now or datetime.now(UTC)
    comparable_deadline = deadline.astimezone(UTC)
    days_left = (comparable_deadline - current).days
    if days_left < 0:
        return "closed"
    if days_left <= 7:
        return "closing_soon"
    return "open"
