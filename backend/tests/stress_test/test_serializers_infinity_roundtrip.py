"""Serializer round-trip for `Decimal("Infinity")` — WFA degradation_ratio edge case.

기존 worker happy-path 테스트는 단조 증가 OHLCV 로 `valid_positive_regime=True` 만
검증한다. OOS_avg=0 / IS_avg>0 경로는 `degradation_ratio = Decimal("Infinity")` 를
만들고, 이 값이 JSONB 직렬화 → Pydantic 스키마 검증까지 round-trip 되는지 보장한다.

계약:
    - `wf_result_to_jsonb` 가 `Decimal("Infinity")` → 문자열 `"Infinity"` 저장.
    - `wf_result_from_jsonb` 는 `degradation_ratio` 를 문자열로 그대로 패스.
    - `WalkForwardResultOut.model_validate(...)` 는 `degradation_ratio: str` 이므로
      `"Infinity"` literal 을 그대로 허용.
    - finite 값도 동일 경로에서 깨지지 않는지 회귀 방지.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from src.stress_test.engine import WalkForwardFold, WalkForwardResult
from src.stress_test.schemas import WalkForwardResultOut
from src.stress_test.serializers import wf_result_from_jsonb, wf_result_to_jsonb


def _make_fold(idx: int, is_ret: str, oos_ret: str) -> WalkForwardFold:
    t = datetime(2026, 1, 1, tzinfo=UTC)
    return WalkForwardFold(
        fold_index=idx,
        train_start=t,
        train_end=t,
        test_start=t,
        test_end=t,
        in_sample_return=Decimal(is_ret),
        out_of_sample_return=Decimal(oos_ret),
        oos_sharpe=None,
        num_trades_oos=0,
    )


def test_infinity_degradation_ratio_roundtrip() -> None:
    """OOS=0 / IS>0 → degradation_ratio=Infinity 가 JSONB + Pydantic 경로 살아남아야."""
    result = WalkForwardResult(
        folds=[_make_fold(0, "0.10", "0.0")],
        aggregate_oos_return=Decimal("0"),
        degradation_ratio=Decimal("Infinity"),
        valid_positive_regime=False,
        total_possible_folds=1,
        was_truncated=False,
    )

    # 1) to_jsonb: Decimal("Infinity") → "Infinity" 문자열
    jsonb = wf_result_to_jsonb(result)
    assert jsonb["degradation_ratio"] == "Infinity"
    assert jsonb["valid_positive_regime"] is False

    # 2) from_jsonb: 문자열 그대로 유지 (schema 가 str 을 기대)
    restored = wf_result_from_jsonb(jsonb)
    assert restored["degradation_ratio"] == "Infinity"
    assert restored["valid_positive_regime"] is False

    # 3) Pydantic model_validate: "Infinity" literal 허용
    out = WalkForwardResultOut.model_validate(restored)
    assert out.degradation_ratio == "Infinity"
    assert out.valid_positive_regime is False
    assert len(out.folds) == 1


def test_finite_degradation_ratio_roundtrip() -> None:
    """Sanity: finite Decimal 도 동일 경로에서 회귀 없이 round-trip."""
    result = WalkForwardResult(
        folds=[_make_fold(0, "0.10", "0.05")],
        aggregate_oos_return=Decimal("0.05"),
        degradation_ratio=Decimal("2.0"),
        valid_positive_regime=True,
        total_possible_folds=1,
        was_truncated=False,
    )

    jsonb = wf_result_to_jsonb(result)
    assert jsonb["degradation_ratio"] == "2.0"

    restored = wf_result_from_jsonb(jsonb)
    assert restored["degradation_ratio"] == "2.0"

    out = WalkForwardResultOut.model_validate(restored)
    assert out.degradation_ratio == "2.0"
    assert out.valid_positive_regime is True


def test_pydantic_schema_accepts_infinity_literal_directly() -> None:
    """Celery→DB→API 경로 단축 — WalkForwardResultOut 이 'Infinity' literal 허용."""
    payload = {
        "folds": [],
        "aggregate_oos_return": Decimal("0"),
        "degradation_ratio": "Infinity",
        "valid_positive_regime": False,
        "total_possible_folds": 0,
        "was_truncated": False,
    }
    out = WalkForwardResultOut.model_validate(payload)
    assert out.degradation_ratio == "Infinity"
