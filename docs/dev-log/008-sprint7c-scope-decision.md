# Sprint 7c: FE 따라잡기 — 스코프 결정 기록

> **작성일:** 2026-04-17
> **작성 세션:** /office-hours (gstack skill, session 12, inner_circle tier)
> **상태:** scope 결정 완료, implementation plan 작성 대기
> **대상 브랜치:** `feat/sprint7c-strategy-ui` (신규, main 기반)
> **관련 plan:** 별도 세션에서 `/superpowers:writing-plans` 호출 후 `docs/superpowers/plans/`에 배치 예정

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

| 후보 | 현재 감내 수단 | 미래 pain | 결론 |
|------|---------------|-----------|------|
| 1. 주문 생성 폼 | curl payload로 leverage/margin 변경 테스트 가능 (Sprint 7a T4 실제 수행) | 낮음 | **Out** |
| 2. Strategy CRUD UI | `curl + JSON escape + auth token`로 회당 3~10분 마찰 | **높음** — 앞으로 Pine 이터레이션을 많이 돌릴 예정 | **In (primary)** |
| 3. ExchangeAccount UI | 1회 셋업이라 curl/psql로 감내 가능 | 낮음 (key 교체는 드뭄) | **Out** |
| 4. OrderList 상세 + 필터 | pgAdmin/logs/auto test로 커버됨 (지난 Sprint 실제 pain 없었음) | 중간 | **Out** (당장 블로커 아님) |

## Stage 2 Design Assets 재채택 (2026-04-17 plan-design-review 결과 반영)

**배경:** office-hours 세션이 DESIGN.md + `docs/prototypes/` + `INTERACTION_SPEC.md` 등 Stage 2(2026-04-14 확정) 자산을 참조하지 않고 진행. plan-design-review에서 Design Completeness 3/10로 채점됨. 아래 자산을 **Sprint 7c 구현의 시각·인터랙션 reference**로 채택한다.

| 자산 | 경로 | Sprint 7c 구현 역할 |
|------|------|---------------------|
| DESIGN.md | `/DESIGN.md` | 색상·타이포·간격 CSS 토큰 SSOT. 하드코딩 금지, 기존 변수 재사용 |
| 전략 목록 프로토타입 | `docs/prototypes/06-strategies-list.html` | `/strategies` 페이지 layout + App Shell 패턴 |
| 전략 편집 프로토타입 | `docs/prototypes/01-strategy-editor.html` | `/strategies/[id]/edit` 편집 페이지 — 탭(코드/파싱/메타데이터) + 에디터 + 분석 패널 |
| 전략 생성 프로토타입 | `docs/prototypes/07-strategy-create.html` | `/strategies/new` — 3-step 위저드 |
| 인터랙션 명세 | `docs/prototypes/INTERACTION_SPEC.md` | `@monaco-editor/react`, react-hook-form, 실시간 파싱 구현 방식 |

## 기술 결정 3가지

| # | 질문 | 결정 | 이유 |
|---|------|------|------|
| Q1 | Monaco editor vs Textarea | **writing-plans 세션에서 재결정 (open)** | Stage 2 프로토타입(`01-strategy-editor.html`)과 `INTERACTION_SPEC.md`가 `@monaco-editor/react`를 이미 채택. office-hours에서 내가 "Pine tokenizer 블랙홀"로 Textarea 대체 결정한 건 Stage 2 자산 미확인 상태의 판단이었음. **Pine syntax highlighting 부재는 사실이지만, 일반 텍스트 Monaco(한 줄 번호 + monospace + 기본 하이라이트 없음) 사용은 Textarea보다 품질 다운그레이드 없이 동일 기간 내 가능.** writing-plans가 Monaco 범위(highlight 없음 vs 최소 tokenizer vs 풀 하이라이트)를 task 분해 단계에서 결정한다. |
| Q2 | 편집 UI: Drawer 통합 vs 별도 라우트 | **별도 라우트** (`/strategies` + `/strategies/new` + `/strategies/[id]/edit`) | Stage 2 프로토타입이 이 3개 라우트로 이미 확정. Drawer 패턴은 프로토타입과 불일치 → 폐기. 3-step create wizard도 `07-strategy-create.html`대로 채택 |
| Q3 | Inline backtest vs 별도 페이지 navigate | **별도 페이지 navigate** (`/backtest?strategy_id=`) | Celery polling UI가 별도 대시보드로 팽창 위험. 기존 `/backtest` 페이지 재사용. |
| Q4 | Strategy versioning 도입 | **도입 안 함** | BE schema 변경(StrategyVersion 테이블) 필요 → P4 time box(1~1.5주) 위반. Sprint 7c는 **pure FE sprint**. |

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
