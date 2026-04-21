"""Funding rate 유틸 테스트 — CCXT monkeypatch."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# apply_funding_to_pnl
# ---------------------------------------------------------------------------

def _make_fr(rate: str, ts: datetime) -> SimpleNamespace:
    """apply_funding_to_pnl이 사용하는 .funding_rate / .funding_timestamp만 구현."""
    return SimpleNamespace(funding_rate=Decimal(rate), funding_timestamp=ts)


def test_apply_funding_long_positive_rate():
    """long + positive rate → 비용 지불 → 음수 PnL."""
    from src.trading.funding import apply_funding_to_pnl

    entry = datetime(2026, 4, 21, 0, 0, tzinfo=UTC)
    exit_ = datetime(2026, 4, 21, 16, 0, tzinfo=UTC)
    frs = [
        _make_fr("0.0001", datetime(2026, 4, 21, 8, 0, tzinfo=UTC)),
        _make_fr("0.0001", datetime(2026, 4, 21, 16, 0, tzinfo=UTC)),  # exit 시점 == 제외
    ]
    result = apply_funding_to_pnl(Decimal("1"), entry, exit_, frs)
    assert result == Decimal("-0.0001")  # 첫 번째만 포함


def test_apply_funding_short_positive_rate():
    """short(음수 position_size) + positive rate → 수령 → 양수 PnL."""
    from src.trading.funding import apply_funding_to_pnl

    entry = datetime(2026, 4, 21, 0, 0, tzinfo=UTC)
    frs = [_make_fr("0.0001", datetime(2026, 4, 21, 8, 0, tzinfo=UTC))]
    result = apply_funding_to_pnl(Decimal("-1"), entry, None, frs)
    assert result == Decimal("0.0001")


def test_apply_funding_excludes_before_entry():
    """entry 이전 funding은 제외."""
    from src.trading.funding import apply_funding_to_pnl

    entry = datetime(2026, 4, 21, 9, 0, tzinfo=UTC)
    frs = [_make_fr("0.0001", datetime(2026, 4, 21, 8, 0, tzinfo=UTC))]
    result = apply_funding_to_pnl(Decimal("1"), entry, None, frs)
    assert result == Decimal("0")


def test_apply_funding_no_rates():
    """funding_rates 빈 리스트 → 0."""
    from src.trading.funding import apply_funding_to_pnl

    entry = datetime(2026, 4, 21, 0, 0, tzinfo=UTC)
    result = apply_funding_to_pnl(Decimal("1"), entry, None, [])
    assert result == Decimal("0")


# ---------------------------------------------------------------------------
# fetch_and_store_funding_rates — CCXT monkeypatch
# ---------------------------------------------------------------------------

async def test_fetch_and_store_inserts_new_records():
    """CCXT mock → 2개 레코드 → INSERT 2개."""
    from src.trading.funding import fetch_and_store_funding_rates

    now = datetime.now(UTC)
    mock_raw = [
        {"timestamp": int((now - timedelta(hours=8)).timestamp() * 1000), "fundingRate": 0.0001},
        {"timestamp": int(now.timestamp() * 1000), "fundingRate": 0.00015},
    ]

    mock_exchange = MagicMock()
    mock_exchange.fetch_funding_rate_history = AsyncMock(return_value=mock_raw)
    mock_exchange.close = AsyncMock()

    mock_cls = MagicMock(return_value=mock_exchange)

    mock_result = MagicMock()
    mock_result.rowcount = 1

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    with patch("ccxt.async_support.bybit", mock_cls):
        inserted = await fetch_and_store_funding_rates(
            exchange_name="bybit",
            symbol="BTC/USDT:USDT",
            since=now - timedelta(hours=10),
            session=mock_session,
        )

    assert inserted == 2  # rowcount=1 per row x 2 rows
    assert mock_session.commit.called


async def test_fetch_and_store_empty_response():
    """CCXT가 빈 리스트 반환 시 DB 접근 없이 0 반환."""
    from src.trading.funding import fetch_and_store_funding_rates

    mock_exchange = MagicMock()
    mock_exchange.fetch_funding_rate_history = AsyncMock(return_value=[])
    mock_exchange.close = AsyncMock()

    mock_cls = MagicMock(return_value=mock_exchange)
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()

    with patch("ccxt.async_support.bybit", mock_cls):
        result = await fetch_and_store_funding_rates(
            exchange_name="bybit",
            symbol="BTC/USDT:USDT",
            since=datetime.now(UTC) - timedelta(hours=2),
            session=mock_session,
        )

    assert result == 0
    mock_session.execute.assert_not_called()


async def test_fetch_and_store_unknown_exchange_raises():
    """미지원 거래소 → ValueError."""
    from src.trading.funding import fetch_and_store_funding_rates

    with pytest.raises(ValueError, match="Unknown CCXT exchange"):
        await fetch_and_store_funding_rates(
            exchange_name="nonexistent_exchange",
            symbol="BTC/USDT:USDT",
            since=datetime.now(UTC),
            session=MagicMock(),
        )
