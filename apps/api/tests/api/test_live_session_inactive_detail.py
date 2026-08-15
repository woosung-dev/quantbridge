"""비활성 세션의 상세 경로가 200 을 준다는 계약을 고정한다 (BL-423).

★이 파일이 존재하는 이유 — 2026-07-30 실측으로 `trading/router.py` 에 `is_active` 게이트가
한 곳도 없음을 확인했다(`grep -n is_active` → 0 hit). 즉 **동작은 이미 맞다.** 그런데 그걸
고정하는 테스트가 하나도 없어서, 누가 "활성 세션만 조회" 라는 그럴듯한 필터를 넣어도 아무
테스트도 깨지지 않았다. 세션이 fail-closed 로 죽은 뒤 사후 조사가 필요한 화면이 정확히
이 경로들이므로(BL-423 의 본체), 회귀를 여기서 막는다.

`/positions` 는 strategy.settings 미설정 → `settings_unset` 경로를 쓴다. 거래소 왕복 없이
소유·존재 게이트만 통과하는지 재는 것이 목적이라 provider 를 태우지 않는다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    AlertChannel,
    AlertRule,
    AlertRuleType,
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
    SessionDeactivationReason,
)

_BASE = datetime(2026, 7, 30, 12, tzinfo=UTC)


async def _seed_inactive_session(
    db_session: AsyncSession,
    user: User,
    *,
    reason: str | None = SessionDeactivationReason.runtime_divergence,
) -> LiveSignalSession:
    """종료된 세션 1건 + 알림 규칙 1건을 심는다. strategy.settings 는 비워 둔다."""
    strategy = Strategy(
        user_id=user.id,
        name="inactive-detail",
        pine_source="//@version=5\nstrategy('inactive-detail')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"key",
        api_secret_encrypted=b"secret",
    )
    db_session.add_all([strategy, account])
    await db_session.flush()

    session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
        is_active=False,
        created_at=_BASE - timedelta(hours=2),
        deactivated_at=_BASE - timedelta(hours=1),
        deactivated_reason=reason,
    )
    db_session.add(session)
    await db_session.flush()
    db_session.add(
        AlertRule(
            session_id=session.id,
            rule_type=AlertRuleType.loss_limit,
            # ck_alert_rules_type_threshold — loss_limit 은 임계값이 있어야 한다.
            threshold_percent=Decimal("5"),
            channel=AlertChannel.slack,
        )
    )
    await db_session.commit()
    return session


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "suffix",
    ["/state", "/positions", "/alert-rules", "/events", "/outcome-parity"],
)
async def test_inactive_session_detail_paths_stay_reachable(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_authed_user: User,
    suffix: str,
) -> None:
    """종료된 세션도 상세 경로 전부 200. `is_active` 필터가 새로 들어오면 여기서 깨진다."""
    session = await _seed_inactive_session(db_session, mock_authed_user)

    response = await client.get(f"/api/v1/live-sessions/{session.id}{suffix}")

    assert response.status_code == 200, f"{suffix} → {response.status_code} {response.text}"


@pytest.mark.asyncio
async def test_inactive_session_positions_reports_unsupported_without_touching_exchange(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_authed_user: User,
) -> None:
    """`/positions` 의 200 이 거래소 왕복 없이 나온 것임을 명시한다(위 테스트의 근거 고정).

    settings 미설정이므로 `settings_unset` 이어야 하고, 이 값이 바뀌면 위 200 판정이
    실은 provider 를 태우고 있었다는 뜻이라 테스트 전제가 무너진다.
    """
    session = await _seed_inactive_session(db_session, mock_authed_user)

    body = (await client.get(f"/api/v1/live-sessions/{session.id}/positions")).json()

    assert body["supported"] is False
    assert body["reason"] == "settings_unset"


@pytest.mark.asyncio
async def test_live_session_list_serializes_deactivation_reason(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_authed_user: User,
) -> None:
    """BL-484 — 목록 응답이 사유를 실제로 내보낸다. 화면은 이 필드로만 사유를 안다."""
    session = await _seed_inactive_session(db_session, mock_authed_user)

    body = (await client.get("/api/v1/live-sessions?include_inactive=true")).json()

    rows = {item["id"]: item for item in body["items"]}
    assert rows[str(session.id)]["deactivated_reason"] == "runtime_divergence"


@pytest.mark.asyncio
async def test_live_session_list_keeps_null_reason_for_legacy_rows(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_authed_user: User,
) -> None:
    """마이그레이션 이전에 죽은 행은 `null` 로 나간다 — 빈 문자열로 위장하지 않는다."""
    session = await _seed_inactive_session(db_session, mock_authed_user, reason=None)

    body = (await client.get("/api/v1/live-sessions?include_inactive=true")).json()

    rows = {item["id"]: item for item in body["items"]}
    assert rows[str(session.id)]["deactivated_reason"] is None
