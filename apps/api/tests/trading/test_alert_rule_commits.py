"""AlertRuleService mutation 의 commit-spy 회귀 ([LESSON-019]).

★2026-08-30 아키텍처 감사 시점에 이 서비스는 **서비스 레벨 테스트 자체가 0건**이었다.
`db_session` 픽스처는 같은 트랜잭션 안 read-your-writes 라 commit 누락을 통과시키므로
(`apps/api/AGENTS.md` §3), mutation 마다 `repo.commit()` 호출을 `AsyncMock` spy 로 얼린다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.strategy.exceptions import StrategyNotFoundError
from src.trading.services.alert_rule_service import AlertRuleService


def _service(*, owner_id):
    repo = AsyncMock()
    session_repo = AsyncMock()
    session_repo.get_by_id.return_value = MagicMock(user_id=owner_id)
    return repo, session_repo, AlertRuleService(repo=repo, session_repo=session_repo)


@pytest.mark.asyncio
async def test_deactivate_commits_when_a_row_changed() -> None:
    owner_id, session_id, rule_id = uuid4(), uuid4(), uuid4()
    repo, _session_repo, svc = _service(owner_id=owner_id)
    repo.get_active_by_id.return_value = MagicMock(session_id=session_id)
    repo.deactivate.return_value = True

    await svc.deactivate(owner_id, session_id, rule_id)

    repo.deactivate.assert_awaited_once_with(rule_id)
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_deactivate_does_not_commit_when_no_row_changed() -> None:
    """이미 비활성이면 `deactivate` 가 0행을 돌려준다 — 그때는 커밋하지 않는다."""
    owner_id, session_id, rule_id = uuid4(), uuid4(), uuid4()
    repo, _session_repo, svc = _service(owner_id=owner_id)
    repo.get_active_by_id.return_value = MagicMock(session_id=session_id)
    repo.deactivate.return_value = False

    await svc.deactivate(owner_id, session_id, rule_id)

    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_deactivate_rejects_a_rule_from_another_session() -> None:
    """★규칙이 그 세션 소유가 아니면 비활성화도 커밋도 없다(fail-closed)."""
    owner_id, session_id = uuid4(), uuid4()
    repo, _session_repo, svc = _service(owner_id=owner_id)
    repo.get_active_by_id.return_value = MagicMock(session_id=uuid4())

    with pytest.raises(StrategyNotFoundError):
        await svc.deactivate(owner_id, session_id, uuid4())

    repo.deactivate.assert_not_awaited()
    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_deactivate_rejects_a_session_owned_by_someone_else() -> None:
    """★소유권 — 남의 세션이면 규칙 조회 이전에 막는다."""
    repo, session_repo, svc = _service(owner_id=uuid4())
    session_repo.get_by_id.return_value = MagicMock(user_id=uuid4())

    with pytest.raises(StrategyNotFoundError):
        await svc.deactivate(uuid4(), uuid4(), uuid4())

    repo.get_active_by_id.assert_not_awaited()
    repo.deactivate.assert_not_awaited()
    repo.commit.assert_not_awaited()
