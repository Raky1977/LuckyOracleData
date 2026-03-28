import requests
import json
import re
from collections import Counter

def update_powerball():
    # Usiamo una pagina HTML pubblica (meno protetta delle API)
    url = "https://www.lotterypost.com/game/11/results"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    print("Ricerca numeri reali Powerball...")

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        html = response.text

        # Cerchiamo i numeri vincenti nel testo HTML usando una Regex
        # Cerchiamo pattern tipo: "24, 25, 30, 41, 52 + 10"
        draw_matches = re.findall(r'(\d{1,2}), (\d{1,2}), (\d{1,2}), (\d{1,2}), (\d{1,2}) \+ (\d{1,2})', html)

        if not draw_matches:
            print("Nessun numero trovato nella pagina. Provo fonte alternativa...")
            # Qui potremmo aggiungere un secondo sito se il primo fallisce
            return

        all_numbers = []
        all_pb = []
        recent_draws = []

        # Elaboriamo i primi 20 risultati reali trovati
        for match in draw_matches[:20]:
            nums = [int(n) for n in match[:5]]
            pb = int(match[5])
            
            all_numbers.extend(nums)
            all_pb.append(pb)
            
            if len(recent_draws) < 5:
                recent_draws.append({
                    "numbers": nums,
                    "pb": pb
                })

        # Calcoliamo le statistiche sui numeri VERI trovati
        stats = {
            "last_update": "March 2026",
            "recent_draws": recent_draws,
            "hot_numbers": [n for n, c in Counter(all_numbers).most_common(10)],
            "cold_numbers": [n for n, c in Counter(all_numbers).most_common()[:-11:-1]],
            "frequent_pb": [n for n, c in Counter(all_pb).most_common(5)]
        }

        with open("powerball_stats.json", "w") as f:
            json.dump(stats, f, indent=4)
        
        print(f"SUCCESSO! Ho trovato {len(draw_matches)} estrazioni reali e aggiornato il file.")

    except Exception as e:
        print(f"Errore durante il recupero dei dati reali: {e}")

if __name__ == "__main__":
    update_powerball()
