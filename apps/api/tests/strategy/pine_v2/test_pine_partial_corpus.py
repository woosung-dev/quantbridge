# Sprint 38 BL-188 v3 A2 — Pine corpus AST scan: partial default_qty declaration 0건 회귀 가드
"""corpus *.pine 의 strategy() 선언이 default_qty_type/value 양쪽 모두 명시 또는
모두 None 인지 검증. partial declaration 은 service helper 가 422 reject 대상이므로
corpus 자체에 partial 이 섞이면 회귀 검증 오염.

Sprint 38 = staged warning (이 테스트가 corpus 0건 보장).
Sprint 39+ = strict error (corpus 외부 사용자 입력 Pine 도 reject 강화 예정).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.strategy.pine_v2.ast_extractor import extract_content


def _collect_corpus_pine_paths() -> list[Path]:
    """tests/fixtures 하위 corpus *.pine 전부 수집."""
    base = Path(__file__).resolve().parents[2] / "fixtures"
    pine_paths: list[Path] = []
    for sub in ("pine_corpus_v2", "dogfood_corpus"):
        d = base / sub
        if not d.is_dir():
            continue
        pine_paths.extend(sorted(d.glob("*.pine")))
    return pine_paths


_CORPUS_PINE_PATHS = _collect_corpus_pine_paths()


@pytest.mark.parametrize(
    "pine_path",
    _CORPUS_PINE_PATHS,
    ids=[p.name for p in _CORPUS_PINE_PATHS],
)
def test_corpus_pine_no_partial_default_qty(pine_path: Path) -> None:
    """각 corpus *.pine 의 strategy() 선언에 partial default_qty 없음."""
    source = pine_path.read_text(encoding="utf-8")
    decl = extract_content(source).declaration
    if decl.kind != "strategy":
        # indicator() 는 default_qty 무관 — skip.
        return
    qt = decl.default_qty_type
    qv = decl.default_qty_value
    # XOR 검사 — 둘 다 명시 (truthy) 또는 둘 다 None.
    assert (qt is None) == (qv is None), (
        f"corpus partial default_qty declaration: {pine_path.name} "
        f"default_qty_type={qt!r}, default_qty_value={qv!r} — "
        f"둘 다 명시 또는 둘 다 None 의무 (BL-188 v3)."
    )


def test_corpus_collected_at_least_one_pine() -> None:
    """corpus 0건 collection 함정 방어 — 최소 1개 *.pine 발견."""
    assert len(_CORPUS_PINE_PATHS) >= 1, (
        "corpus *.pine 수집 0건 — fixtures 경로 변경 또는 path 함정 가능"
    )
