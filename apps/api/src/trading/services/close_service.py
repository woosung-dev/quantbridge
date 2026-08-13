# 라이브 세션의 단일 선물 포지션을 reduce-only 시장가로 청산하는 서비스
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError

from src.strategy.repository import StrategyRepository
from src.strategy.schemas import StrategySettings, validate_strategy_settings
from src.trading.models import ExchangeMode, ExchangeName, OrderSide, OrderType
from src.trading.providers import BybitFuturesProvider, ConditionalOrderSnapshot, Credentials
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.schemas import ClosePositionResponse, OrderRequest, RestingEntryOrder
from src.trading.services.account_service import ExchangeAccountService
from src.trading.services.order_service import OrderService

logger = logging.getLogger(__name__)

# BL-537 — reduce-only 청산에서 leverage/margin_mode 는 **거래소로 가지 않는다**.
# `BybitFuturesProvider.create_order` 가 `if not order.reduce_only:` 로 set_margin_mode 와
# set_leverage 를 둘 다 감싸기 때문이다. 두 값이 여전히 필요한 이유는 둘뿐이다:
#   1. `create_order` 가 None 이면 fast-fail 한다 (NOT NULL 계약)
#   2. ★`tasks/trading.py` `_has_leverage` 가 not-null AND > 0 일 때만 **futures** provider 로
#      보낸다 — 0/None 이면 청산이 조용히 스팟으로 나가 linear 포지션을 못 닫는다
# 즉 원장 필드 + dispatch 판별자일 뿐이므로, 값이 없다고 청산을 막아선 안 된다.
_FALLBACK_LEVERAGE = 1
_FALLBACK_MARGIN_MODE: Literal["cross", "isolated"] = "cross"
# `OrderRequest.leverage` 는 Field(ge=1, le=125). 벗어나면 ValidationError 가 🔴 청산 자체를
# 막으므로, 거래소가 어차피 안 받는 값을 여기서 클램프한다 (cap 우회가 성립하지 않는다).
_MAX_LEVERAGE = 125


def _close_leverage(position_leverage: Decimal | None, settings: StrategySettings | None) -> int:
    """청산 주문에 실을 leverage — 거래소 포지션 → 전략 설정 → 1 순의 **첫 양수**.

    ★비유한(NaN/Inf) 후보는 건너뛴다. `_position_snapshot_from_ccxt` 는 leverage 를
    `finite_only` 없이 파싱하므로(`providers.py`) 거래소가 malformed 값을 주면
    `Decimal("NaN")` 이 그대로 올라오고, `int()` 가 ValueError 를 던져 🔴 청산이
    500 이 된다. 청산은 어떤 필드 때문에도 막히면 안 된다.
    """
    for candidate in (position_leverage, settings.leverage if settings is not None else None):
        if candidate is None:
            continue
        if isinstance(candidate, Decimal) and not candidate.is_finite():
            continue
        value = int(candidate)
        if value > 0:
            return min(value, _MAX_LEVERAGE)
    return _FALLBACK_LEVERAGE


class ClosePositionService:
    def __init__(
        self,
        *,
        session_repo: LiveSignalSessionRepository,
        account_repo: ExchangeAccountRepository,
        strategy_repo: StrategyRepository,
        account_service: ExchangeAccountService,
        bybit_futures_provider: BybitFuturesProvider,
        order_service: OrderService,
    ) -> None:
        self._session_repo = session_repo
        self._account_repo = account_repo
        self._strategy_repo = strategy_repo
        self._account_service = account_service
        self._bybit_futures_provider = bybit_futures_provider
        self._order_service = order_service

    async def _fetch_resting_entries(
        self, credentials: Credentials, symbol: str
    ) -> list[ConditionalOrderSnapshot]:
        """거래소의 일반·trigger 미체결 주문 중 **진입만** 반환한다.

        ★`reduce_only=None` 은 협상 불가 계약이다. 기본값 `True` 는 TP/SL(reduce-only)만
        주므로 그 기본값으로 물으면 표적인 **진입**을 통째로 놓친다. `None` 이라야 필터가
        꺼져 둘 다 오고, 그 뒤 `is False` 로 진입만 남긴다.
        ★고아 TP/SL 만 남은 계정은 **flat 이다** — 그래서 `is False` 로 다시 거른다.
        """
        resting = await self._bybit_futures_provider.fetch_open_conditional_orders(
            credentials, symbol, reduce_only=None
        )
        return [order for order in resting if order.reduce_only is False]

    async def close_position(self, user_id: UUID, session_id: UUID) -> ClosePositionResponse:
        session = await self._session_repo.get_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise HTTPException(status_code=404, detail="live session not found")

        account = await self._account_repo.get_by_id(session.exchange_account_id)
        if account is None:
            raise HTTPException(status_code=404, detail="live session not found")

        strategy = await self._strategy_repo.find_by_id_and_owner(session.strategy_id, user_id)
        settings = strategy.settings if strategy is not None else None
        # BL-537 — 설정이 없거나 깨졌다고 청산을 막지 않는다. 위 상수 블록 참조:
        # 이 두 값은 reduce-only 청산에서 거래소에 도달하지 않으므로, 여기서 422 를 내면
        # 전략 설정을 비운 사용자의 라이브 포지션이 앱에서 **영구히 안 닫힌다**.
        # ★게다가 `position_service.get_account_positions` 의 close_blocked_reason 은 이
        #   게이트를 평가하지 않아, 코크핏이 "누르면 실패하는 버튼" 을 렌더할 수 있었다.
        try:
            validated_settings = validate_strategy_settings(settings)
        except ValidationError:
            validated_settings = None
        if account.mode != ExchangeMode.demo:
            raise HTTPException(status_code=422, detail="live_mode_stub")
        if account.exchange != ExchangeName.bybit:
            raise HTTPException(status_code=422, detail="exchange_unsupported")
        if account.read_only is True:
            raise HTTPException(status_code=422, detail="read_only_key")

        credentials = await self._account_service.get_credentials_for_order(account.id)
        positions = await self._bybit_futures_provider.fetch_open_positions(
            credentials, session.symbol
        )
        if not positions:
            # BL-661 — flat 판정은 거래소 잔량을 확인하지 못하면 성공을 말할 수 없다.
            # 여기서는 예외를 전파해 fail-closed 한다. 공용 헬퍼가 `reduce_only=None`으로
            # 일반 지정가·trigger 주문을 함께 읽고 `is False`인 진입만 남긴다.
            entries = await self._fetch_resting_entries(credentials, session.symbol)
            if not entries:
                raise HTTPException(status_code=409, detail="no_open_position")

            raise HTTPException(
                status_code=409,
                detail={
                    "code": "resting_conditional_entries",
                    "count": len(entries),
                    "detail": (
                        f"포지션은 없지만 미체결 진입 주문 {len(entries)}건이 남아 있습니다."
                    ),
                    # ★`RestingEntryOrder` 를 거쳐 낸다 — 두 경로(409 raw dict · 200
                    #   response_model)의 필드가 영구히 갈라지지 않게 하는 유일한 장치다.
                    #   ★`mode="json"` 이 필수다: 이 경로는 `HTTPException(detail=…)` 로 나가
                    #   **JSONResponse 가 직접** 직렬화하므로 `Decimal` 이 그대로면 터진다.
                    #   200 경로는 Pydantic 이 직렬화하므로 그 제약이 없다.
                    "orders": [
                        RestingEntryOrder.from_snapshot(order).model_dump(mode="json")
                        for order in entries
                    ],
                },
            )
        if len(positions) > 1:
            raise HTTPException(status_code=409, detail="hedge_unsupported")

        position = positions[0]
        if position.position_idx not in (0, None):
            raise HTTPException(status_code=409, detail="hedge_unsupported")
        if position.side == "long":
            side = OrderSide.sell
        elif position.side == "short":
            side = OrderSide.buy
        else:
            raise HTTPException(status_code=409, detail="position_side_unsupported")

        # BL-684 — 두 경로의 조회 실패 처리는 의도적으로 비대칭이다. flat 경로에서
        # fail-open 하면 실제 미체결 진입을 "flat"이라고 거짓 보고하지만, 열린 포지션
        # 경로에서 fail-closed 하면 조회 장애가 위험한 포지션 청산 자체를 봉쇄한다.
        # ★포획을 `ProviderError` 로 좁히지 마라. 좁히면 예상 못 한 예외 하나가 청산을
        #   막아 위 결정이 무효가 된다 — 여기서 중요한 것은 「무엇이 실패했나」가 아니라
        #   「그래도 나갔나」다. 대신 예외 타입을 로그에 남기고, 사용자 문구는 원인을
        #   단정하지 않는다(프로그래밍 오류를 「거래소 오류」라고 부르면 거짓 보고다).
        resting_entries_unknown = False
        try:
            entries = await self._fetch_resting_entries(credentials, session.symbol)
        except Exception as exc:
            logger.warning(
                "close_position_resting_entries_fetch_failed",
                extra={
                    "session_id": str(session.id),
                    "symbol": session.symbol,
                    "error": type(exc).__name__,
                },
                exc_info=True,
            )
            entries = []
            resting_entries_unknown = True

        request = OrderRequest(
            strategy_id=session.strategy_id,
            exchange_account_id=session.exchange_account_id,
            symbol=session.symbol,
            side=side,
            type=OrderType.market,
            quantity=position.size,
            price=None,
            leverage=_close_leverage(position.leverage, validated_settings),
            margin_mode=(
                validated_settings.margin_mode
                if validated_settings is not None
                else _FALLBACK_MARGIN_MODE
            ),
            reduce_only=True,
            risk_percent=None,
        )
        response, _ = await self._order_service.execute(request, idempotency_key=None, flatten=True)
        if resting_entries_unknown:
            detail = "reduce-only market close accepted · 미체결 진입 주문 확인 실패"
        elif entries:
            detail = (
                f"reduce-only market close accepted · 미체결 진입 주문 {len(entries)}건이 남아 있다"
            )
        else:
            detail = "reduce-only market close accepted"
        return ClosePositionResponse(
            order_id=response.id,
            state=response.state,
            detail=detail,
            resting_entries=[RestingEntryOrder.from_snapshot(order) for order in entries],
            resting_entries_unknown=resting_entries_unknown,
        )
