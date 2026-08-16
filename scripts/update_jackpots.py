#!/usr/bin/env python3
"""Update only Powerball/Mega Millions jackpot fields in lottery_data.json.

Primary source: New York Lottery official draw-game pages.
Fallback for Powerball: official powerball.com draw-result page.
The script intentionally leaves every unrelated key untouched and never writes
an empty/zero jackpot when a source fetch or parse fails.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "lottery_data.json"
TIMEOUT = 25
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LuckyOracleUSA-JackpotUpdater/1.0; +https://github.com/)"
}

NY_URLS = {
    # These official NY Lottery live-drawing pages expose Estimated Jackpot
    # as server-readable text (not only inside client-side JavaScript).
    "powerball": "https://nylottery.ny.gov/live-drawings/powerball?playlistID=external",
    "mega_millions": "https://nylottery.ny.gov/live-drawings/megamillions?playlistID=external",
}
NY_DRAW_FALLBACKS = {
    "powerball": "https://nylottery.ny.gov/draw-game?game=powerball",
    "mega_millions": "https://nylottery.ny.gov/draw-game?game=megamillions",
}
POWERBALL_FALLBACK = "https://www.powerball.com/draw-result"


def fetch(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text


def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    return " ".join(soup.stripped_strings)


def format_amount(number: str, unit: str | None = None) -> str:
    value = float(number.replace(",", ""))
    unit = (unit or "").upper()
    if unit == "BILLION":
        return f"${value:g} BILLION"
    if unit == "MILLION":
        return f"${value:g} MILLION"

    # NY Lottery often renders the full dollar amount, e.g. $542,000,000.
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:g} BILLION"
    if value >= 1_000_000:
        return f"${value / 1_000_000:g} MILLION"
    raise ValueError(f"Unexpected jackpot amount: {number}")


def extract_ny_jackpot(html: str) -> str:
    text = clean_text(html)
    patterns = [
        # Dedicated draw page commonly exposes: Estimated Jackpot $ 542,000,000
        r"Estimated\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(BILLION|MILLION)?",
        # Alternate compact markup.
        r"Jackpot\s*\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(BILLION|MILLION)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return format_amount(match.group(1), match.group(2))
    raise ValueError("Estimated Jackpot not found on NY Lottery page")


def extract_powerball_fallback(html: str) -> str:
    text = clean_text(html)
    patterns = [
        r"Estimated\s+Jackpot\s*:?\s*\$\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
        r"\$\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)\s+Cash\s+Value",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return format_amount(match.group(1), match.group(2))
    raise ValueError("Estimated Jackpot not found on Powerball page")


def get_jackpot(game: str) -> str:
    errors: list[str] = []
    try:
        return extract_ny_jackpot(fetch(NY_URLS[game]))
    except Exception as exc:
        errors.append(f"NY Lottery live page: {exc}")

    try:
        return extract_ny_jackpot(fetch(NY_DRAW_FALLBACKS[game]))
    except Exception as exc:
        errors.append(f"NY Lottery draw page: {exc}")

    if game == "powerball":
        try:
            return extract_powerball_fallback(fetch(POWERBALL_FALLBACK))
        except Exception as exc:
            errors.append(f"Powerball.com: {exc}")

    raise RuntimeError("; ".join(errors))


def load_data() -> dict:
    if not DATA_FILE.exists():
        return {}
    with DATA_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    data = load_data()
    jackpots = data.setdefault("jackpots", {})

    previous_pb = data.get("powerball_jackpot") or jackpots.get("powerball")
    previous_mega = data.get("mega_jackpot") or jackpots.get("mega_millions")

    updated_any = False

    for game, flat_key, nested_key, previous in [
        ("powerball", "powerball_jackpot", "powerball", previous_pb),
        ("mega_millions", "mega_jackpot", "mega_millions", previous_mega),
    ]:
        try:
            value = get_jackpot(game)
            data[flat_key] = value
            jackpots[nested_key] = value
            print(f"{game}: {value}")
            updated_any = True
        except Exception as exc:
            print(f"WARNING {game}: {exc}", file=sys.stderr)
            if previous:
                # Preserve the last known-good value.
                data[flat_key] = previous
                jackpots[nested_key] = previous
                print(f"{game}: keeping previous value {previous}")
            else:
                print(f"ERROR {game}: no previous value available", file=sys.stderr)

    if updated_any:
        stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        data["jackpots_last_update"] = stamp
        stats = data.get("stats")
        if isinstance(stats, dict):
            stats["last_update"] = stamp

    with DATA_FILE.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
