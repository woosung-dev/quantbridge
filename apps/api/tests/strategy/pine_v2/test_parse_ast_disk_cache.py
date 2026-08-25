"""AST 디스크 캐시(BL-832)의 계약을 고정한다 — 판정은 **초가 아니라 계수·동일성**이다.

콜드 파스는 실측상 2.7~53.4초라 시간으로 단언하면 머신이 바뀔 때 간헐 red 가 되고,
다음 사람이 가드를 끈다(n12 가 같은 이유로 절대 시간을 안 쟀다). 그래서 이 스위트는
**파스가 실제로 일어났는가**와 **왕복한 AST 가 같은가**만 본다.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from pynescript import ast as pyne_ast

from src.strategy.pine_v2 import parser_adapter
from src.strategy.pine_v2.ast_metrics import compute_edge_digest

_API_ROOT = Path(__file__).resolve().parents[3]
_SOURCE = '//@version=5\nindicator("x")\na = close > open\nplot(close)\n'
_OTHER_SOURCE = '//@version=5\nindicator("y")\nb = close < open\nplot(open)\n'


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """실제 캐시 디렉토리를 겨누지 않게 격리하고 L1 도 매번 비운다."""
    monkeypatch.setattr(parser_adapter.settings, "pine_ast_cache_dir", str(tmp_path), raising=False)
    parser_adapter.parse_to_ast.cache_clear()
    yield tmp_path
    parser_adapter.parse_to_ast.cache_clear()


def _count_parses(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """`pyne_ast.parse` 실호출을 센다 — L1/L2 를 다 통과한 것만 여기 쌓인다."""
    seen: list[str] = []
    real = pyne_ast.parse

    def counting(source: str, *args: object, **kwargs: object) -> object:
        seen.append(source)
        return real(source, *args, **kwargs)

    monkeypatch.setattr(parser_adapter.pyne_ast, "parse", counting)
    return seen


# ── AC ⑵ digest 동일성 ───────────────────────────────────────────────────
def test_cached_ast_has_identical_edge_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """캐시를 왕복한 AST 가 직파스와 구조적으로 같아야 한다."""
    direct = pyne_ast.parse(_SOURCE)
    parser_adapter.parse_to_ast(_SOURCE)  # 캐시 적재
    parser_adapter.parse_to_ast.cache_clear()  # L1 제거 → L2 에서 읽는다

    seen = _count_parses(monkeypatch)
    from_cache = parser_adapter.parse_to_ast(_SOURCE)

    assert seen == [], "L2 가 있는데 파스가 다시 일어났다"
    assert compute_edge_digest(from_cache) == compute_edge_digest(direct)
    assert pyne_ast.dump(from_cache) == pyne_ast.dump(direct)


# ── AC ⑴ 프로세스 밖에서도 1회 ───────────────────────────────────────────
def test_second_process_does_not_parse(_isolated_cache: Path) -> None:
    """★핵심 단언 — 새 프로세스가 같은 소스를 파싱할 때 `pyne_ast.parse` 를 안 부른다.

    두 번째 프로세스에서는 `pyne_ast.parse` 를 **던지게** 바꿔 둔다. 그래도 AST 가
    나오면 그것은 디스크에서 온 것이다. 시간을 재지 않는다.
    """
    warm = textwrap.dedent(f"""
        from src.strategy.pine_v2 import parser_adapter
        parser_adapter.settings.pine_ast_cache_dir = {str(_isolated_cache)!r}
        parser_adapter.parse_to_ast({_SOURCE!r})
        print("WARMED")
    """)
    cold = textwrap.dedent(f"""
        from src.strategy.pine_v2 import parser_adapter
        parser_adapter.settings.pine_ast_cache_dir = {str(_isolated_cache)!r}

        def boom(*a, **k):
            raise AssertionError("파스가 일어났다 — 캐시를 못 읽었다")

        parser_adapter.pyne_ast.parse = boom
        node = parser_adapter.parse_to_ast({_SOURCE!r})
        print("FROM_CACHE", type(node).__name__)
    """)

    first = _run_child(warm)
    assert "WARMED" in first.stdout, first.stderr

    second = _run_child(cold)
    assert second.returncode == 0, f"두 번째 프로세스가 죽었다:\n{second.stderr}"
    assert "FROM_CACHE" in second.stdout, second.stderr


def _run_child(code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=_API_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_child_without_cache_does_parse(_isolated_cache: Path) -> None:
    """★양성 대조 — 캐시가 비어 있으면 위 자식은 반드시 죽어야 한다.

    이 단언이 없으면 「파스를 안 했다」가 「경로가 아예 안 돌았다」와 구별되지 않는다.
    """
    cold = textwrap.dedent(f"""
        from src.strategy.pine_v2 import parser_adapter
        parser_adapter.settings.pine_ast_cache_dir = {str(_isolated_cache)!r}

        def boom(*a, **k):
            raise AssertionError("파스가 일어났다")

        parser_adapter.pyne_ast.parse = boom
        parser_adapter.parse_to_ast({_OTHER_SOURCE!r})
    """)
    result = _run_child(cold)
    assert result.returncode != 0, "캐시가 없는데 파스 없이 통과했다 — 경로가 안 돈다"
    assert "파스가 일어났다" in result.stderr


# ── AC ⑶ 소스 변경 → 미스 ────────────────────────────────────────────────
def test_changed_source_misses(monkeypatch: pytest.MonkeyPatch) -> None:
    parser_adapter.parse_to_ast(_SOURCE)
    parser_adapter.parse_to_ast.cache_clear()

    seen = _count_parses(monkeypatch)
    parser_adapter.parse_to_ast(_SOURCE + "// 한 줄 추가\n")

    assert len(seen) == 1, "소스가 바뀌었는데 캐시가 히트했다"


# ── AC ⑷ 버전 변경 → 미스 ────────────────────────────────────────────────
def test_version_bump_misses(monkeypatch: pytest.MonkeyPatch) -> None:
    """pynescript 업그레이드 후 낡은 AST 가 조용히 살아남으면 안 된다."""
    parser_adapter.parse_to_ast(_SOURCE)
    parser_adapter.parse_to_ast.cache_clear()

    monkeypatch.setattr(parser_adapter, "_pynescript_version", lambda: "99.99.99")
    seen = _count_parses(monkeypatch)
    parser_adapter.parse_to_ast(_SOURCE)

    assert len(seen) == 1, "버전이 바뀌었는데 옛 캐시를 읽었다"


def test_schema_version_participates_in_the_key() -> None:
    """스키마 버전도 키의 재료여야 한다 — 저장 구조를 바꿀 때의 탈출구다."""
    before = parser_adapter._cache_key(_SOURCE)
    original = parser_adapter._CACHE_SCHEMA_VERSION
    try:
        parser_adapter._CACHE_SCHEMA_VERSION = original + "x"
        assert parser_adapter._cache_key(_SOURCE) != before
    finally:
        parser_adapter._CACHE_SCHEMA_VERSION = original


# ── AC ⑸ 예외는 캐시되지 않는다 ──────────────────────────────────────────
def test_syntax_error_is_not_cached(monkeypatch: pytest.MonkeyPatch, _isolated_cache: Path) -> None:
    bad = '//@version=5\nindicator("x"\n  ['
    with pytest.raises(Exception):
        parser_adapter.parse_to_ast(bad)
    parser_adapter.parse_to_ast.cache_clear()

    assert list(_isolated_cache.glob("*.ast")) == [], "실패한 파스가 디스크에 남았다"

    seen = _count_parses(monkeypatch)
    with pytest.raises(Exception):
        parser_adapter.parse_to_ast(bad)
    assert len(seen) == 1, "실패가 캐시돼 재시도가 파스를 안 했다"


# ── 견고성: 캐시가 깨져도 파스를 못 막는다 ───────────────────────────────
def test_corrupt_cache_falls_back_to_parsing(_isolated_cache: Path) -> None:
    """반쯤 쓰인·깨진 파일이 요청을 죽이면 안 된다 — 동시 프로세스에서 실제로 생긴다."""
    parser_adapter.parse_to_ast(_SOURCE)
    parser_adapter.parse_to_ast.cache_clear()

    entries = list(_isolated_cache.glob("*.ast"))
    assert len(entries) == 1
    entries[0].write_bytes(b"not a pickle at all")

    node = parser_adapter.parse_to_ast(_SOURCE)
    assert node is not None
    assert compute_edge_digest(node) == compute_edge_digest(pyne_ast.parse(_SOURCE))


def test_disabled_cache_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, _isolated_cache: Path
) -> None:
    """빈 설정값은 비활성이다 — 끌 수 없는 캐시는 만들지 않는다."""
    monkeypatch.setattr(parser_adapter.settings, "pine_ast_cache_dir", "  ", raising=False)
    parser_adapter.parse_to_ast(_SOURCE)
    assert list(_isolated_cache.glob("*.ast")) == []


# ── 용량 상한 (BL-831 이 적은 임의 입력 표면 방어) ────────────────────────
def test_eviction_keeps_the_store_under_budget(
    monkeypatch: pytest.MonkeyPatch, _isolated_cache: Path
) -> None:
    """상한을 넘으면 오래된 것부터 지운다 — 디스크가 무한히 자라면 안 된다."""
    monkeypatch.setattr(parser_adapter.settings, "pine_ast_cache_max_bytes", 1, raising=False)
    for i in range(3):
        parser_adapter.parse_to_ast(f'//@version=5\nindicator("s{i}")\nplot(close)\n')
        parser_adapter.parse_to_ast.cache_clear()

    remaining = list(_isolated_cache.glob("*.ast"))
    assert len(remaining) <= 1, f"상한을 넘겼는데 {len(remaining)}건이 남았다"
