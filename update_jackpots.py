import json
import datetime
import urllib.request
import re

def get_data_safe(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Origin': 'https://www.lotteryusa.com'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Errore caricamento {url}: {e}")
    return ""

def update_data():
    # --- FONTE A: Cerchiamo di prendere i dati da un aggregatore di news (più permissivo) ---
    # Usiamo un pattern che cerca il numero vicino alla parola jackpot
    pb_html = get_data_safe("https://www.lotteryusa.com/powerball/")
    mega_html = get_data_safe("https://www.lotteryusa.com/mega-millions/")
    
    pb_live = None
    mega_live = None

    # Regex specifica per catturare l'importo dal tag jackpot-amount
    pb_match = re.search(r'jackpot-amount">\$?([0-9.,]+\s?(?:Million|Billion|M|B))', pb_html, re.I)
    if pb_match:
        pb_live = f"${pb_match.group(1).upper()}"

    mega_match = re.search(r'jackpot-amount">\$?([0-9.,]+\s?(?:Million|Billion|M|B))', mega_html, re.I)
    if mega_match:
        mega_live = f"${mega_match.group(1).upper()}"

    # --- FONTE B (FALLBACK): Se fallisce, usiamo una fonte di emergenza diversa ---
    if not pb_live or not mega_live:
        alt_html = get_data_safe("https://data.usatoday.com/lottery/")
        if not pb_live:
            match = re.search(r'Powerball.*?\$([0-9,.]+\s?(?:Million|Billion))', alt_html, re.I | re.S)
            if match: pb_live = f"${match.group(1).upper()}"
        if not mega_live:
            match = re.search(r'Mega\s*Millions.*?\$([0-9,.]+\s?(?:Million|Billion))', alt_html, re.I | re.S)
            if match: mega_live = f"${match.group(1).upper()}"

    # TIMESTAMP
    now = datetime.datetime.now()
    next_ts = int((now + datetime.timedelta(days=2)).replace(hour=23, minute=0).timestamp() * 1000)

    # VALORI DI EMERGENZA (Se vedi 777 o 666, GitHub è ancora bloccato)
    data = {
        "powerball_jackpot": pb_live if pb_live else "$777 MILLION",
        "mega_jackpot": mega_live if mega_live else "$666 MILLION",
        "next_draw_timestamp": next_ts,
        "last_update": now.strftime("%Y-%m-%d %H:%M"),
        "status": "success" if (pb_live and mega_live) else "partial_fallback"
    }

    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"Risultato: PB={pb_live}, MEGA={mega_live}")

if __name__ == "__main__":
    update_data()
