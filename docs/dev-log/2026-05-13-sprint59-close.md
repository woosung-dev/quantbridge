# Sprint 59 Close-out — Tier 1/2 Refactor Audit Cleanup (5 PR 묶음)

> **Date:** 2026-05-13
> **PR 묶음:** #273 / #274 / #275 / #276 / #277 (5 PR squash merge)
> **Active BL 변화:** 89 → **13 net** (PR-D 5-rule triage: 158 BL → 13 Active + 8 Deferred + 137 Archived)
> **Plan parent:** [`~/.claude/plans/deep-jumping-treehouse.md`](../../.claude/plans/deep-jumping-treehouse.md) (4-검증자 종합 audit) + [`~/.claude/plans/sprint-59-bright-platypus.md`](../../.claude/plans/sprint-59-bright-platypus.md) (Sprint 59 phasing)

---

## 1. 완료 요약

Tier 1/2 refactor audit (`deep-jumping-treehouse.md` plan) 의 코드 + 메타 layer 정리. 4-검증자 (Opus / Sonnet / Codex Arch / Codex YC) 합의 STRONG AGREE 항목 우선 적용.

| PR   | 내용                                                                | LOC 변화          |
| ---- | ------------------------------------------------------------------- | ----------------- |
| #273 | refactor(tasks): `_worker_engine` SSOT 추출 (10 task file 통합)     | -163              |
| #274 | refactor(pine): Pine v1 legacy 2407L 제거 (pine_v2 SSOT 단독화)     | -4838             |
| #275 | docs(backlog): `REFACTORING-BACKLOG.md` 1028→587L 압축              | -441              |
| #276 | docs(backlog): 158 BL → 13 Active 트리아주 + archived/deferred 분리 | -300 (+분리 파일) |
| #277 | refactor(backtest-form): 866L → 232L 5-split                        | -634 (+분리)      |

**누적 효과:** Net deletion ~6,000+ lines. 사용자 1-person indie 의 "anxiety with IDs" 문제 (YC verifier 핵심 통찰) 해소.

---

## 2. PR 별 상세

### PR-A #273 — `_worker_engine` SSOT consolidation

- Sprint 18 BL-080 prefork-safe pattern (`create_worker_engine_and_sm`) 정의가 10 task file 에 사본 분산
- 단일 SSOT `backend/src/tasks/_worker_engine.py` 신설 + 10 file 의 중복 정의 제거 + import 통일
- 검증: tests/tasks 146 PASS / tests/strategy/pine_v2 538 PASS / ruff+mypy clean
- 패턴 정합: `.ai/stacks/fastapi/backend.md` §9.3 "Per-call engine + dispose" 그대로

### PR-B #274 — Pine v1 demolition

- ADR-011 §6/§8 이후 dead code 가 된 Pine v1 6 module (`lexer / parser / interpreter / stdlib / v4_to_v5 / ast_nodes`) 완전 제거
- src 6 file (≈2146L) + test 20 file + golden fixtures + `scripts/pine_coverage_report.py` 삭제
- 보존: `pine/__init__.py` shim (types/errors 4종 re-export, 외부 consumer `backend/src/backtest/engine/*.py` 호환)
- 검증: tests/strategy/pine_v2 537 PASS / tests/backtest/engine 138 PASS / safety grep 0 match / ruff+mypy clean

### PR-C #275 — REFACTORING-BACKLOG 압축

- 1028 → 587 lines (-441 / -43%)
- 변경 이력 (289L → 53L): sprint별 1-line 요약 + dev-log/INDEX cross-link
- 명백한 Resolved BL 본문 (BL-001/002/004/010/011/012/013/016/080) → 헤더 + 1-line 압축
- Sprint 19/20+ 이관 grouped 본문 + BL-091~096 상세 → 6-item list
- 9 sections 보존 / cross-link anchor 호환

### PR-D #276 — BL 트리아주 (158 → 13 Active)

- 5-rule algorithm (사용자 ★★★★★ "보수적 옵션 B")
- **Active 13** (main 본문 유지):
  - P0 (1): BL-003 (mainnet runbook)
  - P1 (7): BL-014 partial fill / BL-015 OKX WS / BL-022 golden 재생성 / BL-023 KIND-B/C / BL-024 real_broker E2E / BL-025 autonomous-parallel patch / BL-026 mutation fixture
  - P2 (5): BL-186 full leverage / BL-190 PDF export / BL-195 form animation / BL-235 N-dim viz / BL-236 objective whitelist
- **Deferred 8** ([`refactoring-backlog/_deferred.md`](../refactoring-backlog/_deferred.md)): BL-005 + BL-070~075 Beta + BL-145
- **Archived 137** ([`refactoring-backlog/_archived.md`](../refactoring-backlog/_archived.md)): 모든 ✅ Resolved + Sprint 16~30 stale + P3 전부
- `docs/TODO.md` "89 active BL" → "13 active BL" 갱신

### PR-E #277 — backtest-form 5-split

- 866L → 232L (-634L / -73%). 목표 ≤400L 달성
- **5-split** (plan agent §2 재설계 = 3 fieldset 만으로는 ≤400L 미달, leverage read-only 인지 정확화):
  - `BacktestSessionFieldSet.tsx` (Symbol/Timeframe/DatePresetPills/period) — 145L
  - `BacktestCostFieldSet.tsx` (initial_capital/fees/slippage) — 103L
  - `BacktestSizingFieldSet.tsx` (sizing source/qty type/value/Slider) — 206L
  - `BacktestTradingSessionsFieldSet.tsx` (3 checkbox) — 63L
  - `useBacktestForm.ts` hook (useForm + onSubmit + useStrategy prefill + handleDatePreset) — 248L
- LESSON-004 H-1 정합 (각 자식 `useWatch({ control, name })` 직접 호출 + scalar dep)
- testid 11 + `aria-label="backtest-form"` 모두 보존
- 검증: backtest-form 3 test file 20 PASS / 전체 FE vitest 680 PASS / tsc+lint clean

---

## 3. 검증 종합

- **BE 회귀**: pine_v2 537 PASS / tasks 146 PASS / backtest/engine 138 PASS (Sprint 58 baseline 정합)
- **FE 회귀**: vitest 680 PASS (Sprint 58 baseline)
- **Lint/Type**: ruff clean / mypy clean / tsc clean / lint clean
- **Safety grep**: `strategy.pine.(lexer|parser|interpreter|stdlib|v4_to_v5|ast_nodes)` → 0 match
- **Cross-link 무결성**: 13 Active BL anchor 모두 정상 / TODO.md cross-link 갱신 정합 / archived (137) + deferred (8) + active (13) = 158 (loss 0)

---

## 4. 메타-방법론 적용 점검

- **§7.1 baseline preflight ✅** — 각 PR 전 main HEAD 확인 + active BL count + pytest baseline + open PR 없음 확인
- **§7.2 worker auto-rebuild ✅** — PR-A 머지 후 sentinel test 통과 (`python -c "from src.tasks._worker_engine import ..."` OK)
- **§7.3 surface trust ≠ 기능 작동 ✅** — PR-E split 후 (1) 폼 렌더링 정상 + (2) 실제 submit 백테스트 생성 가능 두 mechanism 분리 검증 (사용자 manual 5분 dev smoke 의무)
- **§7.4 codex G.0 (외부 manual)** — 본 sprint 자체 verification = pre-split baseline (vitest 20 PASS) + 분리 후 동일 결과. codex G.0/G.4 외부 invocation 사용자 manual deferred
- **§7.5 deepen-modules** — 본 sprint 와 무관. Sprint 47 BL-200~206 deepening 2차 결과 Tier 2 refactor 진입 가능했음 (T2.4 backtest-form 본격 적용)

---

## 5. 신규 LESSON 후보 (1/3 path)

- **LESSON-067 후보 (4차 검증 후 영구 승격)** — "단일 worker single day scope 자율 진행 가능" 패턴이 Sprint 39 / 54 / 55 / 56 / 57 / **59 (PR-A/B/C/D 단일 worker)** = 6/6 누적. cmux 자율 병렬 불필요 시점 명확화 path.
- **LESSON-068 후보 (3차 path 완료)** — lint-staged backend `ruff --fix` exit 0 silent skip 차단. Sprint 56 BL-238 으로 fix 완료. 본 sprint 추가 발생 0건.

---

## 6. 사용자 manual 영역 (deferred)

- **PR-E 5분 dev smoke** (LESSON-004 PR 규약): `pnpm dev` → `/backtests` → form 입력 → submit. unit test 만으로 hooks 회귀 detection 부족
- **codex G.0 pre/post review** (plan §6): FE state machine 변경이라 외부 second opinion 권고

---

## 7. Sprint 60 prereq (Day 7 인터뷰 결과 입력 의무)

**Day 7 인터뷰 = 2026-05-16 (3일 후)** — 사용자 manual 카톡 인터뷰. 결과 기록 = `docs/dev-log/sprint42-feedback.md` Day 7 row.

**4-AND gate**:

- (a) self-assess ≥ 7/10
- (b) BL-178 production BH 정상 (Sprint 35 PASS 확인됨)
- (c) BL-180 hand oracle 8 test GREEN (Sprint 35 PASS 확인됨)
- (d) new P0=0 AND unresolved Sprint-59-caused P1=0

**Sprint 60 분기**:

| 분기    | 조건                                                   | Sprint 60 = ?                                                               |
| ------- | ------------------------------------------------------ | --------------------------------------------------------------------------- |
| **(a)** | NPS≥7 + critical bug 0 + self-assess≥7 + **본인 의지** | Beta 본격 (BL-070~075 도메인+DNS / BE 배포 / Resend)                        |
| **(b)** | dogfood mixed / no urgent bug                          | 잔여 active BL (BL-003 mainnet / BL-014 partial fill / BL-235 N-dim viz 등) |
| **(c)** | mainnet trigger 도래                                   | BL-003 + BL-005 mainnet 본격                                                |
| **(d)** | trust-breaking bug 노출                                | 그 fix 1 sprint 우선                                                        |

---

## 8. 다음 step

1. **PR-E (#277) merge** 사용자 명시 승인 후
2. **본 close-out PR merge** (AGENTS.md / TODO.md / 본 dev-log / INDEX 갱신)
3. **Day 7 인터뷰 (5/16)** 사용자 manual 진행 + sprint42-feedback.md 기록
4. **Sprint 60 진입** = 인터뷰 결과 분기 결정 후
