"""Backtest JSONB 직렬화 helpers.

metrics/equity_curve는 PostgreSQL JSONB 컬럼에 저장.
Decimal → str, datetime → ISO 8601 Z.
tz-aware UTC datetime 전제 (AwareDateTime TypeDecorator, Sprint 5 Stage B).
_utc_iso()는 방어적으로 naive 입력도 처리하지만, 신규 코드는 tz-aware 사용.

Sprint 30 gamma-BE: BacktestMetrics 12 → 24 필드 확장.
신규 12 필드는 모두 Optional default None → Sprint 28 이전 backtest backward-compat.
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
    """BacktestMetrics → JSONB dict (Decimal → str, None 필드는 키 생략).

    Sprint 30 gamma-BE: 24 필드 spec. 기존 12 필드는 변경 없음, 신규 12 필드 추가.
    """
    d: dict[str, Any] = {
        "total_return": str(m.total_return),
        "sharpe_ratio": str(m.sharpe_ratio),
        "max_drawdown": str(m.max_drawdown),
        "win_rate": str(m.win_rate),
        "num_trades": m.num_trades,
    }
    if m.sortino_ratio is not None:
        d["sortino_ratio"] = str(m.sortino_ratio)
    if m.calmar_ratio is not None:
        d["calmar_ratio"] = str(m.calmar_ratio)
    if m.profit_factor is not None:
        d["profit_factor"] = str(m.profit_factor)
    if m.avg_win is not None:
        d["avg_win"] = str(m.avg_win)
    if m.avg_loss is not None:
        d["avg_loss"] = str(m.avg_loss)
    if m.long_count is not None:
        d["long_count"] = m.long_count
    if m.short_count is not None:
        d["short_count"] = m.short_count

    # --- Sprint 30 gamma-BE 신규 12 필드 (None 키 생략 → backward-compat) ---
    if m.avg_holding_hours is not None:
        d["avg_holding_hours"] = str(m.avg_holding_hours)
    if m.consecutive_wins_max is not None:
        d["consecutive_wins_max"] = m.consecutive_wins_max
    if m.consecutive_losses_max is not None:
        d["consecutive_losses_max"] = m.consecutive_losses_max
    if m.long_win_rate_pct is not None:
        d["long_win_rate_pct"] = str(m.long_win_rate_pct)
    if m.short_win_rate_pct is not None:
        d["short_win_rate_pct"] = str(m.short_win_rate_pct)
    if m.monthly_returns is not None:
        # list[(str, Decimal)] → list[[str, str]]
        d["monthly_returns"] = [[k, str(v)] for k, v in m.monthly_returns]
    if m.drawdown_duration is not None:
        d["drawdown_duration"] = m.drawdown_duration
    if m.annual_return_pct is not None:
        d["annual_return_pct"] = str(m.annual_return_pct)
    if m.total_trades is not None:
        d["total_trades"] = m.total_trades
    if m.avg_trade_pct is not None:
        d["avg_trade_pct"] = str(m.avg_trade_pct)
    if m.best_trade_pct is not None:
        d["best_trade_pct"] = str(m.best_trade_pct)
    if m.worst_trade_pct is not None:
        d["worst_trade_pct"] = str(m.worst_trade_pct)
    if m.drawdown_curve is not None:
        d["drawdown_curve"] = [[ts, str(v)] for ts, v in m.drawdown_curve]
    # Sprint 32-D BL-156: MDD 수학 정합 메타. None 키 생략 → backward-compat
    # (Sprint 31 이전 backtest round-trip 안전).
    if m.mdd_unit is not None:
        d["mdd_unit"] = m.mdd_unit
    if m.mdd_exceeds_capital is not None:
        d["mdd_exceeds_capital"] = m.mdd_exceeds_capital
    return d


def metrics_from_jsonb(data: dict[str, Any]) -> BacktestMetrics:
    """JSONB dict → BacktestMetrics (신규 Optional 필드는 .get()으로 하위 호환).

    Sprint 30 gamma-BE: 24 필드 round-trip identity. Sprint 28 이전 12 필드만 set 시
    신규 12 필드는 모두 None.
    """
    def _opt_decimal(key: str) -> Decimal | None:
        raw = data.get(key)
        return Decimal(raw) if raw is not None else None

    monthly_raw = data.get("monthly_returns")
    monthly_returns: list[tuple[str, Decimal]] | None = None
    if monthly_raw is not None:
        monthly_returns = [(str(k), Decimal(str(v))) for k, v in monthly_raw]

    dd_curve_raw = data.get("drawdown_curve")
    drawdown_curve: list[tuple[str, Decimal]] | None = None
    if dd_curve_raw is not None:
        drawdown_curve = [(str(ts), Decimal(str(v))) for ts, v in dd_curve_raw]

    return BacktestMetrics(
        total_return=Decimal(data["total_return"]),
        sharpe_ratio=Decimal(data["sharpe_ratio"]),
        max_drawdown=Decimal(data["max_drawdown"]),
        win_rate=Decimal(data["win_rate"]),
        num_trades=int(data["num_trades"]),
        sortino_ratio=_opt_decimal("sortino_ratio"),
        calmar_ratio=_opt_decimal("calmar_ratio"),
        profit_factor=_opt_decimal("profit_factor"),
        avg_win=_opt_decimal("avg_win"),
        avg_loss=_opt_decimal("avg_loss"),
        long_count=data.get("long_count"),
        short_count=data.get("short_count"),
        # Sprint 30 gamma-BE 신규 12
        avg_holding_hours=_opt_decimal("avg_holding_hours"),
        consecutive_wins_max=data.get("consecutive_wins_max"),
        consecutive_losses_max=data.get("consecutive_losses_max"),
        long_win_rate_pct=_opt_decimal("long_win_rate_pct"),
        short_win_rate_pct=_opt_decimal("short_win_rate_pct"),
        monthly_returns=monthly_returns,
        drawdown_duration=data.get("drawdown_duration"),
        annual_return_pct=_opt_decimal("annual_return_pct"),
        total_trades=data.get("total_trades"),
        avg_trade_pct=_opt_decimal("avg_trade_pct"),
        best_trade_pct=_opt_decimal("best_trade_pct"),
        worst_trade_pct=_opt_decimal("worst_trade_pct"),
        drawdown_curve=drawdown_curve,
        # Sprint 32-D BL-156 — Optional, .get() 으로 누락 시 None.
        mdd_unit=data.get("mdd_unit"),
        mdd_exceeds_capital=data.get("mdd_exceeds_capital"),
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
