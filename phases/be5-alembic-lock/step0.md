# Step 0: alembic-lock

## 읽어야 할 파일

- `apps/api/src/scripts/run_alembic_with_lock.py` (162줄) — **이번 테스트의 대상**
- `apps/api/tests/tasks/test_funding_task.py` — ★**mock 관용구 정본.** 로컬 fake 클래스 + `monkeypatch.setattr`
  로 외부 경계를 끊는 모양. **같은 모양으로 써라** — 파일을 열어 보고 베껴라(복사해 오지 않은 이유는 낡은 사본이 되기 때문이다)
- `apps/api/tests/scripts/` — 이 디렉터리의 다른 파일들(셸 스크립트 대상). 이 lane 은 **python 모듈**이 대상이라 모양이 다르다

## 배경

★★**착수 전 CONTROL 이 전량 스위트 커버리지로 쟀다 (2026-08-21 · `concurrency=greenlet,thread` 교정본):**

```
src/scripts/run_alembic_with_lock.py     64 stmt     64 missed     0%     26-162
```

**이 모듈은 실행문 64개가 전부 미커버다.** `apps/api/tests/scripts/test_soak_stack_migrate.py` 에
`"src.scripts.run_alembic_with_lock"` 문자열이 5번 나오지만 그것은 **셸 스크립트가 그 명령줄을 만드는지**만
보는 것이고 **이 모듈을 import 하지 않는다.** 이름만 맞는 파일이다.

이 모듈은 `apps/api/docker-entrypoint.sh` 가 부르는 **운영 entrypoint** 다 — 다중 인스턴스 cold start 에서
동시 migration race 를 advisory lock 으로 막는다. 그것이 조용히 깨지면 **두 인스턴스가 동시에 migration 을 돌린다.**

★**착수 전 CONTROL 실측 — 구조 (모듈을 직접 읽어 확인했다):**

| 심볼                         | 무엇을 하나                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------------- |
| `_normalize_url_for_asyncpg` | `postgresql+asyncpg://` → `postgresql://` 치환. **`.replace(..., 1)` 이라 첫 것만**               |
| `_acquire_advisory_lock`     | `asyncpg.connect` → `SELECT pg_try_advisory_lock($1::bigint)` 재시도 루프. 예외 시 `conn.close()` |
| `_run_alembic_upgrade_head`  | `asyncio.create_subprocess_exec("uv","run","alembic","upgrade","head")` → `proc.wait()` 반환      |
| `run(lock_key, timeout_s)`   | `settings.database_url` falsy → `RuntimeError` / lock 획득 → upgrade / `finally` 에서 conn.close  |
| `_parse_args`                | `--lock-key` 기본 `1903723824` · `--timeout` 기본 `30`                                            |
| `main(argv)`                 | `RuntimeError` → **rc 2**. 그 외는 subprocess rc 를 그대로 반환                                   |

★**`import asyncpg as _asyncpg` 는 `_acquire_advisory_lock` 안에서 지연 import 된다** — mock 위치를 그에 맞춰 잡아라.
★**`asyncio.get_event_loop().time()` 으로 deadline 을 잡는다** — 벽시계가 아니라 loop 시계다.

## 작업

`apps/api/tests/scripts/test_run_alembic_with_lock.py` **하나**를 신설한다.
`asyncpg.connect` · `asyncio.create_subprocess_exec` · `asyncio.sleep` · `src.core.config.settings` 를 mock 한다.
**진짜 DB 를 치지 마라. 진짜 alembic 을 돌리지 마라.**

### 최소한 이 열을 덮어라 (케이스 ≥10)

1. ★**`_normalize_url_for_asyncpg` 4케이스** — `postgresql+asyncpg://…` 는 치환된다 ·
   `postgresql://…` 와 `postgres://…` 는 **그대로** · ★**`count=1` 축**: 같은 접두 문자열이 URL 안에
   두 번 나오는 입력을 만들어 **첫 것만 바뀌는지** 재라. 이것이 `1` 인자를 지우는 변이를 잡는 유일한 케이스다
2. ★**`_parse_args` 기본값** — 인자 없이 부르면 `lock_key == 1903723824` · `timeout == 30`
3. ★**`_parse_args` 명시값** — `["--lock-key","7","--timeout","3"]` 이 그대로 실린다
4. ★★**lock 을 첫 시도에 잡으면 그 conn 이 반환되고 `close()` 는 **안** 불린다** —
   `fetchval` 이 `True` 를 반환하는 fake conn. `sleep` 이 **0회** 불린다
5. ★★**첫 시도 실패 → 두 번째 성공** — `fetchval` 이 `[False, True]` 를 순서대로 낸다.
   `asyncio.sleep` 이 **1회** 불리고 인자가 `1.0` 이다. 반환된 conn 은 열려 있다
6. ★★**timeout 소진 → `RuntimeError` 이고 `conn.close()` 가 불린다** — `fetchval` 이 늘 `False`.
   ★**이것이 누수 방지 `except` 를 재는 유일한 케이스다** — ⑷⑸만 있으면 그 블록을 지워도 초록이다
7. ★**`timeout_s=0` 경계** — 첫 실패 직후 즉시 `RuntimeError` 이고 `sleep` 이 **0회**다.
   ★**관측한 것을 박아라** — 예상과 다르면 `summary` 에 적어라
8. ★★**`_run_alembic_upgrade_head` 의 argv 가 정확히 `("uv","run","alembic","upgrade","head")` 다** +
   반환값이 `proc.wait()` 의 값 그대로다(예: 3). ★argv 를 통째로 assert 해라 — 부분 일치는 순서 변이를 놓친다
9. ★★**`run()` 의 `finally` 가 close 실패를 삼킨다** — `conn.close` 를 예외로 두면
   **예외가 밖으로 안 나오고** upgrade 의 rc 가 그대로 반환된다.
   ★**upgrade 가 던져도 conn.close 가 불린다**도 함께 재라 — `finally` 를 `else` 로 바꾸는 변이를 잡는다
10. ★★**`main()` 의 rc 매핑 2갈래** — `run` 이 `RuntimeError` 를 던지면 **rc 2** ·
    정상이면 **subprocess rc 를 그대로**(0 이 아닌 값으로 재라 — 0 이면 두 갈래가 구별 안 된다)
11. ★**`settings.database_url` 이 falsy 면 `RuntimeError`** — 이때 `asyncpg.connect` 가 **0회**다

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/scripts/test_run_alembic_with_lock.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/scripts/test_run_alembic_with_lock.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 10
cd apps/api && uv run --env-file .env.local pytest tests/scripts -q
cd apps/api && uv run ruff check tests/scripts/test_run_alembic_with_lock.py && uv run ruff format --check tests/scripts/test_run_alembic_with_lock.py
```

★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 **rc=4**(CONTROL 실측 2026-08-21).
★3번째는 인접 회귀다 — 착수 시점 `tests/scripts` 는 초록이다(CONTROL 전량 스위트 실측 2026-08-21 — 레포 전체 **5,130 passed · 3 xfailed · 0 failed**).
★`--env-file .env.local` 을 빼지 마라 — DB 가드가 rc=3 으로 거부한다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **⑺에서 관측한 `timeout_s=0` 의 실제 동작**을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**`src/scripts/run_alembic_with_lock.py` 를 수정하지 마라.** 이유: 이 회차의 계약은 「테스트만 추가하고
  대상 소스는 0줄 변경」이다. 결함을 발견하면 **고치지 말고 `status:"blocked"` + `blocked_reason`** 으로 멈춰라
- ★★**진짜 DB(asyncpg 실연결)·진짜 alembic 서브프로세스를 쓰지 마라.** 이유: 8 lane 이 동시에 돌고,
  실 alembic 은 공유 DB 스키마를 바꾼다. `asyncpg.connect` 와 `create_subprocess_exec` 를 mock 해라
- ★★**`xfail(strict=True)` 를 쓰지 마라. 이유:** 「제품 코드가 지금 틀렸다」를 원장에 박는 주장인데
  **AC·변이·사람 diff 세 층이 전부 통과시킨다**([LESSON-121]). 근거는 `summary` 에 적고 테스트는 지금 동작을 고정해라
- ★**재지 않은 값을 단언하지 마라.** 이유: step 의 산문은 세션에게 AC 와 구별되지 않는다([LESSON-122]).
  위 표의 값은 CONTROL 이 모듈을 읽고 확인한 것이고, ⑺ 처럼 「관측해서 박아라」라고 적힌 것은 **먼저 돌려 보고** 써라
- ★**`tests/scripts/test_soak_stack_migrate.py` 를 수정하지 마라** — 이름이 비슷하지만 다른 대상(셸 스크립트)이고 이 lane 소유가 아니다
- ★**`conftest.py` · `pyproject.toml` · `shards.json` 무변경**(8 lane 동시 실행 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — fake conn/proc 클래스는 이 테스트 파일 안에 둬라
- **새 pytest 마커를 쓰지 마라** — `--strict-markers` 라 `pyproject.toml` 을 함께 고쳐야 하고 그것이 공유 파일이다
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
