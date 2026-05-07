"""SSOT parity invariant audit — Sprint 29 Slice C.

drift 차단 자동 감지:
- STDLIB_NAMES ⊆ SUPPORTED_FUNCTIONS (interpreter ta.* + na/nz 가 coverage 에 등록)
- _RENDERING_FACTORIES.keys() ⊆ SUPPORTED_FUNCTIONS (drawing 메서드가 coverage 에 등록)
- _V4_ALIASES.values() ⊆ SUPPORTED_FUNCTIONS (V4 alias target 이 coverage 에서 인식)
- interpreter._ATTR_CONSTANTS prefixes ⊆ coverage._ENUM_PREFIXES ∪ _CONST_VALUE_PREFIXES
  (enum prefix 이거나 사용자-friendly const value prefix)
"""

import ast
import inspect
from dataclasses import fields as dataclass_fields
from pathlib import Path

from src.strategy.pine_v2.coverage import (
    _ENUM_PREFIXES,
    _STRATEGY_CONSTANTS_EXTRA,
    SUPPORTED_FUNCTIONS,
)
from src.strategy.pine_v2.interpreter import (
    _ATTR_CONSTANTS,
    _RENDERING_FACTORIES,
    _V4_ALIASES,
    STDLIB_NAMES,
)

# _ATTR_CONSTANTS 안 const value (enum 이 아니라 사용자-friendly alias) prefix.
# 예: strategy.long="long" / line.style_dashed="dashed" — coverage._ENUM_PREFIXES
# 가 prefix lookup 으로 enum 만 인식. const value prefix 는 별도 화이트리스트.
_CONST_VALUE_PREFIXES = frozenset({"strategy.", "line."})


def test_stdlib_names_subset_of_supported_functions():
    """interpreter.STDLIB_NAMES (ta.* + na/nz) 가 모두 coverage.SUPPORTED_FUNCTIONS 에 등록."""
    diff = STDLIB_NAMES - SUPPORTED_FUNCTIONS
    assert not diff, f"STDLIB_NAMES not in SUPPORTED_FUNCTIONS: {sorted(diff)}"


def test_rendering_factories_subset_of_supported_functions():
    """interpreter._RENDERING_FACTORIES (line.*/box.*/label.*/table.*) 가 SUPPORTED_FUNCTIONS 에 등록."""
    diff = set(_RENDERING_FACTORIES.keys()) - SUPPORTED_FUNCTIONS
    assert not diff, f"_RENDERING_FACTORIES keys not in SUPPORTED_FUNCTIONS: {sorted(diff)}"


def test_v4_aliases_targets_in_supported_functions():
    """interpreter._V4_ALIASES (atr→ta.atr / max→math.max 등) 의 target 이 coverage.SUPPORTED_FUNCTIONS 에 등록.

    V4 alias 가 interpreter._eval_call 에서 dispatch 되려면 target 이 supported 의무.
    STDLIB_NAMES 가 ta.* + na/nz 만 포함하므로 (math.* 별도 dispatch), 더 넓은
    SUPPORTED_FUNCTIONS 로 검증.
    """
    diff = set(_V4_ALIASES.values()) - SUPPORTED_FUNCTIONS
    assert not diff, f"_V4_ALIASES targets not in SUPPORTED_FUNCTIONS: {sorted(diff)}"


# BL-185 Sprint 37 PR1 TDD-1.3: Pine strategy() default_qty_type 3 종 explicit 등록 검증.
# 이전 prefix-only 검증 (test_attr_constants_prefixes_known_to_coverage) 은 'strategy.' prefix
# 통과만으로 OK 판정 → strategy.fixed / cash / percent_of_equity 가 _ATTR_CONSTANTS 에 빠져도
# 통과하는 false-pass 가능. explicit 검증으로 drift 차단.
_BL185_DEFAULT_QTY_TYPES: frozenset[str] = frozenset(
    {
        "strategy.fixed",
        "strategy.cash",
        "strategy.percent_of_equity",
    }
)


def test_default_qty_type_constants_in_attr_constants():
    """BL-185: Pine strategy(default_qty_type=...) 3종이 interpreter._ATTR_CONSTANTS 에 명시 등록.

    interpreter 가 `strategy.percent_of_equity` 같은 attribute access 를 evaluate 할 때
    실제 string value 를 반환하려면 _ATTR_CONSTANTS dict 에 명시 매핑 필요.
    coverage._STRATEGY_CONSTANTS_EXTRA 에는 이미 등록되어 있으나, _ATTR_CONSTANTS (interpreter)
    에 등록되지 않으면 사용자 strategy 가 `t = strategy.percent_of_equity` 같이 변수에
    저장 후 사용 시 silent fail.
    """
    missing = _BL185_DEFAULT_QTY_TYPES - set(_ATTR_CONSTANTS.keys())
    assert not missing, (
        f"BL-185: _ATTR_CONSTANTS 에 default_qty_type 상수 누락: {sorted(missing)}. "
        "interpreter 가 attribute access 를 evaluate 못 함 → 사용자 strategy 의 "
        "`t = strategy.percent_of_equity` 패턴 silent fail."
    )


def test_default_qty_type_constants_subset_of_strategy_constants_extra():
    """BL-185: BL-185 default_qty_type 3종이 coverage._STRATEGY_CONSTANTS_EXTRA 에 명시 등록.

    coverage 가 `strategy.percent_of_equity` 등의 attribute access 를 SUPPORTED_ATTRIBUTES 로
    인식 못 하면 preflight (lazy validation) 가 false reject.
    """
    missing = _BL185_DEFAULT_QTY_TYPES - _STRATEGY_CONSTANTS_EXTRA
    assert not missing, (
        f"BL-185: coverage._STRATEGY_CONSTANTS_EXTRA 에 default_qty_type 누락: {sorted(missing)}"
    )


def test_attr_constants_prefixes_known_to_coverage():
    """interpreter._ATTR_CONSTANTS 의 dotted key prefix 가 coverage 에 인식.

    - enum prefix (extend./shape./location./size./position./color./...) ⊆ _ENUM_PREFIXES
    - const value prefix (strategy./line.) ⊆ _CONST_VALUE_PREFIXES (사용자-friendly alias)

    합집합에 없는 prefix 발견 시 drift — coverage 가 attribute access 를 인식 못 함.
    """
    attr_prefixes = {key.split(".", 1)[0] + "." for key in _ATTR_CONSTANTS}
    known_prefixes = set(_ENUM_PREFIXES) | _CONST_VALUE_PREFIXES
    diff = attr_prefixes - known_prefixes
    assert not diff, (
        f"_ATTR_CONSTANTS prefixes not in known prefixes: {sorted(diff)}. "
        f"_ENUM_PREFIXES={sorted(_ENUM_PREFIXES)}, _CONST_VALUE_PREFIXES={sorted(_CONST_VALUE_PREFIXES)}. "
        "neither enum 도 사용자-friendly const value prefix 도 아님 — drift."
    )


# ---------------------------------------------------------------------------
# Sprint 38 BL-188 v3 D — 통합 invariant 4종 (codex P2 #4: 신규 파일 폐기,
# 기존 audit 파일에 보강). 4 collection (compat / service / v2_adapter /
# virtual_strategy) 사이의 D2 chain priority + sessions_allowed 전파 정합성을
# 정적/구조적으로 검증해 silent drift 차단.
# ---------------------------------------------------------------------------

# D2 priority chain canonical source labels (`_canonical_dict(source=...)` 호출
# 인자). service.py 가 이 4종 외 source 를 emit 하면 BacktestConfig JSONB 에
# unknown sizing_source 가 저장되어 reporting / dogfood telemetry 깨짐.
_BL188_D2_SOURCES: frozenset[str] = frozenset({"pine", "form", "live", "fallback"})


def _scan_canonical_sources_from_service() -> set[str]:
    """`backend/src/backtest/service.py` 에서 `_canonical_dict(source="...")` 호출의 source 인자 set.

    AST 기반 정적 스캔 — runtime import 가 외부 의존 (DB/Celery) 을 끌어올 수
    있어 ssot audit 는 source 텍스트 파싱으로만 검증.
    """
    service_path = (
        Path(__file__).resolve().parents[3] / "src" / "backtest" / "service.py"
    )
    tree = ast.parse(service_path.read_text(encoding="utf-8"))
    sources: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_canonical = (
            isinstance(func, ast.Name) and func.id == "_canonical_dict"
        ) or (
            isinstance(func, ast.Attribute) and func.attr == "_canonical_dict"
        )
        if not is_canonical:
            continue
        for kw in node.keywords:
            if kw.arg != "source":
                continue
            if isinstance(kw.value, ast.Constant) and isinstance(
                kw.value.value, str
            ):
                sources.add(kw.value.value)
    return sources


def test_bl188_d2_chain_priority_4_collection_sync():
    """BL-188 v3: D2 priority chain (Pine > form > Live > fallback) 4 collection 정합.

    Invariant — 다음 4 곳이 모두 D2 chain 의 같은 의미 모델을 노출:
      1. service._resolve_sizing_canonical 가 _canonical_dict(source=...) 로
         emit 하는 source 종류 == {"pine", "form", "live", "fallback"}
      2. compat.parse_and_run_v2 시그니처에 D2 4 파라미터 모두 존재
         (live_position_size_pct / form_default_qty_type / form_default_qty_value /
         sessions_allowed)
      3. engine.types.BacktestConfig 가 live_position_size_pct 필드 보유
         (request → cfg JSONB persist)
      4. v2_adapter.adapt_run 소스가 cfg.live_position_size_pct 를
         parse_and_run_v2 호출 인자로 전파

    하나라도 깨지면 service 가 결정한 sizing canonical 이 runner 까지 도달 못
    하거나 unknown source 라벨이 DB 에 저장 → "Pine 우선" 보장 깨짐.
    """
    # 1. service.py emit 인자 set
    emitted = _scan_canonical_sources_from_service()
    missing = _BL188_D2_SOURCES - emitted
    extra = emitted - _BL188_D2_SOURCES
    assert not missing, (
        f"BL-188 v3 D2: service._resolve_sizing_canonical 에서 emit 안 된 "
        f"canonical source: {sorted(missing)}. 의미 매핑 누락 — DB JSONB 에 "
        f"sizing_source 가 fallback 으로만 흘러감."
    )
    assert not extra, (
        f"BL-188 v3 D2: service._canonical_dict 가 unknown source emit: "
        f"{sorted(extra)}. _BL188_D2_SOURCES 와 동기화 필요 — reporting/dogfood "
        f"telemetry 깨짐."
    )

    # 2. compat.parse_and_run_v2 시그니처
    from src.strategy.pine_v2.compat import parse_and_run_v2

    compat_params = set(inspect.signature(parse_and_run_v2).parameters)
    required_d2 = {
        "live_position_size_pct",
        "form_default_qty_type",
        "form_default_qty_value",
        "sessions_allowed",
    }
    diff = required_d2 - compat_params
    assert not diff, (
        f"BL-188 v3 D2: compat.parse_and_run_v2 시그니처에 D2 파라미터 누락: "
        f"{sorted(diff)}. v2_adapter → compat propagation 깨짐."
    )

    # 3. BacktestConfig.live_position_size_pct 필드 존재
    from src.backtest.engine.types import BacktestConfig

    cfg_fields = {f.name for f in dataclass_fields(BacktestConfig)}
    assert "live_position_size_pct" in cfg_fields, (
        "BL-188 v3 D2: BacktestConfig.live_position_size_pct 필드 누락. "
        "request canonical 이 cfg JSONB → adapter 로 전파 안 됨."
    )

    # 4. v2_adapter.adapt_run 소스가 cfg.live_position_size_pct 를 compat 으로 전달
    v2_adapter_path = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "backtest"
        / "engine"
        / "v2_adapter.py"
    )
    v2_src = v2_adapter_path.read_text(encoding="utf-8")
    assert "live_position_size_pct=cfg.live_position_size_pct" in v2_src, (
        "BL-188 v3 D2: v2_adapter.adapt_run 가 cfg.live_position_size_pct 를 "
        "compat.parse_and_run_v2 로 전달 안 함. priority chain Live tier 끊김."
    )


def test_bl188_sessions_allowed_propagation_4_layer_sync():
    """BL-188 v3: sessions_allowed 가 cfg.trading_sessions → 4 layer 동기 전파.

    cfg.trading_sessions → compat.parse_and_run_v2(sessions_allowed=...)
      → run_historical / run_virtual_strategy(sessions_allowed=...)
      → StrategyState.sessions_allowed → entry placement + pending fill gate.

    4 layer 중 하나라도 sessions_allowed 를 받지 못하면 entry/fill gate 끊김
    → silent skip 누락 + Live `is_allowed` 와 결과 불일치 risk.
    """
    from src.strategy.pine_v2.compat import parse_and_run_v2
    from src.strategy.pine_v2.event_loop import run_historical
    from src.strategy.pine_v2.strategy_state import StrategyState
    from src.strategy.pine_v2.virtual_strategy import run_virtual_strategy

    layers: dict[str, set[str]] = {
        "compat.parse_and_run_v2": set(
            inspect.signature(parse_and_run_v2).parameters
        ),
        "event_loop.run_historical": set(
            inspect.signature(run_historical).parameters
        ),
        "virtual_strategy.run_virtual_strategy": set(
            inspect.signature(run_virtual_strategy).parameters
        ),
    }
    for name, params in layers.items():
        assert "sessions_allowed" in params, (
            f"BL-188 v3: {name} 시그니처에 sessions_allowed 파라미터 누락. "
            "session gate 전파 끊김."
        )

    # StrategyState 는 dataclass field 로 노출
    state_fields = {f.name: f for f in dataclass_fields(StrategyState)}
    assert "sessions_allowed" in state_fields, (
        "BL-188 v3: StrategyState.sessions_allowed dataclass field 누락. "
        "entry hook + check_pending_fills 가 게이트 reference 잃음."
    )
    # 회귀 0 보증 — 미주입 시 24h (empty tuple) fallback
    state_default = StrategyState()
    assert state_default.sessions_allowed == (), (
        "BL-188 v3: StrategyState.sessions_allowed 기본값이 빈 tuple 이 아님 "
        f"({state_default.sessions_allowed!r}). 미주입 caller 회귀 가능."
    )


def test_bl188_mirror_not_allowed_exception_contract():
    """BL-188 v3: Live mirror Nx reject (`MirrorNotAllowed`) 구조 invariant.

    Live `strategy.settings.leverage != 1` 시 service 가 raise 하는 422 예외의
    contract — FE 가 라벨 매핑 (live_leverage / live_margin_mode) 으로 사용자
    안내 문구 구성하므로 attribute / status_code / code 가 단일 SSOT.

    BL-186 (풀 leverage/funding/liquidation 모델) 까지 본 invariant 유지 의무.
    """
    from src.backtest.exceptions import MirrorNotAllowed

    assert MirrorNotAllowed.status_code == 422, (
        f"BL-188 v3: MirrorNotAllowed.status_code 가 422 가 아님 "
        f"({MirrorNotAllowed.status_code}). FE 가 422 분기로 inline 표시."
    )
    assert MirrorNotAllowed.code == "mirror_not_allowed", (
        f"BL-188 v3: MirrorNotAllowed.code 가 'mirror_not_allowed' 가 아님 "
        f"({MirrorNotAllowed.code!r}). 라벨/번역 키 SSOT 깨짐."
    )

    # __init__ 가 live_leverage / live_margin_mode keyword 인자 보유 — 라벨 매핑.
    init_params = set(inspect.signature(MirrorNotAllowed.__init__).parameters)
    for kw in ("live_leverage", "live_margin_mode"):
        assert kw in init_params, (
            f"BL-188 v3: MirrorNotAllowed.__init__ 가 '{kw}' keyword 미보유. "
            "FE 안내 라벨 (Live leverage Nx isolated 등) 매핑 reference 끊김."
        )

    # 인스턴스에 attribute 노출 (FE serializer 가 attribute access)
    instance = MirrorNotAllowed(live_leverage=3, live_margin_mode="isolated")
    assert instance.live_leverage == 3
    assert instance.live_margin_mode == "isolated"


def _collect_corpus_pine_paths() -> list[Path]:
    """tests/fixtures 하위 corpus *.pine 전부 수집 (test_pine_partial_corpus 와 동일 helper)."""
    base = Path(__file__).resolve().parents[2] / "fixtures"
    pine_paths: list[Path] = []
    for sub in ("pine_corpus_v2", "dogfood_corpus"):
        d = base / sub
        if not d.is_dir():
            continue
        pine_paths.extend(sorted(d.glob("*.pine")))
    return pine_paths


def test_bl188_pine_partial_corpus_invariant():
    """BL-188 v3: corpus *.pine 의 strategy() 선언이 default_qty_type/value XOR partial 0건.

    service._resolve_sizing_canonical 가 partial 선언을 422 reject 하므로 corpus
    에 partial 이 섞이면 회귀 검증 오염. test_pine_partial_corpus.py 와 동일
    invariant — ssot audit 의 "한 곳에 모든 invariant" 원칙 (codex P2 #4) 으로
    duplicate redundancy. helper / fixture 경로 변경 시 단일 자원으로 재현 가능.
    """
    from src.strategy.pine_v2.ast_extractor import extract_content

    paths = _collect_corpus_pine_paths()
    assert len(paths) >= 1, (
        "BL-188 v3: corpus *.pine 수집 0건 — fixtures 경로 변경 또는 path 함정. "
        "tests/fixtures/{pine_corpus_v2,dogfood_corpus} 구조 확인."
    )

    violations: list[str] = []
    for pine_path in paths:
        decl = extract_content(pine_path.read_text(encoding="utf-8")).declaration
        if decl.kind != "strategy":
            continue
        qt = decl.default_qty_type
        qv = decl.default_qty_value
        if (qt is None) != (qv is None):
            violations.append(
                f"{pine_path.name}: type={qt!r} value={qv!r}"
            )
    assert not violations, (
        "BL-188 v3: corpus partial default_qty 선언 발견 — 둘 다 명시 또는 둘 다 "
        f"None 의무 (service._resolve_sizing_canonical 422 reject 대상): {violations}"
    )
