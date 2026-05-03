"""ExchangeProvider Protocol + 구현체.

Per-account ephemeral CCXT client 패턴 (spec §2.1):
- create_order 호출마다 credentials로 새 CCXT 인스턴스 생성 → 주문 → finally close()
- Sprint 5 public CCXTProvider(OHLCV)와는 완전 분리
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Protocol

import ccxt.async_support as ccxt_async

from src.common.metrics import ccxt_timer
from src.trading.exceptions import ProviderError
from src.trading.models import ExchangeMode, OrderSide, OrderType

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
    # environment: demo → 가상 자금(안전 기본값). live → 실제 자금.
    environment: ExchangeMode = ExchangeMode.demo

    def __repr__(self) -> str:
        masked_key = f"***{self.api_key[-4:]}" if len(self.api_key) >= 4 else "***"
        passphrase_marker = "present" if self.passphrase else "none"
        return (
            f"Credentials(api_key='{masked_key}', api_secret='***', "
            f"passphrase=<{passphrase_marker}>, environment={self.environment.value})"
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
    # Sprint 12 Phase C-pre: client-side order id (UUID4 string of Order.id).
    # Bybit V5 orderLinkId / OKX clOrdId 로 전달되어 WebSocket order event 와
    # local DB row 매핑. None = 외부 등록 또는 legacy 주문.
    client_order_id: str | None = None


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


@dataclass(frozen=True, slots=True)
class OrderStatusFetch:
    """Sprint 15 Phase A.1 — provider.fetch_order 응답 정규화.

    submitted watchdog (BL-001) 의 terminal evidence. cancelled 는 OrderReceipt 와
    달리 별개 status — Bybit/OKX 가 user/exchange cancellation 둘 다 보내므로 구분.
    """

    exchange_order_id: str
    status: Literal["filled", "submitted", "rejected", "cancelled"]
    filled_price: Decimal | None = None
    filled_quantity: Decimal | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class ExchangeProvider(Protocol):
    async def create_order(self, creds: Credentials, order: OrderSubmit) -> OrderReceipt: ...

    async def cancel_order(self, creds: Credentials, exchange_order_id: str) -> None: ...

    async def fetch_order(
        self, creds: Credentials, exchange_order_id: str, symbol: str
    ) -> OrderStatusFetch: ...


class FixtureExchangeProvider:
    """결정적 mock — 테스트 전용.

    `exchange_provider=fixture` 설정 시 활성화. autouse conftest fixture로 강제 주입.
    """

    def __init__(
        self,
        *,
        fill_price: Decimal = Decimal("50000.00"),
        fail_next_n: int = 0,
        fetch_status_override: Literal["filled", "submitted", "rejected", "cancelled"]
        | None = None,
    ) -> None:
        self._fill_price = fill_price
        self._fail_remaining = fail_next_n
        self._order_counter = 0
        self._fetch_status_override = fetch_status_override

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

    async def fetch_order(
        self, creds: Credentials, exchange_order_id: str, symbol: str
    ) -> OrderStatusFetch:
        """Sprint 15 Phase A.1 — 결정적 fetch_order. fetch_status_override 로 조작 가능."""
        override = self._fetch_status_override
        status: Literal["filled", "submitted", "rejected", "cancelled"] = (
            "filled" if override is None else override
        )
        return OrderStatusFetch(
            exchange_order_id=exchange_order_id,
            status=status,
            filled_price=self._fill_price if status == "filled" else None,
            filled_quantity=None,
            raw={"id": exchange_order_id, "symbol": symbol, "status": status},
        )


class BybitDemoProvider:
    """Bybit demo (api-demo.bybit.com) ephemeral CCXT client.

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
                "options": {
                    "defaultType": "spot",
                    "testnet": False,
                },
            }
        )
        _apply_bybit_env(exchange, creds.environment)
        try:
            async with ccxt_timer("bybit", "create_order"):
                # Sprint 12 Phase C — orderLinkId 가 있을 때만 params 전달
                # (기존 caller 호환성 + WS order event 매핑용).
                if order.client_order_id is not None:
                    result = await exchange.create_order(
                        order.symbol,
                        order.type.value,
                        order.side.value,
                        float(order.quantity),
                        float(order.price) if order.price is not None else None,
                        {"orderLinkId": order.client_order_id},
                    )
                else:
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
                "options": {
                    "defaultType": "spot",
                    "testnet": False,
                },
            }
        )
        _apply_bybit_env(exchange, creds.environment)
        try:
            async with ccxt_timer("bybit", "cancel_order"):
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

    async def fetch_order(
        self, creds: Credentials, exchange_order_id: str, symbol: str
    ) -> OrderStatusFetch:
        """Sprint 15 Phase A.1 — Bybit Demo spot fetch_order."""
        return await _bybit_fetch_order_impl(
            creds=creds,
            exchange_order_id=exchange_order_id,
            symbol=symbol,
            default_type="spot",
            timer_label="bybit",
        )


def _to_bybit_linear_symbol(symbol: str) -> str:
    """BL-124 — Bybit Linear perpetual unified symbol normalize (USDT-margined).

    ccxt 의 unified symbol convention:
    - Spot:    `BTC/USDT`
    - Linear:  `BTC/USDT:USDT` (USDT-settled perpetual)
    - Inverse: `BTC/USD:BTC` (coin-settled)

    `BybitFuturesProvider` 가 spot symbol 받으면 `set_leverage()` 호출 시
    `NotSupported: bybit setLeverage() only support linear and inverse market`.
    이미 ':' 가 포함되면 그대로 반환 (사용자가 명시 입력한 경우).
    """
    if ":" in symbol:
        return symbol
    if "/" not in symbol:
        return symbol  # malformed — provider 가 처리
    quote = symbol.split("/")[1].upper()
    return f"{symbol}:{quote}"


class BybitFuturesProvider:
    """Bybit futures (Linear Perpetual, USDT margined) demo/live provider.

    Spec decisions (docs/dev-log/007-sprint7a-futures-decisions.md):
    - Q1: BybitDemoProvider 파라미터화 대신 별도 클래스 (심볼/설정/에러 표면이 다름)
    - Q3: One-way position mode only (Hedge는 CCXT 이슈 #24848)

    Flow:
    1. set_margin_mode(order.margin_mode, symbol) — cross/isolated
    2. set_leverage(order.leverage, symbol)
    3. create_order(...)
    모두 동일 ephemeral client에서 실행 후 finally close().

    BL-124 — symbol normalize (`BTC/USDT` → `BTC/USDT:USDT`) 가 dispatch entry
    point 에서 자동 적용. Strategy/UI 는 spot format 유지 (Pine 호환).
    """

    async def create_order(self, creds: Credentials, order: OrderSubmit) -> OrderReceipt:
        if order.leverage is None or order.margin_mode is None:
            # 방어: OrderService가 Futures 경로에서 반드시 채워야 함.
            # 누락은 계약 위반이므로 fast-fail.
            raise ProviderError(
                "BybitFuturesProvider requires leverage and margin_mode "
                f"(got leverage={order.leverage}, margin_mode={order.margin_mode})"
            )

        # BL-124 — Linear symbol normalize. 사용자 입력 `BTC/USDT` 가 ccxt spot
        # 으로 분류되어 set_leverage() 가 NotSupported reject 되는 회귀 차단.
        linear_symbol = _to_bybit_linear_symbol(order.symbol)

        exchange = ccxt_async.bybit(
            {
                "apiKey": creds.api_key,
                "secret": creds.api_secret,
                "enableRateLimit": True,
                "timeout": 30000,
                "options": {
                    "defaultType": "linear",
                    "testnet": False,
                },
            }
        )
        _apply_bybit_env(exchange, creds.environment)
        try:
            # 마진 모드 먼저 → 레버리지 → 주문 순서 (Bybit v5 UTA 요구사항)
            # BL-125 — Bybit v5 의 set_margin_mode/set_leverage 는 이미 같은 값이면
            # error 반환 (retCode 110026 "isolated margin mode not modified" /
            # 110043 "leverage not modified"). 본질적으로 idempotent operation 이므로
            # "not modified" 응답은 silently ignore — 후속 set_leverage / create_order
            # 은 정상 진행.
            async with ccxt_timer("bybit_futures", "set_margin_mode"):
                try:
                    await exchange.set_margin_mode(order.margin_mode, linear_symbol)
                except ccxt_async.BadRequest as e:
                    if "not modified" not in str(e):
                        raise
            async with ccxt_timer("bybit_futures", "set_leverage"):
                try:
                    await exchange.set_leverage(order.leverage, linear_symbol)
                except ccxt_async.BadRequest as e:
                    if "not modified" not in str(e):
                        raise
            async with ccxt_timer("bybit_futures", "create_order"):
                if order.client_order_id is not None:
                    result = await exchange.create_order(
                        linear_symbol,
                        order.type.value,
                        order.side.value,
                        float(order.quantity),
                        float(order.price) if order.price is not None else None,
                        {"orderLinkId": order.client_order_id},
                    )
                else:
                    result = await exchange.create_order(
                        linear_symbol,
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
                "options": {
                    "defaultType": "linear",
                    "testnet": False,
                },
            }
        )
        _apply_bybit_env(exchange, creds.environment)
        try:
            async with ccxt_timer("bybit_futures", "cancel_order"):
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

    async def fetch_order(
        self, creds: Credentials, exchange_order_id: str, symbol: str
    ) -> OrderStatusFetch:
        """Sprint 15 Phase A.1 — Bybit Linear Perp futures fetch_order."""
        return await _bybit_fetch_order_impl(
            creds=creds,
            exchange_order_id=exchange_order_id,
            symbol=symbol,
            default_type="linear",
            timer_label="bybit_futures",
        )

    async def fetch_balance(self, creds: Credentials) -> dict[str, Decimal]:
        """USDT-margined Linear Perp 계좌의 자산별 free balance (Decimal).

        Sprint 8+ capital_base 동적 바인딩용. ephemeral CCXT 클라이언트로 1회 조회 후
        즉시 close. 반환: {"USDT": Decimal("1234.5"), "BTC": Decimal("0.01"), ...}
        CCXT 응답의 free 값이 누락·None이면 0으로 정규화.
        """
        exchange = ccxt_async.bybit(
            {
                "apiKey": creds.api_key,
                "secret": creds.api_secret,
                "enableRateLimit": True,
                "timeout": 30000,
                "options": {
                    "defaultType": "linear",
                    "testnet": False,
                },
            }
        )
        _apply_bybit_env(exchange, creds.environment)
        try:
            async with ccxt_timer("bybit_futures", "fetch_balance"):
                raw = await exchange.fetch_balance()
            result: dict[str, Decimal] = {}
            for asset, data in raw.items():
                if not isinstance(data, dict):
                    continue
                free = data.get("free")
                if free is None:
                    continue
                try:
                    result[asset] = Decimal(str(free))
                except (ValueError, TypeError, InvalidOperation):
                    continue
            return result
        except ProviderError:
            raise
        except ccxt_async.BaseError as e:
            raise ProviderError(f"{type(e).__name__}: {e}") from e
        except Exception as e:
            # SECURITY: non-CCXT 예외는 traceback에 ccxt.bybit 인스턴스 (apiKey/secret 보유) 노출 위험.
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
        exchange.set_sandbox_mode(creds.environment == ExchangeMode.demo)
        try:
            async with ccxt_timer("okx", "create_order"):
                if order.client_order_id is not None:
                    # Sprint 12 Phase C — OKX clOrdId. WS order event 매핑용.
                    result = await exchange.create_order(
                        order.symbol,
                        order.type.value,
                        order.side.value,
                        float(order.quantity),
                        float(order.price) if order.price is not None else None,
                        {"clOrdId": order.client_order_id},
                    )
                else:
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
        exchange.set_sandbox_mode(creds.environment == ExchangeMode.demo)
        try:
            async with ccxt_timer("okx", "cancel_order"):
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

    async def fetch_order(
        self, creds: Credentials, exchange_order_id: str, symbol: str
    ) -> OrderStatusFetch:
        """Sprint 15 Phase A.1 — OKX Demo spot fetch_order. passphrase 필수."""
        if creds.passphrase is None:
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
        exchange.set_sandbox_mode(creds.environment == ExchangeMode.demo)
        try:
            async with ccxt_timer("okx", "fetch_order"):
                result = await exchange.fetch_order(exchange_order_id, symbol)
            return _build_order_status_fetch(exchange_order_id, result)
        except ProviderError:
            raise
        except ccxt_async.BaseError as e:
            raise ProviderError(f"{type(e).__name__}: {e}") from e
        except Exception:
            # SECURITY: non-CCXT 예외 traceback 에 password 노출 차단.
            raise ProviderError("unexpected non-CCXT error in fetch_order") from None
        finally:
            try:
                await exchange.close()
            except Exception:
                logger.warning("okx_close_failed", exc_info=True)


async def _bybit_fetch_order_impl(
    *,
    creds: Credentials,
    exchange_order_id: str,
    symbol: str,
    default_type: Literal["spot", "linear"],
    timer_label: str,
) -> OrderStatusFetch:
    """Sprint 15 Phase A.1 — Bybit Demo / Futures 공유 fetch_order 구현.

    spot 과 linear 의 차이는 defaultType 만. ephemeral CCXT client + finally close.
    """
    exchange = ccxt_async.bybit(
        {
            "apiKey": creds.api_key,
            "secret": creds.api_secret,
            "enableRateLimit": True,
            "timeout": 30000,
            "options": {
                "defaultType": default_type,
                "testnet": False,
            },
        }
    )
    _apply_bybit_env(exchange, creds.environment)
    try:
        async with ccxt_timer(timer_label, "fetch_order"):
            result = await exchange.fetch_order(exchange_order_id, symbol)
        return _build_order_status_fetch(exchange_order_id, result)
    except ProviderError:
        raise
    except ccxt_async.BaseError as e:
        raise ProviderError(f"{type(e).__name__}: {e}") from e
    except Exception:
        # SECURITY: non-CCXT 예외 traceback 에 secret 노출 차단.
        raise ProviderError("unexpected non-CCXT error in fetch_order") from None
    finally:
        try:
            await exchange.close()
        except Exception:
            logger.warning("%s_close_failed", timer_label, exc_info=True)


def _build_order_status_fetch(
    exchange_order_id: str, result: dict[str, Any]
) -> OrderStatusFetch:
    """CCXT fetch_order 응답 → OrderStatusFetch 정규화.

    average / filled 가 None 또는 미존재 시 graceful → None. 0.0 도 None 처리
    (체결 없이 close/cancel 된 시나리오).
    """
    avg = result.get("average")
    filled_qty = result.get("filled")

    filled_price: Decimal | None
    try:
        filled_price = Decimal(str(avg)) if avg is not None else None
    except (ValueError, TypeError, InvalidOperation):
        filled_price = None

    filled_quantity: Decimal | None
    try:
        filled_quantity = Decimal(str(filled_qty)) if filled_qty is not None else None
    except (ValueError, TypeError, InvalidOperation):
        filled_quantity = None

    return OrderStatusFetch(
        exchange_order_id=exchange_order_id,
        status=_map_ccxt_status_for_fetch(result.get("status")),
        filled_price=filled_price,
        filled_quantity=filled_quantity,
        raw=dict(result),
    )


def _apply_bybit_env(exchange: Any, environment: ExchangeMode) -> None:
    """CCXT Bybit 인스턴스에 environment 라우팅을 적용한다.

    - demo: exchange.enable_demo_trading(True) — URL + enableDemoTrading 플래그를 함께 세팅.
      URL만 오버라이드하면 CCXT가 /v5/user/query-api를 호출해 retCode:10032 발생.
    - live: 기본값(api.bybit.com)이므로 no-op.
    """
    if environment == ExchangeMode.demo:
        exchange.enable_demo_trading(True)


def _map_ccxt_status(ccxt_status: str | None) -> Literal["filled", "submitted", "rejected"]:
    """CCXT status → OrderReceipt status 매핑 (3-state, create_order 응답 용).

    create_order 시점엔 user/exchange cancel 구분 무의미 (둘 다 reject 와 동치).
    """
    match ccxt_status:
        case "closed" | "filled":
            return "filled"
        case "canceled" | "cancelled" | "rejected":
            return "rejected"
        case _:
            return "submitted"


def _map_ccxt_status_for_fetch(
    ccxt_status: str | None,
) -> Literal["filled", "submitted", "rejected", "cancelled"]:
    """CCXT status → OrderStatusFetch status 매핑 (4-state, fetch_order 응답 용).

    Sprint 15 Phase A.1 — submitted watchdog 가 cancelled 와 rejected 를 구분
    필요 (cancelled = 사용자/exchange 정상 취소, rejected = 검증 실패 / 자금 부족).
    """
    match ccxt_status:
        case "closed" | "filled":
            return "filled"
        case "canceled" | "cancelled":
            return "cancelled"
        case "rejected" | "expired":
            return "rejected"
        case _:
            return "submitted"


class BybitLiveProvider:
    """Bybit mainnet provider stub — Sprint 22 BL-091 dispatch tuple 호환.

    Sprint 22: ExchangeAccount(mode=live) 의 dispatch 결과로 본 클래스 인스턴스 반환.
    create_order / cancel_order / fetch_order 호출 시 ProviderError raise →
    `tasks/trading.py:_execute_with_session` 의 `except ProviderError` 가 자동
    catch → Order graceful `rejected` 전이 + qb_active_orders dec (winner-only).

    BL-003 Bybit mainnet runbook 완료 후 BybitDemoProvider/BybitFuturesProvider
    base URL mainnet 매핑 + 라이브 검증 시점에 본 stub 본격 구현으로 교체.
    """

    async def create_order(
        self, creds: Credentials, order: OrderSubmit
    ) -> OrderReceipt:
        raise ProviderError(
            "Bybit live (mainnet) 미지원 — BL-003 mainnet runbook 완료 후 활성화"
        )

    async def cancel_order(
        self, creds: Credentials, exchange_order_id: str
    ) -> None:
        raise ProviderError(
            "Bybit live cancel 미지원 — BL-003 mainnet runbook 대기"
        )

    async def fetch_order(
        self, creds: Credentials, exchange_order_id: str, symbol: str
    ) -> OrderStatusFetch:
        raise ProviderError(
            "Bybit live fetch 미지원 — BL-003 mainnet runbook 대기"
        )
