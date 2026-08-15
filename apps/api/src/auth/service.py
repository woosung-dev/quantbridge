"""auth Service. 비즈니스 로직 + 트랜잭션 경계."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from src.auth.exceptions import GeoBlockedCountryError
from src.auth.models import User
from src.auth.repository import UserRepository
from src.core.config import settings
from src.trading.models import SessionDeactivationReason

if TYPE_CHECKING:
    from src.strategy.repository import StrategyRepository
    from src.trading.repositories.live_signal_session_repository import (
        LiveSignalSessionRepository,
    )
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository


# Sprint 11 Phase A — 3계층 geo-block L3. US + EU 27개국 차단.
# L1 (Cloudflare WAF) + L2 (Next.js proxy.ts geo header) 도 병행 운영.
RESTRICTED_COUNTRIES: frozenset[str] = frozenset(
    {
        # United States
        "US",
        # EU 27 (2026-04 기준)
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IE",
        "IT",
        "LV",
        "LT",
        "LU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
        # United Kingdom (post-Brexit, FCA 규제)
        "GB",
    }
)


class UserService:
    """User lazy-create + Webhook 이벤트 처리.

    user.deleted 이벤트에서 Strategy cascade archive를 위해
    StrategyRepository도 함께 주입받는다 (동일 AsyncSession 공유).

    ★2026-08-15 surface-truth (S3) — 여기에 **돈을 멈추는 두 축**이 더 붙었다.
    종전 탈퇴 처리는 `set_inactive` + 전략 archive 뿐이라 **UI 만 잠겼다**: beat 는 그 사람의
    활성 세션을 계속 평가해 저장된 거래소 키를 복호화하고 실주문을 냈고, 유출된 TradingView
    웹훅 시크릿도 계속 체결됐다(`webhook.py` 는 HMAC 만 보고 소유자 활성 여부를 안 본다).
    ⇒ `LiveSignalSessionRepository`·`WebhookSecretRepository` 를 **같은 session** 으로 받아
    한 트랜잭션에서 함께 닫는다.
    """

    def __init__(
        self,
        user_repo: UserRepository,
        strategy_repo: StrategyRepository | None = None,
        live_session_repo: LiveSignalSessionRepository | None = None,
        webhook_secret_repo: WebhookSecretRepository | None = None,
    ) -> None:
        self.user_repo = user_repo
        self.strategy_repo = strategy_repo
        self.live_session_repo = live_session_repo
        self.webhook_secret_repo = webhook_secret_repo

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
                user = await self.user_repo.update_profile(user.id, email=email, username=username)
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
            country_code = _extract_country(data)
            # Sprint 11 Phase A — user.created 시점에만 차단. user.updated 는
            # 기존 사용자 프로필 동기화이므로 country 변경으로 kick-out 하지 않음.
            if event_type == "user.created" and country_code in RESTRICTED_COUNTRIES:
                raise GeoBlockedCountryError(country_code)
            await self.user_repo.upsert_from_webhook(
                clerk_user_id=str(clerk_user_id),
                email=email,
                username=username,
                country_code=country_code,
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
            # ★2026-08-15 surface-truth (S3) — 탈퇴가 **돈을 멈춰야** 한다.
            #   세션·시크릿 두 축을 archive 와 **같은 트랜잭션** 안에서 닫는다. 별도 커밋으로
            #   쪼개면 「전략은 archive 됐는데 세션은 살아 있는」 중간 상태가 원장에 남는다.
            now = datetime.now(UTC)
            if self.live_session_repo is not None:
                await self.live_session_repo.deactivate_all_by_owner(
                    user.id,
                    at=now,
                    reason=SessionDeactivationReason.account_deleted,
                )
            if self.webhook_secret_repo is not None:
                # ★grace 0 — `list_valid_secrets` 는 `revoked_at > now - grace` 를 아직
                #   유효로 센다. 탈퇴·유출에 1시간 유예를 줄 이유가 없으므로 revoke 시각을
                #   그 창 **밖**(과거)으로 찍어 다음 웹훅부터 즉시 401 이 되게 한다.
                await self.webhook_secret_repo.revoke_all_by_owner(
                    user.id,
                    at=now - timedelta(seconds=settings.webhook_secret_grace_seconds + 1),
                )
            await self.user_repo.commit()
            return

        # 기타 이벤트: silently ignore


def _extract_country(data: dict[str, object]) -> str | None:
    """Clerk data payload 의 public_metadata.country 에서 ISO 3166-1 alpha-2 국가코드 추출.

    FE 가입 플로우에서 Cloudflare CF-IPCountry 또는 Clerk signUp.publicMetadata 로 주입.
    존재하지 않으면 None 반환 (기존 사용자 마이그레이션 호환).
    """
    pm_raw = data.get("public_metadata")
    if not isinstance(pm_raw, dict):
        return None
    country_val = pm_raw.get("country")
    if country_val is None:
        return None
    country = str(country_val).strip().upper()
    if not country or len(country) != 2:
        return None
    return country


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
