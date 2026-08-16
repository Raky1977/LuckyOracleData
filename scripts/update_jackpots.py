#!/usr/bin/env python3
"""
Update ONLY Powerball and Mega Millions jackpot fields in lottery_data.json.

Powerball logic is kept compatible with the working v3 behavior.

Mega Millions v4:
  1) Official Winning Numbers page (primary)
  2) Official Jackpot History page
  3) Official homepage
  4) NY Lottery official page (fallback)

For Mega Millions the parser inspects:
- visible text
- raw HTML
- meta description / OpenGraph / Twitter metadata
- HTML attributes
- embedded JSON/script strings

If a fresh value cannot be obtained, the previous valid value is preserved.
All unrelated lottery_data.json keys remain untouched.
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

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

POWERBALL_SOURCES = [
    ("Powerball.com", "https://www.powerball.com/"),
    ("NY Lottery Powerball", "https://nylottery.ny.gov/draw-game/?game=powerball"),
]

MEGA_SOURCES = [
    ("MegaMillions winning numbers", "https://www.megamillions.com/winning-numbers.aspx"),
    ("MegaMillions jackpot history", "https://www.megamillions.com/jackpot-history"),
    ("MegaMillions homepage", "https://www.megamillions.com/"),
    ("NY Lottery Mega Millions", "https://nylottery.ny.gov/draw-game/?game=megamillions"),
]


def fetch(url: str, headers: dict | None = None) -> str:
    h = dict(DEFAULT_HEADERS)
    if headers:
        h.update(headers)
    print(f"Fetching: {url}")
    r = requests.get(url, headers=h, timeout=TIMEOUT, allow_redirects=True)
    print(f"HTTP {r.status_code} | {len(r.text)} chars | final={r.url}")
    r.raise_for_status()
    return r.text


def normalize_spaces(s: str) -> str:
    s = html_lib.unescape(s or "")
    replacements = {
        r"\u0024": "$",
        r"\u0020": " ",
        r"\u002C": ",",
        r"\u002c": ",",
        r"\u002E": ".",
        r"\u002e": ".",
        r"\/": "/",
        "\\\"": '"',
        "\\'": "'",
        "&nbsp;": " ",
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    return re.sub(r"\s+", " ", s).strip()


def amount_to_display(number: str, unit: str | None = None) -> str:
    n = float(number.replace(",", "").replace("$", "").strip())
    u = (unit or "").lower()

    if u.startswith("b"):
        if 0.01 <= n <= 10:
            return f"${n:g} BILLION"
        raise ValueError(f"Implausible billion jackpot: {n}")

    if u.startswith("m"):
        if 1 <= n <= 5000:
            return f"${n:g} MILLION"
        raise ValueError(f"Implausible million jackpot: {n}")

    if n >= 1_000_000_000:
        return f"${n / 1_000_000_000:g} BILLION"
    if n >= 1_000_000:
        return f"${n / 1_000_000:g} MILLION"

    raise ValueError(f"Implausible jackpot amount: {n}")


def parse_amount_near_jackpot(text: str) -> str:
    text = normalize_spaces(text)

    patterns = [
        r"Next\s+Estimated\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
        r"Estimated\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
        r"Next\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
        r"Jackpot\s*:?\s*\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
        r"Next\s+Estimated\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]{5,})",
        r"Estimated\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]{5,})",
    ]

    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            unit = m.group(2) if m.lastindex and m.lastindex >= 2 else None
            return amount_to_display(m.group(1), unit)

    raise ValueError("Estimated jackpot pattern not found")


def parse_meta_descriptions(raw: str) -> str:
    soup = BeautifulSoup(raw, "html.parser")

    values = []
    for tag in soup.find_all("meta"):
        name = (tag.get("name") or tag.get("property") or "").lower()
        if name in {
            "description",
            "og:description",
            "twitter:description",
            "twitter:title",
            "og:title",
        }:
            content = tag.get("content")
            if content:
                values.append(content)

    if not values:
        raise ValueError("No useful metadata found")

    print("Metadata candidates:")
    for value in values:
        preview = normalize_spaces(value)[:300]
        print("  META:", preview)
        try:
            return parse_amount_near_jackpot(value)
        except Exception:
            pass

    raise ValueError("Jackpot not found in metadata")


def parse_attributes(raw: str) -> str:
    soup = BeautifulSoup(raw, "html.parser")

    jackpot_words = (
        "jackpot", "estimated", "prize", "amount",
        "next-jackpot", "nextjackpot", "estimatedjackpot",
    )

    candidates = []
    for tag in soup.find_all(True):
        attrs = tag.attrs or {}
        joined_keys = " ".join(str(k).lower() for k in attrs.keys())
        joined_vals = " ".join(
            " ".join(v) if isinstance(v, list) else str(v)
            for v in attrs.values()
        )

        combined = f"{joined_keys} {joined_vals}"
        if any(word in combined.lower() for word in jackpot_words):
            candidates.append(combined)

    for candidate in candidates:
        try:
            return parse_amount_near_jackpot(candidate)
        except Exception:
            # Some attributes may only contain "$100 Million".
            m = re.search(
                r"\$\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
                normalize_spaces(candidate),
                flags=re.IGNORECASE,
            )
            if m and "jackpot" in candidate.lower():
                return amount_to_display(m.group(1), m.group(2))

    raise ValueError("Jackpot not found in HTML attributes")


def parse_raw_and_scripts(raw: str) -> str:
    # 1. Raw HTML with tags turned into spaces, while script contents remain.
    text = re.sub(r"<[^>]+>", " ", html_lib.unescape(raw))
    text = normalize_spaces(text)

    try:
        return parse_amount_near_jackpot(text)
    except Exception:
        pass

    # 2. Common JSON/property names.
    property_patterns = [
        r'["\']?(?:nextEstimatedJackpot|estimatedJackpot|nextJackpot|jackpotAmount|advertisedJackpot|jackpot)["\']?'
        r'\s*[:=]\s*["\']?\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)',
        r'["\']?(?:nextEstimatedJackpot|estimatedJackpot|nextJackpot|jackpotAmount|advertisedJackpot)["\']?'
        r'\s*[:=]\s*["\']?\$?\s*([0-9][0-9,]{5,})',
    ]

    decoded = normalize_spaces(raw)
    for pat in property_patterns:
        m = re.search(pat, decoded, flags=re.IGNORECASE)
        if m:
            unit = m.group(2) if m.lastindex and m.lastindex >= 2 else None
            return amount_to_display(m.group(1), unit)

    raise ValueError("Jackpot not found in raw HTML/scripts")


def parse_mega(raw: str) -> str:
    parsers = [
        ("metadata", parse_meta_descriptions),
        ("raw/scripts", parse_raw_and_scripts),
        ("attributes", parse_attributes),
    ]

    errors = []
    for label, parser in parsers:
        try:
            value = parser(raw)
            print(f"Mega parsed via {label}: {value}")
            return value
        except Exception as exc:
            errors.append(f"{label}: {exc}")

    raise ValueError(" | ".join(errors))


def parse_powerball(raw: str) -> str:
    # Keep the successful v3-style logic simple.
    try:
        return parse_raw_and_scripts(raw)
    except Exception:
        return parse_meta_descriptions(raw)


def get_from_sources(sources, parser, game_label: str) -> str:
    errors = []

    for label, url in sources:
        try:
            raw = fetch(url)
            value = parser(raw)
            print(f"SUCCESS {label}: {value}")
            return value
        except Exception as exc:
            msg = f"{label}: {exc}"
            print(f"WARNING {msg}", file=sys.stderr)
            errors.append(msg)

    # Final Mega-only retry using a crawler-like UA because the official
    # site may server-render jackpot metadata differently for crawlers.
    if game_label == "Mega Millions":
        crawler_headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; Googlebot/2.1; "
                "+http://www.google.com/bot.html)"
            )
        }
        url = "https://www.megamillions.com/winning-numbers.aspx"
        try:
            print("Retrying Mega Millions official page with crawler UA")
            raw = fetch(url, crawler_headers)
            value = parser(raw)
            print(f"SUCCESS MegaMillions crawler-rendered metadata: {value}")
            return value
        except Exception as exc:
            errors.append(f"Mega crawler retry: {exc}")

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
            POWERBALL_SOURCES, parse_powerball, "Powerball"
        )
    except Exception as exc:
        print(f"ERROR Powerball: {exc}", file=sys.stderr)

    try:
        fresh_mm = get_from_sources(
            MEGA_SOURCES, parse_mega, "Mega Millions"
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
