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
    api_key는 마지막 4자만 표시, api_secret/passphrase는 완전 마스킹.

    Sprint 7d: OKX는 passphrase 필수. Bybit/Binance는 None.
    """

    api_key: str
    api_secret: str
    passphrase: str | None = None

    def __repr__(self) -> str:
        masked_key = f"***{self.api_key[-4:]}" if len(self.api_key) >= 4 else "***"
        passphrase_marker = "present" if self.passphrase else "none"
        return (
            f"Credentials(api_key='{masked_key}', api_secret='***', "
            f"passphrase=<{passphrase_marker}>)"
        )


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
            # SECURITY: non-CCXT 예외는 traceback에 ccxt.bybit 인스턴스 (apiKey/secret 보유) 노출 위험.
            # from None으로 chain 제거. 디버깅을 위해 type만 보존, message 은닉.
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
            # SECURITY: non-CCXT 예외는 traceback에 ccxt.bybit 인스턴스 (apiKey/secret 보유) 노출 위험.
            # from None으로 chain 제거. 디버깅을 위해 type만 보존, message 은닉.
            raise ProviderError(f"unexpected non-CCXT error: {type(e).__name__}") from None
        finally:
            try:
                await exchange.close()
            except Exception:
                logger.warning("bybit_futures_close_failed", exc_info=True)


class OkxDemoProvider:
    """OKX demo (sandbox) ephemeral CCXT client — Sprint 7d.

    OKX 특이사항:
    - API Key + Secret에 더해 Passphrase 필수 (CCXT 옵션명: ``password``).
    - Demo/sandbox 전환은 ``enableRateLimit`` 옵션이 아니라 ``set_sandbox_mode(True)``
      — CCXT OKX 어댑터가 dedicated sandbox 라우팅을 제공.
    - Sprint 7d 범위는 spot only. Futures/Perpetual/Margin은 후속 스프린트.

    Credentials.passphrase 가 None이면 ProviderError로 빠르게 실패 (계약 위반).
    """

    async def create_order(self, creds: Credentials, order: OrderSubmit) -> OrderReceipt:
        if creds.passphrase is None:
            # 방어: OKX 라우팅인데 passphrase가 비어 있으면 CCXT가 런타임에 auth error를
            # 던지기 전에 명시적으로 실패시켜 traceback에 credentials가 섞이지 않게 한다.
            raise ProviderError("OkxDemoProvider requires a passphrase (OKX auth)")

        exchange = ccxt_async.okx(
            {
                "apiKey": creds.api_key,
                "secret": creds.api_secret,
                "password": creds.passphrase,
                "enableRateLimit": True,
                "timeout": 30000,
                "options": {"defaultType": "spot"},
            }
        )
        # OKX는 sandbox 라우팅을 전용 API로 전환. testnet 옵션은 무시됨.
        exchange.set_sandbox_mode(True)
        try:
            result = await exchange.create_order(
                order.symbol,
                order.type.value,
                order.side.value,
                float(order.quantity),
                float(order.price) if order.price is not None else None,
            )
            if "id" not in result:
                raise ProviderError(
                    f"malformed OKX response: missing 'id' (keys={list(result)[:5]})"
                )
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
            # SECURITY: non-CCXT 예외는 traceback에 ccxt.okx 인스턴스 (apiKey/secret/password
            # 보유) 노출 위험. from None으로 chain 제거.
            raise ProviderError(f"unexpected non-CCXT error: {type(e).__name__}") from None
        finally:
            try:
                await exchange.close()
            except Exception:
                logger.warning("okx_close_failed", exc_info=True)

    async def cancel_order(self, creds: Credentials, exchange_order_id: str) -> None:
        if creds.passphrase is None:
            raise ProviderError("OkxDemoProvider requires a passphrase (OKX auth)")

        exchange = ccxt_async.okx(
            {
                "apiKey": creds.api_key,
                "secret": creds.api_secret,
                "password": creds.passphrase,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            }
        )
        exchange.set_sandbox_mode(True)
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
                logger.warning("okx_close_failed", exc_info=True)


def _map_ccxt_status(ccxt_status: str | None) -> Literal["filled", "submitted", "rejected"]:
    """CCXT status → OrderReceipt status 매핑."""
    match ccxt_status:
        case "closed" | "filled":
            return "filled"
        case "canceled" | "rejected":
            return "rejected"
        case _:
            return "submitted"
