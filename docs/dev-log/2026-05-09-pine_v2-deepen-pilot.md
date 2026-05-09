# /deepen-modules 스킬 신설 + pine_v2 SSOT pilot — 2026-05-09

> **Outcome:** 신규 스킬 `~/.claude/skills/deepen-modules/SKILL.md` 등록 + pine_v2 audit 1회 pilot 완료. BL-200/201 신규 등재 + `.ai/common/global.md` §7.5 신규 영구 규칙 1조 추가. Sprint 47 = deepening sprint 단독 권고.

## Context

YouTube _"How to fix an AI-fucked Codebase"_ (John Ousterhout _A Philosophy of Software Design_ 기반) 영상의 통찰을 QuantBridge 에 적용. AI 가 누적 작성한 코드는 **shallow module** (interface 가 큰데 implementation 이 빈약) 과 **locality 깨짐** (같이 변경되어야 할 코드가 N 파일에 흩어짐) 을 누적시킨다는 가설을 pine_v2 인터프리터에서 검증.

기존 자산 갭:

- `simplify` / `health` / `review` 스킬 = _코드 품질_ 관점, _모듈 깊이_ 관점 X
- 93 active BL 인벤토리는 있으나 "shallow module 기인" 분류 X
- codex G.0 / G.4 gate 도 모듈 깊이 lens 명시적 미사용

## Phase 1 결과 — Module Inventory & Depth Mapping

**Scope:** `backend/src/strategy/pine_v2/**` (16 files, ~5048 LOC)

| 모듈                      | LOC  | Public Surface                                          | 분류               | 비고                                  |
| ------------------------- | ---- | ------------------------------------------------------- | ------------------ | ------------------------------------- |
| **interpreter.py**        | 1239 | `Interpreter` 1 클래스 + 8 `_eval_*`/`_exec_*`          | 🟢 Deep            | Bar-by-bar 해석 엔진, SSOT 핵심       |
| **stdlib.py**             | 660  | `StdlibDispatcher.call()` 1 method + 17 ta.\*           | 🟢 Deep            | single dispatch + stateful indicators |
| **strategy_state.py**     | 461  | `StrategyState` 1 클래스 (entry/close/exit/close_all)   | 🟢 Deep            | position lifecycle + fill mechanics   |
| **alert_hook.py**         | 474  | `collect_alerts()` + `classify_message()` + `AlertHook` | 🟢 Deep            | condition AST + regex/JSON parsing    |
| **event_loop.py**         | 270  | `run_historical()` / `run_live()` 2 함수                | 🟢 Deep            | loop state management                 |
| **virtual_strategy.py**   | 240  | `VirtualStrategyWrapper` + `run_virtual_strategy()`     | 🟢 Deep            | alert→action edge-trigger dispatch    |
| **rendering.py**          | 169  | `RenderingRegistry` + 12 메서드                         | 🟢 Deep            | rendering object handle 관리          |
| **runtime/persistent.py** | 145  | `PersistentStore` (persist/reset)                       | 🟢 Deep            | var/varip dict 라이프사이클           |
| **coverage.py**           | 750  | `analyze_coverage()` + 16+ frozenset 상수               | 🔴 **Shallow**     | 거대한 상수 collection lookup         |
| **ast_extractor.py**      | 376  | `extract_content()` + 4 dataclass                       | 🟡 Shallow 의심    | string parsing 위주                   |
| **ast_classifier.py**     | 160  | `classify_script()` → `ScriptProfile`                   | 🔴 **Shallow**     | call counter + Track enum 결정만      |
| **compat.py**             | 138  | `parse_and_run_v2()` + `_extract_default_qty()`         | 🔴 **Shallow**     | Track 3-way dispatcher                |
| **parser_adapter.py**     | 15   | `parse_to_ast()` thin wrapper                           | 🟢 (얕지만 의도적) | pynescript shim                       |

**결론:** Deep 모듈 8/13 + Shallow 후보 5/13. Deep:Shallow 비율 = 1.6:1 (양호). 단 shallow 후보가 SSOT 핵심 (coverage / ast_classifier / compat) 에 집중.

## Phase 2 결과 — Locality & Coupling Analysis

| 패턴                                  | 심각도 | Touch 파일                                                   | Risk                                                       |
| ------------------------------------- | ------ | ------------------------------------------------------------ | ---------------------------------------------------------- |
| **STDLIB_NAMES triple SSOT**          | 🔴 높  | interpreter / stdlib / coverage (3)                          | silent failure (coverage 17 vs interpreter 19, na/nz 누락) |
| **Track S/A/M dispatcher 분산**       | 🔴 높  | compat / ast_classifier / virtual_strategy / interpreter (4) | Track 추가 시 4 파일 동시 수정 의무                        |
| **supported_attributes 4-collection** | 🟡 중  | coverage 내부 + interpreter `_eval_attribute`                | 일관성 mechanism 부재                                      |
| **strategy.\* dispatcher 분산**       | 🟡 중  | interpreter / strategy_state / coverage (3)                  | partial coverage false-positive risk                       |

## Phase 3 결정 로그 — Grilling Session

사용자에게 4 후보 별점 추천도와 함께 제시 (multiSelect):

| 후보                                      | 별점  | 결정    | 사유                                               |
| ----------------------------------------- | ----- | ------- | -------------------------------------------------- |
| **A. STDLIB triple SSOT 단일화**          | ★★★★★ | ✅ 승인 | silent failure risk + dogfood Phase 2 진입 전 권장 |
| **B. Track S/A/M Strategy pattern**       | ★★★★☆ | ✅ 승인 | 누적 분산 가장 큼 + 9-12h 단일 sprint              |
| **C. supported_attributes single source** | ★★★☆☆ | ❌ 거부 | 단독 가치 작음, A 와 묶어야 의미                   |
| **D. strategy.\* dispatcher 통합**        | ★★★☆☆ | ❌ 거부 | 단독 가치 작음, B 와 묶어야 의미                   |

**Sprint 47 권고:** deepening sprint 단독 (등재된 BL A+B 묶음).

**§7.5 영구 규칙:** 즉시 추가.

## Phase 4 등재

### `docs/REFACTORING-BACKLOG.md` 신규 BL 2건 (P2 섹션)

- **BL-200** — pine_v2 STDLIB triple SSOT 단일화 (`stdlib_registry.py` 신설)
  - **현 상태:** `STDLIB_NAMES` 가 interpreter.py:55-77 (19개) / stdlib.py:598-660 dispatch (19개) / coverage.py:26-46 `_TA_FUNCTIONS` (17개, na/nz 누락) 3중 SSOT
  - **목표 인터페이스:**

    ```python
    # pine_v2/stdlib_registry.py
    @dataclass
    class StdlibFunc:
        name: str
        impl: Callable[..., Any]
        is_dogfood_only: bool = False

    REGISTRY: dict[str, StdlibFunc] = {
        "ta.sma": StdlibFunc("ta.sma", _impl_sma),
        # ... 모든 ta.* / na / nz / ...
    }

    # 다른 모듈은 다음 derived view 만 import
    STDLIB_NAMES: frozenset[str] = frozenset(REGISTRY.keys())
    SUPPORTED_BY_COVERAGE: frozenset[str] = frozenset(
        n for n, f in REGISTRY.items() if not f.is_dogfood_only
    )
    ```

  - **영향 파일:** interpreter.py / stdlib.py / coverage.py 3 → 1 신규 + 3 thin import
  - **예상 LOC delta:** -50 (중복 제거)
  - **Risk:** 🟡 중 (252+ pine_v2 test 안전망 보장)
  - **우선순위:** ★★★★★ — dogfood Phase 2 진입 전 권장
  - **Est:** M (4-6h)

- **BL-201** — pine_v2 Track S/A/M Strategy pattern (`track_runner.py` 신설)
  - **현 상태:** Track 분기가 4 파일 분산 (compat dispatcher + ast_classifier 판정 + virtual_strategy/interpreter entry gate)
  - **목표 인터페이스:**

    ```python
    # pine_v2/track_runner.py
    class TrackRunner(Protocol):
        def classify(self, profile: ScriptProfile) -> bool: ...
        def run(self, ast, ctx) -> V2RunResult: ...

    class TrackS: ...   # historical strategy (rule-based)
    class TrackA: ...   # alert-driven virtual strategy
    class TrackM: ...   # mixed (manual hooks)

    RUNNERS: list[TrackRunner] = [TrackS(), TrackA(), TrackM()]

    def parse_and_run_v2(source, ...) -> V2RunResult:
        ast = parse_to_ast(source)
        profile = classify_script(ast)
        for runner in RUNNERS:
            if runner.classify(profile):
                return runner.run(ast, ctx)
    ```

  - **영향 파일:** compat / ast_classifier / virtual_strategy / interpreter 4 → 1 신규 + 3-4 thin
  - **예상 LOC delta:** +0 ~ +50
  - **Risk:** 🔴 높 (SSOT 핵심)
  - **우선순위:** ★★★★☆ — Sprint 47 단독 sprint
  - **Est:** M-L (9-12h)

### `.ai/common/global.md` §7.5 영구 규칙 신규

> **§7.5 신규 도메인 / 큰 모듈 신설 직후 = `/deepen-modules` 1회 권장 (Sprint 46 pilot 채택)**

검증 누적: Sprint 46 pine_v2 SSOT pilot (1/3). 3/3 후 LESSON-XXX 정식 승격.

### LESSON 후보 (lessons.md, 미작성 — Sprint 47 close-out 시 평가)

```
LESSON-062 후보 (deepen-modules pine_v2 pilot, 2026-05-09): pine_v2 SSOT 에서
"동일 list/set 이 N 파일에 정의된 패턴" = silent failure source. interpreter
19개 / coverage 17개 (na/nz 누락) 발견. 신규 도메인 신설 시 single-source
registry 패턴 디폴트 의무.
```

## Sprint 47 권고

**테마:** Architectural Deepening (BL-200 + BL-201 묶음)

**Sub-tasks:**

- Slice 1: BL-200 STDLIB triple SSOT 단일화 (4-6h, 단독)
- Slice 2: BL-201 Track S/A/M Strategy pattern (9-12h, BL-200 후 진행)
- Total: 13-18h (단일 sprint 큰 편이나 risk 분산)

**Prerequisites:**

- Sprint 46 stage→main 사용자 머지 완료 (현재 대기 중)
- dogfood Phase 2 timing 결정 (Sprint 47 동시 또는 Sprint 47 후)

**Sprint kickoff §7.1 baseline preflight 의무 항목:**

- pine_v2 252+ test baseline 재측정 (PR 회귀 0 보증 필수)
- `STDLIB_NAMES` 실제 수 검증 (`grep -c` 으로 19/19/17 확인)
- Track S/A/M 분기 실제 touch point 4 파일 재확인 (drift 없는지)
- codex G.0 master plan validation 1회 + §7.4 prereq spike 의무

## 다음 audit 권고

이번 pine_v2 pilot 이 **1/3 검증**. 다음 도메인 audit 후보 (사용자 결정):

| 후보 도메인                                    | scope    | 예상 발견                                  | 권고 timing        |
| ---------------------------------------------- | -------- | ------------------------------------------ | ------------------ |
| **frontend dashboard-shell + 16 페이지**       | ~80 file | cross-page component 분리 후 locality 검증 | Sprint 48+         |
| **backend Trading 도메인 (CCXT + KS + Order)** | ~30 file | Adapter pattern 적용 정합                  | dogfood Phase 2 후 |
| **backend Backtest + Optimizer + StressTest**  | ~40 file | Celery task locality                       | Sprint 49+         |

3/3 검증 통과 후 LESSON-062 정식 승격 + §7.5 → "권장" → "의무" 승격.

## Verification

- [x] `~/.claude/skills/deepen-modules/SKILL.md` 존재 (9836 bytes)
- [x] available-skills 목록에 `deepen-modules` 등록 (auto-discover)
- [x] `docs/REFACTORING-BACKLOG.md` 에 BL-200 / BL-201 신규 row (P2 섹션 끝)
- [x] BL 항목의 영향 파일 경로 실제 존재 확인 (interpreter.py / stdlib.py / coverage.py / compat.py / ast_classifier.py / virtual_strategy.py — `ls backend/src/strategy/pine_v2/` 검증 가능)
- [x] `.ai/common/global.md` §7.5 신규 + 적용 의무 시점 표 1줄 추가
- [x] dev-log 본 파일 작성

## End-to-End 검증 (다음 sprint 시점)

- [ ] Sprint 47 kickoff 시 §7.1 baseline preflight 통과
- [ ] BL-200 + BL-201 stage 머지 후 252+ pine_v2 test 회귀 0 보증
- [ ] Sprint 48+ 에서 `/deepen-modules` 재호출 → 다른 도메인 (예: Trading 또는 frontend) audit 1 사이클 정상 동작 (2/3 검증)
