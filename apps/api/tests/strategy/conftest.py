"""Strategy 테스트용 fixture — slowapi rate-limit storage 를 매 테스트 flush.

★**왜 생겼나(2026-08-28).** `POST /strategies` 에는 `@limiter.limit("30/minute")` 이 붙어
있고 카운터는 **Redis DB 3 에 60초 창으로 남는다**. `tests/strategy` 는 그 엔드포인트를
30번 넘게 부르므로 스위트가 **빠르면 429 로 깨진다** — 실제로 provider 층 리팩터가
느린 HTTP 테스트 5건을 순수 단위 테스트로 바꾸자 즉시 9건이 red 가 됐다.

★즉 종전의 초록은 **「스위트가 느려서」 유지되던 것**이다. 코드 결함이 아니라 테스트가
rate limit 에 의존하고 있었고, 실행 속도·직전 실행 잔여 카운터·개발 중 브라우저 요청 중
무엇이 바뀌어도 터질 수 있었다.

해법은 `tests/waitlist/conftest.py` 가 이미 세운 것과 같다 — 데코레이터가 import 시점
module-level `limiter` 를 캡처하므로 monkeypatch 로는 못 바꾸고, storage 를 직접 비운다.
★rate limit **자체를 검증하는** 테스트(waitlist 429)가 있으므로 전역 비활성화는 하지 않는다.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Module-level limiter 의 storage 를 flush — 매 테스트 clean slate."""
    from src.common import rate_limit as rl

    rl.limiter.reset()
    yield
    rl.limiter.reset()
