#!/usr/bin/env python
# tmp_code/pine_code Pine 스크립트 8종 × {1h,4h} × {2024,recent} 배치 coverage+백테스트 하니스
"""Pine 코퍼스 배치 백테스트 하니스 (docs/archive/qa/2026-07-12-pine-batch-1h4h).

각 (스크립트, 기간, TF) 셀에 대해:
1. `analyze_coverage` — is_runnable / degraded / unsupported (Trust Layer preflight)
2. runnable 이면 `run_backtest_v2(source, ohlcv, BacktestConfig(freq=tf))` 실행
3. 핵심 메트릭 + wall-clock 추출

산출:
- `results.json` — 전체 셀 원본 기록 (Decimal → 8자리 문자열, opus W-1 규약)
- `tables.md`    — report.md 에 삽입할 마크다운 표 (T1 coverage, T2~ 성과)

사용법::

    uv run python scripts/batch_pine_backtest.py
    uv run python scripts/batch_pine_backtest.py --scripts UtBot_strategy_medium.pine

주의:
- `BacktestConfig.freq` 를 TF 로 명시 (기본 "1D" 는 avg_holding_hours 24x 왜곡).
- Sharpe 는 bar-count 스케일 → TF 간 직접 비교 금지 (tables.md 각주 포함).
- CLI 하니스는 degraded 게이트(service.py submit 레벨) 를 거치지 않음 —
  degraded 컬럼으로 정직하게 표기.
"""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

DEFAULT_SCRIPTS_DIR = REPO_ROOT / "tmp_code" / "pine_code"
FIXTURE_DIR = BACKEND_ROOT / "data" / "fixtures" / "ohlcv"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "qa" / "2026-07-12-pine-batch-1h4h"

# (기간 라벨, TF) → fixture 파일명
DATASETS: dict[tuple[str, str], str] = {
    ("2024", "1h"): "BTCUSDT_1h.csv",
    ("2024", "4h"): "BTCUSDT_4h.csv",
    ("recent", "1h"): "BTCUSDT-RECENT_1h.csv",
    ("recent", "4h"): "BTCUSDT-RECENT_4h.csv",
}

# 셀당 실행 상한 (초). 초과 시 status=timeout.
CELL_TIMEOUT_SECONDS = 900

# report 표에 싣는 메트릭 (attr 이름, 표 헤더, 포맷)
METRIC_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("num_trades", "Trades", "int"),
    ("total_return", "Return", "pct"),
    ("annual_return_pct", "CAGR", "pct"),
    ("sharpe_ratio", "Sharpe", "num"),
    ("sortino_ratio", "Sortino", "num"),
    ("max_drawdown", "MDD", "pct"),
    ("win_rate", "WinRate", "pct"),
    ("profit_factor", "PF", "num"),
    ("avg_holding_hours", "AvgHold(h)", "num"),
    ("consecutive_losses_max", "MaxConsecLoss", "int"),
    ("total_fees", "Fees", "num"),
    ("total_slippage", "Slip", "num"),
)


class CellTimeout(Exception):
    """셀 실행 시간 상한 초과."""


def _alarm_handler(signum: int, frame: Any) -> None:
    raise CellTimeout


def _git_commit_short() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _load_ohlcv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["timestamp"])
    return df.set_index("timestamp")


def _decimal_str(value: Any) -> Any:
    """Decimal/NaN → JSON 안전 값. opus W-1: Decimal 은 8자리 zero-pad 문자열."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        if value.is_nan():
            return None
        return f"{value:.8f}"
    if isinstance(value, float):
        return value if value == value else None
    return value


def _fmt(value: Any, kind: str) -> str:
    """마크다운 표 셀 포맷."""
    if value is None:
        return "—"
    if isinstance(value, Decimal) and value.is_nan():
        return "—"
    if kind == "int":
        return str(int(value))
    if kind == "pct":
        return f"{float(value) * 100:.2f}%"
    return f"{float(value):.2f}"


def _run_cell(source: str, ohlcv: pd.DataFrame, timeframe: str, normalized: bool) -> dict[str, Any]:
    """단일 백테스트 셀 실행 → 상태/메트릭 dict.

    normalized=True 면 form-tier `percent_of_equity=100` 폴백을 주입한다. 엔진 사이징
    우선순위는 **Pine > form > fallback** (service.py `_resolve_sizing_canonical`,
    compat.parse_and_run_v2) 이므로 `strategy(default_qty_type=...)` 를 명시한 스크립트는
    Pine 선언이 우선 적용되고 form 폴백은 무효다. 미선언(지표/qty 없는 strategy)만 100%
    equity 가 적용된다 — 어느 tier 가 적용됐는지는 coverage["sizing"] 로 리포트에 노출.
    """
    from src.backtest.engine.types import BacktestConfig
    from src.backtest.engine.v2_adapter import run_backtest_v2

    if normalized:
        config = BacktestConfig(
            freq=timeframe,
            default_qty_type="strategy.percent_of_equity",
            default_qty_value=100.0,
        )
    else:
        config = BacktestConfig(freq=timeframe)
    started = time.monotonic()
    signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(CELL_TIMEOUT_SECONDS)
    try:
        outcome = run_backtest_v2(source, ohlcv, config=config)
    except CellTimeout:
        return {"status": "timeout", "elapsed_s": round(time.monotonic() - started, 1)}
    except Exception as exc:
        return {
            "status": "harness_error",
            "error": f"{type(exc).__name__}: {exc}",
            "elapsed_s": round(time.monotonic() - started, 1),
        }
    finally:
        signal.alarm(0)
    elapsed = round(time.monotonic() - started, 1)

    row: dict[str, Any] = {"status": outcome.status, "elapsed_s": elapsed}
    if outcome.status != "ok":
        row["error"] = str(outcome.error)
        return row
    metrics = outcome.result.metrics
    row["metrics"] = {
        attr: _decimal_str(getattr(metrics, attr, None)) for attr, _, _ in METRIC_COLUMNS
    }
    row["metrics_raw"] = {attr: getattr(metrics, attr, None) for attr, _, _ in METRIC_COLUMNS}
    row["first_trades"] = [
        {
            "direction": t.direction,
            "entry_bar_index": t.entry_bar_index,
            "entry_price": _decimal_str(t.entry_price),
            "exit_bar_index": t.exit_bar_index,
            "exit_price": _decimal_str(t.exit_price),
        }
        for t in outcome.result.trades[:3]
    ]
    return row


def _pine_sizing(source: str) -> dict[str, Any]:
    """Pine strategy() 선언의 default_qty 추출 — 정규화 시 어느 tier 가 적용됐는지 판정용.

    반환: {"pine_declared": {"type", "value"}} (선언 있음) / {"pine_declared": None} (미선언).
    엔진 우선순위 Pine > form 이므로 pine_declared 가 있으면 --normalized 의 form 폴백은 무효.
    """
    try:
        from src.strategy.pine_v2.compat import _extract_default_qty

        qty_type, qty_value = _extract_default_qty(source)
    except Exception as exc:
        return {"pine_declared": None, "note": f"extract_error: {exc}"}
    if qty_type is None:
        return {"pine_declared": None}
    return {"pine_declared": {"type": qty_type, "value": qty_value}}


def _coverage_row(source: str) -> dict[str, Any]:
    from src.strategy.pine_v2.ast_classifier import classify_script
    from src.strategy.pine_v2.coverage import analyze_coverage

    cov = analyze_coverage(source)
    try:
        track = str(classify_script(source).track)
    except Exception as exc:
        track = f"classify_error: {exc}"
    return {
        "runnable": cov.is_runnable,
        "degraded": sorted(set(cov.degraded_calls)),
        "unsupported": list(cov.all_unsupported),
        "track": track,
        "sizing": _pine_sizing(source),
    }


def _build_tables(cells: list[dict[str, Any]], coverage: dict[str, dict[str, Any]]) -> str:
    """tables.md 마크다운 생성."""
    lines: list[str] = []
    lines.append("## T1 — 검증 매트릭스 (analyze_coverage)")
    lines.append("")
    lines.append("| 스크립트 | Track | Runnable | Degraded | Unsupported |")
    lines.append("|---|---|---|---|---|")
    for name, cov in coverage.items():
        degraded = ", ".join(cov["degraded"]) or "—"
        unsupported = ", ".join(cov["unsupported"]) or "—"
        runnable = "✅" if cov["runnable"] else "❌"
        lines.append(f"| {name} | {cov['track']} | {runnable} | {degraded} | {unsupported} |")
    lines.append("")

    table_no = 2
    for (period, tf), _file in DATASETS.items():
        subset = [c for c in cells if c["period"] == period and c["timeframe"] == tf]
        if not subset:
            continue
        lines.append(f"## T{table_no} — {period} / {tf} 성과")
        lines.append("")
        headers = ["스크립트", "상태", "실행(s)"] + [h for _, h, _ in METRIC_COLUMNS]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "---|" * len(headers))
        for cell in subset:
            run = cell["run"]
            status = run.get("status", "skipped(unsupported)")
            metrics_raw = run.get("metrics_raw", {})
            values = [
                _fmt(metrics_raw.get(attr), kind) if metrics_raw else "—"
                for attr, _, kind in METRIC_COLUMNS
            ]
            row = [cell["script"], status, str(run.get("elapsed_s", "—")), *values]
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        table_no += 1

    lines.append(
        "> **각주**: Sharpe/Sortino 는 bar-count 스케일(연율화 아님) — TF 간 직접 비교 금지. "
    )
    lines.append("> CAGR(annual_return_pct) 은 timestamp 기반 — TF/기간 간 비교 가능. ")
    lines.append("> config: init_cash=10000, fees=0.1%, slippage=0.05%, fill_timing=bar_close. ")
    lines.append(
        "> degraded 스크립트는 CLI 하니스에서 실행되지만 웹 UI 는 명시 동의 없이 422 차단."
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch pine coverage + backtest harness.")
    parser.add_argument("--scripts-dir", type=Path, default=DEFAULT_SCRIPTS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--scripts",
        nargs="*",
        default=None,
        help="파일명 subset (기본: 디렉토리 내 전체 *.pine)",
    )
    parser.add_argument(
        "--normalized",
        action="store_true",
        help="form-tier percent_of_equity=100 폴백 주입 (엔진 우선순위 Pine > form — 선언 스크립트는 Pine 우선)",
    )
    args = parser.parse_args()

    script_paths = sorted(args.scripts_dir.glob("*.pine"))
    if args.scripts:
        wanted = set(args.scripts)
        script_paths = [p for p in script_paths if p.name in wanted]
    if not script_paths:
        sys.stderr.write(f"ERROR: no .pine scripts in {args.scripts_dir}\n")
        return 1

    datasets: dict[tuple[str, str], pd.DataFrame] = {}
    for key, filename in DATASETS.items():
        path = FIXTURE_DIR / filename
        if not path.exists():
            sys.stderr.write(
                f"ERROR: fixture missing: {path} — scripts/fetch_qa_ohlcv.py 먼저 실행\n"
            )
            return 1
        datasets[key] = _load_ohlcv(path)
        print(f"[data] {filename}: {len(datasets[key])} bars")

    coverage: dict[str, dict[str, Any]] = {}
    cells: list[dict[str, Any]] = []
    for path in script_paths:
        source = path.read_text()
        cov = _coverage_row(source)
        coverage[path.name] = cov
        print(f"[coverage] {path.name}: runnable={cov['runnable']} track={cov['track']}")
        for (period, tf), df in datasets.items():
            if not cov["runnable"]:
                run: dict[str, Any] = {"status": "skipped_unsupported"}
            else:
                print(f"  [run] {path.name} × {period}/{tf} ...", flush=True)
                run = _run_cell(source, df, tf, args.normalized)
                print(f"        → {run['status']} ({run.get('elapsed_s', '?')}s)")
            cells.append({"script": path.name, "period": period, "timeframe": tf, "run": run})

    args.output_dir.mkdir(parents=True, exist_ok=True)

    json_cells = []
    for cell in cells:
        run = {k: v for k, v in cell["run"].items() if k != "metrics_raw"}
        json_cells.append({**{k: v for k, v in cell.items() if k != "run"}, "run": run})
    results = {
        "generated_at": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit_short(),
        "config": {
            "init_cash": "10000",
            "fees": 0.001,
            "slippage": 0.0005,
            "freq": "per-TF",
            "cell_timeout_s": CELL_TIMEOUT_SECONDS,
            "normalized": args.normalized,
            "default_qty": (
                {"type": "strategy.percent_of_equity", "value": 100.0} if args.normalized else None
            ),
        },
        "coverage": coverage,
        "cells": json_cells,
    }
    results_path = args.output_dir / "results.json"
    results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    print(f"[write] {results_path}")

    tables_path = args.output_dir / "tables.md"
    tables_path.write_text(_build_tables(cells, coverage) + "\n")
    print(f"[write] {tables_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
