import json
import datetime
import urllib.request
import re

def get_jackpot_from_source(url, pattern):
    try:
        # Usiamo un User-Agent "reale" e header che mimano un browser Chrome su Windows
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        req = urllib.request.Request(url, headers=headers)
        # Aumentiamo il timeout a 30 secondi
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8', errors='ignore')
            # Cerchiamo il valore del jackpot ignorando tutto ciò che sta in mezzo (tag, spazi)
            found = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if found:
                # Prendiamo solo la parte numerica e l'unità (Million/Billion)
                res = found.group(1).replace('&nbsp;', ' ').strip().upper()
                # Pulizia tag HTML se presenti
                res = re.sub(r'<.*?>', '', res)
                return f"${res}" if not res.startswith('$') else res
    except Exception as e:
        print(f"Errore su {url}: {e}")
    return None

def update_data():
    # --- FONTE 1: LOTTO.NET (Struttura semplice) ---
    pb_live = get_jackpot_from_source(
        "https://www.lotto.net/powerball", 
        r'class="jackpot">.*?\$([0-9.,]+\s?(?:Million|Billion|M|B))'
    )
    mega_live = get_jackpot_from_source(
        "https://www.lotto.net/mega-millions", 
        r'class="jackpot">.*?\$([0-9.,]+\s?(?:Million|Billion|M|B))'
    )

    # --- FONTE 2: USA TODAY (Widget News) ---
    if not pb_live:
        pb_live = get_jackpot_from_source(
            "https://www.usatoday.com/lottery/", 
            r'Powerball.*?\$([0-9,.]+\s?(?:Million|Billion))'
        )
    if not mega_live:
        mega_live = get_jackpot_from_source(
            "https://www.usatoday.com/lottery/", 
            r'Mega\s?Millions.*?\$([0-9,.]+\s?(?:Million|Billion))'
        )

    # --- FONTE 3: STATI SPECIFICI (Es: Texas Lottery che è meno protetta) ---
    if not pb_live:
        pb_live = get_jackpot_from_source(
            "https://www.txlottery.org/export/sites/lottery/index.html",
            r'Powerball.*?\$([0-9,.]+\s?Million)'
        )

    # TIMESTAMP
    now = datetime.datetime.now()
    next_ts = int((now + datetime.timedelta(days=2)).replace(hour=23, minute=0).timestamp() * 1000)

    # COSTRUZIONE JSON
    data = {
        "powerball_jackpot": pb_live if pb_live else "$200 Million",
        "mega_jackpot": mega_live if mega_live else "$350 Million",
        "next_draw_timestamp": next_ts,
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "success" if (pb_live and mega_live) else "partial_fallback"
    }

    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"Risultato: PB={pb_live}, MEGA={mega_live}")

if __name__ == "__main__":
    update_data()
