# Sprint 38 Master Retrospective — polish iter 6 + Day 7 (a) FAIL + Sprint 39 = polish iter 7

**기간**: 2026-05-06 ~ 2026-05-07
**브랜치**: `main @ b61b16c` (변경 X) + `stage/sprint38-bl-188-bl-181 @ 8a23f29` (4 PR squash merged, **stage 보존 — Sprint 39 베이스**)
**활성 sprint type**: polish iter 6 (Sprint 37 Day 7 = 6/10 (a) FAIL → Sprint 38 = +1 시도)
**self-assessment Day 7.5/8**: **5/10 (gate (a) FAIL)** — CPU loop +113% delta vs main 검출 (BL-189 신규 P0)
**다음 분기**: Sprint 39 = **polish iter 7** (BL-189 CPU loop 진단 + hotfix + Day 7 재측정)

---

## 1. Context — 왜 Sprint 38 가 필요했나

Sprint 37 Day 7 self-assess = 6/10 → gate (a) FAIL (Sprint 36 동일 점수, +1 미달성). 원인 3:

- Live Settings ↔ 백테스트 mirror 미진행 (BL-188 trust 갭)
- 사용자 hotfix `6434a1d` agent QA 누락
- BL-186 풀 leverage 모델 deferred

Sprint 38 = (a) 단일 미달 회복 polish iter 6. **BL-188 v3** = 1x equity-basis 한정 mirror + Nx reject + sessions parity (4 worker 자율 병렬) + **BL-181** (Docker worker auto-rebuild) 묶음.

---

## 2. 산출물 (stage @ 8a23f29 — main 미반영, Sprint 39 베이스)

| PR       | Worker              | scope                                                                                                                                                                                                                                                                 | 파일 변경          | tests                                                                                              | merge 시각 (UTC)      | sha             |
| -------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | -------------------------------------------------------------------------------------------------- | --------------------- | --------------- |
| **#168** | A1 (메인 세션 직접) | Shared contract: `MirrorNotAllowed` / `PinePartialDeclaration` / `SizingSourceConflict` (3 신규 422 예외) + `CreateBacktestRequest` 2 필드 + `BacktestConfig` 5 필드 + `_resolve_sizing_canonical` helper + `submit()` 통합 + `_build_engine_config` 매핑             | 8 files +1016 / -6 | +28 unit                                                                                           | 2026-05-06 08:52      | b61b16c → main  |
| **#170** | C (worker-c cmux)   | BL-181 Docker worker auto-rebuild — `docker-compose.isolated.yml` 3 서비스 prefork concurrency=2 bind-mount + watchfiles wrapper + `Makefile up-isolated-watch` + `scripts/sentinel_bl181_worker_reload.sh` + ADR (container_name 충돌 + ws-stream prefork fact 정정) | infra              | sentinel exit 0                                                                                    | 2026-05-07 00:51      | d42ddd5 → stage |
| **#171** | B (worker-b cmux)   | FE D2 manual override toggle + 4-state badge + `useStrategy` hook + Zod refine (BE parity) + `react-hook-form reset()` + scalar dep                                                                                                                                   | FE                 | +4 vitest + CPU smoke max 4.7% PASS (단독)                                                         | 2026-05-07 00:51      | efaa23d → stage |
| **#172** | A2 (worker-a2 cmux) | BE chain Live tier + `interpreter.py:1039` entry hook + `event_loop.py:96` fill hook + `virtual_strategy.py:141, :184` + `StrategyState.sessions_allowed` + tz-naive sessions-only fail-closed                                                                        | BE                 | +6 (priority chain / entry gate / fill gate / Live parity / tz-naive reject / Pine partial corpus) | 2026-05-07 직후       | b93f1dc → stage |
| **#173** | D (worker-d cmux)   | Pine SSOT invariant 보강 + Playwright E2E 5 case (Live 1x mirror / Nx blocked / Pine override / Manual toggle / sessions=[asia])                                                                                                                                      | tests              | +invariant + 5 Playwright                                                                          | 2026-05-07 (CI green) | 8a23f29 → stage |

**stage diff vs main** = **33 files / +2426 / -74 lines / +38 신규 tests**.

---

## 3. Day 7 4중 AND gate 결과 (영구 기준)

| Gate                                               | Sprint 37 | Sprint 38 (Day 7.5/8) | 근거                                                                                                                                   |
| -------------------------------------------------- | --------- | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **(a)** self-assess ≥7/10 + 근거 ≥3                | 6/10 FAIL | **5/10 FAIL**         | mid-dogfood Day 7.5 — FE next-server idle CPU **113% sustained** (vs main b61b16c idle 0%) → trust 무너짐 + dogfood 환경 자체 unstable |
| **(b)** BL-178 production BH curve 정상            | PASS      | PASS (main 변경 X)    | main = b61b16c 그대로. BL-178 Resolved 유지                                                                                            |
| **(c)** BL-180 hand oracle 8 test all GREEN        | PASS      | PASS (main 변경 X)    | main = b61b16c 그대로. BL-180 Resolved 유지                                                                                            |
| **(d)** new P0=0 AND unresolved Sprint-caused P1=0 | PASS      | **FAIL**              | **신규 P0 = BL-189 (CPU loop on stage @ 8a23f29 통합 후)**                                                                             |

**결과**: (a) + (d) FAIL → Sprint 39 = polish iter 7 (BL-189 hotfix + Day 7 재측정).

**핵심 lesson** — 단독 worker 환경에서 Generator-Evaluator 통과 (B 의 CPU smoke max 4.7% PASS) 한 fix 가 **통합 환경 (A2 + B + C + D 머지 후)** 에서 **CPU 113%** 회귀 발생. Day 7.5 mid-dogfood 의 falsification signal 정확히 작동 — Sprint 28 LESSON-035 dual metric 의 진정한 가치 = single-worker 못 잡는 통합 회귀 detection layer.

---

## 4. 자율 병렬 sprint cmux 결과 (Bundle 1/2 패턴 4번째 실측)

| metric                           | 결과                                                                         |
| -------------------------------- | ---------------------------------------------------------------------------- |
| 사용자 interaction               | "ok" 1회 (Phase 1 kickoff) + dogfood 결정 1회 + close-out 결정 1회 = **3회** |
| Worker spawn                     | A1 메인 세션 직접 (4-5h) + A2/B/C/D cmux 자율 (각 2-7h)                      |
| Phase 1 kickoff → 4 PR 머지 완료 | ~14h (사용자 자리비움 ≥8h, 자율 진행)                                        |
| pre-push hook 차단 회피          | `QB_PRE_PUSH_BYPASS=1` (stage push) 1회                                      |
| Worker isolation 위반            | 0건 (LESSON-035 영구 차단 검증 4번째)                                        |
| `--no-verify` 사용               | 0건                                                                          |

**LESSON-046 (신규)** — 통합 dogfood 가치. 단독 worker self-verify + Evaluator + codex G.4 P1 review 모두 PASS 통과해도 통합 환경 회귀 detection 못함. dogfood Day 7.5 falsification signal 이 유일한 detection layer.

---

## 5. BL 변경

### Resolved (1건)

- **BL-181** Docker worker auto-rebuild on PR merge — Sprint 38 worker C 가 isolated mode bind-mount + watchfiles + sentinel script + ADR 완료. PR #170. base+isolated 동시 운영 금지 ADR 안 명시 (codex iter 2 P2 #1).

### Deferred 갱신 (2건)

- **BL-188** (백테스트 폼 ↔ Live Session mirror) — Sprint 38 v3 코드 stage 머지 완료 (PR #168/#171/#172/#173) 단 main 미반영. **BL-189 CPU loop hotfix 통과 후 stage→main merge 가능**.
- **BL-186** (풀 leverage/funding/mm/liquidation 모델) — 본 sprint 38 OUT (BL-188 mirror Nx reject 가 BL-186 후 unlock). 변경 없음.

### 신규 P0 (1건)

- **BL-189** [P0, Sprint 39 mandatory] — CPU loop on stage @ 8a23f29 (FE next-server idle 113% sustained vs main 0%). Worker B 의 backtest-form.tsx reset() effect dep 코드상 정상 (5 scalar primitive + stable callback) 이지만 통합 환경에서 회귀. 진단 단계: (1) Worker D revert → CPU 측정 (D 가 원인인지 isolation), (2) 아니면 A2 + B 통합 effect → 통합 시점 hook trigger 분석, (3) Turbopack file watcher 감시 (idle 113% 가 turbopack 일 가능성도 검토). hotfix 후 Day 7 재측정.

### 합계 변동

**87** (Sprint 37 종료) **→ 87 active BL** (BL-181 Resolved -1 / BL-189 신규 +1 = ±0).

---

## 6. 신규 LESSON (lessons.md 영구 등록)

본 sprint 38 retro 에서 6건 신규 등록 + 3건 영구 승격 (LESSON-038/039/040 후보 → 3/3 통과).

### 영구 승격 (3건, status: 후보 2/3 → 영구)

- **LESSON-038** Docker worker auto-rebuild on PR merge 의무 — Sprint 35 발견 + Sprint 35 retro 2/3 + **Sprint 38 BL-181 fix 적용 = 3/3 통과** → 영구 승격
- **LESSON-039** Surface Trust 차단 ≠ 실제 fix 작동 — Sprint 35 발견 + Sprint 35 retro 2/3 + **Sprint 38 BL-189 CPU loop falsification signal = 3/3 통과** → 영구 승격
- **LESSON-040** codex G.0 wrong premise risk — Sprint 35 발견 + Sprint 35 retro 2/3 + **Sprint 38 codex iter 2 P1 #14 ws-stream solo pool 가정 wrong = 3/3 통과** → 영구 승격

### 신규 (6건, status: 1/3 후보)

- **LESSON-041** Pine partial declaration → 422 reject — `default_qty_type` 와 `default_qty_value` 둘 다 명시 또는 둘 다 생략 의무. AST corpus audit 검증.
- **LESSON-042** Sizing source 단일 입력 강제 — `position_size_pct + default_qty_*` 동시 명시 시 422 (`SizingSourceConflict`). schema validator + Zod refine 양쪽.
- **LESSON-043** Live mirror leverage parity — `strategy.settings.leverage != 1` 시 mirror reject (`MirrorNotAllowed`). BL-186 후 unlock. UI 4-state badge 안 명시.
- **LESSON-044** 메인 세션 = 표준 prefix (`feat/fix/chore/docs/test/refactor/hotfix`) / worktree 자율 병렬 워커 = `worker-*` prefix. pre-push hook 화이트리스트 (PR #163) 정합 의무. stage push 는 `QB_PRE_PUSH_BYPASS=1` env override 1회.
- **LESSON-045** isolated docker (5433/6380) ↔ host port 5432/6379 (다른 프로젝트 점유) mismatch 시 baseline preflight 실패. `TEST_DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5433/quantbridge_test + REDIS_URL=redis://localhost:6380/0 + REDIS_LOCK_URL=redis://localhost:6380/3 + CELERY_BROKER_URL=redis://localhost:6380/1` inline export 의무. `.env.local` 변경 회피 (다른 도구 영향).
- **LESSON-046** 통합 dogfood 가치 (BL-189 detection 의 정확한 use case) — 단독 worker self-verify + Evaluator + codex G.4 P1 review 모두 PASS 통과해도 통합 환경 (다중 worker 머지 후) 에서 회귀 발생 가능. Day 7.5 mid-dogfood falsification signal = 유일한 detection layer. Sprint 28 ADR-019 LESSON-035 dual metric 정합.

---

## 7. 다음 sprint 분기 (영구 룰)

**Day 7 4중 AND gate (a) + (d) FAIL** → Sprint 39 = **polish iter 7** (BL-189 CPU loop 진단 + hotfix + Day 7 재측정).

Sprint 39 mandatory:

1. **BL-189 진단 spike** — Worker 단위 revert (D 먼저 → 아니면 A2 → B) + Turbopack file watcher 검증
2. **Hotfix branch** — `feat/sprint39-bl189-cpu-loop-hotfix` (메인 세션 직접, stage @ 8a23f29 베이스)
3. **dogfood Day 7.5 재시도** — hotfix 후 idle CPU < 10% 의무
4. **Day 8 self-assess + 4중 AND gate 재측정**:
   - (a) ≥7/10 PASS + 근거 ≥3
   - (b/c/d) PASS 유지
5. **PASS 시** → stage → main merge (BL-188 v3 비로소 main 반영) → Sprint 40 = BL-003 (Bybit mainnet runbook + smoke) + BL-005 본격
6. **FAIL 시** → Sprint 40 = polish iter 8 (continuing)

**Beta 본격 진입 (BL-070~075)** = Day 7 4중 AND gate 통과 + BL-005 본격 (1-2주 mainnet) 통과 후 별도 trigger. 영구 룰.

---

## 8. 영구 자산 (Sprint 38 안 영구화)

- **BL-188 v3 코드** (stage @ 8a23f29 보존) — Sprint 39 베이스. CPU loop hotfix 후 main 반영 가능
- **BL-181 BL-181 worker auto-rebuild** (PR #170 → stage) — isolated mode bind-mount + watchfiles 영구. Sprint 35/37 stale worker 패턴 영구 차단
- **38 신규 tests** (28 A1 + 6 A2 + 4 B + invariant + 5 Playwright = 44 — 모두 stage 머지) — main 반영 시 회귀 차단 layer
- **autonomous-parallel-sprints 4번째 실측** (Bundle 1/2/3 + Sprint 38) — pattern stable
- **신규 LESSON 6건 + 영구 승격 3건** = 9건 lessons.md 영구 등록

---

## 9. 시간 견적 vs 실측

| 단계            | 견적 | 실측                                |
| --------------- | ---- | ----------------------------------- |
| A1 메인 세션    | 4-5h | ~3.5h (PR #168 머지 08:52)          |
| A2 cmux         | 5-7h | ~14h (자정 → 익일 새벽 자율)        |
| B cmux          | 3-4h | ~14h                                |
| C cmux          | 3-4h | ~14h                                |
| D cmux          | 2h   | ~2h                                 |
| dogfood Day 7.5 | 1h   | ~30분 (CPU loop falsification 발견) |
| close-out       | 1h   | ~1h                                 |
| **합계**        | ≤21h | ~21h+                               |

자율 병렬은 사용자 자리비움 시간이 wall-clock 으로 측정되지 않음 — 사용자 부재 시 cmux 가 자율 실행.

---

## 10. 오류 / 회복 / 영구 차단

### 자율 병렬 cmux 의 limitation (LESSON-046)

- 단독 worker self-verify + Evaluator 통과 ≠ 통합 환경 PASS
- Worker B 의 CPU smoke max 4.7% PASS 가 통합 환경 113% 회귀 못 차단
- 회복: Day 7.5 mid-dogfood falsification signal = detection layer 작동 → Sprint 39 hotfix

### pre-push hook 화이트리스트 정합 (LESSON-044)

- 메인 worktree (main 또는 stage 브랜치 swap 안 한 상태) 에서 stage/\* push 시 차단
- 회복: `QB_PRE_PUSH_BYPASS=1 git push` (stage 브랜치 swap 후 1회 + main 복귀)
- 영구: stage push 는 자율 병렬 sprint kickoff 시 1회 발생 — 패턴 영구 등록

### env override mismatch (LESSON-045)

- baseline preflight 첫 실행 시 다른 프로젝트 (port 5432) PostgreSQL 점유 → password mismatch
- 회복: `TEST_DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5433/quantbridge_test` 등 inline export
- 영구: `.env.local` 변경 회피 + 모든 sprint kickoff baseline preflight 시 env override 의무

---

## 11. 합계 정합

- **active BL**: 87 → 87 (BL-181 Resolved -1 / BL-189 신규 +1)
- **lessons.md**: LESSON-040 (마지막) → LESSON-046 (마지막). 6건 신규 + 3건 영구 승격
- **stage 브랜치**: 신규 (origin/stage/sprint38-bl-188-bl-181 = 8a23f29). Sprint 39 베이스
- **main**: b61b16c 그대로 (변경 X)

---

## 12. Cross-link

- 본 sprint 설계 plan v3: `~/.claude/plans/context-restore-jazzy-charm.md` (codex G.0 iter 1+2 + 사용자 surgery D2/E3/F1)
- 본 세션 plan: `~/.claude/plans/context-restore-iridescent-sunset.md` (Stage 4 후반 + Stage 5 + Stage 6 실행)
- orchestration tracker: `.claude/plans/sprint38-orchestration/tracker.md`
- 4 worker prompts: `.claude/plans/sprint38-orchestration/prompts/worker-{a2,b,c,d}.prompt`
- 직전 Sprint 37 회고: [`2026-05-06-sprint37-master.md`](2026-05-06-sprint37-master.md)
- BL-188 v3 trigger Sprint: Sprint 36 dogfood Day 7 = 6/10 + Sprint 37 polish iter 5 = 6/10 → Sprint 38 = polish iter 6

---

**Sprint 38 결론** — BL-188 v3 mirror + sessions parity 코드는 stage 에 안전하게 머지 (38 신규 tests + Generator-Evaluator + codex 통과). 단 통합 환경 dogfood 회귀 (CPU loop) 발견 → Day 7 (a) FAIL 정직 인정 → Sprint 39 = polish iter 7 (BL-189 hotfix + Day 7 재측정). LESSON-046 = autonomous parallel sprint 의 진정한 가치 = dogfood 회귀 detection. 정직한 Day 7 cycle 작동 증거.
