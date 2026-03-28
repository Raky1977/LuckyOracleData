import requests
import json
from collections import Counter

def update_powerball():
    # Usiamo un'API alternativa più "gentile" con i bot
    url = "https://games.api.lottery.com/api/v2.0/results/games/powerball/draws"
    params = {"limit": 50} # Prendiamo le ultime 50 estrazioni
    
    print("Connessione all'API alternativa...")
    
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        draws = response.json()

        all_numbers = []
        all_pb = []
        recent_list = []

        for draw in draws:
            # Estraiamo i numeri dal formato specifico di questa API
            results = draw.get("results", [])
            if not results: continue
            
            # Di solito i primi 5 sono i numeri bianchi, l'ultimo è la Powerball
            main_nums = [int(r.get("value")) for r in results if r.get("type") == "primary"]
            pb_val = next((int(r.get("value")) for r in results if r.get("type") == "bonus"), None)
            
            if len(main_nums) == 5 and pb_val is not None:
                all_numbers.extend(main_nums)
                all_pb.append(pb_val)
                
                if len(recent_list) < 10:
                    recent_list.append({
                        "date": draw.get("drawDate", "")[:10],
                        "numbers": main_nums,
                        "pb": pb_val
                    })

        stats = {
            "last_update": recent_list[0]["date"] if recent_list else "N/A",
            "recent_draws": recent_list,
            "hot_numbers": [n for n, c in Counter(all_numbers).most_common(10)],
            "cold_numbers": [n for n, c in Counter(all_numbers).most_common()[:-11:-1]],
            "frequent_pb": [n for n, c in Counter(all_pb).most_common(5)]
        }

        with open("powerball_stats.json", "w") as f:
            json.dump(stats, f, indent=4)
        
        print("FINALMENTE: powerball_stats.json generato!")

    except Exception as e:
        print(f"ERRORE: {e}")
        # Se fallisce anche questo, creiamo un file di emergenza per non far crashare l'app
        fallback = {"status": "error", "reason": str(e)}
        with open("powerball_stats.json", "w") as f:
            json.dump(fallback, f)

if __name__ == "__main__":
    update_powerball()
