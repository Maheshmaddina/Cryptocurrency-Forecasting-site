import os
from dotenv import load_dotenv
import requests
import pandas as pd
import numpy as np
import tensorflow as tf
import joblib
from datetime import datetime, timedelta

# Global cache for models and scalers to avoid reloading
_MODEL_CACHE = {}
_SCALER_CACHE = {}

def get_live_data(symbol="BTC", interval="1h", usd_to_inr=88.75):
    symbol_map = {
        "ADA": "ADAUSDT", "AVAX": "AVAXUSDT", "BNB": "BNBUSDT", "BTC": "BTCUSDT", 
        "DOGE": "DOGEUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "XRP": "XRPUSDT"
    }
    pair = symbol_map.get(symbol.upper(), "BTCUSDT")
    limit = 30 if interval == "1d" else 24 

    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": pair, "interval": interval, "limit": limit}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        df = pd.DataFrame(data, columns=[
            "open_time","open","high","low","close","volume",
            "close_time","quote_volume","num_trades","taker_base","taker_quote","ignore"
        ])

        for col in ["open","high","low","close"]:
            df[col] = df[col].astype(float) * usd_to_inr
        df["volume"] = df["volume"].astype(float)

        df.index = pd.to_datetime(df["close_time"], unit='ms')

        df_result = df[["open","high","low","close","volume"]]
        df_result.columns = ["Open", "High", "Low", "Close", "Volume"]
        return df_result
    except Exception as e:
        print(f"[ERROR] Fetching live data: {e}")
        return None

def get_realtime_price(symbol="BTC", usd_to_inr=88.75):
    """Fetches the real-time price for a symbol from Binance ticker."""
    symbol_map = {
        "ADA": "ADAUSDT", "AVAX": "AVAXUSDT", "BNB": "BNBUSDT", "BTC": "BTCUSDT", 
        "DOGE": "DOGEUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "XRP": "XRPUSDT"
    }
    pair = symbol_map.get(symbol.upper())
    if not pair:
        print(f"[ERROR] Invalid symbol for real-time price: {symbol}")
        return None

    url = "https://api.binance.com/api/v3/ticker/price"
    params = {"symbol": pair}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        price_usd = float(data['price'])
        print(f"[INFO] Real-time price for {symbol}: ${price_usd:.2f}")
        return price_usd * usd_to_inr
    except Exception as e:
        print(f"[ERROR] Fetching real-time price for {symbol}: {e}")
        return None


def load_model_and_scaler(symbol="BTC", interval="1h"):
    # Create cache key
    cache_key = f"{symbol}_{interval}"
    
    # Check if already cached
    if cache_key in _MODEL_CACHE and cache_key in _SCALER_CACHE:
        print(f"[INFO] Using cached model and scaler for {symbol} {interval}")
        return _MODEL_CACHE[cache_key], _SCALER_CACHE[cache_key]
    
    base_folder = 'models_hourly' if interval == "1h" else 'models_daily'
    model_file = f"{symbol}_{'hourly' if interval=='1h' else 'daily'}_lstm.keras"
    scaler_file = f"{symbol}_scaler.pkl"

    model_path = os.path.join(os.path.dirname(__file__), base_folder, model_file)
    scaler_path = os.path.join(os.path.dirname(__file__), base_folder, scaler_file)

    if not os.path.exists(model_path):
        print(f"[ERROR] Model file not found: {model_path}")
        return None, None
    if not os.path.exists(scaler_path):
        print(f"[ERROR] Scaler file not found: {scaler_path}")
        return None, None

    try:
        model = tf.keras.models.load_model(model_path)
        scaler = joblib.load(scaler_path)
        
        # Cache the loaded model and scaler
        _MODEL_CACHE[cache_key] = model
        _SCALER_CACHE[cache_key] = scaler
        
        print(f"[INFO] Successfully loaded and cached model and scaler for {symbol} {interval}")
        return model, scaler
    except Exception as e:
        print(f"[ERROR] Loading model/scaler for {symbol} {interval}: {e}")
        return None, None


def get_live_prediction(symbol="BTC", interval="1h", steps_ahead=3, usd_to_inr=88.75):
    window_size = 30 if interval=="1d" else 24

    df = get_live_data(symbol, interval, usd_to_inr)
    if df is None or df.empty:
        return None

    model, scaler = load_model_and_scaler(symbol, interval)
    if model is None or scaler is None:
        return None

    scaled_data = scaler.transform(df)
    X_input = np.expand_dims(scaled_data[-window_size:], axis=0)

    predictions_scaled = []
    current_input = X_input.copy()

    for _ in range(steps_ahead):
        pred = model.predict(current_input, verbose=0)
        predictions_scaled.append(pred[0])
        current_input = np.append(current_input[:,1:,:], np.expand_dims(pred, axis=1), axis=1)

    predictions = scaler.inverse_transform(np.array(predictions_scaled))

    last_time = df.index[-1]
    delta = timedelta(days=1) if interval=="1d" else timedelta(hours=1)
    timestamps = [last_time + (i+1)*delta for i in range(steps_ahead)]

    pred_df = pd.DataFrame(predictions, columns=df.columns, index=timestamps)

    pred_df.index = pred_df.index.strftime('%Y-%m-%d %H:%M:%S')
    return pred_df


if __name__ == "__main__":
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    dotenv_path = os.path.join(root_path, '.env')
    load_dotenv(dotenv_path=dotenv_path)
    USD_TO_INR = float(os.getenv("USD_TO_INR"))

    SYMBOL = input("Enter coin symbol (ADA, AVAX, BNB, BTC, DOGE, ETH, SOL, XRP): ").upper()
    mode = input("Enter mode (daily/hourly): ").lower()
    INTERVAL = "1d" if mode=="daily" else "1h"
    STEPS_AHEAD = int(input("Enter number of future steps to predict: "))

    pred_df = get_live_prediction(SYMBOL, INTERVAL, STEPS_AHEAD, USD_TO_INR)
    if pred_df is not None:
        print(f"\n--- {SYMBOL} Predictions ({INTERVAL}) ---")
        print(pred_df)
    else:
        print("Prediction failed")
