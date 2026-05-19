"""Fetch market data from yfinance, transform it, and load into SQLite."""

from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from app.database import Base, engine
from app.models import Company, StockData

TRACKED_SYMBOLS: list[str] = [
    "INFY.NS",
    "TCS.NS",
    "RELIANCE.NS",
    "HDFCBANK.NS",
    "WIPRO.NS",
]

DISPLAY_NAMES: dict[str, str] = {
    "INFY.NS": "Infosys",
    "TCS.NS": "Tata Consultancy Services",
    "RELIANCE.NS": "Reliance Industries",
    "HDFCBANK.NS": "HDFC Bank",
    "WIPRO.NS": "Wipro",
}

LOOKBACK_YEARS: int = 2


def database_is_empty(db: Session) -> bool:
    """Return True when no companies have been ingested yet."""
    return db.query(Company).count() == 0


def fetch_raw_history(symbol: str) -> pd.DataFrame:
    """Download daily OHLCV history for the last two years."""
    end = datetime.utcnow()
    start = end - timedelta(days=LOOKBACK_YEARS * 365)
    frame = yf.download(
        symbol,
        start=start.strftime("%Y-%m-%d"),
        end=end.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=False,
    )
    if frame.empty:
        raise ValueError(f"No data returned from yfinance for {symbol}")
    return frame


def _flatten_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize yfinance multi-index columns to a flat OHLCV frame."""
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    return frame.rename(columns=str.title)


def clean_history(frame: pd.DataFrame) -> pd.DataFrame:
    """Parse dates, forward-fill gaps, and keep OHLCV columns only."""
    cleaned = _flatten_columns(frame.copy())
    cleaned.index = pd.to_datetime(cleaned.index)
    # Forward-fill preserves last known prices across exchange holidays without inventing values.
    cleaned = cleaned.ffill()
    return cleaned[["Open", "High", "Low", "Close", "Volume"]].dropna(how="all")


def add_daily_return(frame: pd.DataFrame) -> pd.DataFrame:
    """Compute intraday return from open to close."""
    frame["daily_return"] = (frame["Close"] - frame["Open"]) / frame["Open"]
    return frame


def add_moving_average(frame: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    """Add rolling mean of close over trading days."""
    frame["ma_7"] = frame["Close"].rolling(window=window, min_periods=window).mean()
    return frame


def add_52_week_extremes(frame: pd.DataFrame) -> pd.DataFrame:
    """Add trailing 365 calendar day high and low of close."""
    frame["high_52w"] = frame["Close"].rolling("365D", min_periods=1).max()
    frame["low_52w"] = frame["Close"].rolling("365D", min_periods=1).min()
    return frame


def add_volatility_score(frame: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    """Scale 30-day return volatility to a 0–100 score for the symbol."""
    rolling_std = frame["daily_return"].rolling(window=window, min_periods=window).std()
    peak = rolling_std.max()
    if peak and peak > 0:
        frame["volatility_score"] = (rolling_std / peak) * 100.0
    else:
        frame["volatility_score"] = np.nan
    return frame


def transform_history(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply all cleaning and feature engineering steps in sequence."""
    enriched = clean_history(frame)
    enriched = add_daily_return(enriched)
    enriched = add_moving_average(enriched)
    enriched = add_52_week_extremes(enriched)
    return add_volatility_score(enriched)


def _row_to_stock_data(company_id: int, row: pd.Series) -> StockData:
    """Map one transformed Pandas row to a StockData ORM instance."""
    return StockData(
        company_id=company_id,
        date=row.name.date(),
        open=float(row["Open"]),
        high=float(row["High"]),
        low=float(row["Low"]),
        close=float(row["Close"]),
        volume=float(row["Volume"]),
        daily_return=float(row["daily_return"]),
        ma_7=_optional_float(row.get("ma_7")),
        high_52w=_optional_float(row.get("high_52w")),
        low_52w=_optional_float(row.get("low_52w")),
        volatility_score=_optional_float(row.get("volatility_score")),
    )


def _optional_float(value: Any) -> float | None:
    """Return None for NaN values so SQLite stores NULL instead of NaN."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return float(value)


def load_company_frame(db: Session, symbol: str, frame: pd.DataFrame) -> None:
    """Persist transformed rows for one symbol."""
    company = Company(symbol=symbol, name=DISPLAY_NAMES.get(symbol, symbol))
    db.add(company)
    db.flush()
    for _, row in frame.iterrows():
        db.add(_row_to_stock_data(company.id, row))


def run_ingestion(db: Session) -> None:
    """Fetch, transform, and store data for all tracked symbols."""
    for symbol in TRACKED_SYMBOLS:
        raw = fetch_raw_history(symbol)
        cleaned = transform_history(raw)
        load_company_frame(db, symbol, cleaned)
    db.commit()


def ingest_if_needed(db: Session) -> None:
    """Run ingestion once on startup when the database has no rows."""
    Base.metadata.create_all(bind=engine)
    if not database_is_empty(db):
        return
    run_ingestion(db)
