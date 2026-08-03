"""A1~A4 · C1 — `tasks/live_signal.py` 의 「가드 옆 raw」 고장 주입 (BL-580).

★**이 자리들의 형태.** raw `.labels(...).inc()` **바로 뒤**에 같은 사건을 세는
`_count_safely(...)` 가 있다. 즉 레포가 이미 가드를 사 놓고 **그 한 줄 위에서** 무효화한다
(직전 회차 §2 가 `state_handler.py:135` 에서 발견한 것과 같은 형태).

★**바깥 `except` 가 있다는 게 안전하다는 뜻이 아니다.** `_reconcile_conditional_entries` 의
바깥 `except` 는 예외를 `stage="reconcile"` 로 계상하고 로그만 남긴 뒤 **정상과 똑같이 `None`
을 반환**한다. 그래서 「정상 반환」은 이 함수에서 아무 정보도 아니다 — 사전등록대로
**사이트별 비-계측 postcondition** 을 본다(dev-log §1.1 · 2026-08-02 codex G1 BLOCKING#2).

**공통 축 — 「한 줄 아래 가드가 여전히 오르는가」.** S1 이 예측하는 해악이 정확히 이것이라
사이트마다 같은 형태로 잰다. 사이트 고유 postcondition 은 각 테스트에 따로 적는다.

주입은 **라벨 단위**다. 같은 counter 의 다른 호출부까지 터뜨리면 무엇이 원인인지 갈리지 않는다.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest

import src.tasks.live_signal as live_signal_module
from src.common.metrics import (
    qb_live_conditional_divergence_total,
    qb_live_conditional_guard_total,
    qb_live_conditional_reconcile_errors_total,
)
from tests.tasks.test_live_signal_conditional_reconcile import (
    _exchange_order,
    _order,
    _patch_reconcile,
    _pending,
    _position,
    _reconcile,
    _result,
    _session,
)


def _explode_only(
    monkeypatch: pytest.MonkeyPatch, counter: Any, calls: list[dict[str, str]], **match: str
) -> None:
    """`counter.labels(**match)` 호출만 `OSError` 로 터뜨린다.

    ★counter 전체를 터뜨리면 같은 함수의 다른 계측까지 죽어서 **무엇이 원인인지 갈리지
    않는다.** 라벨 단위 주입이라야 「이 한 줄이 뒤를 죽였다」를 말할 수 있다.
    """
    original = counter.labels

    def _labels(**kwargs: str) -> Any:
        if all(kwargs.get(key) == value for key, value in match.items()):
            calls.append(dict(kwargs))
            raise OSError("mmap allocation failed")
        return original(**kwargs)

    monkeypatch.setattr(counter, "labels", _labels)


def _divergence_value(event: str, reason: str) -> float:
    return float(
        qb_live_conditional_divergence_total.labels(event=event, reason=reason)._value.get()
    )


@pytest.mark.asyncio
async def test_exchange_missing_counter_failure_does_not_abort_the_tick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A1 (`:1110`) — 거래소에 없는 resting 주문 계상.

    postcondition: 한 줄 아래 `exchange_divergence` 가드가 오르고, 같은 tick 이 등재
    판단까지 진행한다.
    """
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="cancelled"
    )
    calls: list[dict[str, str]] = []
    _explode_only(
        monkeypatch, qb_live_conditional_reconcile_errors_total, calls, stage="exchange_missing"
    )
    before = _divergence_value("exchange_divergence", "exchange_missing_resting_order")

    await _reconcile(session, _result([_pending()]), harness)

    assert calls, "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert _divergence_value("exchange_divergence", "exchange_missing_resting_order") == before + 1
    harness.order_service.execute.assert_awaited()


@pytest.mark.asyncio
async def test_stand_down_still_cancels_when_its_counter_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A2 (`:1214`) — ★**안전 장치가 통째로 건너뛰어진다** (사전등록 H4).

    hedge mode / 공유 계정에서 stand-down 은 「새로 등재하지 않고 이미 올려둔 조건부 진입을
    **걷는다**」이다. 바로 위 주석이 이유를 적어 놨다 — 「남겨두면 그게 **잘못된 전제로
    체결된다**」. 그 걷어내기 직전의 raw 계측이 던지면 걷어내기가 일어나지 않는다.

    postcondition: 한 줄 아래 `stand_down` 가드가 오르고, resting 조건부 진입에
    `provider.cancel_order` 가 호출된다.
    """
    session = _session()
    resting = _order(session, exchange_order_id="exchange-resting")
    harness = _patch_reconcile(
        monkeypatch,
        local_orders=[resting],
        exchange_orders=[_exchange_order(resting)],
        positions=[_position("long", Decimal("1")), _position("short", Decimal("1"))],
    )
    calls: list[dict[str, str]] = []
    _explode_only(monkeypatch, qb_live_conditional_reconcile_errors_total, calls, stage="positions")
    before = _divergence_value("stand_down", "hedge_mode")

    await _reconcile(session, _result([_pending()]), harness)

    assert calls == [{"stage": "positions"}], "프로덕션 계측 라인이 실제로 실행돼야 한다"
    assert _divergence_value("stand_down", "hedge_mode") == before + 1
    harness.provider.cancel_order.assert_awaited()


@pytest.mark.asyncio
async def test_degraded_input_counter_failure_does_not_abort_the_tick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A3 (`:1234`) — 기준가 부재 계상.

    postcondition: 한 줄 아래 `degraded_input` 가드가 오르고, 전환이 금지된 채로 등재
    판단이 이어진다.
    """
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=None)
    calls: list[dict[str, str]] = []
    _explode_only(
        monkeypatch, qb_live_conditional_guard_total, calls, outcome="reference_unavailable"
    )
    before = _divergence_value("degraded_input", "reference_price_unavailable")

    await _reconcile(
        session, _result([_pending()]), harness, fallback_reference_price=Decimal("99")
    )

    assert calls, "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert _divergence_value("degraded_input", "reference_price_unavailable") == before + 1
    harness.order_service.execute.assert_awaited()


@pytest.mark.asyncio
async def test_reprobe_breach_cap_counter_failure_still_records_the_drop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A4 (`:1500`) — 재조회에서 cap 초과로 드롭할 때의 계상.

    postcondition: 한 줄 아래 `guard_drop/breach_exceeds_cap` 가드가 오른다.
    ★이 자리는 등재를 하지 않는 경로라 `execute` 로는 갈리지 않는다 — **가드 도달성**이
    유일하게 판별력 있는 축이다.
    """
    session = _session()
    # ★계획기 드롭(`:1291`)이 아니라 **재조회 드롭**(`:1500`)을 타야 한다. 최초 기준가는
    #   cap 안이고 재조회 기준가만 cap 을 넘는 형태라야 계획기를 통과해 여기까지 온다
    #   (선례: `test_breach_exceeding_cap_at_reprobe_is_not_converted`).
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("100.5"))
    harness.provider.fetch_last_price = AsyncMock(side_effect=[Decimal("100.5"), Decimal("102")])
    calls: list[dict[str, str]] = []
    _explode_only(monkeypatch, qb_live_conditional_guard_total, calls, outcome="breach_capped")
    before = _divergence_value("guard_drop", "breach_exceeds_cap")

    await _reconcile(
        session,
        _result([_pending()]),
        harness,
        max_trigger_breach_pct=1.0,
    )

    assert calls, "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert _divergence_value("guard_drop", "breach_exceeds_cap") == before + 1


@pytest.mark.asyncio
async def test_position_divergence_deactivation_still_alerts_when_counter_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C1 (`:2572`) — ★**세션이 조용히 죽는다** (사전등록 H2).

    엔진과 거래소가 두 평가 연속 반대 방향이면 세션을 자동 비활성화한다. 그 `commit()`
    **뒤** · `_fire_divergence_alert`(BL-362 무신호 차단 고지) **앞**이 이 자리다.
    여기서 던지면 세션은 죽었는데 **사용자는 통보를 못 받는다.**

    ★이 사이트는 S1 스윕 산출이 아니다 — 손으로 찾았다. 출처를 섞지 않는다.

    postcondition: `_fire_divergence_alert` 가 호출된다.
    """
    from tests.tasks.test_live_signal_instrument_parity import TestDivergenceFailClosed

    fired: list[str] = []
    monkeypatch.setattr(
        live_signal_module,
        "_fire_divergence_alert",
        lambda **kwargs: fired.append(str(kwargs.get("category"))),
    )
    calls: list[dict[str, str]] = []
    _explode_only(
        monkeypatch,
        live_signal_module.qb_live_signal_divergence_total,
        calls,
        stage="position",
        category="direction",
    )

    result = await TestDivergenceFailClosed._evaluate_with_divergence(
        monkeypatch, category="direction", position_size=0.029, previously_seen=True
    )

    assert calls == [{"stage": "position", "category": "direction"}], (
        "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    )
    assert result["deactivated"] == "position_divergence", "세션은 실제로 죽었다"
    assert result["_commit_calls"] == 1, "비활성화는 이미 내구화됐다"
    assert fired == ["position_direction_mismatch"], (
        "세션이 죽었는데 고지가 안 나가면 사용자는 무신호 차단을 알 방법이 없다"
    )
