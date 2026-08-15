"""geo-block L3 — 제한 국가 차단 + `country_code` 저장 (ADR-034 로 입구가 바뀌었다).

★★**종전 이 파일은 무증거였다.** L3 는 Clerk webhook 의 `public_metadata.country` 를 읽었는데
그 값을 넣는 코드가 **FE 어디에도 없었다**(2026-08-17 grep 0건). 테스트는 페이로드를 자기가
만들어 초록이었고, 프로덕션에서 이 분기는 **한 번도 발화한 적이 없다.**

지금의 정문은 `apps/web/src/lib/auth.ts` 의 Better Auth `databaseHooks.user.create.before` 이고
(가입 요청의 `CF-IPCountry` 를 직접 본다), 백엔드는 **JWT payload 의 `country`** 로 같은 판정을
한 겹 더 한다. 이 파일은 그 백스톱을 잰다.
"""

from __future__ import annotations

import uuid

import pytest

from src.auth.exceptions import GeoBlockedCountryError
from src.auth.repository import UserRepository
from src.auth.service import UserService


def _service(db_session) -> UserService:
    return UserService(user_repo=UserRepository(db_session))


@pytest.mark.asyncio
async def test_restricted_country_blocks_first_provisioning(db_session) -> None:
    """음성 — 제한 국가(US)의 토큰은 사용자 행을 만들지 못한다."""
    service = _service(db_session)
    subject = f"user_{uuid.uuid4().hex[:8]}"

    with pytest.raises(GeoBlockedCountryError):
        await service.get_or_create(
            auth_subject=subject, email="us@example.com", username=None, country_code="US"
        )

    assert await service.user_repo.find_by_auth_subject(subject) is None


@pytest.mark.asyncio
async def test_allowed_country_is_stored(db_session) -> None:
    """양성 — 허용 국가는 통과하고 `country_code` 가 대문자로 저장된다."""
    service = _service(db_session)
    subject = f"user_{uuid.uuid4().hex[:8]}"

    user = await service.get_or_create(
        auth_subject=subject, email="kr@example.com", username=None, country_code="kr"
    )

    assert user.country_code == "KR"


@pytest.mark.asyncio
async def test_missing_country_is_not_blocked(db_session) -> None:
    """음성 대조 — 국가를 모르는 토큰은 **차단하지 않는다**.

    ★이것이 판별력의 핵심이다. 헤더가 없는 로컬 개발과 국가 정보 이전에 만들어진 사용자를
    막으면 L3 가 「전건 차단」이 되어 아무것도 재지 못한다.
    """
    service = _service(db_session)
    subject = f"user_{uuid.uuid4().hex[:8]}"

    user = await service.get_or_create(
        auth_subject=subject, email="unknown@example.com", username=None, country_code=None
    )

    assert user.country_code is None


@pytest.mark.asyncio
async def test_malformed_country_is_ignored_not_trusted(db_session) -> None:
    """형식이 아닌 값(길이 2 아님)은 국가로 인정하지 않는다 — 저장도 차단도 하지 않는다."""
    service = _service(db_session)
    subject = f"user_{uuid.uuid4().hex[:8]}"

    user = await service.get_or_create(
        auth_subject=subject, email="x@example.com", username=None, country_code="USA"
    )

    assert user.country_code is None


@pytest.mark.asyncio
async def test_existing_user_is_not_kicked_out_by_country(db_session) -> None:
    """이미 있는 사용자는 국가로 쫓아내지 않는다 — 차단은 **최초 프로비저닝** 시점뿐이다.

    Sprint 11 Phase A 가 웹훅에서 `user.created` 에만 차단을 걸었던 것과 같은 정책이다.
    """
    service = _service(db_session)
    subject = f"user_{uuid.uuid4().hex[:8]}"
    await service.get_or_create(
        auth_subject=subject, email="kr@example.com", username=None, country_code="KR"
    )

    user = await service.get_or_create(
        auth_subject=subject, email="kr@example.com", username=None, country_code="US"
    )

    assert user.is_active is True
    assert user.country_code == "US"
