# Sprint 17 — Path C Emergency: Prefork Async Engine Hardening (부분 진전 + 잔존 P1)

> 2026-05-02. Path C narrowest wedge A → 확장 (codex G.0 P1 #1 채택). 1st task success / 2nd+ task fail = **systematic-debugging Phase 4.5 architectural problem**. Sprint 18 root fix 이관.
> Plan: [`~/.claude/plans/h2-sprint-17-master.md`](~/.claude/plans/h2-sprint-17-master.md) (v2.1)
> 이전 sprint: [Sprint 16 BL-027 + BL-010](./2026-05-01-sprint16-phase0-live-and-backfill.md) (PR #87 main merge 2026-05-01)
> 브랜치: `stage/h2-sprint17` — 사용자 stage→main PR 수동

---

## 1. 배경 — Phase 0 라이브 검증 (격리 docker, 2026-05-02)

Sprint 16 머지 후 라이브 self-assessment 도출 위해 fixture-based 변형 검증 진행 (`trading.orders` 0 rows → Strategy + ExchangeAccount + stale submitted Order INSERT 후 `scan_stuck_orders` trigger).

**6h 라이브 통계 (격리 docker stack)**:

| Task                                       | 6h fail              | 6h success | 패턴                                               |
| ------------------------------------------ | -------------------- | ---------- | -------------------------------------------------- |
| `trading.scan_stuck_orders` (BL-001)       | **141 / 141 (100%)** | 0          | Sprint 15 watchdog 머지 후 한 번도 정상 동작 안 함 |
| `trading.reconcile_ws_streams` (Sprint 12) | **18 / 35 (51%)**    | 17         | 50% intermittent fail                              |
| `backtest.reclaim_stale` (control)         | 0 / 34 (0%)          | 34         | 정상 동작 (per-call engine pattern)                |

**Slack alert**: 미설정 → silent skip. **Redis throttle key**: 0건 (chain 미도달).

### Self-assessment 자동 도출 = **2/10**

- watchdog 라이브 동작 신뢰도: 0/4 (100% silent fail)
- retry/alert 정확도: 0/2 (chain 미도달)
- Pain 발견: 1/2 (이 발견 자체)
- 매일 사용 quality: 1/2

→ ≤4 = **Path C emergency** 자동 결정.

---

## 2. Root cause (systematic-debugging Phase 1+2 완료)

`funding.py:26-31` PR #51 코멘트가 정확한 reference:

> "Celery prefork worker 는 매 task 마다 asyncio.run() 으로 새 event loop 를 만든다. asyncpg connection pool 은 생성 당시 loop 에 bind 되므로 전역 engine 을 캐시하면 두 번째 task 부터 'got Future attached to a different loop' → 'another operation is in progress' 가 연쇄 실패한다."

### Pattern Diff (Phase 2)

| File                                                                                              | Pattern                                                                | 결과                 |
| ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- | -------------------- |
| `funding.py` / `stress_test_tasks.py` / `dogfood_report.py` / `backtest.py:reclaim_stale_running` | per-call `create_worker_engine_and_sm()` + finally `engine.dispose()`  | 정상 (control 34/34) |
| `orphan_scanner.py:35-48`                                                                         | module-level `_worker_engine` + `_sessionmaker_cache` lazy singleton   | **fail 141/141**     |
| `websocket_task.py:110/221`                                                                       | `from src.common.database import async_session_factory` (uvicorn 전역) | **fail 18/35**       |
| `tasks/trading.py:43-56`                                                                          | 동일 module-level singleton (잠재 fail, codex G.0 P1 #1 격상)          | 미검증 (DB 0 rows)   |

---

## 3. codex G.0 P1 발견 + 채택 (medium reasoning, iter cap 2)

### iter 1 (session `019de440-15b4-74d1-bae5-ffd4707ea74d`)

| #   | 발견                                                                               | 채택                                                                                                                         |
| --- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 1   | `trading.py` 도 동일 silent fail 패턴 — wedge 확장 (필수)                          | ✅ **사용자 재결정 후 wedge A → A+trading.py** (master plan v2.1 Phase C 옵션→필수 격상)                                     |
| 2   | mock-only verification 으로는 prefork 회귀 못 잡음 — real DB integration test 필수 | ⏭️ Phase D 신규 (defer — db_session pre-existing infra issue + 라이브 검증으로 일부 demonstrated)                            |
| 3   | `_stream_main` engine lifetime + BaseException dispose                             | ✅ Phase B test scope 확장 (+4 BaseException tests: `BybitAuthError` / `Exception` / `CancelledError` / `KeyboardInterrupt`) |

iter 2 (verify) 호출 — codex CLI resume empty 응답. iter cap 2 정신상 1차 fix 만으로 진행.

---

## 4. 변경 요약 (Phase A + B + C)

### Phase A — `orphan_scanner.py` prefork-safe (TDD)

- `_worker_engine` / `_sessionmaker_cache` / `async_session_factory()` 제거
- `create_worker_engine_and_sm()` 도입 (backtest.py:31 mirror)
- `_async_scan_stuck_orders()` 안 per-call engine + outer try/finally `engine.dispose()`
- 신규 4 tests (`tests/tasks/test_orphan_scanner_prefork_safe.py`)
- 회귀 fix: `tests/trading/test_orphan_scanner.py` 7 monkeypatch path 변경 (`async_session_factory` → `create_worker_engine_and_sm`)

### Phase B — `websocket_task.py` prefork-safe (TDD)

- `from src.common.database import async_session_factory` 제거 (uvicorn 의존 끊기)
- `create_worker_engine_and_sm()` 도입
- `_reconcile_async()` per-call engine + finally dispose
- `_stream_main()` outer try/finally engine + finally dispose (long-running stream lifetime hold + BaseException 통과)
- 신규 8 tests (`tests/tasks/test_websocket_task_prefork_safe.py`)

### Phase C — `tasks/trading.py` prefork-safe (TDD, codex G.0 P1 #1)

- `_worker_engine` / `_sessionmaker_cache` / `async_session_factory()` 제거
- `create_worker_engine_and_sm()` 도입
- `_async_execute()` 분리 → `_execute_with_session(order_id, sm)` helper + outer engine + finally dispose
- `_async_fetch_order_status()` 분리 → `_fetch_order_status_with_session(order_id, attempt, sm)` helper
- 신규 7 tests (`tests/tasks/test_trading_prefork_safe.py`)
- 회귀 fix: `tests/trading/test_celery_task.py` (5 monkeypatch + helper 함수 변경) + `tests/trading/test_fetch_order_status_task.py` (11 monkeypatch + helper)

### Phase C+ (architectural mitigation, 잔존 P1 발견 후 추가)

- `celery_app.py` `worker_max_tasks_per_child=1` 추가 (memory bloat 방어 + stale state 정리 시도)
- 효과 부분적 — 같은 child 가 3 tasks 처리 후 종료 (broker prefetch 영향 추정)

---

## 5. 자동 검증 결과

| 항목                                                                                                                                                      | 결과                                            |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| 신규 19 tests (Phase A 4 + B 8 + C 7)                                                                                                                     | ✅ **100% PASS**                                |
| `ruff check src/tasks/ tests/tasks/ tests/trading/test_celery_task.py tests/trading/test_fetch_order_status_task.py tests/trading/test_orphan_scanner.py` | ✅ All checks passed                            |
| `mypy src/tasks/`                                                                                                                                         | ✅ Success: no issues found in 9 source files   |
| 전체 회귀 (1235 tests)                                                                                                                                    | 957 passed / 4 failed / 296 errors / 18 skipped |

**4 failed + 296 errors = `asyncpg.exceptions.InvalidPasswordError` (DB 인증)** — Sprint 16 dev-log §3.3 동일 **pre-existing infra 문제** (격리 docker 의 `quantbridge` user PW + pytest fixture credential mismatch). 본 sprint 무관.

---

## 6. 라이브 재검증 (격리 docker, post-restart)

```
[16:53:52] Task scan_stuck_orders[cd7f74df-...] received
[16:53:52] Task scan_stuck_orders[cd7f74df-...] succeeded in 0.11s: {'pending': 0, 'submitted': 0, 'interrupted': 0}
[16:54:16] Task scan_stuck_orders[d39c72d2-...] received
[16:54:16] Task scan_stuck_orders[d39c72d2-...] raised unexpected: RuntimeError("attached to a different loop")
[16:54:51] Task scan_stuck_orders[d7e2b0a7-...] raised unexpected: InterfaceError("another operation is in progress")
[16:54:17] Task reconcile_ws_streams[2e9bba74-...] succeeded in 0.04s: {'enqueued': [], 'skipped_active': [], 'total': 0}
```

post-restart `worker_max_tasks_per_child=1` 적용 후 동일 패턴:

```
[16:57:28] Task scan_stuck_orders[bec744e5-...] succeeded in 0.08s
[16:57:29] Task scan_stuck_orders[eb2f1a0b-...] raised unexpected: RuntimeError("attached to a different loop")
[16:57:30] Task scan_stuck_orders[cc28a1eb-...] raised unexpected: InterfaceError("another operation is in progress")
```

### 결론: **부분적 success (1st task / child OK) + 잔존 P1 (2nd+ task fail)**

- Phase 0: **100% silent fail (141/141)** → Sprint 17 후: **~33% success (1/3)**
- 첫 task per-call engine fix 효과 → success
- 같은 child 의 두 번째 task 부터 SQLAlchemy/asyncpg dialect cache + Redis lock pool / 기타 module-level state 가 stale loop 의 Future 보유 → fail
- `worker_max_tasks_per_child=1` 효과 약함 (broker prefetch + 같은 child 가 max 도달 전 multi-task)

---

## 7. systematic-debugging Phase 4.5 — Architectural Problem

3+ fixes 시도 후 새 위치에서 fail 재발 = pattern 자체 재고. 근본 해결책 후보 (Sprint 18 root fix):

| 옵션                                                                   | 설명                                                           | risk                         | est   |
| ---------------------------------------------------------------------- | -------------------------------------------------------------- | ---------------------------- | ----- |
| **A. Celery solo pool** (각 task type 별 dedicated worker)             | scan/reconcile/trading 각각 `--pool=solo`                      | 운영 복잡도 ↑                | 4-6h  |
| **B. 매 task fork-fresh interpreter**                                  | `worker_pool=prefork` + worker_init hook 으로 module reset     | invasive, fragile            | 1~2일 |
| **C. asyncpg/SQLAlchemy connection state reset**                       | `_get_redis_lock_pool_for_alert` + dialect cache 매 task reset | hot path 매번 reset overhead | 1일   |
| **D. backtest.reclaim_stale 이 어떻게 6h 정상이었는지 정밀 비교 분석** | git blame + run-time profiling                                 | unknown                      | 4-8h  |

→ Sprint 18 으로 이관. 본 sprint 결과는 BL-XXX 로 등록 (잔존 P1).

---

## 8. Self-assessment (post-Sprint 17)

| 평가 항목                   | 가중치 | Phase 0  | Sprint 17 후                                  |
| --------------------------- | ------ | -------- | --------------------------------------------- |
| watchdog 라이브 동작 신뢰도 | 4      | 0/4      | 2/4 (1st task success, 2nd+ fail)             |
| retry/alert 정확도          | 2      | 0/2      | 0/2 (chain 여전히 미도달)                     |
| Pain 발견                   | 2      | 1/2      | 2/2 (architectural P1 명확화)                 |
| 매일 사용 quality           | 2      | 1/2      | 1/2 (변화 없음 — 5분 cycle 시 첫 task 성공만) |
| **합계**                    | **10** | **2/10** | **5/10**                                      |

**진전 +3** (2 → 5). H1→H2 gate (≥7) 미통과. Sprint 18 root architectural fix 후 재평가.

---

## 9. Sprint 18 이관 (잔존 BL)

| ID                | 제목                                                                                                    | trigger                              | est    |
| ----------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------ | ------ |
| **BL-080 (신규)** | scan/reconcile/trading prefork-safe **architectural** fix (asyncpg/SQLAlchemy module-level state reset) | self-assessment 5 → ≥7               | 1~2일  |
| BL-005            | 본인 1~2주 dogfood (live broker)                                                                        | self-assessment ≥7                   | 1~2주  |
| BL-070~072        | Beta 오픈 번들                                                                                          | self-assessment ≥7                   | 12~20h |
| Phase D defer     | real asyncpg integration test (`asyncio.run() 2회 연속`)                                                | db_session pre-existing infra fix 후 | S      |
| codex G.0 iter 2  | resume session empty response 재현 시 archived                                                          | -                                    | -      |

---

## 10. 머지 권장

**자동 검증 + 19 신규 tests + 라이브 1st-task 검증 통과 + 잔존 P1 명시** = 부분 진전 머지 권장.

- ✅ Phase A+B+C 19 tests 100% PASS
- ✅ ruff 0 / mypy 0 (src/tasks)
- ✅ 라이브 1st-task succeeded (Phase 0: 0/141 → 1+/cycle)
- ⚠️ 2nd+ task fail = **잔존 P1 critical** — Sprint 18 root architectural fix 의무
- ⚠️ self-assessment 5/10 — H1→H2 gate (≥7) 미통과

**라이브 운영 영향**: Phase 0 의 100% silent fail 보다 개선. 5분 cycle 의 매 firing 이 child rotation + 1st task 성공 가능 (실측 필요). 일부 watchdog 미동작 가능성 있어 Sprint 18 root fix 까지 manual cleanup script (BL-028) 병행.

---

## 11. CI hotfix (2026-05-02 post-push)

첫 commit `f236b8f` push 후 GitHub Actions CI fail.

```
FAILED tests/trading/test_celery_task_futures.py::test_async_execute_uses_bybit_futures_provider_with_leverage
FAILED tests/trading/test_e2e_webhook_to_futures_order.py::test_e2e_manual_futures_order_propagates_leverage_through_ccxt
AttributeError: <module 'src.tasks.trading'> has no attribute 'async_session_factory'
```

**Root cause**: 첫 grep 시 `monkeypatch.*async_session_factory` 패턴 검색에서 2 파일은 `setattr.*async_session_factory` 형태로 작성되어 잡히지 않음. **5 files (test_celery_task / test_fetch_order_status_task / test_celery_task_futures / test_e2e_webhook_to_futures_order / test_orphan_scanner) 모두 수정 필요**였는데 3개만 처리.

**Hotfix `bd61c08`**: 누락된 2 파일 monkeypatch path 변경 (helper `_make_fake_session_factory` → `_make_fake_create_worker_engine_and_sm`, attr `async_session_factory` → `create_worker_engine_and_sm`). 2 files / +34 / -9.

**Lesson (LESSON-020 후보)**: monkeypatch path 변경 시 `grep -rn '"<old_attr>"'` (attribute 이름 자체) 로 1차 검색 후, helper 함수 정의 ref 도 별도 grep. PR 머지 전 CI 단계 fail 으로 발견 = 정상 동작.

---

## 12. 다음 세션 prompt

`~/.claude/plans/h2-sprint-18-prompt.md` — Sprint 18 = BL-080 architectural fix Path 명시.
