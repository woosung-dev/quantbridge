"""Alert Hook 추출 + 메시지/조건 분류기 v1 회귀.

Day 6 스냅샷 `alert_hook_report.json`과 완전 일치해야 한다 (v1 schema:
enclosing_if_* / resolved_condition / message_signal / condition_signal /
signal / discrepancy 필드 추가).

v0 → v1 개선 자동 감지 요건:
- i3_drfx #2 message='BUY' + condition='bear' → **자동 discrepancy=True**
- condition_signal이 None(불가)인 경우 message_signal로 fallback
- alert inside `if cond`의 enclosing 컨텍스트 추적
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.strategy.pine_v2.alert_hook import (
    SignalKind,
    classify_message,
    collect_alerts,
)

_CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "pine_corpus_v2"
_REPORT: dict[str, list[dict]] = json.loads(
    (_CORPUS_DIR / "alert_hook_report.json").read_text()
)


@pytest.mark.parametrize("script_name", sorted(_REPORT.keys()))
def test_collect_alerts_matches_baseline(script_name: str) -> None:
    source = (_CORPUS_DIR / f"{script_name}.pine").read_text()
    actual = [h.to_dict() for h in collect_alerts(source)]
    expected = _REPORT[script_name]

    assert actual == expected, (
        f"{script_name}: alert 추출/분류 드리프트\n"
        f"  expected: {expected}\n"
        f"  actual:   {actual}"
    )


def test_total_alert_count_across_corpus() -> None:
    """ADR-011 §2.1 Alert Hook 사전 조사: Track A 3종에서 alert 총 10개."""
    total = sum(len(hooks) for hooks in _REPORT.values())
    assert total == 10


def test_classify_coverage_v1() -> None:
    """v1 커버리지: 10 alert 모두 final signal 결정 (unknown 0)."""
    unknown = 0
    for hooks in _REPORT.values():
        for h in hooks:
            if h["signal"] == SignalKind.UNKNOWN.value:
                unknown += 1
    assert unknown == 0


@pytest.mark.parametrize(("message", "expected"), [
    ("BUY", SignalKind.LONG_ENTRY),
    ("buy at market", SignalKind.LONG_ENTRY),
    ("SELL", SignalKind.SHORT_ENTRY),
    ("매수 진입", SignalKind.LONG_ENTRY),
    ("매도 청산", SignalKind.SHORT_EXIT),
    ("Close Long", SignalKind.LONG_EXIT),
    ("exit short now", SignalKind.SHORT_EXIT),
    ("Price broke the trendline", SignalKind.INFORMATION),
    ("pivot high detected", SignalKind.INFORMATION),
    ('{"action":"buy"}', SignalKind.LONG_ENTRY),
    ('{"action":"sell","size":1}', SignalKind.SHORT_ENTRY),
    ('{"action":"close_long"}', SignalKind.LONG_EXIT),
    ("", SignalKind.UNKNOWN),
    ("hello world", SignalKind.UNKNOWN),
])
def test_classify_message_keyword_rules(message: str, expected: SignalKind) -> None:
    assert classify_message(message) == expected


def test_information_takes_precedence_over_direction_keyword() -> None:
    """'Price broke the down-trendline upward'는 information (break/trendline 우선)."""
    assert classify_message("Price broke the down-trendline upward") == SignalKind.INFORMATION


# -------- v1 핵심: condition-trace 자동 감지 --------------------------


def test_i3_drfx_alert_2_auto_discrepancy_detection() -> None:
    """v1 핵심 가치: message='BUY' + condition=`bear` 불일치 **자동 감지**.

    v0에서는 수동 assertion만 있었고, v1은 condition_signal 분류 후
    message_signal 과 비교하여 discrepancy=True로 자동 플래그.
    최종 권고 signal은 condition 기반 우선 (short_entry).
    """
    drfx = _REPORT["i3_drfx"]
    alert_2 = next(h for h in drfx if h["index"] == 2)
    assert alert_2["message"] == "BUY"
    assert alert_2["condition_expr"] == "bear"
    assert alert_2["message_signal"] == SignalKind.LONG_ENTRY.value
    assert alert_2["condition_signal"] == SignalKind.SHORT_ENTRY.value
    assert alert_2["discrepancy"] is True, (
        "v1 condition-trace가 message-condition mismatch를 자동 플래그해야 함"
    )
    assert alert_2["signal"] == SignalKind.SHORT_ENTRY.value, (
        "최종 권고는 condition 우선 — BUY 메시지 오타/저자 실수 보호"
    )


def test_no_other_discrepancy_in_corpus() -> None:
    """i3_drfx #2 외에는 discrepancy 없어야 — 의도치 않은 false positive 방지."""
    discrepancies = [
        (name, h["index"])
        for name, hooks in _REPORT.items()
        for h in hooks
        if h["discrepancy"]
    ]
    assert discrepancies == [("i3_drfx", 2)], (
        f"기대 discrepancy 1건 (i3_drfx #2)만. 실측: {discrepancies}"
    )


def test_alertcondition_condition_expr_captured_for_all() -> None:
    """alertcondition은 arg0을 condition_expr에 항상 기록해야."""
    for name, hooks in _REPORT.items():
        for h in hooks:
            if h["kind"] == "alertcondition":
                assert h["condition_expr"] is not None, (
                    f"{name} #{h['index']} alertcondition인데 condition_expr 없음"
                )


def test_bare_alert_uses_enclosing_if_branch() -> None:
    """alert() (bare)는 감싸는 if 컨텍스트를 enclosing_if_* 필드로 기록해야."""
    drfx = _REPORT["i3_drfx"]
    bare_alerts = [h for h in drfx if h["kind"] == "alert"]
    assert len(bare_alerts) == 4, "i3_drfx에 bare alert은 4개 (#3,4,5,6)"
    for h in bare_alerts:
        assert h["enclosing_if_condition"] is not None, (
            f"bare alert #{h['index']}은 if 안에 있으므로 enclosing_if_condition 있어야"
        )
        assert h["enclosing_if_branch"] == "then", (
            "모든 bare alert은 THEN 분기 (ELSE 케이스는 corpus에 없음)"
        )


def test_resolved_condition_performs_variable_lookup() -> None:
    """i3_drfx #1 `bull` 변수가 resolved_condition에서 정의 expression으로 풀려야."""
    drfx = _REPORT["i3_drfx"]
    alert_1 = next(h for h in drfx if h["index"] == 1)
    assert alert_1["condition_expr"] == "bull"
    assert alert_1["resolved_condition"] is not None
    assert "ta.crossover" in alert_1["resolved_condition"], (
        "bull 변수는 ta.crossover 기반으로 정의되어야 함"
    )


def test_condition_signal_prioritizes_variable_name_over_resolved() -> None:
    """변수명 자체가 의미 있는 경우(bull/bear), 해석 결과보다 변수명 우선.

    i3_drfx #1: condition_expr='bull' → LONG_ENTRY (resolved=ta.crossover(...)도 동일 의도이나
    키워드 매칭 불가). 분류기는 원본 변수명을 먼저 시도해야 한다.
    """
    drfx = _REPORT["i3_drfx"]
    alert_1 = next(h for h in drfx if h["index"] == 1)
    assert alert_1["condition_signal"] == SignalKind.LONG_ENTRY.value, (
        "condition_expr='bull' → bull 키워드 매칭으로 long_entry"
    )


# --- Sprint 8b: condition_ast 필드 (Tier-1 bar 단위 재평가용) ---------


def test_collect_alerts_preserves_condition_ast_for_alertcondition() -> None:
    """AlertHook.condition_ast가 alertcondition arg0의 원본 AST 노드를 보존해야 함."""
    from pynescript import ast as pyne_ast

    source = (
        "//@version=5\n"
        "indicator('t', overlay=true)\n"
        "buy = close > open\n"
        "alertcondition(buy, 'Long', 'LONG')\n"
    )
    hooks = collect_alerts(source)
    assert len(hooks) == 1
    h = hooks[0]
    # condition_ast는 존재해야 하고 AST 노드(Name/Compare/BoolOp 등)
    assert h.condition_ast is not None
    assert isinstance(
        h.condition_ast, (pyne_ast.Name, pyne_ast.Compare, pyne_ast.BoolOp)
    )


def test_collect_alerts_preserves_enclosing_if_test_ast_for_alert() -> None:
    """alert() 호출의 경우 enclosing if의 test AST가 condition_ast에 보존."""
    from pynescript import ast as pyne_ast

    source = (
        "//@version=5\n"
        "indicator('t', overlay=true)\n"
        "if close > open\n"
        "    alert('LONG', alert.freq_once_per_bar)\n"
    )
    hooks = collect_alerts(source)
    assert len(hooks) == 1
    h = hooks[0]
    assert h.condition_ast is not None
    assert isinstance(h.condition_ast, pyne_ast.Compare)
