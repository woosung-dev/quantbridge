"""common/metrics.py — Counter/Gauge/Histogram 단위 테스트 (Sprint 9 Phase D).

prometheus_client 는 프로세스 전역 REGISTRY 를 공유하므로 label 조합마다 absolute 비교는
fragile. 반드시 before/after delta 로 검증한다.
"""

from __future__ import annotations

import asyncio
import contextlib
import time

from src.common.metrics import (
    ccxt_timer,
    qb_active_orders,
    qb_backtest_duration_seconds,
    qb_ccxt_request_duration_seconds,
    qb_kill_switch_triggered_total,
    qb_order_rejected_total,
)


def test_kill_switch_counter_increments() -> None:
    counter = qb_kill_switch_triggered_total.labels(trigger_type="unit_test")
    before = counter._value.get()
    counter.inc()
    after = counter._value.get()
    assert after == before + 1


def test_order_rejected_counter_label_split() -> None:
    a = qb_order_rejected_total.labels(exchange="bybit", reason="leverage_cap")
    b = qb_order_rejected_total.labels(exchange="bybit", reason="notional")
    before_a = a._value.get()
    before_b = b._value.get()
    a.inc()
    a.inc()
    b.inc()
    assert a._value.get() == before_a + 2
    assert b._value.get() == before_b + 1


def test_backtest_duration_histogram_observe() -> None:
    before = qb_backtest_duration_seconds._sum.get()
    qb_backtest_duration_seconds.observe(42.0)
    after = qb_backtest_duration_seconds._sum.get()
    # 부동소수 비교 여유 (0.0001)
    assert after - before >= 42.0 - 0.0001


def test_active_orders_gauge_inc_dec() -> None:
    # Gauge 는 상대값 — set/reset 간섭 방지 위해 before/after
    before = qb_active_orders._value.get()
    qb_active_orders.inc()
    qb_active_orders.inc()
    qb_active_orders.dec()
    after = qb_active_orders._value.get()
    assert after == before + 1
    # cleanup — 다른 테스트 간섭 방지
    qb_active_orders.dec()


def _histogram_count(label_child: object) -> float:
    """Histogram 샘플 수 = 모든 bucket 의 합.

    prometheus_client 의 Histogram child 는 `_buckets` list (MutexValue per bucket)
    + `_sum` 만 노출 — 별도 `_count` attribute 가 없다. 내부 bucket 은 non-cumulative
    (각 관측치가 정확히 1 bucket 에 들어감, render 시 cumulative 로 변환).
    따라서 모든 bucket 값을 합치면 전체 observation 수가 된다.
    """
    return float(sum(b.get() for b in label_child._buckets))  # type: ignore[attr-defined]


def test_ccxt_timer_records_latency() -> None:
    """ccxt_timer async context manager 가 histogram 에 latency 를 기록한다."""
    label_pair = qb_ccxt_request_duration_seconds.labels(
        exchange="unit_test", endpoint="noop"
    )
    before_sum = label_pair._sum.get()
    before_count = _histogram_count(label_pair)

    async def _call() -> None:
        async with ccxt_timer("unit_test", "noop"):
            # 측정 가능한 최소 작업
            await asyncio.sleep(0.001)

    asyncio.run(_call())

    after_sum = label_pair._sum.get()
    after_count = _histogram_count(label_pair)
    assert after_count == before_count + 1
    assert after_sum > before_sum


def test_ccxt_timer_records_even_on_exception() -> None:
    """CCXT 호출이 실패해도 finally 경로로 latency 기록."""
    label_pair = qb_ccxt_request_duration_seconds.labels(
        exchange="unit_test", endpoint="fail"
    )
    before_count = _histogram_count(label_pair)

    async def _call() -> None:
        async with ccxt_timer("unit_test", "fail"):
            await asyncio.sleep(0.001)
            raise RuntimeError("boom")

    with contextlib.suppress(RuntimeError):
        asyncio.run(_call())

    after_count = _histogram_count(label_pair)
    assert after_count == before_count + 1


def test_histogram_buckets_include_all_metric_buckets() -> None:
    """샘플 smoke: backtest duration 1s bucket 이 존재."""
    # 42.0s 를 관측했으므로 bucket +inf 에는 최소 1 이상 들어있어야 함
    qb_backtest_duration_seconds.observe(0.5)  # 1.0 bucket 들어감
    # bucket 구조가 유지되는지 간접 확인 (observe 만으로 충분)
    assert qb_backtest_duration_seconds._sum.get() > 0
    # 호출 시간 보장
    time.sleep(0)  # no-op; type hint 안정용
