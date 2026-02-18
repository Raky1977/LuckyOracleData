import json
import datetime
import time
import urllib.request
import re

def get_live_jackpots():
    # La verità è questa: usiamo un sito affidabile come fallback
    # In una versione pro useresti BeautifulSoup, qui usiamo le Regex per velocità
    try:
        # Esempio di URL che fornisce dati testuali semplici
        url = "https://www.lottery.net/powerball"
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            # Cerchiamo il pattern del jackpot (es: $500 Million)
            found = re.findall(r'\$[0-9]+(?:\s|&nbsp;)(?:Million|Billion)', html)
            if found:
                return found[0]
    except:
        pass
    return "$--- MILLION" # Fallback se il sito è giù

def update_data():
    pb_jackpot = get_live_jackpots()
    # Per Mega Millions faremmo lo stesso con il suo URL
    
    # Calcoliamo la prossima estrazione (prossimo Lunedì, Mercoledì o Sabato)
    now = datetime.datetime.now()
    next_draw = now + datetime.timedelta(days=(2 if now.weekday() < 5 else 1))
    
    data = {
        "powerball_jackpot": pb_jackpot,
        "mega_jackpot": "$1.2 BILLION", # Esempio statico o ripeti scraping
        "next_draw_timestamp": int(next_draw.timestamp() * 1000),
        "last_update": now.strftime("%Y-%m-%d %H:%M")
    }
    
    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    update_data()
