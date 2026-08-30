"""KillSwitchService mutation 의 commit-spy 회귀 ([LESSON-019]).

★**왜 필요한가.** `get_async_session()` 은 autocommit 이 꺼져 있어 명시 `commit()` 이 없으면
요청 종료 시 ROLLBACK 이다. 그런데 `db_session` 픽스처 통합 테스트는 **같은 트랜잭션 안에서
read-your-writes** 로 읽으므로 commit 누락도 **통과해 버린다**(위양성). 그래서 `AsyncMock` spy 로
`repo.commit()` **호출 자체**를 얼린다. 같은 결함이 이 레포에서 3회 재발했다(`apps/api/AGENTS.md` §3).

이 서비스는 2026-08-30 아키텍처 감사까지 spy 가 **0건**이었다 — mutation 은 둘이다:
`resolve_for_user`(사용자 해제)와 `ensure_not_gated`(신규 breach 이벤트 기록).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.trading.exceptions import KillSwitchActive
from src.trading.kill_switch import EvaluationResult, KillSwitchService
from src.trading.models import KillSwitchEvent


class _StaticEvaluator:
    def __init__(self, result: EvaluationResult) -> None:
        self._r = result

    async def evaluate(self, ctx):
        return self._r


def _service(*results: EvaluationResult) -> tuple[AsyncMock, KillSwitchService]:
    repo = AsyncMock()
    svc = KillSwitchService(
        evaluators=[_StaticEvaluator(r) for r in results],
        events_repo=repo,
    )
    return repo, svc


@pytest.mark.asyncio
async def test_ensure_not_gated_commits_the_new_breach_event() -> None:
    """신규 breach 는 **즉시** commit 된다 — 호출자의 SAVEPOINT rollback 이 감사 행을 지우지 못하게."""
    repo, svc = _service(
        EvaluationResult(
            gated=True,
            trigger_type="daily_loss",
            trigger_value=Decimal("-600"),
            threshold=Decimal("500"),
        )
    )
    repo.get_active.return_value = None
    repo.save.return_value = MagicMock(spec=KillSwitchEvent, id=uuid4())
    repo.get_account_user_id.return_value = None

    with pytest.raises(KillSwitchActive):
        await svc.ensure_not_gated(strategy_id=uuid4(), account_id=uuid4())

    repo.save.assert_awaited_once()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_not_gated_does_not_commit_when_nothing_is_gated() -> None:
    """통과 경로는 쓰지도 커밋하지도 않는다 — 부작용을 얼린다(`AGENTS.md` §10-1)."""
    repo, svc = _service(EvaluationResult(gated=False))
    repo.get_active.return_value = None

    await svc.ensure_not_gated(strategy_id=uuid4(), account_id=uuid4())

    repo.save.assert_not_awaited()
    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_ensure_not_gated_reentry_does_not_write_a_second_event() -> None:
    """이미 미해결 이벤트가 있으면 재진입은 **기록 없이** 차단만 한다 (alert storm 방지)."""
    repo, svc = _service(
        EvaluationResult(
            gated=True,
            trigger_type="daily_loss",
            trigger_value=Decimal("-600"),
            threshold=Decimal("500"),
        )
    )
    repo.get_active.return_value = MagicMock(spec=KillSwitchEvent, id=uuid4())

    with pytest.raises(KillSwitchActive):
        await svc.ensure_not_gated(strategy_id=uuid4(), account_id=uuid4())

    repo.save.assert_not_awaited()
    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_for_user_commits_the_resolution() -> None:
    repo, svc = _service()
    event_id, user_id = uuid4(), uuid4()
    repo.get_owned.return_value = MagicMock(spec=KillSwitchEvent, id=event_id)
    repo.resolve.return_value = 1
    repo.get_by_id.return_value = MagicMock(spec=KillSwitchEvent, id=event_id)

    outcome = await svc.resolve_for_user(event_id, user_id=user_id, note="done")

    assert outcome.kind == "resolved"
    repo.resolve.assert_awaited_once()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_for_user_does_not_commit_for_someone_elses_event() -> None:
    """★소유권 — 남의 이벤트면 해제도 커밋도 일어나지 않는다(fail-closed)."""
    repo, svc = _service()
    repo.get_owned.return_value = None

    outcome = await svc.resolve_for_user(uuid4(), user_id=uuid4(), note=None)

    assert outcome.kind == "not_owned"
    repo.resolve.assert_not_awaited()
    repo.commit.assert_not_awaited()
