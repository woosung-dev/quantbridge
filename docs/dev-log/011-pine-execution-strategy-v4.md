# ADR-011: Pine Script 실행 전략 v4 — Alert Hook Parser + 3-Track Architecture

> **상태:** 확정 (신뢰도 8/10, Phase -1 실측 완료 전까지 일부 가정)
> **일자:** 2026-04-17
> **출처:** 50+ 턴 세션 (3-way evaluator + Gemini Deep Research + 5개 LLM 반박 + DrFX 실측)
> **관련:** ADR-003(exec 금지), ADR-004(AST 인터프리터 선택)
> **상위 문서:** [`docs/04_architecture/pine-execution-architecture.md`](../04_architecture/pine-execution-architecture.md)
> **세션 아카이브:** [`docs/superpowers/specs/2026-04-17-pine-execution-v4-design.md`](../superpowers/specs/2026-04-17-pine-execution-v4-design.md)

---

## 1. 컨텍스트

### 1.1 트리거

Sprint 7b QA(PR #16) 완료 직후, 사용자가 **LuxAlgo Trendlines-with-Breaks** Pine 스크립트를 QuantBridge에서 파싱 시도. `L6: 예상치 못한 토큰 LBRACKET('[')` 에러로 즉시 차단.

원인 분석 결과 현재 QB 파서가:
- 배열 리터럴 `['a','b','c']` 미지원
- `ta.pivothigh/pivotlow/variance`, `math.abs`, `switch` 표현식 미지원
- `line.new(...)` + method chaining 구조적 미지원
- `request.security` 멀티 타임프레임 미지원
- `array.*`, `box.*`, `label.*`, `table.*` 전면 미지원

즉 현대 Pine v5/v6 스크립트 상당수가 파서 첫 라인부터 차단되는 상태.

### 1.2 상위 질문

> **"TradingView Pine Script를 외부(QuantBridge)에서 백테스트 가능하게 하는 최선의 아키텍처는?"**

ADR-004에서 채택한 **AST 인터프리터**가 여전히 정답인가? 범용 IR 변환이나 Python transpile로 전환해야 하는가? LLM 기반 변환은?

### 1.3 세션 진화 (v0 → v5)

| 단계 | 내용 | 결론 |
|:---:|------|------|
| v0 | AST 인터프리터 재검토 질의 | 기반은 유지하되 상위 아키텍처 필요 |
| v1 | 3-way evaluator 조사 (Opus + Sonnet subagent + me) → **16개 아키텍처** 종합 | Tier-A/B/C/D/E 초기 구조 |
| v2 | Gemini Deep Research(11개 방안) + 5개 LLM 비교 | 4가지 운영 체크포인트 추가 |
| v3 | 반박 1차 8건 + 2차 8건 (총 16건 중 9건 수용) | KPI 현실화, vectorbt 충돌 인정 |
| v4 | **Alert Hook Parser + 3-Track** 수렴 | **세션 최대 통찰 — 본 ADR 핵심 결정** |
| v5 | DrFX Pine 실측 + LLM 변환 코드 평가 + BTC/USDT 1년 백테스트 | v4 가설 증명 시작 |

---

## 2. 결정 요약 (한 줄)

> **Pine Script를 "Execution-First" 원칙으로 있는 그대로 실행하되, `alert()`/`alertcondition()` 호출을 "개발자의 자발적 매매 신호 선언"으로 파싱하여 가상 `strategy()` 래퍼를 자동 생성하는 3-Track(S/A/M) 아키텍처를 채택한다.**

- **Track S** (20~30%): `strategy()` 선언 스크립트 → 네이티브 실행
- **Track A** (40~50%, 차별화 핵심): `indicator() + alert()` → **Alert Hook Parser** 자동 추출
- **Track M** (20~30%): `indicator()` alert 없음 → Variable Explorer 수동 지정

---

## 3. 결정적 통찰 3가지 (Must-Remember)

### 💡 통찰 1: `alert()`은 개발자의 자발적 매매 신호 선언

Pine 개발자는 TV에서 전략을 공유할 때 거의 항상 `alert()`나 `alertcondition()`을 사용한다. 그게 이미 "**이게 내 매매 신호다**"라는 **자발적 라벨 선언**이다.

**의미:** 매매 로직을 **추측**할 필요 없음. AST에서 alert 호출을 수집하고 메시지 파싱만 하면 결정론적으로 entry/exit 신호 추출 가능. LLM 환각 없이.

```pine
if longCondition
    alert("LONG entry at " + str.tostring(close), ...)  // ← 자동 추출 대상
```

### 💡 통찰 2: 매매 로직은 전체 Pine의 13% 이하 (Execution-First)

DrFX Diamond Algo 650줄 분해 실측:
- **매매 의사결정 코드: ~30라인 (4.6%)**
- 나머지 ~95%는 시각화/드로잉/대시보드

**의미:** Pine 전체를 100% 번역하려 하지 말고 **매매 의도만 추출**. 렌더링 객체(box/label/line)는 **좌표 저장 + getter만 지원**(범위 A), 실제 차트 렌더링은 NOP. 이게 "Execution-First" 원칙.

### 💡 통찰 3: 실측 없는 설계 5라운드 < 실측 1번

세션에서 v0~v4까지 5라운드 설계 후 실측 1회(DrFX LLM 변환 + BTC/USDT 1년 백테스트)로 얻은 정보가 이전 설계 전체보다 가치 있었음. 발견된 실제 버그 3개(SL 기준점, 부동소수점 ==, look-ahead)는 설계로는 못 잡았음.

**의미:** Phase -1 PyneCore E2E 실측을 **Sprint 8a 공식 착수 전에 반드시 완료**. 실측 결과가 이 ADR을 amend할 수 있다.

---

## 4. Tier 구조 (결정 채택 순위 + 추천도)

| Tier | 역할 | 추천도 | 주요 내용 |
|:---:|------|:---:|-----------|
| **0** | 공통 코어 | ⭐⭐⭐⭐⭐ | pynescript 포크 + PyneCore 이식 + bar-by-bar 이벤트 루프 + 렌더링 객체 범위 A |
| **1** | Alert Hook Parser ⭐ | ⭐⭐⭐⭐⭐ | 차별화 핵심. AST alert 수집 + 메시지 분류 + 가상 strategy 래퍼 + 3-Track 라우터 |
| **2** | Tier-0 자체 구현체 회귀 CI ([2026-04-18 amendment](#13-phase--1-실측-결과-부록-2026-04-18)) | ⭐⭐⭐⭐⭐ | Trust Layer 생명선. 비교 기준점: **QB Tier-0 구현체 vs pynescript AST + PyneCore `transformers/` 참조 이식**. 상대 오차 <0.1% MVP (기준점 변경, KPI 유지) |
| **3** | strategy() 네이티브 | ⭐⭐⭐⭐ | Track S 엔진. trail_points/offset + 분할 익절 |
| **4** | Variable Explorer | ⭐⭐⭐ | Track M Fallback. H1 Stealth엔 우선순위 낮음 |
| **5** | LLM 하이브리드 + MTF | ⭐⭐⭐ | 장기 지속 개선. Rule+LLM (Oxidizer 73% 패턴) |

상세 명세는 [`pine-execution-architecture.md`](../04_architecture/pine-execution-architecture.md) 참조.

---

## 5. 대안 비교 (왜 v4가 선택되었는가)

16개 아키텍처 중 상위 5개와 v4 대비:

| 대안 | 채택 여부 | 사유 |
|------|:--:|------|
| 순수 AST 인터프리터 (기존 ADR-004) | 🟡 **기반만 유지** | 커버리지 확장 비용 선형 이상 증가. Tier-0 핵심이나 단독으론 부족 |
| 바이트코드 VM | ❌ | 2~3개월 투자 대비 vectorbt+Numba가 이미 커버 |
| AST → Python src emit + exec | ❌ | ADR-003(exec 금지) 위반 + 디버깅 나쁨 |
| LLM 원샷 번역 | ❌ | IBM "Lost in Translation" 2.1~47.3% + 비결정성 + Trust Layer 파괴 |
| **Semantic Extraction DSL** | 🟡 **v4에 흡수** | 좋은 통찰이나 "추측" 기반 → Alert Hook으로 결정론화 |
| **v4 Alert Hook + 3-Track** | ✅ **채택** | 결정성 + 커버리지 + UX 투명성 동시 확보 |

---

## 6. 결과 (Consequences)

### ✅ 긍정적 결과

1. **Pine v5/v6 주요 스크립트 파싱 가능성 확대** — LuxAlgo/DrFX류 포함 Track A(40~50%) 자동 처리 기대
2. **Trust Layer 강화** — PyneCore 골든 오라클 기반 상대 오차 <0.1% 검증 CI
3. **투명성 UX** — 사용자에게 "이 스크립트는 이렇게 해석됐습니다" 1질문 UX
4. **결정성 유지** — LLM을 주경로가 아닌 Tier-5 보조로만 활용
5. **기존 자산 활용** — pynescript 포크(1~2주)로 ANTLR 6~12개월 포팅 회피

### 📏 H1 MVP scope (2026-04-18 amendment)

Phase -1 실측 종료 후 사용자 결정. H1 Stealth는 dogfood-first이므로 **치명 경로 최소화**:

| 요소 | H1 In-Scope | H2+ 이연 |
|------|:----------:|:--------:|
| 진입: `strategy.entry(long/short)` | ✅ | |
| 청산: `strategy.exit(limit=TP, stop=SL)` | ✅ | |
| 명시 청산: `strategy.close`, `strategy.close_all` | ✅ | |
| Trailing stop: `trail_points`/`trail_offset` | | ✅ (RTB/LuxAlgo 필수 기능이지만 H1 dogfood 범위 밖) |
| 분할 익절: `qty_percent` | | ✅ |
| 피라미딩: `pyramiding` | | ✅ |

**근거:** Phase -1 DrFX 실측에서 사용자 주력 전략 2개 모두 TP/SL만으로 재현 가능. 복합 exit 로직은 Sprint 8b~8c Tier-3 확장 단계에서 편성.

### ⚠️ 부정적 결과 / 제약

1. **Sprint 3개월(12주) 필요** — Sprint 8a-pre → 8d
2. **Track M(20~30%) 수동 UX** — H1 Stealth에선 미완성 가능
3. **`strategy.exit trail_points/offset` 구현 복잡도 높음** — RTB/LuxAlgo 필수이므로 Tier-3 난이도
4. **vectorbt 위치 재정립** — 전략 실행 엔진에서 **지표 계산 전용**으로 강등. 기존 `backend/src/backtest/engine/` 리팩토링 필요

### 🔄 후속 작업

- **Phase -1 (Sprint 8a-pre, 2주):** PyneCore E2E 실측 → 본 ADR의 가정 실증 또는 amendment
- **Sprint 8a (3주):** Tier-0 공통 코어 구축
- **Sprint 8b (3주):** Tier-1 Alert Hook Parser + Tier-3 strategy() 네이티브
- **Sprint 8c (2주):** Tier-2 검증 + Tier-4 Variable Explorer
- **Sprint 8d (2주):** Tier-5 LLM 하이브리드 + 베타 오픈

---

## 7. 기피 전략 (명시적 거부)

| 전략 | 거부 사유 |
|------|-----------|
| **PyneTS 포팅/참조** | AGPL-3.0 → QB는 SaaS이므로 네트워크 서비스 조항 자동 발동. Clean-room 설계 참조만 허용 |
| **PyneSys SaaS 영구 구독** | Vendor lock-in + QB 엔진과 호환 불가. 2026-04-18 Phase -1 실측에서 **PyneCore CLI(`pyne compile`)가 PyneSys 상용 API 의존성 확인** — 독립 오라클 불가. 대안: PyneCore 레포의 Apache 2.0 `transformers/` 모듈(`persistent.py` var/varip, `series.py`, `security.py` 등)을 **참조 이식**만 허용. NOTICE 파일 + 원본 헤더 유지 의무 |
| **LLM 원샷 번역 주경로** | IBM ICSE 2024: 상용 LLM 정확 번역률 2.1~47.3%. 비결정성 + 재현성 파괴 + Trust Layer 훼손 |
| **자체 ANTLR Pine v6 문법 6~12개월 포팅** | pynescript(LGPL) 포크 1~2주로 대체 가능. ROI 불명확 |
| **바이트코드 VM / LLVM JIT / MLIR / WASM** | vectorbt + Numba 이미 커버. 과대투자. 솔로 indie H1 Stealth 단계 부적합 |
| **렌더링 객체 완전 구현 (범위 B)** | Canvas/SVG 렌더링은 백테스트 무관. 엔지니어링 부담 5~10배. 범위 A(좌표 저장 + getter만) 엄수 |
| **TV 헤드리스 브라우저 자동 스크래핑** | TV ToS 회색지대 + 불안정. 내부 검증 골든 생성용 수동 간헐만 허용 |

---

## 8. ADR-003/004와의 관계

본 ADR-011은 **기존 결정의 상위 아키텍처**:

```
ADR-003 (2026-04-13): exec()/eval() 절대 금지 + 인터프리터 패턴 강제
   ↓ (기반 원칙)
ADR-004 (2026-04-15): AST 인터프리터 방식 선택 (Python 트랜스파일·DSL 매핑 기각)
   ↓ (구현 기반)
ADR-011 (2026-04-17): Alert Hook Parser + 3-Track 상위 아키텍처 ← 본 ADR
```

- **ADR-003 유지:** 여전히 exec/eval 금지. LLM이 생성한 Python을 exec하는 경로 일체 없음
- **ADR-004 확장:** AST 인터프리터가 Tier-0 기반이지만, 단독으론 커버리지 부족 → Tier-1 Alert Hook Parser가 상위에서 **매매 의도 추출 레이어** 담당
- **새로운 것 (ADR-011):**
  - `alert()` 파싱 → 가상 strategy() 래퍼 자동 생성
  - bar-by-bar 이벤트 루프 백테스터 (vectorbt는 지표 계산 전용으로 격리)
  - 렌더링 객체 런타임 범위 A (박스/라벨/라인 좌표 getter)
  - 3-Track 분류 라우터

---

## 9. 신뢰도 (Confidence)

**9/10** — Phase -1 실측 완료 (2026-04-18, PR #18). 상세: [§13 Phase -1 실측 결과 부록](#13-phase--1-실측-결과-부록-2026-04-18).

### 신뢰도를 낮추는 가정 (3가지)

1. **Track S/A/M 비율 20~30% / 40~50% / 20~30%** — TV 커뮤니티 스크립트 15~20개 프로파일링 전까지 추정치
2. **PyneCore가 `strategy.exit trail_points/offset` 지원** — RTB/LuxAlgo 필수 기능. 미지원 시 Tier-3 난이도 급상승
3. **Alert 메시지 분류기 정확도 > 80%** — JSON/키워드/자유 텍스트/한국어 혼재 실태 미확인

### 신뢰도를 올리는 근거 (4가지)

1. **DrFX 실측 완료** — 650줄 중 매매 로직 2줄, alert 7개 확인 → 통찰 1·2 실증
2. **PyneCore 공개 v6.4.2** — Apache 2.0, 121★, 활발. 참조 이식 가능
3. **pynescript v0.3.0** — LGPL, 88★, ANTLR4 기반. 파서 포크 가능
4. **Amazon Oxidizer PLDI'25 73% 동등성** — Rule+LLM 하이브리드의 실증 사례 (Tier-5 근거)

### Phase -1 실측 후 신뢰도 상승 근거 (2026-04-18 갱신)

- A2(상대 오차 <0.1% KPI 현실성): **반증** — LLM 변환본 단독으론 오라클 불가. 비교 기준점 변경으로 KPI는 유지(§4 Tier-2 참조)
- A3(LLM 변환 버그 3개 재현성): **강하게 실증** — 모델별 구조적 버그 상이, LLM 원샷 주경로 기각 근거 강화
- Track 비율·상대 오차 실측은 Sprint 8a 완료 시점에 추가 상승 여지 (→ 9.5/10)

---

## 10. 참조 자료

### 세션 내부
- [`docs/04_architecture/pine-execution-architecture.md`](../04_architecture/pine-execution-architecture.md) — 메인 아키텍처 명세
- [`docs/superpowers/specs/2026-04-17-pine-execution-v4-design.md`](../superpowers/specs/2026-04-17-pine-execution-v4-design.md) — 세션 전체 아카이브
- [`docs/04_architecture/pine-ecosystem-landscape.md`](../04_architecture/pine-ecosystem-landscape.md) — 13개 프로젝트 비교 (Phase B)
- [`docs/guides/pine-semantics-gotchas.md`](../guides/pine-semantics-gotchas.md) — 의미론 함정 가이드 (Phase B)
- [`.gstack/experiments/phase-minus-1-drfx/README.md`](../../.gstack/experiments/phase-minus-1-drfx/README.md) — Phase -1 실측 기록 (Phase B)

### 핵심 외부 참조
- [PyneCore (GitHub)](https://github.com/PyneSys/pynecore) — Apache 2.0, Tier-0 참조 대상
- [pynescript (GitHub)](https://github.com/elbakramer/pynescript) — LGPL, 파서 포크 대상
- [TradingView Pine Execution Model](https://www.tradingview.com/pine-script-docs/language/execution-model/)
- [Amazon Oxidizer PLDI'25](https://arxiv.org/abs/2412.08035) — Rule+LLM 73% 동등성
- [IBM Lost in Translation ICSE 2024](https://research.ibm.com/publications/lost-in-translation-a-study-of-bugs-introduced-by-large-language-models-while-translating-code) — LLM 원샷 2.1~47.3%

전체 Sources(40+ URL)는 Session Spec 참조.

---

## 11. Amendment History

| 날짜 | 사유 | 변경 |
|------|------|------|
| 2026-04-17 | 최초 작성 | 전체 초안 |
| **2026-04-18** | **Phase -1 실측 완료 (PR #18)** | §9 신뢰도 8→9, §12 blocker 2개 해소, §4 Tier-2 KPI 기준점 재정의, §6 H1 MVP scope 축소 명시, §7 PyneSys 거부 강화, §13 실측 부록 신규 |

---

## 12. 결정 대기 (Blockers)

본 ADR 실행에 앞서 남은 결정:

1. ~~**Sprint 7d vs Sprint 8a-pre 우선순위**~~ → **해소 (2026-04-18)**: Sprint 8a-pre 선착수 완료, Sprint 7d(OKX + Trading Sessions)는 Sprint 8a/8b 종료 후 H1 내 편성
2. ~~**PyneCore `trail_points/trail_offset` 지원 여부**~~ → **N/A (2026-04-18)**: H1 MVP scope 축소로 `trail_points`/`qty_percent`/`pyramiding` H2+ 이연 (§6 H1 MVP scope 참조)
3. **Pine 해석이 QB 진짜 차별점인가?** — H2 Build-in-Public 진입 전 외부 유저 5명 인터뷰 필요. H1 Stealth에선 본인 dogfood만으로 진행. (변경 없음)

---

## 13. Phase -1 실측 결과 부록 (2026-04-18)

**상세 리포트:** [`.gstack/experiments/phase-minus-1-drfx/output/phase-1-findings.md`](../../.gstack/experiments/phase-minus-1-drfx/output/phase-1-findings.md)
**실측 계획:** [`docs/superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md`](../superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md)
**관련 PR:** [#18](https://github.com/woosung-dev/quantbridge/pull/18) (main merge `0f6583d`)

### 13.1 핵심 수치 3가지

1. **파서 커버리지:** pynescript 0.3.0 **6/6 (100%)** vs 현재 QB 파서 **0/6 (0%)**
   - QB 파서 실패 단계별: lex 실패 2종 (i3_drfx 38KB, s3_rsid 6.5KB), normalize 실패 2종 (i1_utbot, s2_utbot), parse 실패 1종 (i2_luxalgo 배열 리터럴), stdlib 실패 1종 (s1_pbr)
   - **함의:** Tier-0 pynescript 포크 결정을 **최대 강도로 실증**. 자체 ANTLR 포팅 시나리오 완전 폐기.

2. **LLM 원샷 변환 수렴도 0:** 1H·4H 두 타임프레임 모두 4개 모델(Opus / Sonnet / GPT-5 / Gemini-flash-lite) 상이한 구조적 버그
   - GPT-5·Gemini: **진입 로직 자체 실패** (0 trades)
   - Opus·Sonnet: 승률 25~41% 편차, 수익률 -52% ~ -10% 편차
   - **함의:** ADR-011 §7 "LLM 원샷 번역 주경로" 거부 실증. Tier-5 Rule+Verify 보조 위치 재확인.

3. **PyneCore 독립 오라클 불가:** PyneCore 런타임(Apache 2.0)은 OK지만 Pine→Python 변환기는 `pyne compile --api-key`로 PyneSys 상용 API($8-45/mo) 호출 요구
   - **함의:** PyneSys SaaS 구독 영구 거부(§7) + PyneCore `transformers/` 모듈 참조 이식 경로 확정(§4 Tier-2)

### 13.2 Phase -1 가정 3개 판정

| 가정 (plan §7) | 판정 | 근거 |
|------|:--:|------|
| A1: PyneCore `trail_points/trail_offset` 지원 | **N/A** | H1 MVP scope 축소 (§6 H1 MVP scope 참조) |
| A2: 상대 오차 <0.1% MVP KPI 현실성 | ❌ **반증** | LLM 단독 대비 불가. 비교 기준점 변경 (QB Tier-0 vs pynescript AST + PyneCore transformers 이식본) |
| A3: LLM 변환 버그 3개 재현성 | ✅ **강하게 실증** | 모델별 전혀 다른 구조적 버그 패턴 |

### 13.3 후속 반영

- **이 amendment:** 상기 5개 소수정 반영
- **Sprint 8a Day 1+:** Tier-0 pynescript 포크 착수 (본 ADR Phase 1 계획)
- **Sprint 8b+ Tier-2 CI:** 비교 기준점 변경 반영 (§4 참조)
- **Day 4-5 (선택):** TV 공개 스크립트 15~20개 alert 패턴 프로파일링 — Sprint 8b Tier-1 Alert Hook Parser 구현 전 필수
