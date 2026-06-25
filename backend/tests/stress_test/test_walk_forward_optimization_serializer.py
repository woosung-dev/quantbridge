# WFO 결과 직렬화 — selected_params + reoptimized_per_fold round-trip + 구버전 row 하위호환.
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.stress_test.engine import WalkForwardFold, WalkForwardResult
from src.stress_test.schemas import WalkForwardResultOut
from src.stress_test.serializers import wf_result_from_jsonb, wf_result_to_jsonb


def _fold(**kw: Any) -> WalkForwardFold:
    base: dict[str, Any] = {
        "fold_index": 0,
        "train_start": datetime(2024, 1, 1, tzinfo=UTC),
        "train_end": datetime(2024, 1, 2, tzinfo=UTC),
        "test_start": datetime(2024, 1, 3, tzinfo=UTC),
        "test_end": datetime(2024, 1, 4, tzinfo=UTC),
        "in_sample_return": Decimal("0.1"),
        "out_of_sample_return": Decimal("0.05"),
        "oos_sharpe": Decimal("1.0"),
        "num_trades_oos": 5,
    }
    base.update(kw)
    return WalkForwardFold(**base)


def test_wfo_result_roundtrip_preserves_selected_params_and_flag() -> None:
    result = WalkForwardResult(
        folds=[_fold(selected_params={"emaPeriod": "7"})],
        aggregate_oos_return=Decimal("0.05"),
        degradation_ratio=Decimal("2"),
        valid_positive_regime=True,
        total_possible_folds=3,
        was_truncated=True,
        reoptimized_per_fold=True,
    )
    jsonb = wf_result_to_jsonb(result)
    assert jsonb["reoptimized_per_fold"] is True
    assert jsonb["folds"][0]["selected_params"] == {"emaPeriod": "7"}

    restored = wf_result_from_jsonb(jsonb)
    assert restored["reoptimized_per_fold"] is True
    assert restored["folds"][0]["selected_params"] == {"emaPeriod": "7"}

    # Out 스키마 검증 통과 (FE 노출 경로).
    out = WalkForwardResultOut.model_validate(restored)
    assert out.reoptimized_per_fold is True
    assert out.folds[0].selected_params == {"emaPeriod": "7"}


def test_from_jsonb_backcompat_old_rows_default() -> None:
    """구버전 저장 row (selected_params/reoptimized 키 없음) → 기본값 (회귀 0)."""
    old = {
        "folds": [
            {
                "fold_index": 0,
                "train_start": "2024-01-01T00:00:00Z",
                "train_end": "2024-01-02T00:00:00Z",
                "test_start": "2024-01-03T00:00:00Z",
                "test_end": "2024-01-04T00:00:00Z",
                "in_sample_return": "0.1",
                "out_of_sample_return": "0.05",
                "oos_sharpe": "1.0",
                "num_trades_oos": 5,
            }
        ],
        "aggregate_oos_return": "0.05",
        "degradation_ratio": "2",
        "valid_positive_regime": True,
        "total_possible_folds": 1,
        "was_truncated": False,
    }
    restored = wf_result_from_jsonb(old)
    assert restored["reoptimized_per_fold"] is False
    assert restored["folds"][0]["selected_params"] is None
    out = WalkForwardResultOut.model_validate(restored)
    assert out.reoptimized_per_fold is False
    assert out.folds[0].selected_params is None
