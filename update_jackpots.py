import json
import datetime
import urllib.request
import re

def fetch_raw(url):
    try:
        # Mimiamo un browser mobile iPhone - raramente bloccato dai widget
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=25) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Errore su {url}: {e}")
        return ""

def extract_jackpot(text, game_keyword):
    # Cerca la cifra (es: 250) seguita da Million/Billion vicino al nome del gioco
    pattern = rf'{game_keyword}.*?\$([0-9.,]+\s?(?:Million|Billion|M|B))'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return f"${match.group(1).upper()}"
    return None

def update_data():
    # FONTE 1: Portale News USA (USA Today Network) - Molto stabile
    raw_html = fetch_raw("https://www.lohud.com/lottery/")
    
    pb_live = extract_jackpot(raw_html, "Powerball")
    mega_live = extract_jackpot(raw_html, "Mega Millions")

    # FONTE 2 (Fallback): Un sito di risultati "leggero"
    if not pb_live or not mega_live:
        raw_html_alt = fetch_raw("https://www.lotteryusa.com/powerball/")
        if not pb_live: pb_live = extract_jackpot(raw_html_alt, "Powerball")
        raw_html_alt2 = fetch_raw("https://www.lotteryusa.com/mega-millions/")
        if not mega_live: mega_live = extract_jackpot(raw_html_alt2, "Mega Millions")

    # TIMESTAMP
    now = datetime.datetime.now()
    next_ts = int((now + datetime.timedelta(days=2)).replace(hour=23, minute=0).timestamp() * 1000)

    # OUTPUT
    data = {
        "powerball_jackpot": pb_live if pb_live else "$259 MILLION", # Valore spia aggiornato
        "mega_jackpot": mega_live if mega_live else "$451 MILLION", # Valore spia aggiornato
        "next_draw_timestamp": next_ts,
        "last_update": now.strftime("%Y-%m-%d %H:%M"),
        "status": "success" if (pb_live and mega_live) else "partial_fallback"
    }

    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"Update: PB={pb_live}, MEGA={mega_live}")

if __name__ == "__main__":
    update_data()
