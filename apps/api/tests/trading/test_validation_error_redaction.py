"""422 응답이 요청 원문을 되돌려 주지 않는다 (2026-08-15 surface-truth · S2).

**실사고 모양** — `RegisterAccountRequest` 의 `@model_validator(mode="after")` 는 body 파싱
**뒤에** 돈다. FastAPI 기본 `RequestValidationError` 핸들러가 `exc.errors()` 를 그대로
직렬화하므로, `loc == ["body"]` 인 그 에러의 `"input"` 에는 **요청 body 전체**가 실린다.
2026-08-15 실측:

    POST /api/v1/exchange-accounts {"exchange":"okx", ..., "api_secret":"SUPER_SECRET_VALUE"}
    → 422 {"detail":[{"type":"value_error", "loc":["body"],
                       "msg":"Value error, OKX accounts require a passphrase",
                       "input":{"api_key":"AKIA_REAL_KEY","api_secret":"SUPER_SECRET_VALUE"}}]}

거래소 API secret 평문이 응답 body 로 되돌아오면 브라우저 콘솔·프록시 로그·에러 텔레메트리에
남는다. 트리거는 OKX 등록 시 passphrase 누락 하나면 된다.

★**이 파일은 세 종류를 함께 잰다** — 양성(값이 없다) · **음성 대조**(진단 정보는 남는다) ·
회귀(정상 등록은 그대로 201). 음성 대조가 없으면 「422 body 를 통째로 비우기」로도 통과해
판별력이 0 이 된다.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from src.main import _scrub_validation_input
from src.trading.providers import BybitFuturesProvider

_API_KEY = "AKIA_REAL_KEY_0123456789"
_API_SECRET = "SUPER_SECRET_VALUE_abcdefgh"
_PASSPHRASE = "PASSPHRASE_PLAINTEXT_zzz"


@pytest.fixture(autouse=True)
def mock_exchange_identity(monkeypatch):
    identity = AsyncMock(return_value=("558689281", False))
    monkeypatch.setattr(BybitFuturesProvider, "fetch_api_identity", identity)
    return identity


def _assert_no_credentials(raw: str) -> None:
    """응답 원문 어디에도 자격증명 값과 `input` 키가 없어야 한다."""
    for needle in (_API_KEY, _API_SECRET, _PASSPHRASE):
        assert needle not in raw, f"422 body 에 자격증명 평문이 남아 있다: {needle!r} in {raw}"
    assert '"input"' not in raw, f"422 body 에 `input` 키가 남아 있다: {raw}"


@pytest.mark.asyncio
async def test_okx_missing_passphrase_422_hides_request_body(client, mock_authed_user):
    """★양성 — `mode="after"` validator 경로. body 전체가 `input` 에 실리던 자리다."""
    res = await client.post(
        "/api/v1/exchange-accounts",
        json={
            "exchange": "okx",
            "mode": "demo",
            "api_key": _API_KEY,
            "api_secret": _API_SECRET,
        },
    )
    assert res.status_code == 422, res.text
    _assert_no_credentials(res.text)


@pytest.mark.asyncio
async def test_field_level_422_hides_field_value(client, mock_authed_user):
    """★양성 — 필드 단위(`max_length`) 실패. 이쪽 `input` 은 그 **필드 값**이다."""
    res = await client.post(
        "/api/v1/exchange-accounts",
        json={
            "exchange": "bybit",
            "mode": "demo",
            "api_key": _API_KEY,
            "api_secret": _API_SECRET + "x" * 200,  # max_length=200 초과
        },
    )
    assert res.status_code == 422, res.text
    _assert_no_credentials(res.text)


@pytest.mark.asyncio
async def test_422_still_reports_which_field_and_why(client, mock_authed_user):
    """★음성 대조 — 진단 정보(`loc`·`msg`·`type`)는 **남아야** 한다.

    이게 없으면 「detail 을 통째로 비우기」가 위 두 테스트를 통과한다(판별력 0).
    FE 는 어느 필드가 왜 틀렸는지 알아야 하고, 그 셋은 값이 아니라 값의 **위치와 규칙**이다.
    """
    res = await client.post(
        "/api/v1/exchange-accounts",
        json={
            "exchange": "bybit",
            "mode": "demo",
            "api_key": _API_KEY,
            "api_secret": _API_SECRET + "x" * 200,
        },
    )
    assert res.status_code == 422, res.text
    detail = res.json()["detail"]
    assert isinstance(detail, list) and detail, f"기본 봉투 모양이 유지돼야 한다: {res.text}"
    err = detail[0]
    assert err["loc"][-1] == "api_secret", f"어느 필드인지 남아야 한다: {err}"
    assert err["type"] == "string_too_long", f"어떤 규칙인지 남아야 한다: {err}"
    assert err["msg"], f"사람이 읽을 사유가 남아야 한다: {err}"


@pytest.mark.asyncio
async def test_valid_registration_still_succeeds(client, mock_authed_user):
    """회귀 — redaction 이 정상 경로를 건드리지 않는다(201 + 암호화 저장 마스킹)."""
    res = await client.post(
        "/api/v1/exchange-accounts",
        json={
            "exchange": "bybit",
            "mode": "demo",
            "api_key": "ABCD1234EFGH5678",
            "api_secret": "secret_value_here_1234",
            "label": "redaction regression",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert "******" in body["api_key_masked"]
    assert "secret_value_here_1234" not in res.text


def test_scrub_removes_nested_input_keys() -> None:
    """★깊이 축 — union/중첩 모델은 `ctx` 안에 또 다른 error list 를 담는다.

    최상위 `input` 만 지우면 그 중첩분이 샌다. 재귀 스크럽의 단위 증거.
    """
    payload = [
        {
            "type": "union_tag_invalid",
            "loc": ["body"],
            "msg": "boom",
            "input": {"api_secret": "TOP_LEVEL_SECRET"},
            "ctx": {
                "errors": [{"type": "missing", "loc": ["body", "x"], "input": "NESTED_SECRET"}]
            },
        }
    ]
    scrubbed = json.dumps(_scrub_validation_input(payload))
    assert "TOP_LEVEL_SECRET" not in scrubbed
    assert "NESTED_SECRET" not in scrubbed
    assert "union_tag_invalid" in scrubbed, "type 은 남아야 한다"
    assert '"loc"' in scrubbed, "loc 은 남아야 한다"
