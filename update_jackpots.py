import json
import datetime
import time

def update_data():
    # In futuro qui metteremo lo scraping reale. 
    # Per ora simuliamo i dati per testare l'app.
    next_draw = int(time.time() * 1000) + (3600 * 4 * 1000) # Prossima estrazione tra 4 ore
    
    data = {
        "powerball_jackpot": "$520 MILLION",
        "mega_jackpot": "$1.2 BILLION",
        "next_draw_timestamp": next_draw,
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    update_data()
