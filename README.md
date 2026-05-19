# Stock Data Intelligence Dashboard

A full-stack project for stock market analysis and visualization. It ingests two years of NSE daily OHLCV data, stores derived analytics in SQLite, and exposes a FastAPI REST API with a Chart.js dashboard for exploration and comparison.

## Tech stack

| Layer      | Technology                      |
|-----------|----------------------------------|
| Backend   | FastAPI, SQLAlchemy, SQLite      |
| Data      | yfinance, Pandas, NumPy          |
| Frontend  | HTML, CSS, Chart.js (CDN)        |
| API docs  | Swagger UI at `/docs`            |

## Setup

1. **Clone or copy the project**
   ```bash
   cd stock-dashboard
   ```

2. **Create a virtual environment and install dependencies** (Python 3.12)
   ```bash
   py -3.12 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
   If `py -3` points to 3.14 and venv creation fails, delete the old folder first: `rmdir /s /q .venv`, then use `py -3.12` as shown above.

3. **Configure environment**
   ```bash
   copy .env.example .env
   ```

4. **Run ingestion (automatic on first startup)**  
   Start the server from the project root. If `stock_dashboard.db` is empty, the app fetches and loads data for all five tickers:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

5. **Open the dashboard**  
   Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) for the UI and [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for Swagger.

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/companies` | List tracked symbols and names |
| GET | `/data/{symbol}?days=30` | Last N days of OHLCV and metrics (`days`: 30, 90, 365) |
| GET | `/summary/{symbol}` | 52W high/low, average close, latest close and return |
| GET | `/compare?symbol1=INFY&symbol2=TCS&days=30` | Two close-price series for overlay charts |
| GET | `/top-movers` | Top 3 gainers and losers on the latest trading day |

Symbols accept either the short form (`INFY`) or the NSE ticker (`INFY.NS`).

## Volatility score

`volatility_score` is the 30-day rolling standard deviation of `daily_return`, min–max scaled to **0–100** per symbol. Higher values mean recent daily moves have been more dispersed relative to that stock’s own history. It is useful for quickly spotting which names are behaving more erratically than usual without comparing raw rupee volatility across different price levels—helpful for risk screens, position sizing, and prioritizing further analysis.

## What I'd build next

1. **Real-time WebSocket feed** — Stream live quotes and intraday bars so the dashboard updates during market hours without manual refresh.
2. **ML price prediction** — Train a lightweight model (e.g., gradient boosting on returns, volume, and volatility features) with backtested confidence intervals surfaced in the UI.
3. **User watchlists** — Persist personalized symbol lists, alerts on daily-return thresholds, and email or push notifications when movers hit user-defined rules.
