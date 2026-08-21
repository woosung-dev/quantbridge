# Step 0: 재료 실사 + 테스트 파일 신설 — celery 워커 수명주기 · ws 스트림 태스크

## 읽어야 할 파일

- ★**`apps/api/AGENTS.md`** — FastAPI 3-Layer · Decimal-first · Celery prefork-safe (§2/§3/§9).
  ★그 디렉터리 파일을 열면 자동 로드된다([ADR-027]) — 안 열렸으면 직접 읽어라
- `apps/api/src/tasks/celery_app.py` — **이번 회차의 대상**
- `apps/api/src/tasks/websocket_task.py` — **이번 회차의 대상**
- `apps/api/src/tasks/_ws_lease.py` — **이번 회차의 대상**
- `apps/api/tests/tasks/test_worker_task_lifecycle.py` · `apps/api/tests/trading/test_alert_rule_repository_contract.py`
  — **5차가 남긴 관용구 정본.** 베끼지 말고 열어서 모양을 따라라

## 이 lane 이 만드는 파일

- `apps/api/tests/tasks/test_celery_app_lifecycle.py`
- `apps/api/tests/tasks/test_websocket_task_runtime.py`

## 착수 전 실측 (2026-08-22 · CONTROL · `concurrency = greenlet,thread` 교정본)

| 대상 | 커버 | 미커버 | 미커버 줄 |
| --- | --- | --- | --- |
| `src/tasks/celery_app.py` | **54.9%** (★AC 기준 **32.0%**) | 43/106 | `264-266,275-276,280-283,290,299,303-305,309-311,313,318-321,325-326,342-343,345-346,376-378,385,389,393-394,396-398,400,407-408,412-413` |
| `src/tasks/websocket_task.py` | **61.0%** (★AC 기준 **58.9%**) | 70/204 | `63-64,96,98,109,111,148-149,162-163,168-169,173-175,192-193,195-196,199-204,208-213,215-224,226-227,232,234-235,278,283,345,349-350,354-358,361,396,398-399,405,427,429,464-470` |
| `src/tasks/_ws_lease.py` | 84.0% (★AC 기준 84.0%) | 10/69 | `114,162,164-165,167,172-173,179,183-184` |

★★**이 수치는 `[tool.coverage.run]` 에 `concurrency = greenlet,thread` 를 넣고 잰 값이다.**
그 설정이 없으면 SQLAlchemy greenlet 전환 뒤의 줄이 전부 미커버로 나와 **거짓으로 낮게** 나온다
(5차 실측: `outcome_parity_service.py` 80% → 100%). 사전 배치 PR 이 그 설정을 이미 넣었다.

★★★**「전량 스위트」와 「AC 기준」이 다르다 — 네가 넘어야 하는 것은 AC 기준이다.**
AC 는 `tests/tasks` 만 돌린다. 다른 디렉터리의 테스트가 이 모듈을 import 하며 덮던 몫은
그 실행에 **안 들어온다**. 그래서 착수 전 값이 전량 스위트보다 낮다 — 위 표의 「★AC 기준」이
**네 시작점**이고, AC 의 하한은 그 값 위에서 정했다. 두 수치를 섞어 읽지 마라.

## 이 lane 만의 사실

★**이 lane 은 DB 를 쓰지 않는다** — 외부 경계는 전부 mock 이다

★★**이 lane 의 미커버는 「신호 핸들러」와 「루프 본문」 둘이다.**
  `celery_app.py` 의 264~413 은 `worker_process_init`·`worker_process_shutdown`·
  `beat_init`·`worker_ready`·`worker_shutdown` 에 붙은 **시그널 콜백**과
  `get_ccxt_provider_for_worker()` 다. **celery 를 띄우지 마라** — 그 함수들은
  그냥 파이썬 함수다. 직접 부르면 된다.
★★`apps/api/AGENTS.md` **§9 Celery prefork-safe** 가 이 파일의 계약이다.
  fork 뒤 상태 초기화가 왜 필요한지 거기 적혀 있다 — 테스트가 그 계약을 재도록 써라.
★`websocket_task.py` 의 미커버는 `_stream_main`·`_public_ticker_stream_main`·
  `_reconcile_async` 의 **재연결·중단·예외 갈래**다. `signal_all_stop_events()` 로
  루프를 끊을 수 있는 구조인지 먼저 읽어라.
★★**진짜 웹소켓에 붙지 마라. 진짜 Redis 를 치지 마라.** 이 lane 은 DB 도 안 쓴다 —
  외부 경계는 전부 mock 이다. 5차의 `tests/tasks/test_worker_task_lifecycle.py` 가
  같은 자리의 관용구를 갖고 있다 — 열어 봐라.

## 작업

1. **대상을 직접 읽어라.** 위 「미커버 줄」 구간을 실제로 열어 **무엇이 안 돌았는지** 확인해라.
   위 표는 CONTROL 이 2026-08-22 에 전량 스위트로 잰 값이다 — **네가 다시 재서 다르면
   그 사실을 `summary` 맨 앞에 적어라.** 5차에서 재료 8개 중 6개가 이 대조로 갈렸다.
2. ★**대상이 이미 85% 이상 덮여 있으면 재료가 아니다.** `status` 를 `blocked` 로 하고
   `blocked_reason` 에 측정 명령과 수치를 적고 **즉시 중단**해라.
3. **테스트 파일을 신설한다** — 위 경로 그대로. 이 step 은 **가장 확실한 것부터 최소 6케이스**만.

## `summary` 에 반드시 담을 것

- 미커버 구간별 「무엇을 하는 코드인가 · 어떻게 도달시킬 것인가」
- 착수 전 실측 커버리지 (AC 첫 두 명령의 출력)
- mock 을 어디에 걸었는지와 **왜 거기인지**

## Acceptance Criteria

1. `test -f apps/api/tests/tasks/test_celery_app_lifecycle.py -a -f apps/api/tests/tasks/test_websocket_task_runtime.py`
2. `cd apps/api && uv run --env-file .env.local pytest tests/tasks -q --cov=src/tasks`
3. `cd apps/api && uv run coverage report --include=src/tasks/celery_app.py --fail-under=38`
4. `cd apps/api && uv run coverage report --include=src/tasks/websocket_task.py --fail-under=62`
5. `cd apps/api && uv run coverage report --include=src/tasks/_ws_lease.py --fail-under=85`
6. `cd apps/api && test "$(uv run --env-file .env.local pytest tests/tasks/test_celery_app_lifecycle.py tests/tasks/test_websocket_task_runtime.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 6`
7. `git diff --quiet -- apps/api/src/tasks/celery_app.py apps/api/src/tasks/websocket_task.py apps/api/src/tasks/_ws_lease.py`

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `apps/api/AGENTS.md` 의 필수 항목(3-Layer 경계 · Decimal · 한국어 헤더 주석)을 지켰는지 확인한다.
3. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **대상 소스를 한 줄도 고치지 마라.** 이유: 이 lane 은 커버리지 lane 이다.
  ★소스에 결함이 보이면 **고치지 말고 `summary` 에 적어라** — 5차에서 그렇게 [BL-819] 를 잡았다.
- **`.skip`·`xfail` 로 통과시키지 마라.** ★`xfail(strict=True)` 는 「제품 코드가 틀렸다」를
  원장에 박는 주장이다 — 코드 대조 없이 쓰면 AC·변이·diff 가 전부 통과시킨다(1차 실증).
- **celery worker·웹소켓·거래소에 실제로 붙지 마라.** 이유: AC 가 외부 상태에 의존하면
  간헐 red 가 되고, 러너는 그것을 실패로 판정한다.
- **`docs/**` 를 만지지 마라.** 이유: 12 lane 이 같은 원장 파일을 고치면 병합이 통째로 충돌한다.
- **`mise run up/down/migrate/seed` 를 하지 마라.** 이유: 컨테이너·앱 DB 는 1벌 공유라 함께 깨진다.
- 커밋하지 마라(커밋은 러너 소관).
