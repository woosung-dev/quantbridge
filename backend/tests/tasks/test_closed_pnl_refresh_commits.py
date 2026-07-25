# closedPnl 반영 작업의 조건부 커밋과 미조회 시 무갱신을 검증한다.
"""closedPnl backfill money-path 커밋 회귀 테스트."""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.trading.models import OrderState


def _order() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        state=OrderState.filled,
        reduce_only=True,
        exchange_order_id="bybit-close-1",
        exchange_account_id=uuid4(),
        leverage=3,
        symbol="BTC/USDT",
        filled_at=datetime.now(UTC),
    )


def _account() -> SimpleNamespace:
    from src.trading.models import ExchangeMode, ExchangeName

    return SimpleNamespace(
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
        passphrase_encrypted=None,
    )


def _sessionmaker(sessions: list[MagicMock]):
    @asynccontextmanager
    async def _ctx():
        yield sessions.pop(0)

    class _SM:
        def __call__(self):
            return _ctx()

    return _SM()


def _patch_crypto(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod

    crypto = MagicMock()
    crypto.decrypt.side_effect = ["key", "secret"]
    monkeypatch.setattr(trading_mod, "EncryptionService", MagicMock(return_value=crypto))


@pytest.mark.asyncio
async def test_refresh_commits_only_when_conditional_update_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.tasks.trading as trading_mod
    from src.trading.providers import ClosedPnlSnapshot

    order = _order()
    first, second = MagicMock(), MagicMock()
    first.get = AsyncMock(return_value=_account())
    second.commit = AsyncMock()
    repo_load = MagicMock(get_by_id=AsyncMock(return_value=order))
    repo_write = MagicMock(backfill_exchange_realized_pnl=AsyncMock(return_value=1))
    repos = iter([repo_load, repo_write])
    monkeypatch.setattr(trading_mod, "OrderRepository", lambda _session: next(repos))
    _patch_crypto(monkeypatch)
    provider = MagicMock(
        fetch_closed_pnl=AsyncMock(
            return_value=ClosedPnlSnapshot("bybit-close-1", Decimal("-4.2"), None, None, None)
        )
    )

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([first, second]), provider=provider
    )

    assert result["applied"] is True
    second.commit.assert_awaited_once()
    repo_write.backfill_exchange_realized_pnl.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_does_not_commit_when_already_synced(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod
    from src.trading.providers import ClosedPnlSnapshot

    order = _order()
    first, second = MagicMock(), MagicMock()
    first.get = AsyncMock(return_value=_account())
    second.commit = AsyncMock()
    repos = iter(
        [
            MagicMock(get_by_id=AsyncMock(return_value=order)),
            MagicMock(backfill_exchange_realized_pnl=AsyncMock(return_value=0)),
        ]
    )
    monkeypatch.setattr(trading_mod, "OrderRepository", lambda _session: next(repos))
    _patch_crypto(monkeypatch)
    provider = MagicMock(
        fetch_closed_pnl=AsyncMock(
            return_value=ClosedPnlSnapshot("bybit-close-1", Decimal("0"), None, None, None)
        )
    )

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([first, second]), provider=provider
    )
    assert result["skipped"] == "already_synced"
    second.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", [None, RuntimeError("offline")])
async def test_refresh_never_updates_without_snapshot(
    monkeypatch: pytest.MonkeyPatch, outcome: object
) -> None:
    """조회 실패·미반환이면 추정 손익 UPDATE와 커밋 모두 구조적으로 불가능해야 한다."""
    import src.tasks.trading as trading_mod

    order = _order()
    first = MagicMock()
    first.get = AsyncMock(return_value=_account())
    first.commit = AsyncMock()
    repo = MagicMock(spec=["get_by_id"])
    repo.get_by_id = AsyncMock(return_value=order)
    monkeypatch.setattr(trading_mod, "OrderRepository", lambda _session: repo)
    _patch_crypto(monkeypatch)
    provider = MagicMock(fetch_closed_pnl=AsyncMock())
    if isinstance(outcome, Exception):
        provider.fetch_closed_pnl.side_effect = outcome
        with pytest.raises(RuntimeError, match="offline"):
            await trading_mod._refresh_closed_pnl_with_session(
                order.id, _sessionmaker([first]), provider=provider
            )
    else:
        provider.fetch_closed_pnl.return_value = None
        result = await trading_mod._refresh_closed_pnl_with_session(
            order.id, _sessionmaker([first]), provider=provider
        )
        assert result["transient"] == "closed_pnl_not_yet_available"
    assert not hasattr(repo, "backfill_exchange_realized_pnl")
    first.commit.assert_not_awaited()
