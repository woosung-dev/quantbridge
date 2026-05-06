# StrategyState 포지션 사이징 helper 단위 회귀 (BL-185, Sprint 37 PR1 TDD-1.2a).
"""BL-185 TDD-1.2a RED — StrategyState.compute_qty + configure_sizing + running_equity.

배경:
- virtual_strategy.py:142 가 qty=1.0 hardcode → BTC 1 BTC = 수천만원 포지션 → 결과 왜곡.
- Pine strategy(default_qty_type, default_qty_value) 3종 (percent_of_equity / cash / fixed)
  을 StrategyState 가 직접 계산하는 helper 가 필요.
- close() 시 running_equity += pnl 갱신 (fees=0 Sprint 37 가정 — 후속 TODO).

Sprint 37 acceptance (PR1 spec 4 항목 중 a/b/c 의 unit-level):
1. configure_sizing 미호출 → compute_qty=1.0 (기존 호환)
2. default_qty_type=None / 미지원 string → 1.0 fallback
3. percent_of_equity: qty = running_equity * pct / 100 / fill_price
4. cash: qty = cash / fill_price
5. fixed: qty = value
6. close() PnL 반영 → running_equity 갱신 → 다음 entry percent_of_equity 가 새 running_equity 사용
"""
from __future__ import annotations

import pytest

from src.strategy.pine_v2.strategy_state import StrategyState


def _new_state() -> StrategyState:
    return StrategyState()


def test_compute_qty_default_when_not_configured() -> None:
    """configure_sizing 미호출 시 1.0 fallback (기존 qty=1 contract 호환)."""
    state = _new_state()
    assert state.compute_qty(fill_price=100.0) == pytest.approx(1.0)


def test_compute_qty_returns_one_when_default_qty_type_none() -> None:
    """default_qty_type=None 명시 시 1.0 fallback."""
    state = _new_state()
    state.configure_sizing(
        initial_capital=10000.0,
        default_qty_type=None,
        default_qty_value=None,
    )
    assert state.compute_qty(fill_price=100.0) == pytest.approx(1.0)


def test_compute_qty_unsupported_type_falls_back_to_one() -> None:
    """미지원 default_qty_type 문자열 → 1.0 fallback (silent drift 방지)."""
    state = _new_state()
    state.configure_sizing(
        initial_capital=10000.0,
        default_qty_type="strategy.unknown_type",
        default_qty_value=99.0,
    )
    assert state.compute_qty(fill_price=100.0) == pytest.approx(1.0)


def test_compute_qty_percent_of_equity_30pct() -> None:
    """percent_of_equity 30%, equity=10000, fill_price=100 → 30 (= 10000*0.3/100)."""
    state = _new_state()
    state.configure_sizing(
        initial_capital=10000.0,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=30.0,
    )
    assert state.compute_qty(fill_price=100.0) == pytest.approx(30.0)


def test_compute_qty_cash_100usdt_at_50() -> None:
    """cash 100, fill_price=50 → 2 (= 100/50)."""
    state = _new_state()
    state.configure_sizing(
        initial_capital=10000.0,
        default_qty_type="strategy.cash",
        default_qty_value=100.0,
    )
    assert state.compute_qty(fill_price=50.0) == pytest.approx(2.0)


def test_compute_qty_fixed_returns_value_directly() -> None:
    """fixed 0.01 → 0.01 (fill_price 무관)."""
    state = _new_state()
    state.configure_sizing(
        initial_capital=10000.0,
        default_qty_type="strategy.fixed",
        default_qty_value=0.01,
    )
    # fill_price 무관 — 0.01 그대로
    assert state.compute_qty(fill_price=50.0) == pytest.approx(0.01)
    assert state.compute_qty(fill_price=10000.0) == pytest.approx(0.01)


def test_compute_qty_zero_or_negative_fill_price_safe_fallback() -> None:
    """fill_price <= 0 시 percent_of_equity / cash 는 0 반환 (DivisionByZero 차단)."""
    state = _new_state()
    state.configure_sizing(
        initial_capital=10000.0,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=30.0,
    )
    assert state.compute_qty(fill_price=0.0) == pytest.approx(0.0)
    assert state.compute_qty(fill_price=-50.0) == pytest.approx(0.0)


def test_running_equity_initialized_by_configure_sizing() -> None:
    """configure_sizing 호출 시 running_equity = initial_capital."""
    state = _new_state()
    state.configure_sizing(
        initial_capital=10000.0,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=30.0,
    )
    assert state.running_equity == pytest.approx(10000.0)
    assert state.initial_capital == pytest.approx(10000.0)


def test_running_equity_updated_after_long_close_with_profit() -> None:
    """long entry → 가격 +50% close → running_equity = initial + pnl."""
    state = _new_state()
    state.configure_sizing(
        initial_capital=10000.0,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=100.0,  # 자기자본 100% 진입
    )
    # 가격 100 에서 entry. percent_of_equity 100% × 10000 / 100 = qty 100.
    qty_at_entry = state.compute_qty(fill_price=100.0)
    state.entry("L", "long", qty=qty_at_entry, bar=0, fill_price=100.0)
    # 가격 150 에서 close. PnL = (150-100) * 100 * 1.0 = +5000.
    state.close("L", bar=1, fill_price=150.0)
    assert state.running_equity == pytest.approx(15000.0), (
        f"close 후 running_equity 갱신 실패: {state.running_equity}"
    )


def test_compute_qty_uses_updated_running_equity_after_close() -> None:
    """close 후 running_equity 갱신 → 다음 entry 의 percent_of_equity 가 새 equity 기반."""
    state = _new_state()
    state.configure_sizing(
        initial_capital=10000.0,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=30.0,
    )
    # 1차 entry: 30% × 10000 / 100 = qty 30
    qty1 = state.compute_qty(fill_price=100.0)
    assert qty1 == pytest.approx(30.0)
    state.entry("L", "long", qty=qty1, bar=0, fill_price=100.0)
    state.close("L", bar=1, fill_price=200.0)
    # PnL = (200-100) * 30 = +3000 → running_equity = 13000.
    assert state.running_equity == pytest.approx(13000.0)
    # 2차 entry: 30% × 13000 / 100 = qty 39
    qty2 = state.compute_qty(fill_price=100.0)
    assert qty2 == pytest.approx(39.0), (
        f"갱신된 running_equity 미반영: 기대 39, 실측 {qty2}"
    )


def test_running_equity_decreases_after_loss_close() -> None:
    """long → 가격 -50% close → running_equity 감소."""
    state = _new_state()
    state.configure_sizing(
        initial_capital=10000.0,
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=100.0,
    )
    qty = state.compute_qty(fill_price=100.0)  # 100
    state.entry("L", "long", qty=qty, bar=0, fill_price=100.0)
    state.close("L", bar=1, fill_price=50.0)  # PnL = (50-100) * 100 = -5000
    assert state.running_equity == pytest.approx(5000.0)


def test_short_close_running_equity_inverse_sign() -> None:
    """short entry → 가격 하락 close → 이익. running_equity 갱신."""
    state = _new_state()
    state.configure_sizing(
        initial_capital=10000.0,
        default_qty_type="strategy.fixed",
        default_qty_value=10.0,
    )
    state.entry("S", "short", qty=10.0, bar=0, fill_price=100.0)
    state.close("S", bar=1, fill_price=80.0)  # short PnL = (80-100) * 10 * (-1) = +200
    assert state.running_equity == pytest.approx(10200.0)
