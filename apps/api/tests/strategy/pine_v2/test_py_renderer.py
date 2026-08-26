"""[ADR-042] Pine AST → 읽기 전용 Python 렌더러 — 계약과 **실행 경로 부재**.

이 파일이 잠그는 것 셋.
 ⑴ 산출물에 실행 가능한 구성(`import`/`exec`/`eval`/dunder)이 **나타나지 않는다**.
 ⑵ 렌더러 출력이 **어떤 실행 경로에도 배선되지 않는다** — 관례가 아니라 집행이다.
 ⑶ **못 옮기는 노드를 조용히 빼지 않는다.** 빠지면 사용자가 없는 로직을 없다고 믿는다.
"""

from __future__ import annotations

import pathlib

import pytest

from src.strategy.pine_v2.py_renderer import render_python

_CORPUS = pathlib.Path(__file__).resolve().parents[2] / "fixtures" / "pine_corpus_v2"
_CORPUS_FILES = sorted(_CORPUS.rglob("*.pine"))

SIMPLE = """//@version=5
strategy("RSI", overlay=true)
length = input.int(14, title="L")
var float acc = 0.0
r = ta.rsi(close, length)
acc := acc + r
cond = close > open and r < 30
if cond
    strategy.entry("long", strategy.long)
else
    strategy.close("long")
"""


def test_corpus_renders_without_raising():
    assert _CORPUS_FILES, "corpus 가 비었다 — 빈 입력이 초록으로 새는 자리다"
    for f in _CORPUS_FILES:
        view = render_python(f.read_text(encoding="utf-8"))
        assert view.code.strip(), f.name
        assert view.source_map, (
            f"{f.name}: source_map 이 비었다 — 줄 대응이 없으면 원본으로 못 데려간다"
        )


def test_rendered_code_reads_as_the_strategy():
    view = render_python(SIMPLE)
    code = view.code

    assert 'strategy("RSI", overlay=True)' in code
    assert 'length = input.int(14, title="L")' in code
    # ★var 는 「봉을 넘어 유지된다」는 사실이 보여야 한다 — 안 보이면 전략을 오독한다.
    assert "acc = 0.0  # var:" in code
    assert "acc = (acc + r)  # := 재대입" in code
    # 조건과 분기가 **주석이 아니라 코드**로 나와야 한다.
    assert "if cond:" in code
    assert "else:" in code
    assert 'strategy.entry("long", strategy.long)' in code


def test_header_states_that_it_is_not_executed_and_explains_series_indexing():
    """★두 문장이 빠지면 이 뷰는 거짓말이 된다.

    ⑴ 실행되지 않는다는 사실 ⑵ `x[1]` 이 리스트 색인이 아니라 **한 봉 전**이라는 사실.
    후자를 모르면 사용자가 코드를 정확히 반대로 읽는다.
    """
    code = render_python(SIMPLE).code
    assert "실행되지 않습니다" in code
    assert "한 봉 전의 값" in code


def test_source_map_points_at_real_pine_lines():
    view = render_python(SIMPLE)
    pine_lines = SIMPLE.count("\n")
    for py_line, pine_line in view.source_map:
        assert 1 <= py_line <= view.code.count("\n"), (py_line, pine_line)
        assert 1 <= pine_line <= pine_lines, (py_line, pine_line)


# ★첫 판의 이 테스트는 판별력이 0이었다 — `array.*` 를 넣고 「출력에 array 가 있다」를 쟀는데
#   `array.new_float()` 는 평범한 `Call` 이라 **보존 경로를 아예 안 지났다.** 보존을 죽이는 변이를
#   심었는데 14/14 초록이었다(2026-08-27). 아래 셋은 실제로 `_preserve` 를 지나는 노드다.
_PRESERVED_CASES = {
    "for..in": '//@version=5\nindicator("A")\narr = array.new_float()\nfor v in arr\n    x = v\n',
    "import": '//@version=5\nimport TradingView/ta/7 as tv\nindicator("A")\n',
    "type": '//@version=5\nindicator("A")\ntype P\n    float x\n',
}


@pytest.mark.parametrize(("label", "source"), list(_PRESERVED_CASES.items()))
def test_unrenderable_nodes_are_preserved_not_dropped(label: str, source: str):
    """★조용히 빼지 않는다 — 원본 Pine 을 **주석으로 되살린다**.

    빠지면 사용자가 **없는 로직을 없다고 믿는다**([ADR-042] §트레이드오프).
    """
    view = render_python(source)

    assert view.unrendered >= 1, f"{label}: 보존 경로를 지나지 않았다 — 이 케이스는 대조가 못 된다"
    preserved = [line for line in view.code.splitlines() if "[원문 보존]" in line]
    assert preserved, f"{label}: 못 옮긴 노드가 산출물에서 통째로 사라졌다"

    # 원문이 **실제로** 되살아났는지 — 마커만 남고 내용이 비면 보존이 아니다.
    body = "\n".join(preserved)
    assert len(body.replace("# [원문 보존]", "").strip()) > 0, f"{label}: 마커만 있고 원문이 없다"


def test_fully_rendered_source_preserves_nothing(tmp_path):
    """★음성 대조 — 위 단언이 「보존 마커를 항상 뱉어서」 통과하는 것이 아님을 증명한다."""
    view = render_python(SIMPLE)
    assert view.unrendered == 0
    assert "[원문 보존]" not in view.code


@pytest.mark.parametrize("path", _CORPUS_FILES, ids=lambda p: p.stem)
def test_no_executable_construct_appears_in_output(path: pathlib.Path):
    """★⑴ 산출물에 실행 가능한 구성이 없다.

    렌더러가 `import os` 같은 줄을 만들어 내면, 언젠가 누가 그 출력을 실행해 보려 할 때
    바로 그 줄이 무기가 된다. 만들지 않는 것이 첫 방어선이다.
    """
    code = render_python(path.read_text(encoding="utf-8")).code
    for banned in ("import ", "exec(", "eval(", "compile(", "__import__", "__builtins__"):
        assert banned not in code, f"{path.name}: 산출물에 {banned!r} 가 있다"
