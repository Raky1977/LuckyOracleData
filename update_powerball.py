import requests
import json
from collections import Counter

def update_powerball():
    # URL aggiornato e più stabile
    url = "https://data.ny.gov/resource/d6yy-dbnr.json"
    params = {"$limit": 1000}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    print(f"Tentativo di scaricamento dati Powerball...")
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        all_numbers = []
        all_pb = []
        recent_draws = []

        for draw in data:
            nums_str = draw.get("winning_numbers", "")
            if not nums_str: continue
            
            nums = [int(n) for n in nums_str.split()]
            if len(nums) >= 6:
                main_nums = nums[:5]
                pb = nums[5]
                all_numbers.extend(main_nums)
                all_pb.append(pb)
                
                if len(recent_draws) < 10:
                    recent_draws.append({
                        "date": draw.get("draw_date", "")[:10],
                        "numbers": main_nums,
                        "pb": pb
                    })

        stats = {
            "last_update": data[0].get("draw_date", "")[:10],
            "recent_draws": recent_draws,
            "hot_numbers": [n for n, c in Counter(all_numbers).most_common(10)],
            "cold_numbers": [n for n, c in Counter(all_numbers).most_common()[:-11:-1]],
            "frequent_pb": [n for n, c in Counter(all_pb).most_common(5)]
        }

        with open("powerball_stats.json", "w") as f:
            json.dump(stats, f, indent=4)
        
        print("SUCCESSO: powerball_stats.json creato!")

    except Exception as e:
        print(f"ERRORE CRITICO POWERBALL: {e}")

if __name__ == "__main__":
    update_powerball()
