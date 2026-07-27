# live-conditional-hardening — 컨텍스트 노트

> 작업 중 내린 결정과 그 근거를 계속 덧붙인다. 커밋하지 않는다.

## D0 — preflight 이 킥오프 전제 2건을 반박했다 (2026-07-27)

- **BL-499 는 원장에 흔적이 없다.** 조건부 진입 주문 31건 중 취소 16건이 **전부 `exchange_order_id` 를 보유**한다. 즉 DB-only 취소 경로(`transition_pending_to_cancelled`)가 **성공한 적은 0건**이다. 48h 워커 로그에도 `cancel_failed` 0 · `concurrent_transition_submitted` 0. ★**아래 D5 #8 로 정정** — 이 관측은 "호출된 적 없다" 를 증명하지 못한다. 패배한 호출은 행에 아무것도 안 쓰기 때문이다.
- **BL-500 도 실측이 아니라 가설이다.** stuck 형태(`submitted` 인데 거래소 부재) 후보 행이 지금 0건이다.
- 따라서 두 건은 "관측된 고장 수리" 가 아니라 **"증명 가능한 구멍 봉인"** 이다. 문서에 그대로 쓴다. 자가 치유가 확인된 결함을 사고처럼 쓰지 않는다.

## D1 — BL-498 이 실측으로 오히려 작아졌다

`ClosePositionService.close_position` 은 세션 `is_active` 를 **요구하지 않는다**. 즉 비활성 세션 id 로도 청산이 된다. 막혀 있던 건 **화면이 활성 세션만 순회**하는 것뿐이었다.

→ 신규 청산 경로를 만들지 않는다. **계정 스코프 읽기 엔드포인트 1개 + 화면**이면 닫힌다. 청산은 기존 `POST /live-sessions/{id}/positions/close` 를 그대로 재사용한다.

## D2 — 계정 전체 포지션은 1콜로 된다

설치된 ccxt 소스 확인 — `bybit.fetch_positions(symbols=None)` 는 `defaultType=linear` 에서 `settleCoin` 을 `USDT` 로 채우고 `category=linear`, `limit=200` 으로 `privateGetV5PositionList` 를 부른다. 심볼 인자가 없어도 계정 전체가 온다.

한계 — `settleCoin` 기본이 `USDT` 라 **USDC 정산 linear 는 안 잡힌다.** MVP 는 USDT 로 한정하고 그 사실을 응답·화면 각주에 쓴다.

## D3 — 사용자 결정 2건

1. **BL-499 = 패자 경로 정의(마이그레이션 0).** 경합을 이기려 하지 않는다. `cancel_requested_at` 컬럼은 창을 줄일 뿐 닫지 못하는데 스키마 비용을 쓴다.
2. **BL-498 청산 귀속 = 세션 있는 심볼만.** `Order.strategy_id` 가 NOT NULL FK 라 귀속 없이는 원장에 기록할 수 없다. 세션이 없던 심볼은 행은 보여주되 청산 버튼 대신 사유를 표기한다 — 보이지 않던 노출이 최소한 보이게는 된다.

## D4 — ★BL-500 "유령 행 종결" 은 (a)도 (b)도 아니다. 우리가 할 일이 아니다

플랜은 유령 행(`submitted` 인데 거래소 부재)의 상태 전이를 (b) `fetch_order_status_task` 위임으로 잡고, 안 되면 (a) 즉시 `transition_to_cancelled` 로 내려가라고 했다. **둘 다 기각한다.**

- **(b) 기각 — 계약이 안 맞는다.** `_fetch_order_status_with_session` 은 `state==submitted` + `exchange_order_id` 조건을 통과시키므로 진입은 한다. 그런데 그게 부르는 `_bybit_fetch_order_impl:1827` 은 ccxt `fetch_order(id, symbol, params={"acknowledged": True})` 이고, ccxt bybit `fetch_order` 는 **`params['trigger']` 가 True 일 때만 `orderFilter='StopOrder'`** 를 붙인다. 우리는 그걸 안 보낸다. 게다가 `/v5/order/realtime` 은 이미 사라진 주문에 `OrderNotFound` 를 던지고, 우리 impl 이 그걸 `ProviderError` 로 감싸 watchdog 이 **재시도 → max attempts → CRITICAL alert** 로 간다. 유령을 무음에서 **영구 오경보**로 바꿀 뿐이다.
- **(a) 기각 — 원장이 거짓이 된다.** 거래소 open-order 에 없는 이유가 "취소" 가 아니라 **"방금 체결"** 일 수 있다. WS 를 놓친 상태에서 우리가 `cancelled` 로 적으면 체결을 취소로 기록한다.
- **★진짜 권한자는 이미 있다.** `src/trading/websocket/reconciliation.py` 의 `Reconciler` 가 로컬 `pending`/`submitted` 를 `fetch_open_orders ∪ fetch_recent_orders` 와 대조해 **terminal evidence 가 명시적일 때만** 전이하고, 증거가 없으면 상태를 유지한 채 Slack alert + `qb_ws_reconcile_unknown_total` 을 올린다(파일 헤더 §"terminal evidence 만 state transition"). 체결과 취소를 구분할 수 있는 유일한 컴포넌트다.

→ **우리는 `actual` 에서 제거하고 발산을 보고하는 것까지만 한다.** 이게 BL-500 본문의 권장 접근 그대로이고, 상태 전이는 원래 우리 책임이 아니었다. 한계(유령 행이 WS 재연결 reconcile 까지 `submitted` 로 남고 매 tick 발산 로그를 낸다)는 dev-log 에 쓴다.

★**정정 (G0.5 codex #6) — (b) 를 기각한 내 근거는 틀렸다.** 나는 "ccxt 가 `trigger=True` 일 때만 `orderFilter=StopOrder` 를 붙이므로 조건부 주문을 못 찾는다" 고 했다. 그런데 Bybit v5 `/v5/order/realtime` 은 `orderFilter` 미전달 시 **모든 타입을 반환**하고, watchdog 도 주문 타입을 제한하지 않는다(`tasks/trading.py:664-721`). 즉 (b) 는 "계약 불일치" 로 기각될 수 없었다. **결론(전이는 우리 책임이 아니다)은 유지하되 근거를 바꾼다** — watchdog 은 최대 3회 재시도라 오래된 유령 행의 종결을 보장하지 않고, 무엇보다 비동기 태스크를 걸어도 **같은 tick 의 재등재가 안전해지지 않는다**. 종결 권한은 terminal evidence 를 요구하는 `Reconciler` 에 남는다.

★**"제거하면 재등재돼서 이중 포지션이 되지 않나" 는 `target_position` 계약이 이미 막는다.** 계획기는 delta 가 아니라 체결 후 순 포지션을 받고, 같은 tick 의 `fetch_open_positions` 로 `current_position` 을 읽는다(`live_signal.py:387`). 유령이 실제로 체결됐다면 그 포지션이 `current_position` 에 잡혀 대체 주문 수량이 그만큼 깎인다. 이 성질을 테스트로 고정한다.

## D5 — G0.5 codex 검증 판정 (8건 전건 재현 판정)

★**액면 수용하지 않고 코드로 재현했다.** 6건 반영 / 1건 이미 반영돼 있었음 / 1건 부분 기각.

### ★★#8 반영 — 내 preflight 추론이 틀렸다

나는 "취소된 16건이 **전부** `exchange_order_id` 를 보유하므로 `transition_pending_to_cancelled` 경로는 미주행" 이라고 결론냈다. **성립하지 않는다.** 경합에 **패배한** 호출은 `rowcount=0` 이라 행에 아무것도 안 쓴다. 그 뒤 dispatch 가 `exchange_order_id` 를 붙이고(`tasks/trading.py:518-526`) 다음 tick 이 거래소 취소로 마무리하면 **최종 행은 정확히 그 16건과 같은 모습**이 된다. 즉 그 관측은 패배 경합과 양립한다.

→ 내가 실제로 증명한 것은 **"DB-only 취소 _성공_ 0건"** 뿐이다. 호출·패배 여부는 별도 metric 이 있어야 알 수 있고, 이번에 그 metric(`stage="cancel_raced"`)을 넣는 이유가 바로 이것이다. 48h 로그의 `cancel_failed` 0 건은 여전히 "관측된 패배 0" 의 증거로 유효하다(패배는 오늘 `RuntimeError` 를 남기므로).

### #4 반영 — 경합 패배 후 같은 tick 에 등재하면 안 된다

플랜은 패배 시 `cancel_failed` 를 세우지 않고 **루프를 계속**하게 했다. 그런데 현행 코드의 `try/except` 는 취소 루프 **안**에 있어 남은 취소는 이미 계속 돈다(`live_signal.py:437-471`). 내 변경의 실제 델타는 **`to_place` 진행 여부 하나뿐**이었고, 그건 위험하다 — `current_position` 은 취소 루프보다 **먼저**(`:387`) 찍힌 스냅샷이라 패배한 주문이 그 사이 체결되면 낡은 포지션으로 신규 등재를 낸다.

→ **패배해도 `to_place` 는 건너뛴다(fail-closed 유지).** 이번 작업의 값은 "무해한 등재를 살린다" 가 아니라 **패배와 진짜 실패를 구분해 관측 가능하게 만드는 것**이다. `logger.exception` 스택과 `stage="cancel"` 오류 metric 을 진짜 실패에만 남긴다.

### #7 반영 — BL-499 는 Resolved 가 아니다

백로그 본문은 취소 의도 영속 또는 dispatch 시점 재검사를 요구한다. 사용자 결정(마이그레이션 0)은 그 근본 경합을 남기므로 **partial mitigation 으로만 기록**한다.

### #5 반영 (설계 변경) — "부재" 와 "체결 전파 중" 을 같은 tick 에 동치로 보지 않는다

거래소 주문 조회(`:320`)와 포지션 조회(`:387`)는 원자적 스냅샷이 아니다. 방금 트리거된 주문은 open-order 에서 먼저 사라지고 포지션에는 늦게 뜬다.

→ **`submitted_at` 나이 게이트**를 둔다. 거래소에 없고 `exchange_order_id` 가 있으며 **`submitted` 상태로 충분히 오래된** 행만 제거한다. BL-500 이 말하는 해악은 **영구** no-op 이므로 나이가 정확히 그 판별자다. 몇 초짜리 전파 지연은 게이트에 걸려 그대로 남는다. Redis 마커나 새 컬럼 없이 이미 있는 데이터로 판별한다.

### #1 반영 — hedge / `position_idx != 0` 행에 청산 버튼을 주면 안 된다

`close_service.py:66-71` 은 leg 2개 이상이거나 `position_idx not in (0, None)` 이면 `409 hedge_unsupported` 다. 계정 표가 그 행에 버튼을 주면 **누르면 실패하는 버튼**이다.

→ 청산 가능 판정을 **서버에서** 계산한다. 심볼당 leg 2개 이상이거나 `position_idx` 가 0/None 이 아니면 `closable_session_id=None` + `close_blocked_reason="hedge_unsupported"`.

★codex 의 "역정규화가 `BTC/USD:BTC` 를 `BTC/USD` 로 뭉갠다" 는 **내 구현에는 해당 없다**(플랜만 보고 낸 지적). `_from_bybit_linear_symbol` 은 settle 이 quote 와 다르면 원문을 그대로 반환한다. 애초에 `category=linear` 조회라 inverse 는 오지도 않는다.

### #2 반영(축소) — 세션 조회에 `user_id` 를 넣는다

계정은 이미 소유 검증을 통과했지만 `LiveSignalSession.user_id` 와 `exchange_account_id` 가 같은 소유자라는 DB 제약은 없다. 방어는 1줄이므로 넣는다. 다만 "실제 주문 연결로 귀속 증명" 은 사용자 결정(최신 세션 귀속)을 뒤집는 별도 설계라 넣지 않고 한계로 고지한다.

### #3 절반은 이미 반영돼 있었다

캐시 무효화 — `accountPositions` 키를 `positionsPrefix` **아래**에 두었으므로 `useClosePosition` 의 기존 invalidate 가 두 표를 함께 무효화한다(플랜 이후 구현에서 반영). 남은 것은 두 표의 청산 버튼 **동시 클릭**이고, 두 번째 reduce-only 주문은 평탄해진 포지션에서 거래소가 거부하므로 손실이 아니라 원장 잡음이다. 공유 lock 을 값싸게 넣을 수 있으면 넣고 아니면 BL 로 등재한다.
