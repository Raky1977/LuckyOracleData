import json
import datetime
import urllib.request
import re

def get_jackpot_from_source(url, pattern):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/json'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8', errors='ignore')
            found = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if found:
                res = found.group(1).replace('&nbsp;', ' ').strip().upper()
                # Rimuove virgole e tag
                res = re.sub(r'<.*?>', '', res)
                return f"${res}" if not res.startswith('$') else res
    except Exception as e:
        print(f"Errore su {url}: {e}")
    return None

def update_data():
    # --- POWERBALL: Fonte USA Today (Più permissiva) ---
    pb_live = get_jackpot_from_source(
        "https://data.usatoday.com/lottery/", 
        r'Powerball.*?\$([0-9,.]+\s?(?:Million|Billion))'
    )
    
    # --- MEGA MILLIONS: Fonte specifica di un giornale locale (Meno protetta) ---
    mega_live = get_jackpot_from_source(
        "https://www.lohud.com/lottery/", 
        r'Mega\s*Millions.*?\$([0-9,.]+\s?(?:Million|Billion))'
    )

    # Se falliscono, proviamo una fonte JSON "nuda"
    if not pb_live or not mega_live:
        print("Tentativo di emergenza su fonte alternativa...")
        if not pb_live:
            pb_live = get_jackpot_from_source("https://www.lottery.net/powerball", r'class="jackpot">.*?\$([0-9.,]+\s?[A-Z]+)')
        if not mega_live:
            mega_live = get_jackpot_from_source("https://www.lottery.net/mega-millions", r'class="jackpot">.*?\$([0-9.,]+\s?[A-Z]+)')

    # TIMESTAMP
    now = datetime.datetime.now()
    next_ts = int((now + datetime.timedelta(days=2)).replace(hour=23, minute=0).timestamp() * 1000)

    # VALORI DI TEST (Ora mettiamo numeri assurdi per essere sicuri al 100% se sono loro)
    # Se vedi 999 o 888 significa che NON ha funzionato lo scraping.
    data = {
        "powerball_jackpot": pb_live if pb_live else "$999 MILLION",
        "mega_jackpot": mega_live if mega_live else "$888 MILLION",
        "next_draw_timestamp": next_ts,
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "success" if (pb_live and mega_live) else "partial_fallback"
    }

    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"Update: PB={pb_live}, MEGA={mega_live}")

if __name__ == "__main__":
    update_data()
