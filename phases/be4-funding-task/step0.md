# Step 0: funding-task

## 읽어야 할 파일

- `apps/api/src/tasks/funding.py` (93줄) — **이번 테스트의 대상**
- `apps/api/tests/tasks/test_orphan_scanner_prefork_safe.py` — ★★**이 lane 의 관용구 정본이다.**
  `_RecordingEngine`(dispose 횟수 기록) + `create_worker_engine_and_sm` mock + 정상/예외 두 경로.
  **같은 모양으로 써라** — 파일을 열어 보고 베껴라(여기 복사해 오지 않은 이유는 낡은 사본이 되기 때문이다)
- `apps/api/src/tasks/_worker_engine.py` — `create_worker_engine_and_sm`
- `apps/api/src/trading/models.py` — `ExchangeName` (bybit · binance · okx)
- `apps/api/AGENTS.md` §9 — Celery prefork-safe 규칙

## 배경

★**이 모듈은 `apps/api` 에서 전이 폐포 미도달 2건 중 하나다**(2026-08-21 실측 · 총 193 모듈 중).
**어떤 테스트도 이 파일에 도달하지 않는다.** beat 로 **매 1시간** 도는 태스크인데 그렇다.

핵심은 **prefork-safe 계약**이다. `apps/api/AGENTS.md` §9 와 [BL-080]/Sprint 17 이력이 말하는 그것:

★★**module-level 캐시 엔진 + Celery prefork 조합이 실제로 6시간 동안 141/141 실패를 냈다**
(`asyncpg InterfaceError` — 새 loop binding mismatch). 처방은 **호출마다 엔진을 새로 만들고
`finally` 에서 `dispose()`** 하는 것이고, `funding.py` 의 `_async_fetch`·`_async_backfill` 이
그 모양으로 쓰여 있다. **그 `finally` 가 지워져도 지금은 아무도 모른다.**

★**착수 전 CONTROL 실측 (2026-08-21):**

| 축         | 관측                                                                                                                                                                        |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 태스크 2개 | `fetch_funding_rates_task`(`name="trading.fetch_funding_rates"`, `max_retries=2`) · `backfill_funding_rates_task`(`name="trading.backfill_funding_rates"`)                  |
| 실제 일    | `_async_fetch` · `_async_backfill` — 둘 다 `create_worker_engine_and_sm()` → `async with sm()` → `src.trading.funding` 의 함수 호출 → **`finally: await engine.dispose()`** |
| 기본값     | `exchange_name="bybit"` · `symbol="BTC/USDT:USDT"` · `lookback_hours=2`                                                                                                     |
| 반환       | `{"exchange": ..., "symbol": ..., "inserted": ...}`                                                                                                                         |

★**`run_in_worker_loop` 는 태스크 함수 안에서 지연 import 된다** — mock 위치를 그에 맞춰 잡아라.
★**`async def _async_*` 를 직접 `await` 하는 것이 가장 얇은 경로다**(`test_conditional_entry_janitor.py`
가 `_async_conditional_entry_janitor()` 를 그렇게 직접 부른다 — 그 선례를 봐라).

## 작업

`apps/api/tests/tasks/test_funding_task.py` **하나**를 신설한다.
`create_worker_engine_and_sm` 과 `src.trading.funding` 의 두 함수를 mock 한다. **DB 를 치지 마라.**

### 최소한 이 여덟을 덮어라 (케이스 ≥8)

1. ★★**정상 경로에서 `engine.dispose()` 가 정확히 1회 await 된다** — `_async_fetch` 직접 호출.
   `_RecordingEngine` 관용구를 써라
2. ★★**저장 함수가 던져도 `dispose()` 가 된다** — `fetch_and_store_funding_rates` 를 `side_effect`
   예외로 두고, 예외가 밖으로 나가면서도 `dispose_calls == 1` 이다.
   ★**이것이 `finally` 를 재는 유일한 케이스다** — ⑴만 있으면 `finally` 를 `else` 로 바꿔도 초록이다
3. ★★**`create_worker_engine_and_sm` 이 호출마다 **1회** 불린다** — 두 번 연속 호출하면 **2회**다
   (module-level 캐시가 되살아나면 여기서 잡힌다). ★모듈에 캐시 전역이 없는지도 함께 관측해라
4. ★★**`since` 가 `now - lookback_hours` 다** — `lookback_hours=5` 로 주고 저장 함수가 받은 `since` 가
   **tz-aware(UTC)** 이고 지금으로부터 약 5시간 전이다(초 단위 오차 허용).
   ★**시각을 하드코딩하지 마라** — 호출 전후로 경계를 잡아 그 사이인지 재라
5. ★**`exchange_name` 문자열이 `ExchangeName` 으로 변환돼 넘어간다** — 저장 함수가 받은 인자가
   `str` 이 아니라 `ExchangeName` 이다. `symbol` 은 그대로 넘어간다
6. ★**알 수 없는 거래소 이름은 `ValueError` 로 죽는다** — `ExchangeName("kraken")` 이 던진다.
   ★**이때 엔진이 만들어지기 **전**인지 **후**인지 관측해서 박아라** — 후라면 `dispose` 가 되는지도 재라
   (예상과 다르면 `summary` 에 적어라. 누수라면 그것이 이 lane 의 산출이다)
7. ★**반환 형상이 계약대로다** — 키 3종(`exchange`·`symbol`·`inserted`)이고 `inserted` 가
   저장 함수의 반환값과 같다. **이것이 양성 대조다**(mock 이 안 불렸으면 값이 안 맞는다)
8. ★★**`_async_backfill` — `start_iso`/`end_iso` 가 `datetime` 으로 파싱돼 넘어간다** +
   **`dispose()` 정상·예외 두 경로**. ★`fromisoformat` 이 못 읽는 문자열에서 무엇이 일어나는지
   **관측해서 박아라**(엔진 생성 전인지 후인지 포함)
9. (선택) **태스크 등록 이름 2종과 `max_retries=2`** — celery 데코레이터의 메타를 재라.
   beat 스케줄이 이름으로 찾으므로 이름이 바뀌면 조용히 안 돈다

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/tasks/test_funding_task.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/tasks/test_funding_task.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 8
cd apps/api && uv run ruff check tests/tasks/test_funding_task.py
```

★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 rc=4 (CONTROL 실측 2026-08-21).
★`--env-file .env.local` 을 빼지 마라 — DB 가드가 rc=3 으로 거부한다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **⑹·⑻에서 관측한 실패 경로의 실제 동작**(엔진 생성 전/후 · dispose 여부)을 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**`src/tasks/funding.py` 를 수정하지 마라.** 이유: 이 회차의 계약은 「테스트만 추가하고 대상 소스는
  0줄 변경」이다. 결함(예: 예외 경로 엔진 누수)을 발견하면 **고치지 말고 `summary` 에 적어라**
- ★★**진짜 DB·거래소를 치지 마라.** 이유: 워크트리에서 celery 경유 검증은 worker 가 **메인 체크아웃의
  소스를 mount** 하므로 내 코드가 아니라 메인 코드가 돈다(침묵 실패). `create_worker_engine_and_sm`
  과 `src.trading.funding` 을 mock 해서 **함수만** 재라
- ★★**`xfail(strict=True)` 를 쓰지 마라. 이유:** 「제품 코드가 지금 틀렸다」를 원장에 박는 주장인데
  **AC·변이·사람 diff 세 층이 전부 통과시킨다**([LESSON-121]). 근거는 `summary` 에 적고 테스트는
  지금 동작을 고정해라
- ★**`celery_app.py` · beat 스케줄을 수정하지 마라** — `test_beat_schedule.py` 가 이미 있고 이 lane 소유가 아니다
- ★**`conftest.py` · `shards.json` 무변경**(8 lane 동시 실행 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — `_RecordingEngine` 같은 것은 이 테스트 파일 안에 둬라
  (선례 파일에서 **베껴 오되 import 하지 마라**)
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
