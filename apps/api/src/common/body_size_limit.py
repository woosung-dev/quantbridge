"""앱 전역 요청 본문 크기 상한 (순수 ASGI 미들웨어).

보안 감사 run-2(2026-11-19) — 웹훅(64KB) 말고는 본문 상한이 없었다. FastAPI 는 JWT 검사·
rate limit 데코레이터보다 **먼저** 본문 전체를 메모리에 올리고 JSON 을 디코드하므로,
401/422 로 끝나는 익명 요청도 큰 본문으로 메모리·CPU 를 쓸 수 있었다.

- `Content-Length` 가 상한을 넘으면 앱을 부르지 않고 413.
- 길이 없이(chunked) 흘려 보내도 받은 바이트를 세다가 넘는 순간 413 을 보내고 앱 쪽 수신을 끊는다.
- 가장 큰 정상 본문은 Pine 원본 100,000자 · 변환 code 131,072자(이스케이프 포함 1MB 미만)라 2MiB 면 여유가 있다.
"""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_REQUEST_BODY_BYTES = 2 * 1024 * 1024


class _BodyTooLarge(Exception):
    """상한 초과 — 앱의 본문 읽기를 끊는다."""


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_REQUEST_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def _send_413(self, send: Send) -> None:
        body = json.dumps({"detail": f"request body too large (max {self.max_bytes}B)"}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = -1
                if declared > self.max_bytes:
                    await self._send_413(send)
                    return
                break

        received = 0
        rejected = False
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received, rejected
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    rejected = True
                    if not response_started:
                        await self._send_413(send)
                    raise _BodyTooLarge
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal response_started
            if rejected:
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            # 413 을 이미 보냈다면 앱 쪽 후속 예외(FastAPI 는 본문 읽기 실패를 400 으로 바꾼다)는 삼킨다.
            if not rejected:
                raise
