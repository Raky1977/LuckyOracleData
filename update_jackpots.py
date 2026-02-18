import json
import datetime
import urllib.request
import re

def get_jackpot(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            # Cerchiamo cifre seguite da Million o Billion
            found = re.findall(r'\$[0-9,.]+(?:\s|&nbsp;)?(?:Million|Billion|B|M)', html)
            if found:
                return found[0].replace('&nbsp;', ' ')
    except Exception as e:
        print(f"Errore: {e}")
    return None

def update_data():
    # Usiamo fonti alternative più semplici da leggere
    pb = get_jackpot("https://www.lotterypost.com/game/181") or "$550 Million"
    mega = get_jackpot("https://www.lotterypost.com/game/159") or "$1.1 Billion"
    
    now = datetime.datetime.now()
    # Calcolo prossima estrazione semplificato per il timer
    next_draw = now + datetime.timedelta(days=2)
    
    data = {
        "powerball_jackpot": pb.upper(),
        "mega_jackpot": mega.upper(),
        "next_draw_timestamp": int(next_draw.timestamp() * 1000),
        "last_update": now.strftime("%Y-%m-%d %H:%M")
    }
    
    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    update_data()
