# Sprint 28 — Beta prereq 종합 (Phase B+C cleanup + BL-141/140b/004) — Kickoff

> **작성일:** 2026-05-04 (Sprint 27 hotfix 완료 + dogfood Day 1 진행 중 + Phase A docs cleanup 완료 시점)
> **상태:** Kickoff plan — 새 세션 진입 시 첫 reference
> **브랜치:** `chore/2026-05-04-docs-cleanup` (Phase A 결과 33 파일 변경 working tree 보존) → Sprint 28 진입 시 `stage/h2-sprint28-comprehensive` 로 rename 검토
> **시간 추정:** 24-35h (Stage 3 office-hours 재진행 + 4 Slice planning 6-7h + 구현 12-20h + 검증 4-6h + 학습 1-2h)
> **워크프로세스:** [`.ai/templates/methodology-tooled.md`](../../.ai/templates/methodology-tooled.md) Stage 1~6 풀 사이클 정식 적용 (Generator-Evaluator + codex G0/G2/G4)
> **상위 plan:** [`~/.claude/plans/dreamy-dancing-pizza.md`](file:///Users/woosung/.claude/plans/dreamy-dancing-pizza.md) (옵션 5 확정)

---

## Context

**Sprint 27 종료 직후 + Phase A docs cleanup 완료 + dogfood Day 1 진행 시점.**

Phase A audit 에서 발견된 PRD/Roadmap/workflow 격차 (Phase B+C) 를 dogfood Day 4-7 자연 사용 결과 반영하여 마무리하고, dogfood Day 1 에서 발견된 Beta prereq BL 3건 (BL-141 Backtest UI, BL-140b equity curve, BL-004 KillSwitch capital_base) 을 Vertical Slice 로 풀 사이클 (Stage 1~6) 적용하여 처리한다.

**Beta path A1 prereq 모두 처리 → dogfood Day 7 종료 시점 = Beta 오픈 결정 가능 상태.**

## 진입 조건 (새 세션이 첫 단계로 검증)

- [ ] Phase A working tree 33 파일 변경 보존 (`git status --short` 으로 확인)
- [ ] `chore/2026-05-04-docs-cleanup` branch active
- [ ] Phase A commit + push + PR 진행 → main merge **(새 세션 첫 step)**
- [ ] Sprint 28 staging branch 결정 — 기존 cleanup branch rename vs 새 branch
- [ ] dogfood Day 4-7 진행 상태 확인 (자연 사용 흐름 보호)

## Vertical Slice 4건 (Stage 3 Vertical Slice 원칙 준수)

### Slice 1 — Phase B + C cleanup 마무리 (5-12h)

**도메인:** docs / PRD / Roadmap / workflow enforcement

**Files (Phase B):**

- `docs/01_requirements/requirements-overview.md` — Phase 1.5b 신규 + Phase 2/3 일정 재산정
- `docs/01_requirements/domain-progress-matrix.md` — 7 도메인 × 6 컬럼 매트릭스 (신규)
- `docs/00_project/phase-vs-sprint-mapping.md` — Phase 0~4 ↔ Sprint 1~28 ↔ H1/H2 (신규)
- `docs/00_project/roadmap.md:88-106` — H1 종료 정량 gate (Prometheus alert / dogfood Day N / BL P0 잔여)
- `docs/00_project/beta-path-decision.md` — Path A1/B framework + 결정 trigger (신규)
- `docs/REFACTORING-BACKLOG.md` — 50→81+ 갱신
- `docs/01_requirements/requirements-overview.md` — REQ-WS / REQ-AUTH / REQ-TRD / REQ-OPS 4 카테고리 추가

**Files (Phase C):**

- `docs/guides/sprint-template.md` — sprint **종료** sweep template (신규)
- `docs/guides/bl-audit-checklist.md` — sprint 시작 시 review 의무 (신규)
- `.github/pull_request_template.md` — codex Gates 섹션 추가
- `.claude/settings.json` — `hooks` 키 신규 (Stop / SessionStart)
- `.husky/pre-commit` — dev-log INDEX 갱신 reminder (선택, reminder only)
- `docs/TODO.md` — 메타 헤더 표준화 (Last Updated / Active Sprint / Recent BLs)

**검증:** `~/.claude/plans/dreamy-dancing-pizza.md` 의 Phase B/C 검증 표 100% 충족.

### Slice 2 — BL-141 Backtest UI 활성화 + ts.ohlcv backfill (4-8h)

**도메인:** Backtest (UI) + Market Data (BE) — Vertical Slice (FE+BE 관통)

**증거:** dogfood Day 1 — `docs/dev-log/2026-05-04-dogfood-day1-sprint27-launch.md:312-321` ("backtest UI disabled + ts.ohlcv 비어있음")

**Files (예상, Stage 3 plan 작성 시 확정):**

- `frontend/src/app/(authed)/backtests/` — UI disable 해제 + 입력 폼 활성화
- `backend/src/services/market_data/backfill.py` — ts.ohlcv backfill Celery task
- `backend/src/api/backtest/run.py` — 422 inline 검증 (BL-141 prerequisite)
- `backend/tests/services/test_market_data_backfill.py` — backfill 검증 (TDD)

**검증:**

- ts.ohlcv hypertable BTC/USDT 1H ≥30일 데이터 존재
- Backtest UI "Sample 백테스트" 1회 완주 (FE 스모크)
- codex G2 challenge PASS

### Slice 3 — BL-140b LiveSignal real equity curve (3-5h)

**도메인:** Trading (BE schema) + Trading (FE chart) — Vertical Slice

**증거:** dogfood Day 1 — `docs/dev-log/2026-05-04-dogfood-day1-sprint27-launch.md:269-271` (LiveSignalDetail equity curve 부재 → Sprint 27 BL-140 chart UI fix 후 BE schema 후속 = BL-140b)

**Files (예상):**

- `backend/src/models/live_signal.py` — equity_curve 필드 schema (Decimal-first 합산)
- `backend/src/services/live_signal/equity_calculator.py` — 누적 equity 계산
- `frontend/src/components/live-signal/EquityCurveChart.tsx` — recharts dual-line (number-only → real value)
- `backend/tests/services/test_equity_calculator.py` — Decimal 합산 검증

**검증:**

- BL-140 chart UI + BL-140b 실 equity 통합 — LiveSignal Activity Timeline 정확도 100%
- codex G2 challenge PASS
- dogfood Day 4-7 LiveSession 5분/15분 timeframe 자연 사용 검증

### Slice 4 — BL-004 KillSwitch capital_base 동적 검증 (3-5h)

**도메인:** Trading (Risk Management) — BE 검증 (FE 영향 X)

**증거:** `docs/REFACTORING-BACKLOG.md` BL-004 (P0, in-progress) — `docs/00_project/roadmap.md:54,131` (Kill Switch capital_base 레버리지 반영 검증). [ADR-006 미해결]

**Files (예상):**

- `backend/src/services/trading/kill_switch.py` — capital_base 동적 fetch_balance 호출
- `backend/src/services/trading/kill_switch_test.py` — 통합 테스트 (Bybit Demo 실측)
- `docs/dev-log/006-sprint6-design-review-summary.md` — ADR-006 결의 (capital_base 동적 명시)

**검증:**

- Kill Switch 동작 시 capital_base = 거래소 fetch_balance 결과 반영 확인
- 레버리지 cap 검증 통과 (Bybit Cross Margin)
- codex G2 challenge PASS
- H1→H2 gate "Kill Switch + leverage cap 재검증 pass" 정량화 진입

---

## 워크프로세스 (Stage 1~6 정식 사이클) + Skill 매핑

> **핵심 규칙:** 모든 skill 동시 invoke 금지. Stage 별 필요한 시점에만 invoke. 사용자 메모리 "Sprint 끊지 말 것" + "자율 병렬 실행 Option C" 정합.

### Stage 1 — 기획 + 아키텍처 (이미 완료)

- 본 sprint 는 Stage 1 산출물 (vision.md / roadmap.md / requirements-overview.md) 위에서 진행. 단 Slice 1 Phase B 가 Stage 1 산출물 자체를 갱신.

### Stage 2 — 디자인 (이미 완료)

- `docs/prototypes/` 12 HTML + DESIGN.md 활용. 단 Slice 2 (Backtest UI) + Slice 3 (equity curve) 는 prototypes 02 (`02-backtest-report.html`) reference.

### Stage 3 — Sprint 계획 (새 세션 첫 진입)

> **2026-05-04 정책 추가 (메타-방법론 분석 결과):**
>
> - **Sprint type 분류** (kickoff 시점) — Type A (신규 기능) / B (BL fix) / C (hotfix) / D (docs only) → brainstorming scope 차등
> - **office-hours 재진행 의무 (Step 0)** — Era 2 (Sprint 13-27) 의 BL 3배 + codex P1 42건 누적 = brainstorming 부재 비용. Sprint 28 = Era 3 정상화 시점
> - **dual metric 의무** (sprint 종료) — self-assessment + BL count. divergence 시 sprint 미완 (Sprint 27 8.0 + 4 P0 BL case 회피)

#### Step 0 — office-hours 재진행 (O-11, 140분 포함 사전, 의무)

**근거:** 처음 office-hours (`docs/dev-log/008-sprint7c-scope-decision.md`, 2026-04-17) 의 Q4 (narrowest wedge) Q5 (observation) 답이 dogfood 3개월 결과로 **부분 무효화**:

- Q4 "Strategy CRUD UI 단독" → 4 신규 도메인 (WebSocket Stability / Auth Trust Layer / Auto-Loop / Multi-account)
- Q5 "curl/psql 감내" → Auto-Loop 자동화 필수 판명
- Q1 "메이커 예측형 demand" → 본인 dogfood 만족도 정량화 (시스템 8.5 / UX 6.5 / 종합 8/10)

**진행:**

1. **(60분 사전)** dogfood 일지 9개 일독 + 핵심 발견 3-line 요약:
   - `docs/dev-log/2026-04-25-dogfood-day1.md`
   - `docs/dev-log/2026-04-26-dogfood-day2.md`
   - `docs/dev-log/2026-04-27-dogfood-day3.md`
   - `docs/dev-log/2026-05-02-sprint20-dogfood-day0-setup.md`
   - `docs/dev-log/2026-05-03-dogfood-day1-sprint21.md`
   - `docs/dev-log/2026-05-04-dogfood-day1-sprint27-launch.md`
   - `docs/dev-log/dogfood-week1-path-beta.md`

2. **(50분 본진행)** `/office-hours` skill — Q4 + Q5 + Q1-indie 변형:
   - Q4 narrowest wedge 재정의 — 4 도메인 명시 (Pine → Backtest → Live → Auto-Loop)
   - Q5 observation 재정의 — Auto-Loop 자동화 필수 (Beat task + reconcile_ws_streams 실증)
   - Q1 demand reality — 본인 dogfood 만족도 정량 (시스템 / UX / 종합)

3. **(30분 산출물)**:
   - `docs/dev-log/008-sprint7c-scope-decision.md` 말미 "2026-05-04 office-hours Addendum" 섹션 추가
   - `docs/00_project/vision.md` + `docs/00_project/roadmap.md` 5-10줄 추가 (4 신규 도메인 + Auto-Loop)
   - 본 산출물 = Slice 1 Phase B (PRD/Roadmap 갱신) 의 사전 input

#### Step 1-4 — Slice 별 brainstorming + writing-plans + codex G0 (Sprint type 차등, 4.5h)

**Sprint type 분류 매트릭스:**

| Slice                                             | Type                  | brainstorming | codex G0 | 시간                                                                                                          |
| ------------------------------------------------- | --------------------- | ------------- | -------- | ------------------------------------------------------------------------------------------------------------- |
| **Slice 1** (Phase B+C cleanup)                   | **D — docs only**     | **면제**      | 면제     | writing-plans 직접 (`dreamy-dancing-pizza.md` §3 task 활용)                                                   |
| **Slice 2** (BL-141 Backtest UI + backfill)       | **A — 신규 기능**     | **의무 60분** | 의무     | 설계 선택지 3+ (UI disable 해제 방식 / backfill batch size / Celery task 분리) + writing-plans 30분           |
| **Slice 3** (BL-140b equity curve BE schema → FE) | **A — 신규 기능**     | **의무 45분** | 의무     | Decimal 합산 (Sprint 4 D8 영구 규칙) + Celery prefork (Sprint 4 D3) + recharts dual-line + writing-plans 30분 |
| **Slice 4** (BL-004 KillSwitch capital_base)      | **B — risk-critical** | **권고 30분** | 의무     | capital_base fetch_balance 시점 + 레버리지 cap + Bybit Cross Margin 통합 테스트 + writing-plans 20분          |

**필수 skill 순차 invoke (각 Slice 별):**

1. **brainstorming** ★★★★★ — Slice 별 의도/요구사항/엣지케이스 (type 별 차등 시간)
2. **writing-plans** ★★★★★ — file path / step / 검증 기준 / 의존성 — `~/.claude/plans/<hash>.md` 또는 `docs/dev-log/sprint28-slice<N>-plan.md`
3. **codex** (review mode, G0 evaluator) ★★★★★ — Generator-Evaluator:
   - Generator: writing-plans 산출물
   - Evaluator: `/codex review` skill (P1 issue 검출 의무)
   - **G0 gate**: P1 issue 0 도달까지 plan 재작성. **최대 2 iter** (LESSON-017 회피)
4. **systematic-debugging** ★★★★☆ — (조건부) G0 P1 root cause 분석 시
5. **ExitPlanMode** — Stage 4 진입

**Sprint type 별 정책 (영구 규칙 — Phase C.1 sprint-template 에 inherit):**

- **Type A** (신규 기능 / 도메인 확장) → brainstorming **의무** (45-60분) + writing-plans + codex G0
- **Type B** (BL fix / technical debt) → brainstorming **선택** (risk-critical 시 권고 30분) + writing-plans + codex G0
- **Type C** (dogfood hotfix) → brainstorming **압축 15분** + writing-plans + codex G0
- **Type D** (docs / cleanup only) → brainstorming **면제** + writing-plans 직접 + codex G0 면제

### Stage 4 — 구현 (병렬 가능 영역 분리)

**병렬 영역 분석:**

- **Slice 1 Phase B (cleanup)** — 독립 도메인 (docs only) — 다른 Slice 와 파일 경계 0 → 병렬 가능
- **Slice 1 Phase C (workflow enforcement)** — 독립 도메인 (.claude/.github/.husky 등 settings) — 병렬 가능
- **Slice 2 BL-141 (Backtest UI + backfill)** — FE+BE Vertical, dogfood Day 4-7 영향 0 검증 후 진행
- **Slice 3 BL-140b (equity curve)** — BE schema 후 FE 의존 — 순차 진행
- **Slice 4 BL-004 (KillSwitch)** — BE 단독, 다른 Slice 와 독립 — 병렬 가능

**필수/강추 skill:**

1. **using-git-worktree** ★★★★☆ — Slice 1 Phase B + Slice 4 KillSwitch 병렬 worktree (cmux 운영 사용자 메모리 정합)
2. **subagent-driven-development** ★★★★☆ — Slice 별 fresh subagent + task 단위 review (컨텍스트 보호. Sprint X1+X3 5 워커 경험)
   - **양자택일:** subagent-driven-development vs `executing-plans` (inline batch). 본 sprint 는 **subagent-driven-development 권장** (Slice 4건 의 독립성 → fresh subagent 효과적)
3. **test-driven-development** ★★★★★ — Slice 2/3/4 BE 테스트 우선 (Red→Green→Refactor). Decimal-first 합산 (Sprint 4 D8 교훈), Celery prefork-safe (Sprint 4 D3 교훈) 등 영구 규칙 준수
4. **simplify** (gstack) ★★★☆☆ — (선택) 구현 후 DRY/YAGNI 적용
5. **/browse** 또는 **/gstack** ★★★★☆ — Slice 2 (Backtest UI 활성화) FE 스모크 검증

**Atomic update:** 코드 + docs + lessons.md 동일 PR

### Stage 5 — 검증 + 배포

**필수 skill 순차 invoke:**

1. **codex** (challenge mode, G2 review) ★★★★★ — 각 Slice PR 별 1회. adversarial review 통해 P1/P2 issue 검출. PR description 의 "Codex Gates" 섹션 (Phase C.3 결과 활용) 에 결과 기록
2. **verification-before-completion** ★★★★★ — type/lint/test 통과 + dogfood smoke (Bybit Demo) 1회 + 실제 실행 결과 확인 후 완료 주장
3. **/qa-only** (gstack) ★★★★☆ — Slice 2 (Backtest UI) + Slice 3 (equity curve) FE 변경분 자동 QA
4. **/codex** (consult mode, G4 P2 review) ★★★★☆ — G2 통과 후 P2 issue 정리 (BL 등록 vs 즉시 fix 결정)
5. **/ship** (gstack) ★★★★☆ — PR + merge + verify (사용자 Git Safety Protocol 단계별 승인 후)
6. **requesting-code-review** (선택) ★★★☆☆ — PR 전 self-review

각 Slice 별 PR (cleanup 1 PR + Slice 2/3/4 각 1 PR = **4 PR**).

### Stage 6 — 학습 (dual metric 의무)

**Manual + skill 조합:**

1. **lessons.md** 신규 항목 (각 Slice 별 발견 1건 이상) — manual
2. **REFACTORING-BACKLOG.md** 갱신 (BL-141/140b/004 Resolved 표시 + 신규 발견 BL 등록) — manual
3. **docs/dev-log/INDEX.md** Sprint 28 항목 추가 (Phase A.4 매트릭스 갱신) — manual
4. **본 파일** (`2026-05-04-sprint28-kickoff.md`) → sprint 종료 시 retrospective 섹션 추가 (Phase C.1 sprint-template prototype)
5. **finishing-a-development-branch** ★★★☆☆ — (선택) sprint 종료 시 branch handoff 자동화
6. **/retro** (gstack) ★★★☆☆ — (선택) weekly retro 적용 — Sprint 28 종료 시 자동 분석

**Dual metric 의무 (Sprint 27 의 self-assess 8.0 + 4 P0 BL divergence case 회피):**

| Metric              | 측정                               | 통과 기준                                                |
| ------------------- | ---------------------------------- | -------------------------------------------------------- |
| **Self-assessment** | 점수 (1-10) + 근거 ≥3 줄           | ≥7 (H1→H2 gate)                                          |
| **신규 BL count**   | P0/P1/P2/P3 분류 (Slice 별 + 합계) | P0=0, P1≤2                                               |
| **divergence 검출** | self-assess ≥7 AND P0=0 모두 충족? | 둘 중 하나 실패 시 sprint 미완 (BL fix 추가 sprint 필요) |

**판정:** dual metric 모두 통과 시 Sprint 28 → H1→H2 gate 통과 가능. Roadmap.md `H1→H2 전환 조건` 의 정량 gate 와 일치 (Slice 1 Phase B.4 산출물 활용).

---

## Skill 사용 비추천 (overhead)

- **brainstorming + executing-plans 동시** — Stage 3 안 순차 (brainstorm → plan), 동시 invoke X
- **subagent-driven-development + executing-plans 둘 다** — 양자택일. 본 sprint = subagent-driven-development
- **autonomous-parallel-sprints** — Slice 4건 동시 cmux 5 워커 시에만 유의미. 단 사용자 직접 실행 시간이 cmux setup 비용 초과 — single agent + git-worktree 로 충분
- **모든 skill 강제** — Stage 별 필요한 것만 invoke (예: Stage 3 시점에 verification-before-completion 미invoke)

---

## 새 세션 진입 시 첫 step (실행 시 즉시 가능)

```
=== Phase A 마무리 (5-15분, Git Safety Protocol 단계별) ===
1. (3분) git status — 33 파일 변경 working tree 인식
2. (1분) git checkout chore/2026-05-04-docs-cleanup (이미 active 면 skip)
3. (5분) 사용자 commit 메시지 승인 요청:
   "chore: docs cleanup Phase A — orphan archive + INDEX + SSOT labels"
4. (1분) git add docs/ + git commit (위 메시지)
5. (1분) git push -u origin chore/2026-05-04-docs-cleanup
6. (5분) gh pr create — title "chore: docs cleanup Phase A (옵션 5 Sprint 28 Slice 1 prep)"
7. (Phase A 종료) 사용자 PR review + main merge

=== Stage 3 — Step 0: office-hours 재진행 (O-11, 140분) ===
8. (60분 사전) dogfood 일지 9개 일독:
   - 2026-04-25/26/27-dogfood-day1/2/3.md
   - 2026-05-02-sprint20-dogfood-day0-setup.md
   - 2026-05-03-dogfood-day1-sprint21.md
   - 2026-05-04-dogfood-day1-sprint27-launch.md
   - dogfood-week1-path-beta.md
   - 핵심 발견 3-line 요약
9. (50분 본진행) /office-hours skill — Q4 narrowest wedge 재정의 + Q5 observation 재정의 + Q1-indie 변형
10. (30분 산출물):
    - docs/dev-log/008-sprint7c-scope-decision.md 말미 "2026-05-04 Addendum"
    - docs/00_project/vision.md + roadmap.md 5-10줄 추가 (4 신규 도메인)
    - 본 산출물 = Slice 1 Phase B PRD 갱신 input

=== Stage 3 — Step 1-4: Slice 별 brainstorming + writing-plans + codex G0 (Sprint type 차등) ===
11. Slice 1 (Phase B+C cleanup, Type D — 면제):
    - brainstorming 면제 → writing-plans 직접 (dreamy-dancing-pizza.md §3 task 활용)
12. Slice 2 (BL-141 Backtest UI + backfill, Type A — 의무):
    - brainstorming 60분 (설계 선택지 3+) → writing-plans 30분 → /codex review G0
13. Slice 3 (BL-140b equity curve BE schema, Type A — 의무):
    - brainstorming 45분 (Decimal 합산 + Celery prefork) → writing-plans 30분 → /codex review G0
14. Slice 4 (BL-004 KillSwitch capital_base, Type B risk-critical — 권고):
    - brainstorming 30분 → writing-plans 20분 → /codex review G0
15. (각 Slice) ExitPlanMode → Stage 4 진입

=== Stage 4 구현 (병렬 영역 분리, 12-20h) ===
16. using-git-worktree (선택) — Slice 1 Phase B + Slice 4 KillSwitch 병렬 worktree
17. subagent-driven-development — Slice 별 fresh subagent + task 단위 review
18. test-driven-development — Slice 2/3/4 BE Red→Green→Refactor

=== Stage 5 검증 + 배포 (Slice 별 PR, 4-6h) ===
19. /codex challenge (G2) — 각 PR adversarial review
20. verification-before-completion — type/lint/test/dogfood smoke (Bybit Demo)
21. /qa-only — FE 변경분 자동 QA (Slice 2/3)
22. /ship — PR + merge + verify (Git Safety Protocol)

=== Stage 6 학습 (dual metric 의무, 1-2h) ===
23. lessons.md 신규 + REFACTORING-BACKLOG 갱신 (BL-141/140b/004 Resolved + 신규 BL)
24. docs/dev-log/INDEX.md Sprint 28 항목 추가
25. 본 파일 retrospective 섹션 추가 (Phase C.1 sprint-template prototype)
26. dual metric 측정:
    - self-assessment 점수 (1-10) + 근거 ≥3줄
    - 신규 BL count (P0/P1/P2/P3 분류)
    - divergence 검출 (self-assess ≥7 AND P0=0 모두 충족? — 실패 시 sprint 미완)
27. dogfood Day 4-7 자연 사용 흐름 보호 검증 (Slice 2 활성화 시 영향 0 확인)
```

**총 시간 분해:** Phase A commit 5-15분 + Step 0 office-hours 140분 + Step 1-4 planning 4.5h + Step 5-6 구현 12-20h + Step 7 검증/배포 4-6h + Step 8 학습 1-2h = **24-35h**

## 참고 문서 (새 세션이 read 할 수 있도록 정리)

- **상위 plan:** `~/.claude/plans/dreamy-dancing-pizza.md` (옵션 5 확정)
- **방법론:** `.ai/templates/methodology-tooled.md` (Stage 1~6)
- **Phase A 결과:** `docs/dev-log/INDEX.md` (Sprint 1-28 매트릭스), `docs/_archive/2026-Q2-h1/next-session/INDEX.md` (12 파일 archive)
- **dogfood Day 1 finding:** `docs/dev-log/2026-05-04-dogfood-day1-sprint27-launch.md` (BL-140/141 발견 근거)
- **활성 Sprint 27 회고:** `docs/dev-log/2026-05-04-sprint27-beta-prereq-hotfix.md`
- **Beta path framework:** `docs/00_project/roadmap.md:88-106` (H1→H2 gate, 정량화는 Slice 1 Phase B.4 산출물)
- **CLAUDE.md "현재 컨텍스트":** Sprint 28 진입 시 갱신

---

## 자체 평가 (kickoff 시점, sprint 종료 후 갱신)

| 항목                       | 점수      | 근거                                                      |
| -------------------------- | --------- | --------------------------------------------------------- |
| Vertical Slice 정합성      | \_/10     | (sprint 종료 후)                                          |
| codex G0/G2 적용 일관성    | \_/10     | (sprint 종료 후)                                          |
| dogfood Day 4-7 영향 0     | \_/10     | (sprint 종료 후, BL-141 활성화 시 dogfood 흐름 변경 가능) |
| Beta path A1 prereq 처리율 | \_/10     | (sprint 종료 후, 4 Slice 완료율)                          |
| **종합**                   | **\_/10** | (sprint 종료 후)                                          |

> **다음 갱신:** Sprint 28 종료 시점 — self-assessment 점수 입력 + retrospective 섹션 추가.
