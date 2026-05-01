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

_(implementation 후 fill-in)_

| 파일                                                                   | 변경     |
| ---------------------------------------------------------------------- | -------- |
| `backend/src/trading/websocket/state_handler.py`                       | \_       |
| `backend/src/trading/websocket/reconciliation.py`                      | \_       |
| `backend/src/tasks/trading.py:200, 255`                                | \_       |
| `backend/tests/trading/test_ws_state_handler_active_orders.py` (신규)  | \_ tests |
| `backend/tests/trading/test_ws_reconciliation_active_orders.py` (신규) | \_ tests |
| `backend/tests/tasks/test_async_execute_active_orders.py` (신규)       | \_ tests |

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

_(implementation 후 fill-in)_

| 항목                                                  | 결과 |
| ----------------------------------------------------- | ---- |
| `pytest -q` (전체)                                    | \_   |
| `pytest tests/trading/ tests/tasks/ -v`               | \_   |
| `ruff check src/trading/websocket/ src/tasks/ tests/` | \_   |
| `mypy src/`                                           | \_   |

---

## 4. Phase B — BL-010 commit-spy 5 도메인 backfill

### 4.1 audit 결과

_(implementation 후 fill-in — codex G.0 audit: broken bug 0건 confirmed)_

| 도메인     | mutation methods | commit 호출 | spy 추가 |
| ---------- | ---------------- | ----------- | -------- |
| Strategy   | \_               | \_          | \_       |
| Backtest   | \_               | \_          | \_       |
| Waitlist   | \_               | \_          | \_       |
| Optimizer  | \_               | \_          | \_       |
| StressTest | \_               | \_          | \_       |

### 4.2 신규 spy test 파일

_(implementation 후 fill-in)_

| 파일                                                           | tests |
| -------------------------------------------------------------- | ----- |
| `backend/tests/strategy/test_strategy_commits.py` (신규)       | \_    |
| `backend/tests/backtest/test_backtest_commits.py` (신규)       | \_    |
| `backend/tests/waitlist/test_waitlist_commits.py` (신규)       | \_    |
| `backend/tests/optimizer/test_optimizer_commits.py` (신규)     | \_    |
| `backend/tests/stress_test/test_stress_test_commits.py` (신규) | \_    |

---

## 5. codex 게이트 결과

| 게이트                                                       | 발견                                                                                        | 처리                                                                                                                             |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **G.0** master plan consult (medium, iter cap 2, 2026-05-01) | P1 #1 silent corruption (commit 전 dec) + P1 #2 tasks/trading 누락 + Phase B broken bug 0건 | P1 #1+#2 plan 보정 완료 + Phase B spy 만 추가. session: `019de3c9-c8e0-72f0-b0cf-4f655727c7e9`. 426k tokens. iter 1 만으로 종료. |
| **G.2** challenge (high, iter cap 2)                         | _(implementation 후 fill-in)_                                                               | \_                                                                                                                               |

---

## 6. Sprint 17 이관 / 후속

_(implementation + 사용자 self-assessment 후 fill-in)_

| ID  | 제목 | trigger | est |
| --- | ---- | ------- | --- |
| TBD | \_   | \_      | \_  |

---

## 7. 머지 권장

_(자동 검증 PASS + codex G.2 PASS + Phase 0 라이브 검증 결과 후 fill-in)_

---

## 8. 다음 세션 prompt

`~/.claude/plans/h2-sprint-17-prompt.md` — self-assessment 결과에 따라 Path A (Beta 오픈) / Path B (잔존 + 발견 Pain) 분기 명시.
