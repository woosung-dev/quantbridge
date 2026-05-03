# Sprint 24a — WebSocket 안정화 (BL-011/012/013/016)

**날짜**: 2026-05-03 (Sprint 22+23 cascade 직후)
**브랜치**: `stage/h2-sprint22` (Sprint 22+23+24a sequential cascade, 단일 PR)
**범위**: BL-011 + BL-012 + BL-013 + BL-016 = **4 BL ✅ Resolved** (Sprint 24 의 Track 2)
**Out of scope (Sprint 24b 후속)**: Track 1 (Backend E2E 자동 dogfood — BL 등록 없음, 순수 자동 회귀 가드)

---

## §1. 배경 + 결정

Sprint 22+23 cascade 완료 후 사용자 dogfood 늦추는 동안 AI 가 진행할 next workflow phase. memory `feedback_dogfood_first_indie` (Trust ≥ Scale) 정합. Hybrid 옵션 사용자 선택:

- **Sprint 24a (본 dev-log)**: Track 2 WebSocket 안정화 (~9h 실측, 24h 한도 내)
- **Sprint 24b (후속 cascade)**: Track 1 자동 dogfood (~10h, 별도 cascade)

권장 분기 = 사용자가 "권장 방식" 선택. 4 BL Track 2 만 본 sprint, Track 1 은 별도 cascade.

---

## §2. codex Generator-Evaluator

### 2.1 G.0 (medium reasoning, 1 iter, ~50k tokens)

**Verdict**: FIX FIRST → plan v2 surgery 후 통과.

**P1 5건 (모두 plan v2 반영)**:

| ID  | 발견                                                       | plan v2 반영                                                                                     |
| --- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| #1  | RedisLock graceful degrade vs WS correctness 충돌          | `_ws_lease.py` 가 wrap, acquired=False → None 반환 + stream skip                                 |
| #2  | prefork shutdown 설계 충돌 (lease 객체 소유 위치)          | `worker_process_shutdown` 에 `signal_all_stop_events()` 호출 + lease release async CM finally 만 |
| #3  | circuit breaker 정책 모순 (1회 vs 3회)                     | `ws:auth:failures` (3회 누적) + `ws:auth:blocked` (즉시) TTL 분리                                |
| #4  | BL-016 retry 위치 모호 (supervisor 내부 reconnect 와 충돌) | task layer (`_stream_main`) TimeoutError catch + record_network_failure. supervisor 손대지 않음  |
| #5  | dogfood_report 재사용 과장                                 | (Track 1 — 본 sprint 24a 후속 24b 로 이관)                                                       |

**P2 4건**: reconcile lease 기반 / multi-account Track 1 / `--run-integration` subprocess / Frontend storageState 옵션 — 모두 plan v2 반영 또는 후속.

### 2.2 G.2 (high reasoning, 1 iter, ~99k tokens)

**Verdict**: FIX FIRST → P1 2건 즉시 fix (Phase B.5).

**P1 2건 (Phase B.5 즉시 fix)**:

| ID                        | 발견                                                                                                                                                             | 본 sprint 처리                                                                                                                                                                               |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| #1 (split-brain critical) | heartbeat extend 실패 시 loop 만 종료, \_stream_main 은 계속 stop_event.wait → lease 만료 후 다른 worker 가 acquire → 두 stream 동시 활성 (split-brain)          | ✅ Phase B.5: WsLease 에 `lost_event: asyncio.Event` 주입. heartbeat 실패 시 `lost_event.set()` → `_stream_main` 이 stop_event 와 함께 wait → lease lost 시 stream 종료 + lease 자동 release |
| #2                        | `test_websocket_task_routing.py:test_duplicate_enqueue_returns_no_op` 가 삭제된 `_PROCESS_LOCK / _PROCESS_ACTIVE_STREAMS` 참조 → CI fail (실제 회귀 1 fail 확인) | ✅ Phase B.5: acquire_ws_lease mock (None 반환) 으로 마이그레이션                                                                                                                            |

**P2 4건 (Sprint 25+ 이관 BL 등록)**:

- #1: INCR + EXPIRE 비원자성 (Lua wrap) — BL-108 신규 (P3 S 30m)
- #2: test_first_connect_timeout 가 account-not-found 조기 return (실제 timeout path 미검증) — BL-109 신규 (P3 S 1h)
- #3: prefork SIGTERM / multi-process lease integration test 부재 — BL-110 신규 (P2 S 1-2h, mark.integration)
- #4: circuit reset admin/CLI path 부재 (현재 `redis-cli DEL` 만) — BL-111 신규 (P3 S 1-2h)

**False Alarms (G.2 가 직접 검증)**: lease vs connect race (SET NX atomic) / heartbeat timing (즉시 시작) / same-account concurrent (SET NX 1 winner) / network reconnect false positive (supervisor 내부 reconnect 는 task layer 미도달) / `_STOP_EVENTS_LOCK` thread-safe — 모두 non-issue.

---

## §3. Implementation

### Phase A.1 — BL-011 Redis lease + heartbeat

**신규**: `backend/src/tasks/_ws_lease.py`

- `acquire_ws_lease(account_id, ttl_ms=60_000) -> WsLease | None` — RedisLock wrap. `acquired=False` 시 None 반환 (codex G.0 P1 #1 fix — graceful degrade vs correctness 분리)
- `WsLease` async CM — `__aenter__` heartbeat task 시작, `__aexit__` heartbeat cancel + lock release
- `_heartbeat_loop()` — TTL 의 1/3 (20s) 마다 `RedisLock.extend(ttl_ms)`. extend 실패 시 loop 종료 + Slack alert
- `is_lease_active(account_id) -> bool` — reconcile path 용 (codex G.0 P2 #1)

**MODIFIED**: `backend/src/tasks/websocket_task.py`

- `_PROCESS_ACTIVE_STREAMS` + `_PROCESS_LOCK` + `import threading` 일부 제거 (`_STOP_EVENTS_LOCK` 만 유지)
- `_run_async`: `acquire_ws_lease()` → None 시 "duplicate" 반환, async with lease: `_stream_main()`

**신규 tests**: `backend/tests/tasks/test_ws_lease.py` 10 tests PASS (single acquire / contention / Redis 장애 / async CM release / heartbeat extend / cancel on exit / key isolation / is_lease_active 3 분기).

### Phase A.2 — BL-012 prefork 복귀 + reconcile lease

**MODIFIED**: `backend/docker-compose.yml`

- `backend-ws-stream` `--pool=solo --concurrency=1` → `--pool=prefork --concurrency=2` (Sprint 12 G4 revisit 한계 해소)
- 주석 추가 — Sprint 24 BL-012 (prefork 복귀 가능 이유 명시)

**MODIFIED**: `backend/src/tasks/celery_app.py`

- `worker_process_shutdown` hook 에 `signal_all_stop_events()` 호출 추가 (codex G.0 P1 #2 fix — prefork child 도 ws_stream graceful shutdown)

**MODIFIED**: `backend/src/tasks/websocket_task.py:_reconcile_async`

- `_PROCESS_ACTIVE_STREAMS` snapshot → `is_lease_active()` 호출 (codex G.0 P2 #1)

### Phase B.1 — BL-013 auth circuit breaker (failures/blocked TTL 분리)

**신규**: `backend/src/tasks/_ws_circuit_breaker.py` (codex G.0 P1 #3 fix)

- `is_circuit_open(account_id) -> bool` — `ws:auth:blocked:{account_id}` exists check
- `record_auth_failure(account_id)` — BybitAuthError 즉시 block (PX 3_600_000) + counter reset
- `record_network_failure(account_id) -> bool` — `ws:auth:failures:{account_id}` INCR (TTL 600s sliding window) + 3회 누적 시 block
- `reset_circuit(account_id)` — admin/runbook helper

**MODIFIED**: `backend/src/tasks/websocket_task.py`

- `_run_async` 에 `is_circuit_open()` check 먼저 → "circuit_open" 반환
- `_stream_main` BybitAuthError catch → `record_auth_failure()` 호출 + Slack alert 메시지에 수동 해제 runbook 추가

**신규 tests**: `backend/tests/tasks/test_ws_auth_circuit_breaker.py` 7 tests PASS.

**Runbook 추가**: Slack alert 메시지에 `redis-cli DEL ws:auth:blocked:{account_id}` 명시.

### Phase B.2 — BL-016 first_connect race (task layer 카운트)

**MODIFIED**: `backend/src/tasks/websocket_task.py:_stream_main`

- `BybitPrivateStream.__aenter__` 60s timeout 시 raise 되는 `TimeoutError` catch 추가
- catch 시 `record_network_failure()` 호출 → 3회 누적 시 BL-013 circuit breaker 자동 trigger
- supervisor 내부 reconnect (1→30s) 손대지 않음 (codex G.0 P1 #4)

**신규 tests**: `backend/tests/tasks/test_first_connect_race.py` 3 tests PASS.

**MODIFIED**: `backend/src/common/metrics.py`

- 신규 `qb_ws_auth_circuit_total{outcome}` Counter (block_auth / block_network / network_failure / restored / skipped)

---

## §4. 검증 결과

### 자동 검증

```
TEST_DATABASE_URL=...localhost:5433/quantbridge \
TEST_REDIS_LOCK_URL=...localhost:6380/3 \
uv run pytest --timeout=120
```

(Phase E commit 직전 결과 보강)

- ruff 0 / mypy 0 (147 source files, +1 신규 metrics)
- 신규 20 tests (BL-011 lease 10 + BL-013 circuit breaker 7 + BL-016 first_connect 3) 100% pass

### 라이브 검증 (사용자 후속, dogfood 재개 시)

```bash
make up-isolated-build  # backend-ws-stream prefork=2 반영
docker logs quantbridge-ws-stream | grep -E "lease acquired|prefork worker ready"

# multi-account 시뮬: 2개 ExchangeAccount 등록 후 reconcile 5분 wait
# 두 lease key 모두 active 확인
docker exec quantbridge-redis redis-cli -n 3 KEYS "ws:lease:*"
```

---

## §5. 신규 BL 등록 / 변동

### Resolved

- BL-011 Redis lease + heartbeat ✅
- BL-012 prefork 복귀 + reconcile lease 기반 ✅
- BL-013 auth circuit breaker ✅
- BL-016 first_connect race ✅

### 등록

- BL-108 (P3 S 30m, codex G.2 P2 #1) — `_ws_circuit_breaker.record_network_failure` 의 INCR+EXPIRE 비원자성 → Lua wrap
- BL-109 (P3 S 1h, codex G.2 P2 #2) — `test_first_connect_timeout_calls_record_network_failure` 가 account-not-found 조기 return, 실제 path 미검증
- BL-110 (P2 S 1-2h, codex G.2 P2 #3) — prefork SIGTERM + multi-process lease integration test (mark.integration)
- BL-111 (P3 S 1-2h, codex G.2 P2 #4) — circuit breaker reset admin/CLI path

### 합계

기존 67 BL → Sprint 24a 후 **67 BL** (4 ✅ Resolved + 4 신규 등록).

---

## §6. Sprint 24b (후속 cascade) 계획

- Track 1 Backend E2E 자동 dogfood (~10h)
  - test_auto_dogfood.py 6 시나리오 (codex G.0 P1 #5 + P2 #2)
  - run_auto_dogfood.py entry script + 별도 summary HTML/JSON

---

## §7. 참조

- Sprint 24 plan v2 (Track 1+2 통합): `~/.claude/plans/claude-plans-h2-sprint-22-prompt-md-elegant-cerf.md`
- Sprint 23 dev-log: `docs/dev-log/2026-05-03-sprint23-c3-bundle.md`
- Sprint 22 dev-log: `docs/dev-log/2026-05-03-sprint22-bl091-architectural.md`
- BL 상세: `docs/REFACTORING-BACKLOG.md`
- backend.md §11 prefork-safe + LESSON-019: `.ai/stacks/fastapi/backend.md`
