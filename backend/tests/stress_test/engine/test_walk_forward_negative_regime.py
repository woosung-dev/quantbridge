"""Walk-Forward valid_positive_regime — degradation_ratio 부호 반전 가드.

Sprint H2 Phase A iter-1 (FIX-2):
- `degradation_ratio = IS_avg / OOS_avg` 은 양쪽 모두 양수일 때만 의미 있음.
- 음수 OOS (losing strategy, 과적합의 정상 케이스) 에서 ratio 는 부호가 뒤집혀
  "2x 악화" 같은 잘못된 해석을 유발.
- 소비자는 `valid_positive_regime=False` 일 때 UI/API 에서 "N/A" 표시해야 함.

테스트 전략:
- 실제 음수 Pine 전략을 결정적으로 만들기 어렵기 때문에, 순수 계산 헬퍼인
  `_compute_aggregates` 를 직접 단위 테스트 (Decimal 합산 규약 포함).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from src.stress_test.engine.walk_forward import (
    WalkForwardFold,
    _compute_aggregates,
)


def _make_fold(idx: int, is_ret: str, oos_ret: str) -> WalkForwardFold:
    """테스트 전용 fold — 시간/sharpe/num_trades 는 aggregate 계산에 무관한 기본값."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    return WalkForwardFold(
        fold_index=idx,
        train_start=base,
        train_end=base,
        test_start=base,
        test_end=base,
        in_sample_return=Decimal(is_ret),
        out_of_sample_return=Decimal(oos_ret),
        oos_sharpe=None,
        num_trades_oos=0,
    )


def test_positive_regime_flagged_true() -> None:
    """IS/OOS 모두 양수 → valid_positive_regime=True."""
    folds = [
        _make_fold(0, "0.10", "0.05"),
        _make_fold(1, "0.15", "0.08"),
    ]
    oos_avg, degradation, valid = _compute_aggregates(folds)
    assert valid is True
    assert oos_avg == Decimal("0.065")
    # avg(IS)=0.125, avg(OOS)=0.065 → 0.125/0.065
    assert degradation > 0


def test_negative_oos_regime_flagged_false() -> None:
    """OOS 음수 → degradation_ratio 부호가 반전되므로 valid=False."""
    folds = [
        _make_fold(0, "0.10", "-0.05"),
        _make_fold(1, "0.20", "-0.03"),
    ]
    oos_avg, degradation, valid = _compute_aggregates(folds)
    assert valid is False  # ratio 해석 불가
    assert oos_avg < 0
    # degradation 자체는 부호가 뒤집혀 음수. 소비자는 valid=False 만 확인하면 됨.
    assert degradation < 0


def test_negative_is_regime_flagged_false() -> None:
    """IS 음수 → valid=False (strategy IS 도 지는 상황)."""
    folds = [
        _make_fold(0, "-0.02", "0.05"),
        _make_fold(1, "-0.03", "0.04"),
    ]
    _oos_avg, _degradation, valid = _compute_aggregates(folds)
    assert valid is False


def test_zero_is_regime_flagged_false() -> None:
    """IS_avg == 0 (경계) → valid=False. > 0 strict 이므로 0 포함 안 함."""
    folds = [
        _make_fold(0, "0.05", "0.10"),
        _make_fold(1, "-0.05", "0.10"),
    ]
    _oos_avg, _degradation, valid = _compute_aggregates(folds)
    assert valid is False  # IS_avg == 0


def test_compute_aggregates_empty_raises() -> None:
    """빈 folds 는 ValueError — 호출자 버그 가드."""
    with pytest.raises(ValueError, match="folds must not be empty"):
        _compute_aggregates([])


def test_zero_oos_nonzero_is_degradation_infinity() -> None:
    """OOS_avg == 0, IS_avg != 0 → degradation = Infinity."""
    folds = [
        _make_fold(0, "0.10", "0.05"),
        _make_fold(1, "0.10", "-0.05"),
    ]
    # OOS_avg = 0, IS_avg = 0.10 → degradation = Infinity.
    _oos_avg, degradation, valid = _compute_aggregates(folds)
    assert degradation == Decimal("Infinity")
    assert valid is False  # OOS_avg == 0 은 > 0 실패


def test_zero_is_zero_oos_degradation_one() -> None:
    """IS_avg == 0, OOS_avg == 0 → degradation = 1 (tautology)."""
    folds = [
        _make_fold(0, "0.05", "0.05"),
        _make_fold(1, "-0.05", "-0.05"),
    ]
    _oos_avg, degradation, valid = _compute_aggregates(folds)
    assert degradation == Decimal("1")
    assert valid is False
