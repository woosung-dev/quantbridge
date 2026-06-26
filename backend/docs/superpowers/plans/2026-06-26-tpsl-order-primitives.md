# TP/SL Order Primitives Implementation Plan (Wave 1)

> **For agentic workers:** money-path = 정석 TDD (test-first). 각 동작 RED → 최소 GREEN → refactor. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 라이브 주문 경로에 reduce-only · bracket TP/SL · Mark-trigger · min-notional 프리미티브를 추가해 `exit_orders.ExitOrderKind` 계약의 첫 라이브 소비자를 만든다.

**Architecture:** 신규 enum 0 · 위험한 enum swap 0. 프리미티브는 `OrderSubmit` 필드 + `create_order` params 조건부 병합으로 표현. `Order` 테이블은 안전한 `ADD COLUMN` alembic. ccxt 4.5.49 unified param 계약(bybit.py / okx.py `create_order_request` 소스 실측)에 맞춰 param shape 를 테스트로 고정한다.

**Tech Stack:** Python 3.12, ccxt 4.5.49 async_support, SQLModel, Pydantic V2, alembic, pytest (monkeypatch + AsyncMock).

## Global Constraints

- demo-only · 실자금 0. `BybitLiveProvider` stub 유지(절대 활성화 X). 검증 = 단위 test(mocked ccxt).
- 금융 숫자 Decimal (float 금지). Fernet 암호화 유지. IDOR/Kill Switch/리스크가드 우회 금지.
- 신규 파일 첫줄 한국어 역할주석. 사고/문서 한국어, 네이밍/커밋 영어.
- 커밋 trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- 신규 필드 default None/False = 기존 entry 주문 경로 byte-identical 회귀.

## ccxt 4.5.49 unified param 계약 (실측, `.venv/.../ccxt/async_support/{bybit,okx}.py`)

| 프리미티브 필드 | ccxt unified param | Bybit `create_order_request` | OKX `create_order_request` |
|---|---|---|---|
| `reduce_only=True` | `params["reduceOnly"]=True` | `safe_bool(params,'reduceOnly')` (bybit.py:3954) | `safe_value(params,'reduceOnly',False)` (okx.py:3024) |
| `trigger_price` | `params["triggerPrice"]=str(x)` | `safe_value_2(params,'triggerPrice','stopPrice')` (3955) | `safe_value_n([...'triggerPrice'...])` (3006) |
| `trigger_by` (Bybit 전용) | `params["triggerBy"]=x` | extend() pass-through, omit 미포함 (4162) | (미주입 — OKX trigger px type 기본 'last') |
| `take_profit` (attached) | `params["takeProfit"]={"triggerPrice":str(x)}` | `safe_value_2(takeProfit,'triggerPrice',...)` (4143) | `safe_value_n(takeProfit,['triggerPrice'...])` (3148) |
| `stop_loss` (attached) | `params["stopLoss"]={"triggerPrice":str(x)}` | `safe_value_2(stopLoss,'triggerPrice',...)` (4128) | `safe_value_n(stopLoss,['triggerPrice'...])` (3117) |

> 정직 고지: standalone `triggerPrice` 는 Bybit linear 에서 `triggerDirection` 도 요구한다(bybit.py:4113). 그 방향 결정은 exit-orchestration(Wave 2) 책임 — 프리미티브 계층은 위 표의 param 만 주입하고 단위 shape 만 검증. 실거래소 round-trip = follow-up(demo 키 필요).

---

## File Structure

- `src/trading/providers.py` — `OrderSubmit` 신규 필드 + `_merge_exit_params` 헬퍼 + 3 provider params 주입.
- `src/trading/models.py` — `Order` 신규 컬럼.
- `src/trading/schemas.py` — `OrderRequest`/`OrderResponse` 신규 optional 필드.
- `src/trading/services/order_service.py` — `OrderRequest→Order` 신규 필드 배선 + min-notional 가드.
- `src/trading/services/account_service.py` — `fetch_min_notional`.
- `src/trading/exceptions.py` — `MinNotionalNotMet`.
- `src/tasks/trading.py` — `Order→OrderSubmit` 신규 필드 배선.
- `src/tasks/live_signal.py` — close 주문 `reduce_only=True`.
- `src/strategy/pine_v2/exit_order_mapping.py` (신규) — `ExitOrderKind → ExitOrderPrimitive` 순수함수.
- `alembic/versions/20260626_0001_add_order_exit_primitives.py` (신규) — ADD COLUMN.

---

### Task 1: OrderSubmit/Order/schema 필드 + ADD COLUMN migration

**Files:**
- Modify: `src/trading/providers.py` (`OrderSubmit` dataclass)
- Modify: `src/trading/models.py` (`Order`)
- Modify: `src/trading/schemas.py` (`OrderRequest`/`OrderResponse`)
- Modify: `src/trading/services/order_service.py` (`Order(...)` 2 INSERT 분기)
- Create: `alembic/versions/20260626_0001_add_order_exit_primitives.py`
- Test: `tests/trading/test_order_exit_primitive_fields.py`

**Interfaces:**
- Produces: `OrderSubmit.reduce_only:bool=False`, `.trigger_price:Decimal|None`, `.trigger_by:str|None`, `.take_profit:Decimal|None`, `.stop_loss:Decimal|None`. 동일 이름의 `OrderRequest`/`OrderResponse`/`Order` 필드.

- [ ] Step 1: RED — OrderSubmit/OrderRequest/Order 가 신규 필드를 수용하고 round-trip 하는 테스트.
- [ ] Step 2: 필드 추가 (전부 Optional/default None, reduce_only=bool False). migration ADD/DROP COLUMN.
- [ ] Step 3: order_service 양쪽 INSERT 분기에 필드 배선.
- [ ] Step 4: GREEN + alembic up→down→up round-trip.
- [ ] Step 5: Commit `feat(trading): OrderSubmit/Order/schema reduce_only+TP/SL+trigger fields + ADD COLUMN migration`.

### Task 2: 3 provider create_order params 주입

**Files:**
- Modify: `src/trading/providers.py` (`_merge_exit_params` 헬퍼 + Bybit demo:210 / Bybit futures:381 / OKX:598)
- Modify: `src/tasks/trading.py` (`OrderSubmit(...)` 신규 필드 배선)
- Test: `tests/trading/test_provider_exit_params.py` (+기존 bybit/okx 회귀 확인)

**Interfaces:**
- Consumes: Task 1 `OrderSubmit` 필드.
- Produces: `_merge_exit_params(base:dict, order:OrderSubmit, *, trigger_by_key:str|None) -> dict`.

- [ ] Step 1: RED — reduce_only/trigger/TP/SL 주입 시 `assert_awaited_once_with` 로 정확 shape 검증 (Bybit + OKX). entry(필드 None) → 기존 5-arg / orderLinkId-only 회귀.
- [ ] Step 2: `_merge_exit_params` + 3 provider 병합 + tasks/trading 배선.
- [ ] Step 3: GREEN + 기존 provider 테스트 전부 통과.
- [ ] Step 4: Commit `feat(trading): 3 provider create_order params 주입 (reduceOnly/TP/SL/trigger)`.

### Task 3: close-signal reduce-only (C3 over-fill fix)

**Files:**
- Modify: `src/tasks/live_signal.py:665-677` (close OrderRequest `reduce_only=True`)
- Test: `tests/tasks/test_live_signal_reduce_only.py`

- [ ] Step 1: RED — close 이벤트 → OrderRequest.reduce_only=True / entry → False.
- [ ] Step 2: `reduce_only=(event.action == "close")` 배선.
- [ ] Step 3: GREEN.
- [ ] Step 4: Commit `fix(trading): close-signal reduce-only — over-fill 방지 (C3)`.

### Task 4: min-notional 가드 (C5)

**Files:**
- Create exception: `src/trading/exceptions.py` (`MinNotionalNotMet`)
- Modify: `src/trading/services/account_service.py` (`fetch_min_notional`)
- Modify: `src/trading/providers.py` (`BybitFuturesProvider.fetch_min_notional`)
- Modify: `src/trading/services/order_service.py` (notional max 직후 min 검증)
- Test: `tests/trading/test_min_notional_guard.py`

- [ ] Step 1: RED — notional < min_cost → MinNotionalNotMet. min None → skip(fail-open).
- [ ] Step 2: provider `fetch_min_notional`(load_markets→limits.cost.min) + service 위임 + order_service enforce.
- [ ] Step 3: GREEN.
- [ ] Step 4: Commit `feat(trading): min-notional 가드 (C5)`.

### Task 5: exit_orders ExitOrderKind → 라이브 프리미티브 매핑

**Files:**
- Create: `src/strategy/pine_v2/exit_order_mapping.py`
- Test: `tests/strategy/pine_v2/test_exit_order_mapping.py`

**Interfaces:**
- Consumes: `exit_orders.ExitOrderKind`, `exit_orders.fill_type_for`.
- Produces: `ExitOrderPrimitive` (frozen) + `map_exit_kind(kind, *, exit_price, order_type_hint=None) -> ExitOrderPrimitive`.

- [ ] Step 1: RED — TP→reduce-only limit(maker)/SL→reduce-only trigger market(taker)/Trail→trigger market(taker). fill_type 가 `fill_type_for(kind)` 와 1:1.
- [ ] Step 2: 순수함수 매핑 (`ExitOrderKind` import 재사용, 중복 정의 0).
- [ ] Step 3: GREEN.
- [ ] Step 4: Commit `feat(trading): exit_orders ExitOrderKind → 라이브 주문 프리미티브 매핑`.

### Task 6: C23 idempotency 재확인 + bracket/reduce-only 통합 test

**Files:**
- Test: `tests/trading/test_exit_primitive_idempotency.py`

- [ ] Step 1: 신규 필드 포함 body_hash 가 payload 다르면 IdempotencyConflict / 같으면 replay (검증 only, 신규 빌드 X).
- [ ] Step 2: GREEN.
- [ ] Step 3: Commit `test(trading): C23 idempotency 재확인 + bracket/reduce-only 경로 통합 test`.
