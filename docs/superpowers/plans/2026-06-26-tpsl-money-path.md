# TP/SL Money-Path (Wave 2 W-A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 라이브 exit 주문(SL/Trail trigger market)이 Bybit v5 에서 올바른 방향으로 트리거되도록 `triggerDirection` + OCO 그룹 식별자 + 네이티브 trailing param 을 ccxt 4.5.49 소스 정합 shape 로 주입하고, 주문 경로(schema→service→task→provider) 전체에 배선한다. 자본×리스크% 기반 서버 권위 사이징(P2)을 추가한다.

**Architecture:** Wave 1 이 깔아둔 `_merge_exit_params` 단일 주입점 + `OrderSubmit`/`Order`/`OrderRequest` exit 필드를 확장한다. 신규 enum 0 — `OrderType`(market|limit) 유지, 트리거 주문도 `type=market` + params. `Order` 신규 컬럼은 **ADD COLUMN alembic**(downgrade DROP COLUMN). triggerDirection 계산은 `exit_order_mapping` 의 순수함수로 추가(테스트 가능). OCO sibling-cancel 오케스트레이션과 라이브 exit-level 추출은 disjoint 계약 밖(다른 워커/Phase 3) → 정직 defer.

**Tech Stack:** Python 3.12, ccxt 4.5.49 (async), SQLModel/SQLAlchemy, alembic, pytest-asyncio, asyncpg/PostgreSQL.

## Global Constraints

- demo-only / 실자금 0. `BybitLiveProvider` stub 절대 활성화 X. 검증 = 단위 test(mocked ccxt) — 실 거래소 round-trip 은 demo API 키 부재로 이 스프린트 범위 밖(정직 고지).
- 금융 숫자 Decimal(float 금지). str(Decimal) 로 ccxt 주입.
- 신규 enum 0. `OrderType` swap 금지. Order 신규 컬럼 = ADD COLUMN(up→down→up round-trip).
- 단일 주입점 = `providers.py _merge_exit_params`. 값 None/False → 키 미포함 = entry 경로 byte-identical 회귀.
- 계약 재사용: `exit_orders`(ExitOrderKind/fill_type_for) + `exit_order_mapping`(map_exit_kind) import 재사용, 중복 정의 금지.
- 신규 테스트는 반드시 `async def`+`await`(pytest-asyncio). `asyncio.get_event_loop().run_until_complete()` 금지(CI event-loop 함정).
- disjoint 편집 허용: `trading/{providers,models,schemas,order_service,exceptions}.py` + `tasks/{live_signal,trading}.py` + `strategy/pine_v2/exit_order_mapping.py` + alembic 1건 + `tests/{trading,tasks}/`. router/liquidation/backtest/strategy_state/repositories 편집 금지.
- 커밋 trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## ★ Grounding Spike 결론 (footnote, 0a)

라이브 평가 경로 `evaluate_live_signals_task`(`tasks/live_signal.py`)는 exit intent(TP/SL 레벨)를 **노출하지 않는다**.

1. **exit 레벨 source = `StrategyState.pending_exits`** (`strategy_state.py:63-137` `ExitOrder` legs: `stop_price`/`limit_price`/`trail_offset`/`from_entry`/`kind`). entry 가 `strategy.exit(...)` 선언 시 생성.
2. **그러나 `to_report()`(`strategy_state.py:693`)는 `pending_exits` 를 미노출** — `strategy_state_report` 에 없음. `LiveSignal`/`LiveSignalResult`(`event_loop.py:176-203`)도 exit 레벨 미운반. `live_signal.py:681-695` OrderRequest 는 `take_profit/stop_loss/trigger_price` 를 채우지 않음(현 상태 확인).
3. **레벨 surfacing 은 `event_loop.py`(run_live) / `strategy_state.py`(to_report) 편집 필요 = disjoint 계약 밖**(strategy_state.py 명시 금지). → **honesty gate 발동**: 라이브 exit-level 추출(신호생성 경로 변경)은 **defer**(strategy-state 워커 / Phase 3).
4. **현 라이브 TP/SL 동작**: `run_live` warmup replay 가 백테스트 sim 으로 exit 를 bar 단위 체결(`try_fill_exit`) → "close" TradeEvent → market reduce-only 주문. 즉 TP/SL 이 **virtual**(1분 폴링 간 미보호). Wave 2 가 닫으려는 갭.
5. **OCO sibling-cancel** 은 `OrderRepository.list_by_oco_group` 필요 = repositories 편집 = 계약 밖 → **defer**. `oco_group_id` 컬럼은 app-side 추적용으로 추가하되 ccxt param 으로 주입 X(Bybit linear 네이티브 OCO 그룹 param 부재).

**따라서 P0 = placement 배관 + ccxt-correct triggerDirection/trailing + 단위 test.** 라이브 feed(레벨 추출) 와 OCO 취소 오케스트레이션은 PR 본문에 명시 defer.

## ★ ccxt 4.5.49 소스 정합 (bybit.py `create_order_request`)

- **triggerDirection**(line 4106-4116): standalone 트리거 주문(`triggerPrice` in params, type=market) 은 **linear/contract 에서 필수**. `safe_string(params,'triggerDirection')` → `'ascending'|'above'|'1'` → request 1(가격 RISE 시 트리거), 그 외 → 2(FALL 시). **spot 은 triggerDirection 미지원**(line 4109-4111). → `params['triggerDirection'] = str(order.trigger_direction)` (1|2). '1'→1, '2'→2 검증됨.
- **bracket TP/SL**(line 4126-4156): `params['stopLoss']={"triggerPrice":str}` / `params['takeProfit']={"triggerPrice":str}` (safe_value_2 triggerPrice/stopPrice). Wave 1 shape 정확. position 에 attach(Bybit 네이티브 bracket) — triggerDirection 불필요(side 추론). spot market+attached SL → InvalidOrder(linear 만).
- **trailingStop**(line 3960-3962, 4102-4105): `trailingAmount = safe_string_2(params,'trailingAmount','trailingStop')` → `isTrailingOrder` → `request['trailingStop']=trailingAmount`. **contract 만**(line 3898). → `params['trailingStop'] = str(order.trailing_stop)` (Bybit futures).
- **OKX**(okx.py): `triggerDirection` 개념 없음(slTriggerPx/tpTriggerPx 가 트리거가로 방향 추론). → triggerDirection/trailingStop 은 **Bybit 전용**, OKX 미주입.
- **triggerDirection 방향 규칙**(ccxt attached SL/TP line 4119-4122 와 정합): exit 주문 side 기준 — closing-long(sell) SL=2(FALL)/TP=1(RISE), closing-short(buy) SL=1(RISE)/TP=2(FALL).

---

## File Structure

- `backend/src/strategy/pine_v2/exit_order_mapping.py` — `trigger_direction_for(exit_side, kind)` 순수함수 추가(triggerDirection 계산 SSOT).
- `backend/src/trading/providers.py` — `OrderSubmit` 에 `trigger_direction`/`oco_group_id`/`trailing_stop` 필드 + `_merge_exit_params` triggerDirection/trailingStop 블록(Bybit only).
- `backend/src/trading/models.py` — `Order` 에 `trigger_direction`/`oco_group_id`/`trailing_stop` 컬럼(ADD COLUMN).
- `backend/src/trading/schemas.py` — `OrderRequest`/`OrderResponse` 신규 필드.
- `backend/src/trading/services/order_service.py` — Order INSERT 양쪽 분기에 신규 필드 전달 + (P2) `_validate_position_size`.
- `backend/src/tasks/trading.py` — `OrderSubmit` 빌드에 신규 필드 전달.
- `backend/alembic/versions/20260626_xxxx_*.py` — ADD COLUMN migration(1건).
- `backend/tests/trading/`, `backend/tests/tasks/` — 단위 test.

---

## Task 1: triggerDirection 순수함수 (exit_order_mapping)

**Files:** Modify `backend/src/strategy/pine_v2/exit_order_mapping.py`; Test `backend/tests/trading/test_exit_trigger_direction.py`

**Produces:** `trigger_direction_for(exit_side: OrderSide, kind: ExitOrderKind) -> int` (1=rise,2=fall).

- [ ] Step 1: 실패 테스트 — closing-long SL(sell)→2, closing-short SL(buy)→1, closing-long TP(sell)→1, closing-short TP(buy)→2, TRAILING==STOP_LOSS 규칙.
- [ ] Step 2: 테스트 실패 확인.
- [ ] Step 3: 구현 — `fill direction`: SL/Trail 은 side==sell→2 / buy→1, TP 는 side==sell→1 / buy→2.
- [ ] Step 4: 통과 확인.
- [ ] Step 5: commit `feat(strategy): trigger_direction_for pure helper (ccxt v5 rise/fall SSOT)`.

## Task 2: OrderSubmit + \_merge_exit_params triggerDirection/trailing (providers)

**Files:** Modify `backend/src/trading/providers.py`; Test `backend/tests/trading/test_provider_trigger_direction_trailing.py`

**Consumes:** `_merge_exit_params` shape.
**Produces:** `OrderSubmit.trigger_direction: int|None`, `OrderSubmit.oco_group_id: str|None`, `OrderSubmit.trailing_stop: Decimal|None`. params 키 `triggerDirection`(str, Bybit), `trailingStop`(str, Bybit). OKX 미주입. `oco_group_id` 는 params 미주입(app-side).

- [ ] Step 1: 실패 테스트 — Bybit futures: trigger_price+trigger_direction=2 → params `triggerDirection:"2"`; trailing_stop=Decimal("150.5") → `trailingStop:"150.5"`; oco_group_id 설정해도 params 미포함. OKX: trigger_direction/trailing_stop 설정해도 미주입. entry(전부 None) byte-identical.
- [ ] Step 2: 실패 확인.
- [ ] Step 3: 구현 — `OrderSubmit` 3 필드 추가; `_merge_exit_params(..., trigger_direction_key, trailing_stop_key)` 2 신규 인자(Bybit="triggerDirection"/"trailingStop", OKX=None/None); 값 존재+키 not None 시만 주입.
- [ ] Step 4: 통과 확인 + 기존 `test_provider_exit_params.py` 회귀 0.
- [ ] Step 5: commit `feat(trading): triggerDirection + native trailingStop ccxt params (Bybit v5)`.

## Task 3: Order 컬럼 + ADD COLUMN migration (models + alembic)

**Files:** Modify `backend/src/trading/models.py`; Create `backend/alembic/versions/20260626_xxxx_add_order_trigger_direction_oco_trailing.py`; Test `backend/tests/trading/test_order_wave2_fields.py`

**Produces:** `Order.trigger_direction: int|None`, `Order.oco_group_id: str|None (max 64)`, `Order.trailing_stop: Decimal|None Numeric(18,8)`.

- [ ] Step 1: 모델 컬럼 3 추가(nullable, server_default 없음 — 전부 None 회귀).
- [ ] Step 2: alembic — `op.add_column('orders', ...)` x3 (schema='trading'); downgrade `op.drop_column` x3. down_revision = 현 head.
- [ ] Step 3: 테스트 — Order 인스턴스 신규 필드 default None.
- [ ] Step 4: 통과 확인.
- [ ] Step 5: commit (Task 4 와 묶음).

## Task 4: 배선 — schemas + order_service + tasks/trading

**Files:** Modify `backend/src/trading/schemas.py`, `order_service.py`, `tasks/trading.py`; Test `backend/tests/tasks/test_trading_wave2_passthrough.py`

**Consumes:** Task 2 OrderSubmit, Task 3 Order.
**Produces:** `OrderRequest.trigger_direction/oco_group_id/trailing_stop`, `OrderResponse` mirror. order_service Order INSERT(idempotent+non-idempotent) 양쪽 전달. tasks/trading `OrderSubmit` 빌드 전달.

- [ ] Step 1: 실패 테스트 — Order(신규 필드 set) → `_async_execute` 빌드한 OrderSubmit 이 동일 값 carry(provider monkeypatch capture).
- [ ] Step 2: 실패 확인.
- [ ] Step 3: 구현 — schema 필드(trigger_direction ge=1 le=2, oco_group_id max 64, trailing_stop gt=0 decimal_places=8) + order_service 2 INSERT 분기 + tasks/trading OrderSubmit.
- [ ] Step 4: 통과 확인.
- [ ] Step 5: commit `feat(trading): wire triggerDirection/oco_group/trailing through order path + ADD COLUMN migration`.

## Task 5 (P2, capacity): risk-based position sizing (order_service)

**Files:** Modify `backend/src/trading/schemas.py`, `order_service.py`; Test `backend/tests/trading/test_risk_sizing.py`

**Produces:** `OrderRequest.risk_percent: Decimal|None`. `_validate_position_size` — effective_price 직후, notional guard 전. 자본(`fetch_balance_usdt`)×risk%÷|entry−stop| = 서버 권위 qty. client qty 신뢰 금지(초과 시 reject 또는 cap — 보수적 reject).

- [ ] Step 1: 실패 테스트 — risk_percent=1%, balance=10000, entry=50000, stop=49000 → max_qty=0.1; req.quantity>max_qty → 거부(RiskSizingExceeded). stop 부재/risk None → skip.
- [ ] Step 2: 실패 확인.
- [ ] Step 3: 구현 — exceptions 신규 `RiskSizingExceeded`; `_validate_position_size` guard.
- [ ] Step 4: 통과 확인.
- [ ] Step 5: commit `feat(trading): risk-based position sizing (capital × risk% ÷ stop distance)`.

---

## Honest Defer (PR 본문 의무)

- 라이브 exit-level 추출(run_live→pending_exits surfacing) — event_loop/strategy_state(계약 밖) → strategy-state 워커/Phase 3.
- OCO sibling-cancel 오케스트레이션 — OrderRepository.list_by_oco_group(계약 밖) → `oco_group_id` 컬럼만 선반영.
- 실 Bybit demo round-trip — demo API 키 부재.
- bracket TP/SL 라이브 attach(0b) — 레벨 source 부재로 plumbing-ready 까지만.

## Self-Review

- Spec 커버리지: P0(triggerDirection/OCO 식별자/배선) ✓, P1(trailing live param) ✓, P2(risk-sizing) ✓. 0b 라이브 attach·OCO 취소·레벨추출 = 정직 defer(honesty gate).
- Placeholder: 없음(코드 shape ccxt 소스 인용).
- Type 일관: trigger_direction int(1|2) 전 계층 동일, trailing_stop Decimal 동일, oco_group_id str 동일.
