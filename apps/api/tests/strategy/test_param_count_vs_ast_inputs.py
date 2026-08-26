"""`_INPUT_RE` 기반 `param_count` 와 `extract_content().inputs` 는 **중복 구현이 아니다**.

두 수는 다른 것을 센다. 이 파일은 그 경계를 고정한다 — 다음 사람이 「이중 구현이니
AST 로 통일하자」고 판단하지 않게 하려는 것이다. 실제로 그 판단이 한 번 서면 두 가지가
동시에 깨진다:

⑴ **의미** — 정규식은 `input(` **호출 지점** 수, AST 는 **override 가능한** input 선언 수다.
   엔진은 대입문 좌변 이름으로만 값을 갈아끼우므로(`pine_v2/interpreter.py` 의
   `_assignment_target_stack`), 좌변이 없는 `input()` 은 Optimizer 가 건드릴 수 없다.
⑵ **비용** — `param_count` 는 목록 페이지의 **전 전략**에 대해 돈다. 콜드
   `extract_content` 는 실측(2026-08-27) corpus 9건 합계 **72초**이고 정규식은 5.7ms 다
   (12,700배). `parse_to_ast` 캐시가 비면 목록 API 가 그 값을 문다.

⇒ **목록은 정규식, 파라미터 표·Optimizer 드롭다운은 AST.**
"""

from __future__ import annotations

import pathlib

import pytest

from src.strategy.pine_v2.ast_extractor import extract_content
from src.strategy.service import _INPUT_RE, _strip_comments, _strip_string_literals

_CORPUS = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "pine_corpus_v2"


def _regex_count(source: str) -> int:
    return len(_INPUT_RE.findall(_strip_comments(_strip_string_literals(source))))


def _ast_count(source: str) -> int:
    return len(extract_content(source).inputs)


# ── 두 수가 **갈리는** 형태 — 전부 AST 가 적게 센다 ──────────────────────────
# (regex, ast) 로 고정한다. 값이 바뀌면 둘 중 하나의 의미가 바뀐 것이다.
DIVERGENT = {
    "대입 없는 input (렌더링 인자)": ("plot(close, linewidth=input.int(2))\n", 1, 0),
    "중첩 input": ("a = input.int(math.max(input.int(1), 2))\n", 2, 1),
    "사용자 함수 본문": ("f() => input.int(7)\na = f()\n", 1, 0),
    "튜플 좌변": ("[a, b] = ta.bb(close, input.int(20), 2.0)\n", 1, 0),
}

# ── 두 수가 **같아야** 하는 형태 (음성 대조) ─────────────────────────────────
# 여기가 갈리면 정규식이 주석·문자열·유사 식별자를 잘못 세고 있다는 뜻이다.
AGREEING = {
    "평범한 대입": "a = input.int(14)\nb = input.float(1.5)\n",
    "주석 안": "// a = input.int(99)\nb = input.int(1)\n",
    "문자열 안": 'a = input.string("input.int(0)")\n',
    "이름이 겹치는 식별자": "myinput(1)\nx_input(2)\na = input.bool(true)\n",
    "if 블록 안 대입": "if true\n    a = input.int(3)\n",
    "v4 무네임스페이스": 'a = input(14, title="len")\n',
}


@pytest.mark.parametrize(("label", "case"), list(DIVERGENT.items()))
def test_regex_and_ast_diverge_in_exactly_these_four_shapes(label, case):
    source, expected_regex, expected_ast = case
    assert _regex_count(source) == expected_regex, label
    assert _ast_count(source) == expected_ast, label
    # 방향까지 고정한다 — AST 가 더 많이 세는 일은 없어야 한다.
    assert _ast_count(source) < _regex_count(source), label


@pytest.mark.parametrize(("label", "source"), list(AGREEING.items()))
def test_regex_and_ast_agree_elsewhere(label, source):
    assert _regex_count(source) == _ast_count(source), label


def test_corpus_is_not_a_witness_for_the_divergence():
    """★corpus 전건 일치는 「두 구현이 같다」의 증거가 **아니다**.

    실측 2026-08-27 — corpus 9건은 9/9 일치한다. 위 4형태가 corpus 에 없을 뿐이고,
    그 초록만 보고 통일했으면 조용히 결함이 들어갔다. 이 테스트는 그 초록이
    **판별력이 없다는 사실 자체**를 고정한다.
    """
    files = sorted(_CORPUS.rglob("*.pine"))
    assert files, "corpus 가 비었다 — 빈 입력이 초록으로 새는 자리다"

    for f in files:
        source = f.read_text(encoding="utf-8")
        assert _regex_count(source) == _ast_count(source), f.name
