"""Stock listing, history, summary, and top-mover endpoints."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, StockData
from app.schemas import (
    CompanyOut,
    MoverOut,
    StockDataPoint,
    SummaryOut,
    TopMoversOut,
)

router = APIRouter(tags=["stocks"])

ALLOWED_DAY_WINDOWS: set[int] = {30, 90, 365}


def _resolve_symbol(db: Session, raw_symbol: str) -> Company:
    """Match INFY, INFY.NS, or full NSE tickers to a stored company."""
    symbol = raw_symbol.strip().upper()
    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"

    company = db.query(Company).filter(Company.symbol == symbol).first()
    if company is None:
        company = (
            db.query(Company)
            .filter(Company.symbol == raw_symbol.strip().upper())
            .first()
        )
    if company is None:
        raise HTTPException(
            status_code=404,
            detail=f"Symbol '{raw_symbol}' is not tracked. Use one of the NSE tickers in /companies.",
        )
    return company


def _validate_days(days: int) -> int:
    """Restrict history windows to supported chart ranges."""
    if days not in ALLOWED_DAY_WINDOWS:
        raise HTTPException(
            status_code=400,
            detail="days must be one of: 30, 90, 365",
        )
    return days


@router.get("/companies", response_model=list[CompanyOut])
async def list_companies(db: Session = Depends(get_db)) -> list[Company]:
    """Return all tracked symbols and display names."""
    return db.query(Company).order_by(Company.name).all()


@router.get("/data/{symbol}", response_model=list[StockDataPoint])
async def get_stock_data(
    symbol: str,
    days: Annotated[int, Query(description="History window in days")] = 30,
    db: Session = Depends(get_db),
) -> list[StockDataPoint]:
    """Return the last N days of OHLCV and derived metrics for one symbol."""
    _validate_days(days)
    company = _resolve_symbol(db, symbol)

    rows = (
        db.query(StockData)
        .filter(StockData.company_id == company.id)
        .order_by(desc(StockData.date))
        .limit(days)
        .all()
    )
    rows.reverse()
    return rows


@router.get("/summary/{symbol}", response_model=SummaryOut)
async def get_summary(
    symbol: str,
    db: Session = Depends(get_db),
) -> SummaryOut:
    """Return 52-week range and latest price metrics for one symbol."""
    company = _resolve_symbol(db, symbol)
    latest = _latest_row(db, company.id)
    if latest is None:
        raise HTTPException(status_code=404, detail=f"No price data for '{symbol}'.")

    avg_close = _average_close(db, company.id)
    return SummaryOut(
        symbol=company.symbol,
        high_52w=latest.high_52w,
        low_52w=latest.low_52w,
        avg_close=avg_close,
        latest_close=latest.close,
        latest_daily_return=latest.daily_return,
    )


@router.get("/top-movers", response_model=TopMoversOut)
async def get_top_movers(db: Session = Depends(get_db)) -> TopMoversOut:
    """Return top gainers and losers on the latest available trading day."""
    latest_date = db.query(StockData.date).order_by(desc(StockData.date)).first()
    if latest_date is None:
        raise HTTPException(status_code=404, detail="No market data available yet.")

    trading_day: date = latest_date[0]
    rows = (
        db.query(Company, StockData)
        .join(StockData, StockData.company_id == Company.id)
        .filter(StockData.date == trading_day)
        .all()
    )

    ranked = sorted(rows, key=lambda item: item[1].daily_return, reverse=True)
    gainers = [
        MoverOut(
            symbol=company.symbol,
            name=company.name,
            daily_return=stock.daily_return,
            close=stock.close,
        )
        for company, stock in ranked[:3]
    ]
    bottom = sorted(rows, key=lambda item: item[1].daily_return)
    losers = [
        MoverOut(
            symbol=company.symbol,
            name=company.name,
            daily_return=stock.daily_return,
            close=stock.close,
        )
        for company, stock in bottom[:3]
    ]
    return TopMoversOut(gainers=gainers, losers=losers)


def _latest_row(db: Session, company_id: int) -> StockData | None:
    """Fetch the most recent stored row for a company."""
    return (
        db.query(StockData)
        .filter(StockData.company_id == company_id)
        .order_by(desc(StockData.date))
        .first()
    )


def _average_close(db: Session, company_id: int) -> float:
    """Compute mean close across all stored history for a company."""
    rows = (
        db.query(StockData.close)
        .filter(StockData.company_id == company_id)
        .all()
    )
    if not rows:
        return 0.0
    return float(sum(row[0] for row in rows) / len(rows))
