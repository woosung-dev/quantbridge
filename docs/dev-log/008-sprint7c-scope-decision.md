# Sprint 7c: FE 따라잡기 — 스코프 결정 기록

> **작성일:** 2026-04-17
> **작성 세션:** /office-hours (gstack skill, session 12, inner_circle tier)
> **상태:** ✅ 구현 완료 (2026-04-17)
> **구현 브랜치:** feat/sprint7c-strategy-ui
> **관련 plan:** [`docs/superpowers/plans/2026-04-17-sprint7c-strategy-ui.md`](../superpowers/plans/2026-04-17-sprint7c-strategy-ui.md)

---

## 배경

Sprint 6(자동 집행 + Kill Switch + AES-256) + Sprint 7a(Futures + leverage/margin_mode + leverage cap)로 BE는 **524 tests green**까지 도달. 반면 FE는 Sprint 6에서 만든 `/trading` read-only 3 panel(Orders/ExchangeAccounts/KillSwitch)뿐이고 Strategy CRUD는 Sprint 3 API만 있고 UI 부재.

**Retro 지적:** FE/BE 격차가 **누적 부채 1위**. Sprint 7b(다음 BE 증분) 시작 전에 FE 부채를 더 쌓지 않는 게 목적.

## 스코프 후보 4개

office-hours 시작 시점에 user가 나열한 candidate:

1. 주문 생성 폼 (leverage/margin_mode 입력 포함)
2. 전략 CRUD UI (Sprint 3 API만 있고 UI 없음)
3. ExchangeAccount 등록 UI
4. OrderList 상세 + 필터

## 결정: **Strategy CRUD UI 단독** (후보 2번)

**나머지 3개는 Sprint 7c 밖**, Sprint 8+에서 재평가.

### 결정 근거 (office-hours Q5 직접 인용)

> **User 발언:** "auto test로 돌렸어서 그래도 크게 문제 없었어.. 3번 방식(Pine 전략 이터레이션)을 통해서 테스트를 많이 해볼것 같기는 해.."

이 한 문장이 scope 결정을 완전히 가름:

| 후보                     | 현재 감내 수단                                                           | 미래 pain                                          | 결론                       |
| ------------------------ | ------------------------------------------------------------------------ | -------------------------------------------------- | -------------------------- |
| 1. 주문 생성 폼          | curl payload로 leverage/margin 변경 테스트 가능 (Sprint 7a T4 실제 수행) | 낮음                                               | **Out**                    |
| 2. Strategy CRUD UI      | `curl + JSON escape + auth token`로 회당 3~10분 마찰                     | **높음** — 앞으로 Pine 이터레이션을 많이 돌릴 예정 | **In (primary)**           |
| 3. ExchangeAccount UI    | 1회 셋업이라 curl/psql로 감내 가능                                       | 낮음 (key 교체는 드뭄)                             | **Out**                    |
| 4. OrderList 상세 + 필터 | pgAdmin/logs/auto test로 커버됨 (지난 Sprint 실제 pain 없었음)           | 중간                                               | **Out** (당장 블로커 아님) |

## Stage 2 Design Assets 재채택 (2026-04-17 plan-design-review 결과 반영)

**배경:** office-hours 세션이 DESIGN.md + `docs/prototypes/` + `INTERACTION_SPEC.md` 등 Stage 2(2026-04-14 확정) 자산을 참조하지 않고 진행. plan-design-review에서 Design Completeness 3/10로 채점됨. 아래 자산을 **Sprint 7c 구현의 시각·인터랙션 reference**로 채택한다.

| 자산                 | 경로                                      | Sprint 7c 구현 역할                                                                 |
| -------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------- |
| DESIGN.md            | `/DESIGN.md`                              | 색상·타이포·간격 CSS 토큰 SSOT. 하드코딩 금지, 기존 변수 재사용                     |
| 전략 목록 프로토타입 | `docs/prototypes/06-strategies-list.html` | `/strategies` 페이지 layout + App Shell 패턴                                        |
| 전략 편집 프로토타입 | `docs/prototypes/01-strategy-editor.html` | `/strategies/[id]/edit` 편집 페이지 — 탭(코드/파싱/메타데이터) + 에디터 + 분석 패널 |
| 전략 생성 프로토타입 | `docs/prototypes/07-strategy-create.html` | `/strategies/new` — 3-step 위저드                                                   |
| 인터랙션 명세        | `docs/prototypes/INTERACTION_SPEC.md`     | `@monaco-editor/react`, react-hook-form, 실시간 파싱 구현 방식                      |

## 기술 결정 3가지

| #   | 질문                                    | 결정                                                                          | 이유                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| --- | --------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Q1  | Monaco editor vs Textarea               | **writing-plans 세션에서 재결정 (open)**                                      | Stage 2 프로토타입(`01-strategy-editor.html`)과 `INTERACTION_SPEC.md`가 `@monaco-editor/react`를 이미 채택. office-hours에서 내가 "Pine tokenizer 블랙홀"로 Textarea 대체 결정한 건 Stage 2 자산 미확인 상태의 판단이었음. **Pine syntax highlighting 부재는 사실이지만, 일반 텍스트 Monaco(한 줄 번호 + monospace + 기본 하이라이트 없음) 사용은 Textarea보다 품질 다운그레이드 없이 동일 기간 내 가능.** writing-plans가 Monaco 범위(highlight 없음 vs 최소 tokenizer vs 풀 하이라이트)를 task 분해 단계에서 결정한다. |
| Q2  | 편집 UI: Drawer 통합 vs 별도 라우트     | **별도 라우트** (`/strategies` + `/strategies/new` + `/strategies/[id]/edit`) | Stage 2 프로토타입이 이 3개 라우트로 이미 확정. Drawer 패턴은 프로토타입과 불일치 → 폐기. 3-step create wizard도 `07-strategy-create.html`대로 채택                                                                                                                                                                                                                                                                                                                                                                      |
| Q3  | Inline backtest vs 별도 페이지 navigate | **별도 페이지 navigate** (`/backtest?strategy_id=`)                           | Celery polling UI가 별도 대시보드로 팽창 위험. 기존 `/backtest` 페이지 재사용.                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| Q4  | Strategy versioning 도입                | **도입 안 함**                                                                | BE schema 변경(StrategyVersion 테이블) 필요 → P4 time box(1~1.5주) 위반. Sprint 7c는 **pure FE sprint**.                                                                                                                                                                                                                                                                                                                                                                                                                 |

## Premises (office-hours Phase 3, 6개 전부 동의 — design-review 반영 후 일부 개정)

- **P1** Sprint 7c primary = Strategy CRUD UI. 다른 3개는 out.
- **P2 (개정)** 핵심 = Stage 2 프로토타입 3개(`06-strategies-list.html` + `01-strategy-editor.html` + `07-strategy-create.html`)를 구현 reference로 3개 라우트(`/strategies`, `/strategies/new`, `/strategies/[id]/edit`) 분리 구현. 편집 에디터는 `@monaco-editor/react` 기본 채택(세부 하이라이트 범위는 writing-plans 결정). 전략↔계정 바인딩/배포는 차기.
- **P3** 주문 폼 + OrderList 필터 + ExchangeAccount UI는 Sprint 7c 밖. 현재 `curl/psql/auto test`로 감내 가능.
- **P4** Sprint 7c = **1~1.5주 time box**. Sprint 7b 시작 전 merge. 넘어가면 scope 잘라냄.
- **P5** 기존 `/trading` read-only 3 panel 유지. `/strategies`·`/strategies/new`·`/strategies/[id]/edit` 신규 라우트로 추가. 기존 refactor 없음.
- **P6** Landscape search 스킵 (solo 프로젝트 FE scope 결정에서 가치 낮음).

> **P2 개정 이유:** office-hours 세션의 P2 원안("Textarea + Parse 프리뷰 + Drawer")은 Stage 2 프로토타입/DESIGN.md 미확인 상태 결정. plan-design-review에서 Stage 2 자산 존재 확인 후, 프로토타입 확정 설계(3 라우트 + Monaco + 3-step wizard)로 재정렬.

## Approach 비교 (탈락 기록 — design-review 후 상태)

### Approach A (원래 "Minimal Viable", **Stage 2 반영 후 개정**)

- 원안: `/strategies` 단일 라우트 + Sheet drawer + Textarea + Parse 버튼
- 개정: `/strategies` + `/strategies/new`(3-step wizard) + `/strategies/[id]/edit`(Monaco 탭 UI) 라우트 분리. Stage 2 프로토타입 3개 재사용. Monaco 범위는 writing-plans 결정.
- 개정 이유: plan-design-review (2026-04-17) — Stage 2 자산 재채택

### Approach B (탈락): 원래 "Ideal, Monaco + inline backtest"

- 원래 탈락 이유: Pine 문법 하이라이트 블랙홀 + inline backtest UI 팽창 리스크.
- 개정 후 상태: Monaco 자체는 이미 Stage 2 결정이라 A에 통합됨. inline backtest(Celery polling UI)만 여전히 탈락 — Sprint 7c 밖.

### Approach C (탈락): Strategy versioning (commit-style)

- **이유:** BE schema 변경 필요. P4 time box 명백히 위반. Sprint 8+에서 "A 돌려보니 version 필요하다"는 관찰 시 re-propose 여부 재검토.

## 워크플로우: 경량 3-Step (Sprint 7a 선례 따름)

1. **gstack `/office-hours` 스코프 결정** → 이 문서 ✅
2. **gstack `/plan-design-review` (Step 0 lite)** → Stage 2 자산 재채택 반영 ✅ (2026-04-17)
3. **`/superpowers:writing-plans` 별도 세션 호출** → `docs/superpowers/plans/2026-04-17-sprint7c-strategy-ui.md` 생성 예정 (대기). 본 ADR의 "Stage 2 Design Assets 재채택" 섹션과 개정된 P2·Q1·Q2를 input으로 사용
4. **(선택) gstack `/plan-design-review` 정식 7-pass** → writing-plans 출력물을 대상으로 empty/error/responsive/a11y 등 세부 design gap 확인
5. **`/superpowers:subagent-driven-development` 실행** → T1~Tn task 단위 구현

> **주의:** gstack office-hours 산출물과 superpowers writing-plans 산출물은 **스킬 체계가 다르다**. office-hours는 scope/requirement 결정까지, implementation plan은 반드시 `/superpowers:writing-plans` 세션에서 생성해서 `docs/superpowers/plans/`에 배치한다. Sprint 7a 선례 참조.

## 선행 Assignment (구현 전 반드시)

T1 착수 전에 Pine 소스 1개를 **현재 curl 방식**으로 등록·Parse·백테스트까지 직접 돌리고 **스텝별 초단위 시간 측정**. Sprint 7c 완료 후 FE로 같은 3스텝을 돌렸을 때 몇 배 빨라졌는지 정량 평가 지표로 사용.

## 외부 demand evidence 메모 (Red flag)

이 sprint의 demand는 "메이커 본인이 앞으로 많이 쓸 것"이라는 **예측형** demand. 외부 유저 없음. Sprint 7b+ 수익화 단계에서 외부 유저 demand evidence **별도 확보 필요** (office-hours Phase 2A red flag self-check).

## 관련 자산

### 프로젝트 내부 (Stage 2 Design System — Sprint 7c가 반드시 준수)

- [DESIGN.md](../../DESIGN.md) — 색상·타이포·간격 토큰 SSOT (2026-04-14 확정)
- [docs/prototypes/06-strategies-list.html](../prototypes/06-strategies-list.html) — `/strategies` reference
- [docs/prototypes/01-strategy-editor.html](../prototypes/01-strategy-editor.html) — `/strategies/[id]/edit` reference (Monaco)
- [docs/prototypes/07-strategy-create.html](../prototypes/07-strategy-create.html) — `/strategies/new` 3-step wizard reference
- [docs/prototypes/INTERACTION_SPEC.md](../prototypes/INTERACTION_SPEC.md) — `@monaco-editor/react` + react-hook-form + 실시간 파싱 인터랙션 스펙

### 선행 sprint 자산

- Sprint 6 design doc: [`docs/01_requirements/trading-demo.md`](../01_requirements/trading-demo.md)

### User-local (참조용, 프로젝트 미커밋)

- office-hours 원본 design doc: `~/.gstack/projects/quant-bridge/woosung-feat-sprint7a-futures-design-20260417-133825.md`
- Claude plan file: `~/.claude/plans/sprint-7a-lazy-giraffe.md`
- **Sprint 28 office-hours 재진행 design doc** (2026-05-04): `~/.gstack/projects/quant-bridge/woosung-stage-h2-sprint28-comprehensive-design-20260504-173422.md`

---

## 2026-05-04 office-hours Addendum (Sprint 28 Step 1)

> **재진행 근거:** Sprint 7c 답 (Q4/Q5) 이 dogfood 3개월 누적 (Sprint 12-27, self-assess 추세 3→6→8→9→8) 결과로 부분 무효화. Sprint 28 진입 시점 narrowest wedge / observation / demand reality 재정의.

### 무효화된 답

| 항목                   | 처음 답 (2026-04-17)                                          | 새 답 (2026-05-04)                                                                                                                                                      |
| ---------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Q4 narrowest wedge** | "Strategy CRUD UI 단독" — Pine 이터레이션 curl 마찰 제거 우선 | **BL-141 + BL-140b + BL-004 완료 = Beta 진입** (보수적, evidence-backed). Strategy CRUD 만으로는 외부 노출 불가 (BL-140/141 부재로 데모 자체 불완전)                    |
| **Q5 observation**     | "curl/psql 감내로 demand 수행 가능"                           | **Auto-Loop 자동화 견고성 (26h+ 무중단 + dispatch rate 1.0/min + 5 sessions 동시 평가)** = 외부 노출 가능 핵심 신뢰 지표. curl/psql 감내 → 자동화 필수성 영구 규칙 승격 |
| **Q1-indie 변형**      | "메이커 본인이 앞으로 많이 쓸 것" (외부 demand 0 인정)        | **본인 dogfood 만족도 정량화 — system 8.5 / UX 6.5 / 종합 8.0** (Sprint 27 시점). system≡stable ≠ UX≡complete 분리 측정. dual metric 정의에 inherit                     |

### 4 신규 도메인 부상 (dogfood evidence)

처음 office-hours 시점에는 미존재. Sprint 12-27 dogfood 일지 8개 (2026-04-25 ~ 2026-05-04) evidence 로 부상:

1. **WebSocket Stability** (BL-001 / BL-011-016 6항목) — Sprint 12 metrics 정의 (qb_ws_orphan_buffer_size / reconcile_skipped / duplicate_enqueue / reconnect_total) + Sprint 27 26h+ 무결 검증 (reject 7 고착)
2. **Auth Trust Layer** (15 ADR + commit-spy) — Sprint 13 OrderService outer commit broken bug (Sprint 6 패턴 재발, 1185 BE tests 전부 통과인데 production bug) + LESSON-004 set-state-in-effect 차단 + Sprint 12 codex G0~G4 6 게이트
3. **Auto-Loop 자동화** (Sprint 27 §0.5 first run) — Beat scheduler `due_count=1→3→5` 즉시 인식 + Worker dispatch + ccxt + Bybit Demo end-to-end 무결. Q5 의 "curl 감내" 가 아니라 "자동화 필수성" 으로 영구 규칙 승격
4. **Multi-account / symbol / timeframe Live Trading** (Sprint 26 PR #100) — 두 ExchangeAccount 동시 active + BTC/SOL 동시 (5/5 limit) + 1m/5m/15m/1h timeframe 혼합

### 4 premises (Phase 3, 모두 동의)

1. **P1 — narrowest wedge:** BL-141+140b+004 완료 = Beta 진입. 다른 BL (BL-001/002/003 등) 은 Beta 후 Phase 2 sprint 처리.
2. **P2 — Auto-Loop 필수성 영구 규칙:** 26h+ 무중단 = 외부 노출 가능 핵심 신뢰 지표.
3. **P3 — dogfood self-assess 3축 분리:** system / UX / 종합 분리 측정 → dual metric inherit.
4. **P4 — Trust ≥ Scale > Monetize 직선 경로:** Sprint 27 → Sprint 28 → Beta open. Phase 2/3 deferred.

### Beta open path 결정 (Phase 4 Recommended Approach)

**Beta path A1 — 자연 시간 1-2주 + Day 7 dual metric 통과 시 Beta open** (Approach A, 추천도 9/10)

- Sprint 28 Slice 2/3/4 완료 → dogfood Day 5-7 자연 사용 → dual metric 통과 → Beta open 결정
- 메모리 BL-005 trigger + "Sprint 끊지 말 것" + "Trust ≥ Scale > Monetize" 모두 정합

### Sprint 28 Sprint type 정책 (영구 규칙 후보)

본 Addendum 자체가 **Sprint 28 메타-방법론 정책 4종** 의 첫 검증 케이스:

1. **Sprint type 분류 (kickoff 의무)** — A 신규 / B BL fix risk-critical / C dogfood hotfix / D docs only
2. **office-hours 재진행 (Step 0) 의무** — Q4/Q5 답 부분 무효화 시 (3개월+ 경과 + dogfood 누적)
3. **dual metric (sprint 종료) 의무** — self-assess + 신규 BL count + 기존 P0 잔여 divergence 검출
4. **Era 1 (Sprint 1-12) brainstorming 패턴 회복** — Era 2 (13-27) 의 BL 3배 + codex P1 42건 누적 회피

Sprint 28 종료 + dual metric 통과 시 → Phase C.1 sprint-template inherit + `.ai/project/lessons.md` 또는 `.ai/common/global.md` 승격 검토.

### Sprint 28 office-hours design doc 본체

상세 (Approach 비교 + Open Questions + Assignment + What I noticed): `~/.gstack/projects/quant-bridge/woosung-stage-h2-sprint28-comprehensive-design-20260504-173422.md`

## 실행 결과 (2026-04-17)

- **Monaco Q1 최종 결정:** Minimal Pine Monarch tokenizer (writing-plans 세션 decision). 반나절 투자, keyword/function/string/number/comment 5색.
- **UI primitives:** shadcn/ui Nova preset (Base UI 기반) + sonner. 12 컴포넌트 (Button/Card/Tabs/Dialog/Select/Input/Form/DropdownMenu/Badge/Label/Textarea/Sonner). ADR 009 참조(form.tsx는 예외적으로 radix-ui Slot+Label 사용).
- **Delete 409 fallback:** `strategy_has_backtests` 감지 시 다이얼로그가 "삭제 → 보관 제안"으로 phase 전환.
- **localStorage draft:** Wizard 중단 복원 auto-save (design review Pass 1 P7-1).
- **AI Slop 회피:** Step 1 method select를 asymmetric 1 primary + 2 chips로 재설계 (Pass 4).
