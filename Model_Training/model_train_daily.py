import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Input,LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import os
import joblib

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
data_dir = os.path.join(BASE_DIR, "Data", "data-days")
models_dir = os.path.join(os.path.dirname(__file__), "models_daily")
os.makedirs(models_dir, exist_ok=True)

features = ['Open', 'High', 'Low', 'Close', 'Volume']
time_step = 30

def create_sequences(data, time_step=30):
    X, y = [], []
    for i in range(len(data) - time_step - 1):
        X.append(data[i:(i + time_step)])
        y.append(data[i + time_step])
    return np.array(X), np.array(y)

for filename in os.listdir(data_dir):
    if filename.endswith("_days_data.csv"):
        coin_name = filename.split('_')[0]
        filepath = os.path.join(data_dir, filename)

        df = pd.read_csv(filepath)
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values("Date")
        df.dropna(subset=features, inplace=True)

        scaler = MinMaxScaler((0, 1))
        scaled_data = scaler.fit_transform(df[features])

        X, y = create_sequences(scaled_data, time_step)
        train_size = int(len(X) * 0.7)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]

        model = Sequential()
        model.add(Input(shape=(time_step, len(features))))
        model.add(LSTM(128, activation='tanh', return_sequences=True,
                       input_shape=(time_step, len(features)), kernel_regularizer=l2(0.002)))
        model.add(Dropout(0.2))
        model.add(BatchNormalization())
        model.add(LSTM(64, activation='tanh', return_sequences=False, kernel_regularizer=l2(0.002)))
        model.add(Dropout(0.2))
        model.add(Dense(len(features), activation='linear'))

        model.compile(optimizer='adam', loss='mean_squared_error')

        early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

        history = model.fit(X_train, y_train,
                            batch_size=32,
                            epochs=20,
                            validation_data=(X_test, y_test),
                            callbacks=[early_stop],
                            verbose=1)

        model.save(os.path.join(models_dir, f"{coin_name}_daily_lstm.keras"))
        joblib.dump(scaler, os.path.join(models_dir, f"{coin_name}_scaler.pkl"))
        print(f"✅ Model trained and saved for {coin_name}")

        y_pred = model.predict(X_test)
        y_test_scaled = scaler.inverse_transform(y_test)
        y_pred_scaled = scaler.inverse_transform(y_pred)

        print("Evaluation Metrics (per feature):")
        for i, feature in enumerate(features):
            rmse = np.sqrt(mean_squared_error(y_test_scaled[:, i], y_pred_scaled[:, i]))
            mae = mean_absolute_error(y_test_scaled[:, i], y_pred_scaled[:, i])
            r2 = r2_score(y_test_scaled[:, i], y_pred_scaled[:, i])
            print(f"{feature}: RMSE = {rmse:.2f}, MAE = {mae:.2f}, R² = {r2:.2f}")

print("All coins processed.")
