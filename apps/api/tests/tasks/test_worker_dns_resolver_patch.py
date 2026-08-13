"""live-signal 데모 dogfood (2026-07-01) — prefork worker DNS resolver 패치 회귀 test.

ccxt 가 강제 의존하는 `aiodns`(aiohttp 기본 AsyncResolver, c-ares 기반) 가
Celery prefork worker 안에서 매 호출 `DNSError: Could not contact DNS servers`
로 100% 재현 실패했다 (동일 셸의 dig/curl/단독 aiodns.DNSResolver 호출은 정상 —
worker 재기동으로도 재현 불변). `_init_worker_state_after_fork` 가
`aiohttp.connector.DefaultResolver` 를 `ThreadedResolver` 로 교체해 이 c-ares
경로를 원천 차단한다.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch

import aiohttp.connector
import aiohttp.resolver
import pytest

from src.tasks.celery_app import _init_worker_state_after_fork


@pytest.fixture(autouse=True)
def _restore_default_resolver() -> Iterator[None]:
    """다른 test 에 aiohttp 전역 상태 누수 방지."""
    original = aiohttp.connector.DefaultResolver  # type: ignore[attr-defined]
    yield
    aiohttp.connector.DefaultResolver = original  # type: ignore[attr-defined]


def test_worker_init_patches_default_resolver_to_threaded() -> None:
    """fork 후 hook 실행 시 DefaultResolver 가 ThreadedResolver 로 교체된다."""
    with (
        patch("src.tasks._worker_loop.init_worker_loop"),
        patch("src.common.redis_client.reset_redis_lock_pool"),
    ):
        _init_worker_state_after_fork()

    assert aiohttp.connector.DefaultResolver is aiohttp.resolver.ThreadedResolver  # type: ignore[attr-defined]
