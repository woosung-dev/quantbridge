"""POST /api/v1/waitlist — 8 TDD.

1. 정상 submit → 202
2. duplicate email → 409
3. TV subscription Pro 미만 → 422
4. exchange_capital under_1k 는 허용하되 enum 에 포함 (실 필드 검증은 422 로 invalid 값만)
5. pain_point < 3자 → 422
6. pain_point > 1000자 → 422
7. DB 저장 확인
8. rate limit 5/hour → 6 번째 429

구현 메모:
- app fixture 가 FastAPI app + DB override 제공. mock_clerk_auth 불필요 (public endpoint).
- rate-limit 테스트는 별도 fixture 로 memory:// storage + custom limiter 주입.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.waitlist.models import WaitlistApplication, WaitlistStatus


def _valid_body(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "email": "alice@example.com",
        "tv_subscription": "pro_plus",
        "exchange_capital": "1k_to_10k",
        "pine_experience": "beginner",
        "existing_tool": "TradingView alerts",
        "pain_point": "Manual copy-paste of alerts to Bybit is painful and error-prone.",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_submit_waitlist_returns_202(client) -> None:
    res = await client.post("/api/v1/waitlist", json=_valid_body())
    assert res.status_code == 202, res.text
    body = res.json()
    assert body["status"] == "pending"
    assert "id" in body


@pytest.mark.asyncio
async def test_submit_waitlist_duplicate_email_returns_409(client) -> None:
    r1 = await client.post("/api/v1/waitlist", json=_valid_body())
    assert r1.status_code == 202
    r2 = await client.post("/api/v1/waitlist", json=_valid_body())
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "waitlist_duplicate_email"


@pytest.mark.asyncio
async def test_submit_waitlist_saves_to_db(client, db_session: AsyncSession) -> None:
    res = await client.post("/api/v1/waitlist", json=_valid_body(email="bob@example.com"))
    assert res.status_code == 202

    result = await db_session.execute(
        select(WaitlistApplication).where(
            WaitlistApplication.email == "bob@example.com"  # type: ignore[arg-type]
        )
    )
    saved = result.scalar_one()
    assert saved.tv_subscription == "pro_plus"
    assert saved.status == WaitlistStatus.pending
    assert saved.pain_point.startswith("Manual copy-paste")


@pytest.mark.asyncio
async def test_submit_waitlist_rejects_tv_subscription_free(client) -> None:
    """Pro+ 미만 (free/basic) 는 Literal 에 없음 → 422."""
    res = await client.post(
        "/api/v1/waitlist",
        json=_valid_body(email="c@example.com", tv_subscription="free"),
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_submit_waitlist_requires_capital_enum(client) -> None:
    """exchange_capital 은 enum 만 허용 — invalid 값은 422."""
    res = await client.post(
        "/api/v1/waitlist",
        json=_valid_body(email="d@example.com", exchange_capital="nothing"),
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_submit_waitlist_pain_point_too_short(client) -> None:
    res = await client.post(
        "/api/v1/waitlist",
        json=_valid_body(email="e@example.com", pain_point="hi"),
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_submit_waitlist_pain_point_too_long(client) -> None:
    res = await client.post(
        "/api/v1/waitlist",
        json=_valid_body(email="f@example.com", pain_point="x" * 1001),
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_submit_waitlist_rate_limited_after_5_per_hour(client) -> None:
    """6 번째 요청부터 429 — conftest autouse fixture 가 limiter storage flush.

    @limiter.limit("5/hour") 는 import 시점 module-level limiter 를 캡처하므로
    rate-limit storage flush 만으로 카운터 초기화 가능.
    """
    # 5 건 성공 (각기 다른 이메일 — unique 충돌 방지)
    for i in range(5):
        r = await client.post(
            "/api/v1/waitlist",
            json=_valid_body(email=f"rl{i}@example.com"),
        )
        assert r.status_code == 202, f"iter {i}: {r.text}"
    # 6 번째 429
    r6 = await client.post(
        "/api/v1/waitlist",
        json=_valid_body(email="rl5@example.com"),
    )
    assert r6.status_code == 429
    assert r6.json()["detail"]["code"] == "rate_limit_exceeded"
