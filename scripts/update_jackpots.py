#!/usr/bin/env python3
"""
Update ONLY Powerball and Mega Millions jackpot fields in lottery_data.json.

Powerball:
- Official Powerball site/page parsing (working behavior retained)

Mega Millions:
- Official Mega Millions internal endpoint used by megamillions.com itself:
  POST /cmspages/utilservice.asmx/GetLatestDrawData
- Reads Jackpot.NextPrizePool from returned JSON.

If a fresh value cannot be fetched, the previous valid value is preserved.
All unrelated lottery_data.json keys remain untouched.
"""

from __future__ import annotations

import gzip
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
    "Accept-Language": "en-US,en;q=0.9",
}

POWERBALL_URL = "https://www.powerball.com/"
POWERBALL_FALLBACK = "https://nylottery.ny.gov/draw-game/?game=powerball"

MEGA_ENDPOINT = "https://www.megamillions.com/cmspages/utilservice.asmx/GetLatestDrawData"


def normalize_text(raw: str) -> str:
    raw = html_lib.unescape(raw or "")
    raw = raw.replace(r"\u0024", "$")
    raw = raw.replace(r"\u0020", " ")
    raw = raw.replace(r"\u002C", ",").replace(r"\u002c", ",")
    return re.sub(r"\s+", " ", raw).strip()


def format_amount(number: str, unit: str | None) -> str:
    value = float(number.replace(",", "").replace("$", "").strip())
    unit = (unit or "").lower()

    if unit.startswith("b"):
        return f"${value:g} BILLION"
    if unit.startswith("m"):
        return f"${value:g} MILLION"

    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:g} BILLION"
    if value >= 1_000_000:
        return f"${value / 1_000_000:g} MILLION"

    raise ValueError(f"Unexpected jackpot amount: {value}")


def fetch_html(url: str) -> str:
    print(f"Fetching: {url}")
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    print(f"HTTP {r.status_code} | {len(r.text)} chars")
    r.raise_for_status()
    return r.text


def extract_powerball(raw: str) -> str:
    soup = BeautifulSoup(raw, "html.parser")
    text = normalize_text(" ".join(soup.stripped_strings))

    patterns = [
        r"Estimated\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
        r"Next\s+Estimated\s+Jackpot\s*:?\s*\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
    ]

    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return format_amount(m.group(1), m.group(2))

    raw_text = normalize_text(raw)
    for pat in patterns:
        m = re.search(pat, raw_text, flags=re.IGNORECASE)
        if m:
            return format_amount(m.group(1), m.group(2))

    raise ValueError("Powerball Estimated Jackpot not found")


def get_powerball() -> str:
    errors = []
    for label, url in [
        ("Powerball.com", POWERBALL_URL),
        ("NY Lottery Powerball", POWERBALL_FALLBACK),
    ]:
        try:
            value = extract_powerball(fetch_html(url))
            print(f"SUCCESS {label}: {value}")
            return value
        except Exception as exc:
            msg = f"{label}: {exc}"
            print(f"WARNING {msg}", file=sys.stderr)
            errors.append(msg)
    raise RuntimeError(" | ".join(errors))


def get_mega_millions() -> str:
    print(f"POST: {MEGA_ENDPOINT}")

    headers = dict(HEADERS)
    headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Origin": "https://www.megamillions.com",
        "Referer": "https://www.megamillions.com/",
        "X-Requested-With": "XMLHttpRequest",
    })

    response = requests.post(
        MEGA_ENDPOINT,
        headers=headers,
        data="",
        timeout=TIMEOUT,
    )

    print(
        f"HTTP {response.status_code} | "
        f"{len(response.content)} bytes | "
        f"encoding={response.headers.get('Content-Encoding')}"
    )
    response.raise_for_status()

    raw = response.content

    # requests usually decompresses gzip automatically. This is only a
    # defensive fallback for servers/proxies returning raw gzip bytes.
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)

    text = raw.decode(response.encoding or "utf-8", errors="replace")
    outer = json.loads(text)

    # ASP.NET ASMX commonly returns {"d": "<JSON string>"}
    payload = outer.get("d", outer) if isinstance(outer, dict) else outer

    # Some representations may wrap it as {"string":{"#text":"..."}}
    if isinstance(payload, dict) and "string" in payload:
        string_obj = payload["string"]
        if isinstance(string_obj, dict) and "#text" in string_obj:
            payload = string_obj["#text"]

    if isinstance(payload, str):
        payload = json.loads(payload)

    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected Mega Millions payload type: {type(payload).__name__}")

    jackpot = payload.get("Jackpot") or payload.get("jackpot")
    if not isinstance(jackpot, dict):
        raise ValueError("Mega Millions payload has no Jackpot object")

    next_pool = (
        jackpot.get("NextPrizePool")
        or jackpot.get("nextPrizePool")
        or jackpot.get("NextPrizeAmount")
    )

    if next_pool is None:
        raise ValueError(
            "Mega Millions Jackpot object has no NextPrizePool. "
            f"Available keys: {list(jackpot.keys())}"
        )

    # Endpoint historically returns a numeric full-dollar value.
    if isinstance(next_pool, (int, float)):
        value = format_amount(str(next_pool), None)
    else:
        s = str(next_pool).strip()

        # Accept "$100 Million" if API format has changed.
        m = re.search(
            r"\$?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(Billion|Million)",
            s,
            flags=re.IGNORECASE,
        )
        if m:
            value = format_amount(m.group(1), m.group(2))
        else:
            value = format_amount(s, None)

    print(f"SUCCESS MegaMillions official API: {value}")
    return value


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
        fresh_pb = get_powerball()
    except Exception as exc:
        print(f"ERROR Powerball: {exc}", file=sys.stderr)

    try:
        fresh_mm = get_mega_millions()
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
