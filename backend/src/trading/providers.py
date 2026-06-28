"""ExchangeProvider Protocol + 구현체.

Per-account ephemeral CCXT client 패턴 (spec §2.1):
- create_order 호출마다 credentials로 새 CCXT 인스턴스 생성 → 주문 → finally close()
- Sprint 5 public CCXTProvider(OHLCV)와는 완전 분리
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from typing import Any, Literal, Protocol

import ccxt.async_support as ccxt_async

from src.common.metrics import ccxt_timer
from src.trading.exceptions import ProviderError, TrailingContractError
from src.trading.models import ExchangeMode, OrderSide, OrderType

logger = logging.getLogger(__name__)

# kill-switch 2차방어 — 트레일링은 ccxt 가 trailingStop param 을 trading-stop 엔드포인트
#   (본질 reduce-only)로 라우팅한다는 계약에 의존. pyproject 는 ccxt>=4.0.0 이라 lock bump
#   시 라우팅이 silent 변경될 수 있어, 검증된 버전 밖이면 발주 전 하드실패(non-retry).
_VALIDATED_CCXT_VERSIONS = frozenset({"4.5.49"})


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
    # Wave 1 (TP/SL order primitives) — 라이브 손익보호 프리미티브.
    # 전부 default None/False = 기존 entry 주문 경로 byte-identical 회귀.
    # ccxt unified params 로 조건부 병합 (providers `_merge_exit_params`).
    # reduce_only: True 시 reduceOnly=True (over-fill 방지, close 전용).
    reduce_only: bool = False
    # trigger_price: standalone 트리거(조건부) 주문 트리거가 (SL/Trail trigger market).
    trigger_price: Decimal | None = None
    # trigger_by: 트리거 가격 기준 (Bybit triggerBy: MarkPrice/IndexPrice/LastPrice).
    trigger_by: str | None = None
    # take_profit / stop_loss: entry 에 attach 하는 bracket TP/SL 트리거가.
    take_profit: Decimal | None = None
    stop_loss: Decimal | None = None
    # Wave 2 (TP/SL placement) — standalone 트리거/트레일링 라이브 param.
    # trigger_direction: Bybit v5 triggerDirection (1=가격 RISE 시 트리거, 2=FALL 시).
    #   linear standalone 트리거 주문 필수(ccxt 4.5.49). exit_order_mapping.trigger_direction_for 계산.
    trigger_direction: int | None = None
    # trailing_stop: Bybit native trailingStop (quote 거리). contract 전용.
    trailing_stop: Decimal | None = None
    # oco_group_id: OCO 형제 추적용 app-side 식별자. ccxt params 미주입(거래소 네이티브
    #   OCO group param 부재) — sibling-cancel 오케스트레이션이 DB 에서 조회(Wave 2 deferred).
    oco_group_id: str | None = None


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


@dataclass(frozen=True, slots=True)
class PositionInfo:
    """STEP B — set_trading_stop 전 stale-position 가드용 현재 포지션 스냅샷.

    size = 절대 수량(contracts, > 0). side = "long" | "short". 무포지션이면 None 반환.
    """

    size: Decimal
    side: Literal["long", "short"]


async def _to_exchange_precision(
    exchange: Any, symbol: str, order: OrderSubmit
) -> tuple[str, str | None]:
    """MP-4: Decimal 수량/가격을 거래소 instrument precision 문자열로 변환한다.

    float() 중간 변환을 제거해 정밀도 손실을 차단한다(Decimal-first 정책 연장).
    amount_to_precision / price_to_precision 는 markets 메타데이터(amount step /
    price tick)를 요구하므로 load_markets() 를 먼저 호출한다. ephemeral 인스턴스라도
    markets 는 per-instance 캐시되어 뒤따르는 create_order 의 내부 load_markets 는
    no-op → 추가 네트워크 round-trip 없음. amount 가 거래소 최소 단위 미만이면
    ccxt 가 InvalidOrder(BaseError) 를 던져 provider 의 BaseError 핸들러가 wrap.
    """
    await exchange.load_markets()
    amount = exchange.amount_to_precision(symbol, order.quantity)
    price = exchange.price_to_precision(symbol, order.price) if order.price is not None else None
    return amount, price


def _merge_exit_params(
    order: OrderSubmit,
    *,
    client_order_id_key: str | None,
    trigger_by_key: str | None,
    trigger_direction_key: str | None = None,
    trailing_stop_key: str | None = None,
    partial_size: bool = False,
    size_str: str | None = None,
) -> dict[str, Any]:
    """Wave 1/2 — client_order_id + exit-primitive 필드를 ccxt unified params 로 조건부 병합.

    값 None/False 면 키 미포함 → 기존 entry 주문 경로 byte-identical 회귀. params 가 비면
    caller 가 create_order 를 5-arg 로 호출(기존 동작).

    ccxt 4.5.49 unified param 계약(.venv/.../ccxt/async_support/{bybit,okx}.py
    create_order_request 실측)에 맞춘 shape:
    - reduceOnly: bool (Bybit safe_bool / OKX safe_value)
    - triggerPrice: scalar str (standalone 트리거 주문, SL/Trail trigger market)
    - takeProfit: object {"triggerPrice": str, "price": str} (entry attach bracket, maker limit TP)
    - stopLoss: object {"triggerPrice": str} (entry attach bracket, taker market SL)
    - trigger_by: Bybit 전용 triggerBy(MarkPrice/IndexPrice/LastPrice). OKX 는 None 키로 미주입.
    - triggerDirection: Bybit 전용. linear standalone 트리거 주문 필수(bybit.py:4113-4116).
      str("1"|"2") — ccxt 가 '1'→ascending(rise)/그외→2(fall) 매핑. OKX 는 None 키로 미주입
      (OKX 는 slTriggerPx/tpTriggerPx 가 방향을 자동 추론 → triggerDirection 개념 부재).
    - trailingStop: Bybit 전용 native trailing(bybit.py:3960-3962, 4102-4105). str(quote 거리).
      OKX 는 별 endpoint → None 키로 미주입.

    oco_group_id 는 ccxt params 로 주입하지 않는다 — 거래소 네이티브 OCO group param 부재.
    app-side sibling-cancel 추적용 DB 컬럼으로만 보존(Wave 2 오케스트레이션 deferred).

    금융 숫자는 str(Decimal) 로 주입(float 금지). ccxt get_price/price_to_precision 가 str 수용.
    """
    params: dict[str, Any] = {}
    if order.client_order_id is not None and client_order_id_key is not None:
        params[client_order_id_key] = order.client_order_id
    if order.reduce_only:
        params["reduceOnly"] = True
    if order.trigger_price is not None:
        params["triggerPrice"] = str(order.trigger_price)
    if order.trigger_by is not None and trigger_by_key is not None:
        params[trigger_by_key] = order.trigger_by
    if order.trigger_direction is not None and trigger_direction_key is not None:
        params[trigger_direction_key] = str(order.trigger_direction)
    if order.trailing_stop is not None and trailing_stop_key is not None and order.reduce_only:
        # ★ STEP B — trailingStop 은 reduce_only(보호/청산) 주문에서만 주입. entry
        #   (reduce_only=False)에 실으면 ccxt 가 trading-stop 엔드포인트로 라우팅해 entry
        #   가 깨짐(+SL 동반 시 bybit.py:3987-3989 InvalidOrder). 라이브 트레일링은 포지션
        #   open 후 set_trading_stop 으로만 placement (entry-injection defense-in-depth).
        params[trailing_stop_key] = str(order.trailing_stop)
    if order.take_profit is not None:
        # Phase 3 — limit TP: triggerPrice + price → ccxt hasTakeProfit branch
        # (bybit.py:4142-4149) 가 tpOrderType=Limit + tpLimitPrice + tpslMode=Partial 설정
        # → resting limit 체결(maker 지향, 백테스트 cost SSOT 정합). 단 post-only 가 아니라
        # gap-through 시 taker 체결 가능 — "limit TP, maker not guaranteed"(codex 게이트).
        # ★ tpslMode=Partial 은 tpSize 필수 (Bybit V5 — 평가자 게이트 E2/E3). 누락 시 엔트리
        #   통째 거부. tpSize = 포지션 전체 수량(full-position). 실 수용은 demo round-trip(D)로 확정.
        params["takeProfit"] = {
            "triggerPrice": str(order.take_profit),
            "price": str(order.take_profit),
        }
        # Bybit V5 전용 — tpslMode=Partial 은 tpSize/slSize 필수. 주문 qty 와 동일한
        # precision-normalized 문자열(size_str) 사용 — raw 수량과 lot-size 불일치 시
        # Bybit 엔트리 거부 방지(평가자 게이트 3/3 NIT). OKX 는 partial_size=False →
        # 미주입(attachAlgoOrds 자체 sizing).
        partial_qty = size_str if size_str is not None else str(order.quantity)
        if partial_size:
            params["tpSize"] = partial_qty
        if order.stop_loss is not None:
            # limit TP 가 Partial 을 켜면 SL 레그도 Partial → slSize 필수(Bybit).
            params["stopLoss"] = {"triggerPrice": str(order.stop_loss)}
            if partial_size:
                params["slSize"] = partial_qty
    elif order.stop_loss is not None:
        # SL 단독 = Full 모드(limit TP 없음) → size 불필요. trigger market(taker, 백테스트 정합).
        params["stopLoss"] = {"triggerPrice": str(order.stop_loss)}
    return params


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
                # MP-4: float() 대신 거래소 precision 문자열 제출(정밀도 손실 차단).
                amount, price = await _to_exchange_precision(exchange, order.symbol, order)
                # Sprint 12 Phase C — orderLinkId + Wave 1/2 exit-primitive params.
                # 필드 미설정 시 params 빈 dict → 기존 5-arg 호출(byte-identical 회귀).
                params = _merge_exit_params(
                    order,
                    client_order_id_key="orderLinkId",
                    trigger_by_key="triggerBy",
                    trigger_direction_key="triggerDirection",
                    trailing_stop_key="trailingStop",
                    partial_size=True,  # Bybit V5 — limit TP 의 tpslMode=Partial tpSize/slSize
                    size_str=amount,  # 주문 qty 와 동일한 precision 문자열로 size 정합
                )
                if params:
                    result = await exchange.create_order(
                        order.symbol,
                        order.type.value,
                        order.side.value,
                        amount,
                        price,
                        params,
                    )
                else:
                    result = await exchange.create_order(
                        order.symbol,
                        order.type.value,
                        order.side.value,
                        amount,
                        price,
                    )
            if "id" not in result:
                # 응답 손상 — 주문 추적 불가, 빠르게 실패. 일부 키만 노출 (PII 회피).
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
                # MP-4: float() 대신 거래소 precision 문자열 제출(정밀도 손실 차단).
                amount, price = await _to_exchange_precision(exchange, linear_symbol, order)
                # Sprint 12 Phase C orderLinkId + Wave 1/2 exit-primitive params 조건부 병합.
                params = _merge_exit_params(
                    order,
                    client_order_id_key="orderLinkId",
                    trigger_by_key="triggerBy",
                    trigger_direction_key="triggerDirection",
                    trailing_stop_key="trailingStop",
                    partial_size=True,  # Bybit V5 — limit TP 의 tpslMode=Partial tpSize/slSize
                    size_str=amount,  # 주문 qty 와 동일한 precision 문자열로 size 정합
                )
                if params:
                    result = await exchange.create_order(
                        linear_symbol,
                        order.type.value,
                        order.side.value,
                        amount,
                        price,
                        params,
                    )
                else:
                    result = await exchange.create_order(
                        linear_symbol,
                        order.type.value,
                        order.side.value,
                        amount,
                        price,
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

    async def set_trading_stop(
        self,
        creds: Credentials,
        *,
        symbol: str,
        side: OrderSide,
        qty: Decimal,
        distance: Decimal,
    ) -> dict[str, Any]:
        """STEP B — 포지션에 Bybit native trailing-stop 부착 (포지션 open 후 호출).

        트레일링은 별도 주문이 아니라 포지션 속성. ccxt 4.5.49 가 trailingStop param 이
        붙은 create_order 를 Bybit trading-stop 엔드포인트(privatePostV5PositionTradingStop)
        로 라우팅한다(bybit.py:3892/3898). 그 분기는 side/qty 를 드롭(bybit.py:4100)하고
        trailingStop 만 전송 — whole-position, 방향은 Bybit 가 포지션에서
        추론(triggerDirection 불필요, bybit.py:4106-4116 미도달). side/qty 는 ccxt.create_order
        시그니처 충족용(Bybit 미전송). reduceOnly/triggerBy 는 이 엔드포인트 no-op → 미전송.
        entry 와 달리 포지션이 이미 열린 뒤라 안전(reduce-only 는 엔드포인트 본질).

        OKX/spot 은 native trailing 미지원(별 endpoint / `bybit.py:3988` spot 거부)이라
        본 메서드는 BybitFuturesProvider 전용 — 일반 ExchangeProvider Protocol 미포함.
        """
        if ccxt_async.__version__ not in _VALIDATED_CCXT_VERSIONS:
            # kill-switch 2차방어 — 라우팅 계약 미검증 시 잘못될 수 있는 주문을 내지 않는다.
            raise TrailingContractError(
                reason="ccxt_unvalidated",
                detail=(
                    f"ccxt {ccxt_async.__version__} not in validated set "
                    f"{sorted(_VALIDATED_CCXT_VERSIONS)} — trailing routing contract unverified"
                ),
            )
        linear_symbol = _to_bybit_linear_symbol(symbol)
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
            async with ccxt_timer("bybit_futures", "set_trading_stop"):
                # qty 는 ccxt 가 트레일링 경로에서 드롭하지만 시그니처/precision 충족용.
                await exchange.load_markets()
                amount = exchange.amount_to_precision(linear_symbol, qty)
                # 보호 거리 tick 정규화 — Bybit 는 TICK_SIZE 모드라 precision.price 가 곧 tick.
                #   price_to_precision 은 round-nearest 라 distance 를 줄일 수 있고(tighter =
                #   premature exit) sub-tick 에선 InvalidOrder 를 던진다 → 직접 tick 으로 올림(ceil)
                #   해 "절대 요청보다 타이트하지 않다"를 보장하고, sub-tick 은 명시 거부한다.
                tick = Decimal(str(exchange.market(linear_symbol)["precision"]["price"]))
                if tick <= 0:
                    raise TrailingContractError(
                        reason="degenerate_distance",
                        detail=f"no positive price tick for {linear_symbol} (tick={tick})",
                    )
                if distance < tick:
                    # sub-tick = config 오류(Bybit 최소가 미만, 재시도 무의미) → 명시 거부.
                    raise TrailingContractError(
                        reason="degenerate_distance",
                        detail=f"trailing distance {distance} < price tick {tick}",
                    )
                distance_q = (distance / tick).to_integral_value(rounding=ROUND_CEILING) * tick
                distance_str = format(distance_q.normalize(), "f")
                params: dict[str, Any] = {"trailingStop": distance_str}
                result = await exchange.create_order(
                    linear_symbol, "market", side.value, amount, None, params
                )
            # ★ codex P1 — Bybit trading-stop 엔드포인트는 성공 시 빈 result(orderId 없음 —
            #   포지션 수정이라 주문 아님, V5 docs result:{}). create_order 가 예외 없이 반환
            #   = 수용. id 부재를 malformed 로 오판하면 성공을 retry → false UNPROTECTED
            #   alert(money-path bug). 호출자(_do_place_trailing_stop)는 반환값 미사용 —
            #   발주 *전* fetch_position stale 가드만 수행(flat/flip/hedge 차단). 발주 *후*
            #   독립 재조회 검증은 없음.
            return dict(result) if isinstance(result, dict) else {}
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

    async def fetch_position(
        self, creds: Credentials, symbol: str
    ) -> PositionInfo | None:
        """STEP B — 현재 linear 포지션 스냅샷(stale-position 가드). 무포지션이면 None.

        place_trailing_stop 가 체결→placement 사이 포지션이 닫히거나(flat) 반대로
        뒤집힌(flip) 경우 stale task 가 신규/없는 포지션에 trailing 오부착하는 것을
        차단한다. ccxt fetch_positions([symbol]) → size>0 인 첫 포지션 정규화.
        """
        linear_symbol = _to_bybit_linear_symbol(symbol)
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
            async with ccxt_timer("bybit_futures", "fetch_position"):
                positions = await exchange.fetch_positions([linear_symbol])
            legs: list[PositionInfo] = []
            for p in positions:
                contracts = p.get("contracts")
                if contracts is None:
                    continue
                size = Decimal(str(contracts))
                side = p.get("side")
                if size > 0 and side in ("long", "short"):
                    legs.append(PositionInfo(size=size, side=side))
            if len(legs) > 1:
                # hedge(long+short 동시 open) — 어느 leg 에 trailing 을 붙일지 추론 불가.
                #   첫 leg 추측 = wrong-leg 오부착(money-path). 발주 차단(non-retry + alert).
                raise TrailingContractError(
                    reason="hedge_mode_unsupported",
                    detail=f"{len(legs)} open legs for {symbol} — one-way mode required",
                )
            return legs[0] if legs else None
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

    async def fetch_mark_price(self, creds: Credentials, symbol: str) -> Decimal | None:
        """심볼의 mark/last price 조회 (P1-13, S5-B: market order notional 근사 가드용).

        ephemeral CCXT 클라이언트로 1회 fetch_ticker 후 즉시 close. mark price 우선,
        fallback to last/close. 모든 실패는 None 반환 (fail-soft) — caller 가
        fallback 결정 (live = fail-closed, demo = fail-open).
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
            async with ccxt_timer("bybit_futures", "fetch_ticker"):
                ticker = await exchange.fetch_ticker(symbol)
            if not isinstance(ticker, dict):
                return None
            # CCXT ticker: {'mark': ..., 'last': ..., 'close': ..., 'bid': ..., 'ask': ...}.
            # mark 우선 (perp 의 가장 보수적 reference), 없으면 last → close.
            for key in ("mark", "last", "close"):
                val = ticker.get(key)
                if val is None:
                    continue
                try:
                    price = Decimal(str(val))
                except (ValueError, TypeError, InvalidOperation):
                    continue
                if price > 0:
                    return price
            return None
        except (ccxt_async.BaseError, ProviderError):
            return None
        except Exception:
            # SECURITY: non-CCXT 예외는 traceback에 ccxt 인스턴스 (apiKey 보유) 노출 위험.
            return None
        finally:
            try:
                await exchange.close()
            except Exception:
                logger.warning("bybit_futures_close_failed", exc_info=True)

    async def fetch_min_notional(self, creds: Credentials, symbol: str) -> Decimal | None:
        """Wave 1 C5 — 심볼의 거래소 최소 주문 cost(limits.cost.min) 조회.

        load_markets() 메타에서 `markets[symbol]['limits']['cost']['min']` 추출.
        ephemeral CCXT 클라이언트로 1회 조회 후 즉시 close. 모든 실패/미가용은 None
        반환(fail-soft) — caller(OrderService)가 None 이면 가드 skip(fail-open).
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
            async with ccxt_timer("bybit_futures", "load_markets"):
                await exchange.load_markets()
            market = exchange.market(symbol)
            if not isinstance(market, dict):
                return None
            min_cost = market.get("limits", {}).get("cost", {}).get("min")
            if min_cost is None:
                return None
            try:
                value = Decimal(str(min_cost))
            except (ValueError, TypeError, InvalidOperation):
                return None
            return value if value > 0 else None
        except (ccxt_async.BaseError, ProviderError):
            return None
        except Exception:
            # SECURITY: non-CCXT 예외는 traceback에 ccxt 인스턴스 (apiKey 보유) 노출 위험.
            return None
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
                # MP-4: float() 대신 거래소 precision 문자열 제출(정밀도 손실 차단).
                amount, price = await _to_exchange_precision(exchange, order.symbol, order)
                # Sprint 12 Phase C clOrdId + Wave 1 exit-primitive params 조건부 병합.
                # OKX 는 triggerBy 미지원(trigger px type 기본 'last') → trigger_by_key=None.
                params = _merge_exit_params(
                    order, client_order_id_key="clOrdId", trigger_by_key=None
                )
                if params:
                    result = await exchange.create_order(
                        order.symbol,
                        order.type.value,
                        order.side.value,
                        amount,
                        price,
                        params,
                    )
                else:
                    result = await exchange.create_order(
                        order.symbol,
                        order.type.value,
                        order.side.value,
                        amount,
                        price,
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


def _build_order_status_fetch(exchange_order_id: str, result: dict[str, Any]) -> OrderStatusFetch:
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

    async def create_order(self, creds: Credentials, order: OrderSubmit) -> OrderReceipt:
        raise ProviderError("Bybit live (mainnet) 미지원 — BL-003 mainnet runbook 완료 후 활성화")

    async def cancel_order(self, creds: Credentials, exchange_order_id: str) -> None:
        raise ProviderError("Bybit live cancel 미지원 — BL-003 mainnet runbook 대기")

    async def fetch_order(
        self, creds: Credentials, exchange_order_id: str, symbol: str
    ) -> OrderStatusFetch:
        raise ProviderError("Bybit live fetch 미지원 — BL-003 mainnet runbook 대기")
