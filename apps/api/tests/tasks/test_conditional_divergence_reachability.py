"""BL-582 — `qb_live_conditional_divergence_total` series 의 **도달성**을 실행으로 판정한다.

★**이 파일이 메우는 seam.** `test_live_conditional_divergence_labels.py` 는 게이트 라인을
`_pending(...)` **손조립** 스냅샷으로 구동한다. 그래서 「게이트는 동작한다」는 증명하지만
「**엔진이 그 입력을 만들 수 있는가**」는 증명하지 않는다. BL-582 가 두 series 를
「구조적 도달 불가」로 적은 근거가 바로 그 미검증 구간이었다:

> `PendingOrderSnapshot.take_profit/stop_loss/trailing_stop` 이 **항상 `None`**

**그 문장은 거짓이다.** 아래 두 테스트는 손조립을 쓰지 않는다 — `run_live` 가 실제로 만든
스냅샷을 **그대로** reconcile 루프에 흘리고 counter 차분을 단언한다.

★올바른 서술은 BL-523 쪽이다 — 「**현재 코퍼스 미발현**」. 발현 조건은 세 가지가 동시에
성립할 때다: (a) 같은 `trade_id` 가 이미 `open_trades` 에 있고(재발행), (b) 그 id 에
`strategy.exit` 브래킷이 붙어 있고, (c) 재발행이 **반대 방향**이라 `to_place` 에 남는다.
(c) 가 없으면 계획기가 `quantity == 0` 에서 `continue` 한다
(`conditional_entry_planner.py:481`) — 게이트는 `to_place` 에만 있다.
"""

from __future__ import annotations

import ast
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

import src as src_module
import src.tasks.live_signal as live_signal_module
from src.common.metrics import qb_live_conditional_divergence_total
from src.strategy.pine_v2.event_loop import run_live
from tests.tasks.test_live_signal_conditional_reconcile import (
    _patch_reconcile,
    _position,
    _reconcile,
    _result,
    _session,
)

# 같은 id 를 **반대 방향**으로 재발행하면서 그 id 에 고정 브래킷을 걸어 둔 형태.
# 시드 코퍼스에는 없다(시드 `s1_pbr` 은 `strategy.exit` 이 0건) — 그래서 인라인이다.
_REVERSAL_SAME_ID_WITH_BRACKET = """//@version=5
strategy("reversal same id with bracket")
if bar_index == 0
    strategy.entry("PivRev", strategy.long, qty=8)
    strategy.exit("X", from_entry="PivRev", stop=64, limit=192)
if bar_index == 1
    strategy.entry("PivRev", strategy.short, qty=8, stop=32)
"""

# 위와 같되 고정 SL 없이 트레일링만. `trail_points` 를 창 밖으로 크게 둬서 이 창에서
# 트레일링이 **발동하지 않게** 한다 — 발동하면 포지션이 닫혀 재발행 자체가 사라진다.
_REVERSAL_SAME_ID_TRAILING_ONLY = """//@version=5
strategy("reversal same id trailing only")
if bar_index == 0
    strategy.entry("PivRev", strategy.long, qty=8)
    strategy.exit("X", from_entry="PivRev", trail_points=5000, trail_offset=100)
if bar_index == 1
    strategy.entry("PivRev", strategy.short, qty=8, stop=32)
"""


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    start = datetime(2026, 5, 1, tzinfo=UTC)
    return pd.DataFrame(
        {
            "timestamp": [start + timedelta(hours=index) for index in range(len(closes))],
            "open": [closes[0], *closes[:-1]],
            "high": [close * 1.01 for close in closes],
            "low": [close * 0.99 for close in closes],
            "close": closes,
            "volume": [100.0] * len(closes),
        }
    )


def _counter_value(reason: str) -> float:
    return float(
        qb_live_conditional_divergence_total.labels(event="guard_drop", reason=reason)._value.get()
    )


@pytest.mark.asyncio
async def test_engine_supplied_trailing_only_bracket_reaches_guard_drop(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`guard_drop/bracket_trailing_only` 는 **엔진 산출물로 도달 가능하다** (BL-582 반증).

    엔진이 `trailing_stop=100.0` · `stop_loss=None` 인 스냅샷을 실제로 만든다.
    ★손조립 금지 — `run_live` 결과를 그대로 흘린다.
    """
    engine = run_live(_REVERSAL_SAME_ID_TRAILING_ONLY, _ohlcv([100.0, 100.0]))

    pending = {order.trade_id: order for order in engine.pending_orders}
    assert set(pending) == {"PivRev"}, "엔진이 조건부 진입을 내지 않으면 이 테스트는 공허하다"
    assert pending["PivRev"].trailing_stop == Decimal("100"), (
        "BL-582 은 이 필드가 '항상 None' 이라고 적었다 — 엔진 실행이 그것을 반증한다"
    )
    assert pending["PivRev"].stop_loss is None, "고정 SL 이 있으면 이 게이트를 타지 않는다"

    session = _session()
    harness = _patch_reconcile(monkeypatch)
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)
    before = _counter_value("bracket_trailing_only")

    await _reconcile(session, _result(list(engine.pending_orders)), harness)

    assert _counter_value("bracket_trailing_only") == before + 1, (
        "엔진 산출물이 실제 reconcile 루프의 게이트를 통과해 counter 를 움직여야 한다"
    )
    assert any(
        record.message == "live_conditional_guard_drop"
        and getattr(record, "reason", None) == "bracket_trailing_only"
        for record in caplog.records
    )
    harness.order_service.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_engine_supplied_reversal_bracket_reaches_tp_size_guard_drop(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`guard_drop/bracket_tp_size_mismatch` 도 **엔진 산출물로 도달 가능하다** (BL-582 반증).

    ★손계산 오라클은 2의 거듭제곱이라 서로 구별된다 — 보유 `+8`, 목표 `-8` ⇒ 주문 수량
    `16`, 체결 후 포지션 `8`. `16 != 8` 이므로 tpSize 정합 게이트가 TP 만 떨어뜨린다.
    (`8`/`24`/`0` 어느 오답도 `16` 과 겹치지 않는다.)
    """
    engine = run_live(_REVERSAL_SAME_ID_WITH_BRACKET, _ohlcv([100.0, 100.0]))

    pending = {order.trade_id: order for order in engine.pending_orders}
    assert pending["PivRev"].take_profit == Decimal("192")
    assert pending["PivRev"].stop_loss == Decimal("64")
    assert pending["PivRev"].target_position == Decimal("-8")

    session = _session()
    harness = _patch_reconcile(monkeypatch, positions=[_position("long", Decimal("8"))])
    caplog.set_level(logging.WARNING, logger=live_signal_module.__name__)
    before = _counter_value("bracket_tp_size_mismatch")

    await _reconcile(session, _result(list(engine.pending_orders)), harness)

    assert _counter_value("bracket_tp_size_mismatch") == before + 1
    request = harness.order_service.execute.await_args.args[0]
    assert request.quantity == Decimal("16"), "반전 주문 수량 = |목표 − 보유|"
    assert request.take_profit is None, "tpSize 불일치라 TP 만 떨어진다"
    assert request.stop_loss == Decimal("64"), "SL 은 유지 — 보호를 통째로 잃지 않는다"


@pytest.mark.asyncio
async def test_same_direction_reissue_never_reaches_the_bracket_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★음성 대조 — **반대 방향**이 발현 조건임을 분리해 고정한다.

    같은 방향 재발행은 엔진이 브래킷을 그대로 싣지만(`take_profit=192`), 계획기가
    `quantity == 0` 에서 `continue` 하므로 `to_place` 에 남지 않는다. 이 테스트가 없으면
    위 두 테스트가 「브래킷만 있으면 발현한다」는 **틀린 결론**을 뒷받침하게 된다.
    """
    same_direction = _REVERSAL_SAME_ID_WITH_BRACKET.replace(
        'strategy.entry("PivRev", strategy.short, qty=8, stop=32)',
        'strategy.entry("PivRev", strategy.long, qty=8, stop=128)',
    )
    engine = run_live(same_direction, _ohlcv([100.0, 100.0]))
    pending = {order.trade_id: order for order in engine.pending_orders}
    assert pending["PivRev"].take_profit == Decimal("192"), "브래킷 자체는 실린다"
    assert pending["PivRev"].target_position == Decimal("8"), "보유분과 같은 목표"

    session = _session()
    harness = _patch_reconcile(monkeypatch, positions=[_position("long", Decimal("8"))])
    before_trailing = _counter_value("bracket_trailing_only")
    before_tp = _counter_value("bracket_tp_size_mismatch")

    await _reconcile(session, _result(list(engine.pending_orders)), harness)

    assert _counter_value("bracket_trailing_only") == before_trailing
    assert _counter_value("bracket_tp_size_mismatch") == before_tp
    harness.order_service.execute.assert_not_awaited()


# ---------------------------------------------------------------------------
# `other` 5종 — 구조 전제 게이트 (BL-582 의 나머지 절반)
# ---------------------------------------------------------------------------


def _resolve_reason_values(
    argument: ast.expr, function: ast.FunctionDef | ast.AsyncFunctionDef
) -> set[str | None] | None:
    """`_conditional_divergence_reason` 의 둘째 인자가 가질 수 있는 값 집합.

    ★**「리터럴만 허용」으로 쓰면 안 된다** (2026-08-02 codex G1 BLOCKING#4). 현 코드의
    `_conditional_divergence_reason("stand_down", stand_down_reason)` 은 둘째 인자가
    **변수**이고, 값은 앞에서 allowlist 값들의 중첩 `IfExp` 로 정해진다. 리터럴만 요구하면
    **옳은 코드가 red** 가 된다.

    그래서 bounded def-use 로 해소한다 — (a) 문자열/`None` 상수, (b) 그것들의 `IfExp`,
    (c) 같은 함수에서 (a)/(b) 로 **한 번만** 대입된 지역 변수. 셋 다 아니면
    `None`(= 해소 실패)을 돌려주고 **호출부가 그것을 red 로 처리**한다.
    해소 실패를 통과로 두면 조용한 구멍이 된다.

    ★`None` 은 값 집합의 원소로 **보존한다** — `_conditional_divergence_reason` 은
    `isinstance(raw, str)` 이 아니면 `other` 로 정규화하므로, `None` 이 도달하면
    `other` 가 발화한다. 그것을 막는 것은 호출부의 `is not None` 가드다(아래).
    """
    if isinstance(argument, ast.Constant):
        if isinstance(argument.value, str):
            return {argument.value}
        return {None} if argument.value is None else None
    if isinstance(argument, ast.IfExp):
        body = _resolve_reason_values(argument.body, function)
        orelse = _resolve_reason_values(argument.orelse, function)
        return None if body is None or orelse is None else body | orelse
    if isinstance(argument, ast.Name):
        assignments = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == argument.id
                for target in node.targets
            )
        ]
        if len(assignments) != 1:
            return None
        return _resolve_reason_values(assignments[0].value, function)
    return None


def _names_guarded_not_none(
    call: ast.Call, function: ast.FunctionDef | ast.AsyncFunctionDef
) -> set[str]:
    """`if <name> is not None:` 본문 안에서 호출됐다면 그 `<name>` 을 돌려준다.

    ★이것이 `stand_down_reason` 의 `None` 갈래를 배제하는 **유일한 근거**다
    (`live_signal.py` 의 `if stand_down_reason is not None:`). 가드를 지우면 `None` 이
    남고 이 오라클이 red 가 된다 — 그게 이 게이트가 지키려는 구조 전제다.
    """
    guarded: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.IsNot)
            and isinstance(test.left, ast.Name)
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value is None
        ):
            continue
        if any(
            statement.lineno <= call.lineno <= (statement.end_lineno or statement.lineno)
            for statement in node.body
        ):
            guarded.add(test.left.id)
    return guarded


def test_other_reason_is_unreachable_from_every_call_site() -> None:
    """`other` 5종이 **호출부에서** 도달 불가임을 def-use 로 증명한다.

    `_conditional_divergence_reason` 은 allowlist 밖 값을 `other` 로 정규화한다. 그 정규화가
    실제로 발화하려면 어떤 호출부가 allowlist 밖 값을 넘겨야 한다. 전 호출부의 가능값
    집합이 allowlist 부분집합이면 `other` 는 **닫힌 집합 가드로만 존재**한다.

    ★이 테스트는 「`other` 를 절대 만들지 마라」가 아니라 「만들려면 이 목록을 갱신해라」다.
    """
    live_signal_path = Path(src_module.__file__).parent / "tasks/live_signal.py"
    tree = ast.parse(live_signal_path.read_text(encoding="utf-8"))

    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    call_sites = 0
    problems: list[str] = []
    for function in functions:
        for node in ast.walk(function):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_conditional_divergence_reason"
                and len(node.args) == 2
            ):
                continue
            call_sites += 1
            event_node = node.args[0]
            if not (isinstance(event_node, ast.Constant) and isinstance(event_node.value, str)):
                problems.append(f":{node.lineno} event 축이 정적 문자열이 아니다")
                continue
            allowed = live_signal_module._CONDITIONAL_DIVERGENCE_REASONS.get(event_node.value)
            if allowed is None:
                problems.append(f":{node.lineno} 미지 event {event_node.value!r}")
                continue
            resolved = _resolve_reason_values(node.args[1], function)
            if resolved is None:
                problems.append(
                    f":{node.lineno} reason 을 해소하지 못했다 "
                    f"({ast.unparse(node.args[1])}) — 손으로 판정하고 이 오라클을 넓혀라"
                )
                continue
            values = set(resolved)
            if (
                None in values
                and isinstance(node.args[1], ast.Name)
                and node.args[1].id in _names_guarded_not_none(node, function)
            ):
                values.discard(None)
            if None in values:
                problems.append(
                    f":{node.lineno} `None` 이 도달 가능하다 — `other` 로 정규화된다. "
                    "`is not None` 가드를 두거나 이 자리를 재판정해라"
                )
                continue
            outside = values - set(allowed)
            if outside:
                problems.append(
                    f":{node.lineno} event={event_node.value} 가 allowlist 밖 {sorted(outside)} 을 넘긴다"
                )

    # ★공허화 방지 — 호출부가 0개면 위 루프가 아무것도 검사하지 않고 통과한다.
    assert call_sites >= 6, f"호출부가 {call_sites} 개다 — 오라클이 대상을 잃었다"
    assert not problems, "\n".join(problems)
