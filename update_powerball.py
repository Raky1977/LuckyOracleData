import requests
import json
from collections import Counter
import urllib3

# Disabilita gli avvisi per i certificati scaduti
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def update_powerball():
    url = "https://games.api.lottery.com/api/v2.0/results/games/powerball/draws"
    params = {"limit": 50}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    print("Tentativo di connessione (ignoro SSL)...")
    
    try:
        # verify=False risolve l'errore del certificato scaduto
        response = requests.get(url, params=params, headers=headers, timeout=20, verify=False)
        response.raise_for_status()
        draws = response.json()

        all_numbers = []
        all_pb = []
        recent_list = []

        for draw in draws:
            results = draw.get("results", [])
            if not results: continue
            
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
        
        print("SUCCESSO: powerball_stats.json creato correttamente!")

    except Exception as e:
        print(f"ERRORE: {e}")

if __name__ == "__main__":
    update_powerball()
