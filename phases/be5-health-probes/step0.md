# Step 0: health-probes

## 읽어야 할 파일

- `apps/api/src/health/router.py` (85줄) — **이번 테스트의 대상**. 특히 `_check_postgres`(61-77) ·
  `_check_redis`(80-95) · `_check_celery_workers`(98-124) · `_get_celery_timeout_s`(39-50)
- `apps/api/tests/health/conftest.py` — ★**이 디렉터리는 상위 `client` 를 shadowing 해서 DB 를 끊는다.**
  `health.router` 만 mount 한 minimal FastAPI app 이다. 그 픽스처를 그대로 써라
- `apps/api/tests/health/test_health_extended.py` — 기존 5 케이스. **이 lane 은 그것과 다른 층이다**(아래 배경)
- `apps/api/tests/health/test_livez_and_timeout_override.py` — `_get_celery_timeout_s` 관련 선례

## 배경

★★★**착수 전 CONTROL 이 전량 스위트 커버리지로 쟀다 (2026-08-21 · `concurrency=greenlet,thread` 교정본):**

```
src/health/router.py     85 stmt   41 missed   54%   63-77, 82-95, 104-124
```

**미커버 41줄 = 세 프로브 함수의 본문 전부다.**

★★**왜 그런지 CONTROL 이 코드로 대조했다** — `tests/health/test_health_extended.py` 의 5 케이스는
`_check_postgres` · `_check_redis` · `_check_celery_workers` 를 **`monkeypatch.setattr` 로 통째 치환**한다.
그래서 그 테스트가 재는 것은 **집계 로직**(200 vs 503 · body 모양)이고, **프로브 본문은 한 번도 안 돈다.**
★**실행 우회는 커버가 아니다.** 모듈 docstring 17줄이 「`test_health_extended.py` 가 mock 으로 dep fail 시뮬」
이라 적어 둔 것은 참이지만, 그것이 **프로브를 검증한다는 뜻은 아니다.**

이 함수들은 **Cloud Run / docker-compose 의 readiness probe** 다. 잘못 `ok` 를 내면 죽은 인스턴스로
트래픽이 가고, 잘못 `fail` 을 내면 멀쩡한 배포가 롤백된다. **지금 세 함수의 `except` 를 전부 지워도 초록이다.**

★**착수 전 CONTROL 실측 — 구조 (모듈을 직접 읽어 확인했다):**

| 함수                    | 갈래                                                                                                                                                                                                                                                                                    |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_check_postgres`       | `asyncio.timeout(_PG_TIMEOUT_S)` + `engine.connect()` → `SELECT 1` → `("ok", None)` / `TimeoutError` → `("fail", f"timeout after {_PG_TIMEOUT_S}s")` / `Exception` → `("fail", str(exc))`                                                                                               |
| `_check_redis`          | `get_redis_lock_pool()` → `await pool.ping()` → **`if not pong: ("fail","PING returned False")`** → `("ok", None)` / `TimeoutError` / `Exception`                                                                                                                                       |
| `_check_celery_workers` | **`celery_app` import 실패 → `(0, f"celery_app import failed: {exc}")`** / `asyncio.to_thread(...inspect(timeout=…).ping())` → **falsy → `(0,"no workers responded")`** → `(len(result), None)` / `TimeoutError` → `(0, f"timeout after {timeout_s}s")` / `Exception` → `(0, str(exc))` |
| `_get_celery_timeout_s` | `HEALTHZ_CELERY_TIMEOUT_S` env → `float()`, `(TypeError, ValueError)` → `12.0`                                                                                                                                                                                                          |

★상수: `_PG_TIMEOUT_S = 5.0` · `_REDIS_TIMEOUT_S = 5.0` · celery 기본 `12.0`.
★**`text` · `engine` · `get_redis_lock_pool` · `celery_app` 은 전부 함수 본문 안에서 지연 import 된다** —
mock 위치를 그에 맞춰 잡아라(`monkeypatch.setattr("src.common.database.engine", …)` 처럼 **원 모듈**을 겨눠라).

## 작업

`apps/api/tests/health/test_health_probes.py` **하나**를 신설한다.
**세 프로브 함수를 직접 `await` 해라** — HTTP 를 거치지 마라(집계는 기존 파일이 이미 잰다).
**진짜 DB·Redis·celery broker 를 치지 마라.**

### 최소한 이 열을 덮어라 (케이스 ≥10)

1. ★★**`_check_postgres` 정상** — `engine.connect()` 가 `SELECT 1` 을 실행하면 `("ok", None)`.
   ★**`conn.execute` 가 실제로 불렸는지**도 재라(연결만 하고 쿼리를 안 보내는 변이를 잡는다)
2. ★★**`_check_postgres` 예외** — `connect` 가 예외를 던지면 `("fail", str(exc))` 이고 **예외가 밖으로 안 나온다**.
   ★두 번째 원소가 그 예외 메시지를 지고 있는지 재라
3. ★★**`_check_postgres` 타임아웃** — `TimeoutError` 를 만들어 `("fail", "timeout after 5.0s")` 형태인지 재라.
   ★**메시지에 `_PG_TIMEOUT_S` 값이 실려 있는지**까지 재라(상수를 바꾸는 변이를 잡는다)
4. ★★**`_check_redis` 의 `pong` falsy 갈래** — `ping()` 이 `False` 를 반환하면 `("fail", "PING returned False")`.
   ★**이것이 `if not pong` 을 재는 유일한 케이스다** — 정상 케이스만 있으면 그 두 줄을 지워도 초록이다
5. ★**`_check_redis` 정상 · 예외 · 타임아웃 3갈래** — ⑴~⑶과 같은 모양
6. ★★★**`_check_celery_workers` 의 import 실패 갈래** — `celery_app` import 를 실패시키면
   `(0, "celery_app import failed: …")`. ★**이 갈래는 지연 import 라 `sys.modules` 조작이 필요할 수 있다** —
   **어떻게 재현했는지 `summary` 에 적어라.** 재현이 불가능하면 그 이유를 적고 나머지를 채워라
7. ★★**`_check_celery_workers` 의 falsy 결과 갈래 2종** — `ping()` 이 `None` 인 경우와 `{}` 인 경우
   **둘 다** `(0, "no workers responded")` 다
8. ★**worker 수 세기** — `ping()` 이 워커 2개짜리 dict 를 주면 `(2, None)` 이다
   (`len(result)` 를 `1` 로 바꾸는 변이를 잡는다)
9. ★**`_check_celery_workers` 타임아웃 · 일반 예외** — 각각 `(0, f"timeout after {timeout_s}s")` / `(0, str(exc))`
10. ★★**`_get_celery_timeout_s` 3갈래** — env 미설정 → `12.0` · 유효 숫자 문자열 → 그 값 ·
    **파싱 불가 문자열 → `12.0`**(fallback). ★`monkeypatch.setenv`/`delenv` 를 써라
11. ★**타임아웃 값이 celery inspect 에도 전달된다** — `inspect(timeout=…)` 가 받은 값이
    `_get_celery_timeout_s()` 와 같다(하드코딩된 다른 값을 쓰는 변이를 잡는다)

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/health/test_health_probes.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/health/test_health_probes.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 10
cd apps/api && uv run --env-file .env.local pytest tests/health -q
cd apps/api && uv run ruff check tests/health/test_health_probes.py && uv run ruff format --check tests/health/test_health_probes.py
```

★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 **rc=4**(CONTROL 실측 2026-08-21).
★`--env-file .env.local` 을 빼지 마라 — DB 가드가 rc=3 으로 거부한다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **⑹의 import 실패 갈래를 어떻게 재현했는지**(또는 왜 못 했는지)를 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**`src/health/router.py` 를 수정하지 마라.** 이유: 이 회차의 계약은 「테스트만 추가하고 대상 소스는
  0줄 변경」이다. 결함을 발견하면 **고치지 말고 `status:"blocked"` + `blocked_reason`** 으로 멈춰라
- ★★**세 프로브 함수 자체를 monkeypatch 하지 마라.** 이유: **그것이 기존 5 케이스가 한 일이고, 그래서
  프로브 본문이 41줄 미커버로 남았다.** 이 lane 은 **프로브 안쪽**(engine·redis pool·celery inspect)을
  mock 해서 **프로브 본문을 실제로 돌리는** 것이 목적이다
- ★★**진짜 Postgres·Redis·celery broker 를 치지 마라.** 이유: 8 lane 이 동시에 돌고, 워크트리에서
  celery 경유 검증은 메인 체크아웃 소스가 돈다(침묵 실패)
- ★★**`xfail(strict=True)` 를 쓰지 마라. 이유:** 「제품 코드가 지금 틀렸다」를 원장에 박는 주장인데
  **AC·변이·사람 diff 세 층이 전부 통과시킨다**([LESSON-121]). 근거는 `summary` 에 적고 테스트는 지금 동작을 고정해라
- ★**`tests/health/conftest.py` 를 수정하지 마라** — 8 lane 공유는 아니지만 기존 4파일이 그 픽스처를 쓴다.
  필요하면 **이 테스트 파일 안에** 로컬 픽스처를 둬라
- ★**`tests/health/` 의 기존 테스트 파일을 수정하지 마라** — 이 lane 소유가 아니다
- ★**`conftest.py`(루트) · `pyproject.toml` · `shards.json` 무변경**(8 lane 동시 실행 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — fake engine/pool 클래스는 이 테스트 파일 안에 둬라
- **새 pytest 마커를 쓰지 마라** — `--strict-markers` 라 `pyproject.toml` 을 함께 고쳐야 하고 그것이 공유 파일이다
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
