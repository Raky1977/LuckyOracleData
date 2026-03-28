import requests
import json
from collections import Counter

def update_powerball():
    # Scarichiamo gli ultimi 1000 risultati dal database ufficiale di New York
    url = "https://data.ny.gov/resource/d6yy-dbnr.json?$limit=1000"
    try:
        response = requests.get(url)
        data = response.json()

        all_numbers = []
        all_pb = []
        recent_draws = []

        for draw in data:
            # Il formato ufficiale è una stringa "01 02 03 04 05 06"
            nums_str = draw.get("winning_numbers", "")
            nums = [int(n) for n in nums_str.split()]
            
            if len(nums) == 6:
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

        # Calcoliamo i 10 numeri più frequenti e i 10 meno frequenti
        stats = {
            "last_update": data[0].get("draw_date", "")[:10],
            "recent_draws": recent_draws,
            "hot_numbers": [n for n, c in Counter(all_numbers).most_common(10)],
            "cold_numbers": [n for n, c in Counter(all_numbers).most_common()[:-11:-1]],
            "frequent_pb": [n for n, c in Counter(all_pb).most_common(5)]
        }

        with open("powerball_stats.json", "w") as f:
            json.dump(stats, f, indent=4)
        print("Successo: Statistiche aggiornate!")

    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    update_powerball()
