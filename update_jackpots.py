import json
import datetime
import urllib.request
import re

def get_jackpot_from_source(url, pattern):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8', errors='ignore')
            # Cerchiamo il pattern ignorando maiuscole/minuscole e spazi strani
            found = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if found:
                res = found.group(1).replace('&nbsp;', ' ').strip().upper()
                res = re.sub(r'<.*?>', '', res) # Rimuove eventuali tag HTML residui
                return f"${res}" if not res.startswith('$') else res
    except Exception as e:
        print(f"Errore su {url}: {e}")
    return None

def update_data():
    # --- LOGICA POWERBALL (Sembrava già funzionare, manteniamo le fonti) ---
    pb_live = get_jackpot_from_source(
        "https://www.lottery.net/powerball", 
        r'class="jackpot">.*?\$([0-9.,]+\s?(?:Million|Billion|M|B))'
    )
    if not pb_live:
        pb_live = get_jackpot_from_source(
            "https://data.usatoday.com/lottery/", 
            r'Powerball.*?\$([0-9,.]+\s?(?:Million|Billion))'
        )

    # --- NUOVA LOGICA MEGA MILLIONS POTENZIATA ---
    # 1. Proviamo Lottery.net con pattern flessibile per lo spazio tra "Mega" e "Millions"
    mega_live = get_jackpot_from_source(
        "https://www.lottery.net/mega-millions", 
        r'Mega\s*Millions.*?\$([0-9.,]+\s?(?:Million|Billion|M|B))'
    )
    
    # 2. Se fallisce, proviamo USA TODAY con pattern flessibile
    if not mega_live:
        mega_live = get_jackpot_from_source(
            "https://data.usatoday.com/lottery/", 
            r'Mega\s*Millions.*?\$([0-9,.]+\s?(?:Million|Billion))'
        )
    
    # 3. Se fallisce ancora, proviamo Lotto.net (fonte alternativa molto pulita)
    if not mega_live:
        mega_live = get_jackpot_from_source(
            "https://www.lotto.net/mega-millions",
            r'class="jackpot">.*?\$([0-9.,]+\s?[A-Z]+)'
        )

    # 4. Ultima spiaggia: LotteryPost
    if not mega_live:
        mega_live = get_jackpot_from_source(
            "https://www.lotterypost.com/game/159", 
            r'(\$[0-9,.]+(?:\s|&nbsp;)?(?:Million|Billion|M|B))'
        )

    # TIMESTAMP E CALCOLI DATA
    now = datetime.datetime.now()
    next_ts = int((now + datetime.timedelta(days=2)).replace(hour=23, minute=0).timestamp() * 1000)

    # COSTRUZIONE JSON CON NUOVI VALORI DI FALLBACK PER TEST
    # Se vedi 251 o 421 significa che ha usato questi valori fissi (FALLBACK)
    data = {
        "powerball_jackpot": pb_live if pb_live else "$251 MILLION",
        "mega_jackpot": mega_live if mega_live else "$421 MILLION",
        "next_draw_timestamp": next_ts,
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "success" if (pb_live and mega_live) else "partial_fallback"
    }

    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"Risultato Finale: PB={pb_live}, MEGA={mega_live}")

if __name__ == "__main__":
    update_data()
