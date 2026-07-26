# Sprint 7a: Bybit Futures + Cross Margin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Context

Sprint 6에서 Trading 데모 MVP가 완료됐다 (PR #9, 34 commits, 506 backend tests). 현재 `BybitDemoProvider`는 **Spot 전용** (`defaultType: "spot"`)이라 파생상품 전략(레버리지, 숏, 크로스마진)을 검증할 수 없다.

Sprint 7a는 **Bybit testnet에서 Futures + Cross Margin 주문을 실행**하는 최소 확장이다. Sprint 7b(OKX 멀티 거래소), Sprint 8+(Binance mainnet 실거래)로 이어지는 Trading 도메인 성숙 단계의 첫 확장.

**사전 결정:** [`docs/dev-log/007-sprint7a-futures-decisions.md`](../../project/agy-project/quant-bridge/docs/dev-log/007-sprint7a-futures-decisions.md)
- **Q1:** 별도 클래스 `BybitFuturesProvider` (BybitDemoProvider 파라미터화 아님)
- **Q2:** `OrderSubmit` DTO에 `leverage: int | None` + `margin_mode: Literal["cross", "isolated"] | None` 필드 추가
- **Q3:** One-way position mode only (Hedge 미지원, CCXT 이슈 #24848 회피)

**Goal:** `exchange_provider=bybit_futures` 설정 시 `OrderService.execute` → Celery → `BybitFuturesProvider` 경로로 Bybit testnet에 Linear Perpetual 주문을 집행한다. Leverage/margin_mode는 OrderRequest로 받아 Order 모델에 persist하고 provider 호출 시 CCXT `set_leverage()` / `set_margin_mode()`를 호출한다.

**Architecture:** Sprint 6 ephemeral CCXT client 패턴 그대로. `BybitFuturesProvider`는 `BybitDemoProvider`의 자매 클래스로 `defaultType: "linear"` + margin/leverage pre-call을 수행. Order 테이블에 `leverage`, `margin_mode` nullable 컬럼 추가해 감사 추적 유지. Kill Switch는 Sprint 7a에서는 컬럼 로깅만 하고, `capital_base × leverage` 동적 반영은 Sprint 8+로 이관 (ADR-006 경로 유지).

**Tech Stack:** FastAPI + SQLModel + Alembic + CCXT async_support 4.5.49 + Celery + Bybit v5 UTA testnet.

**Branch:** `feat/sprint7a-futures` (main 기반, 사용자 별도 명령 없이 워크트리 생성 금지 — superpowers:using-git-worktrees 참조)

---

## File Structure

### Create
- `backend/alembic/versions/20260417_XXXX_add_order_leverage_margin_mode.py` — Order 테이블에 leverage/margin_mode 컬럼 추가
- `backend/tests/trading/test_providers_bybit_futures.py` — BybitFuturesProvider 단위 테스트 (CCXT mock)
- `backend/tests/trading/test_celery_task_futures.py` — execute_order_task + bybit_futures provider 분기 통합 테스트

### Modify
- `backend/src/trading/providers.py` — OrderSubmit DTO 확장 + `BybitFuturesProvider` 클래스 신규
- `backend/src/trading/models.py` — Order 테이블 `leverage: int | None`, `margin_mode: str | None` 추가
- `backend/src/trading/schemas.py` — OrderRequest/OrderResponse에 leverage/margin_mode 추가
- `backend/src/core/config.py` — `exchange_provider` Literal에 `"bybit_futures"` 추가 + `bybit_futures_max_leverage: int = 20` 추가
- `backend/src/trading/service.py` — OrderService.execute에서 leverage/margin_mode를 Order와 OrderSubmit에 전파
- `backend/src/tasks/trading.py` — `_build_exchange_provider()` `"bybit_futures"` 분기 + OrderSubmit 생성 시 leverage/margin_mode 주입
- `backend/tests/trading/test_providers_bybit_demo.py` — OrderSubmit fixture에 leverage=None/margin_mode=None 기본값 (기존 호환)
- `.env.example` — `EXCHANGE_PROVIDER=bybit_futures` 주석 + `BYBIT_FUTURES_MAX_LEVERAGE=20` 추가

---

## Task 1: Data Layer Extension — OrderSubmit DTO, Order model, Schema, Config, Migration

**Files:**
- Modify: `backend/src/trading/providers.py:38-45` (OrderSubmit DTO)
- Modify: `backend/src/trading/models.py:92-169` (Order model)
- Modify: `backend/src/trading/schemas.py:33-63` (OrderRequest, OrderResponse)
- Modify: `backend/src/core/config.py:57-60` (exchange_provider Literal) + 신규 필드
- Create: `backend/alembic/versions/20260417_XXXX_add_order_leverage_margin_mode.py`
- Modify: `backend/tests/trading/test_providers_bybit_demo.py` (OrderSubmit fixture 하위 호환)
- Modify: `.env.example`

- [ ] **Step 1.1: Metadata diff 회귀 테스트로 초기 diff 확인**

Run: `cd backend && pytest tests/common/test_metadata_diff.py -v`
Expected: PASS (현재 green baseline 확인. Order model 변경 전)

- [ ] **Step 1.2: OrderSubmit DTO 확장 (실패 테스트 먼저)**

테스트 추가: `backend/tests/trading/test_providers_bybit_demo.py`에서 기존 `order_submit` fixture 수정 + 신규 테스트 1건.

```python
# 기존 order_submit fixture 수정 (leverage/margin_mode 기본값 None)
@pytest.fixture
def order_submit():
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import OrderSubmit
    return OrderSubmit(
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=None,
        margin_mode=None,
    )


# 신규 테스트 파일 첫 진입 test_order_submit_futures_fields.py는 만들지 않고,
# 아래 한 건만 test_providers_bybit_demo.py에 추가
def test_order_submit_accepts_futures_fields():
    from decimal import Decimal
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import OrderSubmit

    submit = OrderSubmit(
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=5,
        margin_mode="cross",
    )
    assert submit.leverage == 5
    assert submit.margin_mode == "cross"
```

- [ ] **Step 1.3: Run test — should fail**

Run: `cd backend && pytest tests/trading/test_providers_bybit_demo.py::test_order_submit_accepts_futures_fields -v`
Expected: FAIL (TypeError: __init__() got an unexpected keyword argument 'leverage')

- [ ] **Step 1.4: OrderSubmit에 leverage/margin_mode 추가**

`backend/src/trading/providers.py:38-45` 수정:

```python
@dataclass(frozen=True, slots=True)
class OrderSubmit:
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: Decimal
    price: Decimal | None
    # Sprint 7a: Futures/Margin 파생상품 지원. Spot 경로는 모두 None.
    leverage: int | None = None
    margin_mode: Literal["cross", "isolated"] | None = None
```

- [ ] **Step 1.5: Run test — should pass**

Run: `cd backend && pytest tests/trading/test_providers_bybit_demo.py -v`
Expected: 모든 기존 테스트 + 신규 테스트 PASS

- [ ] **Step 1.6: Order 모델에 leverage/margin_mode 컬럼 추가 (실패 테스트 먼저)**

테스트 추가: `backend/tests/trading/test_repository_orders.py`에 신규 테스트 1건.

```python
async def test_order_persists_leverage_and_margin_mode(db_session, seeded_strategy_and_account):
    from decimal import Decimal
    from src.trading.models import Order, OrderSide, OrderState, OrderType
    from src.trading.repository import OrderRepository

    strategy, account = seeded_strategy_and_account
    repo = OrderRepository(db_session)
    order = await repo.save(Order(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=OrderState.pending,
        leverage=5,
        margin_mode="cross",
    ))
    await db_session.commit()

    fetched = await repo.get_by_id(order.id)
    assert fetched is not None
    assert fetched.leverage == 5
    assert fetched.margin_mode == "cross"
```

참고: `seeded_strategy_and_account` fixture가 기존에 있는지 확인 필요. 없으면 해당 파일의 기존 fixture 네이밍을 재사용.

- [ ] **Step 1.7: Run test — should fail**

Run: `cd backend && pytest tests/trading/test_repository_orders.py::test_order_persists_leverage_and_margin_mode -v`
Expected: FAIL (AttributeError 또는 SQLAlchemy unknown column)

- [ ] **Step 1.8: Order 모델 확장**

`backend/src/trading/models.py` Order 클래스에 컬럼 추가 (예: line 147 `error_message` 직전 또는 적절 위치):

```python
# Sprint 7a: Bybit Futures 레버리지/마진 모드. Spot 경로는 NULL.
leverage: int | None = Field(default=None, nullable=True)
margin_mode: str | None = Field(default=None, max_length=16, nullable=True)
```

- [ ] **Step 1.9: Alembic migration 생성**

Run: `cd backend && alembic revision --autogenerate -m "add_order_leverage_margin_mode"`
Expected: `backend/alembic/versions/20260417_XXXX_add_order_leverage_margin_mode.py` 생성됨

생성된 파일을 열어 검증 — 아래처럼 단순해야 함 (불필요한 drift 없음 확인):

```python
def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("leverage", sa.Integer(), nullable=True),
        schema="trading",
    )
    op.add_column(
        "orders",
        sa.Column("margin_mode", sa.String(length=16), nullable=True),
        schema="trading",
    )


def downgrade() -> None:
    op.drop_column("orders", "margin_mode", schema="trading")
    op.drop_column("orders", "leverage", schema="trading")
```

- [ ] **Step 1.10: Migration 적용 + metadata diff 회귀 통과 확인**

Run:
```bash
cd backend && alembic upgrade head
cd backend && pytest tests/common/test_metadata_diff.py tests/trading/test_repository_orders.py -v
```
Expected: PASS (drift 없음 + leverage/margin_mode persistence 테스트 통과)

- [ ] **Step 1.11: OrderRequest/OrderResponse 스키마 확장 (실패 테스트 먼저)**

테스트 추가: `backend/tests/trading/test_router_orders.py` 또는 schema 전용 테스트 파일에 1건.

```python
def test_order_request_accepts_futures_fields():
    from decimal import Decimal
    from uuid import uuid4
    from src.trading.models import OrderSide, OrderType
    from src.trading.schemas import OrderRequest

    req = OrderRequest(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=5,
        margin_mode="cross",
    )
    assert req.leverage == 5
    assert req.margin_mode == "cross"


def test_order_request_defaults_to_none_for_spot():
    from decimal import Decimal
    from uuid import uuid4
    from src.trading.models import OrderSide, OrderType
    from src.trading.schemas import OrderRequest

    req = OrderRequest(
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
    )
    assert req.leverage is None
    assert req.margin_mode is None
```

- [ ] **Step 1.12: Run test — should fail**

Run: `cd backend && pytest tests/trading/test_router_orders.py::test_order_request_accepts_futures_fields -v`
Expected: FAIL (Pydantic ValidationError — unknown field)

- [ ] **Step 1.13: Schema 확장**

`backend/src/trading/schemas.py:33-63` 수정:

```python
from typing import Literal  # 기존 import에 추가


class OrderRequest(BaseModel):
    """수동 주문 생성 또는 webhook payload에서 변환된 요청."""

    strategy_id: UUID
    exchange_account_id: UUID
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: Decimal = Field(gt=0, decimal_places=8)
    price: Decimal | None = Field(default=None, gt=0, decimal_places=8)
    # Sprint 7a: Futures. Spot은 모두 None.
    leverage: int | None = Field(default=None, ge=1, le=125)
    margin_mode: Literal["cross", "isolated"] | None = Field(default=None)


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    strategy_id: UUID
    exchange_account_id: UUID
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: Decimal
    price: Decimal | None
    state: OrderState
    idempotency_key: str | None
    exchange_order_id: str | None
    filled_price: Decimal | None
    error_message: str | None
    submitted_at: AwareDatetime | None
    filled_at: AwareDatetime | None
    created_at: AwareDatetime
    # Sprint 7a 추가
    leverage: int | None = None
    margin_mode: Literal["cross", "isolated"] | None = None
```

- [ ] **Step 1.14: Run schema tests**

Run: `cd backend && pytest tests/trading/test_router_orders.py -v`
Expected: PASS

- [ ] **Step 1.15: Config 확장**

`backend/src/core/config.py:57-60` 수정:

```python
exchange_provider: Literal["fixture", "bybit_demo", "bybit_futures"] = Field(
    default="fixture",
    description=(
        "ExchangeProvider 선택. "
        "fixture=테스트, bybit_demo=Spot testnet, bybit_futures=Linear Perp testnet."
    ),
)
```

`config.py` 하단 kill_switch 그룹 근처에 추가:

```python
# --- Sprint 7a Bybit Futures ---
bybit_futures_max_leverage: int = Field(
    default=20,
    ge=1,
    le=125,
    description=(
        "OrderRequest.leverage 상한. 초과 시 422. "
        "Bybit USDT Perp 이론 상한 125x이나 리스크 관리로 20x 기본."
    ),
)
```

- [ ] **Step 1.16: Config 검증 테스트 — 기존 test_config.py 스타일**

`backend/tests/core/test_config.py` 또는 동등 파일에 1건 추가:

```python
def test_exchange_provider_accepts_bybit_futures(monkeypatch):
    from cryptography.fernet import Fernet
    from src.core.config import Settings

    monkeypatch.setenv("TRADING_ENCRYPTION_KEYS", Fernet.generate_key().decode())
    monkeypatch.setenv("EXCHANGE_PROVIDER", "bybit_futures")
    s = Settings()
    assert s.exchange_provider == "bybit_futures"
    assert s.bybit_futures_max_leverage == 20
```

Run: `cd backend && pytest tests/core/test_config.py -v`
Expected: PASS

- [ ] **Step 1.17: .env.example 업데이트**

`.env.example`의 `EXCHANGE_PROVIDER` 주석에 `bybit_futures` 옵션 추가 + `BYBIT_FUTURES_MAX_LEVERAGE=20` 라인 추가.

- [ ] **Step 1.18: 전체 테스트 + mypy + ruff**

Run:
```bash
cd backend && pytest -v
cd backend && ruff check .
cd backend && mypy src/
```
Expected: 모두 green. 테스트 수 506 → 510~512 (신규 4~6건).

- [ ] **Step 1.19: Commit**

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git add backend/src/trading/providers.py backend/src/trading/models.py backend/src/trading/schemas.py backend/src/core/config.py backend/alembic/versions/ backend/tests/trading/ backend/tests/core/ .env.example
git commit -m "feat(trading): Sprint 7a T1 — OrderSubmit/Order/Schema/Config에 leverage+margin_mode 추가"
```

---

## Task 2: BybitFuturesProvider — CCXT Linear Perpetual + set_leverage/set_margin_mode

**Files:**
- Modify: `backend/src/trading/providers.py` (BybitFuturesProvider 신규 클래스)
- Create: `backend/tests/trading/test_providers_bybit_futures.py`

**Reference pattern:** `backend/src/trading/providers.py:102-185` (BybitDemoProvider) — ephemeral client + finally close() + PII-safe exception wrap 패턴 그대로 재사용.

- [ ] **Step 2.1: 실패 테스트 — 정상 경로 (leverage + cross margin 사전 설정)**

Create: `backend/tests/trading/test_providers_bybit_futures.py`

```python
"""BybitFuturesProvider — CCXT async_support을 monkeypatch로 mock.

실제 Bybit 호출 금지 (네트워크 isolation). BybitDemoProvider 테스트 패턴 계승.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def credentials():
    from src.trading.providers import Credentials
    return Credentials(api_key="test-key", api_secret="test-secret")


@pytest.fixture
def order_submit_futures():
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import OrderSubmit
    return OrderSubmit(
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=5,
        margin_mode="cross",
    )


@pytest.fixture
def ccxt_mock(monkeypatch):
    mock_exchange = MagicMock()
    mock_exchange.create_order = AsyncMock(
        return_value={
            "id": "bybit-futures-42",
            "average": 50123.45,
            "status": "closed",
            "symbol": "BTC/USDT:USDT",
        }
    )
    mock_exchange.cancel_order = AsyncMock(return_value={})
    mock_exchange.set_leverage = AsyncMock(return_value=None)
    mock_exchange.set_margin_mode = AsyncMock(return_value=None)
    mock_exchange.close = AsyncMock()

    mock_bybit_cls = MagicMock(return_value=mock_exchange)
    import ccxt.async_support as ccxt_async
    monkeypatch.setattr(ccxt_async, "bybit", mock_bybit_cls)
    return mock_exchange, mock_bybit_cls


async def test_bybit_futures_create_order_sets_leverage_and_margin_mode(
    credentials, order_submit_futures, ccxt_mock
):
    mock_exchange, mock_bybit_cls = ccxt_mock
    from src.trading.providers import BybitFuturesProvider

    provider = BybitFuturesProvider()
    receipt = await provider.create_order(credentials, order_submit_futures)

    # 1. CCXT config — defaultType=linear + testnet
    call_kwargs = mock_bybit_cls.call_args.args[0]
    assert call_kwargs["apiKey"] == "test-key"
    assert call_kwargs["secret"] == "test-secret"
    assert call_kwargs["options"]["defaultType"] == "linear"
    assert call_kwargs["options"]["testnet"] is True

    # 2. set_margin_mode BEFORE set_leverage BEFORE create_order
    mock_exchange.set_margin_mode.assert_awaited_once_with("cross", "BTC/USDT:USDT")
    mock_exchange.set_leverage.assert_awaited_once_with(5, "BTC/USDT:USDT")
    mock_exchange.create_order.assert_awaited_once_with(
        "BTC/USDT:USDT", "market", "buy", 0.001, None
    )

    # 3. finally close()
    mock_exchange.close.assert_awaited_once()

    # 4. receipt
    assert receipt.exchange_order_id == "bybit-futures-42"
    assert receipt.filled_price == Decimal("50123.45")
    assert receipt.status == "filled"
```

- [ ] **Step 2.2: Run test — should fail**

Run: `cd backend && pytest tests/trading/test_providers_bybit_futures.py -v`
Expected: FAIL (ImportError: cannot import name 'BybitFuturesProvider')

- [ ] **Step 2.3: BybitFuturesProvider 구현**

`backend/src/trading/providers.py` 하단 (`_map_ccxt_status` 함수 직전)에 추가:

```python
class BybitFuturesProvider:
    """Bybit futures (Linear Perpetual, USDT margined) testnet provider.

    Spec decisions (docs/dev-log/007-sprint7a-futures-decisions.md):
    - Q1: BybitDemoProvider 파라미터화 대신 별도 클래스 (심볼/설정/에러 표면이 다름)
    - Q3: One-way position mode only (Hedge는 CCXT 이슈 #24848)

    Flow:
    1. set_margin_mode(order.margin_mode, symbol) — cross/isolated
    2. set_leverage(order.leverage, symbol)
    3. create_order(...)
    모두 동일 ephemeral client에서 실행 후 finally close().
    """

    async def create_order(self, creds: Credentials, order: OrderSubmit) -> OrderReceipt:
        if order.leverage is None or order.margin_mode is None:
            # 방어: OrderService가 Futures 경로에서 반드시 채워야 함.
            # 누락은 계약 위반이므로 fast-fail.
            raise ProviderError(
                "BybitFuturesProvider requires leverage and margin_mode "
                f"(got leverage={order.leverage}, margin_mode={order.margin_mode})"
            )

        exchange = ccxt_async.bybit(
            {
                "apiKey": creds.api_key,
                "secret": creds.api_secret,
                "enableRateLimit": True,
                "timeout": 30000,
                "options": {"defaultType": "linear", "testnet": True},
            }
        )
        try:
            # 마진 모드 먼저 → 레버리지 → 주문 순서 (Bybit v5 UTA 요구사항)
            await exchange.set_margin_mode(order.margin_mode, order.symbol)
            await exchange.set_leverage(order.leverage, order.symbol)
            result = await exchange.create_order(
                order.symbol,
                order.type.value,
                order.side.value,
                float(order.quantity),
                float(order.price) if order.price is not None else None,
            )
            if "id" not in result:
                raise ProviderError(
                    f"malformed Bybit response: missing 'id' (keys={list(result)[:5]})"
                )
            avg = result.get("average")
            return OrderReceipt(
                exchange_order_id=str(result["id"]),
                filled_price=Decimal(str(avg)) if avg is not None else None,
                status=_map_ccxt_status(result.get("status")),
                raw=dict(result),
            )
        except ProviderError:
            raise
        except ccxt_async.BaseError as e:
            raise ProviderError(f"{type(e).__name__}: {e}") from e
        except Exception as e:
            raise ProviderError(f"unexpected non-CCXT error: {type(e).__name__}") from None
        finally:
            try:
                await exchange.close()
            except Exception:
                logger.warning("bybit_futures_close_failed", exc_info=True)

    async def cancel_order(self, creds: Credentials, exchange_order_id: str) -> None:
        exchange = ccxt_async.bybit(
            {
                "apiKey": creds.api_key,
                "secret": creds.api_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "linear", "testnet": True},
            }
        )
        try:
            await exchange.cancel_order(exchange_order_id)
        except ProviderError:
            raise
        except ccxt_async.BaseError as e:
            raise ProviderError(f"{type(e).__name__}: {e}") from e
        except Exception as e:
            raise ProviderError(f"unexpected non-CCXT error: {type(e).__name__}") from None
        finally:
            try:
                await exchange.close()
            except Exception:
                logger.warning("bybit_futures_close_failed", exc_info=True)
```

- [ ] **Step 2.4: Run test — should pass**

Run: `cd backend && pytest tests/trading/test_providers_bybit_futures.py::test_bybit_futures_create_order_sets_leverage_and_margin_mode -v`
Expected: PASS

- [ ] **Step 2.5: 실패 테스트 — leverage/margin_mode 누락 시 fast-fail**

`test_providers_bybit_futures.py`에 추가:

```python
async def test_bybit_futures_rejects_missing_leverage(credentials, ccxt_mock):
    from decimal import Decimal
    from src.trading.exceptions import ProviderError
    from src.trading.models import OrderSide, OrderType
    from src.trading.providers import BybitFuturesProvider, OrderSubmit

    bad = OrderSubmit(
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=None,   # Missing
        margin_mode="cross",
    )
    provider = BybitFuturesProvider()
    with pytest.raises(ProviderError, match="requires leverage and margin_mode"):
        await provider.create_order(credentials, bad)
```

Run: `cd backend && pytest tests/trading/test_providers_bybit_futures.py::test_bybit_futures_rejects_missing_leverage -v`
Expected: PASS (2.3 구현이 이미 커버)

- [ ] **Step 2.6: 실패 테스트 — CCXT InsufficientFunds wrap + close 보장**

`test_providers_bybit_futures.py`에 추가:

```python
async def test_bybit_futures_close_called_on_exchange_error(
    credentials, order_submit_futures, ccxt_mock
):
    mock_exchange, _ = ccxt_mock
    import ccxt.async_support as ccxt_async

    mock_exchange.create_order = AsyncMock(
        side_effect=ccxt_async.InsufficientFunds("margin low")
    )
    from src.trading.exceptions import ProviderError
    from src.trading.providers import BybitFuturesProvider

    provider = BybitFuturesProvider()
    with pytest.raises(ProviderError, match="InsufficientFunds"):
        await provider.create_order(credentials, order_submit_futures)
    mock_exchange.close.assert_awaited_once()
```

Run: `cd backend && pytest tests/trading/test_providers_bybit_futures.py::test_bybit_futures_close_called_on_exchange_error -v`
Expected: PASS

- [ ] **Step 2.7: 실패 테스트 — non-CCXT 예외 PII-safe wrap**

`test_providers_bybit_futures.py`에 추가:

```python
async def test_bybit_futures_non_ccxt_exception_wrapped(
    credentials, order_submit_futures, ccxt_mock
):
    """SECURITY: non-CCXT 예외는 traceback에 apiKey 노출 위험. from None으로 chain 제거."""
    mock_exchange, _ = ccxt_mock
    mock_exchange.create_order = AsyncMock(side_effect=KeyError("transport error"))
    from src.trading.exceptions import ProviderError
    from src.trading.providers import BybitFuturesProvider

    provider = BybitFuturesProvider()
    with pytest.raises(ProviderError, match="unexpected non-CCXT error: KeyError"):
        await provider.create_order(credentials, order_submit_futures)
    mock_exchange.close.assert_awaited_once()
```

Run: `cd backend && pytest tests/trading/test_providers_bybit_futures.py::test_bybit_futures_non_ccxt_exception_wrapped -v`
Expected: PASS

- [ ] **Step 2.8: 실패 테스트 — cancel_order**

`test_providers_bybit_futures.py`에 추가:

```python
async def test_bybit_futures_cancel_order(credentials, ccxt_mock):
    mock_exchange, _ = ccxt_mock
    from src.trading.providers import BybitFuturesProvider

    provider = BybitFuturesProvider()
    await provider.cancel_order(credentials, "bybit-futures-42")
    mock_exchange.cancel_order.assert_awaited_once_with("bybit-futures-42")
    mock_exchange.close.assert_awaited_once()
```

Run: `cd backend && pytest tests/trading/test_providers_bybit_futures.py -v`
Expected: 모든 테스트 (5건) PASS

- [ ] **Step 2.9: mypy + ruff 검증**

Run:
```bash
cd backend && mypy src/trading/providers.py
cd backend && ruff check src/trading/providers.py tests/trading/test_providers_bybit_futures.py
```
Expected: clean

- [ ] **Step 2.10: Commit**

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git add backend/src/trading/providers.py backend/tests/trading/test_providers_bybit_futures.py
git commit -m "feat(trading): Sprint 7a T2 — BybitFuturesProvider (Linear Perp + set_leverage + set_margin_mode)"
```

---

## Task 3: Celery Task + OrderService Propagation

**Files:**
- Modify: `backend/src/tasks/trading.py:65-77` (_build_exchange_provider + _async_execute)
- Modify: `backend/src/trading/service.py:139-215` (OrderService.execute — leverage/margin_mode → Order, OrderSubmit)
- Create: `backend/tests/trading/test_celery_task_futures.py` (또는 기존 test_celery_task.py 확장)

**Reference:** `backend/src/tasks/trading.py:65-77` (_build_exchange_provider 분기), `backend/src/trading/service.py:173-184` (Order 생성 필드 목록).

- [ ] **Step 3.1: 실패 테스트 — OrderService가 leverage/margin_mode를 Order와 OrderSubmit에 전파**

`backend/tests/trading/test_service_orders_futures.py` 신규 또는 `test_service_orders_idempotency.py`에 추가:

```python
async def test_order_service_persists_and_dispatches_futures_fields(
    db_session, seeded_strategy_and_account
):
    """Sprint 7a: leverage/margin_mode가 Order 레코드에 persist되는지 + dispatcher까지 전달되는지."""
    from decimal import Decimal
    from uuid import uuid4
    from src.trading.kill_switch import KillSwitchService
    from src.trading.models import OrderSide, OrderType
    from src.trading.repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.service import OrderDispatcher, OrderService

    strategy, account = seeded_strategy_and_account

    class _NoopDispatcher:
        async def dispatch_order_execution(self, order_id):
            self.last_id = order_id

    class _PassKillSwitch:
        async def ensure_not_gated(self, strategy_id, account_id):
            return None

    disp = _NoopDispatcher()
    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=disp,
        kill_switch=_PassKillSwitch(),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=5,
        margin_mode="cross",
    )
    resp, replayed = await svc.execute(req, idempotency_key=None)
    assert replayed is False
    assert resp.leverage == 5
    assert resp.margin_mode == "cross"

    fetched = await OrderRepository(db_session).get_by_id(disp.last_id)
    assert fetched is not None
    assert fetched.leverage == 5
    assert fetched.margin_mode == "cross"
```

참고: `seeded_strategy_and_account` / `_PassKillSwitch` 패턴은 `test_service_orders_kill_switch.py` 참조해 스타일 맞추기.

- [ ] **Step 3.2: Run test — should fail**

Run: `cd backend && pytest tests/trading/test_service_orders_futures.py -v`
Expected: FAIL (AssertionError: resp.leverage is None)

- [ ] **Step 3.3: OrderService.execute에서 leverage/margin_mode 전파**

`backend/src/trading/service.py:173-184` 및 `191-202` (두 Order 생성 지점) 모두 수정 — `leverage`, `margin_mode` 필드 추가:

```python
order = await self._repo.save(Order(
    strategy_id=req.strategy_id,
    exchange_account_id=req.exchange_account_id,
    symbol=req.symbol,
    side=req.side,
    type=req.type,
    quantity=req.quantity,
    price=req.price,
    state=OrderState.pending,
    idempotency_key=idempotency_key,     # 또는 None (두 분기별로)
    idempotency_payload_hash=body_hash,  # 또는 None
    leverage=req.leverage,
    margin_mode=req.margin_mode,
))
```

두 분기(`if idempotency_key is not None` / `else`)에 동일하게 반영.

- [ ] **Step 3.4: Run test — should pass**

Run: `cd backend && pytest tests/trading/test_service_orders_futures.py -v`
Expected: PASS

- [ ] **Step 3.5: 실패 테스트 — Celery task가 Order의 leverage/margin_mode로 OrderSubmit 생성하고 bybit_futures 분기 호출**

`backend/tests/trading/test_celery_task_futures.py` 신규:

```python
"""execute_order_task + bybit_futures provider 분기 — monkeypatch로 provider factory 교체."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest


async def test_async_execute_uses_bybit_futures_provider_with_leverage(
    db_session, seeded_pending_futures_order, monkeypatch
):
    """pending futures 주문 → Celery async path → BybitFuturesProvider 호출 확인."""
    from src.tasks import trading as task_mod
    from src.trading.providers import OrderReceipt

    order, _strategy, _account = seeded_pending_futures_order

    # Provider mock — OrderSubmit 검증
    captured: dict = {}

    class _FakeFutures:
        async def create_order(self, creds, submit):
            captured["symbol"] = submit.symbol
            captured["leverage"] = submit.leverage
            captured["margin_mode"] = submit.margin_mode
            return OrderReceipt(
                exchange_order_id="fx-1",
                filled_price=Decimal("50000"),
                status="filled",
                raw={},
            )

    # sessionmaker + provider 주입
    fake_sm = _sm_returning(db_session)  # conftest 유틸 또는 인라인 작성
    monkeypatch.setattr(task_mod, "async_session_factory", lambda: fake_sm)
    monkeypatch.setattr(task_mod, "_exchange_provider", _FakeFutures())

    result = await task_mod._async_execute(order.id)
    assert result["state"] == "filled"
    assert captured["symbol"] == "BTC/USDT:USDT"
    assert captured["leverage"] == 5
    assert captured["margin_mode"] == "cross"
```

참고: `seeded_pending_futures_order` fixture는 `seeded_pending_order`(기존 conftest 유틸, test_celery_task.py 참조)를 확장하거나 동일 파일 내 로컬 fixture로 생성. `_sm_returning` 헬퍼도 test_celery_task.py 기존 패턴 재사용.

- [ ] **Step 3.6: Run test — should fail**

Run: `cd backend && pytest tests/trading/test_celery_task_futures.py -v`
Expected: FAIL (OrderSubmit에 leverage/margin_mode 전달 안 됨 — captured 값 None)

- [ ] **Step 3.7: `_async_execute`에서 OrderSubmit에 leverage/margin_mode 주입**

`backend/src/tasks/trading.py:152-158` 수정:

```python
order_submit = OrderSubmit(
    symbol=order.symbol,
    side=order.side,
    type=order.type,
    quantity=order.quantity,
    price=order.price,
    leverage=order.leverage,
    margin_mode=order.margin_mode,  # type: ignore[arg-type]  # StrEnum → Literal narrowing
)
```

`margin_mode`는 DB에서 `str | None`으로 읽히므로 `Literal["cross","isolated"] | None`과 타입 충돌 가능 — `# type: ignore` 또는 cast 적용. 실행시 DB에 저장된 값은 schema validator로 이미 검증됨.

- [ ] **Step 3.8: `_build_exchange_provider()`에 bybit_futures 분기 추가**

`backend/src/tasks/trading.py:65-77` 수정:

```python
def _build_exchange_provider() -> ExchangeProvider:
    """Factory — settings.exchange_provider → concrete provider."""
    provider_name = settings.exchange_provider
    if provider_name == "fixture":
        from src.trading.providers import FixtureExchangeProvider
        return FixtureExchangeProvider()
    elif provider_name == "bybit_demo":
        from src.trading.providers import BybitDemoProvider
        return BybitDemoProvider()
    elif provider_name == "bybit_futures":
        from src.trading.providers import BybitFuturesProvider
        return BybitFuturesProvider()
    else:
        raise ValueError(f"Unknown exchange_provider: {provider_name}")
```

- [ ] **Step 3.9: Run tests**

Run: `cd backend && pytest tests/trading/test_celery_task_futures.py tests/trading/test_celery_task.py -v`
Expected: 모든 테스트 PASS (기존 Spot 경로 회귀 없음)

- [ ] **Step 3.10: 실패 테스트 — `_build_exchange_provider()` 분기 단위 테스트**

`test_celery_task_futures.py`에 추가 (conftest settings monkeypatch):

```python
def test_build_exchange_provider_dispatches_bybit_futures(monkeypatch):
    from src.tasks import trading as task_mod
    from src.trading.providers import BybitFuturesProvider

    # settings 전역 직접 교체 (lru_cache 우회)
    monkeypatch.setattr(task_mod.settings, "exchange_provider", "bybit_futures")
    monkeypatch.setattr(task_mod, "_exchange_provider", None)

    provider = task_mod._build_exchange_provider()
    assert isinstance(provider, BybitFuturesProvider)
```

Run: `cd backend && pytest tests/trading/test_celery_task_futures.py::test_build_exchange_provider_dispatches_bybit_futures -v`
Expected: PASS

- [ ] **Step 3.11: 전체 테스트 + 린트 + 타입**

Run:
```bash
cd backend && pytest -v
cd backend && ruff check .
cd backend && mypy src/
```
Expected: 모두 green. 테스트 수 510~ → 513~515.

- [ ] **Step 3.12: Commit**

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git add backend/src/trading/service.py backend/src/tasks/trading.py backend/tests/trading/test_service_orders_futures.py backend/tests/trading/test_celery_task_futures.py
git commit -m "feat(trading): Sprint 7a T3 — OrderService/Celery가 leverage+margin_mode를 BybitFuturesProvider로 전파"
```

---

## Task 4: E2E Integration Test + Security Checklist + Kill Switch 주석

**Files:**
- Create: `backend/tests/trading/test_e2e_webhook_to_futures_order.py`
- Modify: `backend/src/trading/kill_switch.py` (주석 1개 추가, 로직 변경 없음)
- Modify: `docs/TODO.md` (Sprint 7a 완료 마크)
- Modify: `docs/dev-log/007-sprint7a-futures-decisions.md` (상태: 결정 완료 → 구현 완료)

### 4a. E2E 통합 테스트

- [ ] **Step 4.1: 실패 테스트 — webhook payload → futures order → pending → filled**

Create: `backend/tests/trading/test_e2e_webhook_to_futures_order.py`

```python
"""Sprint 7a E2E: webhook(BTC/USDT:USDT, leverage=5, margin=cross) → Order(pending)
→ execute_order_task → BybitFuturesProvider → filled.

CCXT mock으로 네트워크 차단. TV payload parser가 leverage/margin을 전달한다고
가정하거나, manual OrderRequest 경로로 검증.
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest


async def test_webhook_futures_order_end_to_end(
    client, authed_user, db_session, seeded_strategy_and_account, monkeypatch
):
    """Manual POST /orders 경로. Webhook TV payload parser 확장은 Sprint 7b로 분리."""
    # 1. CCXT mock
    mock_exchange = MagicMock()
    mock_exchange.create_order = AsyncMock(
        return_value={"id": "fx-e2e-1", "average": 50000.0, "status": "closed"}
    )
    mock_exchange.set_leverage = AsyncMock()
    mock_exchange.set_margin_mode = AsyncMock()
    mock_exchange.close = AsyncMock()

    import ccxt.async_support as ccxt_async
    monkeypatch.setattr(ccxt_async, "bybit", MagicMock(return_value=mock_exchange))

    # 2. bybit_futures 활성화 (settings override)
    from src.core.config import settings
    monkeypatch.setattr(settings, "exchange_provider", "bybit_futures")

    # 3. worker singleton reset
    from src.tasks import trading as task_mod
    monkeypatch.setattr(task_mod, "_exchange_provider", None)

    # 4. Dispatcher는 inline async 실행으로 교체
    strategy, account = seeded_strategy_and_account

    async def _inline_dispatch(order_id):
        await task_mod._async_execute(order_id)

    # dependency override for OrderDispatcher (conftest 패턴)
    from src.trading.dependencies import get_order_dispatcher

    class _InlineDispatcher:
        async def dispatch_order_execution(self, order_id):
            await _inline_dispatch(order_id)

    from src.main import app
    app.dependency_overrides[get_order_dispatcher] = lambda: _InlineDispatcher()
    try:
        # 5. POST /api/v1/orders (manual; webhook TV payload parser는 별도 Sprint)
        resp = await client.post(
            "/api/v1/orders",
            json={
                "strategy_id": str(strategy.id),
                "exchange_account_id": str(account.id),
                "symbol": "BTC/USDT:USDT",
                "side": "buy",
                "type": "market",
                "quantity": "0.001",
                "leverage": 5,
                "margin_mode": "cross",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        order_id = body["id"]

        # 6. DB 상태 확인
        from uuid import UUID
        from src.trading.repository import OrderRepository
        from src.trading.models import OrderState

        repo = OrderRepository(db_session)
        order = await repo.get_by_id(UUID(order_id))
        assert order is not None
        assert order.state == OrderState.filled
        assert order.leverage == 5
        assert order.margin_mode == "cross"
        assert order.exchange_order_id == "fx-e2e-1"
        assert order.filled_price == Decimal("50000")

        # 7. CCXT call 순서 검증
        mock_exchange.set_margin_mode.assert_awaited_once_with("cross", "BTC/USDT:USDT")
        mock_exchange.set_leverage.assert_awaited_once_with(5, "BTC/USDT:USDT")
        mock_exchange.create_order.assert_awaited_once()
        mock_exchange.close.assert_awaited()
    finally:
        app.dependency_overrides.pop(get_order_dispatcher, None)
```

**주의:** 이 테스트는 `get_order_dispatcher` DI가 이미 존재한다고 가정. 존재하지 않으면 `test_celery_task.py` 또는 `dependencies.py`에서 실제 이름 확인 후 보정. 존재하지 않으면 "monkeypatch task_mod._exchange_provider + 직접 `_async_execute` 호출" 방식으로 대체하고 엔드포인트 호출 대신 OrderService 직접 호출로 단순화.

- [ ] **Step 4.2: Run test — should fail (initial missing dispatcher hookup)**

Run: `cd backend && pytest tests/trading/test_e2e_webhook_to_futures_order.py -v`
Expected: FAIL or ERROR — dependency 이름/경로 확인 필요

- [ ] **Step 4.3: 실제 dispatcher DI 경로 확인 후 테스트 보정**

확인 명령:
```bash
cd backend && grep -rn "OrderDispatcher\|order_dispatcher\|CeleryDispatcher" src/trading/ src/tasks/
```

결과에 따라 테스트의 `get_order_dispatcher` 부분을 실제 이름으로 교체. `app.dependency_overrides`가 안 먹힐 경우 대안: OrderService 직접 생성 + `_async_execute` 직접 await로 단순화 (네트워크 stub이 핵심이므로 HTTP 경로를 포기해도 시나리오는 살아있음).

- [ ] **Step 4.4: Run test — should pass**

Run: `cd backend && pytest tests/trading/test_e2e_webhook_to_futures_order.py -v`
Expected: PASS

### 4b. Kill Switch 주석 (레버리지 동적 반영은 Sprint 8+)

- [ ] **Step 4.5: kill_switch.py에 Sprint 7a 경계 주석 추가**

`backend/src/trading/kill_switch.py`의 `CumulativeLossEvaluator` 클래스 docstring 또는 `capital_base` 주석에 한 줄 추가:

```python
# Sprint 7a 경계: Order.leverage가 persist되나 capital_base는 여전히 config 고정값.
# 레버리지 × notional 반영은 Sprint 8+에서 ExchangeAccount.fetch_balance() 바인딩과
# 함께 처리 (spec 007 보안 체크리스트 참조).
```

이 단계는 **테스트 추가 없음** — 주석만. 로직 미변경.

Run: `cd backend && pytest tests/trading/test_kill_switch_evaluators.py -v`
Expected: 기존 그대로 PASS (회귀 없음 확인)

### 4c. 문서 업데이트

- [ ] **Step 4.6: docs/TODO.md — Sprint 7 Next Actions 업데이트**

기존 `Sprint 7 Next Actions` 섹션에서 첫 항목 수정:

```markdown
### Sprint 7 Next Actions

- [x] 실 CCXT 거래소 연동 (Bybit testnet Futures + Cross Margin) — Sprint 7a ✅ 완료 (2026-04-17)
- [ ] Bybit testnet Live smoke test (실 API key로 수동 주문 1건) — 사용자 테스트 대기
- [ ] Trading Sessions 도메인 확장 (세션 생성/시작/중지/kill) — Sprint 7b+
- [ ] OKX 멀티 거래소 추가 — Sprint 7b
- [ ] Kill Switch `capital_base` 동적 바인딩 (`ExchangeAccount.fetch_balance()`) — Sprint 8+
- [ ] WebSocket 실시간 주문 상태 스트리밍
- [ ] CSO-5: Frontend dev CVEs 해소
...
```

- [ ] **Step 4.7: docs/dev-log/007-sprint7a-futures-decisions.md — 상태 업데이트**

상단 frontmatter 수정:

```markdown
> **상태:** ✅ 구현 완료 (2026-04-17)
> **구현 브랜치:** feat/sprint7a-futures
> **관련 커밋:** T1/T2/T3/T4 (feat(trading): Sprint 7a ...)
```

- [ ] **Step 4.8: 전체 테스트 + 린트 + 타입 + alembic**

Run:
```bash
cd backend && pytest -v
cd backend && ruff check .
cd backend && mypy src/
cd backend && alembic upgrade head
cd backend && alembic downgrade -1 && alembic upgrade head   # 마이그레이션 round-trip
cd backend && pytest tests/common/test_metadata_diff.py -v   # drift 없음 재확인
```
Expected: 모두 green. 최종 테스트 수 513~517 (Sprint 6 baseline 506 + 신규 7~11건).

- [ ] **Step 4.9: Commit**

```bash
cd /Users/woosung/project/agy-project/quant-bridge
git add backend/tests/trading/test_e2e_webhook_to_futures_order.py backend/src/trading/kill_switch.py docs/TODO.md docs/dev-log/007-sprint7a-futures-decisions.md
git commit -m "feat(trading): Sprint 7a T4 — E2E webhook→futures order + Kill Switch 경계 주석 + docs"
```

---

## Security Checklist (플랜 실행 중 수시 확인)

`docs/dev-log/007-sprint7a-futures-decisions.md` 보안 체크리스트 — Sprint 7a 범위:

- [x] **레버리지 상한 검증:** config `bybit_futures_max_leverage=20` + `OrderRequest.leverage Field(le=125)` 이중 가드. T1 Step 1.13 + 1.15.
- [ ] **Cross margin 청산 시뮬레이션:** testnet 수동 smoke (사용자 단계, 이 플랜 범위 밖 — TODO.md에 Sprint 7 수동 smoke 추가).
- [x] **InsufficientMargin → ProviderError 매핑:** CCXT `BaseError` 일괄 wrap (BybitFuturesProvider). T2 Step 2.6에서 InsufficientFunds 케이스 커버. `InsufficientMargin`은 별도 클래스명이므로 실제 Bybit 응답 확인 후 필요 시 추가 매핑.
- [ ] **Kill Switch capital_base 레버리지 반영:** Sprint 8+ 이관 — T4 주석으로 경계 명시 (Step 4.5).
- [ ] **Funding rate PnL 반영:** Sprint 7a 범위 밖 — 포지션 holding 개념이 없으므로 skip. Sessions 도메인(Sprint 7b+)에서 처리.

보안 회귀 방지 — **PR 머지 전** 아래 명령 필수:

```bash
cd backend && grep -rn "apiKey\|api_key\|secret" src/trading/providers.py | grep -v "creds\."
# Expected: creds 외부 사용처 0건 (ephemeral client 외 credentials 평문 참조 금지)
```

---

## Verification (End-to-End 수동 검증)

실제 Bybit testnet 연동까지 완료한 뒤(사용자 단계) 아래 경로로 검증:

### 1. Local smoke

```bash
# 환경변수
export TRADING_ENCRYPTION_KEYS=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export EXCHANGE_PROVIDER=bybit_futures

# 인프라 + 워커
docker compose up -d db redis
cd backend && alembic upgrade head
cd backend && uvicorn src.main:app --reload &
cd backend && celery -A src.tasks worker --loglevel=info --concurrency=2 &

# 실 Bybit testnet API key로 ExchangeAccount 등록 후
# POST /api/v1/orders (leverage=5, margin_mode=cross)
# → 응답에서 order.state 폴링 → filled 확인
# → Bybit testnet UI에서 실 포지션 확인
```

### 2. 테스트 수

- Sprint 6 baseline: **506 backend tests**
- Sprint 7a 목표: **513~517 tests**
  - T1: +4~6 (OrderSubmit, Order repo, OrderRequest, Config)
  - T2: +5 (BybitFuturesProvider)
  - T3: +3 (OrderService futures, task async, build factory)
  - T4: +1 (E2E)

### 3. CI 통과

```bash
cd backend && pytest -v && ruff check . && mypy src/
# 그리고 main 대비 diff 없는 metadata
cd backend && pytest tests/common/test_metadata_diff.py -v
```

### 4. Git 상태 확인

```bash
git log --oneline main..feat/sprint7a-futures
# 4개 커밋 예상 (T1/T2/T3/T4)
```

---

## 참고 파일

- 설계 근거: [`docs/dev-log/007-sprint7a-futures-decisions.md`](../../project/agy-project/quant-bridge/docs/dev-log/007-sprint7a-futures-decisions.md)
- Sprint 6 spec: `docs/superpowers/specs/2026-04-16-trading-demo-design.md`
- Sprint 6 plan: `docs/superpowers/plans/2026-04-16-trading-demo.md`
- 기존 BybitDemoProvider: `backend/src/trading/providers.py:102-185`
- 기존 Celery task: `backend/src/tasks/trading.py`
- 기존 OrderService: `backend/src/trading/service.py:120-215`
- CCXT mock 패턴: `backend/tests/trading/test_providers_bybit_demo.py`

---

## 실행 준비 체크 (플랜 수락 후)

1. 현재 main 기반 새 브랜치 생성: `git switch -c feat/sprint7a-futures`
2. 이 플랜을 `docs/superpowers/plans/2026-04-17-sprint7a-bybit-futures.md`로 복사 (선택 — Plan Mode 제약으로 최종 플랜은 이 파일에 있음)
3. SDD 실행: `superpowers:subagent-driven-development`
