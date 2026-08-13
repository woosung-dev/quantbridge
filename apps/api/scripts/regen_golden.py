#!/usr/bin/env python
"""백테스트 엔진 골든 expected.json을 의도적으로 재생성하거나 비교한다."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.regen_trust_layer_baseline import metrics_snapshot  # noqa: E402
from src.backtest.engine import run_backtest  # noqa: E402
from tests.backtest.engine.test_golden_backtest import _discover_cases  # noqa: E402


def _decimal_text(value: Any) -> str:
    """골든은 엔진 Decimal의 정확 문자열을 보존한다."""
    return str(value)


def _case_expected(case_dir: Path) -> dict[str, Any]:
    """한 골든 케이스의 현재 엔진 출력을 expected.json 스키마로 만든다."""
    expected_path = case_dir / "expected.json"
    existing = json.loads(expected_path.read_text()) if expected_path.exists() else {}
    source = (case_dir / "strategy.pine").read_text()
    ohlcv = pd.read_csv(case_dir / "ohlcv.csv")
    outcome = run_backtest(source, ohlcv)

    generated = dict(existing)
    generated["status"] = outcome.status
    generated["source_version"] = outcome.parse.source_version
    if outcome.status != "ok" or outcome.result is None:
        return generated

    metrics, metrics_list_digests = metrics_snapshot(
        outcome.result.metrics,
        _decimal_text,
    )
    trades = outcome.result.trades
    backtest = dict(existing.get("backtest", {}))
    backtest["metrics"] = metrics
    backtest["metrics_list_digests"] = metrics_list_digests
    generated["backtest"] = backtest
    generated["entries_indices"] = [trade.entry_bar_index for trade in trades]
    generated["exits_indices"] = [
        trade.exit_bar_index for trade in trades if trade.exit_bar_index is not None
    ]
    return generated


def _differences(committed: Any, generated: Any, path: str = "$") -> list[str]:
    """사람이 읽을 수 있는 의미 단위 JSON diff를 만든다."""
    if isinstance(committed, dict) and isinstance(generated, dict):
        lines: list[str] = []
        for key in sorted(set(committed) | set(generated)):
            lines.extend(_differences(committed.get(key), generated.get(key), f"{path}.{key}"))
        return lines
    if committed == generated:
        return []
    return [
        f"{path:<54} committed={json.dumps(committed, ensure_ascii=False)} "
        f"generated={json.dumps(generated, ensure_ascii=False)}"
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate backtest golden expected.json files.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--confirm", action="store_true", help="재생성본을 실제 파일에 쓴다.")
    mode.add_argument("--check", action="store_true", help="재생성본과 커밋본을 비교만 한다.")
    case_names = {case.name: case for case in _discover_cases()}
    parser.add_argument("--case", choices=sorted(case_names), help="단일 골든 케이스만 처리한다.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        help=(
            "재생성본을 정본 대신 <out-dir>/<case>/expected.json 에 쓴다 (--confirm 전용). "
            "★씨앗(보존 필드)과 비교 기준은 언제나 정본이다 — 여기서 바뀌는 것은 쓰는 자리뿐이다."
        ),
    )
    args = parser.parse_args()

    if not args.confirm and not args.check:
        sys.stderr.write("ERROR: --confirm 또는 --check 플래그가 필요합니다.\n")
        return 1

    if args.out_dir is not None and not args.confirm:
        # 조용히 무시하면 "다른 곳에 썼겠지" 라고 믿은 채 정본을 덮어쓸 수 있다.
        sys.stderr.write("ERROR: --out-dir 은 --confirm 과 함께 써야 합니다.\n")
        return 1

    cases = [case_names[args.case]] if args.case else list(case_names.values())
    if not cases:
        sys.stderr.write("ERROR: strategy.pine 및 ohlcv.csv를 모두 가진 골든 케이스가 없습니다.\n")
        return 2

    differences: list[str] = []
    for case_dir in cases:
        generated = _case_expected(case_dir)
        expected_path = case_dir / "expected.json"
        committed = json.loads(expected_path.read_text()) if expected_path.exists() else {}
        case_differences = _differences(committed, generated)
        if args.check:
            if case_differences:
                differences.append(f"[{case_dir.name}]")
                differences.extend(case_differences)
            continue

        write_path = (
            args.out_dir / case_dir.name / "expected.json"
            if args.out_dir is not None
            else expected_path
        )
        write_path.parent.mkdir(parents=True, exist_ok=True)
        write_path.write_text(json.dumps(generated, indent=2, ensure_ascii=False) + "\n")
        print(f"regenerated: {case_dir.name} -> {write_path}")

    if differences:
        print("\n".join(differences))
        return 1
    if args.check:
        print("golden expected.json files match regenerated output")
    return 0


if __name__ == "__main__":
    sys.exit(main())
