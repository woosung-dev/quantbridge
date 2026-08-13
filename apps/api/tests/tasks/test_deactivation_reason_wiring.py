"""세션을 죽이는 **모든** 경로가 등재된 사유를 넘기는지 소스에서 증명한다 (BL-484).

★왜 AST 스캔인가 — `tasks/live_signal.py` 의 6 갈래는 각각 celery worker + CCXT + Pine 재생을
태워야 도달하는 경로다(워크트리에서는 구조적으로 실행 불가). 경로별 무거운 하네스 6벌보다
"호출부가 사유를 넘기며 그 값이 정본 집합 안에 있다" 를 소스에서 래칫으로 고정하는 것이
정직하다. 같은 파일의 `test_conditional_entry_sweeper.py::
test_every_deactivation_site_enqueues_conditional_sweep` 가 이미 같은 방식으로 청소 요청을 고정한다.

★그리고 이 테스트가 `live_signal.py` 안의 사유 리터럴을 정본과 묶는 유일한 장치다 — 그 파일은
다른 워커 소유라 `SessionDeactivationReason` import 를 추가하지 않았고(소유 경계), 대신 여기서
값 집합을 검사한다. 새 사유를 쓰려면 `SessionDeactivationReason` 에 먼저 등재해야 한다.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import src
from src.trading.models import SessionDeactivationReason

_SRC_ROOT = Path(src.__file__).resolve().parent
_REASONS = {str(member) for member in SessionDeactivationReason}


def _session_deactivate_calls(tree: ast.AST) -> list[ast.Call]:
    """`repo.deactivate(..., at=...)` 호출만 고른다.

    `at=` 로 좁히는 이유 — `AlertRuleService` 도 `self._repo.deactivate(rule_id)` 를 쓰는데
    그건 알림 규칙이라 이 계약과 무관하다. `at` 은 세션 repo 시그니처의 필수 키워드다.
    """
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "deactivate"
        and any(kw.arg == "at" for kw in node.keywords)
    ]


def _string_literals_assigned_to(tree: ast.AST, name: str) -> tuple[set[str], list[int]]:
    """모듈 안에서 그 변수에 대입되는 **모든** 문자열 리터럴과, 리터럴이 아닌 대입의 행번호."""
    literals: set[str] = set()
    opaque: list[int] = []

    def _record(target: ast.expr, value: ast.expr) -> None:
        if not (isinstance(target, ast.Name) and target.id == name):
            return
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            literals.add(value.value)
        elif isinstance(value, ast.Constant) and value.value is None:
            # `preflight_cat: str | None = None` 같은 초기화 — 호출부는 None 을 걸러낸다.
            pass
        else:
            opaque.append(value.lineno)

    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            if node.value is not None:
                _record(node.target, node.value)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
                    for element, value in zip(target.elts, node.value.elts, strict=False):
                        _record(element, value)
                else:
                    _record(target, node.value)
    return literals, opaque


def _reason_values(tree: ast.AST, call: ast.Call) -> set[str]:
    """호출부가 넘기는 사유의 가능한 값 전부. 판정 불가면 빈 집합(= 실패)."""
    reason = next((kw.value for kw in call.keywords if kw.arg == "reason"), None)
    if reason is None:
        return set()
    if isinstance(reason, ast.Constant) and isinstance(reason.value, str):
        return {reason.value}
    if isinstance(reason, ast.Attribute) and isinstance(reason.value, ast.Name):
        if reason.value.id == "SessionDeactivationReason":
            member = getattr(SessionDeactivationReason, reason.attr, None)
            return {str(member)} if member is not None else set()
        return set()
    if isinstance(reason, ast.Name):
        literals, opaque = _string_literals_assigned_to(tree, reason.id)
        assert not opaque, (
            f"`reason={reason.id}` 에 리터럴 아닌 값이 대입된다({opaque} 행) — "
            "사유 집합을 소스에서 판정할 수 없다. 리터럴이나 "
            "SessionDeactivationReason 멤버를 써라."
        )
        assert literals, f"`reason={reason.id}` 에 대입되는 문자열 리터럴을 못 찾았다"
        return literals
    return set()


def _python_sources() -> list[Path]:
    return sorted(p for p in _SRC_ROOT.rglob("*.py") if "__pycache__" not in p.parts)


def test_every_session_deactivation_passes_a_registered_reason() -> None:
    """src 전체 — 세션을 죽이는 호출부가 전부 정본 집합의 사유를 넘긴다."""
    checked = 0
    for path in _python_sources():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for call in _session_deactivate_calls(tree):
            where = f"{path.relative_to(_SRC_ROOT)}:{call.lineno}"
            values = _reason_values(tree, call)
            assert values, f"{where} — `reason=` 이 없거나 소스에서 판정할 수 없다"
            unknown = values - _REASONS
            assert not unknown, (
                f"{where} — SessionDeactivationReason 에 없는 사유 {sorted(unknown)}. "
                "새 사유는 모델 enum 에 먼저 등재하고 FE 라벨도 함께 추가해라."
            )
            checked += 1

    # 래칫 — 호출부를 못 찾으면 이 테스트가 stale 이다(리팩터로 이름이 바뀐 경우).
    assert checked == 7, f"세션 비활성화 호출부 7곳을 기대했는데 {checked}곳을 찾았다"


def test_live_signal_preflight_categories_are_all_registered_reasons() -> None:
    """`preflight_cat` 에 들어가는 값 전부가 등재된 사유다 (미분류 preflight 경로 부재 증명).

    preflight 분류가 늘어나는 것은 정상이다 — 늘어날 때 사유 등재를 빼먹는 것이 사고다.
    """
    from src.tasks import live_signal

    tree = ast.parse(Path(live_signal.__file__).read_text(encoding="utf-8"))
    literals, opaque = _string_literals_assigned_to(tree, "preflight_cat")

    assert not opaque, f"preflight_cat 에 리터럴 아닌 대입({opaque} 행) — 사유 판정 불가"
    assert literals, "preflight_cat 대입을 못 찾았다 — 이 테스트가 stale 이다"
    assert literals <= _REASONS, (
        f"SessionDeactivationReason 에 없는 preflight 분류: {sorted(literals - _REASONS)}"
    )


@pytest.mark.parametrize("reason", list(SessionDeactivationReason))
def test_reason_values_fit_the_column(reason: SessionDeactivationReason) -> None:
    """마이그레이션이 준 String(64) 안에 들어간다 — 넘치면 DataError 로 종료가 실패한다."""
    assert len(str(reason)) <= 64
