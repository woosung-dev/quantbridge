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
    GridSweepMetricsResult,
    MonteCarloResult,
    WalkForwardFold,
    WalkForwardResult,
)
from src.stress_test.models import StressTestKind, StressTestStatus
from src.stress_test.schemas import StressTestHeadlineMetric

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
            k: [Decimal(x) for x in series] for k, series in data["equity_percentiles"].items()
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
        "selected_params": f.selected_params,
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
        "reoptimized_per_fold": r.reoptimized_per_fold,
        "degenerate_folds_skipped": r.degenerate_folds_skipped,
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
            "oos_sharpe": (None if f.get("oos_sharpe") is None else Decimal(f["oos_sharpe"])),
            "num_trades_oos": int(f["num_trades_oos"]),
            # 구버전 row 하위호환 — selected_params 키 없으면 None.
            "selected_params": f.get("selected_params"),
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
        # 구버전 row 하위호환 — 키 없으면 기본값.
        "reoptimized_per_fold": bool(data.get("reoptimized_per_fold", False)),
        "degenerate_folds_skipped": int(data.get("degenerate_folds_skipped", 0)),
    }


# ---------------------------------------------------------------------------
# 2D Grid Sweep (Cost Assumption + Param Stability 공유) ↔ JSONB (BL-392 통합)
# ---------------------------------------------------------------------------
# CA(Sprint 50) 와 PS(Sprint 51 BL-220) 는 동일 7-field cell shape 를 공유 → 단일
# serializer 쌍. JSONB shape 는 통합 전과 byte-identical (구버전 저장 row 하위호환).


def grid_metrics_result_to_jsonb(r: GridSweepMetricsResult) -> dict[str, Any]:
    """GridSweepMetricsResult → JSONB dict. Decimal → str, cells row-major."""
    return {
        "param1_name": r.param1_name,
        "param2_name": r.param2_name,
        "param1_values": [str(v) for v in r.param1_values],
        "param2_values": [str(v) for v in r.param2_values],
        "cells": [
            {
                "param1_value": str(c.param1_value),
                "param2_value": str(c.param2_value),
                "sharpe": None if c.sharpe is None else str(c.sharpe),
                "total_return": str(c.total_return),
                "max_drawdown": str(c.max_drawdown),
                "num_trades": c.num_trades,
                "is_degenerate": c.is_degenerate,
            }
            for c in r.cells
        ],
    }


def grid_metrics_result_from_jsonb(data: dict[str, Any]) -> dict[str, Any]:
    """JSONB dict → GridSweepMetricsResultOut.model_validate 입력 dict.

    str 그대로 유지 (Out schema = str, FE 정합).
    """
    return {
        "param1_name": data["param1_name"],
        "param2_name": data["param2_name"],
        "param1_values": list(data["param1_values"]),
        "param2_values": list(data["param2_values"]),
        "cells": [
            {
                "param1_value": c["param1_value"],
                "param2_value": c["param2_value"],
                "sharpe": c.get("sharpe"),
                "total_return": c["total_return"],
                "max_drawdown": c["max_drawdown"],
                "num_trades": int(c["num_trades"]),
                "is_degenerate": bool(c["is_degenerate"]),
            }
            for c in data["cells"]
        ],
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


# ---------------------------------------------------------------------------
# 목록 행의 대표 지표 (BL-414)
# ---------------------------------------------------------------------------


def _worst_cell_sharpe(result: dict[str, Any]) -> str | None:
    """2D grid sweep 의 non-degenerate cell 중 최저 sharpe **원문 문자열**.

    heatmap 이 이미 sharpe 를 주 지표로 칠하고 degenerate/None cell 을 "—" 로 비운다
    (`param-stability-heatmap.tsx`). 그 관례를 그대로 따르므로 새 지표를 만드는 것이 아니다.
    비교는 Decimal 로 하고 반환은 저장된 문자열 그대로다 — 재포맷하면 화면과 원문이 갈린다.
    """
    best: tuple[Decimal, str] | None = None
    for cell in result.get("cells") or []:
        raw = cell.get("sharpe")
        if cell.get("is_degenerate") or raw is None:
            continue
        parsed = Decimal(str(raw))
        if best is None or parsed < best[0]:
            best = (parsed, str(raw))
    return None if best is None else best[1]


def headline_metric_from(
    kind: StressTestKind,
    status: StressTestStatus,
    result: dict[str, Any] | None,
) -> StressTestHeadlineMetric | None:
    """목록 행 1개의 대표 지표 — 저장된 result JSONB 에서 읽는다.

    COMPLETED 가 아니거나 result 가 없으면 None 이다. FAILED 실행이 지표 칸에
    숫자를 갖지 않는 것이 이 함수의 계약이고, 화면은 그것을 빈칸으로 렌더한다.
    """
    if status is not StressTestStatus.COMPLETED or not result:
        return None
    if kind is StressTestKind.MONTE_CARLO:
        raw = result.get("max_drawdown_p95")
        return (
            None
            if raw is None
            else StressTestHeadlineMetric(key="max_drawdown_p95", value=str(raw))
        )
    if kind is StressTestKind.WALK_FORWARD:
        raw = result.get("degradation_ratio")
        return (
            None
            if raw is None
            else StressTestHeadlineMetric(key="degradation_ratio", value=str(raw))
        )
    # CA/PS 는 result shape 이 같다 (BL-392 통합).
    worst = _worst_cell_sharpe(result)
    return None if worst is None else StressTestHeadlineMetric(key="worst_cell_sharpe", value=worst)
