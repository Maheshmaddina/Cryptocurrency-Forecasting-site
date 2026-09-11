# 🚀 CryptoSight - AI-Powered Cryptocurrency Price Predictor

AI-based web app for real-time cryptocurrency price forecasting using LSTM models and market sentiment analysis.

## ✨ Features

- Dashboard & Visualization
  - Interactive Chart.js graphs with tooltips and legends
  - Current vs predicted prices with trend indicators
  - Color-coded market sentiment (Bullish/Neutral/Bearish)
- Predictions
  - Hourly and daily horizons for multiple cryptocurrencies
  - Confidence indicators and key metrics
- Accounts & History
  - Secure authentication (login/signup)
  - Personal prediction history with filters and pagination
- UX & Accessibility
  - Responsive layout (mobile → desktop)
  - Dark/Light theme toggle with persistence
  - Semantic HTML, ARIA labels, keyboard navigation
- Tech Highlights
  - Real-time market data integration (Binance)
  - Clean, glass-morphism styling

## 🛠️ Tech Stack

- Backend: Django, TensorFlow, Celery, Redis, SQLite
- Frontend: HTML, CSS, JavaScript, Bootstrap, Chart.js

## 🚀 Quick Start

```bash
git clone [repo-url]
cd CryptoSight
python -m venv venv
venv\Scripts\activate  # or: source venv/bin/activate

# Install backend deps from Django/requirements.txt
pip install -r Django/requirements.txt

# Apply migrations
cd Django
python manage.py migrate

# Make sure your Redis server is running
redis-server

# In terminal 1: Start the Django Web Server
python manage.py runserver

# In terminal 2: Start the Celery Worker (for background tasks)
# Note for Windows users: add "-P solo" to use a compatible concurrency pool
celery -A CryptoSight worker -l info -P solo

# In terminal 3: Start the Celery Beat Scheduler (for periodic tasks)
celery -A CryptoSight beat -l info
```

Visit: http://127.0.0.1:8000/

## ☁️ Deploying to Vercel

Vercel can't run TensorFlow (too large), Celery or Redis, so the deployment
uses the exported numpy models and runs each prediction inside the request:

- `api/index.py` — WSGI entrypoint, `vercel.json` — routing, region and cron
- `requirements.txt` (repo root) — light deps for Vercel; `Django/requirements.txt` — full local stack
- Settings switch on the `VERCEL` environment variable (`USE_CELERY=False`, WhiteNoise static files)

Vercel project setup:

1. Root Directory: leave blank (the repo root).
2. Storage → connect Neon Postgres; it sets `DATABASE_URL` automatically.
   Without it, data is stored in a temporary SQLite file and is lost regularly.
3. Environment variables: `DJANGO_SECRET_KEY`, optionally `CRON_SECRET` and `USD_TO_INR`.

After retraining a model, re-export the numpy weights and redeploy:

```bash
python Model_Training/export_numpy_weights.py
```

## 🏗️ Structure

```
ML-Driven-Web-Platform-for-Cryptocurrency-Price-Forecasting_September_2025/
├── Data/                             # Data fetch scripts and CSV outputs
│   ├── data-days/
│   ├── data-hours/
│   ├── fetchdata.py
│   └── symbols.json
│
├── Model_Training/                   # Training scripts & saved models
│   ├── model_train_daily.py
│   ├── model_train_hourly.py
│   ├── models_daily/                 # .keras + scaler.pkl (daily)
│   └── models_hourly/                # .keras + scaler.pkl (hourly)
│
├── Django/                           # Web app (CryptoSight project)
│   ├── manage.py
│   ├── CryptoSight/                  # Project config
│   │   ├── asgi.py
│   │   ├── celery.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── authuser/
│   ├── home/
│   ├── predict/
│   ├── chatbot/
│   ├── static/
│   └── templates/
│
├── venv/                             # Root virtual environment
└── README.md
```

## 🎯 Usage

1. Sign up or log in to your account.
2. Go to Predict and select a cryptocurrency (e.g., BTC, ETH) and timeframe (hourly/daily).
3. Click Predict to generate results.
4. Review the chart, sentiment badge, and confidence indicators.
5. Optionally adjust timeframe/crypto and re-run to compare.
6. Open History to view, filter, and paginate past predictions.
7. Toggle Dark/Light mode from the header as needed.

## 📊 Supported Cryptos

BTC | ETH | BNB | SOL | XRP | ADA | DOGE | AVAX

## 👩‍💻 Developer

Praveena — GitHub: @rsdpraveena

## ⚠️ Note

For educational purposes only. Cryptocurrency trading involves risk.

