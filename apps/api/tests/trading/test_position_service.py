# 포지션 대조 서비스와 Bybit hedge 스냅샷을 검증한다
from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace
from typing import get_args
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.trading.models import ExchangeMode, ExchangeName
from src.trading.providers import ConditionalOrderSnapshot, Credentials, PositionSnapshot
from src.trading.services.position_service import PositionService

_SETTINGS = {"leverage": 3, "margin_mode": "cross", "position_size_pct": 10.0}


class _FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, *, ex: int) -> None:
        assert ex == 15
        self.values[key] = value


def _position(
    *,
    side: str = "long",
    size: str = "1",
    mark_price: Decimal | None = Decimal("101"),
    take_profit_price: Decimal | None = None,
    stop_loss_price: Decimal | None = None,
    position_idx: int | None = None,
    trailing_stop: Decimal | None = None,
) -> PositionSnapshot:
    return PositionSnapshot(
        side=side,
        size=Decimal(size),
        entry_price=Decimal("100"),
        mark_price=mark_price,
        unrealized_pnl=Decimal("1"),
        liquidation_price=None,
        leverage=Decimal("3"),
        take_profit_price=take_profit_price,
        stop_loss_price=stop_loss_price,
        position_idx=position_idx,
        trailing_stop=trailing_stop,
    )


def _service(
    *,
    report=None,
    positions=None,
    conditional_orders=None,
    mode=ExchangeMode.demo,
    exchange=ExchangeName.bybit,
    settings=_SETTINGS,
):
    user_id = uuid4()
    session = SimpleNamespace(
        id=uuid4(),
        user_id=user_id,
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
    )
    state = None if report is None else SimpleNamespace(last_strategy_state_report=report)
    session_repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=session), get_state=AsyncMock(return_value=state)
    )
    account_repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=SimpleNamespace(id=session.exchange_account_id, mode=mode, exchange=exchange))
    )
    strategy_repo = SimpleNamespace(
        find_by_id_and_owner=AsyncMock(return_value=SimpleNamespace(settings=settings))
    )
    account_service = SimpleNamespace(get_credentials_for_order=AsyncMock(return_value=object()))
    provider = SimpleNamespace(
        fetch_open_positions=AsyncMock(return_value=positions or []),
        fetch_open_conditional_orders=AsyncMock(return_value=conditional_orders or []),
    )
    return (
        PositionService(
            session_repo=session_repo,
            account_repo=account_repo,
            strategy_repo=strategy_repo,
            account_service=account_service,
            bybit_futures_provider=provider,
        ),
        user_id,
        session,
        provider,
    )


async def test_reconciliation_match(monkeypatch):
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, session, _ = _service(
        report={"open_trades": [{"direction": "long", "qty": 1}]}, positions=[_position()]
    )
    result = await service.get_reconciliation(user_id, session.id)
    assert result.diff.verdict == "match"


async def test_reconciliation_qty_mismatch(monkeypatch):
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, session, _ = _service(
        report={"open_trades": [{"direction": "long", "qty": 1}]}, positions=[_position(size="2")]
    )
    result = await service.get_reconciliation(user_id, session.id)
    assert result.diff.verdict == "qty_mismatch"


async def test_reconciliation_side_mismatch(monkeypatch):
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, session, _ = _service(
        report={"open_trades": [{"direction": "long", "qty": 1}]},
        positions=[_position(side="short")],
    )
    result = await service.get_reconciliation(user_id, session.id)
    assert result.diff.verdict == "side_mismatch"


async def test_reconciliation_exchange_only(monkeypatch):
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, session, _ = _service(report={"open_trades": []}, positions=[_position()])
    result = await service.get_reconciliation(user_id, session.id)
    assert result.diff.verdict == "exchange_only"


async def test_reconciliation_local_only(monkeypatch):
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, session, _ = _service(
        report={"open_trades": [{"direction": "long", "qty": 1}]}
    )
    result = await service.get_reconciliation(user_id, session.id)
    assert result.diff.verdict == "local_only"


async def test_reconciliation_unknown_when_state_not_evaluated(monkeypatch):
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, session, _ = _service(report=None, positions=[_position()])
    result = await service.get_reconciliation(user_id, session.id)
    assert result.diff.verdict == "unknown"
    assert result.diff.local_source == "none"


@pytest.mark.parametrize(
    ("mode", "exchange", "settings", "reason"),
    [
        (ExchangeMode.live, ExchangeName.bybit, _SETTINGS, "live_mode_stub"),
        (ExchangeMode.demo, ExchangeName.okx, _SETTINGS, "exchange_unsupported"),
        (ExchangeMode.demo, ExchangeName.bybit, None, "settings_unset"),
    ],
)
async def test_reconciliation_unsupported_branches(mode, exchange, settings, reason):
    service, user_id, session, provider = _service(
        report={"open_trades": []}, mode=mode, exchange=exchange, settings=settings
    )
    result = await service.get_reconciliation(user_id, session.id)
    assert result.supported is False
    assert result.reason == reason
    provider.fetch_open_positions.assert_not_awaited()


async def test_reconciliation_spot_defensive_branch():
    service, user_id, session, provider = _service(
        report={"open_trades": []}, settings={**_SETTINGS, "market_type": "spot"}
    )
    result = await service.get_reconciliation(user_id, session.id)
    assert result.market_type == "spot"
    assert result.reason == "spot_position_api_unsupported"
    provider.fetch_open_positions.assert_not_awaited()


async def test_reconciliation_ownership_is_404():
    service, user_id, session, _ = _service(report={"open_trades": []})
    service._session_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(user_id=uuid4())
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.get_reconciliation(user_id, session.id)
    assert exc_info.value.status_code == 404


async def test_reconciliation_cache_hit_skips_provider(monkeypatch):
    from src.trading.services import position_service

    redis = _FakeRedis()
    monkeypatch.setattr(position_service, "_get_position_redis_pool", lambda: redis)
    service, user_id, session, provider = _service(
        report={"open_trades": [{"direction": "long", "qty": 1}]}, positions=[_position()]
    )
    await service.get_reconciliation(user_id, session.id)
    await service.get_reconciliation(user_id, session.id)
    assert provider.fetch_open_positions.await_count == 1


async def test_reconciliation_serializes_position_tpsl(monkeypatch):
    from src.trading.services import position_service

    redis = _FakeRedis()
    monkeypatch.setattr(position_service, "_get_position_redis_pool", lambda: redis)
    service, user_id, session, provider = _service(
        report={"open_trades": [{"direction": "long", "qty": 1}]},
        positions=[_position(take_profit_price=Decimal("110"), stop_loss_price=None)],
    )

    result = await service.get_reconciliation(user_id, session.id)
    cached_result = await service.get_reconciliation(user_id, session.id)

    assert result.positions[0].take_profit_prices == ["110"]
    assert result.positions[0].stop_loss_prices == []
    assert cached_result.positions[0].take_profit_prices == ["110"]
    assert cached_result.positions[0].stop_loss_prices == []
    provider.fetch_open_positions.assert_awaited_once()


async def test_reconciliation_merges_full_and_conditional_tpsl(monkeypatch):
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    conditional_orders = [
        ConditionalOrderSnapshot("tp-near", "sell", "tp", Decimal("102"), None, None, True, 0),
        ConditionalOrderSnapshot("tp-far", "sell", "tp", None, Decimal("105"), None, True, 0),
        ConditionalOrderSnapshot(
            "tp-duplicate", "sell", "tp", Decimal("110"), None, None, True, 0
        ),
        ConditionalOrderSnapshot("sl-near", "sell", "sl", Decimal("97"), None, None, True, 0),
        ConditionalOrderSnapshot("sl-far", "sell", "sl", None, Decimal("95"), None, True, 0),
        ConditionalOrderSnapshot(
            "sl-duplicate", "sell", "sl", Decimal("90"), None, None, True, 0
        ),
        ConditionalOrderSnapshot(
            "wrong-side", "buy", "tp", Decimal("103"), None, None, True, 0
        ),
        ConditionalOrderSnapshot(
            "wrong-index", "sell", "sl", Decimal("96"), None, None, True, 1
        ),
        ConditionalOrderSnapshot("trail", "sell", "trail", Decimal("98"), None, None, True, 0),
    ]
    service, user_id, session, _ = _service(
        report={"open_trades": [{"direction": "long", "qty": 1}]},
        positions=[
            _position(
                mark_price=Decimal("100"),
                take_profit_price=Decimal("110"),
                stop_loss_price=Decimal("90"),
                position_idx=0,
                trailing_stop=Decimal("2"),
            )
        ],
        conditional_orders=conditional_orders,
    )

    result = await service.get_reconciliation(user_id, session.id)

    assert result.positions[0].take_profit_prices == ["110", "102", "105"]
    assert result.positions[0].stop_loss_prices == ["90", "97", "95"]
    assert result.positions[0].has_trailing_stop is True


async def test_has_trailing_stop_true_from_conditional_trail_only(monkeypatch):
    """codex 최종 P1 — position.trailing_stop 부재라도 조건부 trail 주문이면 has_trailing_stop True."""
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, session, _ = _service(
        report={"open_trades": [{"direction": "long", "qty": 1}]},
        positions=[
            _position(
                mark_price=Decimal("100"),
                take_profit_price=None,
                stop_loss_price=None,
                position_idx=0,
                trailing_stop=None,
            )
        ],
        conditional_orders=[
            ConditionalOrderSnapshot("trail", "sell", "trail", Decimal("98"), None, None, True, 0),
        ],
    )

    result = await service.get_reconciliation(user_id, session.id)

    assert result.positions[0].has_trailing_stop is True
    # trail 은 거리 기반이라 익절/손절 가격 열에 섞이지 않는다.
    assert result.positions[0].take_profit_prices == []
    assert result.positions[0].stop_loss_prices == []


async def test_position_snapshot_old_cache_payload_is_a_miss(monkeypatch):
    from src.trading.services import position_service

    redis = _FakeRedis()
    cache_key = "old"
    redis.values[cache_key] = json.dumps(
        {
            "fetched_at": "2026-01-01T00:00:00+00:00",
            "positions": [
                {
                    "side": "long",
                    "size": "1",
                    "entry_price": "100",
                    "mark_price": "101",
                    "unrealized_pnl": "1",
                    "liquidation_price": None,
                    "leverage": "3",
                    "take_profit_price": "110",
                    "stop_loss_price": "90",
                }
            ],
        }
    )
    monkeypatch.setattr(position_service, "_get_position_redis_pool", lambda: redis)
    service, _, _, _ = _service()

    assert await service._read_cache(cache_key) is None


def test_exchange_position_schema_plural_fields_round_trip() -> None:
    from src.trading.schemas import ExchangePositionSchema

    schema = ExchangePositionSchema.model_validate(
        {
            "side": "long",
            "size": "1",
            "entry_price": "100",
            "mark_price": "101",
            "unrealized_pnl": "1",
            "liquidation_price": None,
            "leverage": "3",
            "take_profit_prices": ["110", "112"],
            "stop_loss_prices": ["90"],
            "has_trailing_stop": True,
        }
    )

    assert schema.model_dump(mode="json")["take_profit_prices"] == ["110", "112"]
    assert schema.model_dump(mode="json")["stop_loss_prices"] == ["90"]
    assert schema.has_trailing_stop is True


async def test_bybit_fetch_open_positions_returns_both_hedge_legs(monkeypatch):
    import ccxt.async_support as ccxt_async

    from src.trading.providers import BybitFuturesProvider

    exchange = MagicMock()
    exchange.fetch_positions = AsyncMock(
        return_value=[
            {
                "contracts": "1.25",
                "side": "long",
                "entryPrice": "100",
                "markPrice": "101",
                "unrealizedPnl": "1.25",
                "liquidationPrice": "50",
                "leverage": "3",
            },
            {
                "contracts": "0.5",
                "side": "short",
                "entryPrice": "102",
                "markPrice": "101",
                "unrealizedPnl": "0.5",
                "liquidationPrice": None,
                "leverage": "3",
            },
        ]
    )
    exchange.close = AsyncMock()
    monkeypatch.setattr(ccxt_async, "bybit", MagicMock(return_value=exchange))

    positions = await BybitFuturesProvider().fetch_open_positions(
        Credentials(api_key="key", api_secret="secret"), "BTC/USDT"
    )

    assert [(position.side, position.size) for position in positions] == [
        ("long", Decimal("1.25")),
        ("short", Decimal("0.5")),
    ]
    assert positions[0].mark_price == Decimal("101")
    assert positions[1].liquidation_price is None
    exchange.fetch_positions.assert_awaited_once_with(["BTC/USDT:USDT"])
    exchange.close.assert_awaited_once()


async def test_bybit_fetch_open_positions_normalizes_zero_and_empty_tpsl(monkeypatch):
    import ccxt.async_support as ccxt_async

    from src.trading.providers import BybitFuturesProvider

    exchange = MagicMock()
    exchange.fetch_positions = AsyncMock(
        return_value=[
            {"contracts": "1", "side": "long", "takeProfitPrice": 0, "stopLossPrice": 0},
            {"contracts": "1", "side": "long", "takeProfitPrice": "0", "stopLossPrice": "0"},
            {"contracts": "1", "side": "long", "takeProfitPrice": "", "stopLossPrice": ""},
            {"contracts": "1", "side": "long", "takeProfitPrice": None, "stopLossPrice": None},
            {
                "contracts": "1",
                "side": "long",
                "takeProfitPrice": "102.5",
                "stopLossPrice": "99.5",
            },
        ]
    )
    exchange.close = AsyncMock()
    monkeypatch.setattr(ccxt_async, "bybit", MagicMock(return_value=exchange))

    positions = await BybitFuturesProvider().fetch_open_positions(
        Credentials(api_key="key", api_secret="secret"), "BTC/USDT"
    )

    assert [(p.take_profit_price, p.stop_loss_price) for p in positions] == [
        (None, None),
        (None, None),
        (None, None),
        (None, None),
        (Decimal("102.5"), Decimal("99.5")),
    ]


async def test_bybit_fetch_open_conditional_orders_unions_and_classifies(monkeypatch):
    import ccxt.async_support as ccxt_async

    from src.trading.providers import BybitFuturesProvider

    exchange = MagicMock()
    exchange.fetch_open_orders = AsyncMock(
        side_effect=[
            [
                {
                    "id": "tp",
                    "side": "Sell",
                    "price": "110",
                    "amount": "1",
                    "info": {
                        "stopOrderType": "TakeProfit",
                        "reduceOnly": "true",
                        "positionIdx": "0",
                    },
                },
                {
                    "id": "sl",
                    "side": "Sell",
                    "triggerPrice": "90",
                    "info": {
                        "stopOrderType": "PartialStopLoss",
                        "reduceOnly": True,
                        "positionIdx": "0",
                    },
                },
                {
                    "id": "entry",
                    "side": "Buy",
                    "price": "100",
                    "info": {"stopOrderType": "Stop", "reduceOnly": False},
                },
            ],
            [
                {
                    "id": "tp",
                    "side": "Sell",
                    "price": "110",
                    "info": {"stopOrderType": "TakeProfit", "reduceOnly": "true", "positionIdx": "0"},
                },
                {
                    "id": "trail",
                    "side": "Sell",
                    "info": {"stopOrderType": "TrailingStop", "reduceOnly": "true"},
                },
                {
                    "id": "other",
                    "side": "Sell",
                    "info": {"stopOrderType": "Stop", "reduceOnly": "true"},
                },
            ],
        ]
    )
    exchange.close = AsyncMock()
    monkeypatch.setattr(ccxt_async, "bybit", MagicMock(return_value=exchange))

    orders = await BybitFuturesProvider().fetch_open_conditional_orders(
        Credentials(api_key="key", api_secret="secret"), "BTC/USDT"
    )

    assert [(order.order_id, order.kind) for order in orders] == [
        ("tp", "tp"),
        ("sl", "sl"),
        ("trail", "trail"),
        ("other", "other"),
    ]
    assert orders[0].price == Decimal("110")
    assert orders[1].trigger_price == Decimal("90")
    assert orders[0].qty == Decimal("1")
    assert orders[0].position_idx == 0
    assert exchange.fetch_open_orders.await_args_list[0].args == ("BTC/USDT:USDT",)
    assert exchange.fetch_open_orders.await_args_list[0].kwargs == {
        "params": {"category": "linear", "paginate": True}
    }
    assert exchange.fetch_open_orders.await_args_list[1].kwargs == {
        "params": {"category": "linear", "trigger": True, "paginate": True}
    }


async def test_bybit_fetch_open_positions_fails_loud_on_unparseable_stop_loss(monkeypatch):
    """§7.3 Surface Trust — 파싱 불가한 손절가를 None 으로 삼키면 안 된다.

    None 으로 삼키면 코크핏 §03 이 "손절 없음(—)" 이라 말하는데 실제로는 거래소에 손절이
    걸려 있는 false negative 가 된다. 사용자가 무방비라고 오판하고 수동 개입할 수 있으므로
    ProviderError 로 fail-loud 해야 한다.
    """
    import ccxt.async_support as ccxt_async

    from src.trading.exceptions import ProviderError
    from src.trading.providers import BybitFuturesProvider

    exchange = MagicMock()
    exchange.fetch_positions = AsyncMock(
        return_value=[
            {
                "contracts": "1",
                "side": "long",
                "takeProfitPrice": "110",
                "stopLossPrice": "N/A",
                "info": {"positionIdx": "0"},
            }
        ]
    )
    exchange.close = AsyncMock()
    monkeypatch.setattr(ccxt_async, "bybit", MagicMock(return_value=exchange))

    with pytest.raises(ProviderError):
        await BybitFuturesProvider().fetch_open_positions(
            Credentials(api_key="key", api_secret="secret"), "BTC/USDT"
        )
    exchange.close.assert_awaited_once()


async def test_bybit_fetch_open_conditional_orders_fails_loud_on_unparseable_trigger(monkeypatch):
    """조건부 주문 트리거가도 같은 이유로 fail-loud 한다(§7.3)."""
    import ccxt.async_support as ccxt_async

    from src.trading.exceptions import ProviderError
    from src.trading.providers import BybitFuturesProvider

    exchange = MagicMock()
    exchange.fetch_open_orders = AsyncMock(
        side_effect=[
            [
                {
                    "id": "sl",
                    "side": "Sell",
                    "triggerPrice": "not-a-number",
                    "info": {"stopOrderType": "StopLoss", "reduceOnly": "true"},
                }
            ],
            [],
        ]
    )
    exchange.close = AsyncMock()
    monkeypatch.setattr(ccxt_async, "bybit", MagicMock(return_value=exchange))

    with pytest.raises(ProviderError):
        await BybitFuturesProvider().fetch_open_conditional_orders(
            Credentials(api_key="key", api_secret="secret"), "BTC/USDT"
        )


# ── BL-498 계정 스코프 포지션 ──────────────────────────────────────────


def _account_service(
    *,
    account_positions=None,
    sessions=None,
    mode=ExchangeMode.demo,
    exchange=ExchangeName.bybit,
    read_only=None,
):
    """계정 스코프 조회용 서비스. 세션 순회가 아니라 계정 1콜이 원천이다."""
    user_id = uuid4()
    account_id = uuid4()
    session_repo = SimpleNamespace(
        get_by_id=AsyncMock(return_value=None),
        get_state=AsyncMock(return_value=None),
        list_by_account=AsyncMock(return_value=sessions or []),
    )
    account_repo = SimpleNamespace(
        get_by_id=AsyncMock(
            return_value=SimpleNamespace(
                id=account_id,
                user_id=user_id,
                mode=mode,
                exchange=exchange,
                read_only=read_only,
            )
        )
    )
    provider = SimpleNamespace(
        fetch_all_open_positions=AsyncMock(return_value=(account_positions or [], False)),
    )
    return (
        PositionService(
            session_repo=session_repo,
            account_repo=account_repo,
            strategy_repo=SimpleNamespace(),
            account_service=SimpleNamespace(
                get_credentials_for_order=AsyncMock(return_value=object())
            ),
            bybit_futures_provider=provider,
        ),
        user_id,
        account_id,
        session_repo,
        provider,
    )


def _live_session(account_id, *, symbol="BTC/USDT"):
    return SimpleNamespace(id=uuid4(), symbol=symbol, exchange_account_id=account_id)


async def test_account_positions_render_without_any_active_session(monkeypatch):
    """★BL-498 본체 — 활성 세션이 0건이어도 계정에 남은 포지션이 나온다."""
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, account_id, _, _ = _account_service(
        account_positions=[("BTC/USDT", _position(position_idx=0))],
        sessions=[],
    )

    result = await service.get_account_positions(user_id, account_id)

    assert result.supported is True
    assert [row.symbol for row in result.rows] == ["BTC/USDT"]
    assert result.settle_coin == "USDT"


async def test_account_position_is_closable_via_inactive_owning_session(monkeypatch):
    """★청산 귀속 — 비활성 세션도 귀속 대상이다. fail-closed 종료가 남긴 게 정확히 그것이다."""
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, account_id, session_repo, _ = _account_service(
        account_positions=[("BTC/USDT", _position(position_idx=0))],
    )
    owning = _live_session(account_id)
    session_repo.list_by_account = AsyncMock(return_value=[owning])

    result = await service.get_account_positions(user_id, account_id)

    assert result.rows[0].closable_session_id == owning.id
    assert result.rows[0].close_blocked_reason is None
    # 소유 검증은 계정만으로 끝내지 않는다 — 귀속을 정하는 조회이므로 user_id 도 건다.
    assert session_repo.list_by_account.await_args.kwargs["user_id"] == user_id


async def test_account_position_without_owning_session_is_not_closable(monkeypatch):
    """★주문 원장은 `strategy_id` 를 요구한다. 귀속 못 하면 닫지 않고 사유를 남긴다."""
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, account_id, session_repo, _ = _account_service(
        account_positions=[("ETH/USDT", _position(position_idx=0))],
    )
    session_repo.list_by_account = AsyncMock(return_value=[_live_session(account_id)])

    result = await service.get_account_positions(user_id, account_id)

    assert result.rows[0].closable_session_id is None
    assert result.rows[0].close_blocked_reason == "no_owning_session"


async def test_read_only_account_position_is_not_closable(monkeypatch):
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, account_id, session_repo, _ = _account_service(
        account_positions=[("BTC/USDT", _position(position_idx=0))],
        read_only=True,
    )
    session_repo.list_by_account = AsyncMock(return_value=[_live_session(account_id)])

    result = await service.get_account_positions(user_id, account_id)

    assert result.rows[0].closable_session_id is None
    assert result.rows[0].close_blocked_reason == "read_only_key"


async def test_hedge_legs_are_not_closable(monkeypatch):
    """★`close_service` 는 leg 2개를 409 로 거부한다. 누르면 실패하는 버튼을 주지 않는다."""
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, account_id, session_repo, _ = _account_service(
        account_positions=[
            ("BTC/USDT", _position(side="long", position_idx=1)),
            ("BTC/USDT", _position(side="short", position_idx=2)),
        ],
    )
    session_repo.list_by_account = AsyncMock(return_value=[_live_session(account_id)])

    result = await service.get_account_positions(user_id, account_id)

    assert [row.close_blocked_reason for row in result.rows] == [
        "hedge_unsupported",
        "hedge_unsupported",
    ]
    assert all(row.closable_session_id is None for row in result.rows)


async def test_non_zero_position_idx_alone_is_not_closable(monkeypatch):
    """★단일 leg 라도 `position_idx` 가 0/None 이 아니면 감소전용 청산이 거부된다."""
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, account_id, session_repo, _ = _account_service(
        account_positions=[("BTC/USDT", _position(position_idx=2))],
    )
    session_repo.list_by_account = AsyncMock(return_value=[_live_session(account_id)])

    result = await service.get_account_positions(user_id, account_id)

    assert result.rows[0].close_blocked_reason == "hedge_unsupported"


async def test_unsupported_position_side_is_not_closable(monkeypatch):
    """거래소가 long/short 밖의 side를 주면 close_service도 409으로 거부한다."""
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, account_id, session_repo, _ = _account_service(
        account_positions=[("BTC/USDT", _position(side="flat", position_idx=0))],
    )
    session_repo.list_by_account = AsyncMock(return_value=[_live_session(account_id)])

    result = await service.get_account_positions(user_id, account_id)

    assert result.rows[0].closable_session_id is None
    assert result.rows[0].close_blocked_reason == "position_side_unsupported"


def test_render_time_close_rejections_are_all_blocked_reasons():
    """close_service의 렌더 시점 판정 가능 거부가 버튼으로 새지 않는다.

    `no_open_position`과 `resting_conditional_entries`는 조회 뒤 바뀔 수 있는 런타임 상태,
    404는 버튼을 누른 뒤 세션이 사라진 경합이므로 이 집합에서 의도적으로 제외한다.
    """
    from src.trading.services.position_service import _CloseBlockedReason

    close_service_render_time_rejections = {
        "no_owning_session",
        "hedge_unsupported",
        "read_only_key",
        "position_side_unsupported",
    }

    assert close_service_render_time_rejections <= set(get_args(_CloseBlockedReason))


async def test_account_positions_reject_other_users_account(monkeypatch):
    """★IDOR — 계정 소유자가 아니면 조회 자체가 404 다."""
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, _, account_id, _, provider = _account_service(
        account_positions=[("BTC/USDT", _position(position_idx=0))],
    )

    with pytest.raises(HTTPException) as exc:
        await service.get_account_positions(uuid4(), account_id)

    assert exc.value.status_code == 404
    provider.fetch_all_open_positions.assert_not_awaited()


async def test_live_mode_account_is_unsupported_without_touching_exchange(monkeypatch):
    from src.trading.services import position_service

    monkeypatch.setattr(position_service, "_get_position_redis_pool", _FakeRedis)
    service, user_id, account_id, _, provider = _account_service(mode=ExchangeMode.live)

    result = await service.get_account_positions(user_id, account_id)

    assert result.supported is False
    assert result.reason == "live_mode_stub"
    provider.fetch_all_open_positions.assert_not_awaited()


async def test_account_cache_does_not_collide_with_session_cache(monkeypatch):
    """★캐시 네임스페이스 분리 — 같은 키를 쓰면 계정 조회가 세션 대조 근거를 덮어쓴다."""
    from src.trading.services import position_service

    redis = _FakeRedis()
    monkeypatch.setattr(position_service, "_get_position_redis_pool", lambda: redis)
    service, user_id, account_id, session_repo, _ = _account_service(
        account_positions=[("BTC/USDT", _position(position_idx=0))],
    )
    session_repo.list_by_account = AsyncMock(return_value=[])

    await service.get_account_positions(user_id, account_id)

    keys = list(redis.values)
    assert keys == [position_service.account_position_snapshot_cache_key(account_id)]
    assert position_service.position_snapshot_cache_key(account_id) not in redis.values


async def test_account_positions_are_served_from_cache_on_second_call(monkeypatch):
    from src.trading.services import position_service

    redis = _FakeRedis()
    monkeypatch.setattr(position_service, "_get_position_redis_pool", lambda: redis)
    service, user_id, account_id, session_repo, provider = _account_service(
        account_positions=[("BTC/USDT", _position(position_idx=0))],
    )
    session_repo.list_by_account = AsyncMock(return_value=[])

    first = await service.get_account_positions(user_id, account_id)
    second = await service.get_account_positions(user_id, account_id)

    assert provider.fetch_all_open_positions.await_count == 1
    assert first.rows[0].position.size == second.rows[0].position.size
    assert first.fetched_at == second.fetched_at
