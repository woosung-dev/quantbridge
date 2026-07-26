<!-- trading-surface-pack 운영 계약 델타 — 신규 계약/운영 변경만. 전체 배경 = context-notes.md + ~/.claude/plans/quantbridge-trading-surface-pack-handoff.md -->

# trading-surface-pack 운영 계약 (델타)

> position-cockpit(#472) 후속. 코크핏 §03 포지션 표에 TP/SL 열 + reduce-only 시장가 청산을 완성하고, 소형 부채 4건(BL-416/425/432/433) 청소. **비영속, 마이그레이션 0.**

## 신규 계약

### P-TPSL — 거래소 보고 포지션-부착 TP/SL (read-time, 신규 조회 API 0)

- `ExchangePosition`(BE `trading/schemas.py` `ExchangePositionSchema` + FE `features/live-sessions/schemas.ts`) += `take_profit_price: str|null`, `stop_loss_price: str|null`.
- `PositionSnapshot`(providers.py) += 2필드(`Decimal|None`). `fetch_open_positions` 가 ccxt `takeProfitPrice`/`stopLossPrice` 를 읽고 **`0`/`'0'`/`''`/None → None 정규화**(0 을 실 TP 로 오독 방지).
- **정직 한계:** QB 는 limit-TP 를 tpslMode=Partial 조건부 주문(포지션 필드 아님)으로 부착 → 포지션 필드는 Full-mode SL + set-trading-stop 트레일링만 반영. FE 각주 = "거래소가 포지션에 보고한 TP/SL만 표시 (별도 조건부 주문으로 건 TP/SL은 포함되지 않을 수 있습니다)". Full 보고(fetch_open_orders 조인)는 후속 BL.

### P-CLOSE — reduce-only 시장가 청산 (신규 인증 엔드포인트)

- `POST /api/v1/live-sessions/{session_id}/positions/close` → **202** + `ClosePositionResponse { order_id, state, detail }`(OrderResponse 재사용 아님 — 그건 `id` 필드라 불일치).
- 흐름(신규 `trading/services/close_service.py`, deps = PositionService 미러 + OrderService): ownership(session.user_id==current_user.id, 미소유/계정부재 **404**) → `validate_strategy_settings`(canonical, `strategy/schemas.py:122`) 로 검증(None→**422** settings_unset / ValidationError→**422** settings_invalid) + demo·bybit 한정(else 422) → `fetch_open_positions` 재조회(0→**409** no_open_position / **>1 hedge leg→409** hedge_unsupported / 1→진행) → 반대 side reduce_only market OrderRequest(qty=포지션 size, **leverage=int(validated.leverage)** 필수 — 라우팅이 `(bybit,demo,has_leverage=True)`→BybitFuturesProvider, False→spot) → `OrderService.execute(req, flatten=True)`.
- **503** ProviderError. **demo 만.** 멱등 = 재조회-409(FE pending disabled 병행, pending-락 없음 — 사용자 확정).

### P-METRIC — WS subscribe negative-ack counter

- `qb_ws_subscribe_rejected_total{account_id}` Counter(`common/metrics.py`) — `position_fanout.py` PrivateTopicRouter reject 지점에서 `.labels(account_id=str(...)).inc()`.

## 운영 변경

- **OrderService.execute `flatten` 플래그**: `flatten=True` 는 진입-위험 가드 ②leverage-cap ③risk-sizing ④min-notional ⑤max-notional ⑥balance-unverified ⑦trading-sessions ⑧kill-switch 를 우회하되 ①ownership + dispatch_snapshot + idempotency + INSERT + commit + dispatch 는 유지. **안전 불변식**: `flatten=True and not req.reduce_only` → `ValueError` raise(진입 주문에서 가드 탈취 금지). default `flatten=False` = 전 기존 콜러 회귀 0.
- **코크핏 §03**: TP/SL(익절/손절) 2열 + 청산 액션열(colSpan 11→14). 청산 = 확인 모달(reduce-only 시장가·계정 단위 순 포지션·활성 세션 재진입 가능 정직 고지) + pending 행별 disabled. demo 계정 세션만 청산 어포던스.
- **flat 반영**: 청산 202 후 §03 빈복귀는 기존 WS position_update(fast) + 15s 폴링(fallback)이 담당(사용자 확정 = 비동기 202). WS 미연결 창에선 폴링 지연(~15-30s) — 후속 BL(청산 시 캐시 DEL 로 fast 폴 독립) 후보.
- **BL-416**: 주문취소 행별 disabled(`cancelOrder.variables===o.id`) + 비-409 broad toast. **BL-425**: alert-rule 중복 유형 사전검사(마운트된 `rules.data.items` 재사용, 새 fetch·409 요청 회피, broad 콘솔 allowlist 부활 없음). **BL-432**: positions select→combine 인덱스 zip(고아 `makePositionsSelector`/`LiveSessionPositionQueryData` 삭제).
- 마이그레이션 0(신규 영속 컬럼 없음 — PositionSnapshot=dataclass, ClosePositionResponse=Pydantic). alembic 무변경.

## 운영 레시피 (dogfood/디버깅)

- BE pytest = **3-env 전체**(DATABASE_URL + TEST_DATABASE_URL(…5436/quantbridge_test) + TEST_REDIS_LOCK_URL(…6380/3)). 게이트 = ruff check + mypy + pytest(BE) / typecheck + test + lint(FE). ruff format 은 게이트 아님.
- FE=3100(3000=nexus-core 점유), BE=8100(로컬 uvicorn --reload, main repo). db 5436·redis 6380.
- 독립 오라클 = `bybit_oracle.py`(Fernet MultiFernet 복호화 + api-demo.bybit.com raw HMAC: sign=HMAC(secret, ts+key+recv+query|body)). trading 스키마 prefix 의무.
- 세션 활성화(안전창) = `is_active=true, last_evaluated_bar_time=now()+2h`. 신선 JWT = playwright storageState 컨텍스트 → `Clerk.session.getToken()`. authed e2e = `PLAYWRIGHT_BASE_URL=http://localhost:3100`.
