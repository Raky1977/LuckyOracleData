import json
import datetime
import urllib.request
import re

def get_jackpot_via_search(query):
    try:
        # Interroghiamo DuckDuckGo (molto più permissivo di Google per gli script)
        url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=20) as response:
            html = response.read().decode('utf-8', errors='ignore')
            # Cerchiamo la cifra seguita da Million/Billion nel testo dei risultati
            match = re.search(r'\$([0-9.,]+\s?(?:Million|Billion|M|B))', html, re.I)
            if match:
                return f"${match.group(1).upper()}"
    except Exception as e:
        print(f"Errore ricerca per {query}: {e}")
    return None

def update_data():
    # Cerchiamo i jackpot come farebbe un utente su un motore di ricerca
    pb_live = get_jackpot_via_search("current powerball jackpot amount")
    mega_live = get_jackpot_via_search("current mega millions jackpot amount")

    # TIMESTAMP
    now = datetime.datetime.now()
    next_ts = int((now + datetime.timedelta(days=2)).replace(hour=23, minute=0).timestamp() * 1000)

    # VALORI DI TEST (Se vedi 111 o 222, allora anche la ricerca è fallita)
    data = {
        "powerball_jackpot": pb_live if pb_live else "$111 MILLION",
        "mega_jackpot": mega_live if mega_live else "$222 MILLION",
        "next_draw_timestamp": next_ts,
        "last_update": now.strftime("%Y-%m-%d %H:%M"),
        "status": "success" if (pb_live and mega_live) else "partial_fallback"
    }

    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"Risultato: PB={pb_live}, MEGA={mega_live}")

if __name__ == "__main__":
    update_data()
