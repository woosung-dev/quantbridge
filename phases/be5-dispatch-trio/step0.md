# Step 0: dispatch-trio

## 읽어야 할 파일

- `apps/api/src/tasks/backtest.py` (40 stmt) — **대상 ①**
- `apps/api/src/backtest/dispatcher.py` · `src/optimizer/dispatcher.py` · `src/stress_test/dispatcher.py` — **대상 ②③④**
- `apps/api/tests/tasks/test_backtest_task.py` — 기존 커버 범위 확인용(**수정 금지**)
- `apps/api/tests/tasks/test_funding_task.py` — ★**엔진 수명 관용구 정본**(`_RecordingEngine` + `create_worker_engine_and_sm` mock)
- `apps/api/AGENTS.md` §9.1 / §9.3 — `run_in_worker_loop` 통일 · per-call engine + dispose

## 배경

★★**착수 전 CONTROL 이 전량 스위트 커버리지로 쟀다 (2026-08-21 · `concurrency=greenlet,thread` 교정본):**

```
src/tasks/backtest.py            40 stmt   14 missed   65%   28-34, 39-47, 57-59
src/backtest/dispatcher.py       20 stmt    3 missed   85%   25-28
src/optimizer/dispatcher.py      20 stmt    4 missed   80%   26-29, 36
src/stress_test/dispatcher.py    20 stmt    4 missed   80%   25-28, 35
```

★★**dispatcher 3종에서 미커버인 것이 정확히 두 종류다:**

1. **`Celery*Dispatcher.dispatch_*` 본문** — `run_*_task.delay(str(id))` → `str(async_result.id)` 반환
2. ★★★**`Noop*Dispatcher.dispatch_*` 의 `raise RuntimeError`** (optimizer 36 · stress_test 35)

⑵ 가 이 lane 의 핵심이다. Noop 은 **worker 경로에 주입되는 방어벽**이다 — worker 가 자기 자신을 다시
enqueue 하는 것을 막는다. **지금 그 `raise` 를 `return ""` 으로 바꿔도 스위트는 초록이다.**

★그리고 `src/tasks/backtest.py` 에는 **다른 둘에 없는 축**이 있다:

> `run_backtest_task` 의 docstring — 「성공/실패 무관하게 **finally 에서 1회 observe**」
> (`qb_backtest_duration_seconds.observe(time.monotonic() - started)`)

**그 `finally` 도 미커버다**(28-34).

★**착수 전 CONTROL 실측 — 구조 (네 모듈을 직접 읽어 확인했다):**

| 축                           | 관측                                                                                                                                                                                           |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `run_backtest_task`          | `name="backtest.run"` · `bind=True` · `max_retries=0`. `started = time.monotonic()` → `try: run_in_worker_loop(_execute(UUID(id)))` → **`finally: qb_backtest_duration_seconds.observe(...)`** |
| `_execute`                   | `create_worker_engine_and_sm()` → `async with sm()` → `build_backtest_service_for_worker(session)` → `service.run(id)` → **`finally: await engine.dispose()`**                                 |
| `reclaim_stale_running_task` | `name="backtest.reclaim_stale"` · `run_in_worker_loop(reclaim_stale_running())` 의 반환을 그대로                                                                                               |
| `Celery*Dispatcher`          | 지연 import 한 task 의 **`.delay(str(id))`** → `str(async_result.id)` 반환 (세 도메인 각각)                                                                                                    |
| `Noop*Dispatcher`            | **`raise RuntimeError("Noop… must not dispatch")`** — 메시지는 **파일에서 확인해라**                                                                                                           |
| `Fake*Dispatcher`            | `dispatched` 리스트에 append + 고정 `task_id` 반환 (테스트 전용 — 이미 쓰이고 있을 수 있다)                                                                                                    |

★**메서드 이름이 도메인마다 다르다** — `dispatch_backtest` / `dispatch_optimization` / `dispatch_stress_test`.
**각 파일에서 확인해라**(여기 셋을 다 적지 않은 이유는 backtest 쪽을 재지 않았기 때문이다).

## 작업

`apps/api/tests/tasks/test_dispatch_contracts.py` **하나**를 신설한다.
`.delay` 와 `create_worker_engine_and_sm` · `run_in_worker_loop` 을 mock 한다.
**진짜 celery broker 를 치지 마라. DB 를 치지 마라.**

### 최소한 이 여덟을 덮어라 (케이스 ≥8)

1. ★★★**`Noop*Dispatcher` 3종이 전부 `RuntimeError` 를 던진다** — 세 도메인 각각.
   ★**메시지에 그 클래스 이름이 실려 있는지**도 재라(세 개가 서로 구별되는지 = 복붙 실수를 잡는다)
2. ★★**`Celery*Dispatcher` 3종이 `.delay` 를 부르고 task id 를 문자열로 반환한다** — 세 도메인 각각.
   ★**`.delay` 에 넘어간 인자가 `str(uuid)` 인지**(UUID 객체가 아니라) 재라 — celery 직렬화 계약이다
3. ★**반환값이 `str` 이다** — `async_result.id` 가 문자열이 아닌 타입이어도 `str()` 로 감싸지는지 재라
4. ★★**`Celery*Dispatcher` 가 부르는 태스크가 그 도메인의 것이다** — backtest dispatcher 가
   `run_backtest_task` 를, optimizer 가 `run_optimization_task` 를, stress_test 가 그 짝을 부른다.
   ★**서로 뒤바뀌는 변이를 잡는 것이 목적이다**
5. ★★★**`run_backtest_task` 가 예외에도 히스토그램을 1회 observe 한다** — `run_in_worker_loop` 을
   예외로 두고, 예외가 밖으로 나가면서도 `observe` 가 **정확히 1회** 불린다.
   ★**이것이 `finally` 를 재는 유일한 케이스다** — 정상 경로만 있으면 `finally` 를 지워도 초록이다
6. ★**정상 경로에서도 observe 가 1회** — ⑸의 짝. ★관측된 값이 **음수가 아닌 float** 인지 재라
7. ★★**`_execute` 정상·예외 두 경로에서 `engine.dispose()` 가 1회씩** — `_RecordingEngine` 관용구.
   ★서비스 빌더가 받은 것이 `sm()` 이 연 **그 session** 인지도 재라
8. ★**`reclaim_stale_running_task` 가 `run_in_worker_loop` 의 반환값을 그대로 돌려준다** +
   `run_in_worker_loop` 이 1회 불린다(`asyncio.run` 이 아니라 — §9.1 의무)
9. ★**태스크 등록 이름 2종** — `backtest.run` · `backtest.reclaim_stale` + `max_retries=0`.
   beat 스케줄이 이름으로 찾으므로 이름이 바뀌면 조용히 안 돈다
10. (선택) **`Fake*Dispatcher` 3종이 `dispatched` 에 기록하고 고정 id 를 반환한다** —
    기존 테스트들이 이것을 쓰고 있을 수 있다. **먼저 grep 해서 겹치면 `summary` 에 적고 건너뛰어라**

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/tasks/test_dispatch_contracts.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/tasks/test_dispatch_contracts.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 8
cd apps/api && uv run --env-file .env.local pytest tests/tasks/test_backtest_task.py tests/tasks/test_beat_schedule.py -q
cd apps/api && uv run ruff check tests/tasks/test_dispatch_contracts.py && uv run ruff format --check tests/tasks/test_dispatch_contracts.py
```

★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 **rc=4**(CONTROL 실측 2026-08-21).
★`--env-file .env.local` 을 빼지 마라 — DB 가드가 rc=3 으로 거부한다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **⑽에서 확인한 `Fake*Dispatcher` 기존 사용처**를 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**`src/tasks/backtest.py` 와 dispatcher 3종을 수정하지 마라.** 이유: 이 회차의 계약은 「테스트만
  추가하고 대상 소스는 0줄 변경」이다. 결함을 발견하면 **고치지 말고 `status:"blocked"` +
  `blocked_reason`** 으로 멈춰라
- ★★**`src/optimizer/dependencies.py` · `src/stress_test/dependencies.py` · `src/backtest/dependencies.py` ·
  `src/market_data/dependencies.py` 를 겨누지 마라** — **다른 lane(`be5-di-assembly`)이 그 넷을 겨눈다.**
  「어느 dispatcher 가 주입되는가」는 그쪽 소관이고, 이 lane 은 **dispatcher 자신의 동작**만 잰다
- ★★**`src/tasks/optimizer_tasks.py` · `src/tasks/stress_test_tasks.py` 를 겨누지 마라** —
  **다른 lane(`be5-worker-tasks`)이 그 둘을 겨눈다.** 이 lane 이 그 태스크를 건드리는 것은
  ⑷에서 **`.delay` 가 어느 것을 부르는지 확인할 때뿐**이다
- ★★**진짜 celery broker·worker 를 쓰지 마라.** 이유: 워크트리에서 celery 경유 검증은 worker 가
  **메인 체크아웃의 소스를 mount** 하므로 내 코드가 아니라 메인 코드가 돈다(침묵 실패)
- ★★**`xfail(strict=True)` 를 쓰지 마라. 이유:** 「제품 코드가 지금 틀렸다」를 원장에 박는 주장인데
  **AC·변이·사람 diff 세 층이 전부 통과시킨다**([LESSON-121]). 근거는 `summary` 에 적고 테스트는 지금 동작을 고정해라
- ★**클래스 정의 모듈을 monkeypatch 한 뒤 소비 모듈을 처음 import 하지 마라.** 이유: 루트 conftest 의
  **BL-583 전역 오염 가드**가 teardown 에서 `pytest.fail` 을 낸다. 해법은 `tests/conftest.py:239` 의 **선-import**
- ★**재지 않은 값을 단언하지 마라.** 이유: step 의 산문은 세션에게 AC 와 구별되지 않는다([LESSON-122]).
  dispatcher 메서드 이름과 `RuntimeError` 메시지는 **각 파일을 열어 확인**하고 써라
- ★**`conftest.py` · `pyproject.toml` · `shards.json` 무변경**(8 lane 동시 실행 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — fake `AsyncResult`/엔진은 이 테스트 파일 안에 둬라
- **새 pytest 마커를 쓰지 마라** — `--strict-markers` 라 `pyproject.toml` 을 함께 고쳐야 하고 그것이 공유 파일이다
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
