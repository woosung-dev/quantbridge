"""[BL-595] / ADR-025 — 조건부 진입 체결 권한이 원장으로 넘어간 뒤의 엔진 계약.

사망 픽스처(`test_bl595_death_fixtures.py`)가 **실제 사건**을 재현한다면 이 파일은 그
사건이 성립하는 **경계**를 고정한다. 픽스처만으로는 다음을 구분할 수 없다:

- `None`(모른다) 과 `()`(원장이 답했는데 체결이 없다) 가 정말 다르게 동작하는가
- 봉이 트리거를 **안 덮어도** 원장이 증언하면 체결하는가 (= 형 B 차단의 본체)
- 원장 체결이 창 **밖**일 때 어느 봉에 얹히는가
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import run_live
from src.strategy.pine_v2.strategy_state import (
    ConditionalFillAuthority,
    LedgerConditionalFill,
    PendingOrder,
    StrategyState,
)

_START = datetime(2026, 8, 5, 0, 0, tzinfo=UTC)

# 조건부 stop 진입 하나만 거는 최소 전략. bar 0 에 무장하고 그 뒤 봉에서 체결을 노린다.
_STOP_ENTRY = """//@version=5
strategy("stop entry")
if bar_index == 0
    strategy.entry("E", strategy.long, qty=1, stop=128)
"""


def _ohlcv(closes: list[float], *, high_mult: float = 1.1) -> pd.DataFrame:
    """`test_run_live_pending_orders._ohlcv` 와 같은 배율 관례(고가 = 종가 × 1.1)."""
    frame = pd.DataFrame(
        {
            "open": closes,
            "high": [close * high_mult for close in closes],
            "low": [close * 0.9 for close in closes],
            "close": closes,
            "volume": [1.0] * len(closes),
        }
    )
    frame["timestamp"] = [_START + timedelta(minutes=index) for index in range(len(closes))]
    return frame


def _bar_time(index: int) -> datetime:
    return _START + timedelta(minutes=index)


def _report(result: object) -> dict:
    return result.strategy_state_report  # type: ignore[attr-defined]


# ── 3-상태: None / () / 값 있음 ────────────────────────────────────────────────


def test_without_authority_the_engine_simulates_as_before() -> None:
    """`None` = 「원장을 못 읽었다」 → 종전 경로. 봉이 트리거를 덮으면 체결한다."""
    result = run_live(_STOP_ENTRY, _ohlcv([100.0, 120.0]))

    assert _report(result)["position_size"] > 0
    assert _report(result)["ledger_fill_census"] == {}


def test_empty_authority_blocks_a_fill_the_ledger_never_witnessed() -> None:
    """★[BL-595] 형 A — 봉이 트리거를 덮어도 원장이 증언하지 않으면 체결하지 않는다.

    `()` 는 「원장이 답했는데 조건부 체결이 없다」이고, 그것이 사망 5건 중 4건의 정체다.
    """
    result = run_live(_STOP_ENTRY, _ohlcv([100.0, 120.0]), ledger_conditional_fills=())

    assert _report(result)["position_size"] == 0
    assert _report(result)["ledger_fill_census"] == {"engine_only_suppressed": 1}
    # 주문은 사라지지 않는다 — reconciler 가 거래소 주문을 유지할 근거가 desired 다.
    assert [order["trade_id"] for order in _report(result)["pending_orders"]] == ["E"]


def test_witnessed_fill_opens_the_trade_even_when_the_bar_never_touched_the_stop() -> None:
    """★[BL-595] 형 B — 엔진이 못 본 봉에서 거래소가 체결한 경우.

    `39731d57` 이 죽은 이유가 이것이다: 창의 마지막 봉 고가(64065.0)가 엔진의 stop(64071.91)
    에 못 미쳤는데 거래소는 이미 체결했다. 여기서는 고가를 트리거 아래로 눌러 그 상황을 만든다.
    """
    ohlcv = _ohlcv([100.0, 100.0], high_mult=1.0)  # 고가 100 < stop 128
    result = run_live(
        _STOP_ENTRY,
        ohlcv,
        ledger_conditional_fills=(
            LedgerConditionalFill(trade_id="E", filled_at=_bar_time(1), fill_price=131.5),
        ),
    )

    report = _report(result)
    assert report["position_size"] > 0
    assert report["ledger_fill_census"] == {"ledger_only_adopted": 1}
    # ★체결가는 시뮬 stop(128)이 아니라 **원장 값**이다.
    assert [trade["entry_price"] for trade in report["open_trades"]] == [131.5]


def test_agreeing_fill_still_uses_the_ledger_price() -> None:
    """시뮬도 체결했을 자리라도 가격은 원장이 정한다 — 진실이 하나여야 한다."""
    result = run_live(
        _STOP_ENTRY,
        _ohlcv([100.0, 120.0]),
        ledger_conditional_fills=(
            LedgerConditionalFill(trade_id="E", filled_at=_bar_time(1), fill_price=129.25),
        ),
    )

    report = _report(result)
    assert report["ledger_fill_census"] == {"agree": 1}
    assert [trade["entry_price"] for trade in report["open_trades"]] == [129.25]


def test_orphan_witness_changes_nothing_but_is_counted() -> None:
    """★ADR-025 R4 — 엔진이 안 들고 있는 `trade_id` 는 **채택하지 않는다**. 세기만 한다."""
    result = run_live(
        _STOP_ENTRY,
        _ohlcv([100.0, 100.0], high_mult=1.0),
        ledger_conditional_fills=(
            LedgerConditionalFill(trade_id="없는아이디", filled_at=_bar_time(1), fill_price=131.5),
        ),
    )

    report = _report(result)
    assert report["position_size"] == 0
    assert report["ledger_fill_census"] == {"ledger_only_orphan": 1}


# ── 봉 귀속 ───────────────────────────────────────────────────────────────────


def test_fill_observed_after_the_last_bar_lands_on_the_last_bar() -> None:
    """★관측시각이 마지막 봉보다 뒤인 것이 **정상**이다 — 버리면 엔진이 못 따라간다.

    `39731d57` 의 원장 관측시각(16:24:00.145)은 창의 마지막 봉(16:23)보다 뒤였다.
    """
    result = run_live(
        _STOP_ENTRY,
        _ohlcv([100.0, 100.0], high_mult=1.0),
        ledger_conditional_fills=(
            LedgerConditionalFill(
                trade_id="E", filled_at=_bar_time(1) + timedelta(seconds=59), fill_price=131.5
            ),
        ),
    )

    assert _report(result)["position_size"] > 0


def test_fill_observed_before_the_window_is_dropped() -> None:
    """창 시작보다 앞선 체결은 엔진이 표현할 수 있는 지평 밖이다 — 오늘과 같은 지평.

    ★**이건 안전성 주장이 아니라 한계의 동결이다**(codex challenge P2). 300봉(1분이면 5시간)
    보다 오래 든 포지션은 오늘도 진입 봉이 창을 벗어나면 재생이 잃는다 — 이 수리가 그 문제를
    만들지도 고치지도 않는다. 다만 **조용히 잃지는 않게** 세어서 내보낸다(아래 counter 테스트).
    """
    result = run_live(
        _STOP_ENTRY,
        _ohlcv([100.0, 100.0], high_mult=1.0),
        ledger_conditional_fills=(
            LedgerConditionalFill(
                trade_id="E", filled_at=_START - timedelta(minutes=1), fill_price=131.5
            ),
        ),
    )

    report = _report(result)
    assert report["position_size"] == 0
    assert report["ledger_fill_census"] == {"ledger_fill_out_of_window": 1}


def test_fill_cannot_land_on_a_bar_before_the_order_exists() -> None:
    """무장 이전 봉에 얹힌 증언은 **고아**다 — pending 이 아직 없기 때문이다.

    ★**행위는 계상되지만 census 에는 안 잡힌다.** census 는 이 tick 이 실제로 판정하는
    마지막 봉에서만 센다 — 모든 봉에서 세면 warmup 300봉을 매 tick 다시 세어 카운터가
    사건과 무관하게 자란다(프로덕션 실측 tick 당 **+121**). 그 값으로는 「이 tick 에
    [BL-595] 순간이 있었나」를 물을 수 없다 = 사전등록 관측량의 판별력이 0 이 된다.
    ⇒ 여기서 확인하는 것은 **포지션이 안 열린다**는 행위이고, 계상은 마지막 봉 전용이다.
    """
    result = run_live(
        _STOP_ENTRY,
        _ohlcv([100.0, 100.0], high_mult=1.0),
        ledger_conditional_fills=(
            LedgerConditionalFill(trade_id="E", filled_at=_bar_time(0), fill_price=131.5),
        ),
    )

    report = _report(result)
    assert report["position_size"] == 0
    assert report["ledger_fill_census"] == {}


def test_census_counts_only_the_bar_this_tick_decides_on() -> None:
    """★계상 범위 — warmup 재계상을 막는다.

    같은 증언을 **마지막 봉**에 얹으면 census 가 오르고, **그 앞 봉**에 얹으면 안 오른다.
    이 둘이 갈리지 않으면 카운터가 사건과 무관하게 tick 마다 자란다(실측 +121/tick).
    """
    ohlcv = _ohlcv([100.0, 100.0, 100.0], high_mult=1.0)
    at_last = run_live(
        _STOP_ENTRY,
        ohlcv,
        ledger_conditional_fills=(
            LedgerConditionalFill(trade_id="없는아이디", filled_at=_bar_time(2), fill_price=131.5),
        ),
    )
    before_last = run_live(
        _STOP_ENTRY,
        ohlcv,
        ledger_conditional_fills=(
            LedgerConditionalFill(trade_id="없는아이디", filled_at=_bar_time(1), fill_price=131.5),
        ),
    )

    assert _report(at_last)["ledger_fill_census"] == {"ledger_only_orphan": 1}
    assert _report(before_last)["ledger_fill_census"] == {}


# ── `check_pending_fills` 직접 계약 ───────────────────────────────────────────


def _state_with_pending(*, placed_bar: int = 0) -> StrategyState:
    state = StrategyState()
    state.pending_orders["E"] = PendingOrder(
        id="E", direction="long", qty=1.0, stop_price=128.0, placed_bar=placed_bar
    )
    return state


def test_authority_bypasses_the_same_bar_fill_ban() -> None:
    """★`placed_bar >= bar` 금지는 **시뮬의 규칙**이다. 거래소는 그 규칙을 안 따른다.

    엔진은 매 봉 stop 을 재무장하므로 `placed_bar` 가 늘 최신 봉이다. 그 규칙을 원장 경로에도
    적용하면 「원장이 체결했다고 하는데 엔진은 영원히 못 채우는」 상태가 된다.
    """
    state = _state_with_pending(placed_bar=1)
    filled = state.check_pending_fills(
        bar=1,
        open_=100.0,
        high=100.0,
        low=100.0,
        conditional_fill_authority=ConditionalFillAuthority(
            by_bar={
                1: (LedgerConditionalFill(trade_id="E", filled_at=_bar_time(1), fill_price=131.5),)
            }
        ),
    )

    assert [trade.id for trade in filled] == ["E"]
    assert state.pending_orders == {}


def test_authority_skips_the_margin_gate() -> None:
    """★그 포지션은 **이미 거래소에 존재한다** — 여기서 거절해도 현실은 안 돌아온다.

    `seed_positions_from_ledger` 가 같은 이유로 증거금 게이트를 안 돌린다.
    """
    state = _state_with_pending()
    state.configure_sizing(initial_capital=1.0, leverage=10.0)  # 살 수 없는 자본
    filled = state.check_pending_fills(
        bar=1,
        open_=100.0,
        high=100.0,
        low=100.0,
        conditional_fill_authority=ConditionalFillAuthority(
            by_bar={
                1: (LedgerConditionalFill(trade_id="E", filled_at=_bar_time(1), fill_price=131.5),)
            }
        ),
    )

    assert [trade.id for trade in filled] == ["E"]
    assert state.entry_skips == []


def test_simulation_path_still_enforces_the_margin_gate() -> None:
    """★음성 대조 — 위 우회가 시뮬 경로로 새지 않았는지 같은 상태로 확인한다."""
    state = _state_with_pending()
    state.configure_sizing(initial_capital=1.0, leverage=10.0)
    filled = state.check_pending_fills(bar=1, open_=100.0, high=200.0, low=100.0)

    assert filled == []
    assert [skip["reason"] for skip in state.entry_skips] == ["margin_insufficient"]


def test_disallowed_session_still_wins_over_the_ledger() -> None:
    """금지 세션에서는 reconciler 가 거래소 주문을 걷어내는 것이 계약이다.

    여기서 원장을 우선하면 걷어내기와 채택이 서로를 지운다(`event_loop.py:353` 참조).
    """
    state = _state_with_pending()
    state.sessions_allowed = ("0700-0800",)
    filled = state.check_pending_fills(
        bar=1,
        open_=100.0,
        high=100.0,
        low=100.0,
        bar_ts=_bar_time(1),  # 00:01 UTC — 허용 창 밖
        conditional_fill_authority=ConditionalFillAuthority(
            by_bar={
                1: (LedgerConditionalFill(trade_id="E", filled_at=_bar_time(1), fill_price=131.5),)
            }
        ),
    )

    assert filled == []
    assert "E" in state.pending_orders


@pytest.mark.parametrize("authority", [None, ConditionalFillAuthority(by_bar={})])
def test_census_stays_empty_when_nothing_is_pending(authority: object) -> None:
    """★공허 증가 방지 — pending 이 없으면 어느 경로에서도 census 가 늘지 않는다."""
    state = StrategyState()
    state.check_pending_fills(
        bar=1,
        open_=100.0,
        high=200.0,
        low=100.0,
        conditional_fill_authority=authority,  # type: ignore[arg-type]
    )

    assert state.ledger_fill_census == {}


def test_duplicate_witness_in_one_bar_is_processed_once() -> None:
    """★같은 봉에 같은 `trade_id` 증언이 둘이면 마지막 것만 쓴다 (codex challenge P2).

    `pending_orders.pop` 이 루프 **뒤**에 있어, 그냥 순회하면 두 번째도 매칭돼 반전
    close+open 이 두 번 돌고 **없던 왕복 거래**가 생긴다.
    """
    state = _state_with_pending()
    filled = state.check_pending_fills(
        bar=1,
        open_=100.0,
        high=100.0,
        low=100.0,
        conditional_fill_authority=ConditionalFillAuthority(
            by_bar={
                1: (
                    LedgerConditionalFill(trade_id="E", filled_at=_bar_time(1), fill_price=131.5),
                    LedgerConditionalFill(
                        trade_id="E",
                        filled_at=_bar_time(1) + timedelta(seconds=10),
                        fill_price=140.0,
                    ),
                )
            }
        ),
    )

    assert [trade.id for trade in filled] == ["E"]
    # 마지막 증언의 가격을 쓴다 — 그게 원장이 마지막으로 관측한 현실이다.
    assert [trade.entry_price for trade in filled] == [140.0]
    assert len(state.closed_trades) == 0


def test_out_of_window_fill_is_counted_not_silently_dropped() -> None:
    """★버린 것을 세어서 내보낸다 — 「거래소엔 있는데 엔진이 표현 못 하는 포지션」의 개수다."""
    result = run_live(
        _STOP_ENTRY,
        _ohlcv([100.0, 100.0], high_mult=1.0),
        ledger_conditional_fills=(
            LedgerConditionalFill(
                trade_id="E", filled_at=_START - timedelta(minutes=1), fill_price=131.5
            ),
        ),
    )

    assert _report(result)["ledger_fill_census"] == {"ledger_fill_out_of_window": 1}
