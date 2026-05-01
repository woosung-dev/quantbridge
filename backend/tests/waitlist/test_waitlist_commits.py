"""Sprint 16 BL-010 — Waitlist mutation commit-spy (LESSON-019 backfill).

Sprint 11 도입. submit_application 은 이미 commit 호출 (line 74). admin_approve 도
line 126 commit. spy 추가로 회귀 방어.
"""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.waitlist.models import WaitlistApplication, WaitlistStatus
from src.waitlist.schemas import CreateWaitlistApplicationRequest


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> Generator[None, None, None]:
    """Override waitlist/conftest.py — Redis 우회 (spy test 는 limiter 안 거침).

    autouse fixture 동일 이름으로 module-level override. conftest 의
    limiter.reset() 가 local Redis 6379 (사용자 환경 isolated 6380) mismatch 로
    ConnectionError. spy test 는 service mutation 만 검증 → rate-limit 무관.
    """
    yield


def _make_application(
    *, status: WaitlistStatus = WaitlistStatus.pending
) -> WaitlistApplication:
    return WaitlistApplication(
        id=uuid4(),
        email="user@test.local",
        tv_subscription="pro",
        exchange_capital="1k_to_10k",
        pine_experience="beginner",
        existing_tool="manual",
        pain_point="3commas 의 자동매매가 너무 느려서 직접 만들고 싶음",
        status=status,
        created_at=datetime.now(UTC),
    )


def _make_service(repo, *, email_service=None, token_service=None):
    from src.waitlist.service import ServiceConfig, WaitlistService

    return WaitlistService(
        repo=repo,
        email_service=email_service or AsyncMock(),
        token_service=token_service or AsyncMock(),
        config=ServiceConfig(invite_base_url="https://qb.local/invite"),
    )


@pytest.mark.asyncio
async def test_submit_application_calls_repo_commit() -> None:
    """LESSON-019 spy: submit_application() 가 repo.commit() 호출 강제."""
    repo = AsyncMock()
    repo.find_by_email = AsyncMock(return_value=None)
    saved = _make_application()
    repo.create = AsyncMock(return_value=saved)

    svc = _make_service(repo)

    req = CreateWaitlistApplicationRequest(
        email="user@test.local",
        tv_subscription="pro",
        exchange_capital="1k_to_10k",
        pine_experience="beginner",
        existing_tool="manual",
        pain_point="3commas 의 자동매매가 너무 느려서 직접 만들고 싶음",
    )
    await svc.submit_application(req)

    repo.create.assert_awaited_once()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_approve_calls_repo_commit() -> None:
    """LESSON-019 spy: admin_approve() 가 repo.commit() 호출 강제."""
    application = _make_application()

    repo = AsyncMock()
    repo.find_by_id = AsyncMock(return_value=application)
    invited = _make_application(status=WaitlistStatus.invited)
    invited.invite_sent_at = datetime.now(UTC)
    repo.mark_invited = AsyncMock(return_value=invited)

    token_service = AsyncMock()
    token_service.issue = lambda _email: "fake-invite-token"  # sync method

    email_service = AsyncMock()
    email_service.send_invite_email = AsyncMock(return_value=None)

    svc = _make_service(repo, email_service=email_service, token_service=token_service)

    await svc.admin_approve(application.id)

    repo.mark_invited.assert_awaited_once()
    repo.commit.assert_awaited_once()
    email_service.send_invite_email.assert_awaited_once()
