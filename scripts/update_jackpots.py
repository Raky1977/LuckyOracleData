#!/usr/bin/env python3
"""
Update ONLY Powerball and Mega Millions jackpot fields in lottery_data.json.

Powerball:
  1) Official Powerball homepage
  2) New York Lottery Powerball live page
  3) New York Lottery Powerball draw page

Mega Millions:
  1) New York Lottery Mega Millions live page
  2) New York Lottery Mega Millions draw page
  3) New York Lottery homepage

If every source for a game fails, the previous valid value is preserved.
All unrelated JSON keys are left untouched.
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

TIMEOUT = 30
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

POWERBALL_HOME = "https://www.powerball.com/"
NY_POWERBALL_LIVE = "https://nylottery.ny.gov/live-drawings/powerball?playlistID=external"
NY_POWERBALL_DRAW = "https://nylottery.ny.gov/draw-game?game=powerball"

NY_MEGA_LIVE = "https://nylottery.ny.gov/live-drawings/megamillions?playlistID=external"
NY_MEGA_DRAW = "https://nylottery.ny.gov/draw-game?game=megamillions"
NY_HOME = "https://nylottery.ny.gov/"


def fetch(url: str) -> str:
    print(f"Fetching: {url}")
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    print(f"HTTP {response.status_code} | {len(response.text)} chars")
    response.raise_for_status()
    return response.text


def visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    return " ".join(soup.stripped_strings)


def normalize_amount(number: str, unit: str | None = None) -> str:
    value = float(number.replace(",", "").replace("$", "").strip())
    unit = (unit or "").upper().strip()

    if unit.startswith("B"):
        return f"${value:g} BILLION"
    if unit.startswith("M"):
        return f"${value:g} MILLION"

    # Full amount, for example 748000000
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:g} BILLION"
    if value >= 1_000_000:
        return f"${value / 1_000_000:g} MILLION"

    raise ValueError(f"Unexpected jackpot amount: {number!r} {unit!r}")


def extract_estimated_jackpot(text: str) -> str:
    """
    Handles examples such as:
      Estimated Jackpot $748 Million
      Estimated Jackpot$ 150,000,000
      Estimated Jackpot: $1.2 Billion
    """
    patterns = [
        r"Estimated\s+Jackpot\s*:?\s*\$\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
        r"Estimated\s+Jackpot\s*:?\s*\$\s*([0-9][0-9,]{5,})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            unit = m.group(2) if m.lastindex and m.lastindex >= 2 else None
            return normalize_amount(m.group(1), unit)

    raise ValueError("Estimated Jackpot value not found")


def extract_game_from_ny_home(text: str, game_name: str) -> str:
    """
    NY Lottery homepage contains several games. Restrict parsing to a
    section immediately following the requested game's name so we do not
    accidentally read another game's jackpot.
    """
    pos = text.lower().find(game_name.lower())
    if pos < 0:
        raise ValueError(f"{game_name} section not found on NY Lottery homepage")

    chunk = text[pos:pos + 1500]

    # Homepage often renders:
    # Mega Millions ... Next Drawing ... $542 MILLION Estimated Cash Value ...
    patterns = [
        r"Next\s+Drawing.*?\$\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
        r"\$\s*([0-9][0-9,]{5,})\s+Estimated\s+Cash\s+Value",
    ]
    for pattern in patterns:
        m = re.search(pattern, chunk, flags=re.IGNORECASE | re.DOTALL)
        if m:
            unit = m.group(2) if m.lastindex and m.lastindex >= 2 else None
            return normalize_amount(m.group(1), unit)

    raise ValueError(f"Jackpot not found in {game_name} NY homepage section")


def get_powerball() -> str:
    errors = []

    sources = [
        ("Powerball.com", POWERBALL_HOME, lambda t: extract_estimated_jackpot(t)),
        ("NY Lottery Powerball live", NY_POWERBALL_LIVE, lambda t: extract_estimated_jackpot(t)),
        ("NY Lottery Powerball draw", NY_POWERBALL_DRAW, lambda t: extract_estimated_jackpot(t)),
    ]

    for label, url, parser in sources:
        try:
            value = parser(visible_text(fetch(url)))
            print(f"SUCCESS {label}: {value}")
            return value
        except Exception as exc:
            msg = f"{label}: {exc}"
            print(f"WARNING {msg}", file=sys.stderr)
            errors.append(msg)

    raise RuntimeError(" | ".join(errors))


def get_mega_millions() -> str:
    errors = []

    sources = [
        ("NY Lottery Mega Millions live", NY_MEGA_LIVE, lambda t: extract_estimated_jackpot(t)),
        ("NY Lottery Mega Millions draw", NY_MEGA_DRAW, lambda t: extract_estimated_jackpot(t)),
        (
            "NY Lottery homepage",
            NY_HOME,
            lambda t: extract_game_from_ny_home(t, "Mega Millions"),
        ),
    ]

    for label, url, parser in sources:
        try:
            value = parser(visible_text(fetch(url)))
            print(f"SUCCESS {label}: {value}")
            return value
        except Exception as exc:
            msg = f"{label}: {exc}"
            print(f"WARNING {msg}", file=sys.stderr)
            errors.append(msg)

    raise RuntimeError(" | ".join(errors))


def load_data() -> dict:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Missing {DATA_FILE}")
    with DATA_FILE.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_data(data: dict) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main() -> int:
    data = load_data()
    jackpots = data.setdefault("jackpots", {})

    previous_pb = data.get("powerball_jackpot") or jackpots.get("powerball")
    previous_mega = data.get("mega_jackpot") or jackpots.get("mega_millions")

    updated_any = False

    try:
        pb = get_powerball()
        data["powerball_jackpot"] = pb
        jackpots["powerball"] = pb
        updated_any = True
    except Exception as exc:
        print(f"ERROR Powerball: {exc}", file=sys.stderr)
        if previous_pb:
            data["powerball_jackpot"] = previous_pb
            jackpots["powerball"] = previous_pb
            print(f"Powerball: keeping previous value {previous_pb}")
        else:
            return 1

    try:
        mega = get_mega_millions()
        data["mega_jackpot"] = mega
        jackpots["mega_millions"] = mega
        updated_any = True
    except Exception as exc:
        print(f"ERROR Mega Millions: {exc}", file=sys.stderr)
        if previous_mega:
            data["mega_jackpot"] = previous_mega
            jackpots["mega_millions"] = previous_mega
            print(f"Mega Millions: keeping previous value {previous_mega}")
        else:
            return 1

    if updated_any:
        stamp = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        data["jackpots_last_update"] = stamp

        stats = data.get("stats")
        if isinstance(stats, dict):
            stats["last_update"] = stamp

    save_data(data)

    print("\nFINAL VALUES")
    print("Powerball:", data.get("powerball_jackpot"))
    print("Mega Millions:", data.get("mega_jackpot"))
    print("Updated:", data.get("jackpots_last_update"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
