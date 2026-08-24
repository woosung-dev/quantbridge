"""`live_signal.py` 의 **예외 핸들러 가시성** 래칫.

## 왜 있나

2026-08-04 회차가 [BL-580] 계측 가드 12곳의 「감싸는 핸들러」를 판정하려고 870줄짜리
함수를 읽고도 **틀렸다** — `unrepresentable_key` 는 바깥 fail-open `except` 가 아니라
**안쪽 발주 `except`** 에 잡히는데 그걸 못 봤고, 기존 회귀 테스트가 그제서야 반증했다.
직전 회차도 8곳 중 1곳에서 같은 실수를 했다. **두 회차 연속 같은 병이다.**

뿌리는 판단력이 아니라 **모양**이었다: 한 함수가 845줄짜리 `try` 본문을 갖고 `try` 가
3겹으로 겹쳐 있으면, 어떤 자리가 어느 핸들러에 잡히는지 사람이 안정적으로 못 읽는다.

그래서 그 모양을 **문서가 아니라 게이트로** 고정한다. 이 파일이 지키는 것은 두 가지다.

1. 이번에 해체한 두 계열(리컨사일러 · 평가기)의 **모든 함수는 `try` 중첩이 1**이다.
   = 함수를 열면 그 안의 `try` 가 무엇을 잡는지 **다른 `try` 를 거치지 않고** 읽힌다.
2. 파일 전체의 `try` 본문 길이와 잔여 중첩은 **오늘 실측값이 천장**이다. 늘 수 없다.

★**정확값으로 동결한다** — 여유 있는 반올림은 래칫이 아니다. 줄이는 변경은 환영이지만
그때는 이 상수를 **함께 낮춰라**(그래야 다음 사람이 천장을 믿을 수 있다).
"""

from __future__ import annotations

import ast
from pathlib import Path

_SOURCE = Path(__file__).resolve().parents[2] / "src" / "tasks" / "live_signal.py"

# ── 이번 회차가 해체한 두 계열 — 여기 있는 함수는 `try` 중첩이 반드시 1이다 ──────────
_RECONCILER_FAMILY = (
    "_reconcile_conditional_entries",
    "_reconcile_conditional_entries_inner",
    "_probe_resting_order",
    "_reconcile_market_precision",
    "_cancel_planned_entry",
    "_build_conditional_order_request",
    "_gather_resting_entries",
    "_confirm_exchange_terminals",
    "_resolve_current_position",
    "_resolve_reference_price",
    "_count_plan_divergences",
    "_build_placement_order_service",
    "_market_conversion_breach_pct",
    "_place_planned_entry",
)
_EVALUATOR_FAMILY = (
    "_evaluate_session_inner",
    "_evaluate_session_with_engine",
    "_load_strategy_settings",
    "_probe_gap_resync_state",
    "_read_ledger_gap_seed",
    "_extract_pyramiding",
    "_run_live_or_deactivate",
    "_positions_are_aligned",
    "_next_equity_curve",
    "_fetch_evaluation_bars",
    "_block_on_coverage_preflight",
    "_block_on_equity_exhausted",
    "_block_on_runtime_divergence",
    "_block_on_gap_mismatch",
    "_block_on_direction_divergence",
)

# ── 아직 `try` 안에 `try` 가 있는 함수 — **2026-08-04 실측, 전부 이번 회차 범위 밖** ──
#   여기 있는 것은 「괜찮다」가 아니라 「아직 안 했다」다. 다음 해체의 대상 목록이다.
_NESTED_TRY_DEPTH: dict[str, int] = {
    "_async_sweep_conditional_entries": 4,
    "_async_dispatch_event": 2,
    "_async_evaluate_all": 2,
    "_async_evaluate_session": 2,
    "dispatch_live_signal_event_task": 2,
}

# ── `try` 본문 raw 줄 수 천장 — 실측 최대(`_async_dispatch_event`). 범위 밖이다. ──────
#   해체 전 이 값은 **845**(`_reconcile_conditional_entries`)였다.
_MAX_TRY_BODY_LINES = 225


def _tree() -> ast.Module:
    return ast.parse(_SOURCE.read_text(encoding="utf-8"))


def _try_shape() -> tuple[dict[str, int], dict[str, int], int]:
    """(함수별 최대 try 중첩, 함수별 최대 try 본문 줄수, 관측한 try 총 개수)."""
    tree = _tree()
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    def enclosing_function(node: ast.AST) -> ast.AST | None:
        current = parents.get(node)
        while current is not None:
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return current
            current = parents.get(current)
        return None

    depth: dict[str, int] = {}
    body: dict[str, int] = {}
    seen = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        seen += 1
        function = enclosing_function(node)
        name = (
            function.name
            if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
            else "<module>"
        )
        nesting, current = 1, parents.get(node)
        while current is not None and current is not function:
            if isinstance(current, ast.Try):
                nesting += 1
            current = parents.get(current)
        depth[name] = max(depth.get(name, 0), nesting)
        body[name] = max(body.get(name, 0), node.body[-1].end_lineno - node.body[0].lineno + 1)  # type: ignore[operator]
    return depth, body, seen


def test_every_declared_helper_actually_exists() -> None:
    """★공허화 방지 — 이름이 바뀌면 아래 두 테스트가 **검사할 대상 없이 통과**한다."""
    defined = {
        node.name
        for node in ast.walk(_tree())
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    missing = sorted(set(_RECONCILER_FAMILY + _EVALUATOR_FAMILY) - defined)
    assert not missing, (
        f"목록의 함수가 소스에 없다: {missing}. 이름을 바꿨다면 이 목록도 함께 갱신해라 — "
        "그러지 않으면 아래 테스트가 아무것도 검사하지 않는다."
    )


def test_the_split_families_have_no_nested_try() -> None:
    """해체한 두 계열은 `try` 안에 `try` 를 품지 않는다.

    이것이 이 회차의 산출물이다 — 함수를 열면 **무엇이 잡히는지 다 보인다**.
    """
    depth, _, _ = _try_shape()
    offenders = {
        name: depth[name]
        for name in _RECONCILER_FAMILY + _EVALUATOR_FAMILY
        if depth.get(name, 0) > 1
    }
    assert not offenders, (
        f"해체한 계열에 중첩 `try` 가 생겼다: {offenders}. "
        "중첩을 만들지 말고 안쪽 `try` + 그 핸들러 전부를 별도 함수로 빼라."
    )


def test_remaining_nested_try_functions_are_exactly_the_frozen_list() -> None:
    """잔여 중첩은 실측 목록과 **정확히** 같다 — 늘 수도, 조용히 줄 수도 없다.

    ★줄이는 변경은 환영이다. 그때는 `_NESTED_TRY_DEPTH` 를 **함께 낮춰라** —
    그래야 다음 사람이 이 목록을 「아직 안 한 것」의 정본으로 믿을 수 있다.
    """
    depth, _, _ = _try_shape()
    actual = {name: value for name, value in depth.items() if value > 1}
    assert actual == _NESTED_TRY_DEPTH, (
        f"잔여 중첩 목록이 달라졌다.\n  실측: {dict(sorted(actual.items()))}\n"
        f"  동결: {dict(sorted(_NESTED_TRY_DEPTH.items()))}"
    )


def test_no_try_body_exceeds_the_frozen_maximum() -> None:
    """`try` 본문 raw 줄 수 천장. 해체 전 845 → 지금 225.

    긴 `try` 본문이 바로 2026-08-04 오독의 조건이었다 — 845줄을 다 읽어야만
    「이 계상이 어느 핸들러에 잡히나」를 답할 수 있었다.
    """
    _, body, seen = _try_shape()
    assert seen >= 20, f"`try` 를 {seen}개만 찾았다 — 이 테스트가 stale 이다"
    too_long = {name: value for name, value in body.items() if value > _MAX_TRY_BODY_LINES}
    assert not too_long, (
        f"`try` 본문이 동결 천장 {_MAX_TRY_BODY_LINES} 줄을 넘었다: {too_long}. "
        "본문을 늘리지 말고 그 조각을 자기 핸들러와 함께 함수로 빼라."
    )
