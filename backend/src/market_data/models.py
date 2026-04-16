"""market_data 도메인 SQLModel — OHLCV TimescaleDB hypertable."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, Index, Numeric
from sqlmodel import Field, SQLModel

from src.common.datetime_types import AwareDateTime


class OHLCV(SQLModel, table=True):
    """OHLCV bar — TimescaleDB hypertable (ts.ohlcv).

    PK: (time, symbol, timeframe). TimescaleDB는 모든 UNIQUE 제약에
    partition key(time)를 포함하도록 요구한다.
    """

    __tablename__ = "ohlcv"
    __table_args__ = (
        # 보조 인덱스 — 특정 심볼/타임프레임의 최신 캔들 조회 최적화.
        # Postgres는 ASC 인덱스를 reverse scan할 수 있으므로 추가 DESC 인덱스 불필요.
        Index("ix_ohlcv_symbol_tf_time_desc", "symbol", "timeframe", "time"),
        {"schema": "ts"},
    )

    time: datetime = Field(
        sa_column=Column(AwareDateTime(), primary_key=True, nullable=False)
    )
    symbol: str = Field(primary_key=True, max_length=32)
    timeframe: str = Field(primary_key=True, max_length=8)
    exchange: str = Field(max_length=32, nullable=False)

    open: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    high: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    low: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    close: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
    volume: Decimal = Field(sa_column=Column(Numeric(18, 8), nullable=False))
