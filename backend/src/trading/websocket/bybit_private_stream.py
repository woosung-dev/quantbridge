"""Bybit V5 Private WebSocket order stream (Sprint 12 Phase C).

설계 (codex G0/G3 결정 반영):
- auth: HMAC-SHA256 (`GET/realtime{expires}`), `expires = int((time.time()+1)*1000)`
  공식 예시 기준 +1s. auth response `success != true` 시 즉시 ``BybitAuthError``.
- heartbeat: 20s ping, 60s 무응답 시 reconnect.
- reconnect: exponential backoff 1→2→4→8→16→30s.
- **first connect 포함 모든 connect 후 reconciliation 호출** (codex G3 #11) —
  단 30s debounce (codex G3 #4) 로 reconnect storm 시 REST hammering 방지.
- stop event: 외부 set 가능 (worker_shutdown / SIGTERM hook). ``__aexit__`` 가
  receive_loop / heartbeat_loop 를 cancel + ws.close.
- single-account guard 는 ``websocket_task.py`` 의 process-level set 으로 처리
  (이 모듈은 stream lifecycle 만).
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Protocol
from uuid import UUID

import websockets
from websockets.exceptions import ConnectionClosed

from src.common.metrics import qb_ws_reconcile_skipped_total, qb_ws_reconnect_total

logger = logging.getLogger(__name__)

_RECONCILE_DEBOUNCE_S = 30.0
_AUTH_TIMEOUT_S = 5.0


class BybitAuthError(Exception):
    """Bybit V5 Private WS auth response 가 success!=true 또는 timeout.

    원인: API key 무효 / clock drift > 5s / IP 화이트리스트 위반.
    재시도 무의미 — credentials 갱신 필요. Sprint 13+ 에서 circuit breaker 추가.
    """


class OrderEventHandler(Protocol):
    async def handle_order_event(
        self, account_id: UUID, payload: dict[str, Any]
    ) -> None: ...


class StreamReconciler(Protocol):
    async def run(self, *, account_id: UUID) -> None: ...


class BybitPrivateStream:
    """Bybit V5 Private order stream — async context manager.

    사용:
        stop_event = asyncio.Event()
        async with BybitPrivateStream(
            endpoint=ENDPOINT, api_key=KEY, api_secret=SECRET,
            account_id=acc_id, handler=handler, reconciler=reconciler,
            stop_event=stop_event,
        ) as stream:
            await stop_event.wait()  # graceful shutdown 시 외부에서 set
    """

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        api_secret: str,
        account_id: UUID,
        handler: OrderEventHandler | None = None,
        reconciler: StreamReconciler | None = None,
        stop_event: asyncio.Event | None = None,
        heartbeat_interval: float = 20.0,
        connect_func: Any = None,  # test injection (websockets.connect 대체)
    ) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.api_secret = api_secret
        self.account_id = account_id
        self.handler = handler
        self.reconciler = reconciler
        self._stop_event = stop_event or asyncio.Event()
        self._heartbeat_interval = heartbeat_interval
        self._connect_func = connect_func or websockets.connect

        self.connected = False
        self.reconnect_count = 0
        self._ws: Any = None
        self._tasks: list[asyncio.Task[Any]] = []
        self._last_reconciled_at: float = 0.0  # monotonic. debounce 30s.

    def _sign(self, expires: int) -> str:
        msg = f"GET/realtime{expires}"
        return hmac.new(
            self.api_secret.encode(), msg.encode(), hashlib.sha256
        ).hexdigest()

    async def _authenticate(self) -> None:
        """auth payload 송신 + response 검증."""
        # codex G0-5: 공식 예시 기준 +1s
        expires = int((time.time() + 1) * 1000)
        signature = self._sign(expires)
        await self._ws.send(
            json.dumps(
                {"op": "auth", "args": [self.api_key, expires, signature]}
            )
        )
        # auth response 5s 내 도착 + success=True 검증
        try:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=_AUTH_TIMEOUT_S)
        except TimeoutError as exc:
            raise BybitAuthError(
                f"Bybit auth response timeout after {_AUTH_TIMEOUT_S}s — "
                f"network issue or endpoint misconfig (account={self.account_id})"
            ) from exc
        msg = json.loads(raw)
        if msg.get("op") == "auth" and msg.get("success") is True:
            return
        ret_msg = msg.get("ret_msg") or msg.get("retMsg") or "unknown"
        raise BybitAuthError(
            f"Bybit auth rejected: {ret_msg} "
            f"(account={self.account_id}). "
            "Check API key validity, IP whitelist, system clock (max ±5s drift)."
        )

    async def _subscribe(self) -> None:
        await self._ws.send(json.dumps({"op": "subscribe", "args": ["order"]}))

    async def _maybe_reconcile(self) -> None:
        """30s debounce 로 reconciliation 호출. reconnect storm 시 skip."""
        if self.reconciler is None:
            return
        now = time.monotonic()
        if now - self._last_reconciled_at < _RECONCILE_DEBOUNCE_S:
            qb_ws_reconcile_skipped_total.inc()
            return
        self._last_reconciled_at = now
        await self.reconciler.run(account_id=self.account_id)

    async def _heartbeat_loop(self) -> None:
        try:
            while self.connected and not self._stop_event.is_set():
                await asyncio.sleep(self._heartbeat_interval)
                try:
                    await self._ws.send(json.dumps({"op": "ping"}))
                except ConnectionClosed:
                    return
        except asyncio.CancelledError:
            return

    async def _receive_loop(self) -> None:
        try:
            async for raw in self._ws:
                if self._stop_event.is_set():
                    return
                msg = json.loads(raw)
                # auth/subscribe ack 는 무시
                if msg.get("topic") != "order":
                    continue
                if self.handler is None:
                    continue
                for item in msg.get("data", []):
                    try:
                        await self.handler.handle_order_event(
                            self.account_id, item
                        )
                    except Exception as exc:
                        # handler 예외가 stream 차단 안 함 — log + continue
                        logger.warning(
                            "ws_handler_failed account=%s err=%s",
                            self.account_id,
                            exc,
                        )
        except (ConnectionClosed, asyncio.CancelledError):
            self.connected = False

    async def __aenter__(self) -> BybitPrivateStream:
        backoff = 1.0
        while not self._stop_event.is_set():
            try:
                self._ws = await self._connect_func(self.endpoint)
                await self._authenticate()
                await self._subscribe()
                self.connected = True
                # codex G3 #11: first connect 포함 모든 connect 후 reconcile.
                # debounce 30s 가 storm 차단.
                await self._maybe_reconcile()
                self._tasks = [
                    asyncio.create_task(self._heartbeat_loop()),
                    asyncio.create_task(self._receive_loop()),
                ]
                return self
            except BybitAuthError:
                # auth 실패는 재시도 무의미
                raise
            except (ConnectionClosed, OSError) as exc:
                logger.warning(
                    "ws_connect_failed account=%s err=%s backoff=%.1f",
                    self.account_id,
                    exc,
                    backoff,
                )
                self.reconnect_count += 1
                qb_ws_reconnect_total.labels(account_id=str(self.account_id)).inc()
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
        # stop_event 가 set 된 채 진입 — fast-fail
        raise RuntimeError("BybitPrivateStream stop_event set before connect")

    async def __aexit__(self, *exc_info: Any) -> None:
        self.connected = False
        for t in self._tasks:
            t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._ws is not None:
            try:
                await self._ws.close(code=1000)
            except Exception as exc:
                logger.debug("ws_close_failed err=%s", exc)
