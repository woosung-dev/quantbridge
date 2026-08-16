"""[BL-072] 초대 메일 발신 주소가 **설정에서** 온다.

★수리 전에는 `EmailService.__init__` 의 기본 인자
(`"QuantBridge Waitlist <waitlist@quantbridge.app>"`)가 유일한 값이었다 —
`get_email_service()` 가 `api_key` 만 넘겨서 **실도메인으로 바꿀 경로가 아예 없었다.**
Resend 는 인증된 도메인에서만 발송을 허용하고 이 배포의 도메인은 `qb.woosung.dev` 라,
그대로 두면 Beta 초대 메일이 전건 실패한다.

★[LESSON-092] 2번 — 「그 함수」가 아니라 **「그것을 쓰는 경로」**를 잰다.
`EmailService(from_address=...)` 를 직접 호출해 보는 것은 배선의 증거가 아니다.
여기서는 `get_email_service()` 를 태워 설정값이 실제로 도착하는지 본다.
"""

from __future__ import annotations

import pytest


def test_get_email_service_uses_configured_from_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """설정을 바꾸면 서비스가 그 값을 쥔다."""
    from src.waitlist.dependencies import get_email_service

    monkeypatch.setattr(
        "src.core.config.settings.resend_from_address",
        "QuantBridge <noreply@qb.woosung.dev>",
    )
    svc = get_email_service()
    assert svc._from_address == "QuantBridge <noreply@qb.woosung.dev>"


def test_default_from_address_is_flagged_as_wrong_domain() -> None:
    """★음성 대조 — 기본값은 이 배포에서 **쓰면 안 되는** 값이다.

    이 단언은 「기본값을 바꾸지 마라」가 아니라 **「기본값이 곧 배포 준비 완료가 아니다」**를
    고정한다. 누군가 기본값을 실도메인으로 바꿔 버리면 `.env` 를 안 채운 배포가 조용히
    통과하게 되고, 그때 이 테스트가 red 로 그 사실을 알린다.
    """
    from src.core.config import Settings

    assert "quantbridge.app" in Settings().resend_from_address, (
        "기본 발신 주소가 바뀌었다 — 기본값이 실도메인이 되면 `.env` 미설정 배포가 "
        "발송 실패를 배포 후에야 알게 된다. 바꾸려면 이 계약을 먼저 다시 판단해라."
    )
