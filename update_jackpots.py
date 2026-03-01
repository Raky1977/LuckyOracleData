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
            found = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if found:
                res = found.group(1).replace('&nbsp;', ' ').strip().upper()
                res = re.sub(r'<.*?>', '', res)
                return f"${res}" if not res.startswith('$') else res
    except Exception as e:
        print(f"Errore su {url}: {e}")
    return None

def update_data():
    # --- LOGICA POWERBALL ---
    pb_live = get_jackpot_from_source(
        "https://www.lottery.net/powerball", 
        r'class="jackpot">.*?\$([0-9.,]+\s?(?:Million|Billion|M|B))'
    )
    if not pb_live:
        pb_live = get_jackpot_from_source(
            "https://data.usatoday.com/lottery/", 
            r'Powerball.*?\$([0-9,.]+\s?(?:Million|Billion))'
        )

    # --- LOGICA MEGA MILLIONS ---
    # Proviamo Lottery.net con pattern specifico
    mega_live = get_jackpot_from_source(
        "https://www.lottery.net/mega-millions", 
        r'class="jackpot">.*?\$([0-9.,]+\s?(?:Million|Billion|M|B))'
    )
    
    # Se fallisce, proviamo USA TODAY
    if not mega_live:
        mega_live = get_jackpot_from_source(
            "https://data.usatoday.com/lottery/", 
            r'Mega\s?Millions.*?\$([0-9,.]+\s?(?:Million|Billion))'
        )
    
    # Se fallisce ancora, proviamo LotteryPost
    if not mega_live:
        mega_live = get_jackpot_from_source(
            "https://www.lotterypost.com/game/159", 
            r'(\$[0-9,.]+(?:\s|&nbsp;)?(?:Million|Billion|M|B))'
        )

    # TIMESTAMP E CALCOLI
    now = datetime.datetime.now()
    next_ts = int((now + datetime.timedelta(days=2)).replace(hour=23, minute=0).timestamp() * 1000)

    # COSTRUZIONE JSON
    data = {
        "powerball_jackpot": pb_live if pb_live else "$249 MILLION",
        "mega_jackpot": mega_live if mega_live else "$420 MILLION",
        "next_draw_timestamp": next_ts,
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "success" if (pb_live and mega_live) else "partial_fallback"
    }

    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"Risultato Finale: PB={pb_live}, MEGA={mega_live}")

if __name__ == "__main__":
    update_data()
