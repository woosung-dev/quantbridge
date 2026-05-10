# Sprint 49 Close-out — Track A shim removal (BL-203/204) + Track B dogfood Day 0 발송 trigger

> **2026-05-10. main @ `6ad6d8e`.** Sprint 49 = ★★★★★ Option A1 = **Track A (shim removal) + Track B (dogfood Day 0 prereq 9 항목 + 사용자 manual 발송) 동시**. 회피 패턴 영구 차단 의지. 2 PR 정상 머지 / **Day 7 4-AND gate (b)+(c)+(d) PASS** ((a) 사용자 결정 pending = Day 0 + 6일 = 2026-05-16).

---

## 1. 산출 (2 BL Resolved + dogfood Day 0 trigger 통과)

| PR   | BL                      | Track | 변경                                                                                                                                                                                        | 검증                                                                                                                   |
| ---- | ----------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| #249 | BL-203/204 shim removal | A     | 49 files / +220 / -479 line. 3 commit 분할 (A1 src/ 17 / A2 tests/ 30 + shim test 2 삭제 / A3 shim 2 삭제). 176 import line + 13 monkeypatch alias 사이트 + shim 4 파일 cleanup.            | pytest 1016 PASS / 0 FAILED / 180 errors (환경 baseline 동일). ruff 0 / mypy 0 / zero-gate 0 line / import smoke PASS. |
| #250 | dogfood Track B Day 0   | B     | `docs/dogfood/sprint42-cohort-outreach.md` Day 0 prereq **6 → 9 항목 확장** + 각 항목 명령 1줄 inline. 신규 3 = Bybit Demo walkthrough / share token 만료 정책 / 외부 시크릿 브라우저 검증. | Day 0 prereq 섹션 9 line / 절대날짜 grep '2026-05-[0-9]{2}' Day 0 prereq 섹션 = 0 line (codex Fix #7).                 |

**합계:** 2 PR / 50 files / 회귀 0 / 신규 tests = 0 (refactor only + docs only).

**Day 0 발송 trigger 통과:** Track B 머지 후 사용자 manual 발송 완료 (2026-05-10). prereq 9 항목 walk-through + 카톡 DM 발송. **Day 0 timestamp 기록 = 사용자 manual 의무** (sprint42-feedback.md "1-2명 micro-cohort log" 발송일 칸).

---

## 2. Phase 1 wrong premise 사전 차단 1건 (LESSON-040 4번째 검증)

사용자 prompt 가정: BL-141 + BL-140b 5일째 progress 0 → **stale**.

raw 사실 (REFACTORING-BACKLOG.md L601-603 + 파일 직접 검증):

- BL-141 ✅ Resolved (Sprint 28 Slice 2 PR #110, 2026-05-04). `backend/src/tasks/market_data_backfill.py` (4767B) + `20260416_1458_create_ohlcv_hypertable.py` migration 실존.
- BL-140b ✅ Resolved (Sprint 28 Slice 3 PR #111, 2026-05-04). `20260504_0001_add_live_signal.py` + `20260504_0002_add_equity_curve.py` migration 실존. `equity_curve` JSONB column @ `models.py:441`.

**Track A 재정의** = shim removal (BL-203/204) — 사용자 ★★★★★ 결정.

**LESSON-040 4번째 검증 통과**:

- 1차 (Sprint 35 Slice 1a) — 2026-05-05
- 2차 (Sprint 35 전체) — 2026-05-05
- 3차 (Sprint 38 codex iter 2) — 2026-05-07
- **4차 (본 sprint Phase 1 BL-141/140b stale 차단) — 2026-05-10** = 지속적 가치 입증.

---

## 3. codex G.0 GO_WITH_FIXES (104,576 tokens) — 7 critical fix 모두 반영

| #   | fix                                                                                      | 반영                                                |
| --- | ---------------------------------------------------------------------------------------- | --------------------------------------------------- |
| 1   | 현재 브랜치 = `docs/sprint48-close` (NOT main). main checkout 의무                       | ✅ A.0 preflight                                    |
| 2   | 신규 module 파일명 = suffix 포함 (`order_repository.py` 등). `orders.py` 가정 = wrong    | ✅ A.2.0 mapping 표                                 |
| 3   | "145 사이트" = line. unique test files = 27. 표현 정정                                   | ✅ plan 갱신                                        |
| 4   | A.2.0 신규 step = class → module mapping 확정 (6+5+2 = 13 entry)                         | ✅ Track A 적용                                     |
| 5   | services/ 내부 4 파일 도 old `src.trading.repository` 직접 참조 — shim 삭제 전 갱신 의무 | ✅ A1 commit 4 파일                                 |
| 6   | `test_repository_shim.py` + `test_service_shim.py` = legacy path 검증. shim 삭제 후 깨짐 | ✅ A2 commit 2 파일 삭제                            |
| 7   | `grep '2026-05'` 절대날짜 검증 false fail (placeholder 충돌). 검증 범위 제한 필요        | ✅ Track B 적용 (Day 0 prereq 섹션 한정 awk + grep) |

---

## 4. LESSON-065 1차 sprint 검증 (monkeypatch indirect dependency)

Sprint 48 close-out 시점 신규 등재 LESSON. Sprint 49 = **Sprint 단위 1차 검증 통과**.

| Sprint | 사이트 수                   | 결과                                      |
| ------ | --------------------------- | ----------------------------------------- |
| 47     | (해당 없음)                 | -                                         |
| 48     | 6 사이트 (3 test 파일)      | **5 test FAIL** (CI fix 2 commit 후 머지) |
| **49** | **13 사이트 (5 test 파일)** | **0 FAIL** (사전 monkeypatch 분리 처리)   |

**핵심 차단 패턴**: Sprint 48 = 머지 후 발견 (CI). Sprint 49 = **plan codex G.0 단계에서 사전 발견** + Phase 1 정확 측정 (7 monkeypatch + 6 module-level alias). 13 사이트 모두 Track A 안에서 alias 분리 처리.

**3/3 영구 승격 path**: Sprint 50+ 1-2 회 추가 검증 시 영구 승격 (LESSON-040 패턴 참조).

---

## 5. Day 7 4-AND Gate (Type B 의무)

| 항목                                    | 상태                       | 근거                                                                                    |
| --------------------------------------- | -------------------------- | --------------------------------------------------------------------------------------- |
| (a) self-assess ≥7/10                   | ⏳ pending (= Day 0 + 6일) | Day 0 = 2026-05-10 → Day 7 = **2026-05-16**. 사용자 결정 (codex Fix #7 상대 표기 의무). |
| (b) BL-178 production BH curve 정상     | ✅ PASS                    | main 변경 X 영역 (Track A = trading 도메인 shim removal, Track B = docs only).          |
| (c) BL-180 hand oracle 8 test all GREEN | ✅ PASS                    | main 변경 X 영역 (pine_v2 회귀 0).                                                      |
| (d) new P0=0 + Sprint-caused P1=0       | ✅ PASS                    | 회귀 0. monkeypatch indirect dependency 사전 차단 (vs Sprint 48 PR #246 5 FAIL 사례).   |

**(d) 핵심**: Sprint 48 = 머지 후 CI fail 발견 → 즉시 fix 2 commit. Sprint 49 = plan 단계에서 13 사이트 사전 식별 + alias 분리 처리 → CI 1차 통과 (사용자 머지 직전 fail 0).

---

## 6. Sprint 49 commit / PR 분할 결과

### Track A (refactor/sprint49-shim-removal — PR #249)

| commit  | 내용                                                                        | 검증                                          |
| ------- | --------------------------------------------------------------------------- | --------------------------------------------- |
| 2bd5a01 | refactor(trading): src/ 17 파일 import path 갱신 (shim removal prep)        | pytest baseline 동일 + import smoke           |
| 6b81ed9 | refactor(trading): tests/ 30 파일 + 6 module-level alias + shim test 2 삭제 | pytest 회귀 0 + LESSON-019 commit-spy 18 보존 |
| 4d40a94 | refactor(trading): repository.py + service.py shim wrapper 삭제             | zero-gate 0 line + ruff 0 + mypy 0            |

### Track B (docs/sprint49-dogfood-day0 — PR #250)

| commit  | 내용                                                           | 검증                                            |
| ------- | -------------------------------------------------------------- | ----------------------------------------------- |
| 2a80750 | docs(dogfood): Day 0 prereq 6 → 9 항목 확장 + 각 항목 명령 1줄 | Day 0 prereq 9 line + 절대날짜 0 (codex Fix #7) |

---

## 7. Sprint 49 wall-clock + 의사결정 흐름

**Sprint 49 첫 step = 사용자 prompt baseline 재측정 preflight (LESSON-040)**:

- Phase 1 = 3 Explore agent 병렬 (BL-141 / BL-140b / dogfood Day 0)
- 결과 = BL-141/140b stale 발견 → wrong premise 차단 → Track A 재정의 (shim removal) 사용자 결정
- codex G.0 = 104,576 tokens / GO_WITH_FIXES (7 critical fix)

**의사결정 6회 (사용자 ★★★★★)**:

1. Track A 재정의 = shim removal (vs Beta 본격 / Track B만 / 다른 P0/P1 BL)
2. Track B 신규 작성 자산 = day0-checklist 업데이트만 (신규 파일 X)
3. codex G.0 형식 = Heavy ~100k tokens 7 criteria
4. Track A commit 형식 = 3 commit 분할 (A1+A2+A3) + push + PR
5. Track B + close-out 진행 방식 = Track A PR 머지 후 Track B + C 순차
6. 머지 순서 = Track A 머지 → Track B 머지 → 발송 → close-out

**Sprint 49 핵심 trade-off**: 회피 패턴 차단 의지 (사용자 ★★★★★) + Track A 머지 prereq vs dogfood 발송 timer 빠르게 시작. **사용자 결정 = plan 정합 (1번 옵션)** = Track A 머지 → Track B 머지 → 발송.

---

## 8. 다음 분기 — Sprint 50 (dogfood Day 7 mid-check 결과 따라 4-way)

**Day 7 mid-check 도래 = 2026-05-16 (Day 0 + 6일)**. 사용자 결정 input:

- **NPS ≥7 + critical bug 0 + self-assess ≥7 + 본인 의지 second gate** → Sprint 50 = **Beta 본격 진입 (BL-070~075)** — 도메인+DNS / Backend 프로덕션 배포 / Resend / 캠페인 / 인터뷰 / H2 게이트
- **mixed** → Sprint 50 = **deepening 3차** (Sprint 47/48 패턴 후속) 또는 **다른 BL**
- **신규 critical bug 1+** → Sprint 50 = **polish iter (해당 hotfix)**
- **mainnet trigger 도래** → Sprint 50 = **BL-003 / BL-005 mainnet 본격**

**Beta postpone 유지** (memory `feedback_beta_dual_gate_postpone.md`): Sprint 49 = shim removal + dogfood Day 0 발송. Beta 본격 진입 X. **사용자 의지 second gate** 도래 시점 = Day 7/14 dogfood 결과 + 본인 의지 명시.

---

## 9. 갱신된 의무 사항

**Sprint 50 첫 step = 사용자 manual sprint42-feedback.md 발송일 timestamp 기록 검증**:

- 본 sprint = 발송 timestamp 기록 = 사용자 manual (placeholder 채움 의무)
- Sprint 50 메인 세션 진입 시 `grep '발송일.*2026-05' docs/dogfood/sprint42-feedback.md` 검증 의무 (codex Fix #7 absolute date 의무)

**Sprint 47/48 shim wrapper 1 sprint 만료 패턴 = Sprint 49 검증 통과**:

- Sprint 48 = shim wrapper 도입 (BL-203/204 분할)
- Sprint 49 = shim wrapper 삭제 + 95+ import 사이트 갱신
- 향후 동일 패턴 BL 발생 시 1 sprint shim 만료 의무 영구화 (CLAUDE.md "다음 분기" 명시 패턴).

---

## 10. Cross-link

- Sprint 49 plan: `<repo>/.claude/plans/sprint-49-a-b-snug-pretzel.md` (gitignored)
- Track A PR: https://github.com/woosung-dev/quantbridge/pull/249
- Track B PR: https://github.com/woosung-dev/quantbridge/pull/250
- Sprint 48 close-out (직전): [`2026-05-09-sprint48-close.md`](2026-05-09-sprint48-close.md)
- Sprint 47 close-out: [`2026-05-09-sprint47-close.md`](2026-05-09-sprint47-close.md)
- Day 7 mid-check (= Day 0 + 6일): [`2026-05-08-sprint42-day7-midcheck.md`](2026-05-08-sprint42-day7-midcheck.md)
- Day 14 master (= Day 0 + 13일): [`2026-05-08-sprint42-master.md`](2026-05-08-sprint42-master.md)
- 메타-방법론 영구 규칙 (LESSON-040 4차 검증): `.ai/common/global.md` §7.4
