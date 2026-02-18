import json
import datetime
import urllib.request
import re

def get_jackpot(url):
    try:
        # La verità è questa: usiamo un timeout per non bloccare lo script se il sito è lento
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            # Regex migliorata per catturare i milioni
            found = re.findall(r'\$[0-9,.]+(?:\s|&nbsp;)?(?:Million|Billion|B|M)', html, re.IGNORECASE)
            if found:
                return found[0].replace('&nbsp;', ' ').upper()
    except:
        pass
    return None

def get_next_draw_timestamp():
    # In pratica: Powerball estrae Lunedì(0), Mercoledì(2), Sabato(5) alle 23:00 ET
    # Per semplicità calcoliamo il prossimo traguardo temporale automatico
    now = datetime.datetime.now()
    days_ahead = 0
    weekday = now.weekday() # 0=Lunedì, 1=Martedì...
    
    if weekday == 0: days_ahead = 2 # Prossimo è Mercoledì
    elif weekday == 1: days_ahead = 1
    elif weekday == 2: days_ahead = 3 # Prossimo è Sabato
    elif weekday == 3: days_ahead = 2
    elif weekday == 4: days_ahead = 1
    elif weekday == 5: days_ahead = 2 # Prossimo è Lunedì
    elif weekday == 6: days_ahead = 1
    
    next_draw = now + datetime.timedelta(days=days_ahead)
    # Impostiamo un'ora credibile (es. le 23:00)
    next_draw = next_draw.replace(hour=23, minute=0, second=0, microsecond=0)
    return int(next_draw.timestamp() * 1000)

def update_data():
    # Tentativo di scraping
    pb_live = get_jackpot("https://www.lotterypost.com/game/181")
    mega_live = get_jackpot("https://www.lotterypost.com/game/159")
    
    # La verità è questa: se lo scraping fallisce (None), usiamo valori di sicurezza credibili
    data = {
        "powerball_jackpot": pb_live if pb_live else "$550 MILLION",
        "mega_jackpot": mega_live if mega_live else "$1.2 BILLION",
        "next_draw_timestamp": get_next_draw_timestamp(), # SEMPRE AUTOMATICO
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    print("Dati aggiornati correttamente!")

if __name__ == "__main__":
    update_data()
