"""market_data DI 조립 — config flag로 fixture vs timescale 전환.

service.py / repository.py에서 Depends import 금지 (3-Layer 규칙).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.core.config import settings

if TYPE_CHECKING:
    from src.market_data.providers import OHLCVProvider
    from src.market_data.providers.ccxt import CCXTProvider


def build_ohlcv_provider(
    session: AsyncSession,
    get_ccxt: Callable[[], CCXTProvider],
) -> OHLCVProvider:
    """config flag 로 OHLCVProvider 조립 — HTTP/worker DI 가 공유하는 단일 분기.

    - fixture (기본): FixtureProvider. `get_ccxt` 는 호출하지 않는다.
    - timescale: TimescaleProvider(OHLCVRepository(session), get_ccxt()).
    """
    if settings.ohlcv_provider == "fixture":
        from src.market_data.providers.fixture import FixtureProvider

        return FixtureProvider(root=settings.ohlcv_fixture_root)

    from src.market_data.providers.timescale import TimescaleProvider
    from src.market_data.repository import OHLCVRepository

    return TimescaleProvider(
        OHLCVRepository(session),
        get_ccxt(),
        exchange_name=settings.default_exchange,
    )


def build_ohlcv_provider_for_worker(session: AsyncSession) -> OHLCVProvider:
    """worker 경로 — request 가 없으므로 worker CCXT singleton 을 timescale 갈래에서만 얻는다."""

    def _worker_ccxt() -> CCXTProvider:
        from src.tasks.celery_app import get_ccxt_provider_for_worker

        return get_ccxt_provider_for_worker()

    return build_ohlcv_provider(session, _worker_ccxt)


async def get_ccxt_provider(request: Request) -> CCXTProvider | None:
    """FastAPI lifespan에서 init된 singleton (ohlcv_provider=timescale일 때만 non-None)."""
    return request.app.state.ccxt_provider  # type: ignore[no-any-return]


async def get_ohlcv_provider(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Any:
    """OHLCVProvider 구현체 반환 — config flag로 분기.

    - fixture (기본): Sprint 4 CSV 기반 FixtureProvider
    - timescale: CCXT + TimescaleDB cache 기반 TimescaleProvider
    """

    def _request_ccxt() -> CCXTProvider:
        ccxt = request.app.state.ccxt_provider
        if ccxt is None:
            raise RuntimeError(
                "ohlcv_provider=timescale인데 app.state.ccxt_provider가 None. "
                "lifespan이 init되지 않았거나 test 환경에서 override 필요."
            )
        return ccxt  # type: ignore[no-any-return]

    return build_ohlcv_provider(session, _request_ccxt)
