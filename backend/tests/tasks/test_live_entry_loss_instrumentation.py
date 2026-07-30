# 침묵 유실 지점의 신규 계측과, 등재 counter 두 개가 함께 오른다는 항등식을 고정한다

"""BL-536 ④ + ③-c(a).

★신규 counter 두 개는 **「유실 건수」가 아니라 「평가 발화 횟수」**다. 그 계약 자체를
테스트로 고정한다 — 같은 미해결 leg 를 두 번 평가하면 값이 2 가 되어야 한다. 1 이 되면
누군가 dedup 을 넣은 것이고, 그러면 이 counter 는 "유실 건수" 를 참칭하기 시작한다.

★③-c(a) — `qb_live_conditional_placed_total{long+short}` 와
`qb_live_conditional_guard_total{conditional_placed}` 가 실측에서 126 vs 92 로 달랐다.
모순이 아니다. 두 줄은 인접해 있고 **무조건 함께** 오르지만 라벨 축이 다르다 —
`placed_total` 은 방향으로 쪼개 전량을 세고, guard 는 조건부/시장가 전환으로 쪼갠다.
따라서 성립하는 항등식은 `placed_total{long+short} == guard{conditional_placed} +
guard{market_converted}` 이고, 실측 차 34 는 시장가 전환분이다. 그 관계를 여기서 잠근다.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from types import SimpleNamespace

import pytest

import src.tasks.live_signal  # noqa: F401
from src.common.metrics import (
    qb_live_conditional_guard_total,
    qb_live_conditional_placed_total,
    qb_live_conditional_plan_drop_evaluations_total,
    qb_live_pending_order_skip_evaluations_total,
)
from src.strategy.pine_v2.event_loop import PendingOrderSnapshot
from tests.tasks.test_live_signal_conditional_reconcile import (
    _patch_reconcile,
    _reconcile,
    _result,
    _session,
)

live_signal_module = sys.modules["src.tasks.live_signal"]


def _counter(metric: object, **labels: str) -> object:
    return metric.labels(**labels)  # type: ignore[attr-defined]


def _value(metric: object, **labels: str) -> float:
    return _counter(metric, **labels)._value.get()  # type: ignore[attr-defined]


def _below_minimum_pending(trade_id: str = "PivRevLE") -> PendingOrderSnapshot:
    """거래소 눈금 미만 수량 — `below_exchange_minimum` 드롭을 내는 입력.

    ★영구 유실 사유다. 수량이 step 미만이면 그 전략은 이 계정에서 **영원히 한 주도 못
    낸다**. 지금까지 Prometheus 계측이 0 개였던 자리가 정확히 여기다.
    """
    return PendingOrderSnapshot(
        trade_id=trade_id,
        direction="long",
        target_position=Decimal("0.00029138"),
        entry_qty=Decimal("0.00029138"),
        stop_price=Decimal("100"),
        placed_bar=1,
        comment="entry",
    )


# --- ④-a 계획기 드롭 (M6) -------------------------------------------------------


@pytest.mark.asyncio
async def test_planner_drop_increments_the_new_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★M6 — `.inc()` 한 줄을 지우면 이 단언이 red 다."""
    session = _session()
    harness = _patch_reconcile(monkeypatch)
    before = _value(qb_live_conditional_plan_drop_evaluations_total, reason="below_exchange_minimum")

    await _reconcile(session, _result([_below_minimum_pending()]), harness)

    after = _value(qb_live_conditional_plan_drop_evaluations_total, reason="below_exchange_minimum")
    assert after == before + 1
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_planner_drop_counter_counts_evaluations_not_lost_intents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★계약 그 자체 — 같은 미해결 leg 를 두 번 평가하면 **2** 다.

    계획기는 순수 함수라 상태를 지우지 않는다. 그래서 이 값은 "유실 의도 N 개" 가 아니라
    "한 의도가 N 번 평가됐다" 는 뜻이고, 원장 분해와 절대 합산하면 안 된다. 누군가
    dedup 을 넣어 1 로 만들면 이 counter 는 `engine_only` 와 같은 유형으로 무효가 된다.
    """
    session = _session()
    before = _value(qb_live_conditional_plan_drop_evaluations_total, reason="below_exchange_minimum")

    for _ in range(2):
        harness = _patch_reconcile(monkeypatch)
        await _reconcile(session, _result([_below_minimum_pending()]), harness)

    after = _value(qb_live_conditional_plan_drop_evaluations_total, reason="below_exchange_minimum")
    assert after == before + 2, "중복 발화가 사라지면 이 counter 의 의미가 바뀐다"


@pytest.mark.asyncio
async def test_unknown_planner_drop_reason_falls_into_other(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """label cardinality 보호 — allowlist 밖 사유는 `other` 로 수렴한다."""
    session = _session()
    harness = _patch_reconcile(monkeypatch)
    plan = SimpleNamespace(
        to_cancel=(),
        to_place=(),
        divergences=({"trade_id": "x", "reason": "brand_new_reason_from_the_future"},),
    )
    monkeypatch.setattr(
        "src.trading.services.conditional_entry_planner.plan_reconcile",
        lambda **_kwargs: plan,
    )
    before = _value(qb_live_conditional_plan_drop_evaluations_total, reason="other")

    await _reconcile(session, _result([_below_minimum_pending()]), harness)

    assert _value(qb_live_conditional_plan_drop_evaluations_total, reason="other") == before + 1


# --- ④-b 엔진 pending skip ------------------------------------------------------


def test_pending_order_skip_counter_reads_the_engine_report() -> None:
    before = {
        reason: _value(qb_live_pending_order_skip_evaluations_total, reason=reason)
        for reason in ("session_disallowed", "invalid_leg", "below_api_precision", "other")
    }

    live_signal_module._count_pending_order_skips(
        {
            "pending_order_skips": [
                {"trade_id": "a", "reason": "session_disallowed", "invalid_fields": []},
                {"trade_id": "b", "reason": "invalid_leg", "invalid_fields": ["qty"]},
                {"trade_id": "c", "reason": "below_api_precision", "invalid_fields": ["qty"]},
                {"trade_id": "d", "reason": "something_new"},
                {"trade_id": "e"},
            ]
        }
    )

    for reason, delta in (
        ("session_disallowed", 1),
        ("invalid_leg", 1),
        ("below_api_precision", 1),
        ("other", 2),
    ):
        assert (
            _value(qb_live_pending_order_skip_evaluations_total, reason=reason)
            == before[reason] + delta
        ), reason


def test_pending_order_skip_counter_tolerates_missing_or_broken_reports() -> None:
    """계측이 라이브 평가를 죽이면 안 된다 — 형태가 틀린 report 는 조용히 지나간다."""
    for payload in (None, {}, {"pending_order_skips": None}, {"pending_order_skips": "x"}):
        live_signal_module._count_pending_order_skips(payload)


# --- ③-c (a) 등재 counter 항등식 -----------------------------------------------


@pytest.mark.asyncio
async def test_conditional_placement_increments_both_counters_together(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch)
    before_placed = _value(qb_live_conditional_placed_total, direction="long")
    before_guard = _value(qb_live_conditional_guard_total, outcome="conditional_placed")
    before_market = _value(qb_live_conditional_guard_total, outcome="market_converted")

    await _reconcile(
        session,
        _result(
            [
                PendingOrderSnapshot(
                    trade_id="PivRevLE",
                    direction="long",
                    target_position=Decimal("1"),
                    entry_qty=Decimal("1"),
                    stop_price=Decimal("100"),
                    placed_bar=1,
                    comment="entry",
                )
            ]
        ),
        harness,
    )

    harness.order_service.execute.assert_awaited_once()
    assert _value(qb_live_conditional_placed_total, direction="long") == before_placed + 1
    assert (
        _value(qb_live_conditional_guard_total, outcome="conditional_placed") == before_guard + 1
    )
    assert _value(qb_live_conditional_guard_total, outcome="market_converted") == before_market


@pytest.mark.asyncio
async def test_market_conversion_increments_placed_total_but_not_conditional_placed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★실측 126 vs 92 의 답 — 차이는 `market_converted` 다.

    `placed_total` 은 전량을 방향으로 쪼개 세고 guard 는 조건부/전환으로 쪼갠다.
    두 값이 다른 것이 정상이며, 성립하는 항등식은 아래 합계다.
    """
    session = _session()
    # 기준가가 트리거를 넘어서면 계획기가 시장가 전환을 지시한다.
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))
    before_placed = _value(qb_live_conditional_placed_total, direction="long")
    before_guard = _value(qb_live_conditional_guard_total, outcome="conditional_placed")
    before_market = _value(qb_live_conditional_guard_total, outcome="market_converted")

    await _reconcile(
        session,
        _result(
            [
                PendingOrderSnapshot(
                    trade_id="PivRevLE",
                    direction="long",
                    target_position=Decimal("1"),
                    entry_qty=Decimal("1"),
                    stop_price=Decimal("100"),
                    placed_bar=1,
                    comment="entry",
                )
            ]
        ),
        harness,
    )

    harness.order_service.execute.assert_awaited_once()
    placed_delta = _value(qb_live_conditional_placed_total, direction="long") - before_placed
    conditional_delta = (
        _value(qb_live_conditional_guard_total, outcome="conditional_placed") - before_guard
    )
    market_delta = (
        _value(qb_live_conditional_guard_total, outcome="market_converted") - before_market
    )

    assert (placed_delta, conditional_delta, market_delta) == (1, 0, 1)
    # ★이것이 성립하는 유일한 항등식이다.
    assert placed_delta == conditional_delta + market_delta


@pytest.mark.asyncio
async def test_failed_placement_increments_neither_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """등재가 실패하면 둘 다 안 오른다 — 항등식이 실패 경로에서도 유지된다."""
    from src.trading.exceptions import NotionalExceeded

    session = _session()
    harness = _patch_reconcile(
        monkeypatch,
        execute_error=NotionalExceeded(
            notional=Decimal("1000"),
            available=Decimal("10"),
            leverage=2,
            max_notional=Decimal("19"),
        ),
    )
    before_placed = _value(qb_live_conditional_placed_total, direction="long")
    before_guard = _value(qb_live_conditional_guard_total, outcome="conditional_placed")

    await _reconcile(
        session,
        _result(
            [
                PendingOrderSnapshot(
                    trade_id="PivRevLE",
                    direction="long",
                    target_position=Decimal("1"),
                    entry_qty=Decimal("1"),
                    stop_price=Decimal("100"),
                    placed_bar=1,
                    comment="entry",
                )
            ]
        ),
        harness,
    )

    assert _value(qb_live_conditional_placed_total, direction="long") == before_placed
    assert _value(qb_live_conditional_guard_total, outcome="conditional_placed") == before_guard


# --- ⑤ BL-543 확인만 (코드 수정 금지) -------------------------------------------


def test_engine_only_divergence_counter_still_warns_against_entry_loss_use() -> None:
    """BL-543 권장 접근 (b) 는 이미 착지해 있다. 이 테스트는 그 문장이 사라지지 않게 한다."""
    import inspect

    import src.common.metrics as metrics_module

    source = inspect.getsource(metrics_module)
    assert "이 값을 진입 유실의 측정치로" in source
    assert "쓰지 마라" in source


# --- R2-② 계측 예외가 머니-패스를 멈추지 않는다 -------------------------------


def test_counter_failure_never_escapes_to_the_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    """★이 호출은 `try_claim_bar` **뒤**, 단일 commit **앞**이다.

    여기서 던지면 광역 except 로 떨어져 **claim 이 rollback** 되고, 다음 tick 이 같은 bar 를
    다시 평가해 같은 예외를 다시 만든다 = **매-tick 크래시 루프**. 계측 실패가 머니-패스를
    멈추면 안 된다.

    ★`.labels()` 가 던지는 경우를 고른 이유 — multiprocess 모드에서 새 라벨 조합은 그
    시점에 mmap 파일을 늘린다(디스크 full · 권한 오류). `.inc()` 만 감싸면 절반만 막는다.
    """
    from src.common import metrics as metrics_module

    def _boom(**_labels: str) -> object:
        raise OSError("No space left on device")

    monkeypatch.setattr(
        metrics_module.qb_live_pending_order_skip_evaluations_total, "labels", _boom
    )
    failures = metrics_module.qb_metrics_mutation_failed_total
    before = failures._value.get()

    # 예외가 새어 나오면 이 호출 자체가 실패한다.
    live_signal_module._count_pending_order_skips(
        {"pending_order_skips": [{"trade_id": "a", "reason": "below_api_precision"}]}
    )

    assert failures._value.get() == before + 1, "삼키되 **조용히** 삼키지는 않는다"


def test_plan_drop_counter_failure_is_isolated_too(monkeypatch: pytest.MonkeyPatch) -> None:
    """신규 counter **양쪽 모두**에 적용됐는지 — 한쪽만 막으면 루프는 여전히 가능하다."""
    from src.common import metrics as metrics_module

    def _boom(**_labels: str) -> object:
        raise OSError("No space left on device")

    monkeypatch.setattr(
        metrics_module.qb_live_conditional_plan_drop_evaluations_total, "labels", _boom
    )
    failures = metrics_module.qb_metrics_mutation_failed_total
    before = failures._value.get()

    live_signal_module._count_safely(
        metrics_module.qb_live_conditional_plan_drop_evaluations_total, "below_exchange_minimum"
    )

    assert failures._value.get() == before + 1
