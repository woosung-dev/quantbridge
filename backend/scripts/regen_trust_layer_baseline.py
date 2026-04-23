#!/usr/bin/env python
"""Path β Trust Layer CI — P-3 Execution Golden 의 baseline_metrics.json 재생성.

**전제**: `corpus_ohlcv_frozen.parquet` 가 먼저 생성돼 있어야 함
(`scripts/generate_corpus_ohlcv_frozen.py --confirm` 으로 1회 실행).

생성 과정 (corpus 별):
1. `tests/fixtures/pine_corpus_v2/<id>.pine` 읽기
2. `run_backtest_v2(source, ohlcv_frozen)` 실행
3. `BacktestOutcome.metrics` → Decimal 정규화 (8자리 zero-pad, opus W-1 규약)
4. `var_series` / `trades` / `warnings` → sha256 digest
5. i3_drfx 는 Y1 Coverage 에서 reject 대상 → `{"note": "Skipped ..."}` 로 기록만

**ADR-013 §10.1 / §10.2 / SLO TL-E-6 준수**:
- `--confirm` 없이는 실패 (exit 1)
- 출력 JSON 은 plain JSON (msgpack 금지)
- Decimal 값은 `f"{val:.8f}"` 8자리 zero-pad
- `tool_versions` 자동 기록 (pynescript, python)

사용법::

    uv run python scripts/regen_trust_layer_baseline.py --confirm
    uv run python scripts/regen_trust_layer_baseline.py --confirm --corpus s1_pbr

Path β Stage 2a 의 범위는 스크립트 작성 + `--confirm` 게이트만. 실제 실 값 생성은
사용자가 `generate_corpus_ohlcv_frozen.py` 실행 후 본 스크립트 실행.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "pine_corpus_v2"
OHLCV_PATH = FIXTURE_DIR / "corpus_ohlcv_frozen.parquet"
BASELINE_PATH = FIXTURE_DIR / "baseline_metrics.json"
SCHEMA_PATH = FIXTURE_DIR / "baseline_metrics.schema.json"

# sys.path 확장 — uv run 으로 실행 시 src/tests import 가능하게
sys.path.insert(0, str(REPO_ROOT))

RUNNABLE_CORPUS = ("s1_pbr", "s2_utbot", "s3_rsid", "i1_utbot", "i2_luxalgo")
SKIPPED_CORPUS = ("i3_drfx",)
ALL_CORPUS = RUNNABLE_CORPUS + SKIPPED_CORPUS


def _git_commit_short() -> str:
    """pine_v2/ HEAD commit 의 단축 hash. git 부재 시 'unknown' 반환."""
    import shutil

    git_bin = shutil.which("git")
    if git_bin is None:
        return "unknown"
    try:
        result = subprocess.run(  # noqa: S603
            [git_bin, "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _pynescript_version() -> str:
    """pynescript 설치 버전."""
    try:
        import importlib.metadata

        return importlib.metadata.version("pynescript")
    except Exception:
        return "0.0.0"


def _python_minor() -> str:
    """e.g. '3.12' (schema pattern ^3\\.1[12]$ 과 일치)."""
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def _file_sha256(path: Path) -> str:
    import hashlib

    hasher = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_ohlcv() -> pd.DataFrame:
    """고정 parquet → DataFrame (run_backtest_v2 계약).

    parquet 컬럼: timestamp(UTC), open, high, low, close, volume.
    run_backtest_v2 는 open/high/low/close/volume (float) + datetime index 를 기대.
    """
    df = pd.read_parquet(OHLCV_PATH)
    # timestamp 를 index 로 승격 (엔진 expect)
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df


def _is_nan_like(value: Any) -> bool:
    """Decimal NaN or float NaN 체크. None 은 False."""
    if value is None:
        return False
    if isinstance(value, Decimal):
        return value.is_nan()
    try:
        import math

        return isinstance(value, float) and math.isnan(value)
    except Exception:
        return False


def _normalize_metric(value: Any, normalize_decimal_fn: Any) -> Any:
    """Metric 단일 값을 Decimal string (8자리) 또는 None 으로 직렬화."""
    if value is None or _is_nan_like(value):
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value  # num_trades / long_count / short_count 는 정수
    return normalize_decimal_fn(value)


def _trade_to_dict(trade: Any) -> dict[str, Any]:
    """RawTrade → digest 입력용 dict (Decimal 은 str 로)."""
    return {
        "trade_index": trade.trade_index,
        "direction": trade.direction,
        "status": trade.status,
        "entry_bar_index": trade.entry_bar_index,
        "exit_bar_index": trade.exit_bar_index,
        "entry_price": str(trade.entry_price),
        "exit_price": str(trade.exit_price) if trade.exit_price is not None else None,
        "size": str(trade.size),
        "pnl": str(trade.pnl),
        "return_pct": str(trade.return_pct),
        "fees": str(trade.fees),
    }


def _extract_var_series_and_warnings(v2: Any) -> tuple[dict[str, Any], list[str]]:
    """V2RunResult → (var_series, warnings).

    Track S/M → v2.historical (RunResult). Track A → v2.virtual (VirtualRunResult).
    VirtualRunResult 도 var_series/warnings 을 노출할 가능성이 있으며 없으면 빈 값.
    """
    var_series: dict[str, Any] = {}
    warnings: list[str] = []
    if v2.historical is not None:
        var_series = dict(v2.historical.var_series or {})
        state = v2.historical.strategy_state
        if state is not None:
            warnings = list(getattr(state, "warnings", []) or [])
    elif v2.virtual is not None:
        # VirtualRunResult 는 필드 이름이 조금 다를 수 있음 — 안전하게 getattr
        var_series = dict(getattr(v2.virtual, "var_series", {}) or {})
        state = getattr(v2.virtual, "strategy_state", None)
        if state is not None:
            warnings = list(getattr(state, "warnings", []) or [])
        else:
            warnings = list(getattr(v2.virtual, "warnings", []) or [])
    return var_series, warnings


def _runnable_corpus_record(corpus_id: str, ohlcv_df: pd.DataFrame) -> dict[str, Any]:
    """단일 corpus 를 실 실행해 metrics + digests 반환 (Path β P-3).

    구조:
    1. run_backtest_v2 → metrics + trades (+ status 체크)
    2. parse_and_run_v2 별도 호출 → var_series + warnings
    3. Decimal 직렬화 (8자리 zero-pad, opus W-1)
    4. trades/var_series/warnings → sha256 digest

    실패 시 `{"error": ..., "status": ...}` 반환 (schema 의 oneOf 에서
    Skipped 와 다른 형태지만 Stage 2b 에서 사용자 확인 후 unfail 할 케이스).
    """
    from src.backtest.engine.v2_adapter import run_backtest_v2
    from src.strategy.pine_v2.compat import parse_and_run_v2
    from tests.strategy.pine_v2._tolerance import digest_sequence, normalize_decimal

    source = (FIXTURE_DIR / f"{corpus_id}.pine").read_text()

    # 1. run_backtest_v2 → metrics + trades
    outcome = run_backtest_v2(source, ohlcv_df)
    if outcome.status != "ok" or outcome.result is None:
        return {
            "note": f"run_backtest_v2 status={outcome.status}",
            "error": str(outcome.error) if outcome.error else "unknown",
        }

    m = outcome.result.metrics
    trades = outcome.result.trades

    metrics_dict = {
        "total_return": _normalize_metric(m.total_return, normalize_decimal),
        "sharpe_ratio": _normalize_metric(m.sharpe_ratio, normalize_decimal),
        "max_drawdown": _normalize_metric(m.max_drawdown, normalize_decimal),
        "win_rate": _normalize_metric(m.win_rate, normalize_decimal),
        "num_trades": m.num_trades,
        "profit_factor": _normalize_metric(m.profit_factor, normalize_decimal),
        "sortino_ratio": _normalize_metric(m.sortino_ratio, normalize_decimal),
        "calmar_ratio": _normalize_metric(m.calmar_ratio, normalize_decimal),
        "avg_win": _normalize_metric(m.avg_win, normalize_decimal),
        "avg_loss": _normalize_metric(m.avg_loss, normalize_decimal),
        "long_count": m.long_count if m.long_count is not None else 0,
        "short_count": m.short_count if m.short_count is not None else 0,
    }

    trades_list = [_trade_to_dict(t) for t in trades]

    # 2. parse_and_run_v2 → var_series + warnings (중복 실행이지만 ADR §4.3 정합)
    try:
        v2 = parse_and_run_v2(source, ohlcv_df, strict=False)
        var_series, warnings = _extract_var_series_and_warnings(v2)
    except Exception as exc:
        var_series, warnings = {}, [f"var_series 추출 실패: {exc}"]

    return {
        "metrics": metrics_dict,
        "var_series_digest": digest_sequence(var_series),
        "trades_digest": digest_sequence(trades_list),
        "warnings_digest": digest_sequence(warnings),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate baseline_metrics.json for Path β P-3.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="필수. 의도된 baseline 갱신임을 명시 (SLO TL-E-6, ADR-013 §10.1).",
    )
    parser.add_argument(
        "--corpus",
        choices=list(ALL_CORPUS),
        help="단일 corpus 만 갱신 (기본: 전체). 부분 갱신 시 기존 baseline 병합.",
    )
    args = parser.parse_args()

    if not args.confirm:
        sys.stderr.write(
            "ERROR: --confirm 플래그가 필요합니다.\n"
            "baseline_metrics.json 은 Path β P-3 의 기준 스냅샷입니다. "
            "무심코 덮어쓰면 silent regression 을 놓치게 됩니다.\n"
            "의도된 갱신이면: uv run python scripts/regen_trust_layer_baseline.py --confirm\n"
        )
        return 1

    if not OHLCV_PATH.exists():
        sys.stderr.write(
            f"ERROR: {OHLCV_PATH} 가 존재하지 않습니다.\n"
            "먼저 `scripts/generate_corpus_ohlcv_frozen.py --confirm` 를 실행하세요.\n"
        )
        return 2

    targets = [args.corpus] if args.corpus else list(ALL_CORPUS)
    print(f"[1/4] Targets: {targets}")

    # 기존 baseline 있으면 병합 (부분 갱신 지원)
    existing: dict[str, Any] = {}
    if BASELINE_PATH.exists():
        existing = json.loads(BASELINE_PATH.read_text())

    print("[2/4] Loading OHLCV frozen parquet...")
    ohlcv_df = _load_ohlcv()
    print(f"      → {len(ohlcv_df)} bars")

    corpora: dict[str, Any] = dict(existing.get("corpora", {}))
    for corpus_id in targets:
        if corpus_id in SKIPPED_CORPUS:
            corpora[corpus_id] = {
                "note": "Skipped — is_runnable=false per Y1 Coverage Analyzer",
                "unsupported": [
                    "ta.supertrend",
                    "tostring",
                    "request.security",
                ],
            }
            print(f"      {corpus_id}: skipped (Y1 Coverage reject)")
        else:
            print(f"      {corpus_id}: running backtest...")
            new_record = _runnable_corpus_record(corpus_id, ohlcv_df)
            # opus Gate-2 M-4: corpus 별 updated_at 분리. git diff 가짜 변경 방지.
            new_record["updated_at"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            corpora[corpus_id] = new_record
            rec = corpora[corpus_id]
            if "error" in rec:
                print(f"        ⚠️  error: {rec['error']}")
            elif "metrics" in rec:
                m = rec["metrics"]
                print(
                    f"        ✅ trades={m['num_trades']} "
                    f"total_return={m['total_return']} "
                    f"sharpe={m['sharpe_ratio']}"
                )

    # opus Gate-2 M-4: 부분 regen (--corpus 모드) 에서 envelope generated_at 보존
    # → `--corpus` 모드는 "해당 corpus 만 갱신" 의 의미이므로 envelope 는 기존 값 유지.
    # 전체 regen (args.corpus is None) 일 때만 generated_at 새로 기록.
    is_full_regen = args.corpus is None
    if is_full_regen or not existing:
        envelope_generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        envelope_pine_v2_commit = _git_commit_short()
    else:
        # 부분 regen: 기존 envelope 값 보존 (단 없으면 신규 생성)
        envelope_generated_at = existing.get(
            "generated_at",
            datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        envelope_pine_v2_commit = existing.get("pine_v2_commit", _git_commit_short())

    print("[3/4] Building metadata envelope...")
    baseline = {
        "schema_version": 1,
        "ohlcv_sha256": _file_sha256(OHLCV_PATH),
        "pine_v2_commit": envelope_pine_v2_commit,
        "tool_versions": {
            "pynescript": _pynescript_version(),
            "python": _python_minor(),
        },
        "generated_at": envelope_generated_at,
        "corpora": corpora,
    }

    print(f"[4/4] Writing {BASELINE_PATH}")
    BASELINE_PATH.write_text(json.dumps(baseline, indent=2, sort_keys=False) + "\n")

    print()
    print("Baseline regen 완료. git diff 로 변경 범위 확인 후 PR 에 포함하세요.")
    print("변경 크기가 5% 이상이면 PR 설명에 근거 명시 의무 (requirements §5.2).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
