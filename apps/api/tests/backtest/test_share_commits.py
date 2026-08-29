"""BacktestService share mutation 의 commit-spy 회귀 ([LESSON-019]).

★**왜 필요한가.** `get_async_session()` 은 autocommit 이 꺼져 있어 명시 `commit()` 이 없으면
요청 종료 시 ROLLBACK 이다. 그런데 `db_session` 픽스처 통합 테스트는 같은 트랜잭션 안에서
read-your-writes 로 읽으므로 **commit 누락도 통과한다**(위양성). 그래서 `AsyncMock` spy 로
`repo.commit()` **호출 자체**를 얼린다 (`apps/api/AGENTS.md` §3 — 같은 결함이 3회 재발).

`create_share` / `revoke_share` 는 2026-08-30 아키텍처 감사까지 spy 가 **0건**이었고
`tests/backtest/test_share_endpoint.py` 의 `db_session` 테스트만 있었다 — 그 테스트들은
commit 을 지우고도 초록이다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.backtest.models import Backtest
from src.backtest.service import BacktestService


def _service() -> tuple[AsyncMock, BacktestService]:
    repo = AsyncMock()
    svc = BacktestService(
        repo=repo,
        strategy_repo=AsyncMock(),
        ohlcv_provider=MagicMock(),
        dispatcher=AsyncMock(),
    )
    return repo, svc


def _backtest(**overrides: object) -> MagicMock:
    bt = MagicMock(spec=Backtest)
    bt.id = uuid4()
    bt.share_token = None
    bt.share_revoked_at = None
    for key, value in overrides.items():
        setattr(bt, key, value)
    return bt


@pytest.mark.asyncio
async def test_create_share_commits_the_new_token() -> None:
    repo, svc = _service()
    bt = _backtest()
    repo.get_by_id.return_value = bt
    repo.get_by_id_for_update.return_value = bt

    result = await svc.create_share(bt.id, user_id=uuid4())

    assert result.share_token
    assert bt.share_token == result.share_token
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_share_returns_the_existing_token_without_committing() -> None:
    """이미 유효한 토큰이 있으면 **쓰지도 커밋하지도 않는다** — 멱등 경로의 부작용을 얼린다."""
    repo, svc = _service()
    bt = _backtest(share_token="already-issued")
    repo.get_by_id.return_value = bt
    repo.get_by_id_for_update.return_value = bt

    result = await svc.create_share(bt.id, user_id=uuid4())

    assert result.share_token == "already-issued"
    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_share_commits_the_revocation() -> None:
    repo, svc = _service()
    bt = _backtest(share_token="live-token")
    repo.get_by_id.return_value = bt

    await svc.revoke_share(bt.id, user_id=uuid4())

    assert bt.share_revoked_at is not None
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_revoke_share_is_a_noop_without_a_token() -> None:
    """토큰이 없으면 멱등 no-op — 커밋도 없다."""
    repo, svc = _service()
    repo.get_by_id.return_value = _backtest(share_token=None)

    await svc.revoke_share(uuid4(), user_id=uuid4())

    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_share_does_not_commit_for_someone_elses_backtest() -> None:
    """★소유권 — 남의 백테스트면 취소도 커밋도 일어나지 않는다(fail-closed)."""
    from src.backtest.exceptions import BacktestNotFound

    repo, svc = _service()
    repo.get_by_id.return_value = None

    with pytest.raises(BacktestNotFound):
        await svc.revoke_share(uuid4(), user_id=uuid4())

    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_revoke_share_stamps_an_aware_utc_timestamp() -> None:
    """`share_revoked_at` 은 tz-aware UTC 다 — naive 를 넣으면 `AwareDateTime` 이 뒤에서 깨진다."""
    repo, svc = _service()
    bt = _backtest(share_token="live-token")
    repo.get_by_id.return_value = bt
    before = datetime.now(UTC)

    await svc.revoke_share(bt.id, user_id=uuid4())

    assert bt.share_revoked_at.tzinfo is not None
    assert bt.share_revoked_at >= before
