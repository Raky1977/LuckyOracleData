#!/usr/bin/env python3
"""
Update ONLY Powerball and Mega Millions next-jackpot fields in lottery_data.json.

Official sources:
- Powerball: https://www.powerball.com/
- Mega Millions: https://www.megamillions.com/
Fallbacks:
- New York Lottery official pages.

The parser checks visible HTML AND embedded script/JSON data.
If a game cannot be parsed, its previous valid value is preserved.
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
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

SOURCES = {
    "powerball": [
        ("Powerball.com", "https://www.powerball.com/"),
        ("NY Lottery Powerball", "https://nylottery.ny.gov/draw-game/?game=powerball"),
        ("NY Lottery Powerball live", "https://nylottery.ny.gov/live-drawings/powerball?in-app-view=true&playlistID=external"),
    ],
    "mega_millions": [
        ("MegaMillions.com", "https://www.megamillions.com/"),
        ("MegaMillions winning numbers", "https://www.megamillions.com/winning-numbers.aspx"),
        ("NY Lottery Mega Millions", "https://nylottery.ny.gov/draw-game/?game=megamillions"),
        ("NY Lottery Mega Millions live", "https://nylottery.ny.gov/live-drawings/megamillions?in-app-view=true&playlistID=external"),
    ],
}


def fetch(url: str) -> str:
    print(f"Fetching: {url}")
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    print(f"HTTP {r.status_code} | {len(r.text)} chars")
    r.raise_for_status()
    return r.text


def decode_blob(raw: str) -> str:
    s = html_lib.unescape(raw)
    for old, new in {
        r"\u0024": "$",
        r"\u0020": " ",
        r"\u002C": ",",
        r"\u002c": ",",
        r"\/": "/",
        "&nbsp;": " ",
    }.items():
        s = s.replace(old, new)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s)


def visible_text(raw: str) -> str:
    soup = BeautifulSoup(raw, "html.parser")
    return re.sub(r"\s+", " ", " ".join(soup.stripped_strings))


def amount_to_display(number: str, unit: str | None) -> str:
    n = float(number.replace(",", "").replace("$", "").strip())
    u = (unit or "").lower()

    if u.startswith("b"):
        if not (0.01 <= n <= 10):
            raise ValueError(f"Implausible billion jackpot: {n}")
        return f"${n:g} BILLION"
    if u.startswith("m"):
        if not (1 <= n <= 5000):
            raise ValueError(f"Implausible million jackpot: {n}")
        return f"${n:g} MILLION"
    if n >= 1_000_000_000:
        return f"${n / 1_000_000_000:g} BILLION"
    if n >= 1_000_000:
        return f"${n / 1_000_000:g} MILLION"
    raise ValueError(f"Implausible jackpot amount: {n}")


def find_next_jackpot(raw: str, game: str) -> str:
    candidates = [decode_blob(raw), visible_text(raw)]

    patterns = [
        r"Next\s+Estimated\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
        r"Estimated\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
        r"Next\s+Estimated\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]{5,})",
        r"Estimated\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]{5,})",
        r'(?:nextEstimatedJackpot|estimatedJackpot|nextJackpot|jackpotAmount|advertisedJackpot)'
        r'["\']?\s*[:=]\s*["\']?\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)',
        r'(?:nextEstimatedJackpot|estimatedJackpot|nextJackpot|jackpotAmount|advertisedJackpot)'
        r'["\']?\s*[:=]\s*["\']?\$?\s*([0-9][0-9,]{5,})',
    ]

    for text in candidates:
        for pat in patterns:
            m = re.search(pat, text, flags=re.IGNORECASE)
            if m:
                unit = m.group(2) if m.lastindex and m.lastindex >= 2 else None
                value = amount_to_display(m.group(1), unit)
                print(f"Parsed {game}: {value}")
                return value

    text = decode_blob(raw)
    for m in re.finditer(r"jackpot", text, flags=re.IGNORECASE):
        start = max(0, m.start() - 120)
        end = min(len(text), m.end() + 250)
        chunk = text[start:end]

        money = re.search(
            r"\$\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
            chunk,
            flags=re.IGNORECASE,
        )
        if money and ("estimated" in chunk.lower() or "next" in chunk.lower()):
            return amount_to_display(money.group(1), money.group(2))

        full = re.search(r"\$\s*([0-9][0-9,]{5,})", chunk)
        if full and ("estimated" in chunk.lower() or "next" in chunk.lower()):
            return amount_to_display(full.group(1), None)

    raise ValueError("Next/Estimated Jackpot value not found in HTML or embedded data")


def get_game(game: str) -> str:
    errors = []
    for label, url in SOURCES[game]:
        try:
            value = find_next_jackpot(fetch(url), game)
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

    values = {"powerball": None, "mega_millions": None}

    for game in values:
        try:
            values[game] = get_game(game)
        except Exception as exc:
            print(f"ERROR {game}: {exc}", file=sys.stderr)

    pb = values["powerball"] or old_pb
    mm = values["mega_millions"] or old_mm

    if not pb or not mm:
        print("ERROR: missing both a fresh value and a previous fallback", file=sys.stderr)
        return 1

    data["powerball_jackpot"] = pb
    jackpots["powerball"] = pb
    data["mega_jackpot"] = mm
    jackpots["mega_millions"] = mm

    if any(values.values()):
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
    print("Powerball:", data["powerball_jackpot"], "(fresh)" if values["powerball"] else "(kept previous)")
    print("Mega Millions:", data["mega_jackpot"], "(fresh)" if values["mega_millions"] else "(kept previous)")
    print("Updated:", data.get("jackpots_last_update"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
