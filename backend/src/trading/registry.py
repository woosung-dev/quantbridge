# trading provider registry — 3-tuple (exchange, mode, has_leverage) → factory dispatch
"""Provider dispatch registry — Sprint 47 BL-202.

`tasks/trading.py:_provider_for_account_and_leverage` 가 사용하던 3-tuple
if-chain 을 dict registry 로 승격. 새 (exchange, mode, has_leverage) 조합 추가
시 if-chain 갱신 대신 PROVIDER_REGISTRY 한 군데만 수정.

Celery prefork-safe (CRITICAL):
- 본 모듈은 CCXT 클라이언트나 async engine 을 import 시점에 절대 인스턴스화하지 않는다.
- factory 는 매 dispatch 호출마다 `Provider()` 를 생성하는 per-call factory.
- Provider 클래스 자체의 `create_order` 안에서 ccxt 인스턴스가 생기고 finally close() 됨
  (`providers.py` 의 ephemeral CCXT client 패턴).
- Worker pool=prefork 고정. SQLAlchemy `create_async_engine()` 등 무거운 객체는
  module import 시점 호출 금지 (.claude/CLAUDE.md QuantBridge 고유 규칙).

Iron law: registry 추가 시 반드시 factory 가 lambda/class-instantiation 만 수행하고
어떠한 module-level side effect (engine / CCXT instance / network call) 도 일으키지
말 것. 회귀 방어 = `tests/tasks/test_trading_prefork_safe.py`.
"""

from __future__ import annotations

from collections.abc import Callable

from src.trading import providers
from src.trading.exceptions import UnsupportedExchangeError
from src.trading.models import ExchangeMode, ExchangeName

# factory signature: () -> ExchangeProvider. 매 dispatch 마다 새 인스턴스.
ProviderFactory = Callable[[], providers.ExchangeProvider]


# (exchange, mode, has_leverage) → factory.
# Sprint 22 BL-091 의 if-chain 을 그대로 옮긴 것 — 의미 변경 없음.
PROVIDER_REGISTRY: dict[tuple[ExchangeName, ExchangeMode, bool], ProviderFactory] = {
    # Bybit Demo Spot
    (ExchangeName.bybit, ExchangeMode.demo, False): providers.BybitDemoProvider,
    # Bybit Demo Linear Perpetual (USDT margined) — Sprint 7a
    (ExchangeName.bybit, ExchangeMode.demo, True): providers.BybitFuturesProvider,
    # OKX Spot sandbox via CCXT (passphrase 필수) — Sprint 7d
    (ExchangeName.okx, ExchangeMode.demo, False): providers.OkxDemoProvider,
    # Bybit Live (BL-003 mainnet runbook 까지 stub. has_leverage 양쪽 모두 동일 stub).
    (ExchangeName.bybit, ExchangeMode.live, False): providers.BybitLiveProvider,
    (ExchangeName.bybit, ExchangeMode.live, True): providers.BybitLiveProvider,
}


def dispatch(
    exchange: ExchangeName,
    mode: ExchangeMode,
    has_leverage: bool,
) -> providers.ExchangeProvider:
    """Sprint 22 BL-091 의 본체. (exchange, mode, has_leverage) → concrete provider.

    Sprint 47 BL-202: if-chain → dict registry lookup.
    실패 정책 (P1 #2): 미지원 조합 → UnsupportedExchangeError(ProviderError) raise.
    호출처 (`_execute_with_session` line 214 / `_fetch_order_status_with_session`)
    의 `except ProviderError` 가 자동 catch → Order graceful `rejected` 전이.
    """
    key = (exchange, mode, has_leverage)
    factory = PROVIDER_REGISTRY.get(key)
    if factory is None:
        raise UnsupportedExchangeError(key)
    return factory()
