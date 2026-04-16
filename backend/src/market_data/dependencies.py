"""market_data DI 조립 — config flag로 fixture vs timescale 전환.

service.py / repository.py에서 Depends import 금지 (3-Layer 규칙).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.core.config import settings

if TYPE_CHECKING:
    from src.market_data.providers.ccxt import CCXTProvider


async def get_ccxt_provider(request: Request) -> CCXTProvider | None:
    """FastAPI lifespan에서 init된 singleton (ohlcv_provider=timescale일 때만 non-None)."""
    return request.app.state.ccxt_provider  # type: ignore[no-any-return]


async def get_ohlcv_provider(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    """OHLCVProvider 구현체 반환 — config flag로 분기.

    - fixture (기본): Sprint 4 CSV 기반 FixtureProvider
    - timescale: CCXT + TimescaleDB cache 기반 TimescaleProvider
    """
    if settings.ohlcv_provider == "fixture":
        from src.market_data.providers.fixture import FixtureProvider

        return FixtureProvider(root=settings.ohlcv_fixture_root)

    from src.market_data.providers.timescale import TimescaleProvider
    from src.market_data.repository import OHLCVRepository

    ccxt = await get_ccxt_provider(request)
    if ccxt is None:
        raise RuntimeError(
            "ohlcv_provider=timescale인데 app.state.ccxt_provider가 None. "
            "lifespan이 init되지 않았거나 test 환경에서 override 필요."
        )
    repo = OHLCVRepository(session)
    return TimescaleProvider(
        repo, ccxt, exchange_name=settings.default_exchange
    )
