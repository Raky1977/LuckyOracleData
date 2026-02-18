import json
import datetime
import time

def get_next_draw_date():
    # Powerball estrae Lunedì (0), Mercoledì (2), Sabato (5) alle 23:00 ET
    now = datetime.datetime.now()
    # Simuliamo il calcolo della prossima estrazione (molto semplificato)
    # Aggiunge 3 giorni alla data attuale per far sì che il timer sia sempre vivo
    next_draw = now + datetime.timedelta(days=3)
    return int(next_draw.timestamp() * 1000)

def update_data():
    # Qui in futuro metteremo lo scraping dei siti USA
    # Per ora automatizziamo la data per tenere vivo il timer
    data = {
        "powerball_jackpot": "$560 MILLION",
        "mega_jackpot": "$1.5 BILLION",
        "next_draw_timestamp": get_next_draw_date(),
        "last_update": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    update_data()
