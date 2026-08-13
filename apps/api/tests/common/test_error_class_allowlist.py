"""Sprint 11 Phase G — error_class allowlist 검증.

Prometheus `qb_ccxt_request_errors_total` 의 `error_class` 레이블이 cardinality
안전한 allowlist + "Other" 버킷으로 수렴함을 검증.
"""

from __future__ import annotations

import pytest

from src.common.metrics import ccxt_timer, qb_ccxt_request_errors_total


@pytest.mark.asyncio
async def test_known_ccxt_exception_uses_original_name() -> None:
    """ccxt.NetworkError 처럼 allowlist 에 포함된 예외는 원 클래스명을 라벨로 사용."""
    from ccxt import NetworkError

    before = qb_ccxt_request_errors_total.labels(
        exchange="bybit",
        endpoint="allowlist_create_order",
        error_class="NetworkError",
    )._value.get()

    with pytest.raises(NetworkError):
        async with ccxt_timer("bybit", "allowlist_create_order"):
            raise NetworkError("timeout")

    after = qb_ccxt_request_errors_total.labels(
        exchange="bybit",
        endpoint="allowlist_create_order",
        error_class="NetworkError",
    )._value.get()
    assert after - before == 1


@pytest.mark.asyncio
async def test_unknown_custom_exception_falls_back_to_other_bucket() -> None:
    """allowlist 에 없는 동적 커스텀 예외는 "Other" 버킷으로 수렴."""

    class DynamicWeirdError(Exception):
        pass

    before_other = qb_ccxt_request_errors_total.labels(
        exchange="bybit",
        endpoint="allowlist_custom",
        error_class="Other",
    )._value.get()
    before_custom = qb_ccxt_request_errors_total.labels(
        exchange="bybit",
        endpoint="allowlist_custom",
        error_class="DynamicWeirdError",
    )._value.get()

    with pytest.raises(DynamicWeirdError):
        async with ccxt_timer("bybit", "allowlist_custom"):
            raise DynamicWeirdError("unexpected")

    after_other = qb_ccxt_request_errors_total.labels(
        exchange="bybit",
        endpoint="allowlist_custom",
        error_class="Other",
    )._value.get()
    after_custom = qb_ccxt_request_errors_total.labels(
        exchange="bybit",
        endpoint="allowlist_custom",
        error_class="DynamicWeirdError",
    )._value.get()

    # "Other" 버킷이 증가해야 함.
    assert after_other - before_other == 1
    # 동적 클래스명 라벨은 증가하지 않음 (prometheus_client 은 .labels() 호출 시
    # 시리즈를 만들지만 counter 값이 증가하지 않으면 allowlist 외 분류로 간주).
    assert after_custom == before_custom
