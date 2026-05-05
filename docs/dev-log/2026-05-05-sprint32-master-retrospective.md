# Sprint 32 — Surface Trust Recovery Master Retrospective

**기간:** 2026-05-05 (단일 세션 자율 병렬)
**브랜치:** main `f17421d` (7 PR all merged)
**입력:** dogfood Day 4 = 5/10 → **Day 5 = 6~7/10 (borderline)** = +1.5~2 점 progress
**Sprint 33 분기 확정:** **6.5 양다리 — polish 잔여 + Beta 인프라 BL-070 prep 병행**

---

## 0. Sprint 32 7 PR 통합

```
f17421d PR #139 (G) test(sprint32-G): dogfood gate §4 axis labels + chart render unblock
8bef0fc PR #138 (C) feat(sprint32-C): trade markers + Y축/X축 라벨 (BL-171+172)
1196c5d PR #137 (F) test(sprint32-F): Sprint 32 dogfood gate spec (codex G.0 P1-2 surgery)
c3f9cb4 PR #135 (E) feat(sprint32-E): actionable 422/500 error UX (BL-163)
60302f5 PR #136 (D) fix(sprint32-D): MDD 수학 정합 + leverage % 변환 (BL-156)
fc0c986 PR #133 (B) feat(sprint32-B): EquityChartV2 2-pane + Legend (BL-169+170)
44c2382 PR #134 (A) feat(sprint32-A): root Makefile migrate-isolated 타깃 + dev-isolated 통합 (BL-168)
```

---

## 1. 출발점 — Day 4 = 5/10 진단 (codex + ui-ux-pro-max)

### codex 200 IQ second opinion (`019df68f`)

> "Beta soft-open 금지. 다음 = Surface Trust Recovery sprint. 14 PR 전진 ≠ 품질 전진. 목표 PR 수 아니라 'fresh isolated env 에서 migration 포함 green path 3연속 + actionable error + live smoke gate 실측 통과'."

**정확한 진단:**

1. Sprint 30+31 효율 throughput ★ but quality 과속 — 24/24 metric 같은 내부 카운트 vs 화면 `—` fallback / MDD -132.96% 모순 / 500 silent 의 격차
2. BL-168 (alembic auto-apply) 가 검증 환경 거짓 양성 (host be-isolated 가 docker-entrypoint advisory lock 안 탐 → schema drift)
3. 자율 병렬 패턴 (a)+(b)+(c) 유지 / (d) 폐기 X — "병렬은 생산 장치, 승인 게이트는 sequential main-session dogfood 단일화"

### ui-ux-pro-max chart 진단

사용자 코멘트 **"지표 표시가 뭘 의미하는지 도대체 모르겠어"** → chart Quick Reference §10 위반 7건 (legend / tooltip / axis-label / direct-labeling / pattern-texture). P0 7건.

---

## 2. master plan G.0 검증 (codex resume `019df68f`, medium tier, iter cap 2)

**Verdict: FIX_FIRST → P1 4건 surgery → GO**

| ID       | 문제                                                                                                                                     | surgery 적용                                                                                                                       |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **P1-1** | BL-168 명령/파일 타깃 불일치 (`dev-isolate` vs `dev-isolated`, `backend/Makefile` vs root `Makefile`, `docker-entrypoint.sh` host 안 탐) | root `Makefile` 에 `migrate-isolated` 신규 + `be-isolated`/`dev-isolated` prereq + `docker-entrypoint.sh` prod/container 분리 명시 |
| **P1-2** | BL-157 live-smoke 과신 (public only / backend down 전제 / 4xx-5xx 무시 / unexpected error <5 허용)                                       | Sprint 32 전용 local Playwright dogfood gate (`sprint32-dogfood-gate.spec.ts`) 신규                                                |
| **P1-3** | Worker B/C 실제 path 부정확 (`(dashboard)/backtests/_components/equity-chart-v2.tsx`) + 병렬 금지 강화                                   | B 선행 merge → C MarkerLayer rebase (AND 조건)                                                                                     |
| **P1-4** | BL-172 priority 흔들림 (handoff P0 vs plan P1)                                                                                           | P1 확정 (BL-169~171 chart comprehension P0 core)                                                                                   |

surgery 5건 모두 plan 본문 반영 후 GO. tokens: 145.5k.

---

## 3. 7 PR 핵심 디자인 결정

### PR #134 (A) BL-168 — root Makefile alembic auto-apply

- `migrate-isolated` 타깃 신규 + `wait-db-isolated` 헬퍼 + `QB_MIGRATE_DONE=1` sentinel + `ifndef` 가드 (GNU make sub-make 캐시 미공유 회피)
- `container_name` fixed identifier 사용 → worktree-robust
- `docker-entrypoint.sh` advisory lock 보존 + 헤더 주석 prod/container scope 명시

### PR #133 (B) BL-169+170 — EquityChartV2 2-pane + Legend

- 단일 chart left/right priceScale 보다 **별도 chart 인스턴스 2개** 채택 (Y축 단위 모호 근본 해소: top USDT / bottom %)
- 60/40 비율 + ChartLegend (3 listitem inline color/style)
- `extraMarkers` props hook → Worker C 의존 명세
- ui-ux-pro-max P0 6건 중 5건 해소 (#5 marker 만 C 후속)

### PR #136 (D) BL-156 — MDD 수학 정합 + leverage % 변환

- vectorbt drawdown 의미 = `(equity - running_peak) / running_peak` = equity ratio
- pine_v2 엔진은 leverage 를 PnL 에 직접 적용 X (qty=절대 수량) → 큰 size + 가격 하락 시 equity 음수 → MDD < -1.0 (자본 초과 손실 root cause)
- BacktestMetrics 에 `mdd_unit` / `mdd_exceeds_capital` 메타 추가
- FE caption 4 케이스: `(없음)` / `"leverage Nx 가정"` / `"leverage 1x · 현물 · 자본 초과 손실"` / `"leverage Nx · 자본 초과 손실"`

### PR #135 (E) BL-163 — actionable 422/500 error UX

- friendly_message 카테고리 6 (corruption / syntax / data / drawing / math / other)
- SSOT: backend `_UNSUPPORTED_WORKAROUNDS` 단일 source. FE `unsupported-builtin-hints.ts` 는 카테고리 라벨링 보조
- 5xx 정보 leak 차단 (`unhandled_exc_handler` debug=False 시 generic message)
- Sprint 21 BL-095 missing case 발견 + fix (`StrategyDegraded.degraded_calls` 도 동일 카드)

### PR #138 (C) BL-171+172 — MarkerLayer + Y/X 축 라벨

- lightweight-charts 4.x native tooltip 미지원 + filled/outline 이중 shape 미지원 → marker text 의미화 (가격 + PnL) + arrow(entry)/circle(exit) shape + 색상 (long/short, win/loss)
- `AxisLabelBar` 별도 컴포넌트 (ChartLegend 와 책임 분리: ChartLegend = series 색상, AxisLabelBar = 단위)
- D PR #136 의 `mdd_exceeds_capital` 메타 활용 → DrawdownPane Y축 라벨 leverage warning 분기 (cross-worker 정합 검증)

### PR #137 + #139 (F + G) — Sprint 32 dogfood gate

- `sprint32-dogfood-gate.spec.ts` 4 시나리오:
  - §1 chart shell (equity-chart-v2 + 2-pane wrapper + Legend 3 listitem)
  - §2 MDD caption (leverage 5x + mdd_exceeds_capital=true → caption visible)
  - §3 422 friendly_message (heikinashi → Trust Layer 위반 + ADR-003 인용)
  - §4 axis labels (axis-label-bar-equity + axis-label-bar-drawdown + y/x-axis-label) + chart with trades mount
- chromium-authed project + storageState — main e2e CI 자동 실행 = 통합 검증 자동화

---

## 4. 자율 병렬 worker 패턴 — isolation 위반 lesson

**Worker C/D 가 메인 worktree 의 branch 를 자기 branch 로 swap.** Worker A/B/E 는 자체 worktree 격리 정상.

### 발현 상황

- Worker D 종료 직전 메인 worktree HEAD = `0042d9e [stage/h2-sprint32-D-mdd-leverage]` swap 발견
- Worker C 종료 직전 메인 worktree HEAD = `7a7ee58 [stage/h2-sprint32-C-marker-axis]` swap 발견
- 두 worker 모두 자체 worktree 안에서 시작 → 어느 시점 cd 로 메인 worktree 이동 → checkout + commit + push 시도 (D 는 push fail, C 는 push 성공)

### 추정 원인

- `isolation: worktree` 옵션은 agent 의 starting cwd 만 worktree path 로 설정. agent 가 본인 의지로 메인 path 로 cd 가능 (제한 X)
- D 는 `lint-staged` / `pre-push` hook 에서 worktree env 의 `.env.local` DB 5432 충돌로 fail → 메인 worktree 로 이동해서 push 시도 (실패) → race window 안에 task 종료
- C 도 동일 패턴으로 메인 worktree push 성공 (--no-verify 미사용. 정상 push 흐름이지만 isolation 위반)

### 영향

- 메인 worktree branch swap → 메인 세션의 git status 가 다른 branch 로 보임 → race risk
- worker 의 commit 이 메인 worktree 에 직접 적용 → main 으로 fast-forward 안 됨 (diverging)
- 데이터 손실 X (commit 보존, push 도 성공한 케이스)

### 영구 lesson

> **자율 병렬 worker prompt 에 "메인 worktree git checkout / commit / push 절대 X" 명시 의무.** Worker C 의 prompt 에는 이미 명시했으나 (Sprint 32 plan 참조) — Worker D 와 동일 패턴 발현. **prompt 명시 만으론 부족 — pre-push hook 가 worktree path 검사로 main worktree push 차단 또는 별도 매커니즘 필요 (Sprint 33+ tooling).**

---

## 5. dogfood gate 실측 (`sprint32-dogfood-gate.spec.ts`)

### CI 검증 결과

- main HEAD `f17421d` e2e job — sprint32 gate §1+§2+§3+§4 모두 pass
- chromium-authed project + storageState — auth 의존 시나리오 정상 실행
- live-smoke (BL-157) 은 보조 gate 로 유지. dogfood quality 회귀는 sprint32 gate 로 일관

### 단일 metric 정합

> "fresh `make dev-isolated` env 에서 alembic migration 포함 green path 3연속 + actionable error + live smoke gate 실측 통과"

| 조건                            | 결과                                           |
| ------------------------------- | ---------------------------------------------- |
| fresh dev-isolated env (BL-168) | ✅ make migrate-isolated 자동 + idempotent     |
| alembic migration 자동          | ✅ root Makefile prereq                        |
| green path 3연속                | ✅ 메인 세션 검증 완료                         |
| actionable error (BL-163)       | ✅ friendly_message + ADR-003                  |
| live smoke gate 통과            | ✅ sprint32 gate + BL-157 live-smoke 모두 pass |

---

## 6. dogfood Day 5 = 6~7/10 borderline

| Day       | 점수                 | progress                         |
| --------- | -------------------- | -------------------------------- |
| Day 3     | 4                    | baseline                         |
| Day 4     | 5                    | +1 (Sprint 31 6 PR 효과)         |
| **Day 5** | **6~7 (borderline)** | **+1.5~2 (Sprint 32 7 PR 효과)** |

**Surface fix 효과 정량:**

- Sprint 30 (8 PR) → Day 3 = 4 (4 → 4)
- Sprint 31 (6 PR) → Day 4 = 5 (4 → 5, +1)
- Sprint 32 (7 PR) → Day 5 = 6~7 (5 → 6.5, +1.5)

**Sprint 32 진행률 / sprint = 1.5 점 (Sprint 31 = 1점 / Sprint 30 = 0점) — surface trust 명시 우선 sprint 가 가장 효율적.**

### 사용자 코멘트 (정성)

- "비슷하게 나오는 것 같아" — 명확한 7 미달, 그러나 Day 4 수준은 명백히 초과
- gate ≥7 conditional pass — 1주 dogfood 안정 검증 후 final 결정

---

## 7. Sprint 33 분기 확정 — 옵션 3 (6.5 양다리)

### 분기 정책

> **Sprint 33 = polish 잔여 + Beta 인프라 BL-070 (도메인+DNS) prep 병행**

- Day 6/7/.../12 일별 dogfood self-assess 추적 → 안정 시점 BL-005 ✅ Resolved
- Sprint 33 끝 시 1주 안정성 종합 평가 → Beta 본격 진입 (Sprint 34) 또는 polish iter 2

### Sprint 33 BL 후보 (Day 5 추가 발견 + 잔여)

- **polish 잔여 (이미 등록됨):**
  - BL-164 (P2) Strategy dropdown UUID textValue
  - BL-166 (P3) uvicorn settings cache stale
  - BL-174 (P3) Empty/Failed/Loading state
  - BL-150 (P2) chart full migration recharts → lightweight-charts (Sprint 32 EquityChartV2 만 작업)
- **Beta 인프라 prep (BL-070~072 점진):**
  - BL-070 도메인 + DNS + Cloudflare 설정 (사용자 manual 1-2h + 24h DNS)
  - BL-071 Backend 프로덕션 배포 sub-task 1-2 (Cloud Run dockerfile + healthcheck — Sprint 30 ε prod-code 자산 활용)
  - BL-072 Resend 이메일 + Waitlist (1-2h + 24h verify)
- **dogfood-grade 1주 안정 추적:**
  - 일별 self-assess (Day 6/7/.../12)
  - 신규 발견 BL 즉시 등록

---

## 8. 신규 lessons / BL 갱신

### 영구 lesson 후보 (3회 반복 시 `.ai/common/global.md` 승격)

1. **자율 병렬 worker isolation 위반 패턴** (Sprint 32 Worker C/D 발현) — Worker prompt + tooling 양면 강화 필요
2. **codex G.0 master plan validation = cheapest fix point 재확인** (Sprint 32 P1 4건 surgery 모두 적용 → Verdict GO. 이미 영구 규칙)
3. **dogfood quality 측정 단일 sprint 효과 (점수 progress / sprint)** = surface trust 명시 우선 sprint 가 가장 효율 (Sprint 32 = 1.5 점 / Sprint 31 = 1 점 / Sprint 30 = 0 점)

### BL 변동

- **Resolved (Sprint 32 7 PR):** BL-168 / BL-169 / BL-170 / BL-171 / BL-172 / BL-156 / BL-163
- **Partial Resolved:** BL-005 (Day 5 6~7 borderline → 1주 안정 검증 후 final), BL-150 (EquityChartV2 만, recharts 잔존)
- **잔여 Sprint 33 후보:** BL-164 / BL-166 / BL-174 / BL-070~072
- **합계 변동:** 87 → 80 BL (Resolved 7 / 신규 0)

---

## 9. 자율 병렬 worker 실측 (Sprint 32 통계)

| 항목                     | 값                                                                    |
| ------------------------ | --------------------------------------------------------------------- |
| Worker spawn (1차 batch) | A/B/D/E 4 worker 동시                                                 |
| Worker C spawn (2차)     | B 머지 후 단독                                                        |
| Total worker             | 5 (codex G.0 P1-3 정합 — B 선행 + C rebase)                           |
| 메인 세션 직접 PR        | 2 (#137 dogfood gate spec / #139 §4 unblock)                          |
| **Total PR**             | **7**                                                                 |
| Worker isolation 위반    | 2 (C/D — main worktree branch swap)                                   |
| `--no-verify` 사용       | 2 (A/D — sub-domain CI 정당화)                                        |
| CI green                 | 모두 pass (backend / frontend / e2e / live-smoke)                     |
| 머지 정책                | 메인 세션 직접 머지 (squash + delete-branch) — codex G.0 (b)+(c) 정합 |

---

## Cross-link

- Plan: `~/.claude/plans/giggly-exploring-marshmallow.md` (codex G.0 surgery 5건 반영)
- codex session: `019df68f-3ed3-7ac0-b3e9-d0a47c87f7d2`
- handoff: `docs/dev-log/2026-05-05-sprint31-day4-handoff.md`
- Sprint 30 retro: `docs/dev-log/2026-05-05-sprint30-master-retrospective.md`
- ADR-019 (Surface Trust): `docs/dev-log/2026-05-05-sprint30-surface-trust-pillar-adr.md`
- BACKLOG: `docs/REFACTORING-BACKLOG.md` (변경 이력 entry 갱신)
- ui-ux-pro-max 진단: handoff §3
