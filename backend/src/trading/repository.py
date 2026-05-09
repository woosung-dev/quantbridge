# trading repository — 6 class shim wrapper (BL-204 Sprint 48 분할)
# DEPRECATED: Sprint 49 에서 제거 예정 — 신규 import 는 src.trading.repositories 에서.
# 1 sprint shim 유지 (BL-204 분할). 95+ 기존 import 사이트 호환성 보존.

from __future__ import annotations

from src.trading.repositories import (
    ExchangeAccountRepository,
    KillSwitchEventRepository,
    LiveSignalEventRepository,
    LiveSignalSessionRepository,
    OrderRepository,
    WebhookSecretRepository,
)

__all__ = [
    "ExchangeAccountRepository",
    "KillSwitchEventRepository",
    "LiveSignalEventRepository",
    "LiveSignalSessionRepository",
    "OrderRepository",
    "WebhookSecretRepository",
]
