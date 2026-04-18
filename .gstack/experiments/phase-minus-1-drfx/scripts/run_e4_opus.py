"""E4 — Opus 4.7 변환본 재실행 (고정 OHLCV).

`/tmp/drfx_test/drfx_backtest.py`의 DrFXBacktester + BacktestConfig를 import하여
ohlcv/btc_usdt_1h_frozen.csv 고정 입력으로 실행. 결과를 JSON으로 저장.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OPUS_SRC = Path("/tmp/drfx_test")
sys.path.insert(0, str(OPUS_SRC))

from drfx_backtest import BacktestConfig, DrFXBacktester  # type: ignore[reportMissingImports]  # noqa: E402

import argparse

_ap = argparse.ArgumentParser()
_ap.add_argument("--timeframe", default="1h", choices=["1h", "4h", "1d"])
_args = _ap.parse_args()
_TF = _args.timeframe
_BARS_PER_YEAR = {"1h": 24 * 365, "4h": 6 * 365, "1d": 365}[_TF]

EXP_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = EXP_ROOT / "ohlcv" / f"btc_usdt_{_TF}_frozen.csv"
OUT_PATH = EXP_ROOT / "output" / f"e4_opus_i3_drfx_{_TF}.json"
TRADES_PATH = EXP_ROOT / "output" / f"e4_opus_i3_drfx_{_TF}_trades.csv"
EQUITY_PATH = EXP_ROOT / "output" / f"e4_opus_i3_drfx_{_TF}_equity.csv"


def load_frozen() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("timestamp").sort_index()
    return df[["open", "high", "low", "close", "volume"]]


def main() -> None:
    df = load_frozen()
    print(f"Loaded: rows={len(df)} range=[{df.index[0]} .. {df.index[-1]}]")

    cfg = BacktestConfig(
        sensitivity=2.0,
        take_profit_level=2.0,
        atr_risk_multiplier=1.0,
        initial_capital=10_000.0,
        smart_signals_only=False,
    )
    bt = DrFXBacktester(cfg)
    result = bt.run(df)

    # bars_per_year 주입 (샤프 계산용)
    object.__setattr__(result, "bars_per_year", _BARS_PER_YEAR)

    # 결과 요약
    exit_reasons: dict[str, int] = {}
    for t in result.trades:
        if t.exit_price is None:
            continue
        reason = getattr(t, "exit_reason", "unknown")
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1

    summary = {
        "engine": "E4",
        "model": "Claude Opus 4.7 (추정)",
        "script": "i3_drfx",
        "timeframe": _TF,
        "ohlcv_source": str(CSV_PATH),
        "ohlcv_rows": int(len(df)),
        "initial_capital": float(cfg.initial_capital),
        "final_capital": float(result.final_capital),
        "total_return_pct": float(result.total_return_pct),
        "max_drawdown_pct": float(result.max_drawdown_pct),
        "sharpe_ratio": float(result.sharpe_ratio),
        "profit_factor": float(result.profit_factor) if np.isfinite(result.profit_factor) else None,
        "total_trades": int(result.total_trades),
        "winning_trades": int(result.winning_trades),
        "losing_trades": int(result.losing_trades),
        "win_rate": float(result.win_rate),
        "exit_reasons": exit_reasons,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    # trades CSV
    trade_rows = []
    for t in result.trades:
        trade_rows.append({
            "entry_time": getattr(t, "entry_time", None),
            "exit_time": getattr(t, "exit_time", None),
            "direction": getattr(t, "direction", None),
            "entry_price": getattr(t, "entry_price", None),
            "exit_price": getattr(t, "exit_price", None),
            "pnl": getattr(t, "pnl", None),
            "exit_reason": getattr(t, "exit_reason", None),
        })
    pd.DataFrame(trade_rows).to_csv(TRADES_PATH, index=False)

    # equity curve
    if len(result.equity_curve) > 0:
        result.equity_curve.to_csv(EQUITY_PATH, header=["equity"])

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
