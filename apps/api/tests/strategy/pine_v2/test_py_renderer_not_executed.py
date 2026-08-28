"""[ADR-042] **렌더러 출력이 어떤 실행 경로에도 배선되지 않는다** — 관례가 아니라 집행.

★이 레포에는 [ADR-003] 의 「`exec`/`eval` 절대 금지」를 재는 게이트가 **0건**이었다(2026-08-27 실측).
문서 규칙만 있고 코드 집행이 없으면 다음 사람이 「읽기 전용인데 한 번만 돌려 보자」를 할 수 있다.
`track_runner.py` 가 `_LIVE_ONLY_KWARGS` 를 런타임 raise 로 막으며 「경계를 관례가 아니라 집행으로
만든다」고 적은 선례를 따라, 여기서 **부재를 단언**한다.

★단언은 두 층이다.
 ⑴ **AST 층** — `src/` 안에 `exec`/`eval`/`compile`/`__import__` 호출이 없다.
 ⑵ **배선 층** — `py_renderer` 의 산출(`.code`)이 실행기로 흘러가는 호출부가 없다.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[3] / "src"
_PY_FILES = sorted(_SRC.rglob("*.py"))

# 동적 실행 함수. `getattr` 우회까지는 못 보지만 **직접 호출**은 전부 막는다.
_FORBIDDEN_CALLS = frozenset({"exec", "eval", "compile", "__import__"})

# Redis Lua 는 우리 프로세스에서 도는 파이썬이 아니다(`pool.eval(...)` = 서버측 스크립트).
# 이름이 같을 뿐이라 **속성 호출**은 애초에 안 세지만, 근거를 남긴다.
_ALLOWED_ATTRIBUTE_EVAL = {"redlock.py"}


def _forbidden_calls_in(path: pathlib.Path) -> list[tuple[str, int]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover - 파싱 불가는 별개 게이트의 일이다
        return []
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # 이름 호출만 본다 — `pool.eval(...)`(Redis Lua) 같은 속성 호출은 대상이 아니다.
        if isinstance(func, ast.Name) and func.id in _FORBIDDEN_CALLS:
            found.append((func.id, node.lineno))
    return found


def test_src_has_no_dynamic_execution_call():
    """★[ADR-003] 결정 1 의 코드 집행. 문서에만 있던 규칙을 여기서 잰다."""
    assert _PY_FILES, "src 스캔이 0파일 — 빈 입력이 초록으로 새는 자리다"

    violations = {
        str(p.relative_to(_SRC)): hits for p in _PY_FILES if (hits := _forbidden_calls_in(p))
    }
    assert violations == {}, f"동적 실행 호출이 생겼다: {violations}"


def test_the_guard_actually_detects_a_violation(tmp_path: pathlib.Path):
    """★음성 대조 — 위 초록이 「검사기가 죽어서」가 아님을 증명한다.

    이 대조가 없으면 `_forbidden_calls_in` 이 항상 빈 리스트를 돌려줘도 위 테스트는 통과한다.
    이 레포가 여러 번 밟은 「빈 입력이 초록으로」 패턴이다.
    """
    probe = tmp_path / "probe.py"
    probe.write_text("def f(src):\n    return exec(src)\n", encoding="utf-8")
    assert _forbidden_calls_in(probe) == [("exec", 2)]

    # 양성 대조의 짝 — 속성 호출은 세지 않는다(Redis Lua `pool.eval`).
    attr = tmp_path / "attr.py"
    attr.write_text("async def g(pool, s):\n    return await pool.eval(s)\n", encoding="utf-8")
    assert _forbidden_calls_in(attr) == []


def test_renderer_output_is_not_wired_into_any_execution_path():
    """★렌더러의 `.code` 를 실행기로 넘기는 호출부가 없다.

    `render_python(...)` 의 결과가 닿는 곳은 **응답 스키마뿐**이어야 한다.
    """
    importers = [
        p
        for p in _PY_FILES
        if "py_renderer" in p.read_text(encoding="utf-8") and p.name != "py_renderer.py"
    ]
    # 소비자가 0이면 이 테스트는 항진명제다 — 배선이 생겼는데 못 잡는 상태를 막는다.
    assert importers, "py_renderer 소비자가 0건 — 배선 후 이 단언을 되살려라"

    # ★부분 문자열로 재지 마라 — 첫 판에서 `re.compile(` 을 builtin `compile(` 로 오검했다.
    #   위 `_forbidden_calls_in` 은 **이름 호출만** 보므로 `re.compile`·`pool.eval` 을 안 센다.
    for path in importers:
        hits = _forbidden_calls_in(path)
        assert hits == [], f"{path.name}: 렌더러 소비자에 동적 실행 호출 {hits}"
        # 프로세스를 새로 띄우는 것도 실행이다.
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("subprocess"), (
                        f"{path.name}:{node.lineno} 가 subprocess 를 import 한다"
                    )
            if isinstance(node, ast.ImportFrom):
                assert (node.module or "") != "subprocess", (
                    f"{path.name}:{node.lineno} 가 subprocess 에서 import 한다"
                )


@pytest.mark.parametrize("name", sorted(_FORBIDDEN_CALLS))
def test_forbidden_names_are_not_imported_as_aliases(name: str):
    """`from builtins import exec as run` 류의 우회를 막는다."""
    for path in _PY_FILES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    assert alias.name != name, f"{path.name}:{node.lineno} 가 {name} 을 import 한다"
