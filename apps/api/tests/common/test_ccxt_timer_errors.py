"""Sprint 10 Phase D — ccxt_timer 의 error counter 검증.

TDD 4 case:
1. 정상 호출 (except 미발동) -> qb_ccxt_request_errors_total 미증가
2. ExchangeError raise -> counter +1 (exchange/endpoint/error_class=ExchangeError) + raise 보존
   + finally duration histogram count +1 (finally 실행 보장)
3. 커스텀 예외 raise -> error_class = type(exc).__name__ 정확 라벨링
4. asyncio.CancelledError -> BaseException 하위이므로 counter 미증가 + finally duration 기록
"""

from __future__ import annotations

import pytest

from src.common.metrics import (
    ccxt_timer,
    qb_ccxt_request_duration_seconds,
    qb_ccxt_request_errors_total,
)


def _counter_value(exchange: str, endpoint: str, error_class: str) -> float:
    """Counter labels value 조회 — _value.get() 으로 현재 누적치 반환."""
    return qb_ccxt_request_errors_total.labels(
        exchange=exchange, endpoint=endpoint, error_class=error_class
    )._value.get()


def _histogram_count(exchange: str, endpoint: str) -> float:
    """Histogram 의 _count series (요청 총 수) 조회.

    prometheus_client Histogram 의 labeled child 에서 `_count` sample 을 찾아
    반환한다. `_child_samples()` 는 bucket / _count / _sum / _created 를 포함.
    """
    labeled = qb_ccxt_request_duration_seconds.labels(
        exchange=exchange, endpoint=endpoint
    )
    for sample in labeled._child_samples():
        if sample.name == "_count":
            return sample.value
    return 0.0


@pytest.mark.asyncio
async def test_ccxt_timer_normal_path_does_not_increment_errors() -> None:
    """정상 호출 (yield 만) -> errors counter 절대 inc 하지 않음."""
    before = _counter_value("bybit", "create_order", "ExchangeError")
    async with ccxt_timer("bybit", "create_order"):
        pass  # 정상 종료
    after = _counter_value("bybit", "create_order", "ExchangeError")
    assert after == before, f"counter must not inc on success (before={before}, after={after})"


@pytest.mark.asyncio
async def test_ccxt_timer_on_exception_increments_errors_and_reraises() -> None:
    """예외 raise 시 errors counter +1 + 원 예외 그대로 전파 + finally duration 기록.

    Sprint 11 Phase G 이후 allowlist 기반으로 레이블링 → ccxt 공식 예외 사용 필수.
    """
    from ccxt import ExchangeError

    before_err = _counter_value("bybit_futures", "cancel_order", "ExchangeError")
    before_hist = _histogram_count("bybit_futures", "cancel_order")

    with pytest.raises(ExchangeError, match="boom"):
        async with ccxt_timer("bybit_futures", "cancel_order"):
            raise ExchangeError("boom")

    after_err = _counter_value("bybit_futures", "cancel_order", "ExchangeError")
    after_hist = _histogram_count("bybit_futures", "cancel_order")

    assert after_err == before_err + 1, (
        f"errors counter +1 기대. before={before_err}, after={after_err}"
    )
    # finally 실행 보장 회귀 방어 — 예외 경로에서도 duration histogram count +1
    assert after_hist == before_hist + 1, (
        f"finally 의 duration observe 가 예외 경로에서도 실행되어야. "
        f"before={before_hist}, after={after_hist}"
    )


@pytest.mark.asyncio
async def test_ccxt_timer_labels_error_class_exactly() -> None:
    """서로 다른 예외 클래스 각각 독립 시리즈로 라벨링.

    Sprint 11 Phase G — allowlist 에 포함된 ccxt 공식 예외는 원 이름 유지.
    """
    from ccxt import InsufficientFunds, RateLimitExceeded

    before_rate = _counter_value("okx", "fetch_balance", "RateLimitExceeded")
    before_funds = _counter_value("okx", "fetch_balance", "InsufficientFunds")

    with pytest.raises(RateLimitExceeded):
        async with ccxt_timer("okx", "fetch_balance"):
            raise RateLimitExceeded()

    with pytest.raises(InsufficientFunds):
        async with ccxt_timer("okx", "fetch_balance"):
            raise InsufficientFunds()

    assert _counter_value("okx", "fetch_balance", "RateLimitExceeded") == before_rate + 1
    assert _counter_value("okx", "fetch_balance", "InsufficientFunds") == before_funds + 1


@pytest.mark.asyncio
async def test_ccxt_timer_does_not_count_cancellation_as_error() -> None:
    """asyncio.CancelledError 는 Python 3.8+ BaseException 하위 — `except Exception` 미포착.

    Task cancellation 은 오류가 아닌 정상 제어 흐름이므로 counter 미증가 +
    duration 만 finally 에서 기록. 회귀 방어.
    """
    import asyncio

    before_count = _counter_value("bybit", "fetch_ohlcv", "CancelledError")
    before_hist = _histogram_count("bybit", "fetch_ohlcv")

    with pytest.raises(asyncio.CancelledError):
        async with ccxt_timer("bybit", "fetch_ohlcv"):
            raise asyncio.CancelledError()

    after_count = _counter_value("bybit", "fetch_ohlcv", "CancelledError")
    after_hist = _histogram_count("bybit", "fetch_ohlcv")

    assert after_count == before_count, (
        f"CancelledError 는 task 제어 흐름 — errors counter 미증가. "
        f"before={before_count}, after={after_count}"
    )
    assert after_hist == before_hist + 1, (
        f"CancelledError 경로도 finally 실행 — duration observe 필수. "
        f"before={before_hist}, after={after_hist}"
    )
