# 조건부 진입 주문의 라이브 desired 상태(target_position)를 검증한다.
"""G1 - `run_live`가 조건부 진입의 desired set을 내보내는지 검증한다.

핵심 계약: 스냅샷은 delta(주문 수량)가 아니라 **`target_position`**(체결 후 순 포지션)을
싣는다. 주문 수량은 reconciler가 거래소 실포지션과의 차로 계산한다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical, run_live


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    """마지막 bar의 전략 상태를 검증할 OHLCV DataFrame을 만든다."""
    start = datetime(2026, 5, 1, tzinfo=UTC)
    return pd.DataFrame(
        {
            "timestamp": [start + timedelta(hours=index) for index in range(len(closes))],
            "open": [closes[0], *closes[:-1]],
            "high": [close * 1.1 for close in closes],
            "low": [close * 0.9 for close in closes],
            "close": closes,
            "volume": [100.0] * len(closes),
        }
    )


_PIVOT_REVERSAL = """//@version=5
strategy("pivot reversal")
if bar_index == 0
    strategy.entry("HeldLong", strategy.long, qty=8)
if bar_index == 1
    strategy.entry("PivRevSE", strategy.short, qty=8, comment="PivRevSE", stop=64)
    strategy.entry("PivRevLE", strategy.long, qty=8, comment="PivRevLE", stop=128)
"""

_MARKET_ENTRY_ONLY = """//@version=5
strategy("market entry only")
if close > open
    strategy.entry("Market", strategy.long, qty=8)
"""

_INVALID_PENDING_ORDERS = """//@version=5
strategy("invalid pending orders")
if bar_index == 0
    strategy.entry("BadStop", strategy.long, qty=8, stop=0)
    strategy.entry("BadQty", strategy.short, qty=0, stop=64)
    strategy.entry("Good", strategy.long, qty=8, stop=128)
"""

# 같은 id 가 열려 있는데 같은 방향으로 재발행되는 형태. 시드 전략 s1_pbr 이 이것이다
# (`le` 가 참인 동안 매 bar `PivRevLE` 재발주).
_SAME_ID_REISSUE = """//@version=5
strategy("same id reissue")
if bar_index == 0
    strategy.entry("PivRevLE", strategy.long, qty=8)
if bar_index == 1
    strategy.entry("PivRevLE", strategy.long, qty=8, stop=128)
"""

# 숏 보유 + 롱 pending. abs() 를 잃는 변이를 잡는 유일한 조합이다.
_SHORT_HELD_LONG_PENDING = """//@version=5
strategy("short held long pending")
if bar_index == 0
    strategy.entry("HeldShort", strategy.short, qty=8)
if bar_index == 1
    strategy.entry("PivRevLE", strategy.long, qty=8, stop=128)
"""

# 실측 라이브 수량 2건을 같은 방향으로 누적. float 로 합하면 0.058998579999999995 가 된다.
_DECIMAL_FIRST_PYRAMID = """//@version=5
strategy("decimal first pyramid")
if bar_index == 0
    strategy.entry("L1", strategy.long, qty=0.02953691)
if bar_index == 1
    strategy.entry("L2", strategy.long, qty=0.02946167)
    strategy.entry("L3", strategy.long, qty=0.001, stop=128)
"""

# qty= 미지정 -> percent_of_equity 사이징 -> 소수 20자리가 나오는 경로.
_PERCENT_OF_EQUITY_STOP = """//@version=5
strategy("percent of equity stop")
if bar_index == 0
    strategy.entry("PivRevLE", strategy.long, stop=128)
"""


def _reported(result: object) -> dict[str, dict[str, object]]:
    """리포트의 pending_orders 를 trade_id 로 색인한다."""
    report = result.strategy_state_report  # type: ignore[attr-defined]
    return {order["trade_id"]: order for order in report["pending_orders"]}


def test_reversal_target_position_lets_reconciler_derive_tv_order_size() -> None:
    """롱 보유 중 숏 stop 의 목표는 -8 이고, 실포지션 +8 과의 차가 TV 규칙의 16 이다."""
    result = run_live(_PIVOT_REVERSAL, _ohlcv([100.0, 100.0]))

    reported = _reported(result)
    assert reported["PivRevSE"]["target_position"] == "-8.00000000"
    # 2^3 보유 - (-2^3) 목표 = 2^4. 정답 16은 청산분을 빠뜨린 8, 중복합산한 24,
    # 무포지션 0과 서로 충돌 없이 구별된다.
    position_size = Decimal(str(result.strategy_state_report["position_size"]))
    implied_order_qty = abs(Decimal(reported["PivRevSE"]["target_position"]) - position_size)
    assert implied_order_qty == Decimal("16")
    # 같은 방향(롱) pending 은 pyramiding add-on 이라 보유분을 더한 16 이 목표다.
    assert reported["PivRevLE"]["target_position"] == "16.00000000"


def test_same_id_reissue_targets_unchanged_position() -> None:
    """같은 id 가 같은 방향으로 재발행되면 엔진은 close 후 재open 이라 순변화가 0이다.

    delta 를 내보내면 거래소 포지션이 2배가 된다(s1_pbr 의 실제 형태).
    목표는 보유분과 동일한 +8 이므로 reconciler 가 주문을 내지 않는다.
    """
    result = run_live(_SAME_ID_REISSUE, _ohlcv([100.0, 100.0]))

    reported = _reported(result)
    assert reported["PivRevLE"]["target_position"] == "8.00000000"
    position_size = Decimal(str(result.strategy_state_report["position_size"]))
    assert Decimal(reported["PivRevLE"]["target_position"]) - position_size == Decimal("0")


def test_short_position_with_long_pending_targets_positive() -> None:
    """숏 보유 + 롱 pending 의 목표는 +8 이다 (부호 보존)."""
    result = run_live(_SHORT_HELD_LONG_PENDING, _ohlcv([100.0, 100.0]))

    reported = _reported(result)
    assert reported["PivRevLE"]["target_position"] == "8.00000000"
    position_size = Decimal(str(result.strategy_state_report["position_size"]))
    assert position_size == Decimal("-8")
    assert abs(Decimal(reported["PivRevLE"]["target_position"]) - position_size) == Decimal("16")


def test_target_position_sums_same_side_in_decimal_space() -> None:
    """같은 방향 보유분 합산은 Decimal-first 여야 한다.

    실측 라이브 수량 2건을 float 로 누적하면 0.058998579999999995 가 나온다.
    정답 0.05899858 + 신규 0.001 = 0.05999858 이고 오염값과 문자열로 구별된다.
    이 값은 JSONB 를 거쳐 화면까지 가므로 오염되면 사용자가 그 숫자를 본다.
    """
    result = run_live(_DECIMAL_FIRST_PYRAMID, _ohlcv([100.0, 100.0]))

    assert _reported(result)["L3"]["target_position"] == "0.05999858"


def test_pending_orders_are_quantized_to_api_precision() -> None:
    """percent_of_equity 사이징의 소수 20자리를 8자리로 절삭한다.

    `OrderRequest.quantity`/`trigger_price` 는 Field(decimal_places=8) 이다. 시장가
    경로는 Numeric(18,8) DB 왕복이 양자화하지만 조건부 경로는 JSONB 문자열로만 나가서
    그 양자화가 없다. 자르지 않으면 전량 ValidationError 로 거부된다.
    """
    result = run_live(
        _PERCENT_OF_EQUITY_STOP,
        _ohlcv([101567.4]),
        initial_capital=1000.0,
        live_position_size_pct=3.0,
    )

    order = _reported(result)["PivRevLE"]
    for key in ("target_position", "entry_qty", "stop_price"):
        assert -Decimal(str(order[key])).as_tuple().exponent <= 8, (key, order[key])
    # 양자화 전 원값은 0.00029537036490054884 (소수 20자리) 였다.
    assert Decimal(str(order["entry_qty"])) > 0


def test_result_pending_orders_dataclass_mirrors_report() -> None:
    """★reconciler 가 실제로 소비하는 것은 `result.pending_orders` 다.

    리포트만 검증하면 반환 인자를 지워도 전건 GREEN 이 된다.
    """
    result = run_live(_PIVOT_REVERSAL, _ohlcv([100.0, 100.0]))

    assert [order.trade_id for order in result.pending_orders] == ["PivRevLE", "PivRevSE"]
    by_id = {order.trade_id: order for order in result.pending_orders}
    assert by_id["PivRevSE"].target_position == Decimal("-8.00000000")
    assert by_id["PivRevSE"].direction == "short"
    assert by_id["PivRevSE"].stop_price == Decimal("64.00000000")
    assert by_id["PivRevSE"].entry_qty == Decimal("8.00000000")
    # comment 는 주문까지 날라야 한다 (시장가 경로의 LiveSignal.comment 와 동일 대우).
    assert by_id["PivRevSE"].comment == "PivRevSE"
    assert [order.trade_id for order in result.pending_orders] == [
        order["trade_id"] for order in result.strategy_state_report["pending_orders"]
    ]


def test_pending_orders_sorted_by_trade_id_regardless_of_issue_order() -> None:
    """정렬 결정론 전용. 발행 순서(SE -> LE)와 정렬 순서(LE -> SE)가 반대다."""
    result = run_live(_PIVOT_REVERSAL, _ohlcv([100.0, 100.0]))

    trade_ids = [order.trade_id for order in result.pending_orders]
    assert trade_ids == sorted(trade_ids)
    assert trade_ids == ["PivRevLE", "PivRevSE"]


def test_run_live_does_not_report_market_entries_as_pending_orders() -> None:
    """시장가 진입만 쓰는 전략은 desired conditional order가 없다."""
    result = run_live(_MARKET_ENTRY_ONLY, _ohlcv([100.0, 128.0]))

    assert result.strategy_state_report["pending_orders"] == []
    assert result.pending_orders == []


def test_run_live_drops_invalid_pending_order_legs() -> None:
    """0 stop/qty 조건부 주문은 poison pill이 되기 전에 제외한다."""
    result = run_live(_INVALID_PENDING_ORDERS, _ohlcv([100.0]))

    assert [order["trade_id"] for order in result.strategy_state_report["pending_orders"]] == [
        "Good"
    ]
    # 드롭 사유는 live 전용 키로만 나간다. `warnings` 에 넣으면 run_live 가 엔진 상태를
    # 변형해 run_historical 과의 패리티(mutation oracle)가 비정상 입력에서 깨진다.
    skips = {skip["trade_id"]: skip for skip in result.strategy_state_report["pending_order_skips"]}
    assert skips["BadStop"]["invalid_fields"] == ["stop_price"]
    assert skips["BadQty"]["invalid_fields"] == ["qty"]
    assert all(skip["reason"] == "invalid_leg" for skip in skips.values())


def test_run_live_pending_orders_do_not_mutate_engine_warnings() -> None:
    """비정상 레그가 있어도 `warnings` 는 run_historical 과 동일해야 한다."""
    ohlcv = _ohlcv([100.0])
    historical = run_historical(_INVALID_PENDING_ORDERS, ohlcv, capture_history=False, strict=False)
    live = run_live(_INVALID_PENDING_ORDERS, ohlcv)

    assert historical.strategy_state is not None
    assert (
        live.strategy_state_report["warnings"]
        == historical.strategy_state.to_report()["warnings"]
    )


# asia 세션 = UTC [0,7). bar 0 이 허용 시각에 파킹하고, 이후 bar 가 금지 시각으로 넘어간다.
_SESSION_STOP_ENTRY = """//@version=5
strategy("session stop entry")
if bar_index == 0
    strategy.entry("PivRevLE", strategy.long, qty=8, stop=128)
"""


def _ohlcv_from_hour(start_hour: int, bars: int) -> pd.DataFrame:
    """지정 UTC 시각부터 1시간 간격 프레임 (세션 게이트 판정용)."""
    start = datetime(2026, 5, 1, start_hour, tzinfo=UTC)
    return pd.DataFrame(
        {
            "timestamp": [start + timedelta(hours=index) for index in range(bars)],
            "open": [100.0] * bars,
            "high": [110.0] * bars,
            "low": [90.0] * bars,
            "close": [100.0] * bars,
            "volume": [100.0] * bars,
        }
    )


def test_desired_set_is_empty_when_carried_into_disallowed_session() -> None:
    """허용 세션에 파킹된 주문이 금지 세션으로 이월되면 거래소에서 걷어내야 한다.

    엔진은 금지 세션 bar 에서 `check_pending_fills` 를 통째로 건너뛰고 주문을
    carry-over 한다(`strategy_state.py:748-752`). 그 동안 거래소에 주문이 남아 있으면
    엔진은 절대 체결하지 않는데 거래소는 체결해 조용히 발산한다.
    (금지 세션에 *새로* 발행하는 경우는 엔진이 진입 발행 단계에서 이미 막는다.)
    """
    blocked = run_live(_SESSION_STOP_ENTRY, _ohlcv_from_hour(6, 2), sessions_allowed=("asia",))

    assert blocked.pending_orders == []
    skips = blocked.strategy_state_report["pending_order_skips"]
    assert [skip["reason"] for skip in skips] == ["session_disallowed"]
    assert [skip["trade_id"] for skip in skips] == ["PivRevLE"]


def test_desired_set_survives_allowed_session() -> None:
    """음성 대조 — 마지막 bar 가 허용 세션이면 그대로 방출된다(과잉차단이 아님)."""
    allowed = run_live(_SESSION_STOP_ENTRY, _ohlcv_from_hour(4, 2), sessions_allowed=("asia",))

    assert [order.trade_id for order in allowed.pending_orders] == ["PivRevLE"]
    assert allowed.strategy_state_report["pending_order_skips"] == []


def test_window_bars_accompanies_placed_bar() -> None:
    """`placed_bar` 는 창 상대 인덱스라 창 크기가 함께 나가야 해석 가능하다."""
    result = run_live(_PIVOT_REVERSAL, _ohlcv([100.0, 100.0]))

    assert result.strategy_state_report["window_bars"] == 2
    assert _reported(result)["PivRevLE"]["placed_bar"] == 1
