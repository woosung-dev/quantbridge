"""Sprint 19 BL-084 — Module-level asyncio primitive 차단 audit.

Sprint 18 Option C 의 영속 `_WORKER_LOOP` 채택으로 module-level `asyncio.Semaphore
/Lock/Event/Queue` 객체가 stale loop binding 으로부터 안전해졌지만, **신규
PR 이 이런 패턴 추가 시 영속 loop 가정 위반 회귀 방어** 가 필요하다.

본 audit 은 `src/tasks/*.py` + `src/common/alert.py` + `src/common/redis_client.py`
의 module-level (top-level) Assign / AnnAssign 노드에서 `asyncio.<class>()` 호출
검출. allowlist 외 신규 발견 시 fail.

`async def` 함수 안의 local `asyncio.Event()` 등은 매치 안 함 (loop-bound 안전).
호출자: PR 리뷰 + nightly CI.

codex G.0 P2 (Sprint 19): `ast.AnnAssign` + import alias (`from asyncio import
Semaphore as S`) 까지 detect.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# Sprint 19 BL-084 — 현재 알려진 안전 instance allowlist.
# 추가 시 PR 리뷰 + 본 allowlist 갱신 + Sprint 18 backend.md §11.2 의 안전 사유 명시.
_ALLOWLIST: set[tuple[str, str]] = {
    # _SEND_SEMAPHORE: Slack send burst 상한. Sprint 18 _WORKER_LOOP 통일로
    # 모든 acquire 가 동일 loop. 안전.
    ("src.common.alert", "_SEND_SEMAPHORE"),
}

# 검사 대상 — 신규 prefork-safe 모듈 추가 시 본 list 보강.
_TARGET_FILES: list[tuple[str, Path]] = []


def _backend_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _populate_targets() -> list[tuple[str, Path]]:
    if _TARGET_FILES:
        return _TARGET_FILES
    root = _backend_root()
    targets: list[tuple[str, Path]] = []
    # src/tasks/*.py
    for path in sorted((root / "src" / "tasks").glob("*.py")):
        if path.name == "__init__.py":
            continue
        module = f"src.tasks.{path.stem}"
        targets.append((module, path))
    # src/common/alert.py + src/common/redis_client.py
    for name in ("alert.py", "redis_client.py"):
        path = root / "src" / "common" / name
        if path.exists():
            module = f"src.common.{path.stem}"
            targets.append((module, path))
    _TARGET_FILES.extend(targets)
    return _TARGET_FILES


_FORBIDDEN_CLASS_NAMES = {
    "Semaphore",
    "BoundedSemaphore",
    "Lock",
    "Event",
    "Queue",
    "Condition",
    "PriorityQueue",
    "LifoQueue",
}


def _collect_asyncio_aliases(tree: ast.Module) -> dict[str, str]:
    """import 분석 — module-level alias mapping.

    감지 패턴:
    - `import asyncio` → {"asyncio": "asyncio"}
    - `import asyncio as aio` → {"aio": "asyncio"}
    - `from asyncio import Semaphore` → {"Semaphore": "asyncio.Semaphore"}
    - `from asyncio import Semaphore as S` → {"S": "asyncio.Semaphore"}
    """
    aliases: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "asyncio":
                    aliases[alias.asname or alias.name] = "asyncio"
        elif isinstance(node, ast.ImportFrom) and node.module == "asyncio":
            for alias in node.names:
                local = alias.asname or alias.name
                aliases[local] = f"asyncio.{alias.name}"
    return aliases


def _resolve_call_to_asyncio_class(
    call: ast.Call, aliases: dict[str, str]
) -> str | None:
    """`Call` 노드가 asyncio.<forbidden> 호출인지 판단. 아니면 None.

    예시:
    - `asyncio.Semaphore(8)` → Attribute(value=Name("asyncio"), attr="Semaphore")
    - `Semaphore(8)` (after `from asyncio import Semaphore`) → Name("Semaphore")
    - `aio.Lock()` (after `import asyncio as aio`) → Attribute(value=Name("aio"), attr="Lock")
    """
    func = call.func
    if isinstance(func, ast.Attribute):
        if not isinstance(func.value, ast.Name):
            return None
        module_alias = aliases.get(func.value.id)
        if module_alias != "asyncio":
            return None
        if func.attr in _FORBIDDEN_CLASS_NAMES:
            return func.attr
    elif isinstance(func, ast.Name):
        # `from asyncio import Semaphore` → aliases["Semaphore"] = "asyncio.Semaphore"
        full = aliases.get(func.id)
        if full and full.startswith("asyncio.") and full.split(".", 1)[1] in _FORBIDDEN_CLASS_NAMES:
            return full.split(".", 1)[1]
    return None


def _scan_module_level_violations(
    module_name: str, source: str
) -> list[tuple[str, int, str]]:
    """Top-level Assign / AnnAssign 의 `value` 가 asyncio.<forbidden>(...) 인 경우 수집.

    반환: [(module, lineno, target_name), ...]
    """
    tree = ast.parse(source)
    aliases = _collect_asyncio_aliases(tree)

    violations: list[tuple[str, int, str]] = []
    for node in tree.body:
        targets: list[str] = []
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    targets.append(tgt.id)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                targets.append(node.target.id)
            value = node.value
        else:
            continue

        if value is None or not isinstance(value, ast.Call):
            continue
        forbidden_class = _resolve_call_to_asyncio_class(value, aliases)
        if forbidden_class is None:
            continue
        for target_name in targets:
            violations.append((module_name, node.lineno, target_name))
    return violations


def test_no_unallowed_module_level_asyncio_primitives() -> None:
    """**BL-084 회귀 방어** — 신규 module-level `asyncio.<Semaphore|Lock|Event|Queue>` 차단.

    위반 시: allowlist 에 의도적 추가 + backend.md §11.2 에 안전 사유 기재 + PR 리뷰.
    """
    findings: list[tuple[str, int, str]] = []
    for module_name, path in _populate_targets():
        source = path.read_text(encoding="utf-8")
        for module, lineno, name in _scan_module_level_violations(module_name, source):
            key = (module, name)
            if key in _ALLOWLIST:
                continue
            findings.append((module, lineno, name))

    assert not findings, (
        "Module-level asyncio primitive 신규 발견 — Option C 영속 _WORKER_LOOP 가정 "
        "위반 가능. allowlist 추가 또는 lazy factory 변환 권장.\n"
        "위반 목록:\n"
        + "\n".join(f"  {m}:{ln} `{name}`" for m, ln, name in findings)
    )


def test_audit_targets_cover_known_modules() -> None:
    """audit 대상에 핵심 모듈이 포함되는지 sanity check.

    `src/tasks/_worker_loop.py`, `src/tasks/orphan_scanner.py`, `src/common/alert.py`
    같은 핵심 모듈이 audit list 누락 시 audit 자체가 무효화됨.
    """
    targets = {module for module, _ in _populate_targets()}
    expected_subset = {
        "src.tasks._worker_loop",
        "src.tasks.orphan_scanner",
        "src.tasks.trading",
        "src.tasks.websocket_task",
        "src.tasks.celery_app",
        "src.common.alert",
        "src.common.redis_client",
    }
    missing = expected_subset - targets
    assert not missing, f"audit 대상 누락: {missing}"


def test_audit_detects_synthetic_violation() -> None:
    """**BL-084 self-test** — audit 가 의도적 위반 source 를 fail 시키는지 검증.

    `_scan_module_level_violations` 의 동작 방어. 실제 source 변경 없이 inline.
    """
    synthetic = """
import asyncio
from asyncio import Lock as AsyncLock

# Module-level violations — 본 audit 가 잡아야 함
_BAD_SEMAPHORE = asyncio.Semaphore(4)
_BAD_LOCK: asyncio.Lock = asyncio.Lock()
_BAD_EVENT = AsyncLock()  # alias-imported

# 안전한 패턴 — 매치되지 않아야 함
_OK_SET = set()  # 일반 자료구조

async def _factory() -> asyncio.Event:
    return asyncio.Event()  # function-local — top-level 아님
"""
    findings = _scan_module_level_violations("synthetic", synthetic)
    found_names = {name for _, _, name in findings}

    assert "_BAD_SEMAPHORE" in found_names, "Assign(Call(asyncio.Semaphore)) detect 실패"
    assert "_BAD_LOCK" in found_names, "AnnAssign(Call(asyncio.Lock)) detect 실패"
    assert "_BAD_EVENT" in found_names, "import alias (AsyncLock) detect 실패"
    assert "_OK_SET" not in found_names, "non-asyncio Call 잘못 매치"


@pytest.mark.parametrize(
    "module_name",
    ["src.common.alert"],  # allowlist 검증
)
def test_allowlisted_modules_have_documented_violations(module_name: str) -> None:
    """allowlist 에 등록된 module 은 실제로 module-level asyncio primitive 보유 — stale 방어.

    allowlist 갱신 후 module 코드에서 해당 객체 제거 시 allowlist 도 정리해야 함.
    """
    allowlisted = {name for mod, name in _ALLOWLIST if mod == module_name}
    if not allowlisted:
        pytest.skip(f"{module_name} 에 allowlist entry 없음")

    target_path = next(
        path for mod, path in _populate_targets() if mod == module_name
    )
    source = target_path.read_text(encoding="utf-8")
    actual = {name for _, _, name in _scan_module_level_violations(module_name, source)}

    stale = allowlisted - actual
    assert not stale, (
        f"allowlist 의 {module_name} 항목 {stale} 가 source 에 더 이상 없음. "
        "allowlist 정리 필요."
    )
