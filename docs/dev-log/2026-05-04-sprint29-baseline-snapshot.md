# Sprint 29 baseline snapshot — 6 fixture coverage 실측 (preflight 의무)

> **Date:** 2026-05-04
> **Sprint:** Sprint 29 (Pine Coverage Layer Hardening)
> **Type:** baseline snapshot (LESSON-037 second validation)
> **Trigger:** plan v2 §12 step 1 — sprint 진입 첫 step = baseline 재측정 preflight

---

## 0. TL;DR

`backend/src/strategy/pine_v2/coverage.py:analyze_coverage()` 를 6 canonical fixture 에 적용한 실측 baseline. **plan v2 의 가정 (진입 4/6 runnable) 도 부분 stale** — UtBot indicator 도 FAIL (UtBot strategy 와 동일 4 unsupported). 진입 = **3/6 (50%)** / 목표 = 5/6 (83%, UtBot indicator + UtBot strategy 동시 PASS) / DrFXGOD = 별도 metric.

**LESSON-037 second validation 결과:** baseline 재측정 preflight 가 plan v2 의 stale 가정 1건 추가 발견 (UtBot indicator FAIL 상태). preflight 의무가 사실상 매 sprint kickoff 에서 검증 가치 있음 → second validation 통과 → Sprint 30+ kickoff 에서 third validation 후 영구 승격 후보.

---

## 1. 실측 환경

- python: 3.14.4 (`backend/.venv/bin/python`)
- pytest: 9.0.3 (참고용, 본 실측은 ad-hoc python script 사용)
- 실행 위치: `backend/`
- import: `from src.strategy.pine_v2.coverage import analyze_coverage, SUPPORTED_FUNCTIONS, SUPPORTED_ATTRIBUTES, _ENUM_PREFIXES, _KNOWN_UNSUPPORTED_FUNCTIONS`
- 측정 시점: 2026-05-04 (Sprint 29 kickoff preflight, branch `stage/h2-sprint29-pine-coverage-hardening @ fba912e`)

---

## 2. SSOT collection sizes (실측)

| Collection                     | Size   | 출처                                                 |
| ------------------------------ | ------ | ---------------------------------------------------- |
| `SUPPORTED_FUNCTIONS`          | **99** | coverage.py:195                                      |
| `SUPPORTED_ATTRIBUTES`         | **39** | coverage.py:304                                      |
| `_ENUM_PREFIXES`               | **13** | coverage.py:288 (prefix lookup, NOT a constants set) |
| `_KNOWN_UNSUPPORTED_FUNCTIONS` | **7**  | coverage.py:133                                      |

**plan v2 §5 의 SSOT 명세 검증:** 정확. v1 의 fictional `SUPPORTED_ENUM_CONSTANTS` 는 실제 코드에 부재 (codex 검증 + 본 실측 일치).

---

## 3. 6 fixture baseline 표

| #   | fixture                               | tier   | lines | runnable  | #funcs | #attrs | 진입 status                                             |
| --- | ------------------------------------- | ------ | ----- | --------- | ------ | ------ | ------------------------------------------------------- |
| 1   | s1_pbr (PbR_strategy_easy)            | easy   | 21    | ✅ YES    | 0      | 0      | regression baseline                                     |
| 2   | i1_utbot (UtBot_indicator_easy)       | easy   | 42    | **❌ NO** | 3      | 1      | **FAIL — Slice A target**                               |
| 3   | i2_luxalgo (LuxAlgo_indicator_medium) | medium | 96    | ✅ YES    | 0      | 0      | runnable (e2e verify Slice A 외)                        |
| 4   | s2_utbot (UtBot_strategy_medium)      | medium | 64    | **❌ NO** | 3      | 1      | **FAIL — Slice A target**                               |
| 5   | s3_rsid (RsiD_strategy_hard)          | hard   | 208   | ✅ YES    | 0      | 0      | runnable (e2e verify Slice A 외)                        |
| 6   | i3_drfx (DrFXGOD_indicator_hard)      | hard   | 838   | **❌ NO** | 24     | 15     | **FAIL — Slice B target (PASS 불가, schema 명확 응답)** |

**진입 통과율 = 3/6 (50%)** (plan v2 가정 4/6 stale — UtBot indicator FAIL 발견).

---

## 4. UtBot fixture 4 unsupported (Slice A 정확 처리 대상)

UtBot **indicator** (i1_utbot) 와 UtBot **strategy** (s2_utbot) 가 **동일 4 unsupported**:

### unsupported_functions (3)

| 함수                            | 카테고리 | 처리 방향 (plan v2 §3)                                                           |
| ------------------------------- | -------- | -------------------------------------------------------------------------------- |
| `barcolor`                      | drawing  | interpreter NOP + coverage SUPPORTED_FUNCTIONS 추가 (시각 효과만, 백테스트 무관) |
| `heikinashi`                    | data     | **ADR 결정 필요** (Trust Layer 정합 — BL-096 partial)                            |
| `security` (= request.security) | data     | 단일 timeframe graceful (현재 KNOWN_UNSUPPORTED_FUNCTIONS:139)                   |

### unsupported_attributes (1)

| attribute          | 처리 방향                                                                                          |
| ------------------ | -------------------------------------------------------------------------------------------------- |
| `timeframe.period` | coverage SUPPORTED_ATTRIBUTES 추가 + interpreter 상수 정의 (현재 backtest timeframe string return) |

### Slice A 의 lever 가 plan v2 보다 큼

UtBot indicator + strategy 가 **동일 4 항목 공유** → Slice A 가 4 항목 처리하면 **2 fixture 동시 PASS**. 통과율 lever = 3/6 → **5/6 (+2)** (plan v2 의 "+1" 가정보다 큰 효과).

목표 통과율 5/6 동일 (3/6 → 5/6 vs plan v2 의 4/6 → 5/6), 단 lever 가 2배.

---

## 5. DrFXGOD 39 unsupported (Slice B 정확 처리 대상)

### unsupported_functions (24)

```
barcolor              # Slice A 도 처리 (UtBot 와 공유)
box.delete            # interpreter 이미 구현, coverage 만 등록 → Slice C parity 자연 해소
box.get_bottom        # 동일
box.get_top           # 동일
box.set_right         # 동일
fixnan
label.delete          # interpreter 이미 구현 (codex 검증) → Slice C parity
label.get_x           # 동일
label.set_x           # 동일
label.set_y           # 동일
line.delete           # interpreter 이미 구현 → Slice C parity
line.get_price        # interpreter 이미 구현 → Slice C parity
request.security      # KNOWN_UNSUPPORTED:139 (Slice A 와 공유, 단 graceful 의 결과 차이)
request.security_lower_tf  # KNOWN_UNSUPPORTED:140
ta.alma               # stdlib 미등록
ta.bb                 # stdlib 미등록
ta.cross              # stdlib 미등록
ta.dmi                # stdlib 미등록
ta.mom                # stdlib 미등록
ta.wma                # stdlib 미등록
table.cell            # interpreter 이미 구현 → Slice C parity
table.cell_set_bgcolor  # 미구현
ticker.new            # KNOWN_UNSUPPORTED:143
time                  # 단순 NOP 가능
```

### unsupported_attributes (15)

```
barstate.isrealtime
label.style_label_down  # enum
label.style_label_left  # enum
label.style_label_up    # enum
syminfo.prefix
syminfo.ticker
syminfo.timezone
ta.obv                  # attribute 형태 — 의도된 사용 패턴 의심
timeframe.isdaily       # bool
timeframe.isminutes     # bool
timeframe.ismonthly     # bool
timeframe.isseconds     # bool
timeframe.isweekly      # bool
timeframe.multiplier    # int
timeframe.period        # Slice A 와 공유
```

### Slice B 처리 categorization

| 카테고리                                                      | 항목 수                                | 처리 방식                                                                                   |
| ------------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------- |
| **interpreter 이미 구현, coverage 만 등록**                   | ~10 (box._/line._/label.\_/table.cell) | Slice C parity audit 자연 해소 (workaround = "Drawing layer NOP, 시각 표시 외 로직 의존 X") |
| **enum lookup 누락**                                          | 4 (label.style\__, timeframe.is_)      | \_ENUM_PREFIXES 또는 SUPPORTED_ATTRIBUTES 확장                                              |
| **stdlib ta.\* 미등록**                                       | 6 (ta.alma/bb/cross/dmi/mom/wma)       | Slice B workaround dict + Slice C audit 명시 (단순 알고리즘 차이)                           |
| **request.\* / ticker.new**                                   | 3                                      | KNOWN_UNSUPPORTED 유지, line + workaround "단일 timeframe 권장"                             |
| **fixnan / time / barstate.isrealtime / syminfo.\* / ta.obv** | ~10                                    | workaround dict 등록 (대체 패턴 안내)                                                       |

**Slice C parity audit 으로 ~10 항목 자연 해소 가능** → DrFXGOD response 의 unsupported 가 24+15=39 → ~29 로 감소 가능. workaround dict 80% coverage 임계는 29 항목 중 23+ 가 더 현실적.

---

## 6. plan v2 갱신 사항 (본 preflight 결과 반영)

### 6.1 §3 진단표 — UtBot indicator FAIL 추가

| 변경                        | 기존 (plan v2)              | 신규 (본 preflight)                                                 |
| --------------------------- | --------------------------- | ------------------------------------------------------------------- |
| UtBot indicator 진입 status | ✅ PASS regression baseline | **❌ FAIL — Slice A target (UtBot strategy 와 동일 4 unsupported)** |
| 진입 통과율                 | 4/6 (67%)                   | **3/6 (50%)**                                                       |
| Slice A lever               | UtBot strategy +1 (4→5)     | **UtBot indicator + UtBot strategy +2 (3→5)**                       |

### 6.2 §3 통과율 산식 재정의

- **진입 baseline = 3/6 (50%)**: PbR ✅ + LuxAlgo ✅ + RsiD ✅
- **목표 = 5/6 (83%)**: + UtBot indicator + UtBot strategy 동시 (Slice A 4 항목 처리 효과)
- **DrFXGOD = 6/6 불가**, 별도 metric (`drfx_response_quality`: line + workaround 포함 ≥ 80%)

### 6.3 §4 Slice A scope 명확화

UtBot indicator + UtBot strategy **둘 다 e2e backtest stable PASS** 검증 의무. fixture 등록:

- `backend/tests/strategy/pine_v2/test_utbot_strategy_e2e.py` — UtBot strategy
- `backend/tests/strategy/pine_v2/test_utbot_indicator_e2e.py` (신규 추가) — UtBot indicator

### 6.4 §5 SSOT 명세 검증 완료

실측 SSOT (99 / 39 / 13 / 7) 가 plan v2 §5 의 명세 일치. **변경 불필요**. v1 의 fictional `SUPPORTED_ENUM_CONSTANTS=40+` 는 실제 부재 — Slice C 갱신 의무 (architecture.md:95-126) 정확.

### 6.5 §6 메타-방법론 — LESSON-037 second validation evidence

- first validation: Sprint 29 plan v1 → v2 frame change (codex+Opus 2-검토)
- **second validation: 본 preflight 결과** (plan v2 의 UtBot indicator 가정 stale 1건 추가 발견)
- third validation: Sprint 30+ kickoff 에서 자연 검증
- 3회 누적 통과 → `.ai/common/global.md` 또는 `.ai/project/lessons.md` 영구 승격

**보강 정의 (Sprint 29 second validation 후):**

> baseline 재측정 preflight 는 sprint kickoff 의 첫 step 의무. plan v1 과 plan v2 둘 다 가정 검증 대상. preflight 가 sprint 안 frame change 1회+ 발견 시 plan rewrite 의무 (cost 낮음, 진입 후 발견 cost 와 비교).

---

## 7. Slice C parity audit 의 추가 candidate (본 preflight 발견)

`_RENDERING_FACTORIES` 에 등록된 메서드가 `SUPPORTED_FUNCTIONS` 에 미포함된 항목 — Slice C 의 invariant test 가 자연 catch. 본 preflight 에서 발견된 후보:

```
box.delete, box.get_bottom, box.get_top, box.set_right
label.delete, label.get_x, label.set_x, label.set_y
line.delete, line.get_price
table.cell
```

이 11 항목이 Slice C `test_rendering_factories_subset_of_supported_functions` 가 fail 하면 Slice A 와 자연 통합 (UtBot 외 DrFXGOD 의 unsupported 도 동시 감소).

**Slice C 의 lever 가 plan v2 보다 큼** — 단순 invariant test 가 아니라 11 항목 supported list 자동 확장 trigger.

---

## 8. 다음 step (사용자 보고 후 결정)

1. plan v2 §3 / §4 / §6 갱신 (본 preflight 결과 반영) — Edit tool 로 즉시 가능
2. branch 안 baseline-snapshot.md commit (Slice C scope 산출물이지만 preflight 결과로서 즉시 commit 가능)
3. brainstorming skill (60분) — Slice A/B/C scope 사용자 align
4. Slice A‖C 병렬 진입

**중요:** 본 preflight 의 통과율 산식 변경 (4/6 → 3/6 진입) 은 **dual metric 의 진입 baseline 갱신**. Sprint 29 종료 시 dual metric 측정 시 본 baseline 과 비교.

---

## 9. 영구 사료

- 본 dev-log 가 sprint 29 진입 시점 baseline 의 SSOT
- Sprint 30+ kickoff 시 비교 anchor (3/6 → 진행)
- LESSON-037 second validation evidence 영구 보존
- DrFXGOD 39 unsupported 정확 list = Slice B workaround dict 작성 시 직접 사용

**End of Sprint 29 baseline snapshot.**
