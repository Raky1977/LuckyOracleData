#!/usr/bin/env python3
"""
Update ONLY Powerball and Mega Millions jackpot fields in lottery_data.json.

Powerball:
- Official Powerball site, using strict jackpot patterns.
- NY Lottery official fallback.

Mega Millions:
- Official Mega Millions homepage / winning numbers page.
- STRICTLY parses only the value associated with:
    "Next Estimated Jackpot"
  (or localized equivalent)
- It will NOT scan generic dollar amounts, so recent-winner prizes such as
  $5 Million cannot be mistaken for the jackpot.

If a fresh value cannot be found, the previous valid value is preserved.
All unrelated JSON keys remain untouched.
"""

from __future__ import annotations

import html as html_lib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "lottery_data.json"
TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,it;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

POWERBALL_SOURCES = [
    ("Powerball.com", "https://www.powerball.com/"),
    ("NY Lottery Powerball", "https://nylottery.ny.gov/draw-game/?game=powerball"),
]

MEGA_SOURCES = [
    ("MegaMillions homepage", "https://www.megamillions.com/"),
    ("MegaMillions winning numbers", "https://www.megamillions.com/Winning-Numbers.aspx"),
]


def fetch(url: str) -> str:
    print(f"Fetching: {url}")
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    print(f"HTTP {r.status_code} | {len(r.text)} chars | final={r.url}")
    r.raise_for_status()
    return r.text


def normalize_text(raw: str) -> str:
    raw = html_lib.unescape(raw or "")
    raw = raw.replace(r"\u0024", "$")
    raw = raw.replace(r"\u0020", " ")
    raw = raw.replace(r"\u002C", ",").replace(r"\u002c", ",")
    raw = raw.replace("\\/", "/")
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def soup_text(raw: str) -> str:
    soup = BeautifulSoup(raw, "html.parser")
    return normalize_text(" ".join(soup.stripped_strings))


def format_amount(number: str, unit: str | None) -> str:
    value = float(number.replace(",", "").replace("$", "").strip())
    unit = (unit or "").lower()

    if unit.startswith("b"):
        if 0.01 <= value <= 10:
            return f"${value:g} BILLION"
        raise ValueError(f"Implausible billion jackpot: {value}")

    if unit.startswith("m"):
        if 1 <= value <= 5000:
            return f"${value:g} MILLION"
        raise ValueError(f"Implausible million jackpot: {value}")

    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:g} BILLION"
    if value >= 1_000_000:
        return f"${value / 1_000_000:g} MILLION"

    raise ValueError(f"Implausible jackpot amount: {value}")


def extract_powerball(raw: str) -> str:
    text = soup_text(raw)

    patterns = [
        r"Estimated\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
        r"Next\s+Estimated\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
    ]

    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return format_amount(m.group(1), m.group(2))

    # Raw HTML / embedded JSON fallback, still anchored to jackpot wording.
    raw_text = normalize_text(raw)
    for pat in patterns:
        m = re.search(pat, raw_text, flags=re.IGNORECASE)
        if m:
            return format_amount(m.group(1), m.group(2))

    raise ValueError("Powerball Estimated Jackpot not found")


def extract_mega_strict(raw: str) -> str:
    """
    Mega Millions parser deliberately ONLY accepts a dollar amount
    immediately associated with 'Next Estimated Jackpot' / localized
    equivalents. It never scans arbitrary $X Million values.
    """

    text_variants = [
        soup_text(raw),
        normalize_text(raw),
    ]

    # English + Italian wording (the site may be browser-translated in user view,
    # but GitHub normally receives English; keeping both makes parser tolerant).
    labels = [
        r"Next\s+Estimated\s+Jackpot",
        r"Prossimo\s+jackpot\s+stimato",
    ]

    patterns = []
    for label in labels:
        patterns.extend([
            rf"{label}\s*:?\s*\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
            rf"{label}\s*:?\s*\$?\s*([0-9][0-9,]{{5,}})",
        ])

    for text in text_variants:
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                unit = m.group(2) if m.lastindex and m.lastindex >= 2 else None
                value = format_amount(m.group(1), unit)
                print(f"Mega strict match: {value}")
                return value

    # Meta tags are allowed only if they contain the exact jackpot label.
    soup = BeautifulSoup(raw, "html.parser")
    for meta in soup.find_all("meta"):
        content = meta.get("content") or ""
        if not re.search(
            r"(Next\s+Estimated\s+Jackpot|Prossimo\s+jackpot\s+stimato)",
            content,
            flags=re.IGNORECASE,
        ):
            continue

        for pat in patterns:
            m = re.search(pat, normalize_text(content), flags=re.IGNORECASE)
            if m:
                unit = m.group(2) if m.lastindex and m.lastindex >= 2 else None
                value = format_amount(m.group(1), unit)
                print(f"Mega strict meta match: {value}")
                return value

    raise ValueError("Mega Millions 'Next Estimated Jackpot' not found")


def get_from_sources(sources, parser, label: str) -> str:
    errors = []
    for source_name, url in sources:
        try:
            value = parser(fetch(url))
            print(f"SUCCESS {source_name}: {value}")
            return value
        except Exception as exc:
            msg = f"{source_name}: {exc}"
            print(f"WARNING {msg}", file=sys.stderr)
            errors.append(msg)

    raise RuntimeError(" | ".join(errors))


def load_data() -> dict:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Missing {DATA_FILE}")
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> int:
    data = load_data()
    jackpots = data.setdefault("jackpots", {})

    old_pb = data.get("powerball_jackpot") or jackpots.get("powerball")
    old_mm = data.get("mega_jackpot") or jackpots.get("mega_millions")

    fresh_pb = None
    fresh_mm = None

    try:
        fresh_pb = get_from_sources(
            POWERBALL_SOURCES, extract_powerball, "Powerball"
        )
    except Exception as exc:
        print(f"ERROR Powerball: {exc}", file=sys.stderr)

    try:
        fresh_mm = get_from_sources(
            MEGA_SOURCES, extract_mega_strict, "Mega Millions"
        )
    except Exception as exc:
        print(f"ERROR Mega Millions: {exc}", file=sys.stderr)

    pb = fresh_pb or old_pb
    mm = fresh_mm or old_mm

    if not pb or not mm:
        print("ERROR: no fresh value and no previous fallback available", file=sys.stderr)
        return 1

    data["powerball_jackpot"] = pb
    jackpots["powerball"] = pb
    data["mega_jackpot"] = mm
    jackpots["mega_millions"] = mm

    if fresh_pb or fresh_mm:
        stamp = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        data["jackpots_last_update"] = stamp
        if isinstance(data.get("stats"), dict):
            data["stats"]["last_update"] = stamp

    save_data(data)

    print("\nFINAL VALUES")
    print("Powerball:", pb, "(fresh)" if fresh_pb else "(kept previous)")
    print("Mega Millions:", mm, "(fresh)" if fresh_mm else "(kept previous)")
    print("Updated:", data.get("jackpots_last_update"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
