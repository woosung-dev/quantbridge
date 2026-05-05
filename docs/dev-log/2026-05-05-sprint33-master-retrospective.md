# Sprint 33 — 6.5 양다리 균형 패키지 Master Retrospective

**기간:** 2026-05-05 (단일 세션 자율 병렬 + codex G.0 P1 surgery 3건 + dogfood Day 6 hotfix 2건)
**브랜치:** main `06f5512` (7 PR all merged)
**입력:** dogfood Day 5 = 6~7/10 borderline → **Day 6 = 5/10 (regression -1.5~2)** — BUG 3건 발견 (BL-175 + BL-176 즉시 hotfix / BL-177 Sprint 34 defer)
**Sprint 34 분기 결정:** **polish iter 2** (≥7 미달 → Beta 본격 진입 미루기). 우선순위 = BL-175 본격 fix / BL-177 chart marker / BL-166 uvicorn / BL-176 follow-up / BL-174 detail

---

## 0. Sprint 33 7 PR 통합

```
06f5512 PR #147 fix(sprint33-hotfix): SelectWithDisplayName v=null skip (BL-176 hotfix, dogfood Day 6 발견)
49b07fc PR #146 fix(sprint33-hotfix): Buy & Hold 거짓 trust 차단 (BL-175 hotfix, dogfood Day 6 발견)
376cecf PR #144 feat(sprint33-main): live-session-list Empty/Failed/Loading 통일 (BL-174 list-only)
7663bec PR #142 docs(sprint33-C): Cloud Run topology gap audit + runbook (BL-071 audit, codex P1-2)
a6ac7ea PR #145 feat(sprint33-A): live-session-detail Activity Timeline → lightweight-charts (BL-150 partial)
1c8f4e5 PR #143 feat(sprint33-B): live-session-form SelectValue render prop helper 통일 (BL-164)
78c5d23 PR #141 feat(sprint33-step0): pre-push hook main worktree push 차단 (worker isolation 영구)
```

**총 7 PR** (codex P1-1 surgery 후 6 PR 계획 → BL-166 defer 로 5 PR + dogfood Day 6 BL-175/176 hotfix 2 PR = 7 PR 실측).

---

## 1. 출발점 — 사용자 brainstorming + Plan agent 검증

### 사용자 brainstorming 결정 (별점 추천 우선)

- **모드:** 균형 패키지 (★★★★★) — polish + Beta prep + tooling 동시
- **실행:** 자율 병렬 + 메인 세션 (★★★★★)
- **BL-070:** skip (도메인 미정)
- **P3 흡수:** BL-166 + BL-174 메인 세션 (★★★★★)
- **BL-150 scope:** 핵심 1-2개 (★★★★★)
- **pre-push hook:** Hybrid (★★★★★)

### Plan agent 검증 4 발견

1. **BL-071 이미 Sprint 30 ε 완성** — `backend/Dockerfile` + `backend/src/health/router.py` (`/healthz` 3-dep) 코드 완성. Worker C scope 대폭 축소 가능
2. **충돌 hotspot — `live-session-detail.tsx`** BL-150 + BL-174 중복 → BL-174 = list-only 축소
3. **pre-push hook bootstrap 문제** — Sprint 33 자체에서 hook 신설
4. **BL-150 lightweight-charts 한계** — walk-forward / monte-carlo native 미지원 → Sprint 34 defer

---

## 2. codex G.0 master plan validation (Verdict GO_WITH_FIXES)

session `019df729` / medium tier / **124,335 tokens** / Verdict = **GO_WITH_FIXES** + P1 surgery 3건.

| ID       | 발견                                                                                                                               | surgery 적용                                                                                                                                                                                                                                       |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **P1-1** | pre-push hook 의 D 최후 머지 = Sprint 32 lesson 재발 방어 X                                                                        | **메인 세션 step 0 선행 commit + push** (Worker D 삭제). hook 에 path/git_dir/common_dir 출력 + bypass 명시 로그                                                                                                                                   |
| **P1-2** | BL-071 healthz 가 Celery worker ≥1 강제. API 단일 dry-run 로는 prod ready 검증 불가                                                | Worker C scope = "dry-run + runbook" → **"Cloud Run topology gap audit + runbook"** + Sprint 34 unresolved gap 목록                                                                                                                                |
| **P1-3** | dogfood Day 5 = 6~7 borderline 에서 polish + Beta prep + tooling + chart + e2e + Day 6 동시 = over-scope. "BL 7건 Resolved" = 과장 | Sprint 33 **필수 3 BL** (BL-164 + BL-174 list-only + pre-push hook 선행) + **stretch 3 BL** (BL-150 + BL-071 audit + BL-166). BL-150 = 2-3h kill criterion. Resolved → **Partial / Follow-up required**. **iter cap 2 유지하되 P1 개수 제한 제거** |

**운영 규칙 갱신:** P1 ≤1건 한도 = 잘못된 운영 규칙 (codex challenge). 발견 P1 모두 반영 + scope 줄여 적용. iter cap 2 만 유지.

---

## 3. 5 PR 핵심 디자인 결정

### PR #141 (step 0) hook — codex P1-1 surgery

- 메인 세션 선행 commit (Worker D 삭제 + 작업 흡수)
- `.husky/pre-push` 상단 30 line 추가:
  - main worktree (`git_dir == git_common_dir`) 차단 + path/git_dir/common_dir 출력 + exit 1
  - `QB_PRE_PUSH_BYPASS=1` 명시 우회 + bypass 로그
  - worker worktree 는 path 출력만 + 통과
  - 기존 FE/BE 검사 보존
- dry-run 검증: `bash -n` ✅ / REJECT_EXIT=1 / BYPASS_EXIT=0
- **자율 병렬 worker isolation 영구 차단 — Sprint 32 lesson 즉시 적용**

### PR #143 (Worker B) BL-164 — SelectWithDisplayName helper

- `frontend/src/components/ui/select-with-display-name.tsx` 신규 (UI primitive, generic)
- `live-session-form.tsx` strategy + exchange dropdown 2개 교체 (interval = 정적 옵션 scope 외 유지)
- base-ui `<Select.Value>` render prop 캡슐화 — UUID/raw value 노출 자동 차단
- `emptyMessage` / `triggerTestId` / `ariaLabel` / `disabled` 옵션 + `onValueChange (string|null) → string` 어댑터
- 회귀 테스트 5 case
- Sprint 34+ 다른 dropdown 도 동일 helper 통일 가능

### PR #145 (Worker A) BL-150 partial — Activity Timeline 2-pane

- `live-session-detail.tsx` Activity Timeline 만 lightweight-charts 로
- 2-pane 분리 (top: entries/closes counts / bottom: equity USDT 옵션) — EquityChartV2 60/40 패턴 정합
- `trading-chart.tsx` wrapper 재사용 — 직접 lightweight-charts 호출 X (Sprint 30 BL-157 currentColor fallback 자동 안전)
- React Compiler memoize 호환 위해 수동 useMemo 제거
- 회귀 테스트 17 case (live-session-detail 5 + activity-timeline-chart 12)
- ErrorBoundary 미발동 jsdom 통합 테스트 검증
- **2-3h kill criterion ~30분 여유 통과**
- **walk-forward + monte-carlo Sprint 34 defer** (lightweight-charts native bar chart 미지원)

### PR #142 (Worker C) BL-071 audit — codex P1-2 surgery

- 코드 변경 0
- `docs/07_infra/cloud-run-runbook.md` 신규 (393 lines) — 7 절:
  1. Background — Sprint 30 ε B1/B3/B6 자산 인용
  2. Topology decision matrix — api/worker/beat/ws_stream × Cloud Run service vs job vs single-instance
  3. healthz Celery 의존이 Cloud Run readiness probe race 위험 분석 (옵션 A `/livez` 분리 권장)
  4. Env 매핑 — `.env.example` 30+ 키를 plain env / Secret Manager / Cloud SQL connector 분리
  5. Deploy step dry-run sketch
  6. **Sprint 34 unresolved gap 16건** (P0 8 / P1 5 / P2 3): TimescaleDB hosting / VPC Connector / IAM SA / Cloud SQL connector / Secret Manager / 도메인 / healthz / worker HTTP listener 워크어라운드 등
  7. Sprint 34 deploy 실험 plan sketch (Phase 1-4)
- 핵심 발견:
  - docker-compose 안 backend-api service 미정의 (host `make be` 로 실행)
  - `docker-entrypoint.sh` 는 ws-stream role 미분기 (G9 gap)
  - worker / beat HTTP listener 없음 → Cloud Run dummy port listen 강제 (G8 P0 blocker)
  - TimescaleDB extension on Cloud SQL 공식 미지원 → self-host vs TimescaleDB Cloud vs Fly Postgres 결정 필수 (G1 P0 blocker)

### PR #144 (메인) BL-174 list-only

- `LiveSessionStateView` 신규 (live-session 도메인 전용, trading-empty-state pattern 복제 + variant)
- `live-session-list.tsx` 3 state 통일:
  - Loading: Loader2 spinner + "로드 중" + testid `live-session-loading`
  - Failed: AlertCircle + "로드 실패" + error.message + testid `live-session-error`
  - Empty: Plus + "활성 Live Session 이 없습니다" + testid `live-session-empty` (기존 testid 보존)
- detail 분기는 Worker A BL-150 와 충돌 회피로 **Sprint 34 defer 또는 별 commit**
- 회귀 테스트 4 case
- scope = live-session 1 도메인 한정 (Sprint 34+ generic refactor 후보)

### PR #147 (메인 hotfix #2) BL-176 — SelectWithDisplayName null skip

- **dogfood Day 6 발견**: `/trading` Live Sessions 탭에서 strategy/exchange dropdown 조작 시 Runtime ZodError (`exchange_account_id: invalid_format`)
- root cause: Worker B BL-164 PR #143 의 `select-with-display-name.tsx:89` `handleValueChange` 가 base-ui `(string|null) → string` 변환 시 `null → ""` 어댑터. form 의 zod UUID schema 가 `""` reject → ZodError
- hotfix: `v=null` 시 callback skip → form prior valid value 보존. 사용자 의도적 unset 동선은 별도 clear button 추가가 정합 (현재 form 은 X)
- 회귀 테스트 2 case (null skip + UUID forward) + 전체 frontend 398 tests pass / 회귀 0건
- 신규 BL-176 등록 (P2, Sprint 34 follow-up — clear 동선 정합화)

### PR #146 (메인 hotfix #1) BL-175 — Buy & Hold 거짓 trust 차단

- **dogfood Day 6 발견**: 사용자가 백테스트 결과 화면에서 Buy & Hold line 이 chart 안 미렌더 (legend 표시되나) 발견
- root cause = `frontend/src/features/backtest/utils.ts:290` `computeBuyAndHold` 가 `initialCapital * (last_equity / first_equity)` 로 BH 계산. 이는 buy & hold 의미가 아니라 strategy equity 의 first/last 비율 → BH line 이 strategy line 과 거의 동일 → 두 line 겹쳐 보이지 않음
- 자본 초과 손실 (BL-156 mdd_exceeds_capital=true) 시 BH 도 음수 → Sprint 30 ADR-019 Surface Trust Pillar 위반
- **임시 mitigation (Sprint 33)**: `computeBuyAndHold` 빈 배열 반환 → benchmark series 미렌더 + EquityChartV2 의 `showBenchmark=false` → ChartLegend BH 항목 자동 hide. 거짓 trust 즉시 차단
- **본격 fix Sprint 34 BL-175**: backend `BacktestMetrics.buy_and_hold_curve` 신규 + OHLCV 첫/끝 가격 기반 정확 계산 (`initialCapital * (last_BTC_price / first_BTC_price)`) + frontend 자체 계산 폐기
- 회귀 테스트 6 case rewrite (모든 case 빈 배열 반환 + 자본 초과 손실 scenario 명시) + equity-chart-v2.test.tsx legend test 갱신 (BH 항목 hide 검증)
- 전체 frontend 396 tests pass / 회귀 0건

---

## 4. 자율 병렬 worker 패턴 — isolation 영구 차단 ✅

### Sprint 32 lesson 재발 방어 검증

- Worker A/B/C 모두 자체 worktree 안에서만 commit + push
- 모든 worker push 직전 PR body 에 `pwd` + `git rev-parse --show-toplevel` 출력 캡처 (Worker B/C 명시 확인)
- **main worktree branch swap 0건** (Sprint 32 = 2건 → Sprint 33 = 0건)
- pre-push hook 가 worker worktree 정상 인식 ("worker worktree" 메시지 출력) 후 정상 push

### Worker D 삭제 결정 (codex P1-1 surgery)

- Sprint 32 plan = D worker 가 hook 추가 + 최후 머지
- codex challenge = "같은 메커니즘 재신뢰는 부정확. Sprint 32 에서 이미 실패한 방어"
- 메인 세션 step 0 으로 hook 선행 commit + push + 머지 → 모든 worker 가 이미 보호된 상태
- **본 sprint 자체에서 즉시 차단 검증**

### worker worktree cleanup

- Sprint 32 = 머지 후 stale worktree 자동 cleanup X (사용자 manual)
- Sprint 33 = `git worktree unlock + remove --force` + branch -D + fetch --prune sequence 로 자동 처리

---

## 5. dogfood Day 6 self-assess (사용자 입력 대기)

| Day       | 점수             | progress                                                                         |
| --------- | ---------------- | -------------------------------------------------------------------------------- |
| Day 3     | 4                | baseline                                                                         |
| Day 4     | 5                | +1 (Sprint 31 6 PR 효과)                                                         |
| Day 5     | 6~7 (borderline) | +1.5 (Sprint 32 7 PR 효과)                                                       |
| **Day 6** | **5**            | **-1.5~2 (regression — Sprint 33 Surface fix +N vs BUG 3건 발견 -M = net 하락)** |

**Surface fix 효과 정량 (sprint progress / sprint):**

- Sprint 30 (8 PR) → +0
- Sprint 31 (6 PR) → +1
- Sprint 32 (7 PR) → +1.5
- **Sprint 33 (7 PR) → -1.5~2 (regression — BUG 3건 발견 효과)**

### 사용자 코멘트 (정성)

- 직관 점수 5/10. 부문별 채점 생략 (사용자 자체 dogfood, BUG 3건 발견 자체가 점수 함의)
- Sprint 33 의 5 BL Resolved + 2 hotfix 효과 (+ portion) vs dogfood 발견 BUG 3건 (- portion) = net -1.5~2 점

### gate 판정

- **≥7 미달** → BL-005 ✅ Resolved trigger **미도래**
- **Sprint 34 분기 결정 = polish iter 2** (Beta 본격 진입 미루기)
- Sprint 34 우선순위: BL-175 본격 fix (backend `buy_and_hold_curve`) / BL-177 chart marker / BL-166 uvicorn / BL-176 follow-up / BL-174 detail
- Sprint 34 후 dogfood Day 7 재측정 → ≥7 도달 시 → Sprint 35 Beta 본격 진입

### Day 6 별 dev-log

- 상세: [`docs/dev-log/2026-05-05-dogfood-day6.md`](2026-05-05-dogfood-day6.md)

---

## 6. Sprint 34 분기 후보

### 사용자 결정 prereq (Sprint 34 본격 시작 전)

- **dogfood Day 6 ≥7 안정 여부 (본 retro 입력 대기)**
- **BL-070 도메인 결정** (사용자 manual)
- **BL-071 unresolved gap 16건 처리 우선순위** (특히 P0 8건: TimescaleDB hosting / VPC connector / IAM SA / Cloud SQL connector / Secret Manager / 도메인 / healthz / worker HTTP listener)

### Sprint 34 BL 후보 (defer 항목)

- **BL-166** uvicorn watch list `.env*` 미포함 root cause fix (Sprint 33 plan 가정 noop 발견 → Sprint 34 정확한 fix)
- **BL-150 잔여** walk-forward + monte-carlo (lightweight-charts native 미지원 → Recharts 유지 또는 custom rendering)
- **BL-071 본격 deploy 실험** (Phase 1 prereq 부터)
- **BL-070 + BL-072** 도메인 + DNS + Resend (사용자 manual + DNS 24h 전파)
- **BL-073~075** 캠페인 + 인터뷰 + H2 게이트

---

## 7. 신규 lessons / BL 갱신

### 영구 lesson 후보 (3회 반복 시 `.ai/common/global.md` 승격)

1. **plan agent 가정 검증 필수** — BL-166 plan agent 가정 (`cache_clear()` lifespan)이 noop 발견 (lru_cache + module-level singleton 모두 process scope = uvicorn `--reload` 시 자동 reset). 실제 fix 적용 전 가정 재검증 의무
2. **codex 운영 규칙은 challenge 가능** — "P1 surgery ≤1건 한도" = 잘못된 운영 규칙. memory feedback `feedback_codex_g0_pattern.md` 갱신 완료 (P1 개수 제한 X, scope 축소 우선)
3. **자율 병렬 worker isolation 영구 차단** — pre-push hook hybrid (reject + bypass env) + 메인 세션 step 0 선행 패턴. Sprint 32 lesson 본격 영구 적용 검증 (Sprint 33 main worktree swap 0건)
4. **dogfood = critical BUG 발견 mechanism** (Sprint 33 BL-175 + BL-176 + BL-177 발견 — 본 sprint 만 3건) — automated test (vitest 398 + e2e all pass) 가 잡지 못하는 (a) trust 위반 (BL-175 BH legend mismatch) (b) base-ui transient null state ZodError regression (BL-176) (c) chart marker readability (BL-177 BL-171 follow-up) 을 실 사용자 dogfood 가 잡음. production-quality 검증의 마지막 gate 로 dogfood 의 가치 확정. test 만으로는 충분치 않음 → **Sprint 종료 직전 dogfood = 영구 의무 step**
5. **base-ui Select edge case 미커버 lesson (BL-176)** — Worker B BL-164 PR #143 의 5 case test 가 happy path (UUID forward) 만 검증. base-ui `onValueChange` 시그니처 `(string | null)` 의 `null` transient state 는 mock 안에서 미트리거 → form zod schema 와 runtime 충돌. **신규 helper component 작성 시 base-ui callback edge case (null / undefined / clear) 검증 의무** — Worker prompt 강화 후보
6. **plan/retro URL 안내 검증 의무** — 본 sprint dogfood 안내 메시지에서 `/live-sessions/*` URL 명시 (실제 = `/trading` 탭 안). 사용자가 직접 BUG 보고 시점에야 발견. **plan agent 의 critical files 명시 = 좋으나 사용자-facing URL 도 명시 의무** (특히 dogfood 동선 안내 시)

### BL 변동

- **Resolved (Sprint 33 7 PR):** BL-164 / pre-push hook tooling (신규) / BL-176 hotfix (Sprint 33 안 fix 완료)
- **Partial / Follow-up required:** BL-150 (Activity Timeline 만, walk-forward+monte-carlo Sprint 34 defer) / BL-071 audit (runbook + 16 unresolved gap, 실제 deploy Sprint 34) / BL-174 (list-only, detail Sprint 34 defer) / **BL-175 hotfix** (BH series hide, backend 정확 계산 Sprint 34)
- **defer Sprint 34:** BL-166 (root cause = uvicorn watch list `.env*` — plan 가정 noop 검출), BL-070 (도메인 미정), BL-150 walk-forward+monte-carlo, **BL-175 본격 fix (backend `buy_and_hold_curve` + OHLCV 가격 기반)**, **BL-177 chart marker readability** (Sprint 32 BL-171 follow-up)
- **신규 등록 (Sprint 33)**: BL-175 (P1, BH 정확 계산, Sprint 34 fix prereq) / BL-176 (P2, SelectWithDisplayName clear 동선 정합화 — hotfix Resolved + Sprint 34 follow-up) / **BL-177 (P2, chart marker readability — dogfood Day 6 발견, Sprint 32 BL-171 follow-up)**
- **합계 변동:** 80 → 81 BL (Resolved 2 + Partial 4 + tooling 신규 1 + 신규 BL 3건 BL-175/176/177)

---

## 8. 자율 병렬 worker 실측 (Sprint 33 통계)

| 항목                        | 값                                                                                      |
| --------------------------- | --------------------------------------------------------------------------------------- |
| Worker spawn                | A/B/C 3 worker 동시 (메인 step 0 hook 머지 후)                                          |
| Worker D                    | **삭제** (codex P1-1 surgery — 메인 step 0 흡수)                                        |
| 메인 세션 직접 PR           | 4 (#141 hook step 0 + #144 BL-174 list-only + #146 BL-175 hotfix + #147 BL-176 hotfix)  |
| **Total PR**                | **7** (codex P1-1 후 6 → BL-166 defer 로 5 → dogfood Day 6 BL-175+BL-176 hotfix +2 = 7) |
| Worker isolation 위반       | **0건** (Sprint 32 = 2건, P1-1 surgery 효과 검증)                                       |
| `--no-verify` 사용          | 0건                                                                                     |
| `QB_PRE_PUSH_BYPASS=1` 사용 | 메인 세션 4회 (step 0 hook PR + BL-174 PR + BL-175 hotfix PR + BL-176 hotfix PR)        |
| CI green                    | 모두 pass (frontend/e2e/live-smoke + backend/changes/ci)                                |
| 머지 정책                   | 메인 세션 직접 머지 (squash + delete-branch)                                            |
| 자율 병렬 worker 평균 시간  | ~5-8min (Worker A 30min / B 6min / C 5min)                                              |

---

## 9. dual metric

- **7 PR** (codex P1-1 surgery 후 + dogfood Day 6 hotfix 2건)
- **vitest 398 tests** (Sprint 32 baseline 371 + 27 신규, 회귀 0건)
- **backend pytest 1572 tests** (isolated env)
- **mypy 0 / ruff 0 / tsc 0 / eslint 0**
- **codex G.0 124k tokens** (Sprint 32 145k 대비 ↓ — iter cap 2 + scope tighter)
- **dogfood self-assess Day 5 → Day 6 = TBD** (BL-175 hotfix 후 재측정)
- Surface fix 효과 = TBD / sprint (Sprint 32 = +1.5 / Sprint 31 = +1 / Sprint 30 = +0)

---

## Cross-link

- Plan: `~/.claude/plans/sprint-33-humming-quiche.md` (codex G.0 P1 surgery 3건 반영)
- codex session: `019df729-8c98-7130-b265-0ba62f4993ff`
- 직전 Sprint 32 retro: `docs/dev-log/2026-05-05-sprint32-master-retrospective.md`
- ADR-019 (Surface Trust): `docs/dev-log/2026-05-05-sprint30-surface-trust-pillar-adr.md`
- BACKLOG: `docs/REFACTORING-BACKLOG.md` (변경 이력 entry 갱신)
- BL-071 runbook: `docs/07_infra/cloud-run-runbook.md` (Sprint 33 신규)
- dogfood Day 6 dev-log: `docs/dev-log/2026-05-05-dogfood-day6.md` (사용자 점수 입력 후 작성)
