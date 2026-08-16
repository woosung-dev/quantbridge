"""auth Service. 비즈니스 로직 + 트랜잭션 경계."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

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
    """User lazy-create + 탈퇴 처리.

    탈퇴에서 Strategy cascade archive를 위해
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
        auth_subject: str,
        email: str | None,
        username: str | None,
        country_code: str | None = None,
    ) -> User:
        """보호 엔드포인트에서 호출됨. 첫 요청 시 DB User 생성.

        ★프로필 값의 출처가 웹훅에서 **JWT payload** 로 바뀌었다(ADR-034). 값이 달라졌을 때만
        UPDATE 한다 — 매 요청 쓰기가 되면 인증 경로가 write 경로가 된다.
        """
        normalized_country = _normalize_country(country_code)
        user = await self.user_repo.find_by_auth_subject(auth_subject)
        if user is not None:
            country_changed = (
                normalized_country is not None and user.country_code != normalized_country
            )
            if user.email != email or user.username != username or country_changed:
                user = await self.user_repo.update_profile(
                    user.id,
                    email=email,
                    username=username,
                    country_code=normalized_country,
                )
                await self.user_repo.commit()
            return user

        # geo-block L3 백스톱 — 정문은 FE 의 Better Auth create 훅이다(가입 자체를 막는다).
        # 여기까지 온 것은 그 훅을 지나 발급된 토큰이므로, 방어선을 한 겹 더 둔다.
        if normalized_country in RESTRICTED_COUNTRIES:
            raise GeoBlockedCountryError(normalized_country)

        user = await self.user_repo.insert_if_absent(
            auth_subject=auth_subject,
            email=email,
            username=username,
            country_code=normalized_country,
        )
        await self.user_repo.commit()
        return user

    async def deactivate_account(self, user_id: UUID) -> None:
        """탈퇴 — 계정을 잠그고 **돈을 멈춘다**. 단일 트랜잭션.

        ★2026-08-15 surface-truth (S3) 가 만든 경로다. 종전 입구는 Clerk `user.deleted` 웹훅이었고
        2026-08-17 ADR-034 로 그 웹훅이 사라졌다 — 입구만 `DELETE /auth/me` 로 옮겼고 **안에서
        하는 일은 한 줄도 바꾸지 않았다.** 여기가 얇아지면 종전 결함이 그대로 돌아온다:
        beat 가 그 사람의 활성 세션을 계속 평가해 저장된 거래소 키로 실주문을 내고, 유출된
        TradingView 웹훅 시크릿도 계속 체결된다.
        """
        user = await self.user_repo.find_by_id(user_id)
        if user is None:
            return
        await self.user_repo.set_inactive(user.id)
        if self.strategy_repo is not None:
            await self.strategy_repo.archive_all_by_owner(user.id)
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


def _normalize_country(raw: str | None) -> str | None:
    """JWT payload 의 country 를 ISO 3166-1 alpha-2 대문자로 정규화한다. 형식이 아니면 None."""
    if raw is None:
        return None
    code = str(raw).strip().upper()
    return code if len(code) == 2 else None
