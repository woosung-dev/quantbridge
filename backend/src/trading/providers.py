"""ExchangeProvider Protocol + 구현체.

Per-account ephemeral CCXT client 패턴 (spec §2.1):
- create_order 호출마다 credentials로 새 CCXT 인스턴스 생성 → 주문 → finally close()
- Sprint 5 public CCXTProvider(OHLCV)와는 완전 분리
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, Protocol

import ccxt.async_support as ccxt_async

from src.trading.exceptions import ProviderError
from src.trading.models import OrderSide, OrderType

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Credentials:
    """평문 credentials — 수명을 함수 스코프로 한정.

    SECURITY: __repr__는 마스킹. logging/traceback/Sentry에 평문 노출 방지.
    api_key는 마지막 4자만 표시, api_secret은 완전 마스킹.
    """

    api_key: str
    api_secret: str

    def __repr__(self) -> str:
        masked_key = f"***{self.api_key[-4:]}" if len(self.api_key) >= 4 else "***"
        return f"Credentials(api_key='{masked_key}', api_secret='***')"


@dataclass(frozen=True, slots=True)
class OrderSubmit:
    symbol: str
    side: OrderSide
    type: OrderType
    quantity: Decimal
    price: Decimal | None


@dataclass(frozen=True, slots=True)
class OrderReceipt:
    """Provider 응답의 정규화된 형태.

    `raw`는 원본 응답 그대로 — 로깅/persistence 시 PII 주의.
    """

    exchange_order_id: str
    filled_price: Decimal | None
    status: Literal["filled", "submitted", "rejected"]
    # PII-suspect: Bybit 응답엔 accountId/balance/fills 포함 가능.
    # T11+ Order.raw_response 저장 시 INFO+ 레벨 로깅 금지. T6 BybitDemoProvider는
    # 가능하면 known-key allow-list로 projection 권장.
    raw: dict[str, Any]


class ExchangeProvider(Protocol):
    async def create_order(self, creds: Credentials, order: OrderSubmit) -> OrderReceipt: ...

    async def cancel_order(self, creds: Credentials, exchange_order_id: str) -> None: ...


class FixtureExchangeProvider:
    """결정적 mock — 테스트 전용.

    `exchange_provider=fixture` 설정 시 활성화. autouse conftest fixture로 강제 주입.
    """

    def __init__(
        self,
        *,
        fill_price: Decimal = Decimal("50000.00"),
        fail_next_n: int = 0,
    ) -> None:
        self._fill_price = fill_price
        self._fail_remaining = fail_next_n
        self._order_counter = 0

    async def create_order(self, creds: Credentials, order: OrderSubmit) -> OrderReceipt:
        if self._fail_remaining > 0:
            self._fail_remaining -= 1
            raise ProviderError("FixtureExchangeProvider: configured failure")

        self._order_counter += 1
        return OrderReceipt(
            exchange_order_id=f"fixture-{self._order_counter}",
            filled_price=self._fill_price,
            status="filled",
            raw={"symbol": order.symbol, "side": order.side.value, "quantity": str(order.quantity)},
        )

    async def cancel_order(self, creds: Credentials, exchange_order_id: str) -> None:
        logger.debug("fixture_cancel_order", extra={"exchange_order_id": exchange_order_id})


class BybitDemoProvider:
    """Bybit demo (testnet) ephemeral CCXT client.

    create_order/cancel_order마다 credentials로 새 CCXT 인스턴스를 생성하고,
    finally 블록에서 close()로 즉시 해제. 평문 credentials는 함수 스코프에만 존재.
    """

    async def create_order(self, creds: Credentials, order: OrderSubmit) -> OrderReceipt:
        exchange = ccxt_async.bybit(
            {
                "apiKey": creds.api_key,
                "secret": creds.api_secret,
                "enableRateLimit": True,
                "timeout": 30000,
                "options": {"defaultType": "spot", "testnet": True},
            }
        )
        try:
            result = await exchange.create_order(
                order.symbol,
                order.type.value,
                order.side.value,
                float(order.quantity),
                float(order.price) if order.price is not None else None,
            )
            if "id" not in result:
                # 응답 손상 — 주문 추적 불가, 빠르게 실패. 일부 키만 노출 (PII 회피).
                raise ProviderError(f"malformed Bybit response: missing 'id' (keys={list(result)[:5]})")
            avg = result.get("average")
            return OrderReceipt(
                exchange_order_id=str(result["id"]),
                filled_price=Decimal(str(avg)) if avg is not None else None,
                status=_map_ccxt_status(result.get("status")),
                raw=dict(result),
            )
        except ProviderError:
            raise  # already wrapped, do not re-wrap
        except ccxt_async.BaseError as e:
            raise ProviderError(f"{type(e).__name__}: {e}") from e
        except Exception as e:
            # SECURITY: non-CCXT 예외는 traceback에 ccxt.bybit 인스턴스 (apiKey/secret 보유) 노출 위험.
            # from None으로 chain 제거. 디버깅을 위해 type만 보존, message 은닉.
            raise ProviderError(f"unexpected non-CCXT error: {type(e).__name__}") from None
        finally:
            try:
                await exchange.close()
            except Exception:
                logger.warning("bybit_close_failed", exc_info=True)

    async def cancel_order(self, creds: Credentials, exchange_order_id: str) -> None:
        exchange = ccxt_async.bybit(
            {
                "apiKey": creds.api_key,
                "secret": creds.api_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "spot", "testnet": True},
            }
        )
        try:
            await exchange.cancel_order(exchange_order_id)
        except ProviderError:
            raise  # already wrapped, do not re-wrap
        except ccxt_async.BaseError as e:
            raise ProviderError(f"{type(e).__name__}: {e}") from e
        except Exception as e:
            # SECURITY: non-CCXT 예외는 traceback에 ccxt.bybit 인스턴스 (apiKey/secret 보유) 노출 위험.
            # from None으로 chain 제거. 디버깅을 위해 type만 보존, message 은닉.
            raise ProviderError(f"unexpected non-CCXT error: {type(e).__name__}") from None
        finally:
            try:
                await exchange.close()
            except Exception:
                logger.warning("bybit_close_failed", exc_info=True)


def _map_ccxt_status(ccxt_status: str | None) -> Literal["filled", "submitted", "rejected"]:
    """CCXT status → OrderReceipt status 매핑."""
    match ccxt_status:
        case "closed" | "filled":
            return "filled"
        case "canceled" | "rejected":
            return "rejected"
        case _:
            return "submitted"
