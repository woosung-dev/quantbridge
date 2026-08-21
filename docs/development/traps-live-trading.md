# 함정 — 라이브·원장·거래소

> **진입점은 [`gates-and-traps.md`](./gates-and-traps.md) 다** — 이 파일은 그 §3 함정을 2026-08-21 에 주제별로 나눈 조각이다
> ([ADR-038](../adr/038-docs-top-level-by-question.md) 후속 · 원문 = `git show 9e91809c:docs/development/gates-and-traps.md`).
> **다루는 것:** 라이브 신호 도메인, 거래소 실상, 원장을 읽을 때, 함대·계측, 계기.
> 규율은 ADR-026 ④ 그대로 — 서술만, 지시 금지. 새 함정은 날짜·회차·실측을 적고, 정본 절차가 바뀌면 여기도 같은 PR 에서 고친다.

---

## 라이브 신호 도메인

- ★**라이브 `live_signal_states.total_realized_pnl` 은 세션 원장이 아니다.** `run_live` 가 **창 안 청산만** 합산해 매 tick 덮어쓰므로 **단조가 아니다**(실측: 3건 `5.16879987` → 2건 `4.07002377`). 세션 손익의 SSOT 는 append-only 인 **`live_signal_events`** 다.
- ★**라이브 OHLCV 프레임은 `RangeIndex` + `timestamp` 컬럼**이다(`_ohlcv_rows_to_dataframe`). 인덱스에 의존하는 엔진 게이트(`sessions_allowed` 계열)는 **예외도 경고도 없이 no-op** 이 된다. 백테스트는 `v2_adapter` 가 422 로 막지만 라이브엔 등가물이 없었다.
- ★**시뮬 PnL 과 거래소 PnL 은 부호까지 다를 수 있다.** 같은 청산이 pine_v2 gross `+1.09877350` vs 거래소 net `-1.09767393` 이었다(수수료 왕복 약 2.057, 손검산 일치, raw HMAC 오라클로 외부 확인). **같은 누적기에 넣지 마라.**
- ★**`leverage` 를 엔진에 넘기면 마진 게이트만 켜지는 게 아니다.** `is_leverage_active` 가 `check_liquidations` 도 함께 켜고, 그건 실제 reduce-only 주문을 내는 **머니-패스 동작**이다. 청산 모델은 isolated 전용이라 cross 계정에는 이르게 발동한다(BL-490).

- ★**조건부(트리거) 주문은 `submitted` 로 몇 시간씩 산다.** `orphan_scanner` 의 30분 stuck 판정과 watchdog 이 그것을 "terminal 증거 미수신" 으로 오판해 **30분마다 CRITICAL 알림이 영구 반복**된다. `list_stuck_submitted` 계열은 `trigger_price IS NULL` 로 면제해야 한다. 면제의 의미는 "미발동을 stuck 으로 보지 않는다" 이지 "추적하지 않는다" 가 아니다.
- ★**`OrderService.execute` 는 같은 `idempotency_key` 를 다시 보면 거래소로 dispatch 하지 않고 캐시 응답을 돌려준다**(`order_service.py:417-419`). 취소 후 같은 의도로 재등재할 때 키가 같으면 **거래소엔 아무것도 안 올라가는데 DB 와 metric 은 "등재됨" 이라고 보고**한다. 라이브 키가 `bar_time` 을 싣는 이유가 이것이다 — 재등재 가능한 키에는 bar 를 넣어라.
- ★**`Order.idempotency_key` 는 `VARCHAR(200)`.** 초과하면 `StringDataRightTruncation` 이 상위 `except` 에 삼켜져 "장전됐다고 믿는데 거래소엔 없는" 상태가 된다. 키에 값을 싣기 전에 길이를 검사해라. 그리고 **`datetime.isoformat()` 은 `:` 를 포함**하므로 `:` 로 split 하는 키 형식에 넣지 마라(epoch 초를 써라).
- ★**`except` 블록도 실패 경로다.** `session.rollback()` 이 ORM 객체를 expire 시킨 뒤 `logger.exception(extra={"id": str(obj.id)})` 를 하면 lazy refresh 가 동기 컨텍스트에서 IO 를 시도해 `MissingGreenlet` 으로 **에러 핸들러 자신이 크래시한다**. 루프 안 예외 처리가 필요하면 ORM 속성을 `try` **밖에서 미리 확보**해라.
- ★**bybit ccxt 는 `precisionMode = TICK_SIZE`** 라 `market["precision"]["amount"]` 는 소수 자릿수가 아니라 **스텝 크기**다(BTCUSDT 0.001). 단 `limits.amount.min` 과 항상 같지는 않다.
- ★**이미 돌파된 트리거는 거래소가 거부한다** — `retCode 110093`. 롱 stop 은 트리거가 > 현재가, 숏 stop 은 < 현재가여야 한다. pine_v2 는 `low <= stop` 을 즉시 체결로 보므로 이 지점에서 시뮬과 거래소가 갈린다.
- ★**codex 프롬프트의 "변경 파일 정확히 N개" 는 신규 작업 파일에만 걸어라.** 그 변경이 깨뜨리는 기존 테스트를 파일 수에 안 넣으면 codex 가 **질문하고 멈춘다**(실측: G7 첫 실행 0건 변경). "부수 정합성 수정은 승인된 것으로 간주" 를 함께 적어라.
- ★**변이가 실제로 의미를 바꾸는지 먼저 확인해라.** `x=None or (...)` 는 Python 에서 `(...)` 라 no-op 이고, 그걸 모르면 "테스트 구멍" 으로 오판한다.

## 거래소 실상 (2026-07-28 live-entry-parity, 실거래소 실측)

- ★★**ccxt 에서 `BTC/USDT` 는 perp 이 아니라 스팟이다.** linear perp 는 `BTC/USDT:USDT` 이고 변환기가 이미 있다(`providers.py` `_to_bybit_linear_symbol`). 실측:
  ```
  ccxt.market("BTC/USDT")      -> type=spot
  ccxt.market("BTC/USDT:USDT") -> type=swap, linear=True
  spot last=63561.2  perp last=63526.7  차이 34.50 USDT (0.0543%)
  ```
  **`fetch_ticker` 를 원문 심볼로 부르면 다른 자산의 가격을 읽는다.** 트리거 판정처럼 bp 단위가 중요한 곳에서는 신호보다 오차가 커진다(실측: 오차 0.054% vs 잡으려던 돌파폭 중앙값 0.025%).
- ★**ccxt ticker 에 `"mark"` 키는 없다.** mark price 는 `ticker["info"]["markPrice"]` 다. `ticker.get("mark")` 는 항상 `None` 이라 `fetch_mark_price` 는 도입 이래 늘 `last` 로 폴백해 왔다.
- ★**돌파 거절코드는 방향별로 다르다** — `110092` = "expect Rising"(**롱** stop), `110093` = "expect Falling"(**숏** stop). 한쪽만 allowlist 에 넣으면 절반을 놓친다.
- ★**`110017` 은 "포지션 0" 이 아니라 "reduce-only 규칙 위반"** 이다(ccxt 에러맵). "포지션 없음" 은 `110034` 다. 우리 원장의 옛 메시지만 보고 매핑하면 **포지션 반전 부작용이 "무해" 로 위장**된다(실측으로 재현됨 — `"reduce-only order has same side with current position"`).
- ★**Bybit demo 는 시장가 주문도 `create_order` 응답에서 `submitted` 로 준다.** 체결 확정은 WS 가 나중에 한다(`websocket/state_handler.py` · `reconciliation.py`). 따라서 "거래소가 수락했다" 를 `filled` 로만 세면 **그 카운터는 영구히 0** 이다.

## 원장을 읽을 때 (2026-07-30 close-mismatch-visibility)

- ★★★**`orders.filled_at` 은 이름과 달리 terminal_at 이다** — 체결뿐 아니라 **취소·거절 시각도**
  여기 들어간다(`models.py:293-296` 주석이 이미 그렇게 적었다). 그리고 **한 주문의 terminal 과
  다음 주문의 `created_at` 을 섞지 마라.** 실측 사고 — `0.058` 주문이 09:09:46 까지 살아 있다고
  적었는데 그건 **다음 주문의 생성 시각**이었고 실제 terminal 은 09:07:40 이었다(1m49s vs 3분).
- ★★**라이브 진입 key 는 형식이 둘이다.** 조건부 = `live:<sess>:cond:<bar_epoch>:<stop>:<qty>:<trade_id>`,
  시장가 = `live:<sess>:<bar_time ISO>:<seq>:<action>:<trade_id>`. `split_part` 로 한 형식만
  가정해 자르면 **다른 형식이 조용히 오분류**된다(실측: 21행을 `cond` 로 읽었는데
  `LIKE ':cond:%'` 카운트는 0이었다). **분해 결과를 쓰기 전에 원문을 한 번 출력해라.**
  귀속의 권위는 `conditional_entry_planner.parse_live_entry_key` **하나**다.
- ★★★**같은 에러 코드 안의 갈래가 위험도가 다르면 그 코드는 라벨이 될 수 없다.**
  `110017` 이 `same side`(★엔진↔거래소 **반대 방향**) 9건과 `current position is zero`(무해) 30건을
  한 라벨에 담고 있었다. **무해가 3배라 위험이 수적으로 묻혔고** counter 는 계속 "유령 포지션" 만
  가리켰다. 이 저장소가 `110017` 로 이 교훈을 **두 번째** 받은 것이다.
- ★★**`live_signal_events` 는 진입을 세지 않는다.** `entry`/`close` 시장가만 담고
  **조건부 진입은 거치지 않는다**. 그래서 `bool(new_events)` 로 만든 판정
  (`deferred_market_inflight`)은 stop-entry 전략에서 **사실상 「청산 tick 수」** 다.
  ★그 counter 는 `desired` 를 **읽기 전에** 오르므로 **미룰 진입이 0건이어도 발화한다.**
  **분모를 확인하지 않은 비중(예: "합의 75%")은 측정이 아니다.**

## 함대·계측 함정 (2026-07-31 reversal-ledger-sync)

- ★★★**`herdr agent prompt` 는 텍스트를 붙여넣기만 하고 제출하지 않을 수 있다.** 워커 4벌 전부
  `[Pasted text #1 +9 lines]` 상태로 프롬프트에 멈춰 있었는데 **발송 API 는 성공을 반환**했고
  `agent_prompt_stalled` 조차 안 났다. ⇒ **`herdr agent send-keys <name> enter` 를 항상 뒤에 붙이고
  `agent read` 로 눈으로 확인해라.** `working` 으로 바뀌는 것까지 봐야 발송이다.
- ★★★**psql boolean 을 판정에 쓰지 마라.** 감시 스크립트가 `f|*` 패턴으로 세션 사망을 놓쳐
  **3.7시간을 헛돌았다.** ★한동안 여기 「`-At` 가 `false` 로 찍는다」로 적혀 있었지만 **그게
  변수가 아니다** — 2026-08-01 실측: 같은 세션에서 맨 컬럼 `SELECT is_active` 는 **`t/f`**,
  캐스트 `SELECT is_active::text || …` 는 **`true/false`** 를 냈다. **가르는 건 플래그가 아니라
  캐스트다.** ⇒ 표기를 확인하는 게 아니라 **nullable 텍스트 컬럼**(`deactivated_reason` 등)으로
  판정해라. `tools/scripts/soak-observe.sh` 가 그 형태다.
- ★★**`psql -c` 에 세미콜론 여러 개는 암묵적 단일 트랜잭션**이라 뒤 문장의 실패가 앞 UPDATE 를
  통째로 롤백한다(2026-08-01 실측). **`-c` 하나에 문장 하나**로 써라. archive 에만 남아 있던
  것을 2026-08-03 에 승격했다.
- ★★**호스트 `/metrics` 는 워커의 카운터 증가를 곧바로 안 비춘다.** 2026-08-03 실측 — 워커가
  `close_position_flat` 을 올리고 태스크가 성공 반환한 뒤에도 호스트 HTTP 스크레이프는
  **14 를 두 번** 냈고, 같은 시각 컨테이너 안 multiproc 집계는 **15** 였다(잠시 뒤 호스트도 15).
  스크레이프 자체는 0.55초라 렌더 비용이 아니다 — [가정] macOS Docker bind-mount 의 mmap 전파
  지연. ⇒ **이벤트 직후 몇 초 안의 카운터 읽기로 판정하지 마라. 다시 읽어라.**
  일일 관측(하루 1회)에는 영향이 없다.
- ★★**짧은 창으로는 아무것도 판정할 수 없다.** 42분 창에서 **수정 없이도** `same_side` 0 이 나왔다
  (청산 시도 3). 그리고 4창 4.48h 동안 **청산 시도가 0건**이었다 — 이 전략은 전량 조건부 진입만 낸다.
  **판정 지표가 그 창에서 발화 가능한지를 먼저 확인해라.**
- ★★**`docker exec python -c` 는 러닝 워커가 리로드됐다는 증거가 아니다** — 새 프로세스가 마운트된
  소스를 읽을 뿐이다. **로그에서 그 코드가 실제로 실행된 흔적**을 봐라(태스크 received→succeeded).
- ★★**수정이 실주행에서 실행됐는지를 따로 재라.** 이번에 새 write-back 헬퍼가 최종 창에서
  **0회 발화**했다 — 기존 경로가 먼저 잡았다. **지표가 좋아진 것과 내 코드가 돈 것은 다른 사실이다.**
- ★**`python /tmp/x.py` 는 `sys.path[0]` 이 `/tmp` 다** — 컨테이너 안에서 앱 모듈을 쓰려면
  `docker exec -e PYTHONPATH=/app -w /app`.
- ★**`pnpm e2e` 는 자기 dev 서버를 띄우려다 죽는다** — 같은 디렉터리에 `next dev` 가 이미 떠 있으면
  `Another next dev server is already running`. **정체성 프로브 후 `PLAYWRIGHT_BASE_URL=http://localhost:3100`.**
- ★**`herdr pane split --ratio` 는 쪼개지는(기존) pane 이 *남기는* 비율이다**(폭 298 + `--ratio 0.25`
  → 75/223). n 등분은 `1/(남은 열 수)` 로 접는다.
- ★**두 워커가 같은 자리를 고치면 머지 충돌이 「의미 있는 충돌」이 된다** — 이번에 한 워커의
  훅 통합 헬퍼가 다른 워커의 훅을 몰라서, 손으로 접었으면 **codex 가 방금 잡은 결함을 머지에서
  재도입**할 뻔했다. **소유자에게 돌려줘라.**

## 계기(instrument) — 어떤 상품의 가격을 보고 있는가 (2026-07-28)

- ★★★**"같은 심볼" 이 같은 상품이라는 뜻이 아니다.** `ccxt` 인스턴스의 `defaultType` 이 심볼 해석을 바꾼다. 이 저장소에서 `BTC/USDT` 는 **스팟**, `BTC/USDT:USDT` 가 **무기한선물**이다. `market_data/providers/ccxt.py` 는 `defaultType: "spot"` 이고 `trading/providers.py` 의 `BybitFuturesProvider` 는 `"linear"` 다 — **두 모듈이 같은 문자열을 서로 다른 상품으로 읽는다.**
  - 그래서 라이브 엔진이 **스팟 봉을 재생하면서 perp 에 주문을 냈다**(BL-530). 실측 괴리는 **25~42 USDT (0.04~0.066%)** 로 지속적이고 **한쪽으로 치우친다** — 스팟이 위. 매수 스톱은 시뮬에서만 걸리고 매도 스톱은 거래소에서만 걸리는 **방향성 편향**이 된다.
  - 결정적 증거: 2026-07-28 08:06 UTC 스팟 고가가 **63541.7** 로 시뮬 스톱과 **소수점까지 일치**했는데 같은 분 perp 고가는 **63499.4**. 픽스처로 고정했다(`tests/fixtures/bybit_spot_vs_perp_bars.py`).
  - ★**BL-511 이 같은 결함을 가드 기준가에서 한 번 고쳤는데도 엔진 봉은 그대로였다.** 계기 정렬은 **한 사이트씩** 고쳐지므로, 가격을 읽는 새 코드를 쓸 때마다 _"이건 어느 상품인가"_ 를 되물어라. 실측 대조 1회(`category=spot` vs `category=linear` kline)면 끝난다.
- ★**시뮬 포지션과 거래소 포지션은 자동으로 수렴하지 않는다.** `run_live` 는 OHLCV 재생만 하고 거래소 포지션을 **입력으로 받지 않는다**. 진입이 라이브에서 유실되면 그 유령 포지션은 영원히 남고, 이후 close 는 전부 거절된다(`110017 current position is zero`). 방향까지 어긋나면 `reduce_only=True` 하나가 **반대 방향 포지션 증가**를 막는 유일한 방벽이다.
  - 관측 지점 = `qb_live_position_divergence_total{category}` + `qb_live_signal_divergence_total{stage="position"}`. 진단 SQL 은 [`live-close-diagnostics.md`](../operations/live-close-diagnostics.md).
