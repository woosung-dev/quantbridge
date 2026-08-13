"""L1 + L7 + L4 통합 POC (Day 8).

Pine 소스를 실제 파싱(L1 parser_adapter) → var 선언 추출(L7 ast_extractor) →
PersistentStore(L4 runtime) 등록 + bar-by-bar 시뮬레이션.

목적: Day 1-5 Foundation의 4개 레이어가 실제로 **조립 가능한지** 증명.
Week 2 full interpreter 이전의 최소 smoke test.

Pine 의미 재확인:
- `var x = 0` → 첫 bar에서 0으로 초기화, 이후 bar는 유지
- 재할당(`x := x + 1`)은 ReAssign 노드 → 현재 값에 덮어쓰기
- varip은 historical 백테스트에선 var와 동일 (차이는 realtime rollback에서만)

본 통합 POC는 "var 선언만" 처리. 재할당 해석은 Week 2+ 본격 interpreter 과제.
"""
from __future__ import annotations

from src.strategy.pine_v2.ast_extractor import extract_content
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore


def test_parse_then_register_var_declarations_into_store() -> None:
    """L1 → L7 → L4: `var` 선언을 파싱하여 PersistentStore에 등록 + 값 조회."""
    source = """//@version=5
indicator("integration_test")
var counter = 0
var name = "initial"
var pi = 3.14
"""
    # L1: 파싱
    tree = parse_to_ast(source)
    assert len(tree.body) == 4  # indicator + 3 var decls

    # L7: 구조 추출
    content = extract_content(source)
    assert content.declaration.kind == "indicator"
    assert len(content.var_declarations) == 3

    # L4: Store에 등록. 초기값은 interpreter가 평가할 자리지만 여기선
    # initial_expr 문자열을 해석해서 int/float/str로 변환 (smoke test 수준)
    store = PersistentStore()
    store.begin_bar()  # 첫 bar

    for decl in content.var_declarations:
        key = f"main::{decl.var_name}"
        # 단순 literal parsing (통합 테스트 수준 — 실제 interpreter는 AST 평가)
        raw = decl.initial_expr.strip()
        if raw.startswith("'") and raw.endswith("'"):
            value: int | float | str = raw[1:-1]
        elif "." in raw:
            value = float(raw)
        else:
            value = int(raw)
        store.declare_if_new(key, lambda v=value: v, varip=(decl.kind == "varip"))

    store.commit_bar()

    # 등록 확인
    assert store.get("main::counter") == 0
    assert store.get("main::name") == "initial"
    assert store.get("main::pi") == 3.14
    assert len(store) == 3


def test_persistent_store_detects_varip_via_ast_kind() -> None:
    """ast_extractor가 var/varip을 구분 → PersistentStore varip 플래그 전파 확인."""
    source = """//@version=5
indicator("varip_test")
var regular = 0
varip realtime_hi = 0
"""
    content = extract_content(source)
    var_kinds = {d.var_name: d.kind for d in content.var_declarations}
    assert var_kinds == {"regular": "var", "realtime_hi": "varip"}

    store = PersistentStore()
    store.begin_bar()
    for decl in content.var_declarations:
        store.declare_if_new(
            f"main::{decl.var_name}",
            lambda: 0,
            varip=(decl.kind == "varip"),
        )
    store.commit_bar()

    assert not store.is_varip("main::regular")
    assert store.is_varip("main::realtime_hi")


def test_multi_bar_simulation_with_extracted_var() -> None:
    """3 bar 시뮬레이션: Pine `var counter = 0` 을 파싱 + counter := counter + 1 패턴 재현.

    ReAssign 해석은 Week 2+이므로 여기선 인터프리터 역할을 테스트 내에서 수작업 수행.
    """
    source = """//@version=5
indicator("counter_test")
var counter = 0
"""
    content = extract_content(source)
    assert len(content.var_declarations) == 1

    store = PersistentStore()
    counter_key = "main::counter"

    # 3 bar 동안 counter를 매 bar 증가 — interpreter 역할 수작업
    counter_history: list[int] = []
    for _bar in range(3):
        store.begin_bar()
        store.declare_if_new(counter_key, lambda: 0)  # 첫 bar만 초기화
        cur = store.get(counter_key)
        store.set(counter_key, cur + 1)
        counter_history.append(store.get(counter_key))
        store.commit_bar()

    # 1, 2, 3 — var가 bar를 건너 지속됨을 확인
    assert counter_history == [1, 2, 3]


def test_parse_corpus_s1_pbr_through_layers() -> None:
    """corpus s1_pbr.pine을 L1→L7로 끝까지 통과 (smoke)."""
    from pathlib import Path
    source = (
        Path(__file__).parents[2] / "fixtures" / "pine_corpus_v2" / "s1_pbr.pine"
    ).read_text()

    tree = parse_to_ast(source)
    assert tree.body, "파싱 결과 비어있으면 안 됨"

    content = extract_content(source)
    assert content.declaration.kind == "strategy"
    assert content.declaration.title == "Pivot Reversal Strategy"
    assert len(content.strategy_calls) == 2

    # s1_pbr은 var 0개 — PersistentStore는 비어있을 것
    store = PersistentStore()
    store.begin_bar()
    for decl in content.var_declarations:
        store.declare_if_new(f"main::{decl.var_name}", lambda: None)
    store.commit_bar()
    assert len(store) == 0


def test_parse_corpus_i2_luxalgo_var_registers_nine() -> None:
    """corpus i2_luxalgo의 9개 var를 L7로 추출 → L4에 등록."""
    from pathlib import Path
    source = (
        Path(__file__).parents[2] / "fixtures" / "pine_corpus_v2" / "i2_luxalgo.pine"
    ).read_text()

    content = extract_content(source)
    assert len(content.var_declarations) == 9

    store = PersistentStore()
    store.begin_bar()
    for decl in content.var_declarations:
        # 초기값 평가는 Week 2 interpreter 과제 — 여기선 placeholder None
        store.declare_if_new(
            f"main::{decl.var_name}",
            lambda: None,
            varip=(decl.kind == "varip"),
        )
    store.commit_bar()

    assert len(store) == 9
    # upper / lower 등 핵심 변수 등록 확인
    assert "main::upper" in store
    assert "main::lower" in store
