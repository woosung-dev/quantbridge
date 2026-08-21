# Step 0: di-assembly

## 읽어야 할 파일

- `apps/api/src/optimizer/dependencies.py` (67줄) — **대상 ①**
- `apps/api/src/stress_test/dependencies.py` (62줄) — **대상 ②**
- `apps/api/src/backtest/dependencies.py` (66줄) — **대상 ③**
- `apps/api/src/market_data/dependencies.py` (51줄) — **대상 ④** (HTTP 짝)
- `apps/api/src/optimizer/dispatcher.py` · `src/stress_test/dispatcher.py` · `src/backtest/dispatcher.py` —
  `Celery*Dispatcher` / `Noop*Dispatcher` 두 종류가 무엇을 하는지 확인용(**수정 금지 · 다른 lane 소유**)
- `apps/api/tests/trading/test_account_identity.py` — 이 lane 의 관용구(순수 호출 + `SimpleNamespace` fake)

## 배경

★★**착수 전 CONTROL 이 전량 스위트 커버리지로 쟀다 (2026-08-21 · `concurrency=greenlet,thread` 교정본):**

```
src/optimizer/dependencies.py     23 stmt    9 missed   56%   31, 45-60
src/stress_test/dependencies.py   23 stmt    9 missed   56%   26, 40-55
src/backtest/dependencies.py      24 stmt    8 missed   62%   44-59
src/market_data/dependencies.py   19 stmt    8 missed   52%   21, 38-48
```

**미커버 34줄이 전부 「무엇을 조립하는가」다.** 셋은 `build_*_service_for_worker` 이고 넷째는 그 HTTP 짝이다.

★★★**여기서 무방비인 계약이 무엇인지 CONTROL 이 코드로 확인했다:**

> **HTTP 경로는 `Celery*Dispatcher`, worker 경로는 `Noop*Dispatcher` 를 주입한다.**

**둘이 바뀌면 worker 가 자기 자신을 다시 dispatch 한다.** 지금 그 자리를 바꿔도 스위트는 초록이다.

★★**그리고 `get_ohlcv_provider` 의 timescale 갈래는 스위트에서 구조적으로 안 돈다** —
루트 `tests/conftest.py` 의 **autouse 픽스처 `_force_fixture_provider`** 가
`settings.ohlcv_provider` 를 `"fixture"` 로 못박기 때문이다. `settings` 를 직접 monkeypatch 해야 도달한다.

★**착수 전 CONTROL 실측 — 구조 (네 모듈을 직접 읽어 확인했다):**

| 함수                                                                         | 갈래                                                                                                                                                                                                                                                                                                                      |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `build_optimizer_service_for_worker(session)`                                | `settings.ohlcv_provider == "fixture"` → `FixtureProvider(root=settings.ohlcv_fixture_root)` / else → `TimescaleProvider(OHLCVRepository(session), get_ccxt_provider_for_worker(), exchange_name=settings.default_exchange)`. 반환 = `OptimizerService(repo·backtest_repo·strategy_repo·ohlcv_provider·dispatcher=Noop…)` |
| `build_stress_test_service_for_worker(session)`                              | **같은 모양** · `StressTestService` · `NoopStressTaskDispatcher`                                                                                                                                                                                                                                                          |
| `build_backtest_service_for_worker(session)`                                 | **같은 모양** · `BacktestService` · `NoopTaskDispatcher` (+ `ohlcv_repo`·`funding_repo` 도 받는다 — **파일에서 확인해라**)                                                                                                                                                                                                |
| `get_optimizer_service` / `get_stress_test_service` / `get_backtest_service` | HTTP 경로. `Celery*Dispatcher()` 주입                                                                                                                                                                                                                                                                                     |
| `get_ohlcv_provider(request, session)`                                       | `fixture` → `FixtureProvider` / else → `get_ccxt_provider(request)` 가 `None` 이면 **`RuntimeError`**, 아니면 `TimescaleProvider`                                                                                                                                                                                         |
| `get_ccxt_provider(request)`                                                 | `request.app.state.ccxt_provider` 를 그대로 반환                                                                                                                                                                                                                                                                          |

★**provider 클래스·`get_ccxt_provider_for_worker` 는 함수 본문 안에서 지연 import 된다** —
mock 은 **원 모듈**(`src.market_data.providers.timescale` 등)을 겨눠라.

## 작업

`apps/api/tests/common/test_worker_di_assembly.py` **하나**를 신설한다(네 모듈이 서로 다른 도메인이라
중립 자리에 둔다). session 은 **가짜 sentinel 객체**면 충분하다 — **DB 를 치지 마라.**

### 최소한 이 여덟을 덮어라 (케이스 ≥8)

1. ★★★**worker 3종이 Noop dispatcher 를 주입한다** — `build_optimizer_service_for_worker` ·
   `build_stress_test_service_for_worker` · `build_backtest_service_for_worker` 가 만든 서비스의
   dispatcher 가 **`Noop…` 타입**이다(`isinstance` 로 재라). ★**이것이 이 lane 의 핵심 계약이다**
2. ★★**HTTP 3종이 Celery dispatcher 를 주입한다** — `get_optimizer_service` · `get_stress_test_service` ·
   `get_backtest_service` 가 만든 서비스의 dispatcher 가 **`Celery…` 타입**이다. ⑴의 **음성 대조**다
3. ★★**worker 3종의 fixture 갈래** — `settings.ohlcv_provider="fixture"` 로 두면 provider 가
   `FixtureProvider` 이고 **`root` 가 `settings.ohlcv_fixture_root` 와 같다**
4. ★★**worker 3종의 timescale 갈래** — `settings.ohlcv_provider` 를 `"timescale"` 로 monkeypatch 하면
   provider 가 `TimescaleProvider` 다. ★**`exchange_name` 이 `settings.default_exchange` 와 같은지**도 재라
   (지금 스위트에서 한 번도 안 도는 갈래다)
5. ★★**세 서비스가 받은 repo 들이 전부 같은 session 을 물고 있다** — sentinel session 을 넘기고,
   조립된 repo 들이 **그 sentinel** 을 들고 있는지 재라(cross-repo transaction 계약).
   ★**어떤 repo 가 주입되는지는 각 파일을 열어 확인해라** — 여기 나열하지 않은 이유는 재지 않았기 때문이다
6. ★★★**`get_ohlcv_provider` 의 `RuntimeError` 갈래** — `settings.ohlcv_provider="timescale"` 이고
   `request.app.state.ccxt_provider` 가 `None` 이면 **`RuntimeError`** 다.
   ★**이것이 그 가드를 재는 유일한 케이스다** — 없으면 가드를 지워도 초록이다
7. ★**`get_ohlcv_provider` 의 fixture 갈래 + timescale 정상 갈래** — 후자는 `ccxt_provider` 가 non-None 일 때
8. ★**`get_ccxt_provider` 가 `request.app.state.ccxt_provider` 를 **그대로** 반환한다** —
   `SimpleNamespace` 로 request 를 흉내내고 **동일성(`is`)** 으로 재라
9. (선택) **세 `build_*_for_worker` 가 `settings` 를 **호출 시점에** 읽는지** 재라 —
   import 시점에 캐시하면 monkeypatch 가 안 먹는다. **관측한 것을 박아라**

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/common/test_worker_di_assembly.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/common/test_worker_di_assembly.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 8
cd apps/api && uv run --env-file .env.local pytest tests/common -q
cd apps/api && uv run ruff check tests/common/test_worker_di_assembly.py && uv run ruff format --check tests/common/test_worker_di_assembly.py
```

★2번째 AC 는 **양성 대조**다. 착수 시점 이 파일은 없으므로 첫 AC 는 **rc=4**(CONTROL 실측 2026-08-21).
★`--env-file .env.local` 을 빼지 마라 — DB 가드가 rc=3 으로 거부한다.

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 케이스 수와 **⑸에서 확인한 세 서비스의 실제 repo 목록**, ⑼의 관측 결과를 남겨라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- ★**네 `dependencies.py` 를 전부 수정하지 마라.** 이유: 이 회차의 계약은 「테스트만 추가하고 대상 소스는
  0줄 변경」이다. 결함을 발견하면 **고치지 말고 `status:"blocked"` + `blocked_reason`** 으로 멈춰라
- ★**`dispatcher.py` 3종을 수정하지 마라** — **다른 lane(`be5-dispatch-trio`)이 그 파일들을 겨눈다.**
  읽기만 해라. 테스트도 만들지 마라
- ★★**진짜 DB session 을 만들지 마라.** 이유: 8 lane 이 동시에 돌고, 이 lane 은 「무엇이 조립되는가」만
  재면 된다. session 은 sentinel 객체로 충분하다
- ★★**`xfail(strict=True)` 를 쓰지 마라. 이유:** 「제품 코드가 지금 틀렸다」를 원장에 박는 주장인데
  **AC·변이·사람 diff 세 층이 전부 통과시킨다**([LESSON-121]). 근거는 `summary` 에 적고 테스트는 지금 동작을 고정해라
- ★**재지 않은 값을 단언하지 마라.** 이유: step 의 산문은 세션에게 AC 와 구별되지 않는다([LESSON-122]).
  각 서비스의 생성자 인자 이름·개수는 **그 파일을 열어 확인**하고 써라
- ★**루트 `conftest.py` 의 `_force_fixture_provider` 를 고치지 마라** — 8 lane 공유 파일이다.
  `monkeypatch.setattr` 로 **이 테스트 안에서만** settings 를 덮어라
- ★**`conftest.py` · `pyproject.toml` · `shards.json` 무변경**(8 lane 동시 실행 — 병합 충돌)
- **공용 헬퍼 모듈을 만들지 마라** — sentinel/fake 는 이 테스트 파일 안에 둬라
- **새 pytest 마커를 쓰지 마라** — `--strict-markers` 라 `pyproject.toml` 을 함께 고쳐야 하고 그것이 공유 파일이다
- `docs/**` · `phases/**` 무변경. 다른 lane 의 테스트 파일을 만들지 마라
- 커밋하지 마라(커밋은 러너 소관)
