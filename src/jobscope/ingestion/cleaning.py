import html
import re
from datetime import datetime

import pandas as pd

REQUIRED_COLUMNS = {
    "id", "title", "company", "location", "salary",
    "posted", "tags", "description", "url", "category",
}
LOCATION_ALIASES = {
    "remote": "Worldwide",
    "worldwide": "Worldwide",
    "anywhere": "Worldwide",
    "usa only": "United States",
    "usa": "United States",
    "us": "United States",
    "united states": "United States",
    "eu": "Europe",
    "europe": "Europe",
}
DATE_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y")


_HTML_TAG = re.compile(r"<[^>]+>")
_TAG_SPLIT = re.compile(r"[,;|]")
_SALARY_NUMBER = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(k?)")


def normalize_text(value: str) -> str:
    """Trim and collapse repeated whitespace."""
    return " ".join(value.split())


def normalize_company(value: str) -> str:
    """Fix ALL CAPS or all lowercase names. Caveat: turns 'IBM' into 'Ibm'."""
    text = normalize_text(value)
    return text.title() if text.isupper() or text.islower() else text


def normalize_location(value: str) -> str:
    text = normalize_text(value)
    if not text:
        return "Unspecified"
    return LOCATION_ALIASES.get(text.casefold(), text)


def strip_html(value: str) -> str:
    return normalize_text(html.unescape(_HTML_TAG.sub(" ", value)))


def split_tags(value: str) -> list[str]:
    seen: dict[str, None] = {}
    for part in _TAG_SPLIT.split(value):
        tag = part.strip().casefold()
        if tag:
            seen[tag] = None
    return list(seen)


def parse_date(value: str) -> datetime | None:
    text = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def parse_salary(value: str) -> tuple[float, float, str] | None:
    """Return (min, max, currency) as yearly amounts, or None if unusable."""
    text = value.strip().lower()
    if not text or "hour" in text or "/hr" in text:
        return None
    currency = "EUR" if "€" in text else "GBP" if "£" in text else "USD" if "$" in text else ""
    amounts = []
    for number, suffix in _SALARY_NUMBER.findall(text):
        amount = float(number.replace(",", ""))
        amounts.append(amount * 1000 if suffix else amount)
    amounts = [a for a in amounts if a >= 1000]
    if not amounts:
        return None
    return min(amounts), max(amounts), currency


def clean_jobs(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"missing columns: {sorted(missing)}")

    out = df.copy()
    for column in ("title", "salary", "category", "url"):
        out[column] = out[column].map(normalize_text)
    out["company"] = out["company"].map(normalize_company)
    out["location"] = out["location"].map(normalize_location)
    out["tags"] = out["tags"].map(split_tags)
    out["description"] = out["description"].map(strip_html)
    out["posted_at"] = out["posted"].map(parse_date)

    salaries = out["salary"].map(parse_salary)
    out["salary_min"] = salaries.map(lambda s: s[0] if s else None)
    out["salary_max"] = salaries.map(lambda s: s[1] if s else None)
    out["salary_currency"] = salaries.map(lambda s: s[2] if s else "")

    out = out[out["title"] != ""]
    key = (
        out["title"].str.casefold()
        + "|"
        + out["company"].str.casefold()
        + "|"
        + out["posted_at"].astype(str)
    )
    return out[~key.duplicated()].reset_index(drop=True)