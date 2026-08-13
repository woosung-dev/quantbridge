# [BL-460] 마진 게이트는 gross 가 아니라 net 자본으로 판정해야 한다.
"""게이트 자본 기준의 gross/net 괴리 오라클.

`close()` 는 `running_equity += trade.pnl` 로 **gross** 만 누적한다("fees=0 Sprint 37
가정"). 그 값이 그대로 `compute_qty`(percent_of_equity) 입력이자 Pine
`strategy.equity` 라서 net 으로 바꾸면 leverage=1 byte-identity 가 깨진다. 그래서
[BL-460] 처방 (a) 를 따른다 — **게이트 전용 net 누적치**(`gate_equity`)를 따로 두고
증거금 판정만 그쪽을 본다. `running_equity` 는 gross 그대로다.

여기 테스트는 그 분리를 양쪽에서 못 박는다.
  ① 괴리 자체 — 왕복 거래 후 gross 는 제자리인데 net 은 비용만큼 깎인다.
  ② 판별 — gross 로 재면 통과하고 net 으로 재면 거절되는 진입이 실제로 거절된다.
  ③ 비회귀 — 비용률 0 이면 두 값이 같아 기존 동작과 구분 불가.
"""

from __future__ import annotations

import pytest

from src.strategy.pine_v2.strategy_state import StrategyState

# leg 당 taker 비용률 = fees + slippage. 1% 는 실측치가 아니라 **판별용 확대값**이다
# (실측은 0.055%+0.014%). 괴리를 게이트 문턱을 넘길 만큼 키우는 것이 목적이다.
COST_RATE = 0.01


def _state_with_round_trips(*, cost_rate: float, trips: int = 10) -> StrategyState:
    """손익 0 인 왕복을 `trips` 회 돌린 상태를 만든다.

    진입가 == 청산가 라 **gross PnL 은 정확히 0** 이다. 따라서 gross 와 net 의 차이는
    전부 비용이고, 다른 원인이 섞이지 않는다.
    """
    state = StrategyState()
    state.configure_sizing(
        initial_capital=1000.0,
        leverage=2.0,
        taker_cost_rate=cost_rate,
    )
    for i in range(trips):
        state.entry(f"T{i}", "long", qty=10.0, bar=i, fill_price=100.0)
        state.close(f"T{i}", bar=i, fill_price=100.0)
    return state


def test_gross_equity_stays_flat_while_gate_equity_absorbs_cost() -> None:
    """① 괴리 — 같은 실행에서 gross 는 1000 그대로, net 은 비용만큼 낮다."""
    state = _state_with_round_trips(cost_rate=COST_RATE)

    # gross: 왕복 손익 0 이므로 초기자본 그대로. (이 값이 strategy.equity / compute_qty 입력)
    assert state.running_equity == pytest.approx(1000.0)

    # net: 10 왕복 × 2 leg × notional 1000 × 1% = 200 차감.
    assert state.gate_equity == pytest.approx(800.0)

    # 괴리가 실재한다는 것 자체를 못 박는다 — 이게 [BL-460] 이 주장한 현상이다.
    assert state.gate_equity < state.running_equity


def test_margin_gate_rejects_entry_that_only_gross_equity_could_afford() -> None:
    """② 판별 — gross 기준이면 허용, net 기준이면 거절인 진입.

    required_margin = 17 * 100 / 2 = 850, buffer 0.95.
      · gross(1000): 850 <= 950 → 허용   ← 수리 전 동작
      · net  ( 800): 850 <= 760 → 거절   ← 수리 후 동작
    두 기준의 판정이 **갈리는** 자리라서 이 단언이 게이트의 자본 기준을 판별한다.
    """
    state = _state_with_round_trips(cost_rate=COST_RATE)

    rejected = state.entry("X", "long", qty=17.0, bar=99, fill_price=100.0)

    assert rejected is None
    assert "X" not in state.open_trades
    assert any("증거금 부족으로 진입 skip" in w for w in state.warnings)
    assert state.entry_skips[-1]["reason"] == "margin_insufficient"


def test_gate_still_allows_entry_that_net_equity_covers() -> None:
    """② 대조군 — net 으로 재도 통과하는 크기는 여전히 통과한다.

    음성 대조가 없으면 "게이트가 그냥 빡빡해졌다" 와 구분되지 않는다.
    required_margin = 15 * 100 / 2 = 750 <= 800 * 0.95 = 760 → 허용.
    """
    state = _state_with_round_trips(cost_rate=COST_RATE)

    allowed = state.entry("X", "long", qty=15.0, bar=99, fill_price=100.0)

    assert allowed is not None
    assert "X" in state.open_trades


def test_zero_cost_rate_keeps_gate_equity_equal_to_gross() -> None:
    """③ 비회귀 — 비용률 0(기본값)이면 net == gross 라 기존 판정과 구분 불가."""
    state = _state_with_round_trips(cost_rate=0.0)

    assert state.gate_equity == pytest.approx(state.running_equity)

    # 수리 전이라면 통과했을 진입이 비용 0 에서는 그대로 통과해야 한다.
    allowed = state.entry("X", "long", qty=17.0, bar=99, fill_price=100.0)
    assert allowed is not None


def test_cost_rate_defaults_to_zero_so_existing_callers_are_unchanged() -> None:
    """③ 비회귀 — `taker_cost_rate` 미지정 호출(기존 전 호출부)은 gross 와 동일하다."""
    state = StrategyState()
    state.configure_sizing(initial_capital=1000.0, leverage=2.0)

    assert state.taker_cost_rate == 0.0
    assert state.gate_equity == pytest.approx(state.running_equity)


def test_entry_leg_cost_is_charged_to_gate_equity_on_open() -> None:
    """진입 leg 비용도 즉시 net 에서 빠진다 — 청산 때 몰아서 빼지 않는다.

    미청산 포지션이 있는 동안에도 게이트가 낙관적으로 보이면 안 된다.
    """
    state = StrategyState()
    state.configure_sizing(initial_capital=1000.0, leverage=2.0, taker_cost_rate=COST_RATE)

    state.entry("L", "long", qty=5.0, bar=0, fill_price=100.0)

    # notional 500 × 1% = 5 만 빠지고, gross 는 아직 아무 변화가 없다(미실현).
    assert state.running_equity == pytest.approx(1000.0)
    assert state.gate_equity == pytest.approx(995.0)
