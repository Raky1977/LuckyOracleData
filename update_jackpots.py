import json
import datetime
import urllib.request
import re

def get_jackpot_from_source(url, pattern):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')
            found = re.search(pattern, html, re.IGNORECASE)
            if found:
                # Puliamo il risultato eliminando tag HTML o spazi extra
                res = found.group(1).replace('&nbsp;', ' ').strip().upper()
                return f"${res}" if not res.startswith('$') else res
    except Exception as e:
        print(f"Errore su {url}: {e}")
    return None

def update_data():
    # FONTE 1: LotteryUSA (Più stabile per GitHub Actions)
    # Cerchiamo il valore numerico seguito da Million/Billion
    pb_pattern = r'Powerball.*?jackpot-amount">\$?([0-9.,]+\s?(?:Million|Billion|M|B))'
    mega_pattern = r'Mega Millions.*?jackpot-amount">\$?([0-9.,]+\s?(?:Million|Billion|M|B))'
    
    pb_live = get_jackpot_from_source("https://www.lotteryusa.com/powerball/", pb_pattern)
    mega_live = get_jackpot_from_source("https://www.lotteryusa.com/mega-millions/", mega_pattern)

    # FONTE 2: Se la prima fallisce, proviamo Lottery Post (Il tuo vecchio metodo)
    if not pb_live:
        pb_live = get_jackpot_from_source("https://www.lotterypost.com/game/181", r'(\$[0-9,.]+(?:\s|&nbsp;)?(?:Million|Billion|M|B))')
    if not mega_live:
        mega_live = get_jackpot_from_source("https://www.lotterypost.com/game/159", r'(\$[0-9,.]+(?:\s|&nbsp;)?(?:Million|Billion|M|B))')

    # CALCOLO TIMESTAMP PROSSIMA ESTRAZIONE
    now = datetime.datetime.now()
    # Powerball: Lun, Mer, Sab 23:00 ET / Mega: Mar, Ven 23:00 ET
    # Per semplicità usiamo un calcolo basato su 2 giorni di distanza se non vogliamo complicare il calendario
    next_ts = int((now + datetime.timedelta(days=2)).replace(hour=23, minute=0).timestamp() * 1000)

    data = {
        "powerball_jackpot": pb_live if pb_live else "$200 MILLION",
        "mega_jackpot": mega_live if mega_live else "$350 MILLION",
        "next_draw_timestamp": next_ts,
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "success" if (pb_live and mega_live) else "partial_fallback"
    }

    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Update completato: PB={pb_live}, MEGA={mega_live}")

if __name__ == "__main__":
    update_data()
