"""현재 공개 거래 제품의 불변 정책.

계정 데이터에는 과거 live/OKX 행이 남아 있을 수 있다. 그 행을 삭제하지 않되,
자격증명 복호화와 거래소 egress의 모든 새 진입점은 이 정책을 통과해야 한다.
"""

from __future__ import annotations

from src.trading.exceptions import BybitDemoOnlyError
from src.trading.models import ExchangeMode, ExchangeName


def is_bybit_demo_account(exchange: ExchangeName, mode: ExchangeMode) -> bool:
    """사용자 거래·private API가 허용되는 유일한 계정 조합인지 반환한다."""
    return exchange is ExchangeName.bybit and mode is ExchangeMode.demo


def require_bybit_demo_account(exchange: ExchangeName, mode: ExchangeMode) -> None:
    """Bybit Demo 이외의 사용자 거래 egress를 fail-closed로 막는다."""
    if not is_bybit_demo_account(exchange, mode):
        raise BybitDemoOnlyError(exchange=exchange, mode=mode)
