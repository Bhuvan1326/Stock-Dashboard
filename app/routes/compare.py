"""Side-by-side stock comparison endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StockData
from app.routes.stocks import _resolve_symbol, _validate_days
from app.schemas import CompareOut, ComparePoint

router = APIRouter(tags=["compare"])


@router.get("/compare", response_model=CompareOut)
async def compare_symbols(
    symbol1: Annotated[str, Query(description="First symbol, e.g. INFY or INFY.NS")],
    symbol2: Annotated[str, Query(description="Second symbol, e.g. TCS or TCS.NS")],
    days: Annotated[int, Query(description="History window in days")] = 30,
    db: Session = Depends(get_db),
) -> CompareOut:
    """Return aligned close-price series for two symbols."""
    _validate_days(days)
    company1 = _resolve_symbol(db, symbol1)
    company2 = _resolve_symbol(db, symbol2)

    series1 = _close_series(db, company1.id, days)
    series2 = _close_series(db, company2.id, days)

    if not series1 or not series2:
        raise HTTPException(
            status_code=404,
            detail="Insufficient data to compare the requested symbols.",
        )

    return CompareOut(
        symbol1=company1.symbol,
        symbol2=company2.symbol,
        series1=series1,
        series2=series2,
    )


def _close_series(db: Session, company_id: int, days: int) -> list[ComparePoint]:
    """Build date/close pairs for the last N trading days."""
    rows = (
        db.query(StockData)
        .filter(StockData.company_id == company_id)
        .order_by(desc(StockData.date))
        .limit(days)
        .all()
    )
    rows.reverse()
    return [ComparePoint(date=row.date, close=row.close) for row in rows]
