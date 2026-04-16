"""vectorbt Portfolio.trades → RawTrade list 변환."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

import pandas as pd
import vectorbt as vbt

from src.backtest.engine.types import RawTrade


def extract_trades(pf: vbt.Portfolio, ohlcv: pd.DataFrame) -> list[RawTrade]:
    """vectorbt Portfolio → RawTrade list.

    Args:
        pf: vectorbt Portfolio 인스턴스.
        ohlcv: OHLCV DataFrame. 이 함수에서 직접 사용하지 않으나,
            run_backtest()가 (pf, ohlcv) 쌍을 관례적으로 전달하므로 서명에 포함.
            service layer에서 ohlcv.index로 bar_index → datetime 변환.

    Decimal 변환 원칙: float 공간에서 arithmetic 수행 전 str() 경유로 Decimal 진입.
    fees 같이 합산이 필요한 필드는 Decimal 변환 후 합산 — CLAUDE.md 금융 규칙.
    """
    del ohlcv  # signature convention only

    df = pf.trades.records_readable

    # 거래 없는 portfolio → 빈 DataFrame 반환
    if df.empty:
        return []

    raw_trades: list[RawTrade] = []

    for _, row in df.iterrows():
        # Direction: 알 수 없는 값은 즉시 실패 (silent misclassification 방지)
        raw_direction = row["Direction"]
        if raw_direction == "Long":
            direction: Literal["long", "short"] = "long"
        elif raw_direction == "Short":
            direction = "short"
        else:
            raise ValueError(
                f"extract_trades: unknown vectorbt Direction value: {raw_direction!r}"
            )

        # Status: 알 수 없는 값은 즉시 실패 (silent misclassification 방지)
        raw_status = row["Status"]
        if raw_status == "Closed":
            status: Literal["open", "closed"] = "closed"
        elif raw_status == "Open":
            status = "open"
        else:
            raise ValueError(
                f"extract_trades: unknown vectorbt Status value: {raw_status!r}"
            )

        is_closed = status == "closed"

        # fees: Decimal-first 합산 (float 공간에서 합산 금지)
        fees_total = Decimal(str(row["Entry Fees"])) + Decimal(str(row["Exit Fees"]))

        raw_trades.append(
            RawTrade(
                trade_index=int(row["Exit Trade Id"]),
                direction=direction,
                status=status,
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
