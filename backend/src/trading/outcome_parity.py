"""라이브 청산 결과와 pine_v2 기대값의 read-time parity 요약.

이 모듈은 거래소 청산을 새로 계산하거나 판정하지 않는다. 이미 주문 단위로 매칭된
관측을 받아, 엔진 기대 gross 와 거래소 확정 net 사이의 차이를 보여 줄 수 있는
파생값만 만든다. 특히 산술 항등식 자체는 항상 성립하므로 정합성 검사가 아니다.
어떤 청산이 매칭되었고 어떤 청산이 버킷에 남았는지를 함께 보존해야 결과를
과신하지 않는다.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_CEILING, Context, Decimal, localcontext

# Numeric(18,8) 곱은 36 자리까지 갈 수 있어 기본 28 자리에서는 조용히 반올림된다.
# 요약의 합산, 분산, 제곱근은 이 로컬 컨텍스트 안에서만 계산한다.
PARITY_DECIMAL_CONTEXT = Context(prec=50)

# 표본 크기 기준의 관례값이다. 관측 데이터에서 역산하면 표본이 자신의 통과 기준을
# 바꾸게 되므로, 정책 상수로 고정한다.
PARITY_SE_MULTIPLIER = Decimal("2")

# 표본 표준편차가 평균의 분포를 대표하려면 중심극한정리 근사가 성립해야 한다.
# n 이 이보다 작으면 sd 추정 자체가 신뢰할 수 없어, 정밀도 계산이 무의미하다.
# 이 값은 관측 데이터가 아니라 추정량의 요구조건에서 온다.
MIN_OBSERVATIONS_FOR_VARIANCE = 30


@dataclass(frozen=True, slots=True)
class ParityObservation:
    """매칭된 청산 주문 1건의 parity 입력이다. leg 가 아니라 주문이 단위다.

    거래소가 gross 와 round-trip notional 을 모두 줄 때만 체결가 차이와 비용을 분해할
    수 있다. 둘 중 하나만 결측인 것은 부분 분해가 아니라 해석 계약 위반이므로,
    0으로 메우면 비용이 없는 주문처럼 보이는 위험을 막기 위해 생성 시점에 거부한다.
    """

    expected_gross: Decimal
    actual_net: Decimal
    actual_gross: Decimal | None
    round_trip_notional: Decimal | None

    def __post_init__(self) -> None:
        if (self.actual_gross is None) != (self.round_trip_notional is None):
            raise ValueError(
                "actual_gross and round_trip_notional must both be None or both be Decimal"
            )


@dataclass(frozen=True, slots=True)
class ParityBuckets:
    """주문 매칭에 들어오지 못한 우리 청산의 손익 버킷이다.

    이 버킷은 요약 산술에 억지로 합치지 않는다. expected-only, actual-only,
    ledger-only는 서로 다른 관측 집합이므로 각각을 남겨야 coverage 가 손익의
    완전성을 정직하게 드러낸다.
    """

    expected_only_count: int
    expected_only_gross: Decimal
    expected_only_pending_count: int
    expected_only_failed_count: int
    expected_only_dispatched_count: int
    actual_only_count: int
    actual_only_net: Decimal
    ledger_only_count: int
    ledger_only_net: Decimal


@dataclass(frozen=True, slots=True)
class SampleVerdict:
    """매칭 주문 net 표본이 성능 비율을 말할 만큼 충분한지의 판정이다.

    gross 와 수수료는 한 주문에서 함께 나온 짝지어진 값이다. 이를 독립 표본처럼
    세면 불확실성을 잘못 줄이므로, 주문당 확정 net 하나만 표본으로 삼아 평균의
    표준오차 기준 표본 크기를 계산한다.
    """

    n: int
    mean_net: Decimal | None
    sd_net: Decimal | None
    required_n: int | None
    sufficient: bool


@dataclass(frozen=True, slots=True)
class ParitySummary:
    """주문 단위 parity 관측을 화면 소비자가 그대로 읽을 수 있게 묶은 결과다.

    `expected_gross` 와 `actual_net` 은 모든 매칭 관측을 합산한다. 반면 gross 를 알 수
    없는 주문은 execution gap 과 비용의 어느 한쪽에도 임의 배분할 수 없으므로,
    분해 파생값은 decomposable 관측만 합산하고 나머지는 undecomposed 버킷에 남긴다.

    워터폴은 `decomposable_expected_gross`, `execution_gap`, `cost`,
    `decomposable_actual_net` 네 값만으로 그린다. 전 관측 합계를 분해 파생값과 섞으면
    분해 불가 주문의 net이 빠져 막대가 닫히지 않는다.

    `round_trip_notional`은 진입과 청산 두 leg의 notional 합이다. 따라서 이를 분모로 한
    비용률은 편도 값이며, 비용 가정의 왕복 값과 비교할 때는 별도 왕복 값만 사용한다.
    """

    matched_count: int
    expected_gross: Decimal
    actual_net: Decimal
    decomposable_count: int
    decomposable_expected_gross: Decimal | None
    decomposable_actual_net: Decimal | None
    actual_gross: Decimal | None
    execution_gap: Decimal | None
    cost: Decimal | None
    round_trip_notional: Decimal | None
    effective_cost_pct_per_leg: Decimal | None
    effective_cost_pct_round_trip: Decimal | None
    edge_pct_round_trip: Decimal | None
    cost_to_edge_ratio: Decimal | None
    undecomposed_count: int
    undecomposed_net: Decimal
    buckets: ParityBuckets
    match_coverage_pct: Decimal | None
    decomposition_coverage_pct: Decimal | None
    sample: SampleVerdict


def _sum_decimals(values: Iterable[Decimal]) -> Decimal:
    """금융 합산을 Decimal 영역에서만 수행한다."""
    with localcontext(PARITY_DECIMAL_CONTEXT):
        total = Decimal("0")
        for value in values:
            total = Decimal(str(total)) + Decimal(str(value))
        return total


def _sample_verdict(
    observations: Sequence[ParityObservation],
    *,
    se_multiplier: Decimal,
) -> SampleVerdict:
    """확정 net 표본의 ddof=1 표준편차와 필요한 표본 수를 계산한다.

    n 이 1 이하이면 표본 표준편차가 정의되지 않는다. n 이 충분해도 평균이 0 이거나
    표준편차가 0 이면 요구 표본 수를 정직하게 산출할 수 없으므로, 작은 표본을
    조용히 통과시키지 않고 모두 insufficient 로 둔다.

    실측 n=3, sd=0.1593, mean=-0.9210에서는 기존 정밀도 공식의 required_n 이 1이 되어
    표본 세 건을 충분하다고 잘못 판정했다. 작은 n에서는 sd 추정도 신뢰할 수 없으므로
    요구 표본 수에 추정량 자체의 하한을 적용한다.
    """
    n = len(observations)
    if n == 0:
        return SampleVerdict(
            n=0,
            mean_net=None,
            sd_net=None,
            required_n=None,
            sufficient=False,
        )

    with localcontext(PARITY_DECIMAL_CONTEXT):
        mean_net = _sum_decimals(observation.actual_net for observation in observations) / Decimal(
            n
        )
    if n < 2:
        return SampleVerdict(
            n=n,
            mean_net=mean_net,
            sd_net=None,
            required_n=None,
            sufficient=False,
        )

    with localcontext(PARITY_DECIMAL_CONTEXT):
        squared_deviations = (
            (Decimal(str(observation.actual_net)) - Decimal(str(mean_net))) ** 2
            for observation in observations
        )
        variance = _sum_decimals(squared_deviations) / Decimal(n - 1)
        sd_net = variance.sqrt()
    if sd_net == Decimal("0") or mean_net == Decimal("0"):
        return SampleVerdict(
            n=n,
            mean_net=mean_net,
            sd_net=sd_net,
            required_n=None,
            sufficient=False,
        )

    with localcontext(PARITY_DECIMAL_CONTEXT):
        required_decimal = ((se_multiplier * sd_net) / abs(mean_net)) ** 2
    required_n = max(
        int(required_decimal.to_integral_value(rounding=ROUND_CEILING)),
        MIN_OBSERVATIONS_FOR_VARIANCE,
    )
    return SampleVerdict(
        n=n,
        mean_net=mean_net,
        sd_net=sd_net,
        required_n=required_n,
        sufficient=n >= required_n,
    )


def summarize_parity(
    observations: Sequence[ParityObservation],
    buckets: ParityBuckets,
    *,
    se_multiplier: Decimal = PARITY_SE_MULTIPLIER,
) -> ParitySummary:
    """매칭 청산 주문들을 비용 분해, coverage, 표본 충분성으로 요약한다.

    `actual_gross - expected_gross` 는 체결가가 엔진 가정과 달랐던 execution gap 이고,
    `actual_net - actual_gross` 는 거래소가 이미 뺀 비용이다. 두 값을 더한 항등식은
    계산 방식상 항상 맞으므로 여기서 검증하지 않는다. 대신 매칭 밖 청산을 buckets 로
    보존하고, 분해 불가 주문을 0 비용으로 가장하지 않는 것이 이 함수의 책임이다.
    """
    matched_count = len(observations)
    expected_gross = _sum_decimals(observation.expected_gross for observation in observations)
    actual_net = _sum_decimals(observation.actual_net for observation in observations)

    decomposable = [
        (
            observation.expected_gross,
            observation.actual_net,
            observation.actual_gross,
            observation.round_trip_notional,
        )
        for observation in observations
        if observation.actual_gross is not None and observation.round_trip_notional is not None
    ]
    undecomposed = [observation for observation in observations if observation.actual_gross is None]
    decomposable_count = len(decomposable)
    undecomposed_count = len(undecomposed)
    undecomposed_net = _sum_decimals(observation.actual_net for observation in undecomposed)

    decomposable_actual_gross: Decimal | None = None
    decomposable_expected_gross: Decimal | None = None
    decomposable_actual_net: Decimal | None = None
    execution_gap: Decimal | None = None
    cost: Decimal | None = None
    round_trip_notional: Decimal | None = None
    effective_cost_pct_per_leg: Decimal | None = None
    effective_cost_pct_round_trip: Decimal | None = None
    edge_pct_round_trip: Decimal | None = None
    cost_to_edge_ratio: Decimal | None = None

    if decomposable:
        with localcontext(PARITY_DECIMAL_CONTEXT):
            decomposable_expected_gross = _sum_decimals(row[0] for row in decomposable)
            decomposable_actual_net = _sum_decimals(row[1] for row in decomposable)
            decomposable_actual_gross = _sum_decimals(row[2] for row in decomposable)
            round_trip_notional = _sum_decimals(row[3] for row in decomposable)
            execution_gap = Decimal(str(decomposable_actual_gross)) - Decimal(
                str(decomposable_expected_gross)
            )
            cost = Decimal(str(decomposable_actual_net)) - Decimal(str(decomposable_actual_gross))
            if round_trip_notional != Decimal("0"):
                # 분모가 두 leg 합이라 이 값은 편도다.
                effective_cost_pct_per_leg = (-cost / round_trip_notional) * Decimal("100")
                effective_cost_pct_round_trip = Decimal(str(effective_cost_pct_per_leg)) * Decimal(
                    "2"
                )
                edge_pct_round_trip = (
                    (decomposable_actual_net / round_trip_notional) * Decimal("2") * Decimal("100")
                )
            if decomposable_actual_net != Decimal("0"):
                cost_to_edge_ratio = abs(cost) / abs(decomposable_actual_net)

    with localcontext(PARITY_DECIMAL_CONTEXT):
        covered_count = (
            matched_count
            + buckets.expected_only_count
            + buckets.actual_only_count
            + buckets.ledger_only_count
        )
        match_coverage_pct = (
            (Decimal(str(matched_count)) / Decimal(str(covered_count))) * Decimal("100")
            if covered_count != 0
            else None
        )
        decomposition_coverage_pct = (
            (Decimal(str(decomposable_count)) / Decimal(str(matched_count))) * Decimal("100")
            if matched_count != 0
            else None
        )

    return ParitySummary(
        matched_count=matched_count,
        expected_gross=expected_gross,
        actual_net=actual_net,
        decomposable_count=decomposable_count,
        decomposable_expected_gross=decomposable_expected_gross,
        decomposable_actual_net=decomposable_actual_net,
        actual_gross=decomposable_actual_gross,
        execution_gap=execution_gap,
        cost=cost,
        round_trip_notional=round_trip_notional,
        effective_cost_pct_per_leg=effective_cost_pct_per_leg,
        effective_cost_pct_round_trip=effective_cost_pct_round_trip,
        edge_pct_round_trip=edge_pct_round_trip,
        cost_to_edge_ratio=cost_to_edge_ratio,
        undecomposed_count=undecomposed_count,
        undecomposed_net=undecomposed_net,
        buckets=buckets,
        match_coverage_pct=match_coverage_pct,
        decomposition_coverage_pct=decomposition_coverage_pct,
        sample=_sample_verdict(observations, se_multiplier=se_multiplier),
    )
