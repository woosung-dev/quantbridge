"""Funding rate 수집 유스케이스의 이전 import 경로 호환 shim.

실제 구현은 `trading.services.funding_rate_service`에 있고, 이 모듈은 DB 세션을
받거나 SQL을 실행하지 않는다. 기존 task/호출자의 import 경로는 Repository 주입
형태로만 유지한다.
"""

from __future__ import annotations

from datetime import datetime

from src.trading.models import ExchangeName
from src.trading.repositories.funding_rate_repository import FundingRateRepository
from src.trading.services.funding_rate_service import FundingRateService


async def fetch_and_store_funding_rates(
    *,
    repo: FundingRateRepository,
    exchange_name: ExchangeName,
    symbol: str,
    since: datetime,
    limit: int = 100,
) -> int:
    """기존 함수 import 경로를 service 호출로 연결한다."""
    return await FundingRateService(repo).fetch_and_store(
        exchange_name=exchange_name,
        symbol=symbol,
        since=since,
        limit=limit,
    )


async def backfill_funding_rate_history(
    *,
    repo: FundingRateRepository,
    exchange_name: ExchangeName,
    symbol: str,
    start: datetime,
    end: datetime,
    page_limit: int = 200,
    max_pages: int = 200,
) -> int:
    """기존 함수 import 경로를 service 호출로 연결한다."""
    return await FundingRateService(repo).backfill(
        exchange_name=exchange_name,
        symbol=symbol,
        start=start,
        end=end,
        page_limit=page_limit,
        max_pages=max_pages,
    )


__all__ = [
    "FundingRateService",
    "backfill_funding_rate_history",
    "fetch_and_store_funding_rates",
]
