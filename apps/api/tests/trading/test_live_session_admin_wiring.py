# `live_session_admin` 의 서비스 조립을 **실제로 부른다** — [BL-876]
#
# 이 CLI 는 HTTP 의존성(`src/trading/dependencies.py`)의 조립을 손으로 옮겨 쓴다. 원본이 바뀌면
# 사본이 따라가야 하는데, 종전 테스트는 전부 `_build_close_service` 를 통째로 페이크로 갈아끼워
# (`test_live_session_admin_flatten.py` · `tests/scripts/test_harness_exclusivity_guard.py`)
# 조립 자체는 **한 번도 실행되지 않았다**. mypy 는 `src/` 만 보고 `scripts/` 는 안 본다.
# 그 사이 `_StrategySessionsAdapter` 가 `user_repo` 를 받게 되면서 `flatten` 이 조립에서
# `TypeError` 로 죽고 있었다(2026-11-16 실측).
from __future__ import annotations

from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

import scripts.live_session_admin as admin
from src.auth.repository import UserRepository
from src.strategy.repository import StrategyRepository
from src.trading.dependencies import _StrategySessionsAdapter
from src.trading.services.close_service import ClosePositionService
from src.trading.services.live_session_service import LiveSignalSessionService
from src.trading.services.order_service import OrderService


def test_build_close_service_assembles_without_faking_the_wiring() -> None:
    """`flatten` 이 쓰는 배선이 생성자 시그니처와 맞는다 — 세션만 가짜다."""
    session = MagicMock(spec=AsyncSession)

    service = admin._build_close_service(session)

    assert isinstance(service, ClosePositionService)
    order_service = service._order_service
    assert isinstance(order_service, OrderService)
    port = order_service._sessions_port
    assert isinstance(port, _StrategySessionsAdapter)
    # 세션을 repo 자리에 넘기면 생성은 되더라도 첫 호출에서 죽는다 — 타입까지 본다.
    assert isinstance(port._strategy_repo, StrategyRepository)
    assert isinstance(port._user_repo, UserRepository)
    assert port._strategy_repo.session is session
    assert port._user_repo.session is session


def test_build_session_service_assembles_without_faking_the_wiring() -> None:
    """`start`·`stop` 이 쓰는 배선도 같은 종류의 손 사본이다 — 조립이 도는지만 고정한다."""
    service = admin._build_session_service(MagicMock(spec=AsyncSession))

    assert isinstance(service, LiveSignalSessionService)
