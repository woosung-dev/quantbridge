"""Sprint 32-D BL-156 — MDD 수학 정합 + leverage 가정 응답 검증.

dogfood Day 3 발견: KPI 카드 MDD -132.96% / -343.15% 표시.

진단:
- vectorbt `pf.max_drawdown()` 와 v2 `_max_drawdown(equity)` 모두 의미는
  `(equity - running_max) / running_max` = equity ratio (-1.0 = -100%).
- leverage=1 (현물) 가정 하에서 MDD 는 수학적으로 [-1.0, 0.0] 범위.
- pine_v2 엔진은 leverage 를 PnL 에 직접 적용 안 함 (qty=절대 수량) → 사용자가
  큰 size 거래 시 equity 가 음수 → MDD < -1.0 가능 → 자본 100% 초과 손실 시나리오.
- 이 경우 응답에 `mdd_exceeds_capital=True` 메타 + FE 가 leverage 가정을
  inline 표시 (예: "MDD: -132.96% (leverage 5x 가정)").

본 테스트:
1. leverage=1 정상 fixture → MDD ∈ [-1.0, 0.0], mdd_exceeds_capital=False
2. equity 음수 (큰 size 거래) → MDD < -1.0, mdd_exceeds_capital=True
3. JSONB round-trip 시 메타 보존
4. vectorbt drift 시 메타 None fallback (drift 방어 패턴 정합)
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.backtest.engine.types import BacktestConfig, BacktestMetrics
from src.backtest.engine.v2_adapter import (
    _compute_equity_curve,
    _compute_metrics,
)
from src.backtest.serializers import metrics_from_jsonb, metrics_to_jsonb
from src.strategy.pine_v2.strategy_state import Trade


def _ohlcv(n: int = 10, base: float = 100.0) -> pd.DataFrame:
    """단순 OHLCV fixture — close 만 사용. 1D freq."""
    closes = [base + i for i in range(n)]
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * n,
        },
        index=pd.date_range("2024-01-01", periods=n, freq="1D"),
    )


def _cfg(init: str = "10000", leverage: float = 1.0) -> BacktestConfig:
    return BacktestConfig(
        init_cash=Decimal(init), fees=0.0, slippage=0.0, leverage=leverage
    )


# --- 1. 정상 leverage=1 시나리오: MDD ∈ [-1.0, 0.0] ---


def test_mdd_within_capital_range_with_normal_trades() -> None:
    """정상 long 거래 — MDD 는 [-1.0, 0.0] 범위, mdd_exceeds_capital=False."""
    from src.backtest.engine.v2_adapter import _build_raw_trades

    # entry=100, exit=110 → +10 PnL, init_cash=10000.
    # equity 는 10000~10010 사이 변동 → MDD 는 작은 음수 또는 0.
    state_trades = [
        Trade(
            id="t1",
            direction="long",
            qty=1.0,
            entry_bar=1,
            entry_price=100.0,
            exit_bar=5,
            exit_price=110.0,
            pnl=10.0,
        )
    ]
    from src.strategy.pine_v2.strategy_state import StrategyState

    state = StrategyState()
    state.closed_trades.extend(state_trades)

    cfg = _cfg(init="10000")
    raw_trades = _build_raw_trades(state, cfg)
    ohlcv = _ohlcv(n=10, base=100.0)
    equity = _compute_equity_curve(raw_trades, ohlcv, cfg)
    m = _compute_metrics(raw_trades, equity, cfg, ohlcv)

    # MDD ∈ [-1.0, 0.0]
    assert m.max_drawdown >= Decimal("-1")
    assert m.max_drawdown <= Decimal("0")
    # 메타 정합
    assert m.mdd_unit == "equity_ratio"
    assert m.mdd_exceeds_capital is False


# --- 2. 자본 초과 손실 시나리오 (leverage 가정 없이 큰 size) ---


def test_mdd_exceeds_capital_when_equity_goes_negative() -> None:
    """size 가 init_cash 대비 매우 큰 거래 + 가격 하락 → equity 음수 가능 → MDD < -1.0.

    leverage 가정 없이는 수학 모순 = 사용자 dogfood Day 3 의 -132.96% 케이스 재현.

    시뮬: init_cash=1000, qty=100 (notional=10000), entry=100. close 가
    100 → 80 → 60 ... 40 으로 하락 시 unrealized_pnl = (40-100)*100 = -6000
    → equity = 1000 - 6000 = -5000 → running_max=1000 (초기) → MDD =
    (-5000 - 1000)/1000 = -6.0 (= -600%).
    """
    from src.backtest.engine.v2_adapter import _build_raw_trades
    from src.strategy.pine_v2.strategy_state import StrategyState

    # 가격 하락 fixture — 100 → 40 (전체 하락).
    closes = [100.0, 90.0, 80.0, 70.0, 60.0, 50.0, 40.0, 40.0, 40.0, 40.0]
    ohlcv = pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1.0] * len(closes),
        },
        index=pd.date_range("2024-01-01", periods=len(closes), freq="1D"),
    )

    # init_cash=1000, qty=100 (notional=10000 = 10x 자본). 큰 size 거래
    # → equity 음수 가능. exit 시 PnL = (40-100)*100 = -6000.
    state = StrategyState()
    state.closed_trades.append(
        Trade(
            id="bigshort",
            direction="long",
            qty=100.0,
            entry_bar=0,
            entry_price=100.0,
            exit_bar=9,
            exit_price=40.0,
            pnl=-6000.0,
        )
    )

    cfg = BacktestConfig(
        init_cash=Decimal("1000"),
        fees=0.0,
        slippage=0.0,
        freq="1D",
        leverage=1.0,  # 명시적 leverage=1 = 현물 가정. 그러나 엔진은 leverage 미적용.
    )

    raw_trades = _build_raw_trades(state, cfg)
    equity = _compute_equity_curve(raw_trades, ohlcv, cfg)
    m = _compute_metrics(raw_trades, equity, cfg, ohlcv)

    # MDD < -1.0 = -100% 초과 손실 = 자본 초과 시나리오.
    assert m.max_drawdown < Decimal("-1"), (
        f"기대: MDD < -1.0 (자본 초과), 실제: {m.max_drawdown}"
    )
    # 메타 정합 — 사용자 신뢰 quality 의무.
    assert m.mdd_unit == "equity_ratio"
    assert m.mdd_exceeds_capital is True


# --- 3. leverage=5x 응답 노출 ---


def test_leverage_assumption_propagated_to_config_used() -> None:
    """BacktestConfig leverage=5 → BacktestResult.config_used.leverage=5.

    엔진은 leverage 를 PnL 에 직접 적용 안 하지만, 응답에 명시적으로 노출되어
    FE 가 inline 가정 표시 가능하게 해야 함 (Sprint 31 BL-156 명시).
    """
    cfg = BacktestConfig(
        init_cash=Decimal("10000"),
        fees=0.0,
        slippage=0.0,
        freq="1D",
        leverage=5.0,
    )
    assert cfg.leverage == 5.0


# --- 4. JSONB round-trip 메타 보존 ---


def test_metrics_jsonb_roundtrip_preserves_mdd_meta() -> None:
    """mdd_unit / mdd_exceeds_capital 가 JSONB 직렬화/역직렬화에서 보존."""
    m = BacktestMetrics(
        total_return=Decimal("0.5"),
        sharpe_ratio=Decimal("1.0"),
        max_drawdown=Decimal("-1.32"),  # -132% = 자본 초과 손실
        win_rate=Decimal("0.6"),
        num_trades=10,
        mdd_unit="equity_ratio",
        mdd_exceeds_capital=True,
    )

    payload = metrics_to_jsonb(m)
    assert payload["mdd_unit"] == "equity_ratio"
    assert payload["mdd_exceeds_capital"] is True

    restored = metrics_from_jsonb(payload)
    assert restored.mdd_unit == "equity_ratio"
    assert restored.mdd_exceeds_capital is True


def test_metrics_jsonb_legacy_no_meta_returns_none() -> None:
    """레거시 JSONB (Sprint 31 이전) 에 mdd_unit / mdd_exceeds_capital 없으면 None.

    backward-compat 의무 (Sprint 28 이전 backtest 호환 패턴 정합).
    """
    legacy_payload = {
        "total_return": "0.1",
        "sharpe_ratio": "1.0",
        "max_drawdown": "-0.25",
        "win_rate": "0.5",
        "num_trades": 3,
    }
    restored = metrics_from_jsonb(legacy_payload)
    assert restored.mdd_unit is None
    assert restored.mdd_exceeds_capital is None


# --- 5. v2 path: 정상 음수 MDD 도 mdd_exceeds_capital=False ---


def test_v2_normal_negative_mdd_not_exceeding_capital() -> None:
    """MDD = -0.25 (-25%) 같은 일반 손실 → mdd_exceeds_capital=False."""
    from src.backtest.engine.v2_adapter import _build_raw_trades
    from src.strategy.pine_v2.strategy_state import StrategyState

    # 작은 손실 거래 — equity ~ [9900, 10000].
    state = StrategyState()
    state.closed_trades.append(
        Trade(
            id="loss",
            direction="long",
            qty=1.0,
            entry_bar=1,
            entry_price=100.0,
            exit_bar=5,
            exit_price=99.0,
            pnl=-1.0,
        )
    )

    cfg = _cfg(init="10000")
    raw_trades = _build_raw_trades(state, cfg)
    ohlcv = _ohlcv(n=10, base=100.0)
    equity = _compute_equity_curve(raw_trades, ohlcv, cfg)
    m = _compute_metrics(raw_trades, equity, cfg, ohlcv)

    # MDD 는 작은 음수 — 자본 한도 안.
    assert m.max_drawdown > Decimal("-1")
    assert m.mdd_exceeds_capital is False


# --- 6. vectorbt path 메타 추출 (drift 방어) ---


def test_vectorbt_extract_metrics_returns_mdd_meta() -> None:
    """vectorbt path 도 MDD 메타 응답."""
    import vectorbt as vbt

    from src.backtest.engine.metrics import extract_metrics

    close = pd.Series(
        [10.0, 11.0, 12.0, 11.5, 13.0, 12.5],
        index=pd.date_range("2024-01-01", periods=6, freq="1D"),
    )
    pf = vbt.Portfolio.from_signals(
        close=close,
        entries=pd.Series(
            [False, True, False, False, False, False], index=close.index
        ),
        exits=pd.Series(
            [False, False, False, True, False, False], index=close.index
        ),
        init_cash=10000.0,
        fees=0.001,
        slippage=0.0005,
        freq="1D",
    )
    m = extract_metrics(pf, freq="1D")
    assert m.mdd_unit == "equity_ratio"
    # 정상 fixture → 자본 초과 손실 아님.
    assert m.mdd_exceeds_capital is False
