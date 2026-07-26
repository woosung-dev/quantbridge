# Sprint 28 Slice 1b — Phase B PRD/Roadmap/domain matrix (Type B, brainstorming 권고 30분)

> **Type:** B (design re-establishment — Phase B 는 docs 작성이 아니라 도메인 모델링 재정립)
> **시간:** brainstorming 30분 + writing-plans 직접 + 구현 ~5-8h
> **Branch:** sub-branch from `stage/h2-sprint28-comprehensive` → PR base = stage
> **Plan source:** [`~/.claude/plans/dreamy-dancing-pizza.md`](file:///Users/woosung/.claude/plans/dreamy-dancing-pizza.md) §3 Phase B (Task B.1~B.7)
> **Input:** Step 1 office-hours Addendum (4 신규 도메인 + Auto-Loop 자동화 + Beta path A1 결정)

## Goal

PRD/Roadmap/Phase 의 정합성 격차를 정량 매트릭스 + Phase 매핑 문서로 봉합. dogfood 끝난 후 Beta 경로 결정에 사용 가능한 framework 작성.

## Brainstorming (권고 30분 — 도메인 모델링 핵심 결정)

### 결정 1: Phase 1.5b "Live Trading 조기 구현" 정의

**문제:** PRD `requirements-overview.md` Phase 1~4 는 Live Trading 을 Phase 4 로 두지만, 실제는 Sprint 7-19 안에 90%+ 구현. 노후화 봉합 방식?

**Option A:** Phase 1.5b 신규 추가 (Phase 1.5 와 Phase 2 사이)

- Pros: PRD 가 실제 구현 순서 반영, 시간 흐름 보존
- Cons: Phase 정의 5+개 → 복잡도 ↑

**Option B:** Phase 4 → Phase 1.5b 로 이동 (Phase 4 내용 = Live Trading, Phase 2/3 stress test/optimizer 와 swap)

- Pros: 4 phase 유지, swap 으로 정합
- Cons: Phase 번호 재정의 시 다른 문서 cross-link 깨짐

**결정:** **Option A** (Phase 1.5b 추가). 사유: Phase 1/2/3/4 cross-link 보존 + 신규 Phase 추가가 가장 lightweight.

### 결정 2: 7 도메인 정의

**도메인 후보:**

1. Strategy (Pine Script 파싱, CRUD)
2. Backtest (vectorbt, 지표)
3. Stress Test (Monte Carlo, Walk-Forward) — Phase 2 이관
4. Optimizer (Grid/Bayesian/Genetic) — Phase 3 이관
5. Trading (Demo/Live 주문 실행, KillSwitch)
6. Market Data (OHLCV, TimescaleDB)
7. Exchange (계정 관리, AES-256)

**4 신규 cross-cutting 도메인** (office-hours Addendum):

- WebSocket Stability (Trading + Market Data 교차)
- Auth Trust Layer (Exchange + Trading 교차)
- Auto-Loop 자동화 (Trading 의 sub-domain)
- Multi-account/symbol/timeframe (Trading 의 sub-domain)

**결정:** 7 도메인 = primary axis. 4 신규는 cross-cutting layer 로 표시 (matrix 별도 행 또는 tag).

### 결정 3: domain-progress-matrix 컬럼 정의

**컬럼 후보:**

- A) PRD 정의 / 실제 구현 % / 격차 / 다음 step (4 컬럼)
- B) PRD / 실제 % / 격차 / 다음 step / 첫 sprint / 마지막 sprint / 활성 sprint (7 컬럼)
- C) PRD / 실제 / 격차 / Quality gate (SLO/KPI) / Active BL 카운트 (5 컬럼)

**결정:** **B 7 컬럼** — sprint mapping 까지 명시하면 phase-vs-sprint-mapping.md 와 cross-link 정합.

### 결정 4: H1 종료 정량 gate 측정 가능 정의

**현재 (모호):**

- "Testnet dogfood 3-4주 무사고"
- "Kill Switch + leverage cap + AES-256 재검증 pass"
- "Prometheus alert 1개 이상 실전 동작"

**정량화 후:**

- "**dogfood Day ≥7 + 신규 critical bug 0건 + LiveSession 누적 N개 이상**" — N = 5 (multi-account + multi-symbol 검증)
- "**BL-004 capital_base 동적 검증 PR 머지 + AES-256 unit test green**" — Slice 4 결과
- "**alert rule 등록 + 1회 fire + auto-resolve 검증**" — H2 Phase 2 sprint 으로 이관 가능

**결정:** 위 3 정량 gate. Slice 1b T4 산출물.

## Tasks (7 task, 약 5-8h)

### T1 — `requirements-overview.md` Phase 표 갱신 (1h)

**File:** `docs/01_requirements/requirements-overview.md` (수정)

**변경:**

- Phase 1~4 표 갱신 — Phase 1.5b 신규 행 (Sprint 7~19, ~8주, Live Trading 조기 구현)
- Phase 2 (Stress Test) 일정 재산정 → H2 Sprint 후속
- Phase 3 (Optimizer) 일정 재산정 → H2/H3 Sprint 후속
- Phase 4 (deprecated 또는 Phase 1.5b 흡수)

### T2 — `domain-progress-matrix.md` 신규 (1.5h)

**File:** `docs/01_requirements/domain-progress-matrix.md` (신규)

**내용:**

- 7 도메인 × 7 컬럼 매트릭스 (PRD 정의 / 실제 % / 격차 / 다음 step / 첫 sprint / 마지막 sprint / 활성 sprint)
- 4 cross-cutting 도메인 layer (별도 섹션)
- BL ID cross-link (각 도메인 active BL — 예: WebSocket → BL-001/011-016 6건)
- Quality gate (각 도메인 SLO/KPI 측정 시점 + 결과)

### T3 — `phase-vs-sprint-mapping.md` 신규 (1h)

**File:** `docs/00_project/phase-vs-sprint-mapping.md` (신규)

**내용:**

- Phase 0~4 ↔ Sprint 1~28 ↔ H1/H2 horizon 3-축 매핑 표
- 각 Sprint (계획 phase / 실제 phase / 격차 사유) 3 컬럼
- 미래 Phase (2/3/4) 의 예상 sprint 범위 (Sprint 28-N)
- Phase 종료 trigger 명시 (예: Phase 1.5b → dogfood Day 7 + Beta 전환)

### T4 — `roadmap.md` H1 종료 정량 gate (45분)

**File:** `docs/00_project/roadmap.md` (수정 L88-106 + 본 sprint 28 office-hours Addendum 추가)

**변경:**

- H1→H2 3 항목 정량화 (위 brainstorming 결정 4 결과)
- H2→H3 3 항목 정량화 (지인 Beta 5명 / Monte Carlo 본인 1회+ / Freemium 티어 결정)
- H3 성공 정의 정량화 ($1 paid / TV 공개 1건 / MRR 데이터 수집)

### T5 — `beta-path-decision.md` 신규 (1h)

**File:** `docs/00_project/beta-path-decision.md` (신규)

**내용:**

- Path A1 framework (자연 시간 1-2주 dogfood Day 7+) — prereq / duration / 예상 BL fix / 리스크
- Path B framework (극소액 mainnet 72h + 지인 Beta 5명) — prereq / duration / 자본 cap / 리스크
- 결정 trigger — dogfood Day 7 결과 (critical bug / self-assessment / BL P0 잔여)
- Trade-off 표 (각 path 의 ★별 추천도 + 사용자 상황 추천도)

### T6 — `REFACTORING-BACKLOG.md` 갱신 (1.5h)

**File:** `docs/REFACTORING-BACKLOG.md` (수정 — 현재 762줄)

**변경:**

- BL-076~090 신규 등록 (H2 Sprint 14-19 발견 항목)
- BL-091~110 신규 등록 (H2 Sprint 20-26 발견 항목)
- BL-130~141 신규 등록 (Sprint 27 + dogfood Day 1 발견)
- Beta 오픈 BL-070~075 진행 상태 갱신
- `최종 갱신` 날짜 + `총 항목` 카운트 갱신

### T7 — PRD 노후 항목 보강 (1h)

**File:** `docs/01_requirements/requirements-overview.md` (수정)

**변경:**

- WebSocket Stability (BL-001/011-016) — REQ-WS-### 신규 카테고리 + 8 sprint 분량 명시
- Auth Trust Layer (15 ADR + commit-spy) — REQ-AUTH-### 확장
- Multi-account/symbol/timeframe Live Trading — REQ-TRD-### 확장
- Auto-Loop dogfood (Sprint 27) — REQ-OPS-### 신규 카테고리

## File summary

**신규 (3 파일):**

- `docs/01_requirements/domain-progress-matrix.md`
- `docs/00_project/phase-vs-sprint-mapping.md`
- `docs/00_project/beta-path-decision.md`

**수정 (3 파일):**

- `docs/01_requirements/requirements-overview.md` (Phase 표 + 4 신규 REQ 카테고리)
- `docs/00_project/roadmap.md` (H1/H2/H3 정량 gate)
- `docs/REFACTORING-BACKLOG.md` (50→81+ 갱신)

## Risks & Mitigations

| 리스크                                   | 영향                                 | 완화                                                                                                                                                             |
| ---------------------------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PRD ↔ vision.md ↔ roadmap.md 3 SSOT 충돌 | 3 문서 일관성 깨짐                   | SSOT 명시 정책: PRD = `requirements-overview.md`, Phase = `phase-vs-sprint-mapping.md`, Horizon/Pillar = `roadmap.md`. 각 문서 top 에 SSOT 라벨 (이미 일부 적용) |
| Phase 정의 변경이 다른 cross-link 영향   | dev-log + superpowers cross-ref 깨짐 | grep -r "Phase 4" docs/ 1회 + 발견된 cross-ref 모두 갱신                                                                                                         |
| BL 등록 31개 (50→81) 시간 부족           | T6 1.5h 초과                         | Beta blocker (P0/P1) 우선, P2/P3 는 Slice 1b 종료 후 별도 sprint 가능                                                                                            |

## Acceptance Criteria

- [ ] T1 Phase 표 = Phase 1.5b 신규 + Phase 2/3 일정 재산정
- [ ] T2 domain matrix 7 도메인 × 7 컬럼 + 4 cross-cutting layer
- [ ] T3 phase-vs-sprint mapping Sprint 1-28 모두 매핑 100%
- [ ] T4 H1/H2/H3 9 gate 모두 측정 가능 정의
- [ ] T5 Path A1/B 각각 5 차원 (prereq/duration/risk/추천도/trigger) 표
- [ ] T6 BL ID 81+ 등록 + cross-link CLAUDE.md 일관성
- [ ] T7 4 신규 REQ 카테고리 모두 PRD 안 명시

## PR Strategy

**1 PR**: `feat/sprint28-slice1b-prd-roadmap` → base `stage/h2-sprint28-comprehensive`

- T1-T7 모두 1 PR
- commit 분리: T1+T7 (PRD), T2 (domain matrix), T3 (phase mapping), T4 (roadmap gate), T5 (beta path), T6 (BL backlog)

## Self-Review (G0 evaluator pattern)

- [P1-1] T6 BL 등록 31개 = 1.5h 추정 — 실제 sprint history 일독 필요 시 4-6h. 시간 underestimated. → 권고: Beta blocker 만 우선 (BL-076-110 = 사용자 dogfood 일지 인용 가능, 그 외 P2/P3 는 후속 sprint)
- [P2-1] T2 domain matrix 7 도메인 × 7 컬럼 = 49 cell 채움 + 4 cross-cutting layer 추가 → 1.5h 부족 가능. 권고: 1차 4 컬럼만 (PRD/실제/격차/다음 step) → 2차 7 컬럼 확장
- [P2-2] T4 roadmap H1 gate 정량화 = 본 sprint 28 office-hours Addendum 의 H1→H2 조건 5개 (위에 commit 됨) 와 정합 검증 의무
- [P2-3] T5 beta-path-decision.md 의 결정 trigger = office-hours design doc 의 "Q4 narrowest wedge 답" 과 정합 (BL-141+140b+004 = Beta 진입)

P1 1건 (T6 시간 underestimated) / P2 3건 — Slice 1b 진행 OK with T6 scope 조정.
