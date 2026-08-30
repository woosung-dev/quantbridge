"""[BL-772] LLM 변환 실패가 내부 예외 문자열을 응답에 반사하지 않는다.

★**누출 표면은 원장이 적은 1곳이 아니라 3곳이었다**(2026-08-16 코드 대조):

1. `router.py` 502 — `detail=f"...{type(exc).__name__}: {exc}"` (원장이 지목한 것)
2. `router.py` 503 — `detail=str(exc)`. 서비스가 만드는 RuntimeError 메시지 자체가
   SDK 예외의 타입·본문을 f-string 으로 심고 있었다(`service.py` 3곳)
3. ★**`service.py` 의 `fallback_warnings`** — Anthropic→Gemini fallback 시 SDK 예외
   문자열이 `warnings[]` 에 담겨 **200 응답 본문**으로 나갔다. 실패 경로가 아니라
   **성공 경로**라 훨씬 자주 노출된다

SDK 예외 메시지는 엔드포인트 URL·모델명·요청 ID·때로는 요청 본문 일부를 담는다.
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

# 실제 SDK 예외 문자열이 담는 것들을 흉내낸 표지 — 응답 어디에도 나오면 안 된다.
_LEAK_MARKER = "https://api.anthropic.com/v1/messages model=claude-x req_id=req_0xDEADBEEF"


class _SdkBoomError(Exception):
    """SDK 예외를 대신하는 표지. 클래스 이름 자체가 누출 여부의 판별자다."""


@pytest.fixture(scope="module")
def leak_client() -> Iterator[TestClient]:
    """DB 없이 도는 클라이언트 — 인증과 ConvertService 를 둘 다 override 한다."""
    from src.auth.dependencies import get_current_user
    from src.auth.schemas import CurrentUser
    from src.main import create_app
    from src.strategy.convert.dependencies import get_convert_service

    app = create_app()

    async def _fake_user() -> CurrentUser:
        return CurrentUser(
            id="00000000-0000-0000-0000-000000000001",
            auth_subject="leak-test-subject",
            email=None,
            username=None,
            is_active=True,
        )

    class _BoomService:
        mode = "unexpected"

        def convert(self, _req: object) -> object:
            if self.mode == "runtime":
                raise RuntimeError(f"양쪽 provider 모두 실패 {_LEAK_MARKER}")
            raise _SdkBoomError(_LEAK_MARKER)

    boom = _BoomService()
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_convert_service] = lambda: boom

    client = TestClient(app, raise_server_exceptions=False)
    client.boom = boom  # type: ignore[attr-defined]
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _reset_rate_limit() -> Iterator[None]:
    """이 엔드포인트는 `5/minute` 이라 한 모듈 안에서 금방 429 가 된다.

    ★버킷 키가 `ip:testclient` 인 것 자체가 [BL-754] 가 지목한 공용 버킷 붕괴다 —
    여기서는 그것을 고치지 않고 매 테스트 리셋으로 우회한다.
    """
    from src.common.rate_limit import limiter

    limiter.reset()
    yield
    limiter.reset()


def _post(client: TestClient) -> httpx.Response:
    return client.post(
        "/api/v1/strategies/convert-indicator",
        json={"code": '//@version=5\nindicator("T")\nbull=close>open\nplotshape(bull)'},
    )


@pytest.mark.parametrize(
    ("mode", "expected_status", "expected_code"),
    [
        ("unexpected", 502, "llm_convert_failed"),
        ("runtime", 503, "llm_provider_unavailable"),
    ],
)
def test_error_body_leaks_nothing(
    leak_client: TestClient, mode: str, expected_status: int, expected_code: str
) -> None:
    """502·503 **양쪽** 본문에 예외 클래스명도 SDK 문자열도 없어야 한다.

    ★503 을 함께 재는 것이 이 테스트의 핵심이다 — 원장은 502 만 지목했는데
    실제로는 503 경로가 서비스의 RuntimeError 메시지를 그대로 실어 나갔다.
    """
    leak_client.boom.mode = mode  # type: ignore[attr-defined]
    resp = _post(leak_client)

    assert resp.status_code == expected_status
    body = resp.text

    assert _LEAK_MARKER not in body, "SDK 예외 문자열이 응답에 반사됐다"
    assert "_SdkBoomError" not in body, "예외 클래스명이 응답에 반사됐다"
    assert "RuntimeError" not in body, "예외 클래스명이 응답에 반사됐다"

    detail = resp.json()["detail"]
    assert detail["code"] == expected_code
    # ★지운 대가를 상쇄하는 것이 상관 ID 다 — 없으면 사용자 문의를 추적할 수 없다.
    assert len(detail["error_id"]) == 12
    assert int(detail["error_id"], 16) >= 0


def test_error_id_differs_per_request(leak_client: TestClient) -> None:
    """상관 ID 가 상수면 로그와 못 잇는다."""
    leak_client.boom.mode = "unexpected"  # type: ignore[attr-defined]
    first = _post(leak_client).json()["detail"]["error_id"]
    second = _post(leak_client).json()["detail"]["error_id"]
    assert first != second


def test_fallback_warning_carries_no_sdk_text() -> None:
    """성공 응답 warning은 실제 provider/model만 보이고 내부 실패를 반사하지 않는다.

    `service.convert()` 를 실제로 태워 `warnings[]` 에 SDK 문자열이 없는지 본다.
    라우터를 안 거치므로 위 두 테스트가 못 잡는 축이다.
    """
    from types import SimpleNamespace
    from unittest.mock import patch

    from src.strategy.convert.schemas import ConvertIndicatorRequest
    from src.strategy.convert.service import ConvertService
    from src.strategy.narrative.providers import JsonCompletion

    settings = SimpleNamespace(gemini_model="gemini-test")
    svc = ConvertService(settings)

    with patch(
        "src.strategy.convert.service.complete_json",
        return_value=JsonCompletion(payload={"converted_code": "//ok"}, provider="gemini"),
    ):
        resp = svc.convert(
            ConvertIndicatorRequest(code='//@version=5\nindicator("T")\nplot(close)')
        )

    joined = " ".join(resp.warnings)
    assert _LEAK_MARKER not in joined, "SDK 예외 문자열이 200 응답의 warnings 로 나갔다"
    assert "_SdkBoomError" not in joined, "예외 클래스명이 200 응답의 warnings 로 나갔다"
    assert resp.warnings[0] == "gemini gemini-test 로 변환 완료"
    assert "fallback" not in joined.lower()
