"""vectorbt Portfolio.trades → RawTrade list 변환."""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import vectorbt as vbt

from src.backtest.engine.types import RawTrade


def extract_trades(pf: vbt.Portfolio, ohlcv: pd.DataFrame) -> list[RawTrade]:
    """vectorbt Portfolio → RawTrade list.

    Bar index는 유지 (service layer에서 ohlcv.index로 datetime 복원).

    Decimal 변환 원칙: float 공간에서 arithmetic 수행 전 str() 경유로 Decimal 진입.
    fees 같이 합산이 필요한 필드는 Decimal 변환 후 합산 — CLAUDE.md 금융 규칙.
    """
    df = pf.trades.records_readable

    # 거래 없는 portfolio → 빈 DataFrame 반환
    if df.empty:
        return []

    raw_trades: list[RawTrade] = []

    for _, row in df.iterrows():
        # fees: Decimal-first 합산 (float 공간에서 합산 금지)
        fees_total = Decimal(str(row["Entry Fees"])) + Decimal(str(row["Exit Fees"]))
        is_closed = row["Status"] == "Closed"

        raw_trades.append(
            RawTrade(
                trade_index=int(row["Exit Trade Id"]),
                direction="long" if row["Direction"] == "Long" else "short",
                status="closed" if is_closed else "open",
                entry_bar_index=int(row["Entry Timestamp"]),
                exit_bar_index=int(row["Exit Timestamp"]) if is_closed else None,
                entry_price=Decimal(str(row["Avg Entry Price"])),
                exit_price=Decimal(str(row["Avg Exit Price"])) if is_closed else None,
                size=Decimal(str(row["Size"])),
                pnl=Decimal(str(row["PnL"])),
                return_pct=Decimal(str(row["Return"])),
                fees=fees_total,
            )
        )

    return raw_trades
