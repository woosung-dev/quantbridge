"""auth Service. 비즈니스 로직 + 트랜잭션 경계."""
from __future__ import annotations

from typing import TYPE_CHECKING

from src.auth.models import User
from src.auth.repository import UserRepository

if TYPE_CHECKING:
    from src.strategy.repository import StrategyRepository


class UserService:
    """User lazy-create + Webhook 이벤트 처리.

    user.deleted 이벤트에서 Strategy cascade archive를 위해
    StrategyRepository도 함께 주입받는다 (동일 AsyncSession 공유).
    """

    def __init__(
        self,
        user_repo: UserRepository,
        strategy_repo: StrategyRepository | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.strategy_repo = strategy_repo

    async def get_or_create(
        self,
        clerk_user_id: str,
        email: str | None,
        username: str | None,
    ) -> User:
        """보호 엔드포인트에서 호출됨. 첫 요청 시 DB User 생성."""
        user = await self.user_repo.find_by_clerk_id(clerk_user_id)
        if user is not None:
            if user.email != email or user.username != username:
                user = await self.user_repo.update_profile(
                    user.id, email=email, username=username
                )
                await self.user_repo.commit()
            return user

        user = await self.user_repo.insert_if_absent(
            clerk_user_id=clerk_user_id,
            email=email,
            username=username,
        )
        await self.user_repo.commit()
        return user

    async def handle_clerk_event(self, event: dict[str, object]) -> None:
        """Webhook 이벤트 디스패치.

        user.created/updated → upsert. user.deleted → soft delete + strategy archive.
        기타 이벤트는 silently 무시 (Clerk 재시도 방지).
        """
        event_type = event.get("type")
        data = event.get("data") or {}
        if not isinstance(data, dict):
            return
        clerk_user_id = data.get("id")
        if not clerk_user_id:
            return

        if event_type in ("user.created", "user.updated"):
            email = _extract_email(data)
            username_val = data.get("username")
            username = str(username_val) if username_val is not None else None
            await self.user_repo.upsert_from_webhook(
                clerk_user_id=str(clerk_user_id),
                email=email,
                username=username,
            )
            await self.user_repo.commit()
            return

        if event_type == "user.deleted":
            user = await self.user_repo.find_by_clerk_id(str(clerk_user_id))
            if user is None:
                return
            await self.user_repo.set_inactive(user.id)
            if self.strategy_repo is not None:
                await self.strategy_repo.archive_all_by_owner(user.id)
            await self.user_repo.commit()
            return

        # 기타 이벤트: silently ignore


def _extract_email(data: dict[str, object]) -> str | None:
    """Clerk data payload에서 primary email 추출."""
    emails_raw = data.get("email_addresses") or []
    if not isinstance(emails_raw, list):
        return None
    emails: list[dict[str, object]] = [e for e in emails_raw if isinstance(e, dict)]
    if not emails:
        return None
    primary_id = data.get("primary_email_address_id")
    if primary_id:
        for e in emails:
            if e.get("id") == primary_id:
                val = e.get("email_address")
                return str(val) if val is not None else None
    val = emails[0].get("email_address")
    return str(val) if val is not None else None
