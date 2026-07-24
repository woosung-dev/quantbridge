# 활성 라이브 세션 ticker 심볼 조회 repository 쿼리를 검증한다.
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.trading.repositories.live_signal_session_repository import (
    LiveSignalSessionRepository,
)


@pytest.mark.asyncio
async def test_list_distinct_active_symbols_returns_scalar_rows() -> None:
    session = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = ["BTC/USDT", "ETH/USDT"]
    result = MagicMock()
    result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=result)

    symbols = await LiveSignalSessionRepository(session).list_distinct_active_symbols()

    assert symbols == ["BTC/USDT", "ETH/USDT"]
    session.execute.assert_awaited_once()
