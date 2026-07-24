# 포지션 대조 서비스와 Bybit hedge 스냅샷을 검증한다
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.trading.models import ExchangeMode, ExchangeName
from src.trading.providers import Credentials, PositionSnapshot
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


def _position(*, side: str = "long", size: str = "1") -> PositionSnapshot:
    return PositionSnapshot(
        side=side,
        size=Decimal(size),
        entry_price=Decimal("100"),
        mark_price=Decimal("101"),
        unrealized_pnl=Decimal("1"),
        liquidation_price=None,
        leverage=Decimal("3"),
    )


def _service(*, report=None, positions=None, mode=ExchangeMode.demo, exchange=ExchangeName.bybit, settings=_SETTINGS):
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
    provider = SimpleNamespace(fetch_open_positions=AsyncMock(return_value=positions or []))
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
