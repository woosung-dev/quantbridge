"""Funding rate fetch 테스트 — CCXT monkeypatch."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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


async def test_backfill_paginates_with_next_timestamp_cursor():
    """두 페이지는 마지막 timestamp+1을 다음 since로 사용한다."""
    from src.trading.funding import backfill_funding_rate_history

    start = datetime(2024, 1, 1, tzinfo=UTC)
    first_ts = int(start.timestamp() * 1000)
    second_ts = first_ts + 8 * 60 * 60 * 1000
    mock_exchange = MagicMock()
    mock_exchange.fetch_funding_rate_history = AsyncMock(
        side_effect=[
            [{"timestamp": first_ts, "fundingRate": "0.0001"}],
            [{"timestamp": second_ts, "fundingRate": "0.0002"}],
        ]
    )
    mock_exchange.close = AsyncMock()
    mock_result = MagicMock(rowcount=1)
    mock_session = MagicMock(execute=AsyncMock(return_value=mock_result), commit=AsyncMock())

    with (
        patch("ccxt.async_support.bybit", MagicMock(return_value=mock_exchange)),
        patch("src.trading.funding.asyncio.sleep", new=AsyncMock()),
    ):
        inserted = await backfill_funding_rate_history(
            exchange_name="bybit",
            symbol="BTC/USDT:USDT",
            start=start,
            end=datetime(2024, 1, 1, 8, tzinfo=UTC),
            session=mock_session,
        )

    assert inserted == 2
    assert mock_exchange.fetch_funding_rate_history.call_args_list[0].kwargs["since"] == first_ts
    assert mock_exchange.fetch_funding_rate_history.call_args_list[1].kwargs["since"] == first_ts + 1


async def test_backfill_does_not_store_records_after_end():
    """종료 시각 이후 funding record는 DB insert 대상이 아니다."""
    from src.trading.funding import backfill_funding_rate_history

    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 1, 8, tzinfo=UTC)
    mock_exchange = MagicMock()
    mock_exchange.fetch_funding_rate_history = AsyncMock(
        return_value=[
            {"timestamp": int(start.timestamp() * 1000), "fundingRate": "0.0001"},
            {"timestamp": int((end + timedelta(hours=8)).timestamp() * 1000), "fundingRate": "0.0002"},
        ]
    )
    mock_exchange.close = AsyncMock()
    mock_session = MagicMock(execute=AsyncMock(return_value=MagicMock(rowcount=1)), commit=AsyncMock())

    with patch("ccxt.async_support.bybit", MagicMock(return_value=mock_exchange)):
        inserted = await backfill_funding_rate_history(
            exchange_name="bybit",
            symbol="BTC/USDT:USDT",
            start=start,
            end=end,
            session=mock_session,
        )

    assert inserted == 1
    assert mock_session.execute.await_count == 1


async def test_backfill_is_idempotent_when_all_rows_conflict():
    """ON CONFLICT 결과가 0이면 재실행해도 새 행 수는 0이다."""
    from src.trading.funding import backfill_funding_rate_history

    start = datetime(2024, 1, 1, tzinfo=UTC)
    mock_exchange = MagicMock()
    mock_exchange.fetch_funding_rate_history = AsyncMock(
        return_value=[{"timestamp": int(start.timestamp() * 1000), "fundingRate": "0.0001"}]
    )
    mock_exchange.close = AsyncMock()
    mock_session = MagicMock(execute=AsyncMock(return_value=MagicMock(rowcount=0)), commit=AsyncMock())

    with patch("ccxt.async_support.bybit", MagicMock(return_value=mock_exchange)):
        inserted = await backfill_funding_rate_history(
            exchange_name="bybit",
            symbol="BTC/USDT:USDT",
            start=start,
            end=start,
            session=mock_session,
        )

    assert inserted == 0
    mock_session.commit.assert_awaited_once()


async def test_backfill_empty_first_page_skips_database():
    """첫 페이지가 비어 있으면 저장 및 commit 없이 종료한다."""
    from src.trading.funding import backfill_funding_rate_history

    start = datetime(2024, 1, 1, tzinfo=UTC)
    mock_exchange = MagicMock()
    mock_exchange.fetch_funding_rate_history = AsyncMock(return_value=[])
    mock_exchange.close = AsyncMock()
    mock_session = MagicMock(execute=AsyncMock(), commit=AsyncMock())

    with patch("ccxt.async_support.bybit", MagicMock(return_value=mock_exchange)):
        inserted = await backfill_funding_rate_history(
            exchange_name="bybit",
            symbol="BTC/USDT:USDT",
            start=start,
            end=start,
            session=mock_session,
        )

    assert inserted == 0
    mock_session.execute.assert_not_awaited()
    mock_session.commit.assert_not_awaited()
