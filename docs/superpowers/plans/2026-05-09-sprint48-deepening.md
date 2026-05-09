<!-- Sprint 48 — BL-201/203/204 Deepening 2차 + Dogfood Phase 2 Prereq 병행 plan. 5 subagent worker breakdown (A/B/C/D/E). Sprint 47 패턴 mirror. -->

# Sprint 48 Deepening 2차 — BL-201/203/204 + Dogfood Phase 2 Prereq Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sprint 47 codex G.0 추천 deepening 2차 BL 묶음 (BL-201 pine_v2 dispatcher 통합 / BL-203 trading service 5 파일 분할 / BL-204 trading repository 6 파일 분할) 처리 + dogfood Phase 2 발송 prereq 갱신.

**Architecture:** SSOT registry dict + package shim re-export 패턴 (Sprint 47 mirror). 5 subagent worker (A/B/C/D/E). C=B 후속, E=A 후속 sequencing 의무. 각 worker 별 staging branch + 사용자 squash merge.

**Tech Stack:** Python 3.11 / FastAPI / SQLModel / pytest / pine_v2 인터프리터 / Next.js 16 / Vitest / pnpm.

**Master plan reference:** `~/.claude/plans/sprint-48-gentle-bumblebee.md` (codex G.0 GO_WITH_FIXES 7 fix 반영 완료).

---

## File Structure (5 Worker)

| Worker | Domain | Branch | 진입 |
|---|---|---|---|
| A | pine_v2 TrackRunner 통합 (BL-201) | `feat/sprint48-bl201-track-runner` | 즉시 |
| B | trading repository 6 파일 분할 (BL-204) | `feat/sprint48-bl204-repo-split` | 즉시 |
| C | trading service 5 파일 분할 (BL-203) | `feat/sprint48-bl203-service-split` | **B 머지 후** |
| D | dogfood Track 2 docs (Day 0 발송 prereq + Day 7 skeleton) | `docs/sprint48-dogfood-track2` | 즉시 |
| E | LESSON-064 reverse-mapping audit | (audit-only, no branch) | **A 머지 후** |

**충돌 회피:**
- A = `backend/src/strategy/pine_v2/` 단독
- B/C = `backend/src/trading/{repository,service}.py` 분할 (B 가 repo 안정화 후 C 진입 — codex G.0 권장)
- D = `docs/dogfood/*` only (codex Fix #3 — `docs/TODO.md`/backlog/dev-log 는 P3 메인 세션 처리)
- E = grep + read-only audit, write 0

---

## Task A: BL-201 pine_v2 TrackRunner 통합

**Sub-Skill 필수:** superpowers:test-driven-development

**Files:**
- Create: `backend/src/strategy/pine_v2/track_runner.py`
- Modify: `backend/src/strategy/pine_v2/compat.py:109-138` (if-chain → TrackRunner.invoke())
- Test (Create): `backend/tests/strategy/pine_v2/test_track_runner.py`

**Critical context (codex Fix #2):** TrackRunner 는 `compat.parse_and_run_v2` 의 dispatch 부분만 줄여야 한다. `classify_script()` 은 대체 금지. `event_loop.run_historical` (Track S/M) + `virtual_strategy.run_virtual_strategy` (Track A) 를 dispatch table 의 callable 로 등록.

**Invariants 의무 (codex Fix #2):**
- D2 sizing params 보존 (`initial_capital`, `default_qty_value`, `default_qty_type` 등 compat.py:110-137 의 모든 kwarg)
- `sessions_allowed` 보존
- `V2RunResult` shape (track / historical / virtual) 보존
- 미지원 track 시 `ValueError` 보존 (compat.py:137 의 ValueError 메시지 일관)

**Steps:**

- [ ] **A.1: codebase read & invariant 추출**
  - Read `backend/src/strategy/pine_v2/compat.py`, `event_loop.py`, `virtual_strategy.py`, `ast_classifier.py`
  - 4 invariant 목록 작성 (subagent 자체 메모)

- [ ] **A.2: TrackRunner failing tests 작성 (TDD red)**
  - Test: `tests/strategy/pine_v2/test_track_runner.py`
  - 4 cases: (a) Track S → run_historical 호출, (b) Track A → run_virtual_strategy 호출, (c) Track M → run_historical 호출, (d) unknown track → ValueError raise
  - dispatch table identity (`is`) 검증
  - Run: `cd backend && uv run pytest tests/strategy/pine_v2/test_track_runner.py -v`
  - Expected: FAIL (track_runner.py 미존재)

- [ ] **A.3: track_runner.py 최소 구현 (TDD green)**
  - `TrackRunner` 클래스 + `_dispatch_table` dict
  - `invoke(track, *, source, ohlcv, **kwargs) -> V2RunResult` 메서드
  - run_historical / run_virtual_strategy import + dispatch
  - Run: pytest test_track_runner.py
  - Expected: 4 PASS

- [ ] **A.4: compat.parse_and_run_v2 통합**
  - if-chain (109-138) → `result = TrackRunner.invoke(profile.track, source=..., ohlcv=..., **kwargs)` 단일 분기
  - V2RunResult shape 보존 검증
  - Run: `cd backend && uv run pytest tests/strategy/pine_v2/ -q --tb=short`
  - Expected: 481+4=485 PASS / 16 skipped (Sprint 47 baseline + 신규 4)

- [ ] **A.5: Sprint 47 BL-200 SSOT 회귀 검증**
  - Run: `cd backend && uv run pytest tests/strategy/pine_v2/test_ssot_invariants.py -v`
  - Expected: ALL PASS (BL-200 STDLIB SSOT 19 invariants 보존)

- [ ] **A.6: 6 corpus E2E 회귀**
  - Run: `cd backend && uv run pytest tests/strategy/pine_v2/test_corpus_strategies.py -v`
  - Expected: ALL PASS (Sprint 8b 6/6 corpus 보존)

- [ ] **A.7: Self-verify + commit + push + PR**
  - 의무 Korean header (`# QuantBridge pine_v2 — Track S/A/M dispatch 통합 registry`)
  - `git checkout -b feat/sprint48-bl201-track-runner` (worker 가 worktree 안에서)
  - Commit: "refactor(pine_v2): BL-201 Track S/A/M dispatcher 통합 (TrackRunner registry)"
  - Push + `gh pr create --title "refactor(pine_v2): BL-201 Track S/A/M dispatcher 통합" --base main`

- [ ] **A.8: Evaluator dispatch (subagent-driven-development 의무)**
  - Generator-Evaluator 2-Session: fresh subagent + isolation=worktree
  - Evaluator gate: PASS = lint 0 / tsc 0 / pytest pine_v2 ALL PASS / `_dispatch_table` identity 보존 / D2 sizing kwargs 누락 0

---

## Task B: BL-204 trading repository 6 파일 분할

**Sub-Skill 필수:** superpowers:test-driven-development

**Files:**
- Create: `backend/src/trading/repositories/__init__.py` (shim re-export)
- Create: `backend/src/trading/repositories/order_repository.py`
- Create: `backend/src/trading/repositories/exchange_account_repository.py`
- Create: `backend/src/trading/repositories/kill_switch_event_repository.py`
- Create: `backend/src/trading/repositories/webhook_secret_repository.py`
- Create: `backend/src/trading/repositories/live_signal_session_repository.py`
- Create: `backend/src/trading/repositories/live_signal_event_repository.py`
- Modify: `backend/src/trading/repository.py` (1 sprint 유지 shim wrapper, Sprint 49 제거)

**Critical context (P0 Preflight 정정):** 6 class — `ExchangeAccountRepository:34` / `OrderRepository:67` / `KillSwitchEventRepository:289` / `WebhookSecretRepository:368` / `LiveSignalSessionRepository:440` / `LiveSignalEventRepository:597`. Plan 의 4 class 가정은 wrong premise — 6 파일 분할 의무.

**의무: shim re-export (1 sprint 유지)** — 30+ test 파일이 `from src.trading.repository import OrderRepository` 직접 import. 이를 `repositories/__init__.py` 가 모두 re-export. 또한 기존 `repository.py` 도 동일 re-export wrapper (Sprint 49 제거 TODO).

**Steps:**

- [ ] **B.1: codebase read & 6 class 추출**
  - Read `backend/src/trading/repository.py` 전체
  - 6 class boundary 파악 (각 class 시작/끝 라인)
  - 각 class 의존 (LiveSignalEventRepository 가 LiveSignalSessionRepository 의존 가능?) 확인

- [ ] **B.2: shim 하위호환 failing test 작성 (TDD red)**
  - Test: `backend/tests/trading/test_repository_shim.py`
  - 6 import smoke: `from src.trading.repository import OrderRepository, ExchangeAccountRepository, ...` 모두 정상
  - 6 import smoke (신규 path): `from src.trading.repositories import OrderRepository, ...`
  - Run: pytest test_repository_shim.py
  - Expected: FAIL (repositories/ 미존재)

- [ ] **B.3: 6 파일 분할 + __init__.py shim 구현 (TDD green)**
  - 6 신규 파일 — 각 class 그대로 이동 (Korean header `# trading repository — {class} 책임 단독 분리`)
  - `repositories/__init__.py` 가 6 class 모두 re-export
  - `repository.py` 도 6 class re-export (downstream import 보존, deprecated comment 추가)
  - Run: pytest test_repository_shim.py
  - Expected: PASS

- [ ] **B.4: trading 회귀 검증**
  - Run: `cd backend && uv run pytest tests/trading/test_repository_*.py -v --tb=short`
  - Expected: 변경 0 (모든 기존 test 가 동일 import path 그대로 통과)

- [ ] **B.5: LESSON-019 commit-spy 회귀 보존**
  - Run: `cd backend && uv run pytest tests/trading/test_webhook_secret_commits.py tests/trading/test_live_session_commits.py -v`
  - Expected: ALL PASS

- [ ] **B.6: Self-verify + commit + push + PR**
  - Korean header 모든 신규 파일
  - Commit: "refactor(trading): BL-204 repository.py 6-class god file 분할 + shim re-export"
  - PR: `--base main`

- [ ] **B.7: Evaluator dispatch**
  - Gate: PASS = lint 0 / 6 신규 파일 Korean header / shim 하위호환 / commit-spy 보존 / 기존 trading test 회귀 0

---

## Task C: BL-203 trading service 5 파일 분할 (B 머지 후)

**Sub-Skill 필수:** superpowers:test-driven-development

**전제:** Worker B (BL-204) PR 머지 + main rebase 완료. `from src.trading.repositories import ...` 작동.

**Files:**
- Create: `backend/src/trading/services/__init__.py` (shim re-export)
- Create: `backend/src/trading/services/order_service.py`
- Create: `backend/src/trading/services/account_service.py`
- Create: `backend/src/trading/services/webhook_secret_service.py`
- Create: `backend/src/trading/services/live_session_service.py`
- Create: `backend/src/trading/services/protocols.py` (`OrderDispatcher`, `StrategySessionsPort`)
- Modify: `backend/src/trading/service.py` (1 sprint shim wrapper)

**Critical context:** 5 service class + 2 Protocol = 7 신규 파일.
- `ExchangeAccountService:71` → `account_service.py`
- `WebhookSecretService:160` → `webhook_secret_service.py`
- `OrderDispatcher(Protocol):212` + `StrategySessionsPort(Protocol):216` → `protocols.py`
- `OrderService:226` → `order_service.py`
- `LiveSignalSessionService:466` → `live_session_service.py`

**Celery prefork-safe 의무 (codex Fix #4):**
- `services/live_session_service.py` 에 module-level `engine`, `provider`, `RedisLock`, `asyncio.Lock`, `create_async_engine()` 캐시 **금지**.
- BL-084 audit 가 `src/trading/services/*.py` 까지 scan 하도록 audit test 갱신 의무.

**Steps:**

- [ ] **C.1: codebase read & 5 service + 2 Protocol 추출**
  - Read `backend/src/trading/service.py` 전체
  - 각 class 경계 파악 + module-level state 검증 (현 파일 안 module-level engine/asyncio Lock 0 확인)

- [ ] **C.2: shim 하위호환 failing test 작성 (TDD red)**
  - Test: `backend/tests/trading/test_service_shim.py`
  - import smoke: 5 service + 2 Protocol — 기존 path + 신규 path
  - module-level state 0 검증 (`hasattr(services.live_session_service, '_engine')` False 등)

- [ ] **C.3: 7 파일 분할 + __init__.py shim 구현 (TDD green)**
  - Korean header 의무
  - **module-level state 0 의무** (codex Fix #4)
  - 신규 path import 가능 (`from src.trading.services import OrderService` etc)
  - 기존 path 도 동일 (`from src.trading.service import OrderService`)

- [ ] **C.4: BL-084 audit test scope 확장**
  - Modify: `backend/tests/tasks/test_no_module_level_loop_bound_state.py`
  - scan target 추가: `src/trading/services/*.py`
  - Run: pytest test_no_module_level_loop_bound_state.py
  - Expected: PASS (신규 services/* 도 통과)

- [ ] **C.5: trading 전체 회귀**
  - Run: `cd backend && uv run pytest tests/trading/ -q --tb=short`
  - Expected: 137 PASS 보존 (DB 의존 138 errors 는 로컬 env, CI 신뢰)

- [ ] **C.6: Self-verify + commit + push + PR**
  - Commit: "refactor(trading): BL-203 service.py 5-class+2-protocol 분할 + prefork-safe audit 확장"

- [ ] **C.7: Evaluator dispatch**
  - Gate: PASS = lint 0 / Korean header / shim / module-level state 0 / BL-084 audit 확장

---

## Task D: dogfood Track 2 docs 갱신 (codex Fix #3, #7)

**Sub-Skill 필수:** 없음 (docs only, TDD 면제)

**Write scope (codex Fix #3 — 의무):** `docs/dogfood/*` + Day 7 skeleton **만**. `docs/TODO.md`, `docs/REFACTORING-BACKLOG.md`, `docs/dev-log/sprint48-close.md` 는 P3 메인 세션 처리. 위반 시 Evaluator FAIL.

**Files:**
- Modify: `docs/dogfood/sprint42-cohort-outreach.md` (Day 0 발송 메시지 갱신, 본문 검토)
- Modify: `docs/dogfood/sprint42-feedback.md` (Day 7 mid-check skeleton row 추가)
- Modify: `docs/dev-log/2026-05-08-sprint42-day7-midcheck.md` (Day 7 schedule = Day 0 발송일 +6 의무 명시 — codex Fix #7)

**Steps:**

- [ ] **D.1: 현행 outreach.md 검토**
  - Read 전체 (already partially read)
  - 발송 prereq 체크리스트 항목 검증 (16 페이지 visual ✅, 본인 backtest sample ⏳, share token ⏳, Bybit Demo URL, Clerk 가입)

- [ ] **D.2: outreach.md Day 0 메시지 본문 점검**
  - Sprint 47 머지 후 변경된 페이지/UX 반영 (4 페이지 prototype + dashboard-shell 4 컴포넌트 분할)
  - "최근 polish 내용" 1줄 추가 권장

- [ ] **D.3: feedback.md Day 7 skeleton row 추가**
  - 새 row: Day 7 = Day 0 발송일 +6일 (TBD — Day 0 기록 후 채움)
  - column: NPS / 사용 빈도 / 주요 막힘 / 개선 요청

- [ ] **D.4: day7-midcheck.md 정정 (codex Fix #7)**
  - 명시: "**Day 7 schedule = Day 0 발송일 + 6일**. Day 0 미기록 시 Day 7 고정 금지. 2026-05-15 등 절대 날짜 사용 금지."
  - 기존 절대 날짜 references 삭제

- [ ] **D.5: Self-verify**
  - `git diff docs/dogfood/ docs/dev-log/2026-05-08-sprint42-day7-midcheck.md` 검토
  - write scope 위반 0 (`docs/TODO.md`, `docs/REFACTORING-BACKLOG.md` 변경 0)

- [ ] **D.6: commit + push + PR**
  - Commit: "docs(dogfood): BL-204/sprint48 Track 2 — Day 0 발송 메시지 + Day 7 relative schedule"
  - PR: `--base main`

- [ ] **D.7: Evaluator dispatch**
  - Gate: PASS = scope 위반 0 / Day 7 절대날짜 references 0 / outreach.md Day 0 본문 정상

---

## Task E: LESSON-064 reverse-mapping audit (A 머지 후, audit-only)

**Sub-Skill 필수:** 없음 (read-only, write 0)

**전제:** Worker A (BL-201) PR 머지 + main rebase 완료. `TrackRunner` import 가능.

**Critical context (codex Fix #5 — bounded):** caller trace + `parse_and_run_v2` → TrackRunner 실제 호출 monkeypatch test. silent dead-code 검출. 결과는 audit report markdown 만, 코드 변경 없음.

**Files:**
- Create: `docs/dev-log/2026-05-09-sprint48-bl201-audit.md` (audit report, audit branch)

**Steps:**

- [ ] **E.1: TrackRunner caller trace**
  - grep: `rg "TrackRunner\.invoke" backend/src/`
  - Expected: `compat.py:parse_and_run_v2` 1 호출 (only)

- [ ] **E.2: dispatch table identity 검증**
  - Python: `from src.strategy.pine_v2.track_runner import TrackRunner; TrackRunner._dispatch_table["S"] is event_loop.run_historical`
  - 모두 True 확인

- [ ] **E.3: monkeypatch test 추가 (audit only — 메인 세션이 commit, worker E 는 작성만)**
  - Draft test: `tests/strategy/pine_v2/test_track_runner_caller_trace.py`
  - monkeypatch.setattr(TrackRunner._dispatch_table, "S", mock_S) → parse_and_run_v2(track="S") 가 mock 호출 확인
  - 같은 패턴 A/M

- [ ] **E.4: BL-200 SSOT 영역 충돌 검증**
  - grep: `_names\.STDLIB_NAMES`, `_names\.TA_FUNCTIONS` 가 TrackRunner 분기에 영향 없음 확인
  - 4 invariant 명시

- [ ] **E.5: audit report 작성**
  - `docs/dev-log/2026-05-09-sprint48-bl201-audit.md`
  - findings: caller 1 / dispatch identity 검증 / silent dead-code 0
  - 권장 사항 (있을 시): monkeypatch test 추가 의무 → P3 메인 세션이 commit

- [ ] **E.6: Evaluator dispatch (audit-only mode)**
  - Gate: PASS = grep 결과 1 caller / identity 4 invariant / report 작성

---

## P3 close-out (메인 세션 처리, worker 외)

**Files:**
- Create: `docs/dev-log/2026-05-09-sprint48-close.md`
- Modify: `docs/REFACTORING-BACKLOG.md` (BL-201/203/204 Resolved + Sprint 49 shim removal TODO)
- Modify: `.ai/project/lessons.md` (LESSON 누적 — BL-201 reverse-map 사례 / BL-204 wrong premise 정정)
- Modify: `.claude/CLAUDE.md` (Sprint 47 → Sprint 48 활성 sprint, Sprint 49 분기 추가)

**Steps:**

- [ ] **P3.1: 4 PR 모두 main 머지 확인** (사용자 manual squash)
- [ ] **P3.2: Sprint 48 close-out doc 작성** (3 BL Resolved + dogfood Phase 2 Day 0 발송 prereq + LESSON-064 적용 결과)
- [ ] **P3.3: BL-201/203/204 Resolved + Sprint 49 shim removal TODO**
- [ ] **P3.4: CLAUDE.md 활성 sprint 갱신**
- [ ] **P3.5: Worker E audit 의 monkeypatch test 권장 commit (있을 시)**
- [ ] **P3.6: close-out PR + 사용자 squash merge**
- [ ] **P3.7: dogfood Day 0 발송 timestamp 기록** (사용자 manual 카톡 발송 후)

---

## Self-Review

**1. Spec coverage** (master plan = `~/.claude/plans/sprint-48-gentle-bumblebee.md`):
- ✅ BL-201 (Task A) / BL-203 (Task C) / BL-204 (Task B) 모두 cover
- ✅ dogfood Track 2 (Task D)
- ✅ LESSON-064 audit (Task E)
- ✅ codex G.0 7 fix 모두 반영 (Worker prompt 명시)
- ✅ shim 1 sprint 유지 + Sprint 49 removal TODO (P3.3)
- ✅ B → C 순차 / A → E 순차

**2. Placeholder scan:**
- 모든 Task 가 file paths + commit messages + verification commands 포함
- TBD 있음 = D.3 Day 7 row "Day 0 기록 후 채움" — 의도적 (codex Fix #7)
- 나머지 placeholder 0

**3. Type consistency:**
- `TrackRunner.invoke()` 일관 사용 (Task A 전체)
- `services/__init__.py` shim re-export 일관 (Task C)
- `repositories/__init__.py` shim re-export 일관 (Task B)
- 기존 path 보존 일관 (B/C 모두)

---

## Execution Handoff

Plan complete. Two execution options:

1. **Subagent-Driven (recommended)** — superpowers:subagent-driven-development 으로 5 worker 병렬 dispatch + Evaluator
2. **Inline Execution** — superpowers:executing-plans 으로 메인 세션 직렬 (6-10h)

Subagent-Driven 권장 (Sprint 47 패턴 mirror).
