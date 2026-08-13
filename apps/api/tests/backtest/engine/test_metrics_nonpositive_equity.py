# 자본이 0 이하로 간 실행에 위험조정수익을 매기지 않는지 검증하는 회귀 테스트
"""파산한 계좌에 아첨하는 샤프가 붙지 않아야 한다 (dogfood-restore).

## 왜 이 테스트가 있는가

기간 수익률은 `(cur - prev) / prev` 다. `prev` 가 음수면 부호가 뒤집혀
**더 잃을수록 수익률이 양수**가 된다. `_periodic_returns` 는 `prev == 0` 만
막고 있어서 음수 구간이 그대로 통과했다.

실측(2026-07-26 dogfood) — `s1_pbr` 을 BTC/USDT 1h 2025-07-01→2026-07-25 로
돌린 실행은 초기자본 10,000 에서 **-207,968 로 끝났고(총수익률 -2179.68%)**,
자본이 9,337 지점 중 8,874(95%)에서 음수였다. 그 결과 월간 수익률 13개 중
**11개가 양수**로 계산돼 **샤프가 +0.029** 로 나왔다.

이는 BL-398(#480)이 없애려던 거짓말과 같은 부류다. 그쪽은 수식(bar 기준
t-통계량) 때문이었고 이쪽은 분모 부호 때문이라 원인이 다를 뿐, 화면에 나오는
결과는 똑같이 "파산했는데 위험조정수익이 양수" 다.

음수 자본 자체는 별개 문제다 — 레버리지 1 에서는 마진 게이트가 no-op 이고
(`_can_afford_entry` 의 `is_leverage_active` 조기 반환) 청산도 없다. 그건
설계 귀결이라 여기서 고치지 않는다. 여기서 고치는 것은 **그 위에서 지표가
거짓말하지 않는 것** 뿐이다.
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd

from src.backtest.engine.metrics import (
    SHARPE_CONVENTION_MONTHLY,
    SHARPE_CONVENTION_NONPOSITIVE_EQUITY,
    sharpe_ratio,
    sortino_ratio,
)

# 2026-07-26 dogfood 실측 월말 계열 그대로. 지어낸 곡선으로 줄이면 성질이 죽는다 —
# 큰 음수 하나(-2.84)가 표본 5개에서는 평균을 지배하지만 13개에서는 희석돼
# **평균이 양수로 뒤집힌다**. 그 희석이 이 결함의 핵심이라 표본 수를 줄일 수 없다.
_BLOWN_MONTH_ENDS = [
    10_000.00,
    -18_362.57,
    -38_724.96,
    -79_777.18,
    -98_889.95,
    -111_975.90,
    -134_717.69,
    -149_100.46,
    -146_190.63,
    -155_346.66,
    -169_880.66,
    -187_179.46,
    -194_340.68,
    -207_967.53,
]


def _curve(values: list[float]) -> pd.Series:
    """달력 월말이 2개 이상 잡히도록 월초 간격으로 인덱싱한다."""
    idx = pd.date_range("2025-01-01", periods=len(values), freq="MS", tz="UTC")
    return pd.Series(values, index=idx, dtype=float)


def test_sharpe_refuses_when_equity_goes_negative() -> None:
    """실측 사례 축약 — 자본이 음수로 내려가면 산출을 거부한다."""
    blown = _curve(_BLOWN_MONTH_ENDS)

    value, convention = sharpe_ratio(blown)

    assert convention == SHARPE_CONVENTION_NONPOSITIVE_EQUITY
    assert value == Decimal("0")


def test_sharpe_would_have_reported_a_positive_number_without_the_guard() -> None:
    """가드의 판별력 증명 — 가드가 없었다면 양수가 나왔다.

    구 동작을 직접 재현한다(엔진 호출 아님). 이 단정이 실패하면 위 테스트가
    무엇을 막고 있는지에 대한 전제가 무너진 것이다.
    """
    samples = _BLOWN_MONTH_ENDS
    returns = [
        (samples[i + 1] - samples[i]) / samples[i] for i in range(len(samples) - 1)
    ]

    # 계좌는 13개월 내내 무너지는데 수익률 13개 중 11개가 양수로 계산된다.
    assert len(returns) == 13
    assert sum(1 for r in returns if r > 0) == 11

    mean = sum(returns) / len(returns)
    sd = (sum((r - mean) ** 2 for r in returns) / len(returns)) ** 0.5
    unguarded = (mean - 0.02 / 12) / sd

    # 저장된 실측값과 일치 — 이 테스트가 재현하는 것이 실제로 화면에 나갔던 숫자다.
    assert round(unguarded, 4) == 0.0290
    assert unguarded > 0, "가드가 막는 대상은 '양수로 보이는 파산' 이다"


def test_sortino_refuses_on_the_same_curve() -> None:
    """형제 지표도 같은 `_periodic_returns` 를 쓰므로 함께 막힌다."""
    blown = _curve(_BLOWN_MONTH_ENDS)

    assert sortino_ratio(blown) is None


def test_zero_equity_is_also_refused() -> None:
    """정확히 0 도 거부 — 이후 모든 수익률이 정의되지 않는다."""
    wiped = _curve([10_000, 5_000, 0.0, 0.0, 0.0, 0.0])

    _, convention = sharpe_ratio(wiped)

    assert convention == SHARPE_CONVENTION_NONPOSITIVE_EQUITY


def test_healthy_curve_is_untouched() -> None:
    """대조군 — 양수 자본 실행은 기존 컨벤션 그대로다(회귀 방지)."""
    healthy = _curve([10_000, 10_500, 10_200, 11_000, 10_800, 11_500])

    value, convention = sharpe_ratio(healthy)

    assert convention == SHARPE_CONVENTION_MONTHLY
    assert value != Decimal("0")
    assert sortino_ratio(healthy) is not None
