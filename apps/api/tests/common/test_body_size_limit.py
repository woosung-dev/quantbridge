"""앱 전역 요청 본문 크기 상한 — 보안 감사 run-2 후속."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient

from src.common.body_size_limit import MAX_REQUEST_BODY_BYTES

_OVER = MAX_REQUEST_BODY_BYTES + 1
_PATH = "/api/v1/strategies"


@pytest.mark.asyncio
async def test_declared_oversized_body_is_rejected_with_413(client: AsyncClient) -> None:
    res = await client.post(
        _PATH, content=b"x" * _OVER, headers={"content-type": "application/json"}
    )
    assert res.status_code == 413


@pytest.mark.asyncio
async def test_streamed_oversized_body_without_length_is_rejected_with_413(
    client: AsyncClient,
) -> None:
    async def chunks() -> AsyncIterator[bytes]:
        chunk = b"x" * 65536
        for _ in range(_OVER // len(chunk) + 1):
            yield chunk

    res = await client.post(_PATH, content=chunks(), headers={"content-type": "application/json"})
    assert "content-length" not in res.request.headers
    assert res.status_code == 413


@pytest.mark.asyncio
async def test_body_under_cap_reaches_the_app(client: AsyncClient) -> None:
    # 인증 없는 정상 크기 본문은 상한이 아니라 앱(인증)이 판정한다.
    res = await client.post(
        _PATH,
        content=b"{" + b" " * (MAX_REQUEST_BODY_BYTES - 2) + b"}",
        headers={"content-type": "application/json"},
    )
    assert res.status_code != 413
