import requests
from datetime import datetime
import os
import json
import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

class CoinDeskData:
    def __init__(self, coin, instrument, start_date, interval, api_key, market="cadli", limit=1000):
        self.coin = coin
        self.instrument = instrument
        self.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        self.interval = interval
        self.api_key = api_key
        self.market = market
        self.limit = limit
        self.url = f'https://data-api.coindesk.com/index/cc/v1/historical/{interval}'
        
        self.headers = {
            "Content-type": "application/json; charset=UTF-8",
            "authorization": f"Apikey {self.api_key}"
        }

        self.min_timestamps = {
            "BTC-USD": 1279324800,   # July 17, 2010
            "ETH-USD": 1438214400,   # July 30, 2015
            "XRP-USD": 1361116800,   # February 18, 2013
            "BNB-USD": 1500912000,   # July 24, 2017
            "SOL-USD": 1586563200,   # April 11, 2020
            "DOGE-USD": 1386566400,  # December 9, 2013
            "ADA-USD": 1506729600,   # September 30, 2017
            "AVAX-USD": 1599811200,  # September 11, 2020
        }
        
        self.min_timestamp = self.min_timestamps.get(self.instrument, int(self.start_date.timestamp()))

    def fetch_all_data(self):
        to_ts = int(datetime.now().timestamp())
        all_data = []
        local_min_ts = max(self.min_timestamp, int(self.start_date.timestamp()))

        while True:
            params = {
                "market": self.market,
                "instrument": self.instrument,
                "limit": self.limit,
                "aggregate": 1,
                "fill": "true",
                "apply_mapping": "true",
                "response_format": "JSON",
                "to_ts": to_ts
            }

            response = requests.get(self.url, params=params, headers=self.headers)
            try:
                res_json = response.json()
            except Exception as e:
                print(f"⚠ Failed to parse JSON for {self.coin}: {e}")
                break

            if response.status_code != 200:
                print(f"⚠ Error {response.status_code} for {self.coin} ({self.interval})")
                print(res_json)
                break

            data_chunk = res_json.get("Data", [])
            if not data_chunk:
                print(f"⚠ No data returned for {self.coin} ({self.interval})")
                break

            err_info = res_json.get("Err", {})
            if "other_info" in err_info and "first" in err_info["other_info"]:
                suggested_ts = err_info["other_info"]["first"]
                if suggested_ts > local_min_ts:
                    print(f"⚠ Adjusting min timestamp for {self.coin} ({self.interval}) → {suggested_ts}")
                    local_min_ts = suggested_ts
                    to_ts = int(datetime.now().timestamp())
                    all_data.clear()
                    continue

            all_data.extend(data_chunk)
            earliest_ts = min(d["TIMESTAMP"] for d in data_chunk)

            if earliest_ts <= local_min_ts or len(data_chunk) < self.limit:
                break

            to_ts = earliest_ts - 1
            time.sleep(0.5)

        all_data.sort(key=lambda x: x["TIMESTAMP"])
        return all_data

    def format_timestamp(self, ts):
        dt = datetime.utcfromtimestamp(ts)
        if self.interval == 'hours':
            return dt.strftime("%Y-%m-%d %H:%M")
        return dt.strftime("%Y-%m-%d")

    def save_to_csv(self, data):
        folder = f"data-{self.interval}"
        os.makedirs(folder, exist_ok=True)
        filename = os.path.join(folder, f"{self.coin}_{self.interval}_data.csv")

        headers = ["Date", "Open", "High", "Low", "Close", "Volume", "Quote Volume"]

        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for rec in data:
                writer.writerow([
                    self.format_timestamp(rec['TIMESTAMP']),
                    round(rec.get('OPEN', 0), 2),
                    round(rec.get('HIGH', 0), 2),
                    round(rec.get('LOW', 0), 2),
                    round(rec.get('CLOSE', 0), 2),
                    round(rec.get('VOLUME', 0), 2),
                    round(rec.get('QUOTE_VOLUME', 0), 2)
                ])
        print(f"✅ Saved {self.interval} data for {self.coin} → {filename} ({len(data)} rows)")

def fetch_and_save(coin, info, interval, api_key):
    client = CoinDeskData(coin, instrument=info['instrument'], start_date=info['start_date'], interval=interval,
                          api_key=api_key, market="cadli")
    print(f"⏳ Fetching {interval} data for {coin}...")
    data = client.fetch_all_data()

    if not data:
        print(f"⚠ No data for {coin} ({interval})")
        return

    client.save_to_csv(data)

if __name__ == '__main__':
    # Always load the project-level .env (one directory above Data)
    ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    load_dotenv(dotenv_path=os.path.join(ROOT_DIR, '.env'))
    API_KEY = os.getenv('COINDESK_API_KEY')
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', '4'))

    with open('symbols.json', 'r') as f:
        COINS = json.load(f)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for coin, info in COINS.items():
            for interval in ['days', 'hours']:
                futures.append(executor.submit(fetch_and_save, coin, info, interval, API_KEY))
        for future in as_completed(futures):
            future.result()
