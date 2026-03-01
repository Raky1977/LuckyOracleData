import json
import datetime
import urllib.request
import re

def fetch_raw(url):
    try:
        # User-Agent iPhone: la nostra chiave per il successo
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=25) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Errore caricamento {url}: {e}")
        return ""

def extract_jackpot(text, game_keyword):
    # Regex robusta per catturare cifre tipo "$249 Million"
    pattern = rf'{game_keyword}.*?\$([0-9.,]+\s?(?:Million|Billion|M|B))'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return f"${match.group(1).upper()}"
    return None

def update_data():
    # --- FONTE PRINCIPALE (Lohud/USA Today) ---
    # Funziona bene per Powerball, Mega Millions e Texas Lotto
    main_html = fetch_raw("https://www.lohud.com/lottery/")
    
    pb_live = extract_jackpot(main_html, "Powerball")
    mega_live = extract_jackpot(main_html, "Mega Millions")
    tx_lotto = extract_jackpot(main_html, "Lotto Texas")
    
    # --- FONTE SECONDARIA (California Lottery) ---
    ca_html = fetch_raw("https://www.calottery.com/jackpot-it")
    ca_lotto = extract_jackpot(ca_html, "SuperLotto Plus")

    # Fallback per Powerball/Mega se Lohud fallisce (usando LotteryUSA)
    if not pb_live or not mega_live:
        if not pb_live:
            pb_live = extract_jackpot(fetch_raw("https://www.lotteryusa.com/powerball/"), "Powerball")
        if not mega_live:
            mega_live = extract_jackpot(fetch_raw("https://www.lotteryusa.com/mega-millions/"), "Mega Millions")

    # Timestamp e calcoli
    now = datetime.datetime.now()
    next_ts = int((now + datetime.timedelta(days=2)).replace(hour=23, minute=0).timestamp() * 1000)

    # --- COSTRUZIONE JSON COMPLETO ---
    data = {
        "powerball_jackpot": pb_live if pb_live else "$259 MILLION",
        "mega_jackpot": mega_live if mega_live else "$475 MILLION",
        "pick3": "$500",
        "pick4": "$5,000",
        "cash4life": "$1,000/DAY",
        "luckyforlife": "$1,000/DAY",
        "california_lotto": ca_lotto if ca_lotto else "$7 MILLION",
        "texas_lotto": tx_lotto if tx_lotto else "$5.25 MILLION",
        "next_draw_timestamp": next_ts,
        "last_update": now.strftime("%Y-%m-%d %H:%M"),
        "status": "success" if (pb_live and mega_live) else "partial_fallback"
    }

    with open('lottery_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"Update completato: PB={pb_live}, MEGA={mega_live}, TX={tx_lotto}, CA={ca_lotto}")

if __name__ == "__main__":
    update_data()
