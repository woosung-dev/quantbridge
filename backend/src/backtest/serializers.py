"""Backtest JSONB 직렬화 helpers.

metrics/equity_curve는 PostgreSQL JSONB 컬럼에 저장.
Decimal → str, datetime → ISO 8601 Z.
tz-aware UTC datetime 전제 (AwareDateTime TypeDecorator, Sprint 5 Stage B).
_utc_iso()는 방어적으로 naive 입력도 처리하지만, 신규 코드는 tz-aware 사용.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pandas as pd

from src.backtest.engine.types import BacktestMetrics


def _utc_iso(dt: datetime) -> str:
    """naive UTC datetime → ISO 8601 with Z suffix."""
    if dt.tzinfo is not None:
        # tz-aware → UTC 변환 후 naive화 (방어적)
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc_iso(s: str) -> datetime:
    """'2024-01-01T00:00:00Z' → tz-aware UTC datetime.

    EquityPoint 스키마는 AwareDatetime이므로 tzinfo=UTC 필수.
    """
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


# --- metrics ---

def metrics_to_jsonb(m: BacktestMetrics) -> dict[str, Any]:
    """BacktestMetrics → JSONB dict (Decimal → str)."""
    return {
        "total_return": str(m.total_return),
        "sharpe_ratio": str(m.sharpe_ratio),
        "max_drawdown": str(m.max_drawdown),
        "win_rate": str(m.win_rate),
        "num_trades": m.num_trades,
    }


def metrics_from_jsonb(data: dict[str, Any]) -> BacktestMetrics:
    """JSONB dict → BacktestMetrics."""
    return BacktestMetrics(
        total_return=Decimal(data["total_return"]),
        sharpe_ratio=Decimal(data["sharpe_ratio"]),
        max_drawdown=Decimal(data["max_drawdown"]),
        win_rate=Decimal(data["win_rate"]),
        num_trades=int(data["num_trades"]),
    )


# --- equity_curve ---

def equity_curve_to_jsonb(series: pd.Series) -> list[list[str]]:
    """pd.Series(DatetimeIndex, Decimal or float values) → [[ISO str, Decimal str], ...]."""
    result: list[list[str]] = []
    for ts, value in series.items():
        if not isinstance(ts, datetime):
            # pandas Timestamp → datetime (mypy: Hashable → str로 명시적 변환)
            ts = pd.Timestamp(str(ts)).to_pydatetime()
        result.append([_utc_iso(ts), str(value)])
    return result


def equity_curve_from_jsonb(data: list[list[str]]) -> list[tuple[datetime, Decimal]]:
    """JSONB list → [(datetime, Decimal), ...]."""
    return [(_parse_utc_iso(ts), Decimal(v)) for ts, v in data]
