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
from src.trading.providers import (
    BybitFuturesProvider,
    ConditionalOrderSnapshot,
    PositionSnapshot,
)
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.schemas import (
    AccountPositionRow,
    AccountPositionsResponse,
    ExchangePositionSchema,
    LiveSessionPositionsResponse,
    PositionDiffSchema,
)
from src.trading.services.account_service import ExchangeAccountService

logger = logging.getLogger(__name__)
_CACHE_TTL_SECONDS = 15
# ccxt bybit 는 심볼 없는 포지션 조회에서 settleCoin 을 defaultSettle(=USDT) 로 채운다.
# 응답에 이 값을 실어 "무엇이 조회 범위 밖인가" 를 화면이 숨기지 않게 한다.
_ACCOUNT_SETTLE_COIN = "USDT"
_LocalSource = Literal["strategy_state_report", "none"]
_CloseBlockedReason = Literal[
    "no_owning_session",
    "hedge_unsupported",
    "read_only_key",
    "position_side_unsupported",
]
_MarketType = Literal["futures", "spot"]
_Verdict = Literal[
    "match", "qty_mismatch", "side_mismatch", "exchange_only", "local_only", "unknown"
]


def position_snapshot_cache_key(session_id: UUID) -> str:
    """세션별 거래소 포지션 스냅샷 Redis 키를 만든다."""
    return f"qb_pos_snapshot:{session_id}"


def account_position_snapshot_cache_key(account_id: UUID) -> str:
    """계정별 거래소 포지션 스냅샷 Redis 키를 만든다.

    ★세션 캐시(`position_snapshot_cache_key`)와 **네임스페이스를 분리**한다. 같은
    키를 쓰면 계정 전체 조회 결과가 세션별 대조표의 스냅샷을 덮어써 대조 판정이
    틀린 근거 위에 서게 된다.
    """
    return f"qb_acct_pos_snapshot:{account_id}"


def _position_to_payload(position: PositionSnapshot) -> dict[str, Any]:
    """`PositionSnapshot` → Redis 직렬화 dict."""
    return {
        "side": position.side,
        "size": str(position.size),
        "entry_price": _decimal_string(position.entry_price),
        "mark_price": _decimal_string(position.mark_price),
        "unrealized_pnl": _decimal_string(position.unrealized_pnl),
        "liquidation_price": _decimal_string(position.liquidation_price),
        "leverage": _decimal_string(position.leverage),
        "take_profit_price": _decimal_string(position.take_profit_price),
        "stop_loss_price": _decimal_string(position.stop_loss_price),
        "position_idx": position.position_idx,
        "trailing_stop": _decimal_string(position.trailing_stop),
    }


def _position_from_payload(item: dict[str, Any]) -> PositionSnapshot:
    """Redis 직렬화 dict → `PositionSnapshot`."""
    return PositionSnapshot(
        side=item["side"],
        size=Decimal(item["size"]),
        entry_price=_decimal_or_none(item["entry_price"]),
        mark_price=_decimal_or_none(item["mark_price"]),
        unrealized_pnl=_decimal_or_none(item["unrealized_pnl"]),
        liquidation_price=_decimal_or_none(item["liquidation_price"]),
        leverage=_decimal_or_none(item["leverage"]),
        take_profit_price=_decimal_or_none(item["take_profit_price"]),
        stop_loss_price=_decimal_or_none(item["stop_loss_price"]),
        position_idx=int(item["position_idx"]) if item.get("position_idx") is not None else None,
        trailing_stop=_decimal_or_none(item.get("trailing_stop")),
    )


def _decimal_string(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _decimal_or_none(value: Any) -> Decimal | None:
    return Decimal(value) if value is not None else None


def _merged_prices(
    kind: str,
    full_price: Decimal | None,
    belonging_orders: list[ConditionalOrderSnapshot],
    mark_price: Decimal | None,
) -> list[str]:
    """포지션 부착값과 조건부 주문 가격을 표시 순서로 합친다."""
    conditional_prices = [
        price
        for order in belonging_orders
        if order.kind == kind
        for price in [order.price if order.price is not None else order.trigger_price]
        if price is not None and price != full_price
    ]
    if mark_price is not None:
        mark = mark_price
        conditional_prices.sort(key=lambda price: abs(price - mark))
    values = ([full_price] if full_price is not None else []) + conditional_prices
    return [str(price) for price in values]


def _get_position_redis_pool() -> Any:
    """테스트에서 Redis pool을 교체할 수 있는 간접 지점."""
    return get_redis_lock_pool()


def _exchange_position_schema(position: PositionSnapshot) -> ExchangePositionSchema:
    """계정 스코프 행의 포지션 스키마.

    ★세션 스코프와 달리 **별도 조건부 주문을 합치지 않는다.** 그건 심볼마다 REST
    왕복이 더 필요하고, 이 표의 용도는 대조가 아니라 잔여 노출 관리다. 따라서
    익절/손절은 포지션 부착값만 담고, 그 사실을 화면 각주가 말한다.
    """
    return ExchangePositionSchema(
        side=position.side,
        size=position.size,
        entry_price=position.entry_price,
        mark_price=position.mark_price,
        unrealized_pnl=position.unrealized_pnl,
        liquidation_price=position.liquidation_price,
        leverage=position.leverage,
        take_profit_prices=_merged_prices("tp", position.take_profit_price, [], None),
        stop_loss_prices=_merged_prices("sl", position.stop_loss_price, [], None),
        has_trailing_stop=position.trailing_stop is not None,
    )


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

        positions, conditional_orders, fetched_at = await self._cached_exchange_positions(
            session_id, account.id, session.symbol
        )
        position_schemas = []
        for position in positions:
            reducing_side = (
                "sell"
                if position.side == "long"
                else "buy"
                if position.side == "short"
                else None
            )
            belonging_orders = [
                order
                for order in conditional_orders
                if order.reduce_only
                and order.side == reducing_side
                and (order.position_idx or 0) == (position.position_idx or 0)
            ]

            position_schemas.append(
                ExchangePositionSchema(
                    side=position.side,
                    size=position.size,
                    entry_price=position.entry_price,
                    mark_price=position.mark_price,
                    unrealized_pnl=position.unrealized_pnl,
                    liquidation_price=position.liquidation_price,
                    leverage=position.leverage,
                    take_profit_prices=_merged_prices(
                        "tp",
                        position.take_profit_price,
                        belonging_orders,
                        position.mark_price,
                    ),
                    stop_loss_prices=_merged_prices(
                        "sl",
                        position.stop_loss_price,
                        belonging_orders,
                        position.mark_price,
                    ),
                    has_trailing_stop=position.trailing_stop is not None
                    or any(order.kind == "trail" for order in belonging_orders),
                )
            )
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

    async def get_account_positions(
        self, user_id: UUID, account_id: UUID
    ) -> AccountPositionsResponse:
        """BL-498 — 계정에 남아 있는 거래소 포지션을 세션과 무관하게 반환한다.

        세션 스코프 대조는 활성 세션을 순회하므로 활성 세션이 0건이면 아무것도
        렌더하지 않는다. fail-closed 종료가 주문만 걷고 포지션은 남기는 것은
        **설계**이므로 그 상태는 반복된다 — 그때 사용자에게 남는 것이 이 표다.
        """
        account = await self._account_repo.get_by_id(account_id)
        if account is None or account.user_id != user_id:
            raise HTTPException(status_code=404, detail="exchange account not found")

        reason = self._account_unsupported_reason(account.mode, account.exchange)
        if reason is not None:
            return AccountPositionsResponse(
                account_id=account_id,
                supported=False,
                reason=reason,
                fetched_at=None,
                rows=[],
                settle_coin=_ACCOUNT_SETTLE_COIN,
                truncated=False,
            )

        positions, fetched_at, truncated = await self._cached_account_positions(account_id)
        sessions = await self._session_repo.list_by_account(account_id, user_id=user_id)
        # ★hedge 판정은 심볼 단위다. `close_service` 는 그 심볼의 leg 이 2개 이상이거나
        #   `position_idx` 가 0/None 이 아니면 409 로 거부하므로(`close_service.py:66-71`),
        #   그런 행에 청산 버튼을 주면 **누르면 실패하는 버튼**이 된다.
        legs_by_symbol: dict[str, int] = {}
        for symbol, _ in positions:
            legs_by_symbol[symbol] = legs_by_symbol.get(symbol, 0) + 1

        rows: list[AccountPositionRow] = []
        for symbol, position in positions:
            hedged = legs_by_symbol[symbol] > 1 or position.position_idx not in (0, None)
            # `list_by_account` 는 최신순이므로 첫 일치가 가장 최근 세션이다.
            owning_session = next(
                (session for session in sessions if session.symbol == symbol), None
            )
            blocked_reason: _CloseBlockedReason | None = (
                "hedge_unsupported"
                if hedged
                else "read_only_key"
                if account.read_only is True
                else "no_owning_session"
                if owning_session is None
                else "position_side_unsupported"
                if position.side not in ("long", "short")
                else None
            )
            rows.append(
                AccountPositionRow(
                    symbol=symbol,
                    position=_exchange_position_schema(position),
                    closable_session_id=(
                        owning_session.id if blocked_reason is None and owning_session else None
                    ),
                    close_blocked_reason=blocked_reason,
                )
            )
        return AccountPositionsResponse(
            account_id=account_id,
            supported=True,
            reason=None,
            fetched_at=fetched_at,
            rows=rows,
            settle_coin=_ACCOUNT_SETTLE_COIN,
            truncated=truncated,
        )

    @staticmethod
    def _account_unsupported_reason(
        account_mode: ExchangeMode, account_exchange: ExchangeName
    ) -> str | None:
        """계정 스코프 조회의 미지원 사유. 세션 전용 조건(spot/settings)은 해당 없다."""
        if account_mode != ExchangeMode.demo:
            return "live_mode_stub"
        if account_exchange != ExchangeName.bybit:
            return "exchange_unsupported"
        return None

    async def _cached_account_positions(
        self, account_id: UUID
    ) -> tuple[list[tuple[str, PositionSnapshot]], datetime, bool]:
        cache_key = account_position_snapshot_cache_key(account_id)
        cached = await self._read_account_cache(cache_key)
        if cached is not None:
            return cached

        credentials = await self._account_service.get_credentials_for_order(account_id)
        positions, truncated = await self._bybit_futures_provider.fetch_all_open_positions(
            credentials
        )
        fetched_at = datetime.now(UTC)
        await self._write_account_cache(cache_key, positions, fetched_at, truncated)
        return positions, fetched_at, truncated

    async def _read_account_cache(
        self, cache_key: str
    ) -> tuple[list[tuple[str, PositionSnapshot]], datetime, bool] | None:
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
                (item["symbol"], _position_from_payload(item["position"]))
                for item in payload["rows"]
            ]
            return positions, fetched_at, bool(payload["truncated"])
        except Exception as exc:
            logger.warning(
                "account_position_snapshot_cache_read_failed",
                extra={"error": type(exc).__name__},
            )
            return None

    async def _write_account_cache(
        self,
        cache_key: str,
        positions: list[tuple[str, PositionSnapshot]],
        fetched_at: datetime,
        truncated: bool,
    ) -> None:
        payload = {
            "fetched_at": fetched_at.isoformat(),
            "truncated": truncated,
            "rows": [
                {"symbol": symbol, "position": _position_to_payload(position)}
                for symbol, position in positions
            ],
        }
        try:
            await _get_position_redis_pool().set(
                cache_key, json.dumps(payload), ex=_CACHE_TTL_SECONDS
            )
        except Exception as exc:  # 캐시 장애는 read-only 조회를 막지 않는다.
            logger.warning(
                "account_position_snapshot_cache_write_failed",
                extra={"error": type(exc).__name__},
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
    ) -> tuple[list[PositionSnapshot], list[ConditionalOrderSnapshot], datetime]:
        cache_key = position_snapshot_cache_key(session_id)
        cached = await self._read_cache(cache_key)
        if cached is not None:
            return cached

        credentials = await self._account_service.get_credentials_for_order(account_id)
        positions = await self._bybit_futures_provider.fetch_open_positions(credentials, symbol)
        conditional_orders = await self._bybit_futures_provider.fetch_open_conditional_orders(
            credentials, symbol
        )
        fetched_at = datetime.now(UTC)
        await self._write_cache(cache_key, positions, conditional_orders, fetched_at)
        return positions, conditional_orders, fetched_at

    async def _read_cache(
        self, cache_key: str
    ) -> tuple[list[PositionSnapshot], list[ConditionalOrderSnapshot], datetime] | None:
        try:
            raw = await _get_position_redis_pool().get(cache_key)
            if raw is None:
                return None
            decoded = raw.decode() if isinstance(raw, bytes) else raw
            payload = json.loads(decoded)
            fetched_at = datetime.fromisoformat(payload["fetched_at"])
            if fetched_at.tzinfo is None:
                return None
            conditional_order_items = payload.get("conditional_orders")
            if not isinstance(conditional_order_items, list):
                return None
            positions = [_position_from_payload(item) for item in payload["positions"]]
            conditional_orders = [
                ConditionalOrderSnapshot(
                    order_id=item["order_id"],
                    side=item["side"],
                    kind=item["kind"],
                    price=Decimal(item["price"]) if item["price"] is not None else None,
                    trigger_price=Decimal(item["trigger_price"])
                    if item["trigger_price"] is not None
                    else None,
                    qty=Decimal(item["qty"]) if item["qty"] is not None else None,
                    reduce_only=item["reduce_only"],
                    position_idx=int(item["position_idx"])
                    if item["position_idx"] is not None
                    else None,
                )
                for item in conditional_order_items
            ]
            return positions, conditional_orders, fetched_at
        except Exception as exc:
            logger.warning("position_snapshot_cache_read_failed", extra={"error": type(exc).__name__})
            return None

    async def _write_cache(
        self,
        cache_key: str,
        positions: list[PositionSnapshot],
        conditional_orders: list[ConditionalOrderSnapshot],
        fetched_at: datetime,
    ) -> None:
        payload = {
            "fetched_at": fetched_at.isoformat(),
            "positions": [_position_to_payload(position) for position in positions],
            "conditional_orders": [
                {
                    "order_id": order.order_id,
                    "side": order.side,
                    "kind": order.kind,
                    "price": self._decimal_string(order.price),
                    "trigger_price": self._decimal_string(order.trigger_price),
                    "qty": self._decimal_string(order.qty),
                    "reduce_only": order.reduce_only,
                    "position_idx": order.position_idx,
                }
                for order in conditional_orders
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
