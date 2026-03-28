import requests
import json
from collections import Counter

def update_powerball():
    # Fonte Governativa USA (Dataset storico ufficiale)
    # Questo è un CSV, molto più difficile da bloccare per i server
    url = "https://data.ny.gov/api/views/d6yy-dbnr/rows.csv?accessType=DOWNLOAD"
    
    print("Scaricamento CSV dal database governativo...")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        lines = response.text.splitlines()
        # Rimuoviamo l'intestazione
        header = lines[0]
        data_lines = lines[1:101] # Prendiamo le ultime 100 estrazioni per le statistiche

        all_numbers = []
        all_pb = []
        recent_draws = []

        for line in data_lines:
            # Il CSV è: Date, Winning Numbers, Multiplier
            parts = line.split(',')
            if len(parts) < 2: continue
            
            date_str = parts[0]
            nums_str = parts[1].strip('"') # Rimuove eventuali virgolette
            
            nums = [int(n) for n in nums_str.split()]
            if len(nums) == 6:
                main_nums = nums[:5]
                pb = nums[5]
                all_numbers.extend(main_nums)
                all_pb.append(pb)
                
                if len(recent_draws) < 10:
                    recent_draws.append({
                        "date": date_str,
                        "numbers": main_nums,
                        "pb": pb
                    })

        stats = {
            "last_update": recent_draws[0]["date"] if recent_draws else "N/A",
            "recent_draws": recent_draws,
            "hot_numbers": [n for n, c in Counter(all_numbers).most_common(10)],
            "cold_numbers": [n for n, c in Counter(all_numbers).most_common()[:-11:-1]],
            "frequent_pb": [n for n, c in Counter(all_pb).most_common(5)]
        }

        with open("powerball_stats.json", "w") as f:
            json.dump(stats, f, indent=4)
        
        print("CE L'ABBIAMO FATTA: powerball_stats.json generato dal CSV governativo!")

    except Exception as e:
        print(f"ERRORE: {e}")

if __name__ == "__main__":
    update_powerball()
