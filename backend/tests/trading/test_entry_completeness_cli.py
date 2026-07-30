# CLI 가 counter 스냅샷을 읽는 부분만 고정한다 — 없는 숫자를 지어내지 않는지가 핵심이다

"""BL-536 ③ 데이터 원천.

`qb_live_conditional_cancelled_total` 은 **프로세스 전역 누적** counter 이고 세션 label 이
없다. DB 만으로는 특정 soak 창의 `replaced` 차분을 복원할 수 없고, multiprocess registry 도
현재 합계를 렌더할 뿐 과거 창을 되살리지 못한다. 그래서 CLI 는 창 양 끝의 `/metrics`
스냅샷을 **명시 입력**으로 받는다. 이 파일은 그 파싱과 차분이 조용히 틀리지 않게 잠근다.
"""

from __future__ import annotations

from scripts.entry_completeness_report import _reading, parse_metrics_text
from src.trading.entry_completeness import CounterBasis

_DUMP = """
# HELP qb_live_conditional_placed_total Live conditional entry intents accepted for execution
# TYPE qb_live_conditional_placed_total counter
qb_live_conditional_placed_total{direction="long"} 70.0
qb_live_conditional_placed_total{direction="short"} 56.0
qb_live_conditional_guard_total{outcome="conditional_placed"} 92.0
qb_live_conditional_guard_total{outcome="market_converted"} 34.0
qb_live_conditional_cancelled_total{reason="replaced"} 25.0
qb_live_conditional_cancelled_total{reason="desired_removed"} 3.0
qb_metrics_render_fallback_total 0.0
garbage line that is not a sample
qb_live_conditional_placed_total{direction="long"} not_a_number
"""


def test_snapshot_parser_reads_labels_and_bare_series() -> None:
    snapshot = parse_metrics_text(_DUMP)
    assert snapshot.value("qb_live_conditional_placed_total", direction="long") == 70.0
    assert snapshot.value("qb_live_conditional_guard_total", outcome="market_converted") == 34.0
    assert snapshot.value("qb_metrics_render_fallback_total") == 0.0
    # 없는 series 는 0 이다 — counter 는 처음 발화 전까지 노출되지 않는다.
    assert snapshot.value("qb_live_conditional_guard_total", outcome="breach_capped") == 0.0
    assert len(snapshot.series("qb_live_conditional_cancelled_total")) == 2


def test_measured_placed_vs_guard_gap_is_exactly_market_converted() -> None:
    """★실측 126 vs 92 를 이 스냅샷으로 재현한다 — 차 34 는 시장가 전환분이다."""
    snapshot = parse_metrics_text(_DUMP)
    placed = sum(value for _labels, value in snapshot.series("qb_live_conditional_placed_total"))
    guard = snapshot.value(
        "qb_live_conditional_guard_total", outcome="conditional_placed"
    ) + snapshot.value("qb_live_conditional_guard_total", outcome="market_converted")
    assert placed == 126.0
    assert guard == 126.0
    assert placed == guard


def test_reading_from_two_snapshots_is_a_delta() -> None:
    after = parse_metrics_text(_DUMP)
    before = parse_metrics_text('qb_live_conditional_cancelled_total{reason="replaced"} 20.0\n')
    reading = _reading(before, after, "qb_live_conditional_cancelled_total", reason="replaced")
    assert reading is not None
    assert (reading.value, reading.basis) == (5.0, CounterBasis.delta)


def test_reading_is_none_without_an_after_snapshot() -> None:
    """★스냅샷이 없으면 숫자를 지어내지 않는다. `None` 이 "미제공" 을 그대로 표면화한다."""
    assert _reading(None, None, "qb_live_conditional_cancelled_total", reason="replaced") is None


def test_probe_distinguishes_absent_series_from_zero() -> None:
    """★`value()` 의 0.0 기본값이 두 사실을 뭉갠다 — 차분 계산은 `probe` 를 써야 한다."""
    snapshot = parse_metrics_text(_DUMP)
    assert snapshot.value("qb_live_conditional_guard_total", outcome="breach_capped") == 0.0
    assert snapshot.probe("qb_live_conditional_guard_total", outcome="breach_capped") is None
    assert snapshot.probe("qb_live_conditional_guard_total", outcome="conditional_placed") == 92.0
