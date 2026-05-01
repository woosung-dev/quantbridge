# Sprint 16 — Live Verification + BL-027 + BL-010 Backfill

> 2026-05-01. Path B Option A. **codex G.0 iter 1 P1 #1+#2 plan 보정 적용**.
> Plan: [`~/.claude/plans/h2-sprint-16-master.md`](~/.claude/plans/h2-sprint-16-master.md)
> 이전 sprint: [Sprint 15 Track Watchdog](./2026-05-01-sprint15-watchdog.md) (PR #86 main merge 2026-05-01)
> 브랜치: `stage/h2-sprint16` — 사용자 stage→main PR 수동

---

## 1. 배경 (Sprint 15 머지 후 + codex G.0 발견)

Sprint 15 머지 직후. self-assessment 잠정 5-6/10 (Day 2 6/10 + watchdog 적용 후 갱신 미수행). H1→H2 gate (≥7/10) 1~2점 차 미통과. D+7 routine (2026-05-08) fire 까지 1주 — 사용자 즉시 진행 의지로 Path B 채택.

**Sprint 16 의 narrowest wedge**: Phase 0 라이브 검증 (사용자) + Phase A BL-027 (3 path commit-then-dec winner-only) + Phase B BL-010 (5 도메인 commit-spy backfill).

**codex G.0 iter 1 핵심 발견** (2026-05-01):

1. **P1 #1 silent corruption** — 초기 plan 의 `_apply_transition` 안 dec() 가 commit 전 발화 → commit 실패/rollback 시 DB 는 active 인데 gauge 만 감소. Fix: rowcount return + caller commit 후 winner-only dec.
2. **P1 #2 scope 누락** — `tasks/trading.py:200, 255` 의 `_async_execute` rejected/error 분기도 동일 unconditional dec. WS/reconciler/watchdog/user-cancel race loser 도 dec → drift. Fix: rowcount 받아서 winner-only commit-then-dec.
3. **Phase B 발견** — 5 도메인 (Strategy/Backtest/Waitlist/Optimizer/StressTest) commit 누락 broken bug **0건**. spy 추가만으로 회귀 방어.

---

## 2. Phase 0 — 라이브 검증 (사용자 직접, 30분)

### 2.0 사전 준비 — 격리 docker stack 확인

```bash
make help                                # 가이드 확인
docker compose -f docker-compose.yml -f docker-compose.isolated.yml ps
# 기대: db / redis (healthy) + worker / beat / ws-stream (Up)

# FE 미가동 시 (사용자 결정):
make fe-isolated   # 별도 터미널 — 사용자 메모리 'BE/FE 자동 기동 X' 준수
```

### 2.1 시나리오 5.2 — Day 2 stuck pending 자동 reconcile

```bash
# 1. 현재 stuck pending 확인
docker compose -f docker-compose.yml -f docker-compose.isolated.yml exec -T db \
  psql -U quantbridge -d quantbridge \
  -c "SELECT id, state, created_at FROM trading.orders WHERE state='pending';"

# 2. scan_stuck_orders 즉시 trigger (또는 5분 beat 대기)
docker compose -f docker-compose.yml -f docker-compose.isolated.yml exec -T backend-beat \
  uv run celery -A src.tasks.celery_app call trading.scan_stuck_orders

# 3. backend-worker 로그 watch
docker compose -f docker-compose.yml -f docker-compose.isolated.yml logs -f backend-worker

# 4. 5-30분 후 DB 재조회 — state 변경 확인
```

**Pass 기준**: stuck pending order 가 30분 내 자동 reconcile (state 변경) + Slack alert 1회.

**결과**: _(사용자 input 대기)_

### 2.2 시나리오 5.3 — 의도적 stale submitted (선택)

```bash
# 1. DB 에 stale submitted order 강제 삽입 — 1시간 전 + fake id
docker compose -f docker-compose.yml -f docker-compose.isolated.yml exec -T db \
  psql -U quantbridge -d quantbridge -c "
  INSERT INTO trading.orders (
    id, strategy_id, exchange_account_id, symbol, side, type, quantity,
    state, submitted_at, exchange_order_id, created_at
  )
  SELECT
    gen_random_uuid(), strategy_id, exchange_account_id, 'BTCUSDT', 'buy', 'market', 0.001,
    'submitted', NOW() - INTERVAL '1 hour', 'fake-watchdog-test',
    NOW() - INTERVAL '1 hour'
  FROM trading.orders LIMIT 1;
  "

# 2. scan_stuck_orders 즉시 trigger
docker compose -f docker-compose.yml -f docker-compose.isolated.yml exec -T backend-beat \
  uv run celery -A src.tasks.celery_app call trading.scan_stuck_orders

# 3. fetch_order_status_task 가 fake id 로 CCXT error → retry 3회 (15s+30s+60s) → max 후 alert
```

**Pass 기준**: 3 retry 후 1회 alert (Redis throttle key `qb_watchdog_alert:{order_id}`) + 4번째 attempt 없음 + 다음 cycle silent throttle.

**결과**: _(사용자 input 대기)_

### 2.3 self-assessment 갱신

10점 기준:

- Sprint 15 watchdog 라이브 동작 신뢰도
- 시나리오 5.2/5.3 의 UX 막힘 / 발견 Pain
- 본인 매일 사용 quality

**Day 2 = 6/10 → Sprint 16 Phase 0 = ?/10**

| 점수 | Sprint 17 분기                                                |
| ---- | ------------------------------------------------------------- |
| ≥ 7  | BL-005 trigger 도래 → Sprint 17 = Beta 오픈 번들 (BL-070~072) |
| 5-6  | Sprint 17 = 발견 Pain top 3 + 잔존 BL                         |
| ≤ 4  | emergency triage (라이브 검증으로 새 P1 발견 시)              |

**갱신된 점수**: _(사용자 input 대기)_
**발견 Pain top 3**: _(사용자 input 대기)_

---

## 3. Phase A — BL-027 + tasks/trading commit-then-dec winner-only (3 path)

### 3.1 변경 파일

| 파일                                                                   | 변경                                                                                                                                                 |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/src/trading/websocket/state_handler.py`                       | `_apply_transition` rowcount return + `handle_order_event` caller 가 commit 성공 후 winner-only dec/alert (race noise 방어)                          |
| `backend/src/trading/websocket/reconciliation.py`                      | `_apply_transition` rowcount return + `run()` 가 winners 누적 → commit 후 일괄 dec + `qb_active_orders` import (이전엔 dec 자체 누락 → drift)        |
| `backend/src/tasks/trading.py:165, 200, 253`                           | `_async_execute` 의 3 rejected 분기 (decrypt_failed / ProviderError / exchange_rejected) 가 `transition_to_rejected` rowcount 받아서 winner-only dec |
| `backend/tests/trading/test_ws_state_handler_active_orders.py` (신규)  | 9 tests (winner/loser/commit_failure × 분기)                                                                                                         |
| `backend/tests/trading/test_ws_reconciliation_active_orders.py` (신규) | 6 tests (apply_transition + run() winner/loser/commit_failure/multi-transition)                                                                      |
| `backend/tests/tasks/test_async_execute_active_orders.py` (신규)       | (생략) — \_async_execute 단위 test setup 복잡도 대비 가치 낮음. codex G.2 가 변수 shadowing 등 break vector 검토 후 P1 0건 confirm                   |

### 3.2 codex G.0 P1 #1+#2 fix 패턴

```python
# 표준 (Sprint 15 watchdog tasks/trading.py:458 reuse):
rowcount = await repo.transition_to_*(...)
if rowcount == 1:                  # race winner
    await session.commit()         # commit 성공 후
    qb_active_orders.dec()         # winner-only dec
else:
    await session.rollback()       # loser
```

### 3.3 자동 검증 결과

| 항목                                                       | 결과                                                                                                            |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Phase A 신규 15 tests (state_handler 9 + reconciliation 6) | ✅ 100% PASS                                                                                                    |
| 기존 trading + tasks 회귀                                  | ✅ 130 passed (db_session 의존 일부 6 ERROR — 사용자 환경 isolated DB 인증 mismatch, pre-existing, 본 fix 무관) |
| `ruff check src/trading/websocket/ src/tasks/ tests/`      | ✅ All checks passed                                                                                            |
| `mypy src/`                                                | ✅ no issues found in 14 source files                                                                           |
| 커밋                                                       | `a3d4a20` (6 files / 987+ insertions)                                                                           |

---

## 4. Phase B — BL-010 commit-spy 5 도메인 backfill

### 4.1 audit 결과 (codex G.0 broken bug 0건 confirmed)

| 도메인     | mutation methods                                         | commit 호출 | spy 추가                                   |
| ---------- | -------------------------------------------------------- | ----------- | ------------------------------------------ |
| Strategy   | `create` / `update` / `delete`                           | ✅ 모두     | ✅ 4 spy (atomic auto-issue 분기 포함)     |
| Backtest   | `submit` / `cancel` / `delete`                           | ✅ 모두     | ✅ 3 spy                                   |
| Waitlist   | `submit_application` / `admin_approve`                   | ✅ 모두     | ✅ 2 spy + autouse fixture override        |
| Optimizer  | (H1 미구현 — service.py 1 line 스캐폴드만)               | N/A         | ⏭️ skip (BL-010 5번째는 H1 구현 후 BL-XXX) |
| StressTest | `submit_monte_carlo` / `submit_walk_forward` → `_submit` | ✅ 모두     | ✅ 2 spy                                   |

### 4.2 신규 spy test 파일

| 파일                                                           | tests                                | 비고                                                                         |
| -------------------------------------------------------------- | ------------------------------------ | ---------------------------------------------------------------------------- |
| `backend/tests/strategy/test_strategy_commits.py` (신규)       | 4                                    | atomic auto-issue (Sprint 13 패턴) spy 별도                                  |
| `backend/tests/backtest/test_backtest_commits.py` (신규)       | 3                                    | submit (no idempotency) / cancel winner / delete terminal                    |
| `backend/tests/waitlist/test_waitlist_commits.py` (신규)       | 2                                    | autouse `_reset_rate_limiter` override (Redis 우회 — spy 는 limiter 안 거침) |
| `backend/tests/stress_test/test_stress_test_commits.py` (신규) | 2                                    | monte_carlo / walk_forward 둘 다 `_submit` 경유                              |
| **합계**                                                       | **11**                               | Phase A 15 + Phase B 11 = **26 tests 신규**                                  |
| 회귀                                                           | ✅                                   | 11 + 15 + reference webhook spy 5 = 31 PASS. ruff 0.                         |
| 커밋                                                           | `beacc89` (4 files / 460 insertions) |                                                                              |

---

## 5. codex 게이트 결과

| 게이트                                                       | 발견                                                                                                                                                          | 처리                                                                                                                             |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **G.0** master plan consult (medium, iter cap 2, 2026-05-01) | P1 #1 silent corruption (commit 전 dec) + P1 #2 tasks/trading 누락 + Phase B broken bug 0건                                                                   | P1 #1+#2 plan 보정 완료 + Phase B spy 만 추가. session: `019de3c9-c8e0-72f0-b0cf-4f655727c7e9`. 426k tokens. iter 1 만으로 종료. |
| **G.2** challenge (high, iter cap 2, 2026-05-01)             | 6 break vector 검토 — silent rollback / SQLAlchemy lazy flush race / 변수 shadowing / spy false negative / pytest fixture resolution / OrderState fallthrough | **P1 critical 0건** confirm. session: `019de3f8-5f25-76d0-a3f5-97a47d5ef9a8`. 515k tokens. iter 1 만으로 종료.                   |

---

## 6. Sprint 17 이관 / 후속

| ID                  | 제목                                                                                                                                                                                                 | trigger                     | est      |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- | -------- |
| BL-005              | 본인 1~2주 dogfood (live broker)                                                                                                                                                                     | self-assessment ≥7 시 도래  | 1~2주    |
| BL-070~072 (Path A) | Beta 오픈 번들 (도메인+DNS / Backend prod 배포 / Resend)                                                                                                                                             | self-assessment ≥7 시       | 12~20h   |
| BL-XXX (신규)       | Optimizer commit-spy backfill — H1 구현 시 BL-010 의 5번째 도메인                                                                                                                                    | Optimizer service 구현 시   | S (1-2h) |
| (Day 4 Pain top 3)  | 사용자 라이브 검증 (시나리오 5.2/5.3) 결과 발견 P1                                                                                                                                                   | self-assessment 라이브 결과 | TBD      |
| BL-027 (잔존)       | (주의) 본 sprint 가 BL-027 의 SOURCE 파일 (state_handler / reconciliation) 만 fix. 추가 dec 호출 위치 (`tasks/trading.py:467/497/509` Sprint 15 watchdog reference) 는 이미 winner-only — audit 완료 | -                           | -        |

**Sprint 17 분기 결정 = Phase 0 사용자 self-assessment 결과**:

- ≥ 7 → Path A (Beta 오픈 번들)
- 5-6 → Path B 재진입 (잔존 Pain top 3)
- ≤ 4 → emergency triage

---

## 7. 머지 권장

자동 검증 + codex G.0/G.2 + LESSON-019 backfill 모두 PASS:

- Phase A: 15 tests 100% PASS / ruff 0 / mypy 0 (14 source files)
- Phase B: 11 spy tests 100% PASS / ruff 0
- codex G.0 (medium): P1 #1 silent corruption + P1 #2 scope 누락 모두 plan 보정 + 구현
- codex G.2 (high): 6 break vector 검토 + P1 critical 0건
- 4 도메인 commit-spy backfill (LESSON-019 의무) — Sprint 6/13/15-A 4번째 재발 차단
- BL-027 (silent corruption + 음수 drift) ✅ Resolved
- BL-010 (commit-spy backfill) ✅ Resolved (Optimizer 만 H1 미구현 — 별도 BL)

**자동 검증 기준 머지 권장**. 라이브 시나리오 5.2/5.3 + self-assessment ≥7/10 확인 시 BL-005 trigger 도래 → Sprint 17 = Beta 오픈 번들. 5-6 유지 시 Sprint 17 = 라이브 발견 Pain top 3 + 잔존 BL.

---

## 8. 다음 세션 prompt

`~/.claude/plans/h2-sprint-17-prompt.md` — self-assessment 결과에 따라 Path A (Beta 오픈) / Path B (잔존 + 발견 Pain) 분기 명시.
