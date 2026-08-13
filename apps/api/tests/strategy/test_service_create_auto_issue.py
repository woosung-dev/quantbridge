"""Sprint 13 Phase A.1 — webhook_secret atomic auto-issue + Sprint 6 broken bug 회귀.

dogfood Day 1 의 webhook_secrets 0건 root cause:
- WebhookSecretService.issue() / rotate() 가 self._repo.commit() 미호출
- get_async_session() 자동 commit 안 함 → request 종료 시 rollback

Phase A.1.1: issue/rotate commit 추가 + commit=False 옵션 (atomic create 용)
Phase A.1.2: StrategyService.create() 가 secret_svc.issue(commit=False) 호출 후 단일 commit
Phase A.1.4: StrategyCreateResponse 가 webhook_secret plaintext 1회 포함
"""
from __future__ import annotations

from uuid import UUID

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy import func, select

from src.trading.encryption import EncryptionService
from src.trading.models import WebhookSecret

_OK = """//@version=5
strategy("ok")
long = ta.crossover(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
"""


@pytest.fixture
def crypto() -> EncryptionService:
    return EncryptionService(SecretStr(Fernet.generate_key().decode()))


# ── E2E (POST /strategies — atomic auto-issue + response schema) ─────


@pytest.mark.asyncio
async def test_create_response_includes_plaintext_secret(client, mock_clerk_auth):
    """A.1.4: POST /strategies response 에 webhook_secret plaintext 1회 포함."""
    res = await client.post(
        "/api/v1/strategies",
        json={"name": "auto-issue", "pine_source": _OK},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert "webhook_secret" in body
    assert body["webhook_secret"] is not None
    # secrets.token_urlsafe(32) → base64 URL-safe, ~43 chars
    assert len(body["webhook_secret"]) >= 32


@pytest.mark.asyncio
async def test_get_strategy_does_not_expose_secret(client, mock_clerk_auth):
    """GET /strategies/{id} 응답은 StrategyResponse — webhook_secret 노출 X."""
    res = await client.post(
        "/api/v1/strategies",
        json={"name": "x", "pine_source": _OK},
    )
    sid = res.json()["id"]
    detail = await client.get(f"/api/v1/strategies/{sid}")
    assert detail.status_code == 200
    body = detail.json()
    assert "webhook_secret" not in body


@pytest.mark.asyncio
async def test_create_persists_webhook_secret_to_db(
    client, mock_clerk_auth, db_session
):
    """A.1.2 atomic: DB 에 webhook_secret 1건 영구 저장 (Sprint 6 broken bug 해소)."""
    res = await client.post(
        "/api/v1/strategies",
        json={"name": "persist", "pine_source": _OK},
    )
    assert res.status_code == 201
    strategy_id = UUID(res.json()["id"])

    result = await db_session.execute(
        select(func.count())
        .select_from(WebhookSecret)
        .where(WebhookSecret.strategy_id == strategy_id)  # type: ignore[arg-type]
    )
    assert result.scalar_one() == 1


# Unit tests (issue/rotate commit) — tests/trading/test_webhook_secret_commits.py 참조
