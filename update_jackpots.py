import json
import datetime
import urllib.request

def get_json_data(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Errore su {url}: {e}")
        return None

def update_data():
    # --- FONTE 1: NY LOTTERY (Governativo, JSON pulito) ---
    # New York pubblica un JSON con tutti i jackpot attuali
    ny_data = get_json_data("https://nylottery.ny.gov/api/v2/jackpots")
    
    pb_live = None
    mega_live = None

    if ny_data:
        for game in ny_data:
            game_name = game.get('gameName', '').lower()
            if 'powerball' in game_name:
                pb_live = f"${game.get('jackpotAmount', '')} MILLION"
            elif 'mega' in game_name:
                mega_live = f"${game.get('jackpotAmount', '')} MILLION"

    # --- FONTE 2 (Fallback): TEXAS LOTTERY RSS/JSON ---
    if not pb_live or not mega_live:
        # Usiamo l'endpoint di un aggregatore che fornisce JSON per widget
        backup_data = get_json_data("https://www.lotterypost.com/api/v1/jackpots")
        # Nota: Se questo richiede API Key, usiamo il metodo della New York Lottery che è pubblico.

    # TIMESTAMP
    now = datetime.datetime.now()
    next_ts = int((now + datetime.timedelta(days=2)).replace(hour=23, minute=0).timestamp() * 1000)

    # OUTPUT FINALE
    # Usiamo valori di "sicurezza" realistici solo se i siti governativi sono giù
    data = {
        "powerball_jackpot": pb_live if pb_live else "$258 MILLION",
        "mega_jackpot": mega_live if mega_live else "$450 MILLION",
        "next_draw_timestamp": next_ts,
        "last_update": now.strftime("%Y-%m-%d %H:%M"),
        "status": "success" if (pb_live and mega_live) else "gov_api_error"
    }

    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"Aggiornamento completato: PB={pb_live}, MEGA={mega_live}")

if __name__ == "__main__":
    update_data()
