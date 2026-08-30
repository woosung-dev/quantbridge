"""Sprint 12 Phase C — Bybit Private WebSocket order stream.

M2 Slim scope (codex G3 결정):
- BybitPrivateStream: auth + heartbeat + reconnect + first-connect reconcile
- StateHandler/Reconciler: transport callback adapter
- DB transition은 `trading.services.websocket_*`가 Repository를 통해 처리

dogfood 1-user 가정 (Sprint 13+ multi-account scaling).
"""

from src.trading.websocket.bybit_private_stream import (
    BybitAuthError,
    BybitPrivateStream,
)
from src.trading.websocket.position_fanout import PositionFanoutHandler, PrivateTopicRouter
from src.trading.websocket.reconciliation import Reconciler
from src.trading.websocket.state_handler import StateHandler

__all__ = [
    "BybitAuthError",
    "BybitPrivateStream",
    "PositionFanoutHandler",
    "PrivateTopicRouter",
    "Reconciler",
    "StateHandler",
]
