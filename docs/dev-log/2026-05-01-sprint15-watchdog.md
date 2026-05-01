# Sprint 15 — Stuck Order Watchdog (BL-001 + BL-002)

> 2026-05-01. Track P0 trading hardening. **자동 검증 완료** + **사용자 라이브 dogfood Day 4 대기**.
> Plan: [`~/.claude/plans/h2-sprint-15-master.md`](~/.claude/plans/h2-sprint-15-master.md)
> 이전 sprint: [Sprint 14 Track UX-2](./../../docs/dev-log/2026-04-27-dogfood-day3.md) (PR #81 main merge 2026-04-27)

---

## 1. 배경 (Day 2 발견 + 정합성)

dogfood Day 2 (2026-04-26) 자동 검증 후 격리 DB 직접 조회 결과:

```
trading.orders: 1 row
  id           = 13705a91-8a85-4115-a165-484d312b9b35
  state        = pending (NOT submitted)
  created_at   = 2026-04-26 14:27:25 UTC (14h+ 고착)
  submitted_at = NULL
  filled_at    = NULL
```

→ **Sprint 14 Phase C fix (`receipt.status=submitted` 시 attach_exchange_order_id 만, terminal 전이 WS event/reconciler 의존) 의 watchdog 부재 = silent data corruption**. + **Day 2 hotfix 직후 별도 broken bug (dispatch 누락 / broker 메시지 만료) 가능성**.

→ 본 Sprint 의 scope: **pending + submitted 양쪽** stuck order 자동 reconcile + alert. BL-001 (submitted watchdog) + BL-002 (Day 2 stuck pending cleanup) 합본.

---

## 2. 변경 요약

### Phase A.1 (`backend/src/trading/providers.py`)

- `OrderStatusFetch` dataclass — `status: Literal["filled","submitted","rejected","cancelled"]` 4-state. cancelled 별도 (사용자/exchange 정상 취소 vs rejected = 검증 실패)
- `ExchangeProvider` Protocol 에 `fetch_order(creds, exchange_order_id, symbol)` 메서드
- 4 provider 구현 — `BybitDemo` / `BybitFutures` / `OKXDemo` / `Fixture`
- `_map_ccxt_status_for_fetch` helper (4-state)
- `_bybit_fetch_order_impl` 공유 (spot/linear)
- `_build_order_status_fetch` 정규화 (Decimal 변환 + None graceful)
- TDD: 10 tests (`test_provider_fetch_order.py`)

### Phase A.2 (`backend/src/tasks/trading.py`)

- `_async_fetch_order_status(order_id, attempt) -> dict` — submitted watchdog core
  - state guard (terminal/non-submitted/null exchange_order_id skip)
  - decrypt + provider.fetch_order
  - status 분기 (filled/rejected/cancelled → transition\_\* + commit + dec, submitted → retry 또는 giveup+alert)
- `fetch_order_status_task` (`@shared_task bind=True max_retries=3`) — Celery sync wrapper
- `_build_watchdog_retry_kwargs` — codex G.2 P1 #1 fix (args=[order_id] 명시 override 로 positional 충돌 회피)
- `_try_watchdog_alert_throttled` — codex G.0 P1 #2 fix (Redis SET NX EX 3600)
- `_get_redis_lock_pool_for_alert` — test mock 가능 indirection
- `_async_execute` submitted 분기 끝에 `fetch_order_status_task.apply_async(args=[str(order_id)], countdown=15)` enqueue
- TDD: 11 tests (`test_fetch_order_status_task.py`)

### Phase A.3 (`backend/src/tasks/orphan_scanner.py` + `repository.py` + `celery_app.py`)

- `OrderRepository.list_stuck_pending(cutoff)` — pending + created_at < cutoff
- `OrderRepository.list_stuck_submitted(cutoff)` — submitted + submitted_at < cutoff + **exchange_order_id IS NOT NULL** (codex G.0 P1 #3)
- `OrderRepository.list_stuck_submission_interrupted(cutoff)` — submitted + **NULL exchange_order_id** (별도 manual cleanup 대상)
- `scan_stuck_orders_task` (5분 beat) — 위 3 list 호출
  - pending → `execute_order_task.apply_async` (dispatch 복구) + per-order throttled alert
  - submitted+id → `fetch_order_status_task.apply_async` (terminal 확인)
  - submitted+null → throttled alert 만 (BL-028 force-reject script 대상)
- TDD: 7 tests (`test_orphan_scanner.py`)

### codex G.2 P1 fix (master plan §5)

- **P1 #1 — Celery retry args collision** ✅ — `_build_watchdog_retry_kwargs` pure helper 분리. `args=[order_id]` 명시 override
- **P1 #2 — ProviderError silent skip** ✅ — `provider.fetch_order` 예외 시 retry signal (max attempts 후 alert)
- **P1 #3 — WS state_handler.py:176 unconditional dec** → BL-027 분리 (Sprint 16+ 이관, watchdog 가 worse 만들지 않음)

---

## 3. 자동 검증 결과

| 항목                      | 결과                                                         |
| ------------------------- | ------------------------------------------------------------ |
| `pytest -q`               | ✅ **1216 passed** (Sprint 14 1185 → +31) / 18 skip / 0 fail |
| `ruff check src/ tests/`  | ✅ All checks passed                                         |
| `mypy src/`               | ✅ Success: no issues found in 144 source files              |
| Trading domain regression | ✅ 233 → 240 tests (+7)                                      |

신규 테스트:

- `tests/trading/test_provider_fetch_order.py`: 10 (4-state mapping + 4 provider × fetch_order + dataclass frozen + OKX passphrase guard)
- `tests/trading/test_fetch_order_status_task.py`: 11 (filled/rejected/cancelled transition + race winner-only dec + retry/giveup signal + alert throttle + null exchange_order_id skip + provider error retry/alert + Celery retry args/kwargs)
- `tests/trading/test_orphan_scanner.py`: 7 (list_stuck_pending/submitted/submission_interrupted + scan enqueue pending/submitted + alert throttle + no-op)

---

## 4. codex 게이트 결과

| 게이트                               | 발견                                                                  | 처리                             |
| ------------------------------------ | --------------------------------------------------------------------- | -------------------------------- |
| **G.0** master plan consult (medium) | P1 #1 race / #2 alert flood / #3 null exchange_order_id 윈도우        | 모두 master plan 에 fix 반영     |
| **G.2** challenge (high)             | P1 #1 retry args / #2 provider error silent / #3 WS unconditional dec | #1 + #2 즉시 fix. #3 BL-027 분리 |

iter cap 2 준수 (각 게이트 1차만).

---

## 5. dogfood Day 4 자동 검증 결과 (2026-05-01)

격리 모드 사용자 기동 후 AI 자동 검증 7+6 = 13 항목 진행.

### 5.0 인프라 자동 검증 (Bash, ✅ 7/7 PASS)

| #   | 항목                                   | 결과                                                                                            |
| --- | -------------------------------------- | ----------------------------------------------------------------------------------------------- |
| 1   | docker stack 5/5 Up                    | ✅ db / redis / worker / beat / ws-stream (1분 전 재시작)                                       |
| 2   | worker container Sprint 15 코드 픽업   | ✅ `fetch_order_status_task` + `scan_stuck_orders_task` + `_async_fetch_order_status` 모두 등록 |
| 3   | Beat schedule `scan-stuck-orders` 등록 | ✅ `trading.scan_stuck_orders schedule=300.0` (5min)                                            |
| 4   | BE :8100 `/health`                     | ✅ `{"status":"ok","env":"development"}`                                                        |
| 5   | BE `/metrics`                          | ✅ `qb_active_orders 0.0` / `qb_redis_lock_pool_healthy 1.0` / `qb_ws_*` 정상 노출              |
| 6   | scan_stuck_orders 즉시 trigger         | ✅ task `353ef6a9-...` succeeded `{"pending":0, "submitted":0, "interrupted":0}` (no-op 정상)   |
| 7   | FE :3100 LISTEN                        | ✅ Next.js dev server                                                                           |

### 5.1 Public 페이지 자동 검증 (curl, ✅ 6/6 PASS)

Playwright MCP browser user data dir 가 다른 process 에서 lock 중 → curl fallback (status code + HTML title).

| #   | path             | status | size     | title                          |
| --- | ---------------- | ------ | -------- | ------------------------------ |
| 1   | `/`              | 200    | 30,509 B | QuantBridge                    |
| 2   | `/disclaimer`    | 200    | 32,989 B | Disclaimer · QuantBridge       |
| 3   | `/terms`         | 200    | 34,040 B | Terms of Service · QuantBridge |
| 4   | `/privacy`       | 200    | 35,503 B | Privacy Policy · QuantBridge   |
| 5   | `/not-available` | 200    | 26,971 B | QuantBridge                    |
| 6   | `/waitlist`      | 200    | 36,535 B | QuantBridge                    |

(콘솔 에러 / 스크린샷은 Playwright lock 으로 skip — 사용자 브라우저로 별도 확인 권장.)

### 5.2 사용자 직접 영역 — Live 시나리오

자동 검증 불가 영역 — 사용자 브라우저로 직접 진행 필요:

#### A. Strategy 생성 → Test Order Dialog (Sprint 13/14 회귀)

1. http://localhost:3100/sign-in — Clerk 로그인
2. http://localhost:3100/strategies/new — Strategy 생성 (Pine source 입력)
3. 생성 직후 redirect → `?tab=webhook` 자동 진입 + amber card webhook URL/secret 즉시 표시 (Sprint 14 hydration race fix 회귀)
4. http://localhost:3100/trading — exchange account 등록 (Bybit Demo API key)
5. **Test Order Dialog** → BTCUSDT limit order 0.001 BTC + Idempotency-Key
6. DB 에서 Order state 추적: pending → submitted (REST 30s) → ?
7. backend-worker 로그에서 `fetch_order_status_task[<uuid>] received` + 15s 후 first attempt 확인

#### B. Watchdog 실 동작 검증 (Sprint 15 본 작업)

- **fetch_order_status_task** 가 submitted 분기 enqueue 후 15s 뒤 첫 호출 → Bybit Demo `fetch_order` 응답 검증
  - 즉시 filled → `qb_active_orders` -1 + DB state=filled
  - 여전히 submitted → 30s 후 retry, 60s 후 retry, 그 후 alert + giveup
  - rejected/cancelled → DB state 전이 + dec
- **scan_stuck_orders** 5분마다 자동 발화 — DB watch (5분 후 worker logs 에 `Task trading.scan_stuck_orders[...] succeeded` 발화)

#### C. self-assessment

10점 기준 측정:

- "본인이 매일 쓰고 싶은 quality 인가" (Trust ≥ Scale > Monetize 기준)
- 라이브 시나리오 A + B 의 신뢰도 / UX 막힘 / 발견 Pain 종합

**≥ 7/10 = H1→H2 gate 통과** → BL-005 (1~2주 dogfood) trigger 도래 → Sprint 16 = Beta 오픈 번들 (BL-070~072)
**< 7/10** → Sprint 16 = 발견 Pain + BL-027 (WS unconditional dec) + BL-010 (commit-spy 도메인 확장)

### 5.3 의도적 stale order 시나리오 (선택, 사용자 직접)

Day 2 stuck order `13705a91` 가 DB 에서 사라짐 (cleanup 됐거나 격리 DB 재생성). 인위적 검증 시:

1. 사용자가 brower 통해 Test Order 1건 생성 (위 시나리오 A)
2. 또는 직접 SQL: `UPDATE trading.orders SET state='submitted', submitted_at=NOW() - INTERVAL '1 hour', exchange_order_id='fake-watchdog-test' WHERE id=...;`
3. `docker compose -f docker-compose.yml -f docker-compose.isolated.yml exec -T backend-beat uv run celery -A src.tasks.celery_app call trading.scan_stuck_orders`
4. worker logs 에서 fetch_order_status_task 호출 → CCXT fetch_order 가 fake id 로 ProviderError → retry 3회 → max attempts alert

**보고**: 검증 결과 (DB state 변화 / alert 발화) + self-assessment 점수 → 다음 sprint 분기 결정.

---

## 5-archived. dogfood Day 4 사전 가이드 (rebuild 전 plan)

자동 검증으론 측정 불가능한 시나리오. 격리 모드 (`make dev-isolated`) 사용:

### 5.1 사전 준비

```bash
# 격리 docker stack 재시작 (worker container 가 sprint 15 코드 픽업)
make down-isolated
docker compose -f docker-compose.yml -f docker-compose.isolated.yml build backend-worker backend-beat
make up-isolated
make be-isolated   # 별도 터미널
make fe-isolated   # 별도 터미널
```

### 5.2 시나리오 1 — Day 2 stuck order `13705a91` 자동 reconcile

```bash
# 1. 현재 stuck pending 확인
docker compose -f docker-compose.yml -f docker-compose.isolated.yml exec -T db \
  psql -U quantbridge -d quantbridge \
  -c "SELECT id, state, created_at FROM trading.orders WHERE state='pending';"
# 예상: 13705a91 가 그대로 (cleanup 전)

# 2. Celery beat 가 5분 안에 scan_stuck_orders 자동 trigger.
#    또는 즉시 trigger 하려면:
docker compose -f docker-compose.yml -f docker-compose.isolated.yml exec -T backend-beat \
  uv run celery -A src.tasks.celery_app call trading.scan_stuck_orders

# 3. backend-worker 로그 watch
make logs-isolated  # 또는 docker compose logs -f backend-worker

# 4. 5분 후 DB 재조회
# 예상: state=pending → state=submitted (Bybit Demo 응답 시) 또는 rejected (잔고 부족 등)
```

**Pass 기준**: stuck pending order 가 30분 내 자동 reconcile (state 변경) + Slack alert 1회 (qb_scan_alert:pending:{order_id} key 발화).

### 5.3 시나리오 2 — 의도적 stale submitted (선택)

```bash
# 1. DB 에 stale submitted order 강제 삽입
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

# 2. fetch_order_status_task 가 5분 안에 trigger (또는 즉시):
docker compose -f docker-compose.yml -f docker-compose.isolated.yml exec -T backend-beat \
  uv run celery -A src.tasks.celery_app call trading.scan_stuck_orders

# 3. fetch task 가 fake exchange_order_id 로 Bybit fetch_order 호출 → ccxt error → retry → max 후 alert
```

**Pass 기준**: 3 retry (15s + 30s + 60s) 후 Slack alert 1회. 4번째 attempt 안 보냄. 동일 cycle 의 다음 scan (5분 후) 도 alert silent (Redis throttle).

### 5.4 self-assessment

dogfood Day 3 = 6/10 (라이브 미수행). 본 sprint 후 라이브 시:

- ✅ Day 2 stuck order 자동 cleanup 검증 → +1점
- ✅ silent data corruption 위험 차단 → +1점
- 예상 self-assessment: **7~8/10** (H1→H2 gate 통과)

---

## 6. Sprint 16+ 이관

신규 BL 등록 (master plan §8):

| ID     | 제목                                                                            | trigger                              | est      |
| ------ | ------------------------------------------------------------------------------- | ------------------------------------ | -------- |
| BL-027 | WS state_handler.py:176 unconditional dec + reconciliation.py:182 dec 누락      | Sprint 16 직후                       | M (3-4h) |
| BL-028 | scripts/force-reject-stuck.py — submitted+null exchange_order_id manual cleanup | submission_interrupted alert 발화 시 | S (1-2h) |
| BL-029 | provider.fetch_order CCXT rate limit Redis throttle middleware                  | rate limit alert 다발 시             | M (3-4h) |

기존 BL:

- **BL-010** commit-spy 도메인 확장 → Sprint 16 Track 우선 (4번째 broken bug 재발 예방)
- **BL-005** 본인 1~2주 dogfood → BL-001/002 완료 + self-assessment ≥7 → trigger 도래

---

## 7. 머지 권장

- 자동 검증 100% PASS (1216 BE / ruff 0 / mypy 0)
- codex G.0 + G.2 P1 critical 모두 fix 또는 BL 분리
- Sprint 13 LESSON-019 (commit-spy 회귀) 적용 — fetch*order_status_task 가 transition*\* + commit 호출 시 race winner only

**자동 검증 기준 머지 권장**. 라이브 시나리오 5.2/5.3 + self-assessment ≥7/10 확인 시 **H1→H2 gate 통과** + BL-005 (본인 1~2주 dogfood) trigger 도래 → 다음 sprint 는 Beta 오픈 번들 (BL-070~072) 또는 commit-spy 백필 (BL-010).

self-assessment < 7/10 시 Sprint 16 Track 우선순위:

1. 라이브 발견 추가 Pain (Day 4 dogfood 결과 반영)
2. BL-027 WS unconditional dec fix
3. BL-010 commit-spy 도메인 확장

---

## 8. 다음 세션 prompt

`~/.claude/plans/h2-sprint-16-prompt.md` 별도 작성 — Sprint 16 우선순위 분기:

**Path A (self-assessment ≥7)**: Beta 오픈 번들 (BL-070~072 도메인+DNS+백엔드 배포+Resend) — 사용자 메모리 "Dogfood-first indie SaaS" 정합. 본인 매일 사용 가능 quality 도달 후 외부 사용자.

**Path B (self-assessment <7)**: Sprint 15 라이브 발견 Pain + BL-027/BL-010 + Day 4 회고 반영.
