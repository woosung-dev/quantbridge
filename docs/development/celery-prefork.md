# Celery prefork-safe 패턴 (Sprint 18 [BL-080])

> 규칙 요지는 `apps/api/AGENTS.md` §9 이 갖는다(자동 로드). 이 문서는 **배선 상세와 allowlist 절차**다.
> 2026-08-23 분리 — 자동 로드되는 파일에서 119줄을 덜어냈다.

> Sprint 17 → Sprint 18 architectural 진화. `asyncio.run()` per task 패턴이 module-level async state 와 함께 쓰이면 **2nd+ task 부터 `RuntimeError("Future ... attached to a different loop")` / `InterfaceError("another operation is in progress")` 로 silent fail**. asyncpg 의 `BaseProtocol._on_waiter_completed` callback 이 1st task asyncio.run() loop 에 stale bound. Option C (영속 worker loop) 로 root fix.

## 의무 — `_WORKER_LOOP` 통일

**모든 Celery task entry point** 는 `asyncio.run(coro)` 대신 `run_in_worker_loop(coro)` 사용.

```python
# apps/api/src/tasks/<task_module>.py
@shared_task(name="domain.task_name")
def task_entry(payload: str) -> dict:
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_impl(payload))
```

**예외 (master process 만)**:

- `celery_app.py:_on_worker_ready` — `@worker_ready.connect` 는 master process 에서 1회 실행. `_WORKER_LOOP` 비대상 → `asyncio.run()` 그대로.

**worker_process_init / worker_process_shutdown signal**:

```python
@worker_process_init.connect
def _init(...):
    init_worker_loop()         # 영속 loop 생성
    reset_redis_lock_pool()    # fork stale FD 폐기

@worker_process_shutdown.connect
def _shutdown(...):
    shutdown_worker_loop()     # pending cancel + asyncgens drain + close
```

## 의무 — Module-level async state 검증

`asyncio.Semaphore` / `Lock` / `Event` / `Queue` 를 module-level 에 두는 것 자체는 OK 이지만 (영속 loop 통일로 stale 안 됨), **새 module-level async object 추가 시 PR 리뷰 의무**:

1. 해당 객체가 worker child fork 후 `_WORKER_LOOP` 안에서만 acquire/await 되는가?
2. `worker_process_init` 의 reset hook 필요한가? (Redis pool 처럼 fork 시 FD 공유 회피)
3. `_WORKER_LOOP` 미초기화 환경 (uvicorn FastAPI / pytest unit) 에서 안전한가?

**자동 audit gate**: `tests/tasks/test_no_module_level_loop_bound_state.py` (Sprint 19 BL-084) 가 `src/tasks/*.py` + `src/common/alert.py` + `src/common/redis_client.py` + **`src/trading/services/*.py`**([BL-203] Sprint 48) 의 module-level `Assign + AnnAssign` 노드에서 `asyncio.<Semaphore|Lock|Event|Queue|Condition|...>(...)` 호출 검출. import alias (`from asyncio import Semaphore as S`) 도 catch.

**Allowlist 갱신 절차**:

1. `tests/tasks/test_no_module_level_loop_bound_state.py` 의 `_ALLOWLIST` 상수에 `(module, name)` 튜플 추가 (현재 `("src.common.alert", "_SEND_SEMAPHORE")` 1개).
2. 본 §9.2 에 안전 사유 1-2줄 명시 (왜 영속 `_WORKER_LOOP` 통일 가정 하에 안전한지).
3. PR 리뷰에서 (1)+(2) 동시 변경 검증.
4. 미준수 시 audit `test_allowlisted_modules_have_documented_violations` 가 stale allowlist 검출.

**현재 allowlist (1개)**:

- `src.common.alert._SEND_SEMAPHORE` — Slack send burst 상한 `asyncio.Semaphore(8)`. Sprint 18 `_WORKER_LOOP` 통일로 모든 acquire 가 동일 loop. Sprint 19 BL-081 `track_pending_alert` helper 가 cross-task semantic 명시화.

## 의무 — Per-call engine + dispose

Option C 가 loop 통일하더라도 **engine 수명은 task 단위로 유지**:

```python
async def _async_impl():
    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            ...
    finally:
        await engine.dispose()
```

이유: connection pool stale connection 누수 방어 (loop binding 과 별개). `apps/api/src/tasks/backtest.py:31-91` 가 표준 reference.

## 금지 — nested `run_in_worker_loop`

`run_in_worker_loop` 는 이미 실행 중인 loop 안에서 호출 시 `RuntimeError` raise (silent fallback 금지). pytest-asyncio / celery_eager 환경에서 호출자가 직접 coroutine 을 await 해야 함.

## 라이브 검증 의무

새 Celery task 추가 시:

1. 동일 child 의 N 번째 task 도 success 인지 라이브 검증 (즉시 3회 + 5분 cycle 30분 자동)
2. ws_stream 같은 long-running 은 별도 queue (`task_routes`) 로 분리 — pool 은 prefork 고정 (Sprint 12 solo → Sprint 24 BL-012 prefork 복귀, `docker-compose.yml` 이 정본)
3. Sprint 19 BL-082 1h soak gate 통과 (RSS slope < 임계, fd 누수 없음)

## 백포트 — `AsynPool.flush()` (Celery 5.6.x · [BL-870] ⑵)

broker 연결이 끊기면 5.6.3 의 `AsynPool.flush()` 가 `_busy_workers` 를 통째로 비운다. 그러면 끝나지 않는
태스크(ws-stream)를 돌리는 자식도 「한가함」이 되고, 재연결 뒤 새 태스크가 그 자식의 파이프에 들어가
`reserved` 에 영원히 머문다. `src/tasks/_celery_backports.py` 가 상류 수정(celery/celery#10346)과 같은 규칙으로
「살아 있고 수락된 job 을 돌리는 자식」을 바쁨으로 되돌리고, `celery_app.py` 가 import 시점에 건다.

- ★**Celery ≥5.7 로 올리면 백포트는 스스로 꺼진다** — 그때 모듈과 호출 한 줄을 지워라. 카나리
  `tests/tasks/test_celery_backports.py::test_installed_celery_flush_still_clears_busy_workers` 가 그 시점을 알린다
- 실프로세스 재현 = `apps/api/scripts/repro_bl870_broker_reconnect.py` — **전용 docker 네트워크 + 일회용 redis** 위에서
  운영 이미지로 워커를 띄운다. 공유 스택의 worker 를 쓰지 않으므로 워크트리 금지 규칙(메인 `src` mount)에 걸리지 않는다

## Alert task pending observability

영속 `_WORKER_LOOP` 채택으로 fire-and-forget alert task (e.g. `KillSwitchService` 의 Slack 발송 task) 가 **Celery task 경계를 넘어 살아남을 수 있음** — 이전 `asyncio.run()` 패턴은 task 종료 시 모든 pending task 자동 cancel. cross-task semantic 변화 → 운영 모니터링 의무.

**의무 규약**:

1. fire-and-forget alert task 는 `track_pending_alert(task)` helper 사용. `_PENDING_ALERTS.add(task)` 직접 호출 금지.
2. `track_pending_alert` 가 `qb_pending_alerts` Prometheus Gauge inc + idempotent `add_done_callback` (set membership 검사로 외부 drain + done callback 중복 dec underflow 방지).
3. 표준 reference: `apps/api/src/common/alert.py:track_pending_alert` + `apps/api/src/trading/kill_switch.py:225` (migration 패턴).
4. 운영 임계값: `qb_pending_alerts > 50` 시 Slack/Grafana alert 권장 (Sprint 20+ BL-089 wire-up).

**예시 패턴**:

```python
# apps/api/src/<domain>/<service>.py
import asyncio
from src.common.alert import send_critical_alert, track_pending_alert

class MyService:
    async def trigger_alert(self, ...):
        # 직접 add 금지 — track_pending_alert helper 사용
        task = asyncio.create_task(self._send_alert(...))
        track_pending_alert(task)
        # 호출자는 task 결과 await 안 함 (fire-and-forget). gauge 가 in-flight 모니터링.
```

**금지 패턴** (Sprint 19 BL-081 migration 후):

```python
# 직접 _PENDING_ALERTS 조작 — gauge 동기화 누락
_PENDING_ALERTS.add(task)
task.add_done_callback(_PENDING_ALERTS.discard)
```

---

