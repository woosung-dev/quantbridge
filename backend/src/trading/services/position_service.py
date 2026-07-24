# 거래소 포지션과 Pine 전략 open trade를 읽기 전용으로 대조하는 서비스
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException

from src.common.redis_client import get_redis_lock_pool
from src.strategy.repository import StrategyRepository
from src.trading.models import ExchangeMode, ExchangeName
from src.trading.providers import BybitFuturesProvider, PositionSnapshot
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.schemas import (
    ExchangePositionSchema,
    LiveSessionPositionsResponse,
    PositionDiffSchema,
)
from src.trading.services.account_service import ExchangeAccountService

logger = logging.getLogger(__name__)
_CACHE_TTL_SECONDS = 15
_LocalSource = Literal["strategy_state_report", "none"]
_MarketType = Literal["futures", "spot"]
_Verdict = Literal[
    "match", "qty_mismatch", "side_mismatch", "exchange_only", "local_only", "unknown"
]


def _get_position_redis_pool() -> Any:
    """테스트에서 Redis pool을 교체할 수 있는 간접 지점."""
    return get_redis_lock_pool()


class PositionService:
    def __init__(
        self,
        *,
        session_repo: LiveSignalSessionRepository,
        account_repo: ExchangeAccountRepository,
        strategy_repo: StrategyRepository,
        account_service: ExchangeAccountService,
        bybit_futures_provider: BybitFuturesProvider,
    ) -> None:
        self._session_repo = session_repo
        self._account_repo = account_repo
        self._strategy_repo = strategy_repo
        self._account_service = account_service
        self._bybit_futures_provider = bybit_futures_provider

    async def get_reconciliation(
        self, user_id: UUID, session_id: UUID
    ) -> LiveSessionPositionsResponse:
        session = await self._session_repo.get_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise HTTPException(status_code=404, detail="live session not found")

        local_open_trades_snapshot, local_source = await self._local_open_trades(session_id)
        account = await self._account_repo.get_by_id(session.exchange_account_id)
        if account is None:
            raise HTTPException(status_code=404, detail="live session not found")

        strategy = await self._strategy_repo.find_by_id_and_owner(session.strategy_id, user_id)
        settings = strategy.settings if strategy is not None else None
        market_type: _MarketType = (
            "spot"
            if isinstance(settings, dict) and settings.get("market_type") == "spot"
            else "futures"
        )
        unsupported = self._unsupported_response(
            session_id=session_id,
            symbol=session.symbol,
            market_type=market_type,
            account_mode=account.mode,
            account_exchange=account.exchange,
            settings=settings,
            local_open_trades_snapshot=local_open_trades_snapshot,
            local_source=local_source,
        )
        if unsupported is not None:
            return unsupported

        positions, fetched_at = await self._cached_exchange_positions(
            session_id, account.id, session.symbol
        )
        position_schemas = [
            ExchangePositionSchema(
                side=position.side,
                size=position.size,
                entry_price=position.entry_price,
                mark_price=position.mark_price,
                unrealized_pnl=position.unrealized_pnl,
                liquidation_price=position.liquidation_price,
                leverage=position.leverage,
                take_profit_price=self._decimal_string(position.take_profit_price),
                stop_loss_price=self._decimal_string(position.stop_loss_price),
            )
            for position in positions
        ]
        return LiveSessionPositionsResponse(
            session_id=session_id,
            symbol=session.symbol,
            market_type="futures",
            supported=True,
            reason=None,
            fetched_at=fetched_at,
            positions=position_schemas,
            local_open_trades_snapshot=local_open_trades_snapshot,
            diff=PositionDiffSchema(
                verdict=self._verdict(local_open_trades_snapshot, local_source, positions),
                local_source=local_source,
            ),
        )

    async def _local_open_trades(
        self, session_id: UUID
    ) -> tuple[list[dict[str, object]], _LocalSource]:
        state = await self._session_repo.get_state(session_id)
        if state is None or not isinstance(state.last_strategy_state_report, dict):
            return [], "none"
        open_trades = state.last_strategy_state_report.get("open_trades")
        if not isinstance(open_trades, list) or not all(isinstance(trade, dict) for trade in open_trades):
            return [], "none"
        return [dict(trade) for trade in open_trades], "strategy_state_report"

    def _unsupported_response(
        self,
        *,
        session_id: UUID,
        symbol: str,
        market_type: _MarketType,
        account_mode: ExchangeMode,
        account_exchange: ExchangeName,
        settings: dict[str, object] | None,
        local_open_trades_snapshot: list[dict[str, object]],
        local_source: _LocalSource,
    ) -> LiveSessionPositionsResponse | None:
        reason: str | None = None
        if account_mode != ExchangeMode.demo:
            reason = "live_mode_stub"
        elif account_exchange != ExchangeName.bybit:
            reason = "exchange_unsupported"
        elif market_type == "spot":
            reason = "spot_position_api_unsupported"
        elif not isinstance(settings, dict) or settings.get("leverage") is None:
            reason = "settings_unset"
        if reason is None:
            return None
        return LiveSessionPositionsResponse(
            session_id=session_id,
            symbol=symbol,
            market_type=market_type,
            supported=False,
            reason=reason,
            fetched_at=None,
            positions=[],
            local_open_trades_snapshot=local_open_trades_snapshot,
            diff=PositionDiffSchema(verdict="unknown", local_source=local_source),
        )

    async def _cached_exchange_positions(
        self, session_id: UUID, account_id: UUID, symbol: str
    ) -> tuple[list[PositionSnapshot], datetime]:
        cache_key = f"qb_pos_snapshot:{session_id}"
        cached = await self._read_cache(cache_key)
        if cached is not None:
            return cached

        credentials = await self._account_service.get_credentials_for_order(account_id)
        positions = await self._bybit_futures_provider.fetch_open_positions(credentials, symbol)
        fetched_at = datetime.now(UTC)
        await self._write_cache(cache_key, positions, fetched_at)
        return positions, fetched_at

    async def _read_cache(
        self, cache_key: str
    ) -> tuple[list[PositionSnapshot], datetime] | None:
        try:
            raw = await _get_position_redis_pool().get(cache_key)
            if raw is None:
                return None
            decoded = raw.decode() if isinstance(raw, bytes) else raw
            payload = json.loads(decoded)
            fetched_at = datetime.fromisoformat(payload["fetched_at"])
            if fetched_at.tzinfo is None:
                return None
            positions = [
                PositionSnapshot(
                    side=item["side"],
                    size=Decimal(item["size"]),
                    entry_price=Decimal(item["entry_price"]) if item["entry_price"] is not None else None,
                    mark_price=Decimal(item["mark_price"]) if item["mark_price"] is not None else None,
                    unrealized_pnl=Decimal(item["unrealized_pnl"])
                    if item["unrealized_pnl"] is not None
                    else None,
                    liquidation_price=Decimal(item["liquidation_price"])
                    if item["liquidation_price"] is not None
                    else None,
                    leverage=Decimal(item["leverage"]) if item["leverage"] is not None else None,
                    take_profit_price=Decimal(item["take_profit_price"])
                    if item["take_profit_price"] is not None
                    else None,
                    stop_loss_price=Decimal(item["stop_loss_price"])
                    if item["stop_loss_price"] is not None
                    else None,
                )
                for item in payload["positions"]
            ]
            return positions, fetched_at
        except Exception as exc:
            logger.warning("position_snapshot_cache_read_failed", extra={"error": type(exc).__name__})
            return None

    async def _write_cache(
        self, cache_key: str, positions: list[PositionSnapshot], fetched_at: datetime
    ) -> None:
        payload = {
            "fetched_at": fetched_at.isoformat(),
            "positions": [
                {
                    "side": position.side,
                    "size": str(position.size),
                    "entry_price": self._decimal_string(position.entry_price),
                    "mark_price": self._decimal_string(position.mark_price),
                    "unrealized_pnl": self._decimal_string(position.unrealized_pnl),
                    "liquidation_price": self._decimal_string(position.liquidation_price),
                    "leverage": self._decimal_string(position.leverage),
                    "take_profit_price": self._decimal_string(position.take_profit_price),
                    "stop_loss_price": self._decimal_string(position.stop_loss_price),
                }
                for position in positions
            ],
        }
        try:
            await _get_position_redis_pool().set(
                cache_key, json.dumps(payload), ex=_CACHE_TTL_SECONDS
            )
        except Exception as exc:  # 캐시 장애는 거래소 read-only 대조를 막지 않는다.
            logger.warning("position_snapshot_cache_write_failed", extra={"error": type(exc).__name__})

    @staticmethod
    def _decimal_string(value: Decimal | None) -> str | None:
        return str(value) if value is not None else None

    @staticmethod
    def _verdict(
        local_open_trades_snapshot: list[dict[str, object]],
        local_source: _LocalSource,
        positions: list[PositionSnapshot],
    ) -> _Verdict:
        if local_source == "none":
            return "unknown"
        local_sizes: dict[str, Decimal] = {}
        try:
            for trade in local_open_trades_snapshot:
                side = trade["direction"]
                if side not in ("long", "short"):
                    return "unknown"
                local_sizes[side] = local_sizes.get(side, Decimal("0")) + Decimal(
                    str(trade["qty"])
                )
        except (InvalidOperation, KeyError, TypeError, ValueError):
            return "unknown"

        exchange_sizes: dict[str, Decimal] = {}
        for position in positions:
            if position.side not in ("long", "short"):
                return "unknown"
            exchange_sizes[position.side] = exchange_sizes.get(position.side, Decimal("0")) + position.size

        if not local_sizes and not exchange_sizes:
            return "match"
        if not local_sizes:
            return "exchange_only"
        if not exchange_sizes:
            return "local_only"
        if set(local_sizes) != set(exchange_sizes):
            return "side_mismatch"
        return "match" if local_sizes == exchange_sizes else "qty_mismatch"
