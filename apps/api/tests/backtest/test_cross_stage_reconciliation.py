# BL-391 cross-stage 오라클 — trades → equity → metrics 3단 정합 불변식
"""`_build_raw_trades` → `_compute_equity_curve` → `_compute_metrics` 계약 검증.

세 단계는 서로 의존하는데(equity ← trade pnl, metrics ← 양쪽) 각각 **격리로만**
테스트돼 왔다. 그래서 단계 **사이**의 off-by-one 은 각 단계의 단위 테스트를 전부
통과하면서 살아남을 수 있다 — "testability 를 위해 추출된 순수함수" 안티패턴.

고정하는 불변식 (closed-trade · no-funding 조건):

    equity[-1] - init_cash == Σ trade.pnl                       (1단 ↔ 2단)
    metrics.net_profit_abs == metrics.total_return * init_cash  (1단 ↔ 2단, 3단 경유)

두 번째가 특히 유효한 이유 — `_compute_metrics` 안에서
`net_profit_abs` 는 **trade 목록**에서(`v2_adapter.py:719`),
`total_return` 은 **equity 종가**에서(`:663`) 각각 독립적으로 계산된다.
코드가 둘의 일치를 강제하지 않으므로 이 등식은 동어반복이 아니다.

★`trade.pnl` 은 수수료·슬리피지를 이미 차감한 **net** 이다(`v2_adapter.py:360`).
  그래서 이 불변식은 fees > 0 에서도 그대로 성립해야 한다 — 성립하지 않으면
  비용이 한쪽 단계에서만 반영됐다는 뜻이다.

판별력 실측 (2026-08-03, 변조 2종):

    변조                                        이 파일   기존 backtest 스위트
    exit-bar off-by-one (`<=` → `<`)             red      **red** (557건 중 3건)
    `net_profit_abs` 비용 이중 차감               red      **green** (557 passed)

★백로그 BL-391 이 표적으로 지목한 off-by-one 은 **이미 커버돼 있었다** —
  `test_golden_oracle_minimal` 이 equity **전 계열**을 하드코딩 기대값과 대조하고
  `test_v2_adapter::test_equity_curve_accrues_realized_pnl_on_exit_bar` 가 그 경계를
  직접 짚는다. 실제로 비어 있던 곳은 (a) **metrics 단계에서 두 집계가 서로 어긋나는 것**
  과 (b) **fees > 0 경로**였다 — 기존 골든은 전부 `fees=0` 이다.
  off-by-one 케이스를 남겨두는 이유는 새로 잡아서가 아니라 계약을 문서화하기 위해서다.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.backtest.engine.types import BacktestConfig
from src.backtest.engine.v2_adapter import (
    _build_raw_trades,
    _compute_equity_curve,
    _compute_metrics,
)
from tests.fixtures.backtest_golden_minimal import (
    make_s1_ohlcv,
    make_s1_state,
    make_s2_ohlcv,
    make_s2_state,
)

_INIT_CASH = Decimal("1000")


def _cfg(fees: float = 0.0, slippage: float = 0.0) -> BacktestConfig:
    return BacktestConfig(init_cash=_INIT_CASH, fees=fees, slippage=slippage, freq="1D")


@pytest.mark.parametrize(
    ("scenario", "make_ohlcv", "make_state"),
    [
        # S1 의 exit_bar=4 는 **마지막 bar** 다. 그 bar 에서 실현과 평가가 겹치면
        # (예: `exit_bar_index <= bar_idx` 를 `<` 로 잘못 쓰면) pnl 이 두 번 셰인다.
        ("s1_exit_on_final_bar", make_s1_ohlcv, make_s1_state),
        # S2 는 exit 가 중간 bar(1, 4)에 있고 마지막 bar 는 flat 이다.
        ("s2_multi_trade_flat_tail", make_s2_ohlcv, make_s2_state),
    ],
)
def test_closed_trade_pnl_reconciles_with_equity_delta(
    scenario: str,
    make_ohlcv: object,
    make_state: object,
) -> None:
    """1단 ↔ 2단: Σ trade.pnl == equity 종가 delta."""
    ohlcv = make_ohlcv()  # type: ignore[operator]
    state = make_state()  # type: ignore[operator]
    cfg = _cfg()

    trades = _build_raw_trades(state, cfg, ohlcv)
    assert trades, f"{scenario}: trade 0건이면 불변식이 공허하게 참이다"
    assert all(t.status == "closed" for t in trades), (
        f"{scenario}: 이 오라클은 closed-trade 전용 (open 포지션은 평가손익이 섞인다)"
    )

    equity = _compute_equity_curve(trades, ohlcv, cfg)

    pnl_sum = sum((t.pnl for t in trades), start=Decimal("0"))
    equity_delta = equity.iloc[-1] - _INIT_CASH
    assert equity_delta == pnl_sum, (
        f"{scenario}: 단계 간 불일치\n"
        f"  Σ trade.pnl      = {pnl_sum}\n"
        f"  equity 종가 delta = {equity_delta}\n"
        "trades → equity 사이에서 pnl 이 누락되거나 이중 계상됐다."
    )


@pytest.mark.parametrize(("fees", "slippage"), [(0.0, 0.0), (0.001, 0.0005)])
def test_reconciliation_holds_with_costs(fees: float, slippage: float) -> None:
    """비용이 있어도 성립해야 한다 — `trade.pnl` 이 net 이기 때문이다.

    한쪽 단계에서만 비용을 차감하면 이 등식이 깨진다.
    """
    ohlcv = make_s2_ohlcv()
    cfg = _cfg(fees=fees, slippage=slippage)

    trades = _build_raw_trades(make_s2_state(), cfg, ohlcv)
    equity = _compute_equity_curve(trades, ohlcv, cfg)

    pnl_sum = sum((t.pnl for t in trades), start=Decimal("0"))
    assert equity.iloc[-1] - _INIT_CASH == pnl_sum, (
        f"fees={fees} slippage={slippage} 에서 단계 간 비용 반영이 어긋났다"
    )
    if fees > 0:
        # 음성 대조 — 비용이 실제로 걸리는 입력인지 확인한다.
        # 이게 없으면 fees 파라미터가 무시돼도 테스트가 통과한다.
        zero_cost_trades = _build_raw_trades(make_s2_state(), _cfg(), ohlcv)
        zero_cost_sum = sum((t.pnl for t in zero_cost_trades), start=Decimal("0"))
        assert pnl_sum != zero_cost_sum, "비용이 pnl 을 전혀 안 바꿨다 — 대조군으로 무효"


def test_metrics_net_profit_reconciles_with_total_return() -> None:
    """1단 ↔ 3단 ↔ 2단: `net_profit_abs`(trades) == `total_return`(equity) × init_cash.

    `_compute_metrics` 는 두 값을 서로 다른 입력에서 독립적으로 계산한다.
    """
    ohlcv = make_s2_ohlcv()
    cfg = _cfg(fees=0.001, slippage=0.0005)

    trades = _build_raw_trades(make_s2_state(), cfg, ohlcv)
    equity = _compute_equity_curve(trades, ohlcv, cfg)
    metrics = _compute_metrics(trades, equity, cfg, ohlcv)

    assert metrics.net_profit_abs is not None
    assert metrics.total_return is not None
    implied = metrics.total_return * _INIT_CASH
    assert metrics.net_profit_abs == implied, (
        "metrics 안에서 trade 집계와 equity 집계가 어긋났다\n"
        f"  net_profit_abs (trades 출처) = {metrics.net_profit_abs}\n"
        f"  total_return × init_cash     = {implied}"
    )
