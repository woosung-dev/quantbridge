"""WaitlistRepository의 실제 DB 조회·초대 상태 전이를 고정한다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.waitlist.models import WaitlistApplication, WaitlistStatus
from src.waitlist.repository import WaitlistRepository


def _application(
    email: str,
    *,
    status: WaitlistStatus = WaitlistStatus.pending,
    created_at: datetime | None = None,
) -> WaitlistApplication:
    return WaitlistApplication(
        email=email,
        tv_subscription="pro",
        exchange_capital="1k_to_10k",
        pine_experience="beginner",
        existing_tool="manual",
        pain_point="Manual alerts are painful.",
        status=status,
        created_at=created_at or datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_create_finds_normalized_email_and_marks_application_invited(
    db_session: AsyncSession,
) -> None:
    """생성·이메일 정규화 조회·초대 토큰 갱신은 같은 영속 객체를 반환한다."""
    repository = WaitlistRepository(db_session)
    application = _application("ada@example.com")

    saved = await repository.create(application)
    found_by_id = await repository.find_by_id(saved.id)
    found_by_email = await repository.find_by_email("  ADA@EXAMPLE.COM ")
    invited = await repository.mark_invited(saved, invite_token="invite-token")

    assert found_by_id is saved
    assert found_by_email is saved
    assert invited is saved
    assert invited.status == WaitlistStatus.invited
    assert invited.invite_token == "invite-token"
    assert invited.invited_at is not None
    assert invited.invite_sent_at is not None


@pytest.mark.asyncio
async def test_list_by_status_counts_filtered_and_unfiltered_pages(
    db_session: AsyncSession,
) -> None:
    """상태 필터는 count와 항목에 같이 적용하고, 무필터 페이지도 최신순이다."""
    repository = WaitlistRepository(db_session)
    started_at = datetime(2026, 8, 22, 8, tzinfo=UTC)
    pending = await repository.create(_application("pending@example.com", created_at=started_at))
    invited = await repository.create(
        _application(
            "invited@example.com",
            status=WaitlistStatus.invited,
            created_at=started_at + timedelta(minutes=1),
        )
    )
    await repository.create(
        _application(
            "rejected@example.com",
            status=WaitlistStatus.rejected,
            created_at=started_at + timedelta(minutes=2),
        )
    )

    pending_items, pending_total = await repository.list_by_status(
        status=WaitlistStatus.pending,
        limit=10,
        offset=0,
    )
    page_items, all_total = await repository.list_by_status(
        status=None,
        limit=2,
        offset=1,
    )

    assert [application.id for application in pending_items] == [pending.id]
    assert pending_total == 1
    assert [application.id for application in page_items] == [invited.id, pending.id]
    assert all_total == 3


@pytest.mark.asyncio
async def test_commit_persists_and_rollback_discards_waitlist_application(
    db_session: AsyncSession,
) -> None:
    """저장소의 명시적 트랜잭션 경계가 commit·rollback 모두 실제 DB에 반영된다."""
    repository = WaitlistRepository(db_session)
    committed = await repository.create(_application("committed@example.com"))
    await repository.commit()

    assert await repository.find_by_invite_token("missing-token") is None
    assert await repository.find_by_id(committed.id) is committed

    rolled_back = await repository.create(_application("rolled-back@example.com"))
    await repository.rollback()

    assert await repository.find_by_id(rolled_back.id) is None


@pytest.mark.asyncio
async def test_find_by_invite_token_returns_the_invited_application(
    db_session: AsyncSession,
) -> None:
    """초대 토큰 조회는 같은 초대 신청서를 실제 DB에서 다시 찾는다."""
    repository = WaitlistRepository(db_session)
    application = await repository.create(_application("token@example.com"))
    invited = await repository.mark_invited(application, invite_token="token-123")

    found = await repository.find_by_invite_token("token-123")

    assert found is not None
    assert found.id == invited.id
    assert found.status == WaitlistStatus.invited


@pytest.mark.asyncio
async def test_create_propagates_duplicate_email_and_rollback_restores_repository(
    db_session: AsyncSession,
) -> None:
    """중복 이메일 DB 오류는 삼키지 않고 전파되며 rollback 뒤 조회가 다시 가능하다."""
    repository = WaitlistRepository(db_session)
    original = await repository.create(_application("duplicate@example.com"))
    await repository.commit()

    with pytest.raises(IntegrityError):
        await repository.create(_application("duplicate@example.com"))
    await repository.rollback()

    found = await repository.find_by_email("DUPLICATE@EXAMPLE.COM")
    assert found is not None
    assert found.id == original.id


@pytest.mark.asyncio
async def test_lookup_and_pagination_boundaries_return_empty_results(
    db_session: AsyncSession,
) -> None:
    """없는 식별자와 0건 페이지는 예외 없이 빈 조회 결과를 반환한다."""
    repository = WaitlistRepository(db_session)

    assert await repository.find_by_id(uuid4()) is None
    assert await repository.find_by_email("missing@example.com") is None
    assert await repository.find_by_invite_token("missing-token") is None
    items, total = await repository.list_by_status(
        status=WaitlistStatus.joined,
        limit=0,
        offset=0,
    )

    assert items == []
    assert total == 0
