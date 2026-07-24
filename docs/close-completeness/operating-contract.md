<!-- close-completeness 운영 계약 델타 — 신규/변경 계약만. 전체 배경 = context-notes.md + ~/.claude/plans/glimmering-noodling-sunrise.md -->

# close-completeness 운영 계약 (델타)

> trading-surface-pack(#473) 후속. 청산/TP-SL 완성도 3건 — B1 즉시 flat · B2 청산 margin_mode 503 회피 · B3 완전 TP/SL 보고(display). **비영속, 마이그레이션 0.** codex G0 = REJECT → 전건 코드 대조 검증 후 개정. 사용자 재인터뷰 = 스윕 후속 BL 이연 + 트레일링 각주 표기만.

## 변경 계약

### C-TPSL-PLURAL — §03 포지션 TP/SL = 병합 가격 리스트 (breaking, 내부 FE-only 소비)

- `ExchangePositionSchema`(BE `trading/schemas.py` + FE `features/live-sessions/schemas.ts`): `take_profit_price: str|None` / `stop_loss_price: str|None`(singular) **→ `take_profit_prices: list[str]` / `stop_loss_prices: list[str]`** + **`has_trailing_stop: bool`**. 빈 리스트 = 표시 `—`.
- 병합 규칙(read-time, position_service): 포지션별 = [Full 포지션-부착값(있으면)] + [조건부 주문 중 reduce_only ∧ side==reducing_side(long→sell/short→buy) ∧ positionIdx 일치인 kind=tp/sl 의 price(없으면 trigger_price)]. **source-dedup**(조건부값이 Full 값과 같으면 제외, Decimal 비교). 정렬 = Full 값 앞 → 나머지 마크가 근접순. `str(Decimal)` 출력.
- `has_trailing_stop` = position `trailingStop`(거리) 존재 **또는** belonging 조건부 주문 중 kind=trail 존재(codex 최종 P1). 트레일링 거리는 가격 열에 미표시(각주로만).
- 유일 producer = `position_service.py get_reconciliation`. 유일 consumer = FE `open-positions-table`. WS position 채널은 이 shape 미생성.

### C-COND — 신규 조건부 주문 조회 (read-time, provider)

- `BybitFuturesProvider.fetch_open_conditional_orders(creds, symbol) -> list[ConditionalOrderSnapshot]`. `ConditionalOrderSnapshot(order_id, side, kind, price, trigger_price, qty, reduce_only, position_idx)`.
- **2회 호출 union + orderId dedupe**: `fetch_open_orders(sym, params={"category":"linear","paginate":True})` + `params={"category":"linear","trigger":True,"paginate":True}`. Bybit 기본 호출이 StopOrder 도 포함해 두 호출이 겹치므로 orderId 로 dedupe(오라클 대조로 실증 — 동일 2건이 count=2 로 병합). `params=` 키워드 필수(2번째 positional=since).
- **분류 = Bybit v5 `stopOrderType` 엄격**: TakeProfit/PartialTakeProfit→tp, StopLoss/PartialStopLoss→sl, TrailingStop→trail, 그외(Stop/공백 등)→other(TP/SL 표시 제외). reduce_only=True 만 반환.
- `PositionSnapshot` += `position_idx: int|None`, `trailing_stop: Decimal|None`(fetch_open_positions info 파싱, 0→None).

### C-CLOSE-MARGIN — 청산 create_order 는 margin/leverage 재설정 생략 (B2, 503 회피)

- `BybitFuturesProvider.create_order`: `set_margin_mode`+`set_leverage` 를 **`if not order.reduce_only:`** 로 감쌈. reduce-only 주문은 기존 포지션의 leverage/margin 을 그대로 사용 → 잘못된 값 재설정으로 인한 BadRequest(503) 회피. ccxt `marginMode` 신뢰성 문제(Bybit v5 tradeMode deprecated) 자체를 우회. fast-fail(leverage/margin_mode None) 불변. `reduce_only` 는 Order 영속·OrderSubmit 운반 → 마이그레이션 불요.

### C-FLAT-DEL — 청산 즉시 flat = post-fill 캐시 DEL (B1)

- 청산은 async Celery dispatch → accept 시점 DEL 은 무효. **`tasks/trading.py _execute_with_session` 의 동기 fill 승자 경로**(`order.reduce_only` 시)에서 그 account 의 활성 세션들(`list_active_by_account`) 포지션 캐시(`position_snapshot_cache_key`)를 best-effort DEL. WS fanout(`position_fanout.py:74`)과 독립으로 no-WS 창 커버. over-DEL 무해(cache-miss→fresh). SSOT 키 헬퍼 `position_snapshot_cache_key(session_id)` 를 3곳(position_service:169 / position_fanout:74 / task DEL) 공유.
- 정직 한계: Bybit async settle 잔존. 단 캐시가 완료된 fill 을 더는 가리지 않음(dogfood 에서 close 후 redis 키 부재·flat 실증).

### C-HEDGE — hedge positionIdx 청산 차단 (방어)

- `close_service`: `position = positions[0]` 후 `position.position_idx not in (0, None)` → **409 hedge_unsupported**. fetch_open_positions 가 zero-size leg 를 버려 1-leg hedge 가 통과할 수 있으나 close 주문이 positionIdx 미전달이라 차단(codex G0).

## 이연 (후속 BL)

- **청산 스윕**(청산 후 잔여 reduce-only 조건부 주문 자동취소) = **후속 BL**. codex G0 이 2 BLOCKING 발견 — (1) 타이밍(accept≠fill, 체결 전 스윕 시 보호주문 조기 취소) (2) account+symbol 공유 세션의 타 세션 주문 오취소(세션 귀속 orderLinkId 매핑 필요). 안전 구현 = post-fill flat 확인 + orderLinkId 세션 스코핑. **dogfood 실측: 포지션-부착 Partial 조건부 TP/SL 은 Bybit flat 시 자동취소(close 후 orders count=0)** → 이연 안전성 확인.
- 트레일링 별도 표시(거리값 열/배지) = 각주로 충족, 필요 시 후속.

## 운영 레시피 (dogfood/디버깅 — trading-surface-pack 상속 + 신규)

- BE pytest = **3-env 전체**(DATABASE_URL + TEST_DATABASE_URL …5436/quantbridge_test + TEST_REDIS_LOCK_URL …6380/3). 게이트 = ruff check + mypy + pytest(BE) / tsc + test + lint(FE). ruff format 은 게이트 아님.
- **★docker db/redis 포트 오버레이 함정**: 이 스택은 db 5436·redis 6380 **커스텀 오버레이**(base compose 는 5432/6379 하드코딩). `docker compose up -d <svc>`(plain) 은 db/redis 를 재생성해 오버레이를 **base 포트로 되돌린다**(볼륨은 보존). worker 만 재빌드하려면 `docker compose up -d --build --no-deps backend-worker`. 복구 = `docker compose -f docker-compose.yml -f <port-override(5436/6380 !override)> up -d db redis`.
- 독립 오라클 = `bybit_oracle.py`(Fernet MultiFernet 복호화 + api-demo.bybit.com raw HMAC: GET/POST sign=HMAC(secret, ts+key+recv+query|body)). trading. 스키마 prefix. POST 로 조건부 주문 셋업(place market / set-trading-stop tpslMode=Partial / cancel-all).
- 앱 provider 대조 = `app_provider_check.py`(실 creds 로 `fetch_open_conditional_orders`/`fetch_open_positions` 직접 호출 → 오라클 raw 와 대조). BE end-to-end = `dogfood_be.py`(실 DI 로 `get_reconciliation` → 병합 리스트 확인).
- authed dogfood spec = chromium-authed testMatch **열거식**(파일명 등재 안 하면 미발견). 신선 JWT = global.setup(Clerk 로그인) → storageState.
