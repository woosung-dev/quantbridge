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
from typing import Any, ClassVar
from unittest.mock import AsyncMock

import pytest

import src.tasks.live_signal as live_signal_module
from src.common.metrics import (
    qb_live_conditional_divergence_total,
    qb_live_conditional_guard_total,
    qb_live_conditional_reconcile_errors_total,
    qb_live_signal_dispatch_total,
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
    from src.trading.exceptions import (
        KillSwitchActive,
        LeverageCapExceeded,
        MinNotionalNotMet,
        NotionalExceeded,
        TradingSessionClosed,
    )

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

    # ★2026-08-03 metric-guard-residual-sweep — **5종 전부**를 고정한다.
    #   위 한 종만 구동하던 동안, 무재시도 튜플에서 `KillSwitchActive` 를 지우는 변이(M4)를
    #   `tests/tasks` + `tests/trading` **1578건 중 어느 것도 잡지 못했다**(실측).
    #   ★이 튜플은 D8·D9 수리가 기대는 대상이다 — 도메인 타입을 살려 놔도 호출자가 그것을
    #     결정론적 거절로 분류하지 않으면 수리의 값이 사라진다. 그래서 여기서 함께 고정한다.
    #   귀결이 가장 나쁜 것이 `KillSwitchActive` 다: 리스크 게이트가 건 거절이 3회 재시도된
    #   뒤 `max_retries_exhausted` 로 기록돼 **kill-switch 사유가 지워진다**([BL-584] 형태).
    for exc in (
        KillSwitchActive("Kill Switch active for cumulative_loss"),
        NotionalExceeded(
            notional=Decimal("10"),
            available=Decimal("1"),
            leverage=1,
            max_notional=Decimal("1"),
        ),
        LeverageCapExceeded(requested=200, cap=125),
        MinNotionalNotMet(notional=Decimal("1"), min_notional=Decimal("5")),
        TradingSessionClosed(sessions=[], current_hour_utc=3),
    ):
        result_n, retry_n, raised_n = _drive(exc)
        assert raised_n is None, f"{type(exc).__name__} 은 재시도 대상이 아니다"
        assert result_n == {"failed": "deterministic_reject"}, (
            f"{type(exc).__name__} 이 무재시도 튜플에서 빠졌다"
        )
        retry_n.assert_not_called()


# ── BL-580 (2026-08-03 metric-guard-residual-sweep) — D 계열 8곳 고장 주입 ──────
#
# 대상 = `_async_dispatch_event` 의 raw `qb_live_signal_dispatch_total` 11곳 +
# `dispatch_live_signal_event_task` 1곳 중 **프로덕션 도달 경로를 한 줄로 적을 수 있는 8곳**.
#
# ★**공통 기전.** 8곳 전부 `mark_failed`/`mark_dispatched` + `commit()` **뒤**다. 계측이
#   던지면 터미널 dict 가 반환되지 못하고 `OSError` 가 탈출한다. 호출자
#   `dispatch_live_signal_event_task:2793` 은 **예외 타입으로** 재시도를 가르므로(결정론적
#   거절 5종만 무재시도), `OSError` 는 `except Exception` 으로 떨어져 재시도 대상이 된다.
#   ⇒ 사전등록 라벨 **H6**(정상 종결이 재시도로 오분류). D8·D9 는 도메인 예외가 통째로
#   사라지므로 **H5** 가 겹친다.
#
# ★**「commit 뒤라 안전하다」를 근거로 쓰지 않는다.** 그 형태의 산문이 직전 두 회차에서
#   21곳 중 21곳 반증됐다(BL-580). 주입해서 잰다.
#
# ★**빠진 4곳은 도달 경로를 못 적어 판정 보류다** — 하네스를 만들면 프로덕션이 못 만드는
#   상태를 손조립해 「실측 유해」로 적게 된다([BL-582] 함정의 거울상, 직전 회차 codex G6):
#     D2 `:3089` strategy_missing — FK `strategies.id ON DELETE RESTRICT`(`models.py:502`)가
#        세션 존재 중 삭제를 막고, owner 는 등재 시 일치 후 이전 경로가 없다.
#     D3 `:3098` invalid_settings — `update_settings(settings: StrategySettings)` 가 같은
#        클래스를 `model_dump()` 하므로 round-trip 이 항상 유효하다.
#     D4 `:3105` settings_unset — 등록 게이트(`live_session_service.py:84`)가 유일 방벽이고
#        통과 뒤 settings 가 비는 경로가 없다.
#     D10 `:3253` idempotency_conflict — ★**도달 불가**. 유일 raise 지점
#        (`order_service.py:369`)이 `if body_hash is not None` 안인데 `:3230` 은
#        **`body_hash=None`** 을 넘긴다. 즉 그 `except` 는 이 호출자에게 사문(死文)이다.


def _dispatch_strategy(strategy_id: Any) -> Any:
    from types import SimpleNamespace

    return SimpleNamespace(
        id=strategy_id,
        settings={"leverage": 5, "margin_mode": "cross", "position_size_pct": 10.0},
        pine_source="//@version=5\nstrategy('x')",
    )


def _dispatch_harness(
    monkeypatch: pytest.MonkeyPatch,
    *,
    event: Any,
    order_service: type | None = None,
    is_active: bool = True,
    positions: list[Any] | None = None,
) -> Any:
    """`_async_dispatch_event` 를 구동할 표준 대역을 조립하고 `event_repo` 를 돌려준다.

    ★정의 모듈을 patch 하므로 **패치 전에 소비 모듈을 적재**한다 (BL-583 오염 가드).
    `_patch_repos` 가 각 repo 모듈을 먼저 import 하고, 아래 `import ... as mod` 들도 같다.
    """
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from uuid import uuid4

    from tests.tasks.test_live_signal_dispatch_task import (
        _build_active_session,
        _patch_engine,
        _patch_repos,
    )

    _patch_engine(monkeypatch)
    sess = _build_active_session(uuid4())
    sess.id = event.session_id
    sess.is_active = is_active

    event_repo = AsyncMock()
    event_repo.get_by_id = AsyncMock(return_value=event)
    event_repo.mark_failed = AsyncMock(return_value=1)
    event_repo.mark_dispatched = AsyncMock(return_value=1)
    event_repo.commit = AsyncMock()

    sess_repo = AsyncMock()
    sess_repo.get_by_id = AsyncMock(return_value=sess)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=_dispatch_strategy(sess.strategy_id))

    _patch_repos(
        monkeypatch,
        event_repo=event_repo,
        sess_repo=sess_repo,
        strategy_repo=strategy_repo,
        order_repo=AsyncMock(),
        account_repo=AsyncMock(),
        kse_repo=AsyncMock(),
    )

    if order_service is not None:
        import src.trading.services.order_service as trading_service_mod

        monkeypatch.setattr(trading_service_mod, "OrderService", order_service)

    import src.trading.kill_switch as kill_switch_mod

    monkeypatch.setattr(kill_switch_mod, "KillSwitchService", MagicMock())
    monkeypatch.setattr(kill_switch_mod, "CumulativeLossEvaluator", MagicMock())
    monkeypatch.setattr(kill_switch_mod, "DailyLossEvaluator", MagicMock())

    if positions is not None:
        # close 경로 — 거래소 flat 확인. provider 와 credential 조회를 대역으로 바꾼다.
        import src.trading.providers as providers_mod
        import src.trading.services.account_service as account_service_mod

        provider = SimpleNamespace(fetch_open_positions=AsyncMock(return_value=positions))
        monkeypatch.setattr(providers_mod, "BybitFuturesProvider", lambda *a, **k: provider)
        monkeypatch.setattr(
            account_service_mod,
            "ExchangeAccountService",
            lambda **k: SimpleNamespace(get_credentials_for_order=AsyncMock(return_value=object())),
        )

    return event_repo


class _NeverCalled:
    """`execute` 에 도달하면 안 되는 사이트용 — 도달하면 기록한다."""

    calls: ClassVar[list[int]] = []

    def __init__(self, **_: Any) -> None:
        pass

    async def execute(self, *_a: Any, **_k: Any) -> tuple[Any, bool]:
        from types import SimpleNamespace
        from uuid import uuid4

        _NeverCalled.calls.append(1)
        return (SimpleNamespace(id=uuid4(), state="pending", side=None), False)


@pytest.mark.asyncio
async def test_d1_session_inactive_still_returns_its_terminal_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D1 (`:3078`) — 비활성 세션 종결.

    도달 경로: 세션 비활성화 뒤 outbox 에 남은 event 를 `dispatch_pending` Beat(5분)이
    재발행하면 dispatch 시점엔 이미 inactive 다.

    postcondition: `{"failed": "session_inactive"}` 를 반환한다. 던지면 호출자가 이 종결을
    **일시 장애로 오분류해 재시도**한다 (H6).
    """
    from tests.tasks.test_live_signal_dispatch_task import _build_pending_event

    event = _build_pending_event()
    event_repo = _dispatch_harness(monkeypatch, event=event, is_active=False)
    calls: list[dict[str, str]] = []
    _explode_only(
        monkeypatch, qb_live_signal_dispatch_total, calls, action="entry", outcome="session_inactive"
    )

    result = await live_signal_module._async_dispatch_event(event.id)

    assert calls == [{"action": "entry", "outcome": "session_inactive"}], (
        "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    )
    assert result == {"failed": "session_inactive"}
    event_repo.commit.assert_awaited_once()  # 종결은 이미 내구화됐다


@pytest.mark.asyncio
async def test_d5_close_position_flat_still_returns_its_terminal_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D5 (`:3133`) — ★★★**거절이 집행으로 뒤집힌다** (사전등록 H6 을 반증, 신규 **H8**).

    도달 경로: close 이벤트 + 거래소 포지션 0건. BL-560 소크가 청산 시도의 46.2% 에서
    close mismatch 를 실측했다.

    ★**사전등록은 이 자리를 H6(종결이 재시도로 오분류)로 예측했고 틀렸다.** 다른 10곳과
    달리 이 계측만 **fail-open `try` 블록 안**에 있다(`:3125`~`:3142`). 계측이 던지면
    `except Exception` 이 그것을 「포지션 조회 실패」로 오인해 삼키고(로그
    `live_signal_close_position_check_failed_open`), `return` 을 건너뛴 채 **그대로 발주까지
    간다**. 실측 결과 = `{"dispatched": "<order_id>"}`.

    ⇒ 귀결은 오기록이 아니라 **원장 분기**다. `mark_failed("close_position_flat")` +
    `commit()` 이 이미 끝난 이벤트에 대해 **실주문이 나간다.** 「거래소가 flat 이라 청산을
    내지 않는다」는 이 분기의 존재 이유가 계측 한 줄에 뒤집힌다.

    postcondition: `{"failed": "close_position_flat"}` + reduce-only 거부 주문을 만들지 않는다.
    """
    from tests.tasks.test_live_signal_dispatch_task import _build_pending_event

    event = _build_pending_event()
    event.action = "close"
    _NeverCalled.calls = []
    _dispatch_harness(monkeypatch, event=event, order_service=_NeverCalled, positions=[])
    calls: list[dict[str, str]] = []
    _explode_only(
        monkeypatch,
        qb_live_signal_dispatch_total,
        calls,
        action="close",
        outcome="close_position_flat",
    )

    result = await live_signal_module._async_dispatch_event(event.id)

    assert calls == [{"action": "close", "outcome": "close_position_flat"}], (
        "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    )
    # ★가장 강한 위반을 먼저 본다 — 수리 전에는 여기서 red 다(주문이 실제로 나갔다).
    assert _NeverCalled.calls == [], "거래소가 flat 인데 청산 주문이 나갔다 (H8)"
    assert result == {"failed": "close_position_flat"}


@pytest.mark.asyncio
async def test_d6_trailing_only_entry_rejection_still_returns_its_terminal_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D6 (`:3180`) — ★**무방비 포지션 차단 가드**의 종결.

    도달 경로: trailing 만 선언하고 고정 SL 이 없는 Pine 전략의 entry.

    postcondition: `{"failed": "trailing_unsupported"}` + `execute` 미호출. 계측이 던지면
    이 거부가 일시 장애로 재분류돼 **같은 무방비 진입이 3회 재시도**된다 (H6).
    """
    from decimal import Decimal as _D

    from tests.tasks.test_live_signal_dispatch_task import _build_pending_event

    event = _build_pending_event(trailing_stop=_D("3.0"))  # stop_loss=None
    _NeverCalled.calls = []
    _dispatch_harness(monkeypatch, event=event, order_service=_NeverCalled)
    calls: list[dict[str, str]] = []
    _explode_only(
        monkeypatch, qb_live_signal_dispatch_total, calls, action="entry", outcome="rejected"
    )

    result = await live_signal_module._async_dispatch_event(event.id)

    assert calls == [{"action": "entry", "outcome": "rejected"}], (
        "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    )
    assert result == {"failed": "trailing_unsupported"}, "이 자리는 trailing 가드 분기다"
    assert _NeverCalled.calls == [], "무방비 진입을 막는 것이 이 분기의 존재 이유다"


@pytest.mark.asyncio
async def test_d7_invalid_order_request_still_returns_its_terminal_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D7 (`:3218`) — poison pill 차단(OrderRequest ValidationError) 종결.

    도달 경로: `OrderRequest.quantity = Field(gt=0, decimal_places=8)`. NUMERIC(18,8)
    round-trip 으로 exit 레벨이나 qty 가 0 으로 반올림되면 발생한다(코드 주석이 명시).

    postcondition: `{"failed": "invalid_order_request"}` + `execute` 미호출.
    """
    from decimal import Decimal as _D

    from tests.tasks.test_live_signal_dispatch_task import _build_pending_event

    event = _build_pending_event(take_profit=_D("0"))  # gt=0 위반
    _NeverCalled.calls = []
    _dispatch_harness(monkeypatch, event=event, order_service=_NeverCalled)
    calls: list[dict[str, str]] = []
    _explode_only(
        monkeypatch, qb_live_signal_dispatch_total, calls, action="entry", outcome="rejected"
    )

    result = await live_signal_module._async_dispatch_event(event.id)

    assert calls == [{"action": "entry", "outcome": "rejected"}], (
        "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    )
    assert result == {"failed": "invalid_order_request"}, "이 자리는 요청 검증 분기다"
    assert _NeverCalled.calls == [], "ValidationError 면 발주에 도달하지 않는다"


@pytest.mark.asyncio
async def test_d8_kill_switch_rejection_still_propagates_its_domain_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D8 (`:3235`) — ★**타입이 재시도 여부를 가른다** (H6 + H5).

    도달 경로: 누적손실/일일손실 한도 위반 → `KillSwitchActive`.

    이 자리의 계측은 `commit()` 과 `raise` **사이**에 있다. 던지면 `KillSwitchActive` 가
    아예 발생하지 않고 `OSError` 가 대신 탈출한다. 호출자는 결정론적 거절 5종만 무재시도로
    종결하므로(`:2793`), 「재시도해도 풀리지 않는다」고 코드가 적어 둔 거절이 재시도된다.

    postcondition: `KillSwitchActive` 가 **그대로** 올라온다.
    귀결의 두 번째 단계는 A-C2 오라클이 이미 고정한다 —
    `test_dispatch_task_retries_a_non_domain_error_but_not_a_domain_reject`.
    """
    from src.trading.exceptions import KillSwitchActive
    from tests.tasks.test_live_signal_dispatch_task import _build_pending_event

    class _OrderServiceKS:
        def __init__(self, **_: Any) -> None:
            pass

        async def execute(self, *_a: Any, **_k: Any) -> tuple[Any, bool]:
            raise KillSwitchActive("Kill Switch active for cumulative_loss")

    event = _build_pending_event()
    _dispatch_harness(monkeypatch, event=event, order_service=_OrderServiceKS)
    calls: list[dict[str, str]] = []
    _explode_only(
        monkeypatch, qb_live_signal_dispatch_total, calls, action="entry", outcome="kill_switched"
    )

    with pytest.raises(KillSwitchActive):
        await live_signal_module._async_dispatch_event(event.id)

    assert calls == [{"action": "entry", "outcome": "kill_switched"}], (
        "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    )


@pytest.mark.asyncio
async def test_d9_deterministic_reject_still_propagates_its_domain_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D9 (`:3247`) — 도메인 거절 4종의 공통 자리 (H6 + H5).

    도달 경로: min-notional 미달 / notional 초과 / leverage cap / 거래시간 밖.

    postcondition: `MinNotionalNotMet` 가 **그대로** 올라온다. D8 과 같은 형태이고
    `except` 절만 다르다.
    """
    from decimal import Decimal as _D

    from src.trading.exceptions import MinNotionalNotMet
    from tests.tasks.test_live_signal_dispatch_task import _build_pending_event

    class _OrderServiceReject:
        def __init__(self, **_: Any) -> None:
            pass

        async def execute(self, *_a: Any, **_k: Any) -> tuple[Any, bool]:
            raise MinNotionalNotMet(notional=_D("1"), min_notional=_D("5"))

    event = _build_pending_event()
    _dispatch_harness(monkeypatch, event=event, order_service=_OrderServiceReject)
    calls: list[dict[str, str]] = []
    _explode_only(
        monkeypatch, qb_live_signal_dispatch_total, calls, action="entry", outcome="rejected"
    )

    with pytest.raises(MinNotionalNotMet):
        await live_signal_module._async_dispatch_event(event.id)

    assert calls == [{"action": "entry", "outcome": "rejected"}], (
        "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    )


@pytest.mark.asyncio
async def test_d11_successful_dispatch_still_reports_the_order_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D11 (`:3261`) — ★**주문이 실제로 나간 뒤**의 계측.

    도달 경로: 정상 발주.

    이 자리에서 던지면 거래소에 주문이 나갔고 `mark_dispatched` + `commit` 까지 끝난
    상태에서 호출자는 **실패**를 본다. postcondition: 반환 dict 가 order_id 를 싣는다.
    """
    from types import SimpleNamespace
    from uuid import uuid4

    from tests.tasks.test_live_signal_dispatch_task import _build_pending_event

    order_id = uuid4()

    class _OrderServiceOk:
        def __init__(self, **_: Any) -> None:
            pass

        async def execute(self, req: Any, **_k: Any) -> tuple[Any, bool]:
            return (SimpleNamespace(id=order_id, state="pending", side=req.side), False)

    event = _build_pending_event()
    event_repo = _dispatch_harness(monkeypatch, event=event, order_service=_OrderServiceOk)
    calls: list[dict[str, str]] = []
    _explode_only(
        monkeypatch, qb_live_signal_dispatch_total, calls, action="entry", outcome="dispatched"
    )

    result = await live_signal_module._async_dispatch_event(event.id)

    assert calls == [{"action": "entry", "outcome": "dispatched"}], (
        "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    )
    assert result == {"dispatched": str(order_id), "replayed": False}
    event_repo.mark_dispatched.assert_awaited_once()  # 발주는 이미 내구화됐다


def test_d12_retry_exhaustion_still_returns_its_terminal_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D12 (`:2820`) — 호출자의 포기 기록.

    도달 경로: 일시 장애가 `max_retries=3` 까지 반복돼 소진된 뒤.

    이 계측은 **`except Exception` 핸들러 안**에 있다. 던지면 `{"failed":
    "max_retries_exhausted"}` 반환이 사라지고 `OSError` 가 태스크 밖으로 탈출한다 —
    이미 포기하기로 한 이벤트가 태스크 실패로 기록되고, 포기 사실은 어디에도 안 남는다.
    """
    from unittest.mock import Mock
    from uuid import uuid4

    from src.tasks import _worker_loop as worker_loop
    from src.tasks.live_signal import dispatch_live_signal_event_task as task

    def _run(coro: Any) -> Any:
        import contextlib

        with contextlib.suppress(Exception):
            coro.close()
        raise TimeoutError("broker unavailable")

    monkeypatch.setattr(worker_loop, "run_in_worker_loop", _run)
    retry = Mock(side_effect=AssertionError("소진 뒤에는 재시도하지 않는다"))
    monkeypatch.setattr(task, "retry", retry)
    calls: list[dict[str, str]] = []
    _explode_only(
        monkeypatch,
        qb_live_signal_dispatch_total,
        calls,
        action="unknown",
        outcome="max_retries_exhausted",
    )

    task.push_request(retries=3)
    try:
        result = task.run(str(uuid4()))
    finally:
        task.pop_request()

    assert calls == [{"action": "unknown", "outcome": "max_retries_exhausted"}], (
        "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    )
    assert result == {"failed": "max_retries_exhausted"}
    retry.assert_not_called()
