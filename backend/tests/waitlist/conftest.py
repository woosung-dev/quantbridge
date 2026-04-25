"""Waitlist 테스트용 fixture — slowapi rate-limit storage 를 매 테스트 flush.

문제: `@limiter.limit("5/hour")` 데코레이터는 import 시점 module-level `limiter`
객체를 캡처. monkeypatch 로 module attr 만 바꿔서는 이미 decorated 된 라우터
엔드포인트에 반영되지 않는다.

해결: slowapi 의 storage reset 을 직접 호출 (limiter.reset()).
이는 memory:// 뿐 아니라 Redis storage 의 카운터도 전부 삭제.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Module-level limiter 의 storage 를 flush — 매 테스트 clean slate."""
    from src.common import rate_limit as rl

    rl.limiter.reset()
    yield
    rl.limiter.reset()
