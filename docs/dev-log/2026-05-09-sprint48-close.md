# Sprint 48 Close-out — Architectural Deepening 2차 (BL-201/203/204) + Dogfood Phase 2 Prereq 병행

> **2026-05-09. main @ `4829543`.** Sprint 48 = ★★★★★ Option (a) = 3 BL deepening 2차 (BL-201 pine_v2 TrackRunner / BL-203 trading service 5 분할 / BL-204 trading repository 6 분할) + dogfood Phase 2 발송 prereq 동시. **회귀 0 / 4 PR 정상 머지 / Worker E audit 이슈 0 / Day 7 4-AND gate (b)+(c)+(d) PASS**.

---

## 1. 산출 (3 BL Resolved + dogfood Track 2 prereq)

| PR   | BL                                          | Worker | 변경                                                                                                                                                                            | 검증                                                                                  |
| ---- | ------------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| #243 | dogfood Track 2 docs (Day 0 prereq + Day 7) | D      | `sprint42-cohort-outreach.md` 발송 prereq 갱신 + `sprint42-feedback.md` Day 7 mid-check skeleton row + `2026-05-08-sprint42-day7-midcheck.md` codex Fix #7 (Day 7 = Day 0 + 6일) | docs only / write scope 위반 0 / Day 7 절대 날짜 references 0                         |
| #244 | BL-204 trading repository 6 분할             | B      | `repository.py` 727→23 LOC shim wrapper + `repositories/__init__.py` shim re-export + 6 신규 파일 (orders/exchange_accounts/kill_switch_events/webhook_secrets/live_signal_sessions/live_signal_events) + `test_repository_shim.py` 5 신규 test | 5 TDD test PASS / 95+ 기존 import 사이트 호환성 보존 / LESSON-019 commit-spy 18 collection 정상 |
| #245 | BL-201 pine_v2 TrackRunner                  | A      | `track_runner.py` 신규 (90 LOC) `TrackRunner._dispatch_table` (S/A/M → run_historical/run_virtual_strategy) + `compat.py:107-126` if-chain → `TrackRunner.invoke()` 단일 분기 + `test_track_runner.py` 5 TDD test | pine_v2 481→**486 PASS** (+5 신규) / BL-200 SSOT 22 PASS / 6 corpus 회귀 0 / `classify_script()` 변경 0 (codex Fix #2) |
| #246 | BL-203 trading service 5 분할                | C      | `service.py` 562→23 LOC shim wrapper + `services/__init__.py` shim re-export + 6 신규 파일 (order_service/account_service/webhook_secret_service/live_session_service/protocols) + `test_service_shim.py` 5 신규 test + `test_no_module_level_loop_bound_state.py` BL-084 audit scope 확장 | 5 TDD test PASS / Celery prefork-safe (codex Fix #4) module-level state 0 / BL-084 audit scope `services/*.py` 4 module 추가 |

**합계:** 4 PR / 24 files / 회귀 0 / 신규 +15 tests (pine_v2 +5 + trading +10).

**Worker E (BL-201 audit, audit-only):** TrackRunner caller trace 1 (compat.py:117 only) + dispatch identity 4/4 PASS + silent dead-code 0 + BL-200 SSOT 충돌 0 + ast_classifier.py 변경 0 (Sprint 8a 이후). audit report = `docs/dev-log/2026-05-09-sprint48-bl201-audit.md`. 이슈 0건. Sprint 49 추가 BL 등재 의무 없음.

---

## 2. subagent-driven-development 첫 실측 (cmux 패턴 대신)

Sprint 47 = cmux 6번째 wall-clock ≈45min. **Sprint 48 = superpowers `subagent-driven-development` 1st 실측** (사용자 명시 선택 ★★★★★).

| 항목                                  | Sprint 47 cmux 6번째    | Sprint 48 subagent-driven  |
| ------------------------------------- | ----------------------- | -------------------------- |
| 직렬 vs 병렬                          | 4 worker 병렬           | **직렬** (Red Flag: 병렬 금지) |
| Worker per BL                         | 1 worker × 1 BL         | 1 worker × 1 BL            |
| Generator-Evaluator                   | 1-pass evaluator        | **2-stage (spec + code quality)** |
| wall-clock 추정                       | 45-90min                | **5-10h** (직렬 + 2-stage review) |
| 사용자 interaction                    | 4회 (design/머지/우회/충돌) | 5회 (방향/3 결정/머지 분리/CI fix 결정/`--no-verify` 명시 승인) |
| 검증 강도                             | 1 evaluator subagent    | spec compliance + code quality 분리 |

**Trade-off:** subagent-driven 가 검증 강도 높은 대신 walltime 길음. cmux 가 walltime 단축 + 병렬성. Sprint 49+ 결정 input.

**핵심 발견:** subagent review 2-stage 도 `monkeypatch indirect dependency` 못 잡음 (PR #246 5 test FAIL CI 검출). `Python namespace 분리 원리` = shim re-export 가 module-level attribute (logger/datetime/settings) 까지는 보존 안 함 → services/* 의 자체 attribute 가 monkeypatch 대상이어야 함.

---

## 3. Day 7 4-AND Gate (Type B 의무)

| 항목                                    | 상태       | 근거                                                                |
| --------------------------------------- | ---------- | ------------------------------------------------------------------- |
| (a) self-assess ≥7/10                   | ⏳ pending | 사용자 결정 (Day 7 시점, dogfood Phase 2 mid-check)                 |
| (b) BL-178 production BH curve 정상     | ✅ PASS    | pine_v2 영역 BL-201 통합 후 481→486 PASS (회귀 0)                   |
| (c) BL-180 hand oracle 8 test all GREEN | ✅ PASS    | `test_track_runner.py` 5 신규 test + 기존 hand oracle 회귀 0       |
| (d) new P0=0 + Sprint-caused P1=0       | ✅ PASS    | 회귀 0 / PR #246 CI 5 fail = monkeypatch indirect dependency (Sprint-caused, 즉시 fix 머지 = Sprint-caused P1=0 결과) |

**(d) 주의:** PR #246 5 test fail = Sprint 48 surgery 가 노출시킨 indirect dependency. 즉시 fix 2 commit (`59218dc` + `1c80dde`) 로 main 머지 직전 해소. **Sprint-caused P1 = 0 (CI 통과 후 머지)**.

---

## 4. PREFLIGHT vs 실측 정합 (codex G.0 1회 / 100k tokens)

| codex G.0 GO_WITH_FIXES 7 fix                                  | 실측 정합                                                                        |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Fix #1: B → C 순차 (cmux 충돌 비용)                              | ✅ B 머지 후 C 진입 / import 충돌 0                                              |
| Fix #2: BL-201 invariants (D2 sizing/sessions/V2RunResult/ValueError) | ✅ Worker A 5 invariant test 보존 / classify_script 변경 0                        |
| Fix #3: Worker D scope = docs/dogfood/* + day7-midcheck.md 만 | ✅ write scope 위반 0 (TODO/backlog/sprint48-close.md 변경 0)                      |
| Fix #4: services/live_session_service.py module-level state 0 | ✅ Worker C audit test 가 module attribute 0 검증 + BL-084 scope 확장             |
| Fix #5: LESSON-064 bounded audit                              | ✅ Worker E caller trace 1 + identity 4/4 + dead-code 0 / over-engineering 0     |
| Fix #6: shim 1 sprint 유지                                    | ✅ service.py + repository.py 둘 다 1 sprint shim wrapper / Sprint 49 제거 TODO  |
| Fix #7: dogfood Day 7 = Day 0 + 6일 의무                        | ✅ Worker D day7-midcheck.md + feedback.md 절대 날짜 references 0                 |

→ **codex G.0 (100k tokens) ROI = 7 fix 중 critical mitigation 2 (BL-201 invariants + prefork-safe) + scope discipline 2 (Worker D scope + shim 기간) + dogfood policy 1 = 5 wrong assumption 사전 차단**.

**Wrong premise 사전 차단 (LESSON-040 작동):**

1. **BL-201 dispatcher 위치 정정** — Plan `interpreter.py:1057` ❌ → 실제 `event_loop.py:59 def run_historical` ✅. `compat.py:20` 가 `from src.strategy.pine_v2.event_loop import run_historical` import.
2. **BL-204 repository class 수 정정** — Plan 가정 3 class ❌ → 실제 6 class ✅ (`LiveSignalSessionRepository:440` + `LiveSignalEventRepository:597` 누락 발견).

P0 Preflight 단계에서 grep + 직접 read 로 사전 차단. Plan footnote 즉시 적용 후 codex G.0 호출 → Worker A/B prompt 에 정확한 boundary 명시.

---

## 5. CI 인프라 발견 — Sprint 48 신규

**PR #246 backend CI 5 test FAIL (subagent review 못 잡음)** — Worker C 의 `service.py` shim 이 `logger` / `datetime` / `settings` module-level attributes 를 re-export 안 함. 5 test 가 `monkeypatch.setattr(service_mod, "X", Y)` 사용. Python namespace 분리 원리로 shim 변경이 services/* 의 attribute 영향 0. spec compliance + code quality reviewer 모두 못 잡음.

**Fix:** 6 사이트 (3 test 파일) `from src.trading import service as service_mod` → `from src.trading.services import {order_service|account_service} as service_mod` 변경.

- 1차 push (`59218dc`) — 5 test 중 4 fix (1 사이트 누락)
- 2차 push (`1c80dde`) — 두 번째 사이트 (`test_service_orders_futures.py:192`) fix
- CI 결과: backend 7m55s PASS / ci 3s PASS

**LESSON-061 카운트 +1** (Sprint 48 = `--no-verify` 메인 세션 1회, 사용자 명시 승인 + 로컬 DB env hook 차단 회피). 7건 → **8건 누적**.

**신규 LESSON-065 후보 (1/3):** "subagent review 2-stage 가 monkeypatch indirect dependency 못 잡음." spec compliance reviewer 는 import path 만 검증 / code quality reviewer 는 architectural pattern 만 검증 → Python namespace 분리에 따른 attribute resolution 은 둘 다 미검증. 신규 검증 의무: PR review 시 `monkeypatch.setattr(<module>, "X", Y)` 패턴 + grep `<module>` 가 신규/리네임/분할된 module 인 경우 attribute resolution 직접 검증.

---

## 6. LESSON 정식 등재 / 카운트 갱신

**신규 등재 후보 (1/3 검증):**

- **LESSON-065 (1/3) — subagent review 2-stage monkeypatch indirect dependency miss 패턴.** PR #246 사례 = Worker C spec/code review 모두 PASS (10/10 + 5 strengths). 그러나 GitHub Actions backend job 5 test FAIL = `monkeypatch.setattr(service_module, "datetime"|"logger"|"settings", ...)` 가 shim 변경 만으로는 효과 없음 (Python namespace 분리). 향후 PR review 시 `monkeypatch.setattr(<shimmed_module>, "X", Y)` + module rename/split 영역에 한해 attribute resolution 직접 검증 의무.

**카운트 갱신 (inline 갱신, 별도 등재 X):**

- **LESSON-061** force-push / hook 우회 우회 패턴 — Sprint 44 (4건) + Sprint 46 (2건) + Sprint 47 (1건) + **Sprint 48 (1건 메인 세션 `--no-verify` push)** = **8건 누적**. 점진적 누적 패턴 = 영구 hook 절대 의무 vs 사용자 명시 승인 한도 = 운영 모델 정합. P3 close-out 시점 인지.
- **LESSON-064 첫 적용 (1/3 검증 완료)** — Sprint 47 정식 등재 후 Sprint 48 = Worker E 가 BL-201 통합 후 reverse-mapping audit 의무 수행. caller trace 1 + identity 4/4 + dead-code 0 + BL-200 SSOT 충돌 0 = audit clean. **이슈 0 = LESSON-064 의무 수행 후 false positive / negative 모두 0**. 정식 패턴 검증.
- **LESSON-040 작동 (3/3 검증 완료)** — P0 Preflight wrong premise 사전 차단 2건 (BL-201 event_loop / BL-204 6 class). 누적 검증 = Sprint 35 Slice 1a + Sprint 38 codex iter + **Sprint 48 P0 grep audit** = 3/3 통과. 정식 패턴 (이미 §7.1 등재).

---

## 7. Sprint 49 분기 옵션

dogfood Phase 2 mid-check (Day 7 ≈ Day 0 + 6일) 결과 따라 4-way 분기:

- **NPS ≥7 + critical bug 0 + 본인 self-assess ≥7** → Sprint 49 = **Beta 본격 진입 (BL-070~075)** OR **사용자 의지 second gate** (memory `feedback_beta_dual_gate_postpone.md`)
- **dogfood mixed** → Sprint 49 = **deepening 3차** (Sprint 49 의 BL 후보: Sprint 49 시점 backlog 재평가)
- **dogfood critical bug 1+ 발견** → Sprint 49 = **polish iter (해당 hotfix)**
- **mainnet trigger 도래** → Sprint 49 = **BL-003 / BL-005 mainnet 본격**

**Shim removal 의무 (BL-203/204 둘 다, Sprint 49):**
- `backend/src/trading/repository.py` shim wrapper 제거 + 95+ 기존 import 사이트 갱신 (`from src.trading.repository import X` → `from src.trading.repositories import X`)
- `backend/src/trading/service.py` shim wrapper 제거 + 동일 갱신

---

## 8. 결론

Sprint 48 = **architectural deepening 2차 + dogfood Phase 2 prereq 병행** 결정 ★★★★★ 결과 = 3 BL Resolved + dogfood Day 0 발송 prereq 갱신 + Worker E audit clean. **회귀 0 / 4 PR 정상 머지 / Day 7 (b)(c)(d) PASS**.

핵심 수확:
1. **subagent-driven-development 첫 실측** = walltime 5-10h trade-off + 검증 강도 (spec + code quality 2-stage)
2. **Wrong premise 사전 차단 2건** (LESSON-040 작동 3/3 검증)
3. **codex G.0 100k tokens GO_WITH_FIXES** 7 fix 중 5 critical mitigation 사전 차단
4. **monkeypatch indirect dependency** (LESSON-065 후보 1/3) — subagent review 2-stage 가 못 잡는 신규 패턴
5. **Worker E LESSON-064 reverse-mapping audit 첫 적용** = 이슈 0 (positive validation)

**다음 분기:** dogfood Phase 2 mid-check (~Day 0 + 6일) 결과 따라 Sprint 49 4-way 결정.
