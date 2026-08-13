# 알림 규칙 채널별 발송을 서로 격리해 fan-out 하는 디스패처

from __future__ import annotations

import logging
from typing import Any

from src.common.alert import send_critical_alert
from src.common.telegram_alert import send_telegram_critical_alert
from src.core.config import Settings
from src.trading.models import AlertChannel

logger = logging.getLogger(__name__)


async def send_rule_alert(
    settings: Settings,
    *,
    channel: AlertChannel,
    title: str,
    message: str,
    context: dict[str, Any],
) -> dict[str, bool]:
    """채널 한쪽 실패가 다른 채널 발송을 막지 않도록 독립 실행한다."""
    result: dict[str, bool] = {}
    if channel in (AlertChannel.slack, AlertChannel.both):
        try:
            result["slack"] = await send_critical_alert(settings, title, message, context)
        except Exception:
            logger.exception("alert_rule_slack_failed")
            result["slack"] = False
    if channel in (AlertChannel.telegram, AlertChannel.both):
        try:
            result["telegram"] = await send_telegram_critical_alert(
                settings, title, message, context
            )
        except Exception:
            logger.exception("alert_rule_telegram_failed")
            result["telegram"] = False
    return result
