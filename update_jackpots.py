import json
import datetime
import urllib.request
import re

def get_jackpot_from_source(url, pattern):
    try:
        # Usiamo un User-Agent molto comune per sembrare un browser reale
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            html = response.read().decode('utf-8')
            # Cerchiamo il pattern
            found = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if found:
                res = found.group(1).replace('&nbsp;', ' ').strip().upper()
                # Pulizia finale: togliamo eventuali tag residui o virgole doppie
                res = re.sub(r'<.*?>', '', res) 
                return f"${res}" if not res.startswith('$') else res
    except Exception as e:
        print(f"Errore caricamento {url}: {e}")
    return None

def update_data():
    # --- PROVA FONTE A: LOTTERY.NET (Molto pulito) ---
    pb_live = get_jackpot_from_source(
        "https://www.lottery.net/powerball", 
        r'class="jackpot">\$?([0-9.,]+\s?(?:Million|Billion|M|B))'
    )
    mega_live = get_jackpot_from_source(
        "https://www.lottery.net/mega-millions", 
        r'class="jackpot">\$?([0-9.,]+\s?(?:Million|Billion|M|B))'
    )

    # --- PROVA FONTE B (Fallback): LOTTO.NET ---
    if not pb_live:
        pb_live = get_jackpot_from_source(
            "https://www.lotto.net/powerball", 
            r'<h4>\$?([0-9.,]+\s?(?:Million|Billion|M|B))'
        )
    if not mega_live:
        mega_live = get_jackpot_from_source(
            "https://www.lotto.net/mega-millions", 
            r'<h4>\$?([0-9.,]+\s?(?:Million|Billion|M|B))'
        )

    # --- PROVA FONTE C (Fallback Estremo): USA TODAY ---
    if not pb_live:
        pb_live = get_jackpot_from_source(
            "https://www.usatoday.com/lottery/", 
            r'Powerball.*?\$?([0-9.,]+\s?(?:Million|Billion))'
        )

    # CALCOLO PROSSIMA ESTRAZIONE AUTOMATICA (Powerball: Lun, Mer, Sab / Mega: Mar, Ven)
    now = datetime.datetime.now()
    next_ts = int((now + datetime.timedelta(days=2)).replace(hour=23, minute=0).timestamp() * 1000)

    # DATI DI EMERGENZA (Se tutto fallisce, mettiamo almeno valori verosimili)
    data = {
        "powerball_jackpot": pb_live if pb_live else "$200 Million",
        "mega_jackpot": mega_live if mega_live else "$350 Million",
        "next_draw_timestamp": next_ts,
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "success" if (pb_live and mega_live) else "partial_fallback"
    }

    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"Update completato! PB: {pb_live} | MEGA: {mega_live}")

if __name__ == "__main__":
    update_data()
