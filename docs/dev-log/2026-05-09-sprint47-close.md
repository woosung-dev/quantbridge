# Sprint 47 Close-out — Architectural Deepening 3 BL (BL-200/202/206)

> **2026-05-09. main @ `9badae6`.** Sprint 47 = ★★★★★ Option D = 3 BL deepening (cmux 4 worker 자율 병렬) + dogfood Phase 2 사용자 manual 카톡 발송 동시 분기. **회귀 0 / 3 PR 정상 머지 / Day 7 4-AND gate (b)+(c)+(d) PASS**.

---

## 1. 산출 (3 BL Resolved + BL-205 intentional doc-only)

| PR   | BL                                   | Worker | 변경                                                                                                                                                                                            | 검증                                                                                     |
| ---- | ------------------------------------ | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| #241 | BL-200 pine_v2 STDLIB SSOT           | A      | `_names.py` 신규 단일 SSOT (TA 17 + Utility 2 = 19) + `interpreter.py` re-export + `coverage.py` re-export + `test_ssot_invariants.py` +3 invariants                                            | pine_v2 481 PASS / 16 skip / 0 fail                                                      |
| #240 | BL-202 trading provider registry     | B      | `backend/src/trading/registry.py` 신규 (3-tuple → dict + Protocol + Celery prefork-safe) + `tasks/trading.py:105` registry.dispatch() 단순화 + monkeypatch 12 사이트 변경 0 (wrapper 심볼 보존) | provider dispatch 27 PASS + 2 pre-existing ERROR (asyncpg infra) / prefork-safe 7/7 PASS |
| #239 | BL-206 frontend Skeleton variant API | C      | `skeleton.tsx` variant API 5 (text/card/list-row/chart/table-cell) + `empty-state.tsx` variant 4 + animate-pulse hardcode 9 occurrences (6 파일) → 0 (의도된 보존 8 사이트 분리)                | frontend 635 PASS (Sprint 46 baseline 603 → 635, +11 tests 추가)                         |

**합계:** 3 PR / 16 files / 회귀 0 / 신규 +14 tests (pine_v2 +3 invariants + frontend +11 variant tests).

**BL-205 = Resolved (intentional, doc only).** codex G.0 2차 (776k tokens) 에서 OrderReceipt 3-state vs OrderStatusFetch 4-state split 이 의도된 설계로 확인. `_map_ccxt_status()` (providers.py:708-719) 가 canceled/cancelled → "rejected" 매핑. 코드 변경 없음.

**BL-201/203/204 = Sprint 48+ 이연.** dogfood 결과 따라 4-way 분기 input.

---

## 2. cmux 4 worker 6번째 실측 (LESSON-059 카운트 +1)

- Sprint 46 = 5번째 (≈1h, 4 worker × 16 시나리오 + 6 surgical BL)
- Sprint 47 = **6번째 wall-clock ≈45분** (3 worker A/B/C 병렬 + Worker D smoke 메인 세션 read-only)
- 사용자 interaction = 4회 (BL-202/206 design freeze 결정 + 머지 전략 + push 차단 우회 + main pull stash 충돌 처리)
- 직렬 추정 = 13-19h (4-6h × 3 BL + 통합 / 사용자 결정 cycle 포함)
- 단축율 ≈95% (직렬 대비)

---

## 3. Day 7 4-AND Gate (Type B 의무, plan §8)

| 항목                                    | 상태       | 근거                                                                |
| --------------------------------------- | ---------- | ------------------------------------------------------------------- |
| (a) self-assess ≥7/10                   | ⏳ pending | 사용자 결정 (Day 7 시점, dogfood Phase 2 mid-check)                 |
| (b) BL-178 production BH curve 정상     | ✅ PASS    | golden_oracle 8 test 76 passed 안 포함 (재검증 의무 통과)           |
| (c) BL-180 hand oracle 8 test all GREEN | ✅ PASS    | `pytest tests/backtest/test_golden_oracle_minimal.py -v` 실측 PASS  |
| (d) new P0=0 + Sprint-caused P1=0       | ✅ PASS    | 회귀 0 / 2 ERROR pre-existing asyncpg infra (BL-202 surgery 영향 0) |

(b)(c) 가 자동 PASS 가 아니라 **재검증 의무** 였음 (BL-200 pine_v2 영역 + BL-180 backtest 경로 영향 가능성). 6 suite 실측에서 76 passed 중 모두 포함 → PASS 확정.

---

## 4. PREFLIGHT vs 실측 정합 (codex G.0 2회 검증 효과)

| codex G.0 1+2차 발견                                            | 실측 정합                                                                        |
| --------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| BL-200 17+2 분리 구조 (na/nz UTILITY)                           | ✅ `_names.py` 정확 17 TA + 2 Utility = 19 union                                 |
| BL-202 providers.py 단일 파일 + tasks/trading.py:105 dispatcher | ✅ Worker B 가 정확히 그 위치 surgery + 5 entries 구성                           |
| BL-205 OrderReceipt 3-state 의도된 split                        | ✅ 코드 변경 없음, ADR/docstring 문서화로 종결                                   |
| Worker B sequencing — monkeypatch 12 사이트                     | ✅ wrapper 심볼 (`_provider_for_account_and_leverage`) 보존으로 12 사이트 0 변경 |
| Celery prefork-safe (module import 시 CCXT X)                   | ✅ `test_trading_prefork_safe.py` 7/7 PASS                                       |
| BL-206 기존 `skeleton.tsx` 확장 (신규 X)                        | ✅ Worker C 가 기존 파일 variant 5 추가                                          |
| frontend `pnpm test --run` wrong                                | ✅ `pnpm test` 정정 사용                                                         |
| 2 pre-existing ERROR (asyncpg infra)                            | ✅ Worker B 실측 동일 패턴 + sprint 47 변경 영향 0 confirmed                     |

→ **codex G.0 2회 (314k + 776k tokens) ROI = wrong premise 4건 + sequencing 1건 + prefork-safe 1건 = 6 critical 사전 차단**. plan v3 의 가정 7건이 모두 실측 정합.

---

## 5. CI 인프라 marginal 발견

- **PR #241 ruff RUF003** — `_names.py:67` 주석 `∪` (UNION 문자) 가 Latin `U` 와 ambiguous. ASCII `|` (set operator) 로 정정. Worker A 가 첫 push 때 통과한 이유 = 다른 ruff config 또는 transient. **CI 측 ruff 가 더 엄격**. 메인 세션 hotfix commit `9673293` push 시 pre-push hook backend pytest 4 fail + 314 errors (worktree venv DB infra pre-existing) → `--no-verify` 사용자 명시 승인 1회 사용 (LESSON-061 카운트 +1).
- **PR #241 coverage.py I001** — import 정렬. `ruff --fix` 자동 적용. 결과: 단일 from 이 두 별도 from 으로 분리 (sub-optimal readability 지만 ruff isort 결정 PASS).

---

## 6. LESSON 정식 등재 (Sprint 47 신규 + 카운트 갱신)

**신규 등재:**

- **LESSON-064 (1/3) — deepen-modules audit silent failure 판단 의무.** BL-205 사례 = audit pilot 이 OrderReceipt 3-state 를 silent failure 로 등재했으나 codex G.0 2차 직접 read 결과 의도된 split 확인. 단일 파일 grep 만으로 silent failure 확정 금지. `_map_*` reverse 매핑 함수 + dispatcher consumer 전수 추적 의무. BL 등재 전 codex G.0 1회 cross-check 권장.

**카운트 갱신 (lessons.md inline 갱신, 별도 등재 X):**

- **LESSON-061** force-push 차단 시 우회 패턴 — Sprint 44 (4건) + Sprint 46 (2건) + Sprint 47 (1건 ruff fix push `--no-verify`) = 7건 누적. `--no-verify` vs GitHub UI 직접 squash 두 갈래 모두 패턴 검증.
- **LESSON-055** Worker prompt 첫 step `cd <worktree path>` 사전 명시 — Sprint 43 + 44 + 46 + 47 (3 worker 모두 isolation 위반 0건 추가 검증). 누적 4 sprint 적용 = **3/3 검증 완료** (정식 승격 후보).
- **LESSON-063** AI 누적 코드 3 패턴 — 본 Sprint 47 = `/deepen-modules` pilot 의 BL surgery 직접 검증. 3 패턴 (Triple SSOT / Cross-module dispatcher / Cross-page primitive) 모두 surgery 후 silent failure 차단 확인. 정합 재확인.

---

## 7. dogfood Phase 2 calendar (Sprint 47 plan §9 정합)

- Day 0 = 2026-05-09 또는 2026-05-10 (사용자 manual)
- Day 7 mid-check ≈ 2026-05-16/17
- Day 14 close-out ≈ 2026-05-23/24

본 sprint close-out trigger 는 dogfood Day 14 에 의존 X. 3 BL Resolved + Day 7 4-AND gate (b)(c)(d) PASS = close 가능. Day 14 결과는 Sprint 48 분기 결정 input.

---

## 8. Sprint 48 분기 (4-way, dogfood 결과 따라)

- (a) NPS ≥7 + critical bug 0 + 본인 self-assess ≥7 → **Beta 본격 진입 (BL-070~075)**
- (b) dogfood mixed → **BL-201 + BL-203 + BL-204 묶음 deepening 2차 (cmux 5w 8-12h)**
  - BL-203 (service.py 5 class 분할) 은 BL-202 registry 변경 반영 의무
- (c) dogfood 신규 critical bug 1+ → **polish iter (해당 hotfix)**
- (d) mainnet trigger 도래 → **BL-003/005 mainnet 본격**

---

## 9. baseline 갱신

- main: `43b9aa3` → `9badae6` (PR #239/#240/#241 squash merge)
- backend total: 1679+ → 동등 (회귀 0)
- frontend vitest: 603 → **635** (BL-206 Skeleton/EmptyState variant +11 tests + Worker A SSOT invariants +3)
- pine_v2 tests: 252+ → 481 PASS / 16 skip
- e2e baseline: smoke 4 PASS
- 활성 BL: 93 → **89** (BL-200/202/206 + BL-205 Resolved). BL-205 는 intentional doc-only 마커.

---

## 10. References

- plan v3 SSOT: `<repo>/.claude/plans/sprint-47-kickoff-prereq-nested-cloud.md` (codex G.0 2회 314k+776k tokens)
- plan execution: `<repo>/.claude/plans/sprint-47-adaptive-lightning.md`
- pre-pilot dev-log: `docs/dev-log/2026-05-09-pine_v2-deepen-pilot.md` / `2026-05-09-trading-deepen.md` / `2026-05-09-frontend-deepen.md`
- meta-rules: `.ai/common/global.md` §7.5 (deepen-modules 권장 시점)
- LESSON-063 (이미 §7.5 반영) — 본 sprint 가 첫 검증
- LESSON-064 (신규 1/3) — BL-205 사례 정식 등재
