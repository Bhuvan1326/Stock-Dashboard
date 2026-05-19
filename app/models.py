"""SQLAlchemy ORM models for companies and daily stock data."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Company(Base):
    """Tracked stock symbol and display name."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    stock_rows: Mapped[list["StockData"]] = relationship(
        "StockData",
        back_populates="company",
        cascade="all, delete-orphan",
    )


class StockData(Base):
    """One row of OHLCV and derived metrics for a single trading day."""

    __tablename__ = "stock_data"
    __table_args__ = (
        UniqueConstraint("company_id", "date", name="uq_company_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    daily_return: Mapped[float] = mapped_column(Float, nullable=False)
    ma_7: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_52w: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_52w: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    company: Mapped["Company"] = relationship("Company", back_populates="stock_rows")
