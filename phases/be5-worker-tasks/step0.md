# Step 0: worker-tasks

## 읽어야 할 파일

- `apps/api/src/tasks/optimizer_tasks.py` (80줄) — **이번 테스트의 대상 ①**
- `apps/api/src/tasks/stress_test_tasks.py` (72줄) — **이번 테스트의 대상 ②**
- `apps/api/tests/tasks/test_funding_task.py` — ★★**이 lane 의 관용구 정본이다.**
  `_RecordingEngine`(dispose 횟수 기록) + `create_worker_engine_and_sm` mock + 정상/예외 두 경로.
  **같은 모양으로 써라** — 파일을 열어 보고 베껴라(여기 복사해 오지 않은 이유는 낡은 사본이 되기 때문이다)
- `apps/api/tests/tasks/test_orphan_scanner_prefork_safe.py` — 같은 관용구의 두 번째 선례
- `apps/api/src/tasks/_worker_engine.py` — `create_worker_engine_and_sm`
- `apps/api/AGENTS.md` §9.1 / §9.3 — Celery prefork-safe 규칙(`run_in_worker_loop` 통일 · per-call engine + dispose)

## 배경

★★**착수 전 CONTROL 이 전량 스위트 커버리지로 쟀다 (2026-08-21 · `concurrency=greenlet,thread` 교정본):**

```
src/tasks/optimizer_tasks.py      34 stmt   22 missed   35%   35-37, 43-51, 57-59, 64-80
src/tasks/stress_test_tasks.py    34 stmt   22 missed   35%   27-29, 35-43, 49-51, 56-72
```

**두 모듈 다 함수 본문이 통째로 미커버다** — 커버된 35% 는 import 와 데코레이터뿐이다.
`optimizer.run` · `stress_test.run` 은 사용자가 최적화/스트레스 테스트를 돌릴 때마다 도는 경로이고,
`*.reclaim_stale` 은 **Celery Beat 가 주기적으로** 부른다.

★**AGENTS.md §9.3 이 의무로 못박은 계약이 여기서 무증거다:**

> Option C 가 loop 통일하더라도 **engine 수명은 task 단위로 유지** — `finally: await engine.dispose()`.
> 이유: connection pool stale connection 누수 방어.

**지금 네 함수의 `finally` 를 전부 지워도 스위트는 초록이다.** 그것이 이 lane 의 산출이다.

★**착수 전 CONTROL 실측 — 구조 (두 모듈을 직접 읽어 확인했다. 둘은 거의 완전한 mirror 다):**

| 축                      | `optimizer_tasks`                                                                                                                                                          | `stress_test_tasks`                                                          |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 실행 태스크             | `run_optimization_task(self, run_id: str)` · `name="optimizer.run"`                                                                                                        | `run_stress_test_task(self, stress_test_id: str)` · `name="stress_test.run"` |
| 실행 본문               | `run_in_worker_loop(_execute(UUID(run_id)))`                                                                                                                               | `run_in_worker_loop(_execute(UUID(stress_test_id)))`                         |
| `_execute`              | `create_worker_engine_and_sm()` → `async with sm()` → `build_optimizer_service_for_worker(session)` → `service.run(id)` → **`finally: await engine.dispose()`**            | 같은 모양 · `build_stress_test_service_for_worker`                           |
| reclaim 태스크          | `reclaim_stale_running_task()` · `name="optimizer.reclaim_stale"`                                                                                                          | `reclaim_stale_running_task()` · `name="stress_test.reclaim_stale"`          |
| `reclaim_stale_running` | `OptimizationRepository(session).reclaim_stale(threshold_seconds=settings.optimizer_stale_threshold_seconds, now=...)` → `repo.commit()` → 반환 → **`finally: dispose()`** | `StressTestRepository` · `settings.stress_test_stale_threshold_seconds`      |
| 데코레이터 메타         | `bind=True` · `max_retries=0` · **`soft_time_limit=600` · `time_limit=660`**([BL-237])                                                                                     | `bind=True` · `max_retries=0` (**시간 상한 없음**)                           |

★**`run_in_worker_loop` 과 서비스 빌더는 함수 본문 안에서 지연 import 된다** — mock 위치를 그에 맞춰 잡아라.
★**`async def _execute` / `reclaim_stale_running` 를 직접 `await` 하는 것이 가장 얇은 경로다**
(`test_funding_task.py` 가 `_async_fetch` 를 그렇게 직접 부른다).

## 작업

`apps/api/tests/tasks/test_worker_task_lifecycle.py` **하나**를 신설한다(두 모듈을 같은 파일에서 다룬다 —
둘이 mirror 라 한 자리에서 대조하는 것이 계약을 더 잘 고정한다). **DB 를 치지 마라. celery worker 를 띄우지 마라.**

### 최소한 이 열을 덮어라 (케이스 ≥10)

1. ★★**`_execute` 정상 경로에서 `engine.dispose()` 가 정확히 1회 await 된다** — 두 모듈 **각각**.
   `_RecordingEngine` 관용구를 써라
2. ★★**서비스가 던져도 `dispose()` 가 된다** — `service.run` 을 `side_effect` 예외로 두고,
   예외가 밖으로 나가면서도 `dispose_calls == 1` 이다. 두 모듈 **각각**.
   ★**이것이 `finally` 를 재는 유일한 케이스다** — ⑴만 있으면 `finally` 를 `else` 로 바꿔도 초록이다
3. ★★**`_execute` 가 서비스에 넘기는 인자가 `UUID` 이고 받은 값과 같다** — 서비스 빌더가 받은 것이
   `sm()` 이 연 **그 session** 인지도 함께 재라(빌더에 다른 것을 넘기는 변이를 잡는다)
4. ★**`create_worker_engine_and_sm` 이 호출마다 1회** — 두 번 연속 호출하면 **2회**다
   (module-level 캐시가 되살아나면 여기서 잡힌다)
5. ★★**`reclaim_stale_running` 이 repo 의 반환값을 그대로 돌려준다** + **`repo.commit()` 이 await 된다**.
   ★**commit 없이 반환하는 변이를 잡는 것이 목적이다** — 두 모듈 각각
6. ★★**`reclaim_stale_running` 이 `threshold_seconds` 로 넘기는 값이 그 모듈의 settings 키다** —
   `optimizer_stale_threshold_seconds` vs `stress_test_stale_threshold_seconds`.
   ★**두 모듈이 서로의 키를 쓰는 변이를 잡는다** — 두 값을 **서로 다르게** 놓고 재라
7. ★**`now` 가 tz-aware(UTC) 다** — 하드코딩하지 말고 호출 전후로 경계를 잡아 그 사이인지 재라
8. ★★**reclaim 경로도 예외 시 `dispose()` 가 된다** — `repo.reclaim_stale` 을 예외로 두고 재라
9. ★**sync wrapper 가 `run_in_worker_loop` 에 코루틴을 넘긴다** — `run_optimization_task` /
   `run_stress_test_task` / 두 `reclaim_stale_running_task` 를 부르고, mock 한 `run_in_worker_loop` 이
   **1회** 불렸는지 + reclaim wrapper 는 그 **반환값을 그대로 돌려주는지** 재라.
   ★`asyncio.run` 이 아니라 `run_in_worker_loop` 인지도 재라(§9.1 의무)
10. ★★**태스크 등록 이름 4종과 데코레이터 메타** — `optimizer.run`·`optimizer.reclaim_stale`·
    `stress_test.run`·`stress_test.reclaim_stale` + `max_retries=0` +
    **`optimizer.run` 만 `soft_time_limit=600`/`time_limit=660`**([BL-237]).
    beat 스케줄이 이름으로 찾으므로 이름이 바뀌면 조용히 안 돈다
11. (선택) **잘못된 UUID 문자열**을 sync wrapper 에 주면 무엇이 일어나는지 **관측해서 박아라**
    (엔진 생성 전인지 후인지 포함 — 예상과 다르면 `summary` 에 적어라)

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/tasks/test_worker_task_lifecycle.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/tasks/test_worker_task_lifecycle.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 10
cd apps/api && uv run --env-file .env.local pytest tests/tasks -q
cd apps/api && uv run ruff check tests/tasks/test_worker_task_lifecycle.py && uv run ruff format --check tests/tasks/test_worker_task_lifecycle.py
```

★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 **rc=4**(CONTROL 실측 2026-08-21).
★`--env-file .env.local` 을 빼지 마라 — DB 가드가 rc=3 으로 거부한다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **⑾에서 관측한 잘못된 UUID 의 실제 동작**을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**`src/tasks/optimizer_tasks.py` · `src/tasks/stress_test_tasks.py` 를 수정하지 마라.** 이유: 이 회차의
  계약은 「테스트만 추가하고 대상 소스는 0줄 변경」이다. 결함(예: 예외 경로 엔진 누수)을 발견하면
  **고치지 말고 `status:"blocked"` + `blocked_reason`** 으로 멈춰라
- ★★**진짜 DB·진짜 celery worker 를 쓰지 마라.** 이유: 워크트리에서 celery 경유 검증은 worker 가
  **메인 체크아웃의 소스를 mount** 하므로 내 코드가 아니라 메인 코드가 돈다(침묵 실패).
  `create_worker_engine_and_sm` · `run_in_worker_loop` · 서비스 빌더 · repository 를 mock 해서 **함수만** 재라
- ★★**`xfail(strict=True)` 를 쓰지 마라. 이유:** 「제품 코드가 지금 틀렸다」를 원장에 박는 주장인데
  **AC·변이·사람 diff 세 층이 전부 통과시킨다**([LESSON-121]). 근거는 `summary` 에 적고 테스트는 지금 동작을 고정해라
- ★**클래스 정의 모듈을 monkeypatch 한 뒤 소비 모듈을 처음 import 하지 마라.** 이유: 루트 conftest 의
  **BL-583 전역 오염 가드**가 teardown 에서 `pytest.fail` 을 낸다. 해법은 `tests/conftest.py:239` 가
  적어 둔 **선-import**(`from src.tasks import optimizer_tasks as _preload  # noqa: F401`)다
- ★**`celery_app.py` · beat 스케줄을 수정하지 마라** — `test_beat_schedule.py` 가 이미 있고 이 lane 소유가 아니다
- ★**`conftest.py` · `pyproject.toml` · `shards.json` 무변경**(8 lane 동시 실행 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — `_RecordingEngine` 같은 것은 이 테스트 파일 안에 둬라
  (선례 파일에서 **베껴 오되 import 하지 마라**)
- **새 pytest 마커를 쓰지 마라** — `--strict-markers` 라 `pyproject.toml` 을 함께 고쳐야 하고 그것이 공유 파일이다
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
