"""Outcome parity 순수 파생값의 주문 단위 회귀 테스트."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.trading.outcome_parity import (
    ParityBuckets,
    ParityObservation,
    summarize_parity,
)


def _empty_buckets() -> ParityBuckets:
    return ParityBuckets(
        expected_only_count=0,
        expected_only_gross=Decimal("0"),
        actual_only_count=0,
        actual_only_net=Decimal("0"),
        unattributed_count=0,
    )


def _observation(
    *,
    expected_gross: Decimal,
    actual_net: Decimal,
    actual_gross: Decimal | None = Decimal("0"),
    round_trip_notional: Decimal | None = Decimal("0"),
) -> ParityObservation:
    return ParityObservation(
        expected_gross=expected_gross,
        actual_net=actual_net,
        actual_gross=actual_gross,
        round_trip_notional=round_trip_notional,
    )


def test_reproduces_sql_oracle_totals_and_effective_cost_rate() -> None:
    """프로덕션 DB SQL 손계산 오라클을 주문 합계로 재현한다.

    기대값 21건과 거래소 확정 27건의 집계 차이를 표현할 때, 이 순수 모듈에는
    주문 매칭을 이미 마친 27 관측이 들어온다. 기대 이벤트가 없는 6건은 기대 gross
    0으로 둬서 매칭된 주문 수와 각 금액 합계를 함께 고정한다.
    """
    oracle_observation = _observation(
        expected_gross=Decimal("17.9124"),
        actual_gross=Decimal("16.6437"),
        actual_net=Decimal("-27.6433"),
        round_trip_notional=Decimal("80145.51"),
    )
    expected_events = [oracle_observation] + [
        _observation(expected_gross=Decimal("0"), actual_net=Decimal("0"))
        for _ in range(20)
    ]
    exchange_only_expected = [
        _observation(expected_gross=Decimal("0"), actual_net=Decimal("0"))
        for _ in range(6)
    ]

    summary = summarize_parity([*expected_events, *exchange_only_expected], _empty_buckets())

    assert summary.matched_count == 27
    assert summary.expected_gross == Decimal("17.9124")
    assert summary.actual_gross == Decimal("16.6437")
    assert summary.actual_net == Decimal("-27.6433")
    assert summary.round_trip_notional == Decimal("80145.51")
    assert summary.cost == Decimal("-44.2870")
    assert summary.effective_cost_pct is not None
    assert abs(summary.effective_cost_pct - Decimal("0.05526")) <= Decimal("0.00001")


def test_decomposable_totals_obey_expected_gap_cost_net_identity() -> None:
    """분해 가능한 관측에서는 항등식이 Decimal 산술로 정확히 성립한다."""
    summary = summarize_parity(
        [
            _observation(
                expected_gross=Decimal("100"),
                actual_gross=Decimal("95"),
                actual_net=Decimal("90"),
                round_trip_notional=Decimal("1000"),
            ),
            _observation(
                expected_gross=Decimal("-5"),
                actual_gross=Decimal("-4"),
                actual_net=Decimal("-6"),
                round_trip_notional=Decimal("200"),
            ),
        ],
        _empty_buckets(),
    )

    assert summary.execution_gap is not None
    assert summary.cost is not None
    assert summary.expected_gross + summary.execution_gap + summary.cost == summary.actual_net


def test_waterfall_closes_on_decomposable_subset_only() -> None:
    """워터폴은 전 관측 총계가 아닌 분해 가능 부분집합만 써야 닫힌다."""
    summary = summarize_parity(
        [
            _observation(
                expected_gross=Decimal("10"),
                actual_gross=Decimal("12"),
                actual_net=Decimal("-3"),
                round_trip_notional=Decimal("1000"),
            ),
            _observation(
                expected_gross=Decimal("4"),
                actual_gross=None,
                actual_net=Decimal("-1"),
                round_trip_notional=None,
            ),
        ],
        _empty_buckets(),
    )

    assert summary.decomposable_expected_gross is not None
    assert summary.execution_gap is not None
    assert summary.cost is not None
    assert summary.decomposable_actual_net is not None
    assert (
        summary.decomposable_expected_gross + summary.execution_gap + summary.cost
        == summary.decomposable_actual_net
    )
    assert summary.expected_gross + summary.execution_gap + summary.cost != summary.actual_net


def test_decomposable_totals_are_none_when_nothing_is_decomposable() -> None:
    """gross 를 분해할 수 있는 주문이 없으면 워터폴 양 끝도 제공하지 않는다."""
    summary = summarize_parity(
        [
            _observation(
                expected_gross=Decimal("10"),
                actual_gross=None,
                actual_net=Decimal("-3"),
                round_trip_notional=None,
            ),
            _observation(
                expected_gross=Decimal("4"),
                actual_gross=None,
                actual_net=Decimal("-1"),
                round_trip_notional=None,
            ),
        ],
        _empty_buckets(),
    )

    assert summary.decomposable_expected_gross is None
    assert summary.decomposable_actual_net is None


def test_sums_decimals_without_a_float_intermediate() -> None:
    """float 를 거치면 흔들리는 0.1 세 번의 합도 정확히 보존한다."""
    observations = [
        _observation(
            expected_gross=Decimal("0.1"),
            actual_gross=Decimal("0.1"),
            actual_net=Decimal("0.1"),
            round_trip_notional=Decimal("1"),
        )
        for _ in range(3)
    ]

    summary = summarize_parity(observations, _empty_buckets())

    assert summary.expected_gross == Decimal("0.3")
    assert summary.actual_gross == Decimal("0.3")
    assert summary.actual_net == Decimal("0.3")


def test_undecomposable_observation_stays_out_of_gross_cost_and_notional() -> None:
    """분해 불가 net은 전체 net과 전용 버킷에만 남기고 0으로 가장하지 않는다."""
    summary = summarize_parity(
        [
            _observation(
                expected_gross=Decimal("10"),
                actual_gross=Decimal("9"),
                actual_net=Decimal("8"),
                round_trip_notional=Decimal("100"),
            ),
            _observation(
                expected_gross=Decimal("4"),
                actual_gross=None,
                actual_net=Decimal("-3"),
                round_trip_notional=None,
            ),
        ],
        _empty_buckets(),
    )

    assert summary.actual_net == Decimal("5")
    assert summary.actual_gross == Decimal("9")
    assert summary.cost == Decimal("-1")
    assert summary.round_trip_notional == Decimal("100")
    assert summary.undecomposed_count == 1
    assert summary.undecomposed_net == Decimal("-3")


@pytest.mark.parametrize(
    ("actual_gross", "round_trip_notional"),
    [
        (None, Decimal("100")),
        (Decimal("10"), None),
    ],
)
def test_partial_decomposition_input_is_rejected(
    actual_gross: Decimal | None,
    round_trip_notional: Decimal | None,
) -> None:
    """gross 와 notional 중 하나만 결측이면 조용한 0 보정 없이 즉시 실패한다."""
    with pytest.raises(ValueError):
        _observation(
            expected_gross=Decimal("1"),
            actual_gross=actual_gross,
            actual_net=Decimal("1"),
            round_trip_notional=round_trip_notional,
        )


def test_sample_gate_rejects_the_measured_27_order_sample() -> None:
    """실측 mean, sd, n으로 필요한 64건을 계산하고 성급한 통과를 막는다."""
    mean_net = Decimal("-1.0238")
    sd_net = Decimal("4.0943")
    nets = [mean_net + sd_net] * 13 + [mean_net - sd_net] * 13 + [mean_net]
    observations = [
        _observation(expected_gross=Decimal("0"), actual_net=net) for net in nets
    ]

    summary = summarize_parity(observations, _empty_buckets())

    assert summary.sample.n == 27
    assert summary.sample.mean_net == mean_net
    assert summary.sample.sd_net == sd_net
    assert summary.sample.required_n == 64
    assert summary.sample.sufficient is False


def test_sample_gate_rejects_undefined_or_zero_signal_cases() -> None:
    """n이 1 이하이거나 표준편차 또는 평균이 0이면 표본 통과를 허용하지 않는다."""
    insufficient_n = summarize_parity(
        [_observation(expected_gross=Decimal("0"), actual_net=Decimal("1"))],
        _empty_buckets(),
    )
    zero_sd = summarize_parity(
        [
            _observation(expected_gross=Decimal("0"), actual_net=Decimal("-1")),
            _observation(expected_gross=Decimal("0"), actual_net=Decimal("-1")),
        ],
        _empty_buckets(),
    )
    zero_mean = summarize_parity(
        [
            _observation(expected_gross=Decimal("0"), actual_net=Decimal("-1")),
            _observation(expected_gross=Decimal("0"), actual_net=Decimal("1")),
        ],
        _empty_buckets(),
    )

    for summary in (insufficient_n, zero_sd, zero_mean):
        assert summary.sample.required_n is None
        assert summary.sample.sufficient is False


def test_empty_input_returns_zero_or_none_without_raising() -> None:
    """매칭 주문이 하나도 없어도 빈 상태를 소비자가 안전하게 렌더할 수 있다."""
    buckets = _empty_buckets()

    summary = summarize_parity([], buckets)

    assert summary.matched_count == 0
    assert summary.expected_gross == Decimal("0")
    assert summary.actual_net == Decimal("0")
    assert summary.decomposable_count == 0
    assert summary.decomposable_expected_gross is None
    assert summary.decomposable_actual_net is None
    assert summary.actual_gross is None
    assert summary.execution_gap is None
    assert summary.cost is None
    assert summary.round_trip_notional is None
    assert summary.effective_cost_pct is None
    assert summary.undecomposed_count == 0
    assert summary.undecomposed_net == Decimal("0")
    assert summary.buckets == buckets
    assert summary.coverage_pct is None
    assert summary.sample.n == 0
    assert summary.sample.mean_net is None
    assert summary.sample.sd_net is None
    assert summary.sample.required_n is None
    assert summary.sample.sufficient is False


def test_coverage_uses_all_matched_and_unmatched_order_counts() -> None:
    """coverage 분모는 matched, expected-only, actual-only 주문 수의 합이다."""
    observations = [
        _observation(expected_gross=Decimal("0"), actual_net=Decimal("0"))
        for _ in range(21)
    ]
    buckets = ParityBuckets(
        expected_only_count=51,
        expected_only_gross=Decimal("0"),
        actual_only_count=6,
        actual_only_net=Decimal("0"),
        unattributed_count=0,
    )

    summary = summarize_parity(observations, buckets)

    assert summary.coverage_pct == Decimal("26.92307692307692307692307692")
