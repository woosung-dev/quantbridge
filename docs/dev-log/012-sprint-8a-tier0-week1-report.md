# Sprint 8a Tier-0 Week 1 Foundation Report

> **일자:** 2026-04-18 (Day 1-8 통합 v1.1)
> **브랜치:** `feat/sprint8a-tier0-pynescript-fork`
> **관련 PR:** #20
> **ADR:** [ADR-011 Pine Execution Strategy v4](011-pine-execution-strategy-v4.md) (+[#19 amendment](https://github.com/woosung-dev/quantbridge/pull/19))
> **선행 작업:** [Phase -1 findings](../../.gstack/experiments/phase-minus-1-drfx/output/phase-1-findings.md) (PR #18 merge `0f6583d`)

---

## 🎯 한 줄 권고

> **CONTINUE to Sprint 8a Week 2-3 (bar-by-bar 이벤트 루프 + 렌더링 범위 A 런타임 + strategy.* 실행). Week 1 Foundation 5개 레이어 + 통합 POC가 6 corpus × 99 tests로 검증됨. Day 6-8 심화로 v0 약점 4개(condition-trace 미구현 / 선언 kwargs 손실 / 파서 에러 경로 미검증 / 4레이어 통합 미증명)가 전부 해소.**

---

## 1. Week 1 실측 범위 — 5 레이어 Foundation (Day 1-8)

Sprint 8a 3주 중 Week 1(Day 1-8)을 5개 수직 레이어 구축 + 통합 POC에 투입:

| # | 레이어 | 파일 | 테스트 수 | 가치 |
|:--:|------|------|:--:|------|
| **L1** | **Pine 파서** (pynescript 0.3.0 래퍼) | `parser_adapter.py`, `ast_metrics.py` | 7 + **10 edges** | AST 생성 + E2 노드 수치 회귀 + **빈/공백/주석/구문오류/unicode 에러 경로 고정** |
| **L2** | **AST 분류기** | `ast_classifier.py` | 12 | Track S/A/M 자동 판정 + 호출 분포 프로파일 |
| **L3** | **Alert Hook** (v1, condition-trace) | `alert_hook.py` | **29** | 메시지 + **조건 변수 역추적** + i3_drfx #2 mismatch 자동 감지 |
| **L4** | **런타임 primitive** (var/varip) | `runtime/persistent.py` | 15 | PyneCore Apache 2.0 의미론 참조 이식 |
| **L7** | **AST content extractor** | `ast_extractor.py` | 21 | strategy kwargs + inputs + var 선언 + strategy.* 실행 call 전부 |
| **Integration** | **L1 → L7 → L4 POC** | `test_runtime_integration.py` | 5 | 파싱 → 추출 → 스토어 등록 → multi-bar 시뮬레이션 |
| **합계** | — | 9 소스 / 6 테스트 파일 | **99 tests** | ruff/mypy clean, 기존 526 regression green |

---

## 2. 6 Pine Script × 4 레이어 매트릭스

### 입력 corpus (Phase -1 frozen snapshot)

| # | Track | 파일 | 크기 | Pine ver |
|:--:|:---:|------|---:|:---:|
| S1 | S 🟢 | `s1_pbr.pine` (Pivot Reversal Strategy) | 828B | v5 |
| S2 | S 🟠 | `s2_utbot.pine` (UT Bot Strategy) | 2,784B | v5 |
| S3 | S 🔴 | `s3_rsid.pine` (RSI Divergence Strategy) | 6,555B | v5 |
| I1 | A 🟢 | `i1_utbot.pine` (UT Bot Alerts) | 1,781B | v4 `study()` |
| I2 | A 🟠 | `i2_luxalgo.pine` (LuxAlgo Trendlines) | 3,903B | v5 |
| I3 | A 🔴 | `i3_drfx.pine` (DrFX Diamond Algo) | 38,308B | v5 |

### L1 — Pine 파서 (pynescript 0.3.0 AST 생성)

Phase -1 E2 실측 수치와 **strict equality** 회귀 고정:

| Corpus | Node types | Total nodes |
|:---|---:|---:|
| s1_pbr     | 24 | 231 |
| s2_utbot   | 27 | 734 |
| s3_rsid    | 32 | 1,245 |
| i1_utbot   | 25 | 587 |
| i2_luxalgo | 30 | 822 |
| i3_drfx    | **40** | **10,289** |

**합의:** pynescript 0.3.0으로 6/6 파싱 성공 재확인. QB 자체 파서(기존 `src/strategy/pine/`)가 0/6이었던 Phase -1 결과 대비 대비 **완전 역전**. 파서 포크 결정 실증 계속.

### L2 — AST 분류기 (3-Track 자동 판정)

| Corpus | decl | **Track** | alert | security | strategy.* | render A | render NOP |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| s1_pbr     | strategy  | **S** | 0 | 0 | 2 | 0 | 0 |
| s2_utbot   | strategy  | **S** | 0 | 0 | 2 | 0 | 4 |
| s3_rsid    | strategy  | **S** | 0 | 0 | 3 | 0 | 13 |
| i1_utbot   | indicator (v4 study) | **A** | 2 | 0 | 0 | 0 | 4 |
| i2_luxalgo | indicator | **A** | 2 | 0 | 0 | 2 | 4 |
| i3_drfx    | indicator | **A** | 6 | **8** | 0 | **79** | 12 |

**Track 분포 (N=6):** S 3/6 (50%) / A 3/6 (50%) / **M 0/6 (0%)** — 사용자 제공 corpus 특성 반영. TV 공개 스크립트 15~20개 프로파일링(별도 Day 6-7 액션) 필요.

### L3 — Alert Hook v1 (condition-trace 포함, Day 6)

Track A 3 corpus에서 **alert 10개 추출 + 메시지/조건 독립 분류 + discrepancy 자동 감지**:

| # | Corpus | kind | message | condition | **signal** |
|:--:|:---|:---|---|---|:---:|
| 1 | i1_utbot | alertcondition | `"UT Long"` | `buy` | **long_entry** |
| 2 | i1_utbot | alertcondition | `"UT Short"` | `sell` | **short_entry** |
| 3 | i2_luxalgo | alertcondition | `"Price broke the down-trendline upward"` | `upos <cmp> …` | **information** |
| 4 | i2_luxalgo | alertcondition | `"Price broke the up-trendline downward"` | `dnos <cmp> …` | **information** |
| 5 | i3_drfx | alertcondition | `"BUY"` | `bull` | **long_entry** |
| 6 | i3_drfx | alertcondition | `"BUY"` | `bear` ⚠️ | **long_entry** ⚠️ |
| 7 | i3_drfx | alert | `"break down trendline"` | (no cond arg) | **information** |
| 8 | i3_drfx | alert | `"break upper trendline"` | (no cond arg) | **information** |
| 9 | i3_drfx | alert | `"Buy Alert"` | (no cond arg) | **long_entry** |
| 10 | i3_drfx | alert | `"Sell Alert"` | (no cond arg) | **short_entry** |

- **분류 커버리지 100% (unknown 0/10)** — ADR-011 §2.1.2 정확도 >80% 가정 충족
- **최종 분포 (v1 condition 우선):** long_entry 3 / short_entry 3 / information 4
- **⚠️ i3_drfx #2 자동 감지 (v1 핵심):** `alertcondition(bear, "BUY", "BUY")` → message_signal=LONG_ENTRY vs condition_signal=SHORT_ENTRY → **discrepancy=True 자동 플래그**, 최종 signal=SHORT_ENTRY(condition 우선). 소스 오타·저자 실수 자동 방어.
- **v1 구현 메커니즘 (ADR-011 §2.1.3):** AST ancestor 추적으로 감싸는 if 조건 수집 → symbol_table(top-level Assign)로 변수명 1-step look-up → 원본 변수명 우선, 해석 결과는 fallback

### L4 — PersistentStore (var/varip 런타임 primitive)

PyneCore `transformers/persistent.py` 의미론 참조 이식 + 15 유닛 테스트:

- `declare_if_new(key, factory, varip=False)` — lazy init (첫 bar에서만 factory 평가)
- Bar lifecycle: `begin_bar() → [execute] → commit_bar() | rollback_bar()`
- var rollback: 시작-of-bar 값으로 복원 (realtime 재실행)
- varip rollback 예외: 인트라-bar 업데이트 유지
- 이번 바 신규 선언 var는 rollback에서 제거, 신규 varip은 유지
- historical 5-bar 시뮬레이션: `var highest := max(highest, close)` 패턴 검증

**Day 8 통합 POC (Week 2-3 교두보):** 실제 Pine 소스 `var counter = 0`을 pynescript로 파싱 → ast_extractor로 `VarDecl` 추출 → PersistentStore에 등록 → 3-bar `counter := counter + 1` 시뮬레이션 → `[1, 2, 3]` 확인. i2_luxalgo 9개 var 등록도 통과. **4개 레이어가 조립 가능함을 실증**.

### L7 — AST content extractor (Day 7)

strategy()/indicator() 선언의 **전체 kwargs 보존** + inputs + var 선언 + strategy.* 실행 call 구조화 추출.

**추출 총량 (N=6 corpus):**

| 요소 | 총합 | 내역 |
|:---|---:|---|
| **inputs** | 57 | s1:2, s2:9, s3:15, i1:3, i2:7, i3:21 |
| **var/varip 선언** | 33 | s1/s2/s3/i1:0, i2:9, i3:24 |
| **strategy.* 실행** | 7 | s1:2 entry, s2:2 entry, s3:1 entry+2 close, i1-i3:0 |
| **strategy() kwargs** | s3 기준 7개 | title, overlay, initial_capital, commission_type, commission_value, pyramiding |

**핵심 성과:** s3_rsid의 `initial_capital`, `commission_value`, `pyramiding` 같은 백테스트 정밀도 좌우 kwargs가 이제 interpreter에서 사용 가능. Pine v4 legacy `input()` vs v5+ `input.int/float` 모두 감지.

### L1 edge cases + Integration POC (Day 8)

- **L1 에러 경로 10개:** 빈/공백/주석 → 파싱 OK (body 빈 리스트) / syntax error / invalid token / unbalanced paren → `pynescript.ast.error.SyntaxError` (Python 내장 SyntaxError 미상속, Week 2+ error UX 전제 고정) / 긴 line + unicode 파싱 통과
- **통합 POC 5개:** L1 파싱 → L7 VarDecl 추출 → L4 등록 → 3-bar 시뮬레이션 → 값 확인. corpus s1_pbr 통과, corpus i2_luxalgo 9 var 모두 등록 성공

---

## 3. ADR-011 §9 가정 3개 재판정

| # | 가정 (ADR-011 §9) | Week 1 증거 | 판정 |
|:--:|---|---|:--:|
| **A1** | Track S/A/M 비율 **20~30% / 40~50% / 20~30%** | L2: N=6에서 S 50%, A 50%, M 0%. 사용자 corpus 특성이 반영되어 일반화는 **불가**. TV 15~20개 프로파일링 별도 필요 | 🟡 **재정의** |
| **A2** | PyneCore가 `strategy.exit trail_points/offset` 지원 | Phase -1 amendment로 H2+ 이연 확정 (#19 PR, §6 H1 MVP scope) | ✅ **N/A** (scope 축소) |
| **A3** | Alert 메시지 분류기 정확도 **>80%** | L3 v1: N=10 alert 100% 분류 + **discrepancy 자동 감지** (1건, i3_drfx #2). ADR-011 §2.1.3 condition-trace 구현 완료 | ✅ **강하게 실증** |

### 신뢰도 업데이트
- Phase -1 amendment 후 9/10 (ADR-011 §9)
- Week 1 A3 **v1 condition-trace 구현 + discrepancy 자동 감지**로 **9.2/10 소폭 상승**
- Week 2-3 bar 이벤트 루프 + 렌더링 범위 A 런타임 작동 확인 시 9.5/10 예상

---

## 4. Week 1 핵심 발견 5가지

### 💡 발견 1: Track 분포가 corpus 특성에 크게 좌우됨 (N=6 한계)

사용자 제공 5종 + PR #18 DrFX에서 S 50% / A 50% / M 0%. ADR-011 원 가정 "M 20~30%"가 N=6에선 관찰 불가 — alert 없는 indicator가 corpus에 없었기 때문. **Track M UX 우선순위 판단은 TV 15~20개 프로파일링(Day 6-7 별도 액션) 후 재평가**.

### 💡 발견 2: i3_drfx 렌더링 호출 79개 — Execution-First 원칙 수치 실증

DrFX Diamond Algo: box 25 + label 35 + line 16 + table 3 = **79 render scope A**. 동시 strategy/entry/exit 등 매매 집행 호출 = 0 (indicator 선언이라). ADR-011 통찰 2 "매매 로직은 전체의 4.6%" 원칙이 **이 스크립트 하나만으로도 실증**. 렌더링 범위 A(좌표 저장 + getter)가 필수이며 차트 실제 렌더링은 NOP으로 유지해도 매매 로직 추출 가능.

### 💡 발견 3: Pine v4 `study()` 자동 alias 감지 성공

i1_utbot은 Pine v4 문법 (`study("UT Bot Alerts", overlay=true)`). `_INDICATOR_ALIASES = {"indicator", "study"}` 처리로 Track A 자동 판정. **ADR-011 §7.2 "v4는 자동 업그레이드 안내"** 정책이 분류 단계에선 이미 투명하게 작동. (실제 실행 시엔 v4 → v5 변환 여전히 필요)

### 💡 발견 4: alert 메시지-조건 불일치 (i3_drfx #6)

`alertcondition(bear, title="BUY", message="BUY")` — 저자가 BUY 메시지를 bear 조건에 실수로 연결했거나, 의도적 signal semantic 반전. **메시지 전용 분류기는 long_entry로 오판**. ADR-011 §2.1.3 condition-trace (감싸는 if의 조건 변수를 AST 역추적) **Sprint 8b Tier-1 우선순위 근거**. 실사용 스크립트에서 10% 빈도 관측(1/10) — 무시 불가.

### 💡 발견 5: i3_drfx `request.security` 8회 — MTF 수요 입증

i3_drfx의 Multi-Timeframe 요청 8회. ADR-011 §2.5.2 MTF(Tier-5)가 인기 Pine 전략의 핵심 기능임을 실측으로 확인. **H1 MVP scope 밖**(#19 PR 확정)이지만 H2 진입 시 우선순위 상위 고정.

---

## 5. 라이선스 & 외부 자산 현황

| 자산 | 라이선스 | QB 사용 방식 | NOTICE | 상태 |
|:---|:---:|---|:---:|:---:|
| pynescript 0.3.0 | LGPL-3.0 | PyPI 의존성 (pinned) | ✅ `NOTICE` | 활성 |
| antlr4-python3-runtime 4.13.2 | BSD-3-Clause | pynescript transitive | (BSD 무고지 가능) | 활성 |
| PyneCore `transformers/persistent.py` | Apache 2.0 | 의미론 참조 이식 (코드 직접 copy 아님) | ✅ `NOTICE` 예정 항목 명시 | Week 1 완료 |

**격리 정책 엄수 확인:**

```bash
cd backend && rg -n "^import pynescript|^from pynescript" src/strategy/pine_v2/
# parser_adapter.py, ast_metrics.py, ast_classifier.py, alert_hook.py  (4 파일만)
```

**기존 `pine/` 모듈 touch 여부 확인:**

```bash
git diff --stat main -- backend/src/strategy/pine/
# (empty) — 0 lines changed
```

---

## 6. Week 2-3 후속 결정 (Sprint 8a 남은 범위)

### 다음 세션 Week 2 (1주 내 목표)

1. **Pine AST interpreter 스켈레톤** — `interpreter.py`. pynescript AST visit + scope 관리 + Assign/ReAssign/If 해석. **Day 8 통합 POC의 패턴 확장** (수작업 해석 → 체계적 visitor). var/varip 수식어 감지는 ast_extractor.VarDecl 재활용.
2. **bar-by-bar 이벤트 루프** — `event_loop.py`. OHLCV DataFrame 순회 + interpreter 호출 + PersistentStore begin/commit/rollback 관리
3. **Indicators bridge** — vectorbt/TA-Lib을 지표 계산용으로만 호출 (ADR-011 §2.0.3 분리 원칙). ta.sma/ta.ema/ta.atr/ta.crossover 등 8-10개 함수부터
4. **strategy.* 실행 핸들러** — `strategy.entry(id, direction, qty, limit, stop)` + `strategy.exit(limit, stop)` + `strategy.close`. **ast_extractor.StrategyCall로 추출된 args 재활용**. H1 MVP 범위 준수(trail_points/qty_percent/pyramiding H2+ 이연)

### Week 3 (Tier-0 완성)

4. **렌더링 범위 A 런타임** — `rendering/` 서브패키지. `box.new/get_top/get_bottom`, `line.new/get_price`, `label.new/set_x/set_y`, `table.new/cell` 좌표 저장 + getter. 차트 렌더링 NOP. i3_drfx 79 호출이 runtime 오류 없이 완주해야 함
5. **첫 E2E 실측**: s1_pbr (가장 단순 Track S)을 pine_v2로 실행 → 거래 목록 추출 → 기존 `pine/` 모듈 실행 결과와 **교차 검증**

### 선택 액션 (분리 가능)

- **Day 6-7: TV 공개 스크립트 15~20개 프로파일링** — Track 분포 본격 실측. A1 가정 재검증. ADR-011 §9 신뢰도 9 → 9.5로 상승 조건.
- **Bybit V5 API flag recheck** (Sprint 7a 후속) — 별도 Sprint

---

## 7. 커밋 & PR 요약 (이 PR에 포함됨)

| Day | Commit | 내용 |
|:---:|:---:|---|
| 1 | `fb9d318` | pynescript 0.3.0 scaffold + NOTICE + E2 baseline parity 회귀 (7) |
| 2 | `ec1175a` | AST 분류기 + Track S/A/M 판정 + structure report fixture (12) |
| 3 | `92a5af9` | Alert Hook v0 (24) |
| 4 | `3a5896f` | PersistentStore var/varip 런타임 (15) |
| 5 | `7352345` | Week 1 보고서 v1.0 |
| **6** | `4f278d8` | **Alert Hook v1 — condition-trace + discrepancy 자동 감지** (+5) |
| **7** | `725b035` | **AST content extractor — strategy kwargs + inputs + var decls + strategy.* calls** (21) |
| **8** | `7cc3225` | **L1 에러 경로 10 + L1→L7→L4 통합 POC 5** |
| 8b | (본 커밋) | 보고서 v1.1 갱신 (Day 6-8 반영) |

**총 변경:** 5 소스 모듈 + 6 테스트 파일 + 4 fixture JSON + NOTICE + README + 본 보고서
**총 테스트:** **99 pine_v2** (99/99 PASS) + 526 기존 회귀 green
**품질 게이트:** ruff ✅ · mypy ✅ (9 source files)

---

## 8. 참조

- [ADR-011 Pine Execution Strategy v4](011-pine-execution-strategy-v4.md)
- [ADR-011 Phase -1 amendment](https://github.com/woosung-dev/quantbridge/pull/19) (PR #19)
- [Phase -1 findings](../../.gstack/experiments/phase-minus-1-drfx/output/phase-1-findings.md)
- [pine-execution-architecture §2](../04_architecture/pine-execution-architecture.md#2-tier-05-구조)
- [pine_v2 README (라이선스 경계 정책)](../../backend/src/strategy/pine_v2/README.md)
- [NOTICE (LGPL/Apache 고지)](../../NOTICE)
