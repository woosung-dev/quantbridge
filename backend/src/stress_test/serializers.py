"""Stress test JSONB 직렬화 helpers.

MonteCarloResult / WalkForwardResult ↔ JSONB dict.
Decimal → str (JSON safe). datetime → ISO 8601 Z.
`degradation_ratio=Decimal("Infinity")` 는 문자열 `"Infinity"` 로 저장.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.stress_test.engine import (
    MonteCarloResult,
    WalkForwardFold,
    WalkForwardResult,
)

# ---------------------------------------------------------------------------
# datetime helpers (backtest.serializers 와 동일 포맷)
# ---------------------------------------------------------------------------


def _utc_iso(dt: datetime) -> str:
    """tz-aware UTC → 'YYYY-MM-DDTHH:MM:SSZ'."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc_iso(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


# ---------------------------------------------------------------------------
# Monte Carlo ↔ JSONB
# ---------------------------------------------------------------------------


def mc_result_to_jsonb(r: MonteCarloResult) -> dict[str, Any]:
    """MonteCarloResult → JSONB dict. Decimal → str, percentiles dict[str, list[str]]."""
    return {
        "samples": r.samples,
        "ci_lower_95": str(r.ci_lower_95),
        "ci_upper_95": str(r.ci_upper_95),
        "median_final_equity": str(r.median_final_equity),
        "max_drawdown_mean": str(r.max_drawdown_mean),
        "max_drawdown_p95": str(r.max_drawdown_p95),
        "equity_percentiles": {
            k: [str(v) for v in series] for k, series in r.equity_percentiles.items()
        },
    }


def mc_result_from_jsonb(data: dict[str, Any]) -> dict[str, Any]:
    """JSONB dict → schema 호환 dict (Pydantic MonteCarloResultOut.model_validate 입력용).

    Decimal 로 복원한다.
    """
    return {
        "samples": int(data["samples"]),
        "ci_lower_95": Decimal(data["ci_lower_95"]),
        "ci_upper_95": Decimal(data["ci_upper_95"]),
        "median_final_equity": Decimal(data["median_final_equity"]),
        "max_drawdown_mean": Decimal(data["max_drawdown_mean"]),
        "max_drawdown_p95": Decimal(data["max_drawdown_p95"]),
        "equity_percentiles": {
            k: [Decimal(x) for x in series]
            for k, series in data["equity_percentiles"].items()
        },
    }


# ---------------------------------------------------------------------------
# Walk-Forward ↔ JSONB
# ---------------------------------------------------------------------------


def _fold_to_jsonb(f: WalkForwardFold) -> dict[str, Any]:
    return {
        "fold_index": f.fold_index,
        "train_start": _utc_iso(f.train_start),
        "train_end": _utc_iso(f.train_end),
        "test_start": _utc_iso(f.test_start),
        "test_end": _utc_iso(f.test_end),
        "in_sample_return": str(f.in_sample_return),
        "out_of_sample_return": str(f.out_of_sample_return),
        "oos_sharpe": None if f.oos_sharpe is None else str(f.oos_sharpe),
        "num_trades_oos": f.num_trades_oos,
    }


def wf_result_to_jsonb(r: WalkForwardResult) -> dict[str, Any]:
    """WalkForwardResult → JSONB dict.

    `degradation_ratio` 는 `Decimal("Infinity")` 일 수 있어 str(Decimal("Infinity")) =
    "Infinity" 를 그대로 저장한다. JSON spec 외 값이지만 Python Decimal round-trip
    가능 + FE 는 이 literal 을 "N/A"/"∞" 로 렌더링. 대안(null + is_infinite flag)
    대비 단순성 우선.
    """
    return {
        "folds": [_fold_to_jsonb(f) for f in r.folds],
        "aggregate_oos_return": str(r.aggregate_oos_return),
        "degradation_ratio": str(r.degradation_ratio),
        "valid_positive_regime": r.valid_positive_regime,
        "total_possible_folds": r.total_possible_folds,
        "was_truncated": r.was_truncated,
    }


def wf_result_from_jsonb(data: dict[str, Any]) -> dict[str, Any]:
    """JSONB dict → schema 호환 dict.

    `degradation_ratio` 는 문자열 그대로 유지 (schema Out.degradation_ratio: str).
    """
    folds_raw = data.get("folds", [])
    folds_out = [
        {
            "fold_index": int(f["fold_index"]),
            "train_start": _parse_utc_iso(f["train_start"]),
            "train_end": _parse_utc_iso(f["train_end"]),
            "test_start": _parse_utc_iso(f["test_start"]),
            "test_end": _parse_utc_iso(f["test_end"]),
            "in_sample_return": Decimal(f["in_sample_return"]),
            "out_of_sample_return": Decimal(f["out_of_sample_return"]),
            "oos_sharpe": (
                None if f.get("oos_sharpe") is None else Decimal(f["oos_sharpe"])
            ),
            "num_trades_oos": int(f["num_trades_oos"]),
        }
        for f in folds_raw
    ]
    return {
        "folds": folds_out,
        "aggregate_oos_return": Decimal(data["aggregate_oos_return"]),
        "degradation_ratio": data["degradation_ratio"],  # str
        "valid_positive_regime": bool(data["valid_positive_regime"]),
        "total_possible_folds": int(data["total_possible_folds"]),
        "was_truncated": bool(data["was_truncated"]),
    }


# ---------------------------------------------------------------------------
# equity_curve JSONB → list[Decimal]
# ---------------------------------------------------------------------------


def equity_curve_values(
    equity_curve: list[Any] | None,
) -> list[Decimal]:
    """backtests.equity_curve ([[ts_iso, val_str], ...]) → value 만 Decimal list.

    MC 입력용 (타임스탬프 불필요, 값만 필요).
    """
    if not equity_curve:
        return []
    return [Decimal(str(v)) for _ts, v in equity_curve]
