# 라이브 태스크의 top-level import 폭발반경이 조용히 자라지 못하게 막는다

"""BL-536 R2 — `src.tasks.live_signal` import 폐포 래칫.

## 왜 이 감사가 필요한가

celery worker 는 `backend/src` 를 bind-mount 하고 **watchfiles** 로 문다. 그래서 편집
중간 상태가 그대로 worker 에 들어간다. 그때 무엇이 죽는지가 import 위치로 갈린다:

- **지연 import** (함수 안) — `pine_v2` 가 반쯤 저장된 순간에 도는 평가 **한 건**이 실패한다.
  fail-closed 비활성화 코드는 **여전히 돈다**.
- **top-level import** — `src.tasks.live_signal` **모듈 자체**가 import 에 실패한다.
  = **celery 태스크 미등록**. 비활성화 코드조차 안 돌고 beat 는 계속 큐에 쌓는다.

2026-07-27 에 이 파일에서 정확히 그 종류의 `NameError` 가 실제로 났다
(`docs/reference/gates-and-traps.md` §3).

## ★래칫이지 금지가 아니다 — 그 이유

"`live_signal` 의 top-level 이 `pine_v2` 에 **닿지 않는다**" 로 잠그고 싶겠지만
**그 단언은 `origin/main` 에서도 실패한다.** 실측으로 main 은 이미 6 개를 끌어온다
(`ast_extractor` · `coverage` · `strategy_state` 등이 top-level 이다). 그래서 이 테스트는
**선재 폐포를 동결하고 증가만 막는다.**

BL-536 R0 이 `conditional_entry_planner` 를 top-level 로 올렸을 때 실측 증가:

    pine_v2 모듈  6 -> 14   (event_loop · interpreter · stdlib · sizing · rendering ·
                             parser_adapter · runtime · runtime.persistent 가 새로 들어옴)
    src 모듈    29 -> 38

R2 가 두 방어로 되돌렸다 — 계획기의 `PendingOrderSnapshot` 을 `TYPE_CHECKING` 으로 내리고,
`parse_live_entry_key` import 를 쓰는 함수 안으로 옮겼다.

## 왜 AST 인가

실제로 import 해 보면 그 시점에 이미 모듈이 적재돼 있어 `sys.modules` 가 오염된다.
정적 분석이 "**이 파일을 처음 import 하면 무엇이 딸려 오는가**" 를 정확히 답한다.
선례: `tests/tasks/test_no_module_level_loop_bound_state.py` (같은 성격의 AST 감사).
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"

ENTRYPOINT = "src.tasks.live_signal"

# ★`origin/main` 실측 폐포. 이 집합을 **늘리려면** 위 docstring 의 위험을 읽고
#   왜 안전한지를 PR 에 적어라. 줄이는 것은 언제나 환영이다.
ALLOWED_PINE_V2_MODULES: frozenset[str] = frozenset(
    {
        "src.strategy.pine_v2._names",
        "src.strategy.pine_v2.ast_extractor",
        "src.strategy.pine_v2.coverage",
        "src.strategy.pine_v2.exit_orders",
        "src.strategy.pine_v2.leverage_model",
        "src.strategy.pine_v2.strategy_state",
    }
)

# ★특히 이것들은 **절대** 들어오면 안 된다. 인터프리터 본체이고, 편집 빈도가 가장 높으며,
#   백테스트·옵티마이저·스트레스 테스트가 같은 파일을 재실행한다.
FORBIDDEN_PINE_V2_MODULES: frozenset[str] = frozenset(
    {
        "src.strategy.pine_v2.event_loop",
        "src.strategy.pine_v2.interpreter",
        "src.strategy.pine_v2.stdlib",
    }
)


def _module_path(module: str) -> Path | None:
    relative = module.replace(".", "/")
    if relative.startswith("src/"):
        relative = relative[len("src/") :]
    for candidate in (SRC_ROOT / f"{relative}.py", SRC_ROOT / relative / "__init__.py"):
        if candidate.exists():
            return candidate
    return None


def _collect_runtime_imports(body: list[ast.stmt], found: set[str]) -> None:
    """★`FunctionDef`/`ClassDef` 안으로는 내려가지 않는다 — 그것이 지연 import 다."""
    for node in body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None and node.level == 0:
                found.add(node.module)
        elif isinstance(node, ast.If):
            # `if TYPE_CHECKING:` 블록은 런타임에 돌지 않는다.
            if "TYPE_CHECKING" in ast.unparse(node.test):
                continue
            _collect_runtime_imports(node.body, found)
            _collect_runtime_imports(node.orelse, found)
        elif isinstance(node, ast.Try):
            _collect_runtime_imports(node.body, found)
            _collect_runtime_imports(node.orelse, found)
            _collect_runtime_imports(node.finalbody, found)
            for handler in node.handlers:
                _collect_runtime_imports(handler.body, found)
        elif isinstance(node, (ast.With, ast.For, ast.While)):
            _collect_runtime_imports(node.body, found)


def _runtime_import_closure(entrypoint: str) -> set[str]:
    seen: set[str] = set()
    queue = [entrypoint]
    while queue:
        module = queue.pop()
        if module in seen or not module.startswith("src"):
            continue
        seen.add(module)
        path = _module_path(module)
        if path is None:
            continue
        found: set[str] = set()
        _collect_runtime_imports(ast.parse(path.read_text()).body, found)
        for imported in found:
            if imported.startswith("src") and imported not in seen:
                queue.append(imported)
    return seen


def test_live_signal_never_pulls_the_pine_interpreter_at_import_time() -> None:
    """★핵심 단언 — 인터프리터 본체가 top-level 폐포에 들어오면 red."""
    closure = _runtime_import_closure(ENTRYPOINT)
    intruders = sorted(closure & FORBIDDEN_PINE_V2_MODULES)
    assert not intruders, (
        f"{ENTRYPOINT} 의 top-level import 가 {intruders} 에 닿는다. "
        "그 파일의 편집 중간 상태가 celery 태스크 **미등록**을 만든다 — "
        "지연 import(함수 안) 로 내리거나 TYPE_CHECKING 으로 바꿔라."
    )


def test_pine_v2_import_surface_does_not_grow() -> None:
    """선재 폐포를 동결한다. **증가만** 막는다 — main 도 이미 6 개를 끌어오기 때문이다."""
    closure = _runtime_import_closure(ENTRYPOINT)
    reached = {module for module in closure if module.startswith("src.strategy.pine_v2")}
    added = sorted(reached - ALLOWED_PINE_V2_MODULES)
    assert not added, (
        f"pine_v2 top-level 폐포가 늘었다: {added}. "
        "의도한 것이면 ALLOWED_PINE_V2_MODULES 를 갱신하고 왜 안전한지 적어라."
    )


def test_the_audit_itself_has_teeth() -> None:
    """★계측기 자기검증 — 감사가 실제로 뭔가를 보고 있는지.

    폐포가 비어 있거나 진입점을 못 찾으면 위 두 단언은 **공짜로 통과**한다.
    이 레포의 실측 실패 유형이 정확히 그것이라 여기서 한 번 더 잰다.
    """
    closure = _runtime_import_closure(ENTRYPOINT)
    assert ENTRYPOINT in closure
    assert len(closure) > 20, f"폐포가 너무 작다({len(closure)}) — 경로 해석이 깨졌다"
    # main 이 실제로 끌어오는 것들이 보여야 감사가 살아 있는 것이다.
    assert "src.strategy.pine_v2.strategy_state" in closure
    assert "src.trading.models" in closure


def test_conditional_entry_planner_is_pure_of_the_interpreter() -> None:
    """계획기 자체도 런타임에 인터프리터를 끌지 않는다 (R2-① 의 근본 수리)."""
    closure = _runtime_import_closure("src.trading.services.conditional_entry_planner")
    assert not (closure & FORBIDDEN_PINE_V2_MODULES), (
        "계획기가 다시 event_loop 를 런타임 import 한다 — "
        "`PendingOrderSnapshot` 은 타입으로만 쓰므로 TYPE_CHECKING 이면 충분하다."
    )


def test_entry_completeness_module_is_pure_of_the_interpreter() -> None:
    """분해 모듈도 마찬가지 — 오프라인 CLI 가 인터프리터를 적재할 이유가 없다."""
    closure = _runtime_import_closure("src.trading.entry_completeness")
    assert not (closure & FORBIDDEN_PINE_V2_MODULES)
