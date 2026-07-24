# 알림 규칙 디스패처의 채널 라우팅과 실패 격리를 검증한다

from __future__ import annotations

import pytest

from src.core.config import settings
from src.trading.models import AlertChannel


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("channel", "expected"),
    [
        (AlertChannel.slack, {"slack": True}),
        (AlertChannel.telegram, {"telegram": True}),
        (AlertChannel.both, {"slack": True, "telegram": True}),
    ],
)
async def test_send_rule_alert_routes_selected_channels(
    channel: AlertChannel, expected: dict[str, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    import src.trading.alerting as alerting

    async def _ok(*_args, **_kwargs):
        return True

    monkeypatch.setattr(alerting, "send_critical_alert", _ok)
    monkeypatch.setattr(alerting, "send_telegram_critical_alert", _ok)
    assert await alerting.send_rule_alert(
        settings, channel=channel, title="t", message="m", context={}
    ) == expected


@pytest.mark.asyncio
async def test_send_rule_alert_isolates_one_channel_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.trading.alerting as alerting

    async def _fail(*_args, **_kwargs):
        raise RuntimeError("slack unavailable")

    async def _ok(*_args, **_kwargs):
        return True

    monkeypatch.setattr(alerting, "send_critical_alert", _fail)
    monkeypatch.setattr(alerting, "send_telegram_critical_alert", _ok)
    assert await alerting.send_rule_alert(
        settings, channel=AlertChannel.both, title="t", message="m", context={}
    ) == {"slack": False, "telegram": True}
