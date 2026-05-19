"""Pydantic response models for the REST API."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class CompanyOut(BaseModel):
    """Company symbol and display name."""

    symbol: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class StockDataPoint(BaseModel):
    """Single day of OHLCV and derived fields for charting."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    daily_return: float
    ma_7: float | None = None

    model_config = ConfigDict(from_attributes=True)


class SummaryOut(BaseModel):
    """52-week range and latest price summary for one symbol."""

    symbol: str
    high_52w: float | None
    low_52w: float | None
    avg_close: float
    latest_close: float
    latest_daily_return: float


class ComparePoint(BaseModel):
    """Close price on a given date for comparison charts."""

    date: date
    close: float


class CompareOut(BaseModel):
    """Side-by-side close series for two symbols."""

    symbol1: str
    symbol2: str
    series1: list[ComparePoint]
    series2: list[ComparePoint]


class MoverOut(BaseModel):
    """Top gainer or loser on the latest trading day."""

    symbol: str
    name: str
    daily_return: float
    close: float


class TopMoversOut(BaseModel):
    """Top gainers and losers by latest daily return."""

    gainers: list[MoverOut]
    losers: list[MoverOut]


class ErrorOut(BaseModel):
    """Standard error payload."""

    error: str
