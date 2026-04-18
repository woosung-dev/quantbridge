# Phase -1 Findings — Day 1-3 실측 최종 리포트

> **일자:** 2026-04-18
> **브랜치:** `experiment/phase-minus-1-drfx`
> **plan:** [`docs/superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md`](../../../docs/superpowers/plans/2026-04-18-phase-minus-1-measurement-plan.md)
> **ADR:** [ADR-011 Pine Execution Strategy v4](../../../docs/dev-log/011-pine-execution-strategy-v4.md)

---

## 🎯 한 줄 권고

> **CONTINUE to Sprint 8a (Tier-0 pynescript 포크 착수). ADR-011 본문은 유지. H1 MVP scope 확정(trail_points/qty_percent/pyramiding → H2+ 이연). Tier-5 LLM은 보조 전용 재확인 (원샷 변환은 프로덕션 불가).**

---

## 1. 핵심 발견 3가지

### 💡 발견 1: pynescript **6/6** vs 현재 QB 파서 **0/6**

| 도구 | 커버리지 | 의미 |
|------|:--:|------|
| **pynescript 0.3.0** | **6/6 (100%)** | Pine v5/v6 주요 구문 전부 AST 생성. Tier-0 포크 대상 확정. LGPL 파일 단위 copyleft 주의 |
| **현재 QB 파서** | **0/6 (0%)** | lex/normalize/parse/stdlib 전 단계에서 실 사용자 스크립트 처리 불가 |

실패 단계별 분해(QB 파서):
- `lex` 실패: i3_drfx (38.9KB, ta.* 다수), s3_rsid (6.5KB)
- `normalize` 실패: i1_utbot (1.7KB), s2_utbot (2.7KB)
- `parse` 실패: i2_luxalgo (3.9KB, 배열 리터럴 `[...]`)
- `stdlib` 실패: s1_pbr (828B, 가장 멀리 갔으나 미지원 함수)

**결정적 함의:** ADR-011 **Tier-0 pynescript(LGPL) 포크** 결정 정당성 **최대 강도로 실증**. 파서 자체 ANTLR 6~12개월 포팅 시나리오 완전 폐기.

### 💡 발견 2: LLM 단독 원샷 변환은 오라클 대체 **불가** (1H + 4H 모두)

사용자가 주로 사용하는 1H + 4H 두 타임프레임 모두 매트릭스.

**1H (8,760 bars):**

| 엔진 | 모델 | 수익률 | 거래수 | 승률 |
|:----:|------|--------:|:-----:|:-----:|
| E4 | Claude Opus 4.7 | -40.80% | 145 | 25.52% |
| E5 | Claude Sonnet 4.6 | -52.21% | 100 | 41.00% |
| E6 | GPT-5 | 0.00% | **0 (진입 실패)** | 0% |
| E7a | Gemini 3.1-pro-preview | — | ❌ 429 quota | — |
| E7b | Gemini 3.1-flash-lite | -0.10% | **0 (진입 실패)** | 0% |

**4H (2,190 bars):**

| 엔진 | 모델 | 수익률 | 거래수 | 승률 |
|:----:|------|--------:|:-----:|:-----:|
| E4 | Claude Opus 4.7 | -10.13% | 37 | 32.43% |
| E5 | Claude Sonnet 4.6 | -20.51% | 18 | 50.00% |
| E6 | GPT-5 | 0.00% | **0 (진입 실패)** | 0% |
| E7a | Gemini 3.1-pro-preview | — | ❌ 429 quota | — |
| E7b | Gemini 3.1-flash-lite | -0.10% | **0 (진입 실패)** | 0% |

**수렴도 0.** 4개 중 2개가 진입 로직 자체 미구현. 나머지 2개도 승률 16~18%p 차이. 두 TF 모두 같은 패턴 → 타임프레임 변경으로는 LLM 수렴 문제 해결 안 됨.

### 💡 부산물: 타임프레임에 따른 DrFX 전략 자체 성능 차이

작동한 2개 엔진(Opus, Sonnet)에서 관찰되는 공통 패턴:

| 엔진 | 1H | 4H | delta |
|:----:|------:|------:|:-----:|
| E4 Opus | -40.80% | -10.13% | **+30.66%p** |
| E5 Sonnet | -52.21% | -20.51% | **+31.70%p** |

**시사점 (본 실측의 부산물):**
- 사용자가 선호하는 **4H가 1H보다 약 30%p 유리.** 145 trades × 0.1% × 2 = 약 29% 수수료 손실을 4H에서는 37 trades × 0.1% × 2 = 약 7.4%로 축소. 노이즈 감소와 함께 주요 요인.
- 하지만 두 TF 모두 **절대 수익률 음수** — DrFX의 TP 2:1 × 승률 32%는 구조적 적자 (이전 세션 아카이브 §5 확인과 일치). TV 공유 전략의 실효성 자체에 의문. Sprint 8+ dogfood 단계에서 **파라미터 튜닝 또는 전략 선택 단계 UX** 중요성 부각.

**결정적 함의:**
- **Tier-5 LLM 하이브리드** 결정(Rule+Verify) **옳음**
- LLM 원샷은 프로덕션 백테스트 엔진으로 부적합
- ADR-011 §7 기피 전략 "LLM 원샷 번역 주경로 (2.1~47.3% 정확도)" **실증**. 오히려 Phase -1 실측에서 본 것은 "실행 가능성 자체가 불확실" — 측정 정확도 이전의 문제

### 💡 발견 3: PyneCore는 **독립 오라클 불가** (PyneSys 상용 API 의존)

원안 `E1 PyneCore 주 오라클`은 가정에 오류 있음:
- **PyneCore 런타임**(Apache 2.0): Python 코드를 Pine 의미론(var/varip/series)으로 실행. OK.
- **Pine → Python 변환기**: `pyne compile --api-key` 로 **PyneSys 상용 API($8-45/mo)** 호출. 오픈소스 단독 사용 불가.

**결정적 함의:**
- 세션 결정 `PyneSys SaaS 구독 거부` 유지 → PyneCore는 "Python AST transformer + 런타임" 역할로만 활용
- Tier-0 공통 코어에서 **PyneCore의 `transformers/` 모듈**(`persistent.py` var/varip, `series.py`, `security.py` 등)을 **참조 이식**하여 QB 자체 Pine-Python 변환 파이프라인 구축

---

## 2. Phase -1 가정 판정

| 가정 (plan §7) | 판정 | 근거 |
|------|:--:|------|
| ~~A1: PyneCore `trail_points/trail_offset` 지원~~ | **N/A** | H1 scope 축소(2026-04-18 사용자 결정) — MVP는 TP/SL/LONG/SHORT만. trail_points/qty_percent/pyramiding H2+ 이연 |
| **A2:** 상대 오차 <0.1% MVP KPI 현실적 | ❌ **반증** | LLM 4개 수익률 범위 **-52.21% ~ 0%p**. 오라클 없이는 KPI 측정 자체 불가. 오라클 확보 경로 재설계 필요 |
| **A3:** LLM 변환 버그 3개(SL 기준점/float==/look-ahead) 재현성 | ✅ **강하게 실증** | 모델별로 **전혀 다른 구조적 버그**. E6/E7b는 진입 로직 자체 실패, E5는 승률 41% vs E4 25% |

**종합:** A2 반증은 ADR-011 원안의 "KPI 단계별(MVP <0.1% → v1.0 <0.01%)"을 **LLM 단독 대비가 아닌 Tier-0 자체 구현체 vs pynescript 자체 AST** 비교로 전환할 필요 있음. 즉 KPI 유지하되 비교 기준점 변경.

---

## 3. ADR-011에 대한 영향

### 유지 (변경 불필요)

- **Tier 0~5 구조 전체**
- **3-Track(S/A/M) 분류**
- **Alert Hook Parser 차별화 전략**
- **범위 A/B 구분**
- **기피 전략 (PyneTS AGPL / LLM 원샷 / ANTLR 자체 포팅 / 바이트코드 VM 등)**
- **12주 로드맵 (Sprint 8a-pre → 8d)**

### Amendment 필요 (Day 6-7 공식 amendment 세션에서)

1. **§5.5 MVP scope 명시화:**
   - H1 MVP in-scope: `strategy.entry(long/short)`, `strategy.exit(limit=TP, stop=SL)`, `strategy.close/close_all`
   - H2+ 이연: `trail_points/trail_offset`, `qty_percent` (분할익절), `pyramiding`
2. **§2.2 Tier-2 KPI 재정의:**
   - `상대 오차 <0.1%` 비교 기준을 "LLM 변환본 vs PyneCore"가 아닌 **"QB Tier-0 구현체 vs pynescript AST + PyneCore 런타임 참조 이식"**으로 명시
3. **§5.5 오라클 확보 경로 구체화:**
   - PyneSys 상용 API 구독 영구 거부
   - PyneCore의 Apache 2.0 transformers 참조 이식
   - TV 수동 스폿체크는 분기 1회 샘플 검증에 한정(과대 기대 금지)
4. **§9 신뢰도 갱신:** 8/10 → 9/10 (A2·A3 실증 통해)
5. **§12 Blockers 해소:**
   - ~~PyneCore `trail_points` 지원~~ → N/A (scope 축소)
   - `Pine 해석이 QB 진짜 차별점?` → H2 진입 전 외부 5명 인터뷰 여전히 필요 (변경 없음)

### 새로 추가 권장

- **§13 Phase -1 실측 결과 (신규 부록):** 본 리포트 링크 + 핵심 수치 3개 인용

---

## 4. 스크립트 매트릭스 (5 스크립트 E2/E3 결과 요약)

| # | Track | 난이도 | E2 pynescript | E3 QB 파서 | E4 Opus 실행 |
|:--:|:---:|:---:|:---:|:---:|:---:|
| S1 | strategy | 🟢 쉬움 | ✅ 24 types / 231 nodes | ❌ stdlib | (I3만 심층) |
| S2 | strategy | 🟠 중간 | ✅ 27 types / 734 nodes | ❌ normalize | (I3만 심층) |
| S3 | strategy | 🔴 어려움 | ✅ 32 types / 1,245 nodes | ❌ lex | (I3만 심층) |
| I1 | indicator | 🟢 쉬움 | ✅ 25 types / 587 nodes | ❌ normalize | (I3만 심층) |
| I2 | indicator | 🟠 중간 | ✅ 30 types / 822 nodes | ❌ parse | (I3만 심층) |
| **I3** | **indicator** | 🔴 **어려움** | ✅ **40 types / 10,289 nodes** | ❌ **lex** | **심층 — §2 참조** |

---

## 5. 비용 + 시간 결산

| 항목 | 계획 | 실제 |
|------|------|------|
| 소요 시간 | Day 1-3 (2-3일) | Day 1-2 집중 실행 (~4h) + Day 3 리포트 작성 |
| LLM API 비용 | ~$0.30 예상 | ~$0.50 실제 (Anthropic + OpenAI, Google은 무료 quota 사용) |
| 인프라 비용 | 0 | 0 (uv + 로컬) |
| 외부 서비스 | 없음 | 없음 (PyneSys 구독 없음) |

---

## 6. Day 4+ 후속 액션

| 항목 | 권고 |
|------|------|
| Day 4-5: TV 공개 스크립트 15~20개 alert 패턴 프로파일링 | **Sprint 8b Tier-1 Alert Hook Parser 구현 전에 필수** — 시간 배분 존중 |
| Day 6-7: ADR-011 amendment 세션 | §3의 5개 항목 반영 |
| Day 8-10: Sprint 8a 착수 (pynescript 포크 초기) | **즉시 착수 권고** — Phase -1 근거 강력 |
| TV 수동 스폿체크 1건 (I3 1H 최근 30일) | **선택 사항** — 사용자 여유 시점에 수행. Phase -1 결론 이미 확보 |

---

## 7. 한 줄 결론 (재차 강조)

**"pynescript 6/6 vs QB 파서 0/6" 한 데이터포인트만으로도 Tier-0 포크 착수 조건 충족. LLM 단독 원샷은 프로덕션 불가 (발견 2)를 추가로 확보 — 자연스럽게 Tier-5 Rule+Verify 보조 위치 재확인. ADR-011 본문 유지, 5개 작은 amendment만.**
