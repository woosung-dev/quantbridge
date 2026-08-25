# Step 0: prove-parse-blocks-event-loop

## 읽어야 할 파일

- `apps/api/src/strategy/service.py` — `_parse`(`:129-176`)와 그것을 부르는 **세 `async def`**:
  `parse_preview`(`:200`, 호출 `:201`) · `create`(`:222`, 호출 `:231`) · `update`(`:349`, 호출 `:375`)
- `apps/api/src/strategy/router.py` — 파스 엔드포인트
- `apps/api/tests/strategy/test_strategies_parse.py` — **기존 파스 엔드포인트 테스트의 조립 방식 정본**
- `apps/api/src/health/router.py:113` — 레포에서 **유일한** `run_in_threadpool`/`to_thread` 사용례

## 배경 — 확인된 사실

`_parse` 는 **동기 함수**이고 그 안에서 `parse_to_ast(source)` 가 CPU 를 잡는다. 그것을
`async def` 세 곳이 **await 없이 직접** 호출한다 ⇒ 파싱 동안 **이벤트 루프가 통째로 멈춘다.**

실측된 파스 비용(격리, median-of-3): 콜드 프로세스에서 `s5_ema_trend` 2.61s · `s3_rsid` 11.55s ·
39KB 짜리 `i3_drfx` **52.37s**. 레포 어디에도 uvicorn `--workers` 지정이 없어 워커는 1개다
⇒ 그 시간 동안 `/healthz` 를 포함한 **모든 요청**이 대기한다.

★**이것은 속도 문제가 아니라 가용성 문제다.** 같은 회차의 다른 lane 이 파스 횟수를 줄이지만,
한 번의 파스가 루프를 막는다는 사실은 그것과 무관하게 남는다.

## 작업

신설 — `apps/api/tests/strategy/test_parse_event_loop_blocking.py`

이 step 은 **제품 코드를 고치지 않는다.** 「지금 막는다」를 기계로 박는 것이 산출이고,
step 1 이 그 단언을 뒤집는다.

### 탐지 방식 — 시간이 아니라 **틱 수**로 판정해라

절대 시간을 단언하면 머신에 따라 간헐 red 가 난다(이 레포에서 반복된 함정이다). 대신:

1. `strategy.service` 가 보는 `parse_to_ast` 를 **의도적으로 블로킹하는 스텁**으로 갈아끼운다
   (`time.sleep(<짧은 상수>)` — 0.2초 정도면 충분하다. `asyncio.sleep` 이 아니다).
2. 파스 요청 코루틴과 **하트비트 코루틴**을 `asyncio.gather` 로 동시에 띄운다.
   하트비트는 `for _ in range(N): await asyncio.sleep(0); ticks += 1` 처럼 **루프에 양보만** 한다.
3. 루프가 막히면 `ticks` 가 목표에 못 미치고, 안 막히면 목표에 도달한다.
   ★단언은 **`ticks` 에 대한 것**이지 경과 초에 대한 것이 아니다.

★**스텁 주입 지점은 `src.strategy.service` 의 이름이다** — `monkeypatch.setattr("src.strategy.service.parse_to_ast", stub)`.
`parser_adapter` 쪽을 갈아끼우지 마라. 이유: 다른 lane 이 그 함수에 캐시를 걸 수 있고, 그러면
스텁이 캐시 뒤로 밀려 호출조차 안 된다. **이 lane 은 `service` 의 이름만 만진다.**

필수 테스트 3종:

1. **현재 상태 단언** — 블로킹 스텁을 넣으면 하트비트 틱이 목표에 **도달하지 못한다**(= 막힌다).
2. **양성 대조** — 같은 하네스에서 스텁을 **비블로킹**(즉시 반환)으로 바꾸면 틱이 목표에 **도달한다**.
   「하네스가 고장나서 항상 못 센다」를 배제한다.
3. **경로 도달 단언** — 스텁이 실제로 **호출됐다**(호출 카운터 ≥ 1). 「요청이 파스 경로에 안 닿아서
   막히지 않았다」를 배제한다. ★이 세 번째가 없으면 1·2 가 둘 다 참인 항진명제가 될 수 있다.

세 곳(`parse_preview` · `create` · `update`) 중 **`parse_preview` 하나만** 덮어도 된다 —
가장 조립이 가벼운 경로다. 어느 것을 골랐는지 `summary` 에 적어라.

## Acceptance Criteria

```
cd apps/api && set -a; . ./.env.local; set +a; uv run pytest tests/strategy/test_parse_event_loop_blocking.py -q
cd apps/api && set -a; . ./.env.local; set +a; test "$(uv run pytest tests/strategy/test_parse_event_loop_blocking.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 3
cd apps/api && uv run ruff check tests/strategy
```

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `summary` 에 ⑴ 고른 엔드포인트 ⑵ 하트비트 목표 틱 수와 그 근거 ⑶ 스텁 sleep 상수 ⑷ **테스트 함수
   이름 3개**(step 1 이 뒤집을 대상)를 적어라.
3. 규약: `apps/api/AGENTS.md`.
4. 사람 개입이 필요하면 `status:"blocked"` + `blocked_reason` 후 즉시 중단.

## 금지사항

- **`src/` 를 한 줄도 고치지 마라.** 이유: step 1 의 red→green 이 무엇 때문인지 갈리지 않는다.
- **`src/strategy/pine_v2/` 를 읽는 것은 되지만 만지지 마라.** 이유: 그 디렉터리는 **다른 lane 이
  동시에 수정 중**이다. 두 lane 이 같은 파일을 고치면 머지가 충돌한다.
- **경과 시간(초)을 단언하지 마라.** 이유: 머신 부하로 흔들려 간헐 red 가 되고, 그러면 다음 사람이
  이 가드를 끈다.
- 실제 `pynescript` 파싱을 테스트에서 돌리지 마라(스텁을 써라). 이유: 콜드 파스가 최대 52초다.
- 커밋하지 마라(커밋은 러너 소관).
