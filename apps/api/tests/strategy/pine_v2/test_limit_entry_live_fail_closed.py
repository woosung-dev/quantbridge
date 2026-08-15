# 지정가 진입은 라이브에서 거래소로 나가지 않는다 — 그 fail-closed 를 못박는다 (2026-08-15 · U8).
"""`entry(limit=)` 의 라이브 축 — **아무것도 발주하지 않는다.**

**왜 막는가 (2026-08-15 결정).** 백테스트 엔진은 limit pending 을 지정가로 체결하지만,
라이브 발주 경로는 `OrderRequest.trigger_price`(= stop) 하나만 표현한다. 그대로 내보내면
「지정가로 사겠다」는 의도가 **시장가나 트리거 주문으로 왜곡**돼 거래소에 도달한다.
엔진이 올바로 표현하지 못하는 진입을 내보내느니 **막는 쪽**이 낫다.

★**이 전환은 동작 변경이다.** 종전에는 `entry(limit=)` 전략이 라이브에서 **시장가 체결**을
받고 있었다(인터프리터가 limit 을 버리고 market intent 로 보냈다). 이 회차 뒤에는 그 진입이
아예 안 나간다. 리포트 ⑨ 의 문구가 그 사실을 선언한다.

★**「코드 0줄」이 「동작 불변」을 뜻하지 않는다** — 라이브 task·reconciler 는 한 줄도 안
고쳤지만 공유 타입(`PendingOrder`)이 바뀌었으므로 결과가 바뀐다. 그래서 여기서 `run_live`
를 실제로 태워 **signals 와 `PendingOrderSnapshot` 양쪽이 비어 있는지**를 잰다.
순수 함수 테스트는 배선의 증거가 아니다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from src.strategy.pine_v2.event_loop import run_live


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    start = datetime(2026, 5, 1, tzinfo=UTC)
    return pd.DataFrame(
        {
            "timestamp": [start + timedelta(hours=i) for i in range(len(closes))],
            "open": [closes[0], *closes[:-1]],
            "high": [c * 1.1 for c in closes],
            "low": [c * 0.9 for c in closes],
            "close": closes,
            "volume": [100.0] * len(closes),
        }
    )


# 체결되지 않을 만큼 먼 지정가 — pending 으로 남아 발주 대상 후보가 되는 형태.
_LIMIT_ENTRY = """//@version=5
strategy("limit entry")
if bar_index == 1
    strategy.entry("LimitLong", strategy.long, qty=8, limit=10)
"""

# 음성 대조 — 같은 모양의 **stop** 진입은 지금까지처럼 발주 대상이어야 한다.
_STOP_ENTRY = """//@version=5
strategy("stop entry")
if bar_index == 1
    strategy.entry("StopLong", strategy.long, qty=8, stop=128)
"""


def test_limit_entry_emits_no_pending_order_snapshot() -> None:
    """★양성 — 지정가 진입은 `pending_orders`(발주 desired set)에 **실리지 않는다**."""
    result = run_live(_LIMIT_ENTRY, _ohlcv([100.0, 100.0]))

    assert result.pending_orders == [], (
        f"지정가 진입이 거래소 발주 대상으로 나갔다: {result.pending_orders}"
    )
    reported = result.strategy_state_report["pending_orders"]
    assert reported == [], f"리포트에도 실리면 안 된다: {reported}"


def test_limit_entry_emits_no_market_signal() -> None:
    """★양성 — 시장가 signal 로도 새지 않는다.

    고치기 전의 병이 정확히 이것이었다 — 인터프리터가 limit 을 버리고 `MarketIntent` 로
    보내서 **지정가 의도가 시장가로 체결**됐다. `and limit is None` 가드가 빠지면 여기가 red 다.
    """
    result = run_live(_LIMIT_ENTRY, _ohlcv([100.0, 100.0]))

    assert result.signals == [], f"지정가 진입이 시장가 signal 로 샜다: {result.signals}"


def test_limit_entry_is_recorded_as_a_policy_skip_not_a_broken_leg() -> None:
    """★관측 — 막았다는 사실이 원장에 남고, 사유가 「고장」과 구분된다.

    `invalid_leg` 로 뭉뚱그리면 운영자가 「값이 깨졌다」와 「이 주문 종류는 라이브 미지원」을
    구분하지 못한다. 전자는 조사할 일이고 후자는 정책이다.
    """
    result = run_live(_LIMIT_ENTRY, _ohlcv([100.0, 100.0]))

    skips = result.strategy_state_report["pending_order_skips"]
    assert len(skips) == 1, f"막은 사실이 원장에 남아야 한다: {skips}"
    assert skips[0]["trade_id"] == "LimitLong"
    assert skips[0]["reason"] == "limit_entry_unsupported_live", (
        f"사유가 정책 라벨이어야 한다 (실제 {skips[0]['reason']!r})"
    )


def test_stop_entry_still_dispatches() -> None:
    """★음성 대조 — 이게 없으면 「pending 을 전부 막기」로도 위 셋이 통과한다(판별력 0)."""
    result = run_live(_STOP_ENTRY, _ohlcv([100.0, 100.0]))

    assert len(result.pending_orders) == 1, (
        f"stop 진입까지 막혔다 — 이 회차는 stop 축을 건드리지 않는다: {result.pending_orders}"
    )
    assert result.pending_orders[0].trade_id == "StopLong"
    assert result.strategy_state_report["pending_order_skips"] == []


def test_limit_entry_skip_reason_is_registered_for_metrics() -> None:
    """계측 배선 — 새 사유가 `_PENDING_ORDER_SKIP_REASONS` 에 등재돼 있어야 한다.

    미등재면 `_count_pending_order_skips` 가 `other` 버킷으로 접어 **어떤 정책이 몇 번
    발화했는지**를 영영 못 본다. 「값을 실어야 없었다를 말할 수 있다」는 [BL-523] 의 규율과 같다.
    """
    from src.tasks.live_signal import _PENDING_ORDER_SKIP_REASONS

    assert "limit_entry_unsupported_live" in _PENDING_ORDER_SKIP_REASONS
