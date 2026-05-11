"""Convert 라우터 — 인증 및 에러 처리 테스트."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def convert_client() -> TestClient:
    """DB 연결 없이 사용 가능한 동기 테스트 클라이언트."""
    from src.main import create_app

    return TestClient(create_app(), raise_server_exceptions=False)


def test_convert_requires_auth(convert_client: TestClient) -> None:
    """인증 없이 요청 시 401 반환."""
    resp = convert_client.post(
        "/api/v1/strategies/convert-indicator",
        json={"code": '//@version=5\nindicator("T")\nbull=close>open\nplotshape(bull)'},
    )
    assert resp.status_code == 401
