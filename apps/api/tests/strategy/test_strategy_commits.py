"""Sprint 16 BL-010 — Strategy mutation commit-spy (LESSON-019 backfill).

Sprint 6 (webhook_secret) → Sprint 13 (OrderService) → Sprint 15-A (ExchangeAccount)
패턴 4번째 재발 방어. db_session 기반 통합 테스트는 conftest 트랜잭션 안에서
read-your-writes 통과 = false-positive. AsyncMock spy 가 Sprint 6 broken bug 의
본질 (commit 호출 누락) 을 직접 검증.

표준 reference: backend/tests/trading/test_webhook_secret_commits.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.schemas import CreateStrategyRequest, UpdateStrategyRequest

_OK_PINE = """//@version=5
strategy("ok")
long = ta.crossover(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
"""


def _make_strategy() -> Strategy:
    return Strategy(
        id=uuid4(),
        user_id=uuid4(),
        name="t",
        pine_source=_OK_PINE,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )


@pytest.mark.asyncio
async def test_create_calls_repo_commit() -> None:
    """LESSON-019 spy: create() 가 repo.commit() 호출 강제 (secret_svc 미주입)."""
    from src.strategy.service import StrategyService

    repo = AsyncMock()
    saved = _make_strategy()
    repo.create = AsyncMock(return_value=saved)

    svc = StrategyService(repo=repo)

    req = CreateStrategyRequest(name="t", pine_source=_OK_PINE)
    await svc.create(req, owner_id=uuid4())

    repo.create.assert_awaited_once()
    repo.commit.assert_awaited_once()  # ← Sprint 13 atomic auto-issue 표준


@pytest.mark.asyncio
async def test_create_with_secret_svc_atomic_single_commit() -> None:
    """Sprint 13 atomic: secret_svc 주입 시 secret 발급 + repo.commit 1회 (atomic)."""
    from src.strategy.service import StrategyService

    repo = AsyncMock()
    saved = _make_strategy()
    repo.create = AsyncMock(return_value=saved)

    secret_svc = AsyncMock()
    secret_svc.issue = AsyncMock(return_value="plaintext-secret")

    svc = StrategyService(repo=repo, secret_svc=secret_svc)

    req = CreateStrategyRequest(name="t", pine_source=_OK_PINE)
    response = await svc.create(req, owner_id=uuid4())

    secret_svc.issue.assert_awaited_once_with(saved.id, commit=False)
    repo.create.assert_awaited_once()
    repo.commit.assert_awaited_once()  # atomic — 1번만
    assert response.webhook_secret == "plaintext-secret"


@pytest.mark.asyncio
async def test_update_calls_repo_commit() -> None:
    """LESSON-019 spy: update() 가 repo.commit() 호출 강제."""
    from src.strategy.service import StrategyService

    repo = AsyncMock()
    existing = _make_strategy()
    repo.find_by_id_and_owner = AsyncMock(return_value=existing)
    repo.update = AsyncMock(return_value=existing)

    svc = StrategyService(repo=repo)

    req = UpdateStrategyRequest(name="updated")
    await svc.update(strategy_id=existing.id, owner_id=existing.user_id, data=req)

    repo.update.assert_awaited_once()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_calls_repo_commit() -> None:
    """LESSON-019 spy: delete() (no backtests) 가 repo.commit() 호출 강제."""
    from src.strategy.service import StrategyService

    repo = AsyncMock()
    existing = _make_strategy()
    repo.find_by_id_and_owner = AsyncMock(return_value=existing)
    repo.delete = AsyncMock(return_value=None)

    backtest_repo = AsyncMock()
    backtest_repo.exists_for_strategy = AsyncMock(return_value=False)

    svc = StrategyService(repo=repo, backtest_repo=backtest_repo)

    await svc.delete(strategy_id=existing.id, owner_id=existing.user_id)

    repo.delete.assert_awaited_once()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_settings_calls_repo_commit() -> None:
    """Sprint 26 LESSON-019 spy: update_settings() 가 repo.commit() 호출 강제."""
    from src.strategy.schemas import StrategySettings
    from src.strategy.service import StrategyService

    repo = AsyncMock()
    existing = _make_strategy()
    repo.find_by_id_and_owner = AsyncMock(return_value=existing)
    repo.update = AsyncMock(return_value=existing)

    svc = StrategyService(repo=repo)

    settings = StrategySettings(leverage=2, margin_mode="cross", position_size_pct=10)
    await svc.update_settings(
        strategy_id=existing.id, owner_id=existing.user_id, settings=settings
    )

    repo.update.assert_awaited_once()
    repo.commit.assert_awaited_once()  # ← broken bug 재발 방어


@pytest.mark.asyncio
async def test_update_settings_404_does_not_commit() -> None:
    """Sprint 26: 404 (ownership 위반 또는 미존재) 시 commit 호출 0 — 의도치 않은 변경 차단."""
    from src.strategy.exceptions import StrategyNotFoundError
    from src.strategy.schemas import StrategySettings
    from src.strategy.service import StrategyService

    repo = AsyncMock()
    repo.find_by_id_and_owner = AsyncMock(return_value=None)

    svc = StrategyService(repo=repo)

    settings = StrategySettings(leverage=2, margin_mode="cross", position_size_pct=10)
    with pytest.raises(StrategyNotFoundError):
        await svc.update_settings(
            strategy_id=uuid4(), owner_id=uuid4(), settings=settings
        )

    repo.update.assert_not_called()
    repo.commit.assert_not_called()
