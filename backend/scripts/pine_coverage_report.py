"""Pine Coverage Go/No-Go 판정 스크립트.

사용법:
  uv run python scripts/pine_coverage_report.py [--cases docs/01_requirements/pine-coverage-assignment.yaml]

기본은 docs/01_requirements/pine-coverage-assignment.yaml 에서 케이스 목록을 읽는다.
파일이 없거나 Phase A가 아직 진행 중이면 `--cases` 생략 시 경고 후 0건 리포트.

exit code:
  0 — 모든 티어 목표 + ground zero 통과
  1 — 티어 목표 미달 (중간/헤비)
  2 — ground zero 실패 (표준 티어 불합격)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import pandas as pd

# backend/ 디렉토리를 sys.path에 추가 (스크립트 직접 실행 시 src 임포트 가능하도록)
_BACKEND_DIR = Path(__file__).parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from src.strategy.pine import parse_and_run  # noqa: E402

Tier = Literal["standard", "medium", "heavy"]


@dataclass
class CaseResult:
    case_id: str
    tier: Tier
    status: Literal["ok", "unsupported", "error"]
    feature: str | None = None


@dataclass
class CoverageReport:
    cases: list[CaseResult] = field(default_factory=list)

    def by_tier(self, tier: Tier) -> list[CaseResult]:
        return [c for c in self.cases if c.tier == tier]

    def tier_pass_rate(self, tier: Tier) -> float:
        tier_cases = self.by_tier(tier)
        if not tier_cases:
            return 1.0  # 케이스 0개는 제약 없음
        oks = sum(1 for c in tier_cases if c.status == "ok")
        return oks / len(tier_cases)

    @property
    def ground_zero_passed(self) -> bool:
        """표준 티어 100%가 ground zero 기준."""
        return self.tier_pass_rate("standard") == 1.0

    def unsupported_features_top(self, n: int = 10) -> list[tuple[str, int]]:
        from collections import Counter
        counter = Counter(
            c.feature for c in self.cases
            if c.status == "unsupported" and c.feature
        )
        return counter.most_common(n)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ground_zero_passed": self.ground_zero_passed,
            "tier_pass_rates": {
                "standard": self.tier_pass_rate("standard"),
                "medium": self.tier_pass_rate("medium"),
                "heavy": self.tier_pass_rate("heavy"),
            },
            "case_count": len(self.cases),
            "by_tier_counts": {
                "standard": len(self.by_tier("standard")),
                "medium": len(self.by_tier("medium")),
                "heavy": len(self.by_tier("heavy")),
            },
            "unsupported_top": [
                {"feature": f, "count": c}
                for f, c in self.unsupported_features_top()
            ],
            "cases": [
                {
                    "case_id": c.case_id,
                    "tier": c.tier,
                    "status": c.status,
                    "feature": c.feature,
                }
                for c in self.cases
            ],
        }


def evaluate_case(
    *,
    case_id: str,
    tier: Tier,
    source: str,
    ohlcv: pd.DataFrame,
) -> CaseResult:
    outcome = parse_and_run(source, ohlcv)
    feature = None
    if outcome.error is not None and hasattr(outcome.error, "feature"):
        feature = getattr(outcome.error, "feature", None)
    return CaseResult(
        case_id=case_id,
        tier=tier,
        status=outcome.status,
        feature=feature,
    )


def run_report(
    cases: list[dict[str, Any]],
    *,
    ohlcv_factory: Callable[[str], pd.DataFrame],
) -> CoverageReport:
    report = CoverageReport()
    for case in cases:
        result = evaluate_case(
            case_id=case["case_id"],
            tier=case["tier"],
            source=case["source"],
            ohlcv=ohlcv_factory(case["case_id"]),
        )
        report.cases.append(result)
    return report


def _default_ohlcv(_case_id: str) -> pd.DataFrame:
    import numpy as np
    close = pd.Series(np.linspace(10.0, 30.0, 30))
    return pd.DataFrame({
        "open": close - 0.1, "high": close + 0.5, "low": close - 0.5,
        "close": close, "volume": [100.0] * 30,
    })


def _load_cases_from_yaml(path: Path) -> list[dict[str, Any]]:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        print("PyYAML not installed; please add 'pyyaml' to dependencies or pass cases as JSON.", file=sys.stderr)
        return []
    if not path.exists():
        print(f"[warn] cases file not found: {path}", file=sys.stderr)
        return []
    raw: Any = yaml.safe_load(path.read_text())
    cases: list[dict[str, Any]] = raw.get("cases", []) if isinstance(raw, dict) else list(raw)
    return cases


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("docs/01_requirements/pine-coverage-assignment.yaml"),
    )
    parser.add_argument(
        "--medium-target",
        type=float,
        default=0.0,
        help="중간 티어 최소 통과율 (0.0~1.0). 기본값은 Phase A 결과로 덮어쓰기.",
    )
    args = parser.parse_args(argv)

    cases = _load_cases_from_yaml(args.cases)
    if not cases:
        print("[info] no cases to evaluate; exiting 0")
        return 0

    report = run_report(cases, ohlcv_factory=_default_ohlcv)
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))

    if not report.ground_zero_passed:
        print("[FAIL] ground zero (standard tier) not 100%", file=sys.stderr)
        return 2
    if report.tier_pass_rate("medium") < args.medium_target:
        print(
            f"[FAIL] medium tier {report.tier_pass_rate('medium'):.1%} < target {args.medium_target:.1%}",
            file=sys.stderr,
        )
        return 1
    print("[OK] all coverage targets met")
    return 0


if __name__ == "__main__":
    sys.exit(main())
