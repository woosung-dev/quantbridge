"""Bybit V5 Private WebSocket order stream (Sprint 12 Phase C).

설계 (codex G0/G3/G4 결정 반영):
- **supervisor 패턴** (G4 fix): ``__aenter__`` 가 supervisor task 를 시작하고
  첫 connect 까지 대기 후 반환. supervisor 가 connection 라이프사이클 전체를 관리:
  ConnectionClosed/heartbeat 종료 시 자동 reconnect, auth 실패 시 fatal raise.
- auth: HMAC-SHA256 (`GET/realtime{expires}`), `expires = int((time.time()+1)*1000)`.
  공식 예시 기준 +1s. auth response `success != true` 시 즉시 ``BybitAuthError``.
- heartbeat: 20s ping, ConnectionClosed 시 종료 → supervisor 가 재연결.
- reconnect: exponential backoff 1→2→4→8→16→30s. `qb_ws_reconnect_total` inc.
- **first connect 포함 모든 connect 후 reconciliation 호출** (codex G3 #11) —
  단 30s debounce (codex G3 #4) 로 reconnect storm 시 REST hammering 방지.
- stop event: 외부 set 가능 (worker_shutdown 가 모든 active stream 의 event set).
  ``__aexit__`` 가 supervisor 도 cancel + ws close.
- **FD leak fix** (G4 #5): supervisor 의 finally block 이 ws.close() 보장. auth
  실패 경로에서도 FD 누수 없음.
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
_MAX_BACKOFF_S = 30.0
# G4 revisit fix B: 첫 connect 가 60s 안에 성공 못 하면 fail-fast.
# 무한 connection failure 시 __aenter__ 영원 block 방지.
_FIRST_CONNECT_TIMEOUT_S = 60.0


class BybitAuthError(Exception):
    """Bybit V5 Private WS auth response 가 success!=true 또는 timeout.

    원인: API key 무효 / clock drift > 5s / IP 화이트리스트 위반.
    재시도 무의미 — credentials 갱신 필요. Sprint 13+ 에서 circuit breaker 추가.
    """


class OrderEventHandler(Protocol):
    async def handle_order_event(self, account_id: UUID, payload: dict[str, Any]) -> None: ...


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

    runtime 동작:
    - 첫 connect 가 성공할 때까지 ``__aenter__`` 가 block.
    - 진입 후 supervisor 가 ConnectionClosed → 자동 reconnect 무한 처리.
    - auth 실패 시 ``__aenter__`` 가 BybitAuthError raise (재시도 X).
    - ``__aexit__`` 또는 stop_event set → supervisor 종료 + ws close.
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
        self._supervisor_task: asyncio.Task[None] | None = None
        self._first_connect_event = asyncio.Event()
        self._auth_error: BybitAuthError | None = None
        self._last_reconciled_at: float = 0.0  # monotonic. debounce 30s.

    @property
    def stop_event(self) -> asyncio.Event:
        """외부에서 graceful shutdown 트리거용. worker_shutdown signal 이 set."""
        return self._stop_event

    def _sign(self, expires: int) -> str:
        msg = f"GET/realtime{expires}"
        return hmac.new(self.api_secret.encode(), msg.encode(), hashlib.sha256).hexdigest()

    async def _authenticate(self) -> None:
        """auth payload 송신 + response 검증. 실패 시 BybitAuthError."""
        # codex G0-5: 공식 예시 기준 +1s
        expires = int((time.time() + 1) * 1000)
        signature = self._sign(expires)
        await self._ws.send(json.dumps({"op": "auth", "args": [self.api_key, expires, signature]}))
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
        try:
            await self.reconciler.run(account_id=self.account_id)
        except Exception as exc:
            logger.warning("ws_reconcile_failed account=%s err=%s", self.account_id, exc)

    async def _heartbeat_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(self._heartbeat_interval)
                if self._stop_event.is_set():
                    return
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
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if msg.get("topic") != "order":
                    continue
                if self.handler is None:
                    continue
                for item in msg.get("data", []):
                    try:
                        await self.handler.handle_order_event(self.account_id, item)
                    except Exception as exc:
                        logger.warning(
                            "ws_handler_failed account=%s err=%s",
                            self.account_id,
                            exc,
                        )
        except (ConnectionClosed, asyncio.CancelledError):
            return

    async def _close_ws_safely(self) -> None:
        """ws 가 있으면 close. FD leak 방지 (G4 #5)."""
        if self._ws is None:
            return
        try:
            await self._ws.close(code=1000)
        except Exception as exc:
            logger.debug("ws_close_failed err=%s", exc)
        finally:
            self._ws = None

    async def _supervisor_loop(self) -> None:
        """connection 라이프사이클 관리 — 무한 reconnect (G4 fix).

        흐름:
        1. connect → authenticate → subscribe → reconcile → heartbeat+receive 동시 실행
        2. heartbeat 또는 receive 종료 = 연결 끊김 → backoff 후 reconnect
        3. auth fail = fatal. _auth_error 저장 + first_connect_event set + return
        4. stop_event set = 정상 종료
        """
        backoff = 1.0
        while not self._stop_event.is_set():
            try:
                self._ws = await self._connect_func(self.endpoint)
                await self._authenticate()
                await self._subscribe()
                self.connected = True
                self._first_connect_event.set()
                await self._maybe_reconcile()
                # heartbeat + receive 동시 실행. 둘 중 하나 종료 = 재연결 신호.
                tasks: list[asyncio.Task[Any]] = [
                    asyncio.create_task(self._heartbeat_loop()),
                    asyncio.create_task(self._receive_loop()),
                ]
                _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for p in pending:
                    p.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                self.connected = False
                # 정상 stop_event 면 즉시 종료
                if self._stop_event.is_set():
                    return
                # 연결 끊김 → reconnect 카운트 + metric
                self.reconnect_count += 1
                qb_ws_reconnect_total.labels(account_id=str(self.account_id)).inc()
                logger.info(
                    "ws_supervisor_reconnect account=%s count=%d backoff=%.1f",
                    self.account_id,
                    self.reconnect_count,
                    backoff,
                )
            except BybitAuthError as exc:
                # auth 실패 = fatal. _auth_error 저장 후 main task 에 알림.
                self._auth_error = exc
                self._first_connect_event.set()
                return
            except (ConnectionClosed, OSError) as exc:
                logger.warning(
                    "ws_supervisor_connect_failed account=%s err=%s",
                    self.account_id,
                    exc,
                )
                self.connected = False
            except asyncio.CancelledError:
                return
            finally:
                # 어떤 경로든 ws close 보장 (G4 #5 FD leak fix)
                await self._close_ws_safely()
            # backoff 후 재시도
            if self._stop_event.is_set():
                return
            await asyncio.sleep(min(backoff, _MAX_BACKOFF_S))
            backoff = min(backoff * 2, _MAX_BACKOFF_S)

    async def __aenter__(self) -> BybitPrivateStream:
        if self._stop_event.is_set():
            raise RuntimeError("BybitPrivateStream stop_event set before connect")
        self._supervisor_task = asyncio.create_task(self._supervisor_loop())
        # 첫 연결 또는 stop 까지 대기
        first_done = asyncio.create_task(self._first_connect_event.wait())
        stop_done = asyncio.create_task(self._stop_event.wait())
        try:
            # G4 revisit fix B: 60s startup timeout. 첫 connect 안 되면 fail-fast.
            await asyncio.wait(
                [first_done, stop_done],
                timeout=_FIRST_CONNECT_TIMEOUT_S,
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            for p in (first_done, stop_done):
                if not p.done():
                    p.cancel()
        # G4 revisit fix B: timeout 발생 = Event 둘 다 미 set (cancel 된 task 와 무관).
        if not self._first_connect_event.is_set() and not self._stop_event.is_set():
            await self._wait_supervisor_done()
            raise TimeoutError(
                f"BybitPrivateStream first connect timeout after "
                f"{_FIRST_CONNECT_TIMEOUT_S}s (account={self.account_id})"
            )
        # auth 실패는 first_connect_event 도 set 됨 — 구분 필요
        if self._auth_error is not None:
            await self._wait_supervisor_done()
            raise self._auth_error
        if not self.connected and self._stop_event.is_set():
            await self._wait_supervisor_done()
            raise RuntimeError("BybitPrivateStream stop_event set before first connect")
        return self

    async def _wait_supervisor_done(self) -> None:
        if self._supervisor_task is None:
            return
        if not self._supervisor_task.done():
            self._supervisor_task.cancel()
        await asyncio.gather(self._supervisor_task, return_exceptions=True)

    async def __aexit__(self, *exc_info: Any) -> None:
        # 외부 set 안 됐으면 우리가 set
        self._stop_event.set()
        await self._wait_supervisor_done()
        # supervisor finally 가 ws close 처리하지만 안전망
        await self._close_ws_safely()
        self.connected = False
