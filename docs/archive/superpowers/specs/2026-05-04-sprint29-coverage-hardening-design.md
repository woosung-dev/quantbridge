# Sprint 29 — Pine Coverage Layer Hardening + DrFXGOD Schema (Design Spec)

> **Date:** 2026-05-04
> **Sprint:** 29 (Type A, 신규 기능)
> **Branch:** `stage/h2-sprint29-pine-coverage-hardening` @ `9cf55f6`
> **Plan v2.1:** `~/.claude/plans/quantbridge-sprint-29-sunny-origami.md`
> **Preflight evidence:** [`docs/dev-log/2026-05-04-sprint29-baseline-snapshot.md`](../../dev-log/2026-05-04-sprint29-baseline-snapshot.md)
> **v1→v2 pivot evidence:** [`docs/dev-log/2026-05-04-sprint29-v1-to-v2-pivot.md`](../../dev-log/2026-05-04-sprint29-v1-to-v2-pivot.md)
> **Time budget:** 12-18h (3 Slice, C → A‖B 순서, cmux 2 워커)

---

## 1. Context

### 1.1 왜 본 sprint

Sprint 28 종료 후 본인 dogfood 결과:

- 본인이 사용하는 indicator (LuxAlgo / RsiD) 는 사실 coverage runnable. e2e backtest 의 unstable 만 잔존.
- **UtBot strategy** + **UtBot indicator** 가 둘 다 reject 되어 dogfood 흐름이 깨짐 (실측 4 unsupported 공유 — preflight 발견)
- **DrFXGOD** 는 reject 시 Coverage Analyzer 가 함수명만 나열 — 사용자가 어디 line / 어떻게 우회 인지 알 수 없음 → 매번 함수 검색 + 수동 line scan + 우회 추측 = whack-a-mole 의 user-side 재현

### 1.2 결정 (Sprint 28 §13 + v2 pivot + preflight 갱신)

- Beta open 인프라 (BL-070~075) **deferred → Sprint 30+**
- Sprint 29 = **Coverage Layer Hardening + DrFXGOD structured schema**
- 사용자 명시 요구: **if/else 패치 금지** (whack-a-mole 종식). Coverage layer 자체 강화 — patch 가 아니라 schema/parity 로 해결

### 1.3 의도된 outcome (정량)

- 6 Pine fixture coverage runnable **3/6 → 5/6 (83%)** (UtBot indicator + strategy 동시 PASS)
- DrFXGOD reject 응답이 line + workaround 포함 → 사용자가 즉시 다음 행동 결정 가능 (`drfx_response_quality` ≥ 80%)
- SSOT parity audit test 4건 자동화 → drift 재발 차단

---

## 2. Architecture

```
[Slice C]  4-6h  단독          SSOT parity audit + ~11 항목 자동 supported 확장
   ↓                            (DrFXGOD 39 → ~28 unsupported 자연 감소)
   ↓
[Slice A] ║ [Slice B]  cmux 2 워커  병렬
8-12h       8-12h
UtBot 4     Coverage schema +
unsupported  DrFXGOD response
```

### 2.1 Slice 구분

| Slice | 영역                                                                    | 시간  | 의존        |
| ----- | ----------------------------------------------------------------------- | ----- | ----------- |
| **C** | SSOT parity audit + ~11 항목 자동 supported 확장 + architecture.md 갱신 | 4-6h  | 없음 (단독) |
| **A** | UtBot 4 unsupported (heikinashi Trust Layer 위반 ADR 포함)              | 8-12h | Slice C     |
| **B** | Coverage schema + DrFXGOD line-numbered 응답                            | 8-12h | Slice C     |

### 2.2 실행 순서 근거 (D-2)

- **C 단독 진행 → A‖B 병렬:** Slice C 의 invariant test 가 supported list ~11 항목 자동 확장 trigger. Slice B 가 처리할 항목 수 39 → ~28 로 감소 (28% 감소)
- LESSON-037 정합 — Slice C 가 또 다른 frame change 발견 기회 제공 (preflight 가 v2 가정 1건 stale 발견한 것처럼)
- coverage.py 충돌 회피: Slice A (supported list 추가, 행 단위) ↔ Slice B (schema 확장, 클래스/dict 추가) 가 물리적 영역 분리

---

## 3. Components

### 3.1 Slice C — SSOT parity audit + 자동 supported 확장 (4-6h)

**신규 파일:**

- `backend/tests/strategy/pine_v2/test_ssot_invariants.py` — 4 invariant:

  ```python
  def test_stdlib_names_subset_of_supported_functions():
      assert STDLIB_NAMES.issubset(SUPPORTED_FUNCTIONS)

  def test_rendering_factories_subset_of_supported_functions():
      assert set(_RENDERING_FACTORIES.keys()).issubset(SUPPORTED_FUNCTIONS)

  def test_v4_aliases_targets_in_stdlib():
      assert all(target in STDLIB_NAMES for target in _V4_ALIASES.values())

  def test_attr_constants_parity_with_enum_prefixes():
      """interpreter 의 enum constant 정의 (예: location.absolute='absolute') 의
      prefix 집합 ⊆ coverage._ENUM_PREFIXES.

      구현 시 interpreter.py 안 enum constant 정의 위치 검색 후 prefix 추출 로직 결정.
      e.g., `_ATTR_CONSTANTS` dict 또는 module-level 상수 — 발견 위치에 맞춰 invariant.
      """
      ...
  ```

**수정 파일:**

- `backend/src/strategy/pine_v2/coverage.py` — invariant test 가 fail 한 ~11 항목 자동 supported 등록:
  - `box.delete`, `box.get_top`, `box.get_bottom`, `box.set_right`
  - `line.delete`, `line.get_price`
  - `label.delete`, `label.get_x`, `label.set_x`, `label.set_y`
  - `table.cell`
- `docs/04_architecture/pine-execution-architecture.md:95-126` — SSOT 명세 갱신:
  - 실측 size: `SUPPORTED_FUNCTIONS=99` / `SUPPORTED_ATTRIBUTES=39` / `_ENUM_PREFIXES=13` / `_KNOWN_UNSUPPORTED_FUNCTIONS=7`
  - fictional `SUPPORTED_ENUM_CONSTANTS` 표현 제거 (실제 `_ENUM_PREFIXES` prefix lookup 명시)
  - 4 invariant audit 의무 명시

**원칙:**

- audit test 4건 모두 fast (< 1s 합산)
- baseline snapshot 은 Sprint 30 진입 비교 anchor
- pine-execution-architecture.md 갱신은 SSOT 의 SSOT 가 stale 한 문제 해소

### 3.2 Slice A — UtBot 4 unsupported (heikinashi ADR 포함, 8-12h)

**수정 파일:**

- `backend/src/strategy/pine_v2/interpreter.py`:
  - `barcolor` NOP (시각 효과만, 백테스트 무관)
  - `timeframe.period` 상수 정의 (현재 backtest timeframe string return)
  - `security` graceful (이미 line 709-715 일부 처리, 단일 timeframe 가정)
- `backend/src/strategy/pine_v2/coverage.py`:
  - `SUPPORTED_FUNCTIONS` 갱신: `barcolor`, `heikinashi`, `security` 추가
  - `SUPPORTED_ATTRIBUTES` 갱신: `timeframe.period` 추가
  - `_KNOWN_UNSUPPORTED_FUNCTIONS` 에서 `request.security` 제거 (graceful 으로 이전)
- `backend/src/strategy/pine_v2/coverage.py:analyze_coverage()`:
  - heikinashi 사용 감지 시 `CoverageReport.dogfood_only_warning: str | None` 필드 추가 (Trust Layer 위반 transparency)

**신규 파일:**

- `docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md`:
  - 옵션 (a) Trust Layer 위반 + dogfood-only flag 채택 영구 기록
  - 거짓 양성 risk 명시 (heikin-ashi 캔들 ↔ 일반 OHLC 차이)
  - 사용자 명시 동의 절차 (Coverage 응답 warning 필드)
  - Sprint 30+ ADR-009 trigger (Candle transformation layer 신설 — Renko/Range bar 까지 묶어 처리)
- `backend/tests/strategy/pine_v2/test_utbot_indicator_e2e.py` (신규):
  - canonical fixture `i1_utbot.pine` 사용 → e2e backtest stable PASS
- `backend/tests/strategy/pine_v2/test_utbot_strategy_e2e.py` (신규):
  - canonical fixture `s2_utbot.pine` 사용 → e2e backtest stable PASS

**TDD 의무:**

- UtBot indicator + strategy fixture 둘 다 e2e backtest stable PASS
- 1448 BE regression 0 (Slice A 변경 후)
- coverage report 의 unsupported 카운트 4 → 0 (UtBot 양방)

### 3.3 Slice B — Coverage schema + DrFXGOD line-numbered 응답 (8-12h)

**수정 파일:**

- `backend/src/strategy/pine_v2/coverage.py` — `CoverageReport` schema 확장:

  ```python
  from typing import Literal, TypedDict

  class UnsupportedCall(TypedDict):
      name: str
      line: int
      col: int | None
      workaround: str | None
      category: Literal['drawing', 'data', 'syntax', 'math', 'other']

  @dataclass(frozen=True)
  class CoverageReport:
      used_functions: tuple[str, ...]
      used_attributes: tuple[str, ...]
      unsupported_functions: tuple[str, ...]  # 기존, backward-compat
      unsupported_attributes: tuple[str, ...]  # 기존, backward-compat
      unsupported_calls: tuple[UnsupportedCall, ...]  # 신규
      dogfood_only_warning: str | None = None  # Slice A 와 공유

      @property
      def is_runnable(self) -> bool:
          return not self.unsupported_functions and not self.unsupported_attributes
  ```

- `backend/src/strategy/pine_v2/coverage.py` — `_UNSUPPORTED_WORKAROUNDS` dict (Slice C 후 ~28 항목):

  ```python
  _UNSUPPORTED_WORKAROUNDS: dict[str, str] = {
      'request.security': '다른 timeframe 데이터는 미지원. 단일 timeframe 으로 전략 재구성 필요.',
      'request.security_lower_tf': '동일 — 단일 timeframe 권장.',
      'ta.alma': 'ta.sma 또는 ta.ema 로 근사. 정확도 차이 < 1%.',
      'ta.bb': 'ta.sma + ta.stdev 조합으로 직접 구현.',
      'ta.cross': 'ta.crossover + ta.crossunder 조합으로 대체.',
      'ta.dmi': 'ta.atr + 직접 +DI/-DI 계산.',
      'ta.mom': '변수 = close - close[length] 단순 계산.',
      'ta.wma': 'ta.sma 또는 ta.ema 로 근사.',
      'ta.obv': '단순 누적 sum 으로 직접 구현.',
      'fixnan': 'nz() 조합으로 대체.',
      'ticker.new': '단일 ticker 사용 권장 (현재 backtest symbol).',
      'time': '시간 기반 로직은 변수로 추출 (open/close 가격 기반 권장).',
      'table.cell_set_bgcolor': 'Drawing layer 는 시각 NOP. 시각 표시 외 로직에 의존하면 안전.',
      # syminfo.* / barstate.isrealtime / timeframe.is* / label.style_label_* 등
      # 카테고리별 80% coverage = 23+ 항목 등록
  }
  ```

- `backend/src/strategy/router.py` + `backend/src/strategy/schemas.py`:
  - parse-preview API 응답 schema 반영 (Pydantic V2)
  - `UnsupportedCallResponse` Pydantic model 추가
  - 기존 응답 backward-compat (추가 필드만)

**신규 파일:**

- `backend/tests/strategy/pine_v2/test_drfx_response_schema.py`:
  - DrFXGOD `i3_drfx.pine` 의 unsupported 39 (Slice C 후 ~28) 모두 `unsupported_calls` 에 line + category 포함
  - workaround dict coverage ≥ 80% (28 중 23+)
  - Pydantic schema serialization round-trip 검증

**원칙:**

- Schema 변경은 BE 단독 가능. FE 적용은 Sprint 30+ deferred (response 추가 필드는 기존 FE graceful 무시)
- workaround dict 누락 항목은 `null` (FE 가 graceful 처리)
- regex 정밀화 (BL-037 자연 연계) 는 본 sprint **deferred**. line 번호는 현재 regex 위치 사용

---

## 4. Data Flow

```
Pine source
  ↓ analyze_coverage(source)
CoverageReport {
  used_functions, used_attributes,
  unsupported_functions, unsupported_attributes,  # 기존 (backward-compat)
  unsupported_calls: [{name, line, workaround?, category}, ...]  # Slice B 신규
  dogfood_only_warning: str | None  # Slice A 신규 (heikinashi 사용 시)
}
  ↓
is_runnable?
  ├─ True (Slice A 후 UtBot 양방 PASS)
  │   ↓
  │   dogfood_only_warning?
  │     ├─ None → backtest 직접 실행
  │     └─ "heikinashi 사용 — 결과가 Pine 원본과 다를 수 있음" → 사용자 명시 동의 후 backtest
  │
  └─ False
      ↓
      422 reject + structured response (line + workaround)
        ↓
        사용자가 즉시 다음 행동 결정 (workaround 채택 또는 다른 indicator)
```

---

## 5. Error Handling

| 상황                                               | 처리                                                                                                                 |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| heikinashi 사용 (Slice A)                          | Coverage 응답 `dogfood_only_warning` 필드 → FE 또는 dogfood 사용자 명시 동의 후 backtest. ADR-008 Addendum 영구 기록 |
| 4 invariant test fail (Slice C)                    | CI 차단 (PR base 보호). supported list drift 자동 감지                                                               |
| DrFXGOD workaround 80% 미달 (Slice B)              | PR 머지 차단. dual metric `drfx_response_quality` 검증                                                               |
| 1448 BE regression 회귀                            | 즉시 rollback. Slice 별 commit 전 baseline snapshot 의무                                                             |
| `_RENDERING_FACTORIES` 신규 추가 시 supported 누락 | invariant test `test_rendering_factories_subset_of_supported_functions` 가 자동 catch                                |

---

## 6. Testing Strategy / Dual Metric

### 6.1 정량 metric

| Metric               | 통과 기준                             | 측정                                |
| -------------------- | ------------------------------------- | ----------------------------------- |
| **Pine 통과율**      | 진입 3/6 → 종료 **5/6 (83%)** ★       | UtBot indicator + strategy e2e PASS |
| **DrFXGOD response** | line + workaround ≥ 80% (28 중 23+) ★ | `test_drfx_response_schema.py`      |
| **SSOT parity**      | 4 invariant test PASS ★               | `test_ssot_invariants.py`           |
| BE regression        | 1448/1448                             | `pytest -v`                         |
| FE regression        | 257/257 (FE 변경 X 자연 PASS)         | `pnpm test`                         |
| ruff/mypy/tsc/eslint | 0/0/0/0                               | `make be-check && make fe-check`    |
| Self-assessment      | ≥7/10 + 근거 ≥3 줄                    | dev-log frontmatter                 |
| 신규 BL              | P0=0, P1≤2                            | sprint 안 추가                      |
| 기존 P0 잔여         | ≤2 (BL-003/005 deferred OK)           | sprint 종료 카운트                  |

### 6.2 검증 명령

```bash
# 1. SSOT invariant audit (Slice C)
cd backend && pytest tests/strategy/pine_v2/test_ssot_invariants.py -v

# 2. UtBot 양방 e2e (Slice A)
cd backend && pytest tests/strategy/pine_v2/test_utbot_indicator_e2e.py tests/strategy/pine_v2/test_utbot_strategy_e2e.py -v

# 3. DrFXGOD response schema (Slice B)
cd backend && pytest tests/strategy/pine_v2/test_drfx_response_schema.py -v

# 4. 1448 BE regression
cd backend && pytest -v

# 5. FE 257 regression
cd frontend && pnpm test

# 6. dogfood Bybit Demo PbR smoke (verification-before-completion)
make up-isolated  # frontend → /strategies → PbR upload → Backtest → result check
```

### 6.3 office-hours Q4 narrowest wedge sub-decision

> **Beta open prereq = "UtBot 양방 stable PASS + DrFXGOD line+workaround 응답"**

ADR-008 Addendum 후보 — Sprint 29 종료 시점에 작성. 본인 dogfood 가 narrowest wedge 검증 = 본인 신뢰 indicator 5+ 도달의 정량 metric.

---

## 7. Dependencies

- **Slice C → Slice A**: supported list ~11 항목 확장 후 Slice A 가 작은 변경 (heikinashi/timeframe.period 만 추가)
- **Slice C → Slice B**: workaround dict 작성 항목 수 감소 (39 → ~28, 80% coverage threshold = 23+)
- **Slice A ‖ Slice B**: coverage.py 충돌 X
  - A: `SUPPORTED_FUNCTIONS` / `SUPPORTED_ATTRIBUTES` 행 단위 추가
  - B: 새 클래스 (`UnsupportedCall`) + 새 dict (`_UNSUPPORTED_WORKAROUNDS`) + `CoverageReport.unsupported_calls` 필드
  - 물리적 영역 분리 → cmux 2 워커 안전

---

## 8. Decisions (확정)

| ID         | 결정                                                                                     | 근거                                                                         |
| ---------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **D1**     | heikinashi = (a) Trust Layer 위반 인정 + dogfood-only flag (ADR 영구 기록)               | dogfood-first 정합. narrowest wedge 도달. transparency ADR 으로 유지         |
| **D2+D3**  | 실행 순서 = C → A‖B (cmux 2 워커, 12-18h)                                                | Slice C 의 supported list 확장 trigger 가 Slice B input. LESSON-037 정합     |
| **D3-FE**  | Slice B FE 적용 = Sprint 30+ deferred                                                    | BE schema 단독 가능. FE 추가 필드 graceful. dogfood 시 console/API 직접 확인 |
| **D4**     | dual metric 진입 3/6 → 목표 5/6 (preflight 실측 반영)                                    | preflight `analyze_coverage` 6 fixture 실측 결과                             |
| **D4-bis** | Beta open prereq = "UtBot 양방 stable PASS + DrFXGOD line+workaround" (ADR-008 Addendum) | 본인 dogfood narrowest wedge 정량 metric                                     |
| **D5**     | Slice A‖B 병렬 = cmux 2 워커                                                             | 사용자 메모리 16+ sprint 누적 검증 패턴                                      |

---

## 9. 종료 trigger

**모든 조건 AND:**

- [ ] Slice C → A‖B commit + PR squash merge
- [ ] UtBot indicator + strategy fixture e2e PASS (5/6 통과율 도달)
- [ ] DrFXGOD response 28 unsupported 의 ≥80% (23+) line + workaround 포함
- [ ] 4 invariant audit test PASS (Slice C)
- [ ] 1448 BE + 257 FE regression 0
- [ ] heikinashi ADR 영구 기록 (`docs/dev-log/2026-05-04-sprint29-heikinashi-adr.md`)
- [ ] architecture.md SSOT 명세 갱신 verify
- [ ] dev-log + INDEX.md + lessons.md 갱신
  - LESSON-037 second validation 결과 영구 기록
  - 3회 누적 trigger (Sprint 30+ third validation 후 영구 승격) 명시
- [ ] CLAUDE.md 활성 sprint → 직전 완료 이관 (Sprint 30+ 활성)
- [ ] Self-assessment ≥7/10 dev-log frontmatter

**종료 시 Sprint 30 진입 가능 시점:** Beta open 인프라 (BL-070~075) 또는 BL-003 Bybit mainnet runbook.

---

## 10. References

### 10.1 Plan + dev-log

- Plan v2.1: `~/.claude/plans/quantbridge-sprint-29-sunny-origami.md`
- v1→v2 pivot: [`docs/dev-log/2026-05-04-sprint29-v1-to-v2-pivot.md`](../../dev-log/2026-05-04-sprint29-v1-to-v2-pivot.md)
- Baseline snapshot: [`docs/dev-log/2026-05-04-sprint29-baseline-snapshot.md`](../../dev-log/2026-05-04-sprint29-baseline-snapshot.md)
- Sprint 28 §13 (Sprint 29 scope 결정): [`docs/dev-log/2026-05-04-sprint28-retrospective.md`](../../dev-log/2026-05-04-sprint28-retrospective.md)

### 10.2 Architecture / 영구 규칙

- SSOT for Pine v4: `docs/04_architecture/pine-execution-architecture.md`
- Pine 영구 규칙: `.claude/CLAUDE.md` (exec/eval 금지, 1 unsupported = 전체 Unsupported, Tier-0 Execution-First, 범위 A, 3-Track 분류)
- ADR-003 Pine runtime safety: `docs/dev-log/003-pine-runtime-safety-and-parser-scope.md`
- ADR-016 Sprint Y1 Coverage Analyzer: `docs/dev-log/016-sprint-y1-coverage-analyzer.md`

### 10.3 BL audit

- BL-022 (golden expectations 재생성) → Sprint 30+ deferred
- BL-037 (Coverage Analyzer regex → AST visitor) → 본 sprint deferred (workaround dict + line 만)
- BL-096 partial (UtBot×2 잔존 — heikinashi/security) → **Slice A 안 ADR 결정 의무 (D1 = a)**
- BL-098/099 ✅ Resolved (Sprint 23)
- BL-142 (ts.ohlcv daily refresh) → Sprint 30+ deferred
- BL-146 (메타-방법론 4종 영구 규칙 승격) → Sprint 29 second validation + LESSON-037 first/second validation

### 10.4 LESSON

- LESSON-001 (Pine exec() 인젝션 위험)
- LESSON-003 (Pine 파싱 80% 가정 과대평가)
- LESSON-019 (commit-spy 회귀 의무화) — 본 sprint scope 외
- LESSON-033 (Sprint type 분류, Sprint 28 first validation)
- LESSON-035 (dual metric, Sprint 28 first validation)
- **LESSON-037 후보 (sprint kickoff baseline 재측정 preflight, Sprint 29 first/second validation)**

---

**End of Sprint 29 design spec.**
