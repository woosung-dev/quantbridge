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


# ── BL-580 (2026-08-03 metric-guard-residual-close) — A-C1 · A-C2 판정 오라클 ──
#
# ★**이 두 테스트는 red→green 게이트가 아니라 「판정용 오라클」이다.** 그렇게 적어 두지
#   않으면 다음 사람이 이것을 수리의 증거로 오독한다.
#
# H4 주장은 **두 단계 실측의 합성**이다:
#   ① `tests/trading/test_order_rejected_metric.py` 가 잰 것 — `order_service.py` 의 계측
#      한 줄이 던지면 도메인 예외가 **아예 발생하지 않고** `OSError` 가 대신 탈출한다.
#      (수리 전 10/10 이 이 이유로 red 였다.)
#   ② 아래 두 테스트가 재는 것 — 호출자는 **예외 타입으로 분기**하므로, 도메인 예외가
#      아닌 것이 올라오면 `mark_failed` + `commit` 이 실행되지 않고 Celery 가 재시도한다.
#
# ①+② ⇒ 계측 한 줄이 이벤트를 outbox 에 `pending` 으로 남기고 결정론적 거절을 3회
# 재시도시킨다. ②는 호출자의 성질이라 수리 뒤에도 참이다 — 그래서 회귀 가드로 남긴다.


async def test_dispatch_skips_mark_failed_when_execute_raises_a_non_domain_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A-C1 오라클 — `execute` 가 도메인 예외가 아닌 것을 던지면 기록 분기가 통째로 빠진다.

    양성 대조는 이미 스위트에 있다 —
    `tests/tasks/test_live_signal_dispatch_task.py::test_kill_switch_active_marks_failed_and_raises`
    가 **같은 하네스에서** `KillSwitchActive` 일 때 `mark_failed(error="kill_switched")`
    + `commit` 이 일어남을 단언한다. 두 테스트의 차이는 **예외 타입 하나뿐**이다.
    """
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from uuid import uuid4

    from tests.tasks.test_live_signal_dispatch_task import (
        _build_active_session,
        _build_pending_event,
        _patch_engine,
        _patch_repos,
    )

    _patch_engine(monkeypatch)
    event = _build_pending_event()
    sess = _build_active_session(uuid4())
    sess.id = event.session_id

    event_repo = AsyncMock()
    event_repo.get_by_id = AsyncMock(return_value=event)
    event_repo.mark_failed = AsyncMock(return_value=1)
    event_repo.commit = AsyncMock()

    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(
        return_value=SimpleNamespace(
            id=sess.strategy_id,
            settings={"leverage": 5, "margin_mode": "cross", "position_size_pct": 10.0},
            pine_source="//@version=5\nstrategy('x')",
        )
    )

    _patch_repos(
        monkeypatch,
        event_repo=event_repo,
        sess_repo=sess_repo,
        strategy_repo=strategy_repo,
        order_repo=AsyncMock(),
        account_repo=AsyncMock(),
        kse_repo=AsyncMock(),
    )

    class _OrderServiceMetricBlown:
        """계측이 터져 도메인 예외 대신 `OSError` 가 올라온 상태를 재현한다."""

        def __init__(self, **_: Any) -> None:
            pass

        async def execute(self, *_a: Any, **_kw: Any) -> tuple[Any, bool]:
            raise OSError("mmap allocation failed")

    import src.trading.services.order_service as trading_service_mod

    monkeypatch.setattr(trading_service_mod, "OrderService", _OrderServiceMetricBlown)

    import src.trading.kill_switch as kill_switch_mod

    monkeypatch.setattr(kill_switch_mod, "KillSwitchService", MagicMock())
    monkeypatch.setattr(kill_switch_mod, "CumulativeLossEvaluator", MagicMock())
    monkeypatch.setattr(kill_switch_mod, "DailyLossEvaluator", MagicMock())

    with pytest.raises(OSError, match="mmap allocation failed"):
        await live_signal_module._async_dispatch_event(event.id)

    event_repo.mark_failed.assert_not_awaited()
    event_repo.commit.assert_not_awaited()


def test_dispatch_task_retries_a_non_domain_error_but_not_a_domain_reject(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A-C2 오라클 — 태스크 레벨도 타입으로 갈린다.

    `dispatch_live_signal_event_task` 는 결정론적 거절 5종을 `{"failed":
    "deterministic_reject"}` 로 종결하고 **재시도하지 않는다**. 계측이 그 타입을 `OSError`
    로 바꾸면 같은 사건이 `except Exception` 으로 떨어져 **재시도 대상**이 된다.
    """
    from unittest.mock import Mock
    from uuid import uuid4

    from celery.exceptions import Retry

    from src.tasks import _worker_loop as worker_loop
    from src.tasks.live_signal import dispatch_live_signal_event_task as task
    from src.trading.exceptions import TradingSessionClosed

    def _drive(exc: BaseException) -> tuple[dict | None, Mock, Retry | None]:
        def _run(coro: Any) -> Any:
            import contextlib

            with contextlib.suppress(Exception):
                coro.close()
            raise exc

        monkeypatch.setattr(worker_loop, "run_in_worker_loop", _run)
        retry = Mock(side_effect=lambda **_kw: Retry())
        monkeypatch.setattr(task, "retry", retry)
        task.push_request(retries=0)
        try:
            try:
                return task.run(str(uuid4())), retry, None
            except Retry as raised:
                return None, retry, raised
        finally:
            task.pop_request()

    # 도메인 거절 — 종결, 재시도 없음
    result, retry, raised = _drive(TradingSessionClosed(sessions=[], current_hour_utc=3))
    assert raised is None
    assert result == {"failed": "deterministic_reject"}
    retry.assert_not_called()

    # 계측이 터져 타입이 바뀐 경우 — 같은 사건이 재시도 대상이 된다
    _result2, retry2, raised2 = _drive(OSError("mmap allocation failed"))
    assert raised2 is not None, "OSError 는 일시 장애로 분류돼 재시도된다"
    retry2.assert_called_once()
