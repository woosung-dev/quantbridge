"""BL-576 — 조건부 reconcile 발화 이름과 계측 축이 사건을 섞지 않는지 검증한다."""

from __future__ import annotations

import ast
import logging
from collections import Counter
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import src as src_module
import src.tasks.live_signal as live_signal_module
from src.common.metrics import (
    qb_live_conditional_divergence_total,
    qb_live_conditional_plan_drop_evaluations_total,
)
from tests.tasks.test_live_signal_conditional_reconcile import (
    _order,
    _patch_reconcile,
    _pending,
    _position,
    _reconcile,
    _result,
    _session,
)

_SPLIT_EVENTS = {
    "live_conditional_exchange_divergence",
    "live_conditional_stand_down",
    "live_conditional_degraded_input",
    "live_conditional_plan_drop",
    "live_conditional_guard_drop",
    "live_conditional_market_converted",
}
_LEGACY_EVENT = "live_conditional_reconcile_divergence"

# 로그 이벤트명 → 새 counter 의 `event` 축. `plan_drop` 만 None 이다 —
# 계획기 드롭은 `qb_live_conditional_plan_drop_evaluations_total{reason}` 가 이미 세므로
# 새 counter 에 넣지 않았다(중복 계수 금지).
_COUNTER_EVENT: dict[str, str | None] = {
    "live_conditional_exchange_divergence": "exchange_divergence",
    "live_conditional_stand_down": "stand_down",
    "live_conditional_degraded_input": "degraded_input",
    "live_conditional_plan_drop": None,
    "live_conditional_guard_drop": "guard_drop",
    "live_conditional_market_converted": "market_converted",
}
# 로그 이벤트명 → 기대 로그 레벨. ★2026-08-02 codex LOW#9 — 오라클이 reason 만 보면
# 나중에 `error → warning` 강등이 조용히 통과한다.
_EVENT_LEVEL: dict[str, int] = dict.fromkeys(_COUNTER_EVENT, logging.WARNING)
_EVENT_LEVEL["live_conditional_stand_down"] = logging.ERROR

_baseline: dict[tuple[str, str], float] = {}


def _counter_value(event: str, reason: str) -> float:
    return float(
        # 테스트 전용 판독 — 프로덕션 코드는 `_count_safely` 만 쓴다(AST 오라클이 고정).
        qb_live_conditional_divergence_total.labels(event=event, reason=reason)._value.get()
    )


@pytest.fixture(autouse=True)
def _snapshot_divergence_counters() -> None:
    """테스트 시작 시점의 counter 값을 전건 기록한다.

    ★counter 는 프로세스 전역이라 절대값으로 단언할 수 없다. 각 테스트가 자기 창의
    **차분**만 보게 한다(직전 회차 교훈: 출생일 다른 counter 는 절대값 비교 불가).
    """
    _baseline.clear()
    for event, reasons in live_signal_module._CONDITIONAL_DIVERGENCE_REASONS.items():
        for reason in reasons:
            _baseline[(event, reason)] = _counter_value(event, reason)


def _assert_event_reason(caplog: pytest.LogCaptureFixture, *, event: str, reason: str) -> None:
    """발화 1건당 (이름 · reason · 레벨 · counter 차분) 네 축을 함께 고정한다.

    ★2026-08-02 codex MAJOR#6 — 이전 판은 로그만 봤다. 7개 counter 배선 중 한 조합
    (`guard_drop`/`breach_exceeds_cap`)만 값으로 검증되고 나머지는 **배선 여부조차
    확인되지 않았다.** 여기서 로그와 counter 를 같은 단언에 묶는다.
    """
    matches = [
        record
        for record in caplog.records
        if record.message == event and getattr(record, "reason", None) == reason
    ]
    assert matches, f"{event} / reason={reason} 발화가 없다"

    expected_level = _EVENT_LEVEL[event]
    bad = [r.levelname for r in matches if r.levelno != expected_level]
    assert not bad, f"{event} 로그 레벨이 바뀌었다: {bad} (기대 {expected_level})"

    counter_event = _COUNTER_EVENT[event]
    if counter_event is None:
        # plan_drop — 새 counter 에 없다. 있으면 그게 중복 계수다.
        assert (counter_event, reason) not in _baseline
        return

    before = _baseline[(counter_event, reason)]
    after = _counter_value(counter_event, reason)
    assert after == before + len(matches), (
        f"{counter_event}/{reason} counter 차분 {after - before} != 발화 {len(matches)}"
    )


def test_reconcile_divergence_log_sites_are_exactly_the_split_eight() -> None:
    """발화 8곳을 빠뜨리거나 새로 만들거나 옛 이름을 되돌리지 못하게 고정한다."""
    live_signal = Path(src_module.__file__).parent / "tasks/live_signal.py"
    tree = ast.parse(live_signal.read_text(encoding="utf-8"))

    emitted: list[str] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "logger"
            and node.func.attr in {"warning", "error"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            continue
        message = node.args[0].value
        if message == _LEGACY_EVENT or message in _SPLIT_EVENTS:
            emitted.append(message)

    assert _LEGACY_EVENT not in emitted
    assert Counter(emitted) == Counter(
        {
            "live_conditional_exchange_divergence": 1,
            "live_conditional_stand_down": 1,
            "live_conditional_degraded_input": 1,
            "live_conditional_plan_drop": 1,
            "live_conditional_guard_drop": 3,
            "live_conditional_market_converted": 1,
        }
    )
    direct_labels = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "labels"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "qb_live_conditional_divergence_total"
    ]
    assert not direct_labels, f"새 divergence counter는 _count_safely만 써야 한다: {direct_labels}"


@pytest.mark.asyncio
async def test_exchange_missing_resting_order_emits_exchange_divergence(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = _session()
    ghost = _order(session, exchange_order_id="exchange-ghost")
    harness = _patch_reconcile(
        monkeypatch, local_orders=[ghost], exchange_orders=[], probe_status="cancelled"
    )
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)

    await _reconcile(session, _result([_pending()]), harness)

    _assert_event_reason(
        caplog,
        event="live_conditional_exchange_divergence",
        reason="exchange_missing_resting_order",
    )


@pytest.mark.asyncio
async def test_hedge_mode_emits_stand_down(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = _session()
    harness = _patch_reconcile(
        monkeypatch,
        positions=[_position("long", Decimal("1")), _position("short", Decimal("1"))],
    )
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)

    await _reconcile(session, _result([_pending()]), harness)

    _assert_event_reason(caplog, event="live_conditional_stand_down", reason="hedge_mode")


@pytest.mark.asyncio
async def test_shared_account_symbol_emits_stand_down(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = _session()
    harness = _patch_reconcile(
        monkeypatch,
        active_sessions=[
            SimpleNamespace(
                id=object(),
                strategy_id=object(),
                exchange_account_id=session.exchange_account_id,
                symbol=session.symbol,
            )
        ],
    )
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)

    await _reconcile(session, _result([_pending()]), harness)

    _assert_event_reason(
        caplog,
        event="live_conditional_stand_down",
        reason="shared_account_symbol",
    )


@pytest.mark.asyncio
async def test_missing_reference_price_emits_degraded_input(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=None)
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)

    await _reconcile(
        session,
        _result([_pending()]),
        harness,
        fallback_reference_price=Decimal("99"),
    )

    _assert_event_reason(
        caplog,
        event="live_conditional_degraded_input",
        reason="reference_price_unavailable",
    )


@pytest.mark.asyncio
async def test_planner_breach_cap_emits_plan_drop(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)

    await _reconcile(
        session,
        _result([_pending()]),
        harness,
        max_trigger_breach_pct=1.0,
    )

    _assert_event_reason(
        caplog,
        event="live_conditional_plan_drop",
        reason="breach_exceeds_cap",
    )


@pytest.mark.asyncio
async def test_reprobe_breach_cap_emits_guard_drop(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("100.5"))
    harness.provider.fetch_last_price = AsyncMock(side_effect=[Decimal("100.5"), Decimal("102")])
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)

    await _reconcile(
        session,
        _result([_pending()]),
        harness,
        max_trigger_breach_pct=1.0,
    )

    _assert_event_reason(
        caplog,
        event="live_conditional_guard_drop",
        reason="breach_exceeds_cap",
    )


@pytest.mark.asyncio
async def test_trailing_only_bracket_emits_guard_drop(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch)
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)

    await _reconcile(session, _result([_pending(trailing_stop=Decimal("4"))]), harness)

    _assert_event_reason(
        caplog,
        event="live_conditional_guard_drop",
        reason="bracket_trailing_only",
    )


@pytest.mark.asyncio
async def test_tp_size_mismatch_emits_guard_drop(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, positions=[_position("long", Decimal("8"))])
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)

    await _reconcile(
        session,
        _result(
            [
                _pending(
                    direction="short",
                    target_position=Decimal("-8"),
                    stop_price=Decimal("32"),
                    take_profit=Decimal("16"),
                    stop_loss=Decimal("64"),
                )
            ]
        ),
        harness,
    )

    _assert_event_reason(
        caplog,
        event="live_conditional_guard_drop",
        reason="bracket_tp_size_mismatch",
    )


@pytest.mark.asyncio
async def test_market_conversion_emits_market_converted(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = _session()
    harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)

    await _reconcile(session, _result([_pending()]), harness)

    _assert_event_reason(
        caplog,
        event="live_conditional_market_converted",
        reason="market_converted",
    )


def test_divergence_counter_reason_is_event_scoped() -> None:
    expected: dict[str, frozenset[str]] = {
        "exchange_divergence": frozenset({"exchange_missing_resting_order"}),
        "stand_down": frozenset({"hedge_mode", "shared_account_symbol"}),
        "degraded_input": frozenset({"reference_price_unavailable"}),
        "guard_drop": frozenset(
            {"breach_exceeds_cap", "bracket_trailing_only", "bracket_tp_size_mismatch"}
        ),
        "market_converted": frozenset({"market_converted"}),
    }
    assert expected == live_signal_module._CONDITIONAL_DIVERGENCE_REASONS
    for event, reasons in expected.items():
        for reason in reasons:
            assert live_signal_module._conditional_divergence_reason(event, reason) == reason
        assert (
            live_signal_module._conditional_divergence_reason(event, "unbounded_reason") == "other"
        )

    # ★BL-576 — 여기가 `event` 축의 존재 이유다. 위 단언들은 정규화 함수가 **event 를 무시하고
    # 전체 합집합으로 걸러도 전부 통과한다** (2026-08-02 CONTROL 표적 변이 M2 가 그렇게 탈출했다).
    # 남의 event 의 reason 이 `other` 로 떨어지는지를 봐야 비로소 스코프를 고정한다.
    # 이 단언이 없으면 cardinality 상한 13 이 무너지고 `breach_exceeds_cap` 충돌 보호가 사라진다.
    for event, reasons in expected.items():
        foreign = set().union(*(r for e, r in expected.items() if e != event)) - reasons
        for reason in foreign:
            assert live_signal_module._conditional_divergence_reason(event, reason) == "other", (
                f"{reason!r} 은 {event!r} 의 reason 이 아닌데 통과했다 — event 축이 무력화됐다"
            )


@pytest.mark.asyncio
async def test_breach_cap_planner_and_guard_counters_stay_separate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """동일 reason도 계획기 평가 counter와 등재 가드 event series를 합치지 않는다."""
    planner = qb_live_conditional_plan_drop_evaluations_total.labels(reason="breach_exceeds_cap")
    guard = qb_live_conditional_divergence_total.labels(
        event="guard_drop", reason="breach_exceeds_cap"
    )
    planner_before = planner._value.get()
    guard_before = guard._value.get()

    planner_session = _session()
    planner_harness = _patch_reconcile(monkeypatch, last_price=Decimal("110"))
    await _reconcile(
        planner_session,
        _result([_pending()]),
        planner_harness,
        max_trigger_breach_pct=1.0,
    )

    assert planner._value.get() == planner_before + 1
    assert guard._value.get() == guard_before

    guard_session = _session()
    guard_harness = _patch_reconcile(monkeypatch, last_price=Decimal("100.5"))
    guard_harness.provider.fetch_last_price = AsyncMock(
        side_effect=[Decimal("100.5"), Decimal("102")]
    )
    await _reconcile(
        guard_session,
        _result([_pending()]),
        guard_harness,
        max_trigger_breach_pct=1.0,
    )

    assert planner._value.get() == planner_before + 1
    assert guard._value.get() == guard_before + 1
