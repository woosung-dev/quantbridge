# 라이브 세션의 단일 선물 포지션을 reduce-only 시장가로 청산하는 서비스
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError

from src.strategy.repository import StrategyRepository
from src.strategy.schemas import validate_strategy_settings
from src.trading.models import ExchangeMode, ExchangeName, OrderSide, OrderType
from src.trading.providers import BybitFuturesProvider
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.schemas import ClosePositionResponse, OrderRequest
from src.trading.services.account_service import ExchangeAccountService
from src.trading.services.order_service import OrderService


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

    async def close_position(self, user_id: UUID, session_id: UUID) -> ClosePositionResponse:
        session = await self._session_repo.get_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise HTTPException(status_code=404, detail="live session not found")

        account = await self._account_repo.get_by_id(session.exchange_account_id)
        if account is None:
            raise HTTPException(status_code=404, detail="live session not found")

        strategy = await self._strategy_repo.find_by_id_and_owner(session.strategy_id, user_id)
        settings = strategy.settings if strategy is not None else None
        try:
            validated_settings = validate_strategy_settings(settings)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail="settings_invalid") from exc
        if validated_settings is None:
            raise HTTPException(status_code=422, detail="settings_unset")
        if account.mode != ExchangeMode.demo:
            raise HTTPException(status_code=422, detail="live_mode_stub")
        if account.exchange != ExchangeName.bybit:
            raise HTTPException(status_code=422, detail="exchange_unsupported")

        credentials = await self._account_service.get_credentials_for_order(account.id)
        positions = await self._bybit_futures_provider.fetch_open_positions(
            credentials, session.symbol
        )
        if not positions:
            raise HTTPException(status_code=409, detail="no_open_position")
        if len(positions) > 1:
            raise HTTPException(status_code=409, detail="hedge_unsupported")

        position = positions[0]
        if position.side == "long":
            side = OrderSide.sell
        elif position.side == "short":
            side = OrderSide.buy
        else:
            raise HTTPException(status_code=409, detail="position_side_unsupported")
        request = OrderRequest(
            strategy_id=session.strategy_id,
            exchange_account_id=session.exchange_account_id,
            symbol=session.symbol,
            side=side,
            type=OrderType.market,
            quantity=position.size,
            price=None,
            leverage=(
                int(position.leverage)
                if position.leverage is not None
                else int(validated_settings.leverage)
            ),
            margin_mode=validated_settings.margin_mode,
            reduce_only=True,
            risk_percent=None,
        )
        response, _ = await self._order_service.execute(
            request, idempotency_key=None, flatten=True
        )
        return ClosePositionResponse(
            order_id=response.id,
            state=response.state,
            detail="reduce-only market close accepted",
        )
