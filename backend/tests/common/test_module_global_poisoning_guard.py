"""BL-583 — 「테스트 대역이 프로덕션 모듈 전역에 남았는가」 가드의 판별력을 고정한다.

지키는 대상은 `tests/conftest.py` 의 가드 3부품이다 — 술어(`leaked_test_doubles`) ·
창(`leaked_test_doubles_since`) · 배선(`pytest_runtest_setup`/`_teardown` 훅). 셋 중 하나만
무력화돼도 순서 의존 오염이 **다시 조용해진다**: BL-583 의 red 는 무관한 파일 2개를 함께
수집할 때만 나타났고, 전체 스위트에서는 알파벳상 앞선 무관한 파일 6개가 문제 모듈을 미리
적재해 줘서 green 이었다.

★세 부품을 따로 시험하는 이유(codex G1 BLOCKING) — 술어만 시험하면 「스캔 범위를 없애는」
  변이가 어떤 테스트도 red 로 만들지 못하고, 순수 함수만 시험하면 훅이 아예 등록되지 않아도
  전부 green 이다.
★합성 모듈은 반드시 `sys.modules` 에서 제거한다. 안 하면 이 테스트 자신이 가드에 걸린다 —
  그 사실 자체가 창의 의미(한 항목 안에서 **처음** 적재된 `src.*` 모듈)를 증명한다.
"""

from __future__ import annotations

import os
import subprocess
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.conftest import leaked_test_doubles, leaked_test_doubles_since

_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_DIRTY = "src.__bl583_probe_dirty__"
_CLEAN = "src.__bl583_probe_clean__"
_LATE = "src.__bl583_probe_late__"


def _helper_defined_in_a_test_module() -> None:
    """하네스가 심는 것이 Mock 만이 아니라는 것을 재현하는 미끼."""
    return None


@pytest.fixture
def synthetic_modules() -> Iterator[tuple[types.ModuleType, types.ModuleType]]:
    dirty = types.ModuleType(_DIRTY)
    dirty.OrderRepository = MagicMock(return_value=AsyncMock())  # type: ignore[attr-defined]
    dirty.RETRY_LIMIT = 7  # type: ignore[attr-defined]
    clean = types.ModuleType(_CLEAN)
    clean.OrderRepository = object  # type: ignore[attr-defined]  # 진짜 클래스가 있어야 할 자리
    clean.RETRY_LIMIT = 7  # type: ignore[attr-defined]
    sys.modules[_DIRTY] = dirty
    sys.modules[_CLEAN] = clean
    try:
        yield dirty, clean
    finally:
        sys.modules.pop(_DIRTY, None)
        sys.modules.pop(_CLEAN, None)


def test_detects_mock_copied_into_module_globals(
    synthetic_modules: tuple[types.ModuleType, types.ModuleType],
) -> None:
    """MagicMock 이 프로덕션 모듈 전역에 남으면 `module.attr` 로 지목한다."""
    assert leaked_test_doubles([_DIRTY]) == [f"{_DIRTY}.OrderRepository"]


def test_detects_test_defined_callable_not_only_mocks(
    synthetic_modules: tuple[types.ModuleType, types.ModuleType],
) -> None:
    """★Mock 만 보면 놓친다 — 하네스는 `monkeypatch.setattr(..., lambda ...)` 도 쓴다."""
    _dirty, clean = synthetic_modules
    clean.leaked_lambda = lambda: None  # type: ignore[attr-defined]
    clean.leaked_helper = _helper_defined_in_a_test_module  # type: ignore[attr-defined]

    assert sorted(leaked_test_doubles([_CLEAN])) == [
        f"{_CLEAN}.leaked_helper",
        f"{_CLEAN}.leaked_lambda",
    ]


def test_clean_module_is_not_flagged(
    synthetic_modules: tuple[types.ModuleType, types.ModuleType],
) -> None:
    """음성 대조 — 「테스트 중 처음 적재됐다」만으로 실패시키면 모든 지연 import 를 오판한다."""
    assert leaked_test_doubles([_CLEAN]) == []


def test_unimported_module_name_is_ignored() -> None:
    """창 계산이 아직 안 적재된 이름을 넘겨도 술어는 던지지 않는다."""
    assert leaked_test_doubles(["src.__bl583_never_imported__"]) == []


def test_window_only_looks_at_the_src_namespace() -> None:
    """★`src.` 필터를 고정한다 — 없애면 테스트 모듈이 들고 있는 정당한 대역까지 오염으로 센다.

    (codex G6 MINOR — 이 필터를 제거해도 다른 6건은 전부 통과했다. 합성 모듈이 모두 `src.*`
    였기 때문이다. 그래서 **비-src 이름**으로 같은 오염을 만들어 「보지 않는다」를 못 박는다.)
    """
    foreign = "tests.__bl583_probe_foreign__"
    module = types.ModuleType(foreign)
    module.OrderRepository = MagicMock()  # type: ignore[attr-defined]
    modules_before = frozenset(sys.modules)
    sys.modules[foreign] = module
    try:
        assert leaked_test_doubles_since(modules_before) == []
        assert leaked_test_doubles([foreign]) == [f"{foreign}.OrderRepository"], (
            "술어 자체는 이름을 안 가린다 — 가리는 것은 창이다"
        )
    finally:
        sys.modules.pop(foreign, None)


def test_window_ignores_modules_loaded_before_the_snapshot(
    synthetic_modules: tuple[types.ModuleType, types.ModuleType],
) -> None:
    """창 축 — 스냅샷 **전**에 오염된 모듈은 이 항목의 책임이 아니다. 후에 들어온 것만 잡는다."""
    modules_before = frozenset(sys.modules)  # 합성 오염 모듈은 이미 여기 들어 있다
    assert leaked_test_doubles_since(modules_before) == []

    late = types.ModuleType(_LATE)
    late.OrderRepository = MagicMock()  # type: ignore[attr-defined]
    sys.modules[_LATE] = late
    try:
        assert leaked_test_doubles_since(modules_before) == [f"{_LATE}.OrderRepository"]
    finally:
        sys.modules.pop(_LATE, None)


@pytest.fixture(scope="module")
def child_session_output(tmp_path_factory: pytest.TempPathFactory) -> str:
    """가드 훅을 등록한 **자식 pytest 세션**을 1회 돌려 그 출력을 돌려준다.

    배선 축은 순수 함수로 증명할 수 없다 — 훅이 아예 등록되지 않아도 단위 테스트는 전부
    green 이기 때문이다(codex G1 BLOCKING). 자식 세션 conftest 가 **진짜 훅 함수를 import**
    하므로 pluggy 가 그것을 그대로 등록한다.

    자식 안에 항목을 둘 둔다:
      (a) 정상 teardown 에서 대역을 남긴다        → 가드가 그 항목을 teardown ERROR 로 만든다
      (b) teardown 이 터지는 동시에 대역을 남긴다 → 가드는 **원인 예외를 가리지 않고**
          `exc.add_note` 로 보고를 붙인다(pytest 가 원인 예외 바로 아래에 출력한다)

    `pytest_plugins = ["pytester"]` 를 쓰지 않는 이유: 그 선언은 rootdir conftest 에서만
    허용돼 이 파일(`tests/common/`)에 두면 하드 에러가 될 수 있다. 자식 프로세스를 직접
    띄우면 전역 설정을 건드리지 않고 같은 것을 증명한다.
    """
    path = tmp_path_factory.mktemp("bl583_child")
    (path / "conftest.py").write_text(
        "from tests.conftest import (  # noqa: F401\n"
        "    pytest_runtest_setup,\n"
        "    pytest_runtest_teardown,\n"
        ")\n",
        encoding="utf-8",
    )
    (path / "test_child.py").write_text(
        "import sys\n"
        "import types\n"
        "from unittest.mock import MagicMock\n"
        "\n"
        "import pytest\n"
        "\n"
        "\n"
        "def _leak(name):\n"
        "    module = types.ModuleType(name)\n"
        "    module.OrderRepository = MagicMock()\n"
        "    sys.modules[name] = module\n"
        "\n"
        "\n"
        "@pytest.fixture\n"
        "def exploding_teardown():\n"
        "    yield\n"
        '    raise RuntimeError("teardown boom")\n'
        "\n"
        "\n"
        "def test_leaks_a_double_into_a_freshly_imported_module():\n"
        '    _leak("src.__bl583_child_probe__")\n'
        "\n"
        "\n"
        "def test_leaks_a_double_while_its_teardown_explodes(exploding_teardown):\n"
        '    _leak("src.__bl583_child_probe_boom__")\n',
        encoding="utf-8",
    )

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(path)],
        cwd=path,
        # 상속된 PYTHONPATH 를 덮어쓰지 않는다 — 앞에 붙인다.
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                filter(None, [str(_BACKEND_ROOT), os.environ.get("PYTHONPATH", "")])
            ),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0, (
        f"자식 세션이 통과했다 — 가드가 발화하지 않았다:\n{completed.stdout}"
    )
    return completed.stdout


def test_guard_reports_the_leaking_test_as_a_teardown_error(child_session_output: str) -> None:
    """배선 축 — 순수 함수가 아니라 **보고**를 본다. 오염원 항목에 귀속돼야 한다."""
    # ★요약 줄을 통째로 문자열 비교하지 않는다 — 사이에 `N warnings` 가 끼어든다(실측).
    assert "2 passed" in child_session_output, child_session_output
    assert "2 errors" in child_session_output, child_session_output
    assert "ERROR at teardown of test_leaks_a_double_into_a_freshly_imported_module" in (
        child_session_output
    ), child_session_output
    assert "src.__bl583_child_probe__.OrderRepository" in child_session_output, child_session_output


def test_guard_does_not_mask_an_exploding_teardown(child_session_output: str) -> None:
    """★가드가 원인 예외를 덮지 않는다 — 덮으면 진짜 teardown 실패가 오염 보고에 묻힌다.

    pluggy 는 teardown 예외를 wrapper 의 `yield` 지점에 재발화하므로 post-yield 검사는
    통째로 건너뛰어진다(codex G1 MAJOR). 그래서 예외 경로에서도 스캔하되 `fail` 이 아니라
    **`exc.add_note`** 로 붙인다 — 이 테스트가 그 정책의 두 방향(원인 보존 + 보고 도달)을
    함께 고정한다.
    """
    assert "RuntimeError: teardown boom" in child_session_output, child_session_output
    assert "src.__bl583_child_probe_boom__.OrderRepository" in child_session_output, (
        child_session_output
    )
