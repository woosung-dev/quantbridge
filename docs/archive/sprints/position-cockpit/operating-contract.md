<!-- position-cockpit 운영 계약 델타 — 신규 계약/운영 변경만. 전체 배경은 context-notes.md + ~/.claude/plans/quantbridge-position-cockpit-handoff.md -->

# position-cockpit 운영 계약 (델타)

## 신규 계약

### P1 — realtime `position_update` envelope
- 채널 `qb:rt:user:{user_id}`(DB user UUID, order/ticker 와 동일).
- `{ v:1, type:"position_update", ts:<epoch-ms>, payload:{ symbol:<Bybit raw, to_bybit_raw_symbol>, side:"long"|"short"|"flat", size:<Decimal str> } }`.
- **invalidate 힌트 전용** — FE 는 값으로 setQueryData 금지. 3-site 등재 의무(schemas Literal + PAYLOAD_MODELS + realtime_publisher cast) — 누락 시 manager.py 재검증에서 silent drop.

### P2 — `GET /api/v1/exchange-accounts/{account_id}/balance`
- `{ account_id, asset:"USDT", supported:bool, reason:str|null, total:str|null, free:str|null, fetched_at:datetime|null }`.
- 404 비소유/미존재 / 503 ProviderError / 비-Bybit → supported:false 200. Redis `qb_balance_snapshot:{account_id}` TTL 15s.
- **total/free = CCXT USDT coin total/free**(account-level totalEquity 아님). supported:true 라도 null 가능.

## 운영 변경

- **WS position 채널**: `_stream_main` 이 `topics=("order","position")` + `message_handler=PrivateTopicRouter`(handler= 제거). PositionFanoutHandler = DEL-before-debounce + 활성 세션 없으면 no-op. 신규 celery 태스크 없음(기존 run_bybit_private_stream 재사용).
- **코크핏 IA**: §01 현황 / **§02 계좌 잔고**(활성 세션 계정만) / **§03 세션별 열린 포지션** / §04 리스크가드 / §05 주문원장 / §06 거래소계좌 / §07 라이브세션 / §08 진단(포지션 카드 제거, 알림규칙+스트림 2카드).
- 마이그레이션 0(비영속). alembic 무변경.

## 운영 레시피 (dogfood/디버깅)

- BE pytest = **3-env 전체**(DATABASE_URL + TEST_DATABASE_URL + TEST_REDIS_LOCK_URL). 게이트 = ruff check + mypy + pytest(BE) / typecheck + test + lint(FE). ruff format 은 게이트 아님.
- ws-stream 새 코드 강제 = `docker restart quantbridge-ws-stream`(reconciler 300s 후 스트림 재기동). sentinel = 컨테이너 안 `from src.trading.websocket.position_fanout import PrivateTopicRouter`.
- 세션 활성화(안전창) = `is_active=true, last_evaluated_bar_time=now()+2h`. 독립 오라클 = Fernet 복호화 + raw HMAC(api-demo.bybit.com). 실시간 프레임 관찰 = `redis-cli PSUBSCRIBE 'qb:rt:user:*'`.
