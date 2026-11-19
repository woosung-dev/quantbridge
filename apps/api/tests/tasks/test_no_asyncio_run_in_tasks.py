"""`src/tasks/` 는 `asyncio.run()` 을 직접 부르지 않는다 — `run_in_worker_loop()` 를 쓴다.

prefork worker 에서 task 마다 새 loop 를 만들면 2번째 task 부터 asyncpg 콜백이 죽은 loop 에
묶여 `RuntimeError("Future attached to a different loop")` 로 조용히 실패한다
(`src/tasks/_worker_loop.py` docstring).
"""

from __future__ import annotations

import ast
from pathlib import Path

_TASKS_DIR = Path(__file__).resolve().parents[2] / "src" / "tasks"

# (모듈, 감싸는 함수) — 늘리려면 그 코드가 왜 worker loop 밖에서 도는지 함께 적는다.
_ALLOWED: frozenset[tuple[str, str]] = frozenset(
    {
        # 영속 loop 가 없을 때(worker hook 미발화 — ad-hoc CLI)의 fallback 본체.
        ("_worker_loop", "run_in_worker_loop"),
        # `@worker_ready` 는 prefork 자식이 아니라 Celery master 에서 1회 돈다(함수 docstring).
        ("celery_app", "_on_worker_ready"),
    }
)


def _asyncio_run_names(tree: ast.Module) -> tuple[set[str], set[str]]:
    """`asyncio` 모듈의 별칭과, `from asyncio import run` 으로 들어온 이름을 모은다."""
    modules: set[str] = set()
    bare: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(a.asname or a.name for a in node.names if a.name == "asyncio")
        elif isinstance(node, ast.ImportFrom) and node.module == "asyncio":
            bare.update(a.asname or a.name for a in node.names if a.name == "run")
    return modules, bare


def _is_asyncio_run(call: ast.Call, modules: set[str], bare: set[str]) -> bool:
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr == "run":
        return isinstance(func.value, ast.Name) and func.value.id in modules
    return isinstance(func, ast.Name) and func.id in bare


def find_asyncio_run_calls(source: str) -> list[tuple[str, int]]:
    """`asyncio.run(...)` 호출을 (감싸는 최상위 함수 이름, 줄) 로 돌려준다."""
    tree = ast.parse(source)
    modules, bare = _asyncio_run_names(tree)
    found: list[tuple[str, int]] = []
    for top in tree.body:
        owner = (
            top.name
            if isinstance(top, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            else "<module>"
        )
        for node in ast.walk(top):
            if isinstance(node, ast.Call) and _is_asyncio_run(node, modules, bare):
                found.append((owner, node.lineno))
    return found


def test_detector_sees_every_call_shape() -> None:
    source = (
        "import asyncio\n"
        "import asyncio as aio\n"
        "from asyncio import run as go\n"
        "def a():\n    asyncio.run(x())\n"
        "def b():\n    aio.run(x())\n"
        "def c():\n    go(x())\n"
        "def d():\n    loop.run(x())\n"  # asyncio 가 아니다
        "asyncio.run(x())\n"
    )
    assert find_asyncio_run_calls(source) == [("a", 5), ("b", 7), ("c", 9), ("<module>", 12)]


def test_tasks_do_not_call_asyncio_run_outside_the_allowlist() -> None:
    files = sorted(_TASKS_DIR.glob("*.py"))
    assert len(files) > 10, "스캔 대상이 비면 초록이 무증거다"

    seen: set[tuple[str, str]] = set()
    offenders: list[str] = []
    for path in files:
        for owner, lineno in find_asyncio_run_calls(path.read_text(encoding="utf-8")):
            key = (path.stem, owner)
            seen.add(key)
            if key not in _ALLOWED:
                offenders.append(f"src/tasks/{path.name}:{lineno} ({owner})")

    assert not offenders, (
        "asyncio.run() 대신 `from src.tasks._worker_loop import run_in_worker_loop` 를 써라: "
        + ", ".join(offenders)
    )
    assert seen == _ALLOWED, f"allowlist 에 더는 없는 항목이 남아 있다: {sorted(_ALLOWED - seen)}"
