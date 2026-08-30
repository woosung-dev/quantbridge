# registry.dispatch 의 모듈 레벨 불변식(per-call factory + 미지원 매트릭스) 회귀 가드
"""trading.registry 모듈 단위 불변식 테스트 (BL-309, W3).

dispatch 의 (exchange, mode, has_leverage) → provider 매핑 자체는
``tests/tasks/test_provider_dispatch.py`` 가 ``_provider_for_account_and_leverage``
wrapper 경유로 이미 망라 검증(5-tuple + unsupported + .key + ProviderError 서브클래스).
본 파일은 그 wrapper-suite 가 검증하지 않는 **registry 모듈 자체의 불변식 2종**만 추가:

1. per-call factory — prefork-safe iron law(registry.py docstring): 매 dispatch 가
   새 provider 인스턴스를 만들어야 worker child fork 후 stale CCXT/engine 공유가 없다.
   wrapper-suite 는 인스턴스 *타입*만 보고 *동일성(per-call)*은 검증하지 않는다.
2. 미지원 매트릭스 빈칸 (okx, live, True) — 현재 어느 테스트도 직접 단언하지 않는
   유일한 조합(test_provider_dispatch 는 (okx,demo,True)/(okx,live,False)/binance 만).
"""

from __future__ import annotations

import pytest

from src.trading import registry
from src.trading.exceptions import BybitDemoOnlyError, ProviderError
from src.trading.models import ExchangeMode, ExchangeName
from src.trading.providers import BybitDemoProvider


def test_dispatch_returns_new_instance_per_call() -> None:
    """prefork-safe iron law — 같은 key 2회 dispatch 가 서로 다른 인스턴스.

    registry.py 의 factory 는 per-call (`Provider()` 매번 생성). 만약 누군가
    factory 를 module-level singleton (`provider = BybitDemoProvider()`) 으로
    바꾸면 Celery prefork child 들이 stale CCXT client/engine 을 공유 → 2nd+
    task 부터 silent fail. 이 불변식이 그 회귀를 차단.
    """
    key = (ExchangeName.bybit, ExchangeMode.demo, False)
    first = registry.dispatch(*key)
    second = registry.dispatch(*key)
    assert isinstance(first, BybitDemoProvider)
    assert isinstance(second, BybitDemoProvider)
    assert first is not second  # per-call 생성 (singleton 아님)


def test_dispatch_legacy_okx_live_futures_is_blocked_by_product_policy() -> None:
    """registry는 legacy provider를 만들기 전에 Bybit Demo 제품 정책을 강제한다."""
    key = (ExchangeName.okx, ExchangeMode.live, True)
    with pytest.raises(BybitDemoOnlyError) as exc_info:
        registry.dispatch(*key)
    assert isinstance(exc_info.value, ProviderError)
