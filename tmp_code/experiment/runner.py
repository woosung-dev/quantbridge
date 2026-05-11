# Pine Script 호환성 실험 — 4 접근법 × 3 스크립트 = 12 케이스 실행
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from src.strategy.pine_v2.signal_extractor import SignalExtractor  # noqa: E402

# approach_a는 같은 디렉토리
sys.path.insert(0, str(Path(__file__).parent))
from approach_a import run as run_a  # noqa: E402

PINE_DIR = _REPO_ROOT / "tmp_code" / "pine_code"

SCRIPTS = {
    "DrFXGOD (hard)": PINE_DIR / "DrFXGOD_indicator_hard.pine",
    "LuxAlgo (medium)": PINE_DIR / "LuxAlgo_indicator_medium.pine",
    "SupplyDemand (medium-hard)": PINE_DIR / "supply_demand_zones.pine",
}


@dataclass
class CaseResult:
    approach: str
    script: str
    is_runnable: bool = False
    input_tokens: int = 0
    output_lines: int = 0
    slicing_ratio: float | None = None
    latency_ms: int = 0
    error: str | None = None


def run_c(source: str, script_name: str, mode: str) -> CaseResult:
    extractor = SignalExtractor()
    r = extractor.extract(source, mode=mode)  # type: ignore[arg-type]
    approach = f"C-{mode}"
    return CaseResult(
        approach=approach,
        script=script_name,
        is_runnable=r.is_runnable,
        input_tokens=len(r.sliced_code) // 4,  # 토큰 근사치 (chars/4)
        output_lines=len(r.sliced_code.splitlines()),
        slicing_ratio=round(1 - r.token_reduction_pct / 100, 2),
    )


def run_approach_a(source: str, script_name: str) -> CaseResult:
    r = run_a(source)
    return CaseResult(
        approach="A",
        script=script_name,
        is_runnable=r.is_runnable,
        input_tokens=r.input_tokens,
        output_lines=r.output_lines,
        latency_ms=r.latency_ms,
        error=r.error,
    )


def _md_table_row(r: CaseResult) -> str:
    ratio_str = f"{r.slicing_ratio:.2f}" if r.slicing_ratio is not None else "N/A"
    status = "✅" if r.is_runnable else ("⚠️" if r.error else "❌")
    error_note = f" ({r.error[:40]})" if r.error else ""
    return (
        f"| {r.approach:8s} | {r.script[:22]:22s} | {status}{error_note:42s} "
        f"| {r.input_tokens:6d} | {r.output_lines:4d} | {ratio_str:5s} | {r.latency_ms:6d} |"
    )


def main() -> None:
    results: list[CaseResult] = []

    for script_name, path in SCRIPTS.items():
        if not path.exists():
            print(f"[SKIP] {path} 없음")
            continue
        source = path.read_text()
        print(f"\n=== {script_name} ({len(source.splitlines())} lines) ===")

        for mode in ("text", "ast"):
            r = run_c(source, script_name, mode)
            results.append(r)
            status = "✅" if r.is_runnable else "❌"
            print(
                f"  C-{mode:4s} {status}  "
                f"tokens≈{r.input_tokens:5d}  lines={r.output_lines:3d}  "
                f"ratio={r.slicing_ratio}"
            )

        r_a = run_approach_a(source, script_name)
        results.append(r_a)
        status = "✅" if r_a.is_runnable else ("⚠️" if r_a.error else "❌")
        print(
            f"  A       {status}  "
            f"tokens={r_a.input_tokens:5d}  lines={r_a.output_lines:3d}  "
            f"latency={r_a.latency_ms}ms"
            + (f"  error={r_a.error}" if r_a.error else "")
        )

    # 마크다운 테이블 생성
    header = (
        "| Approach | Script                 | Runnable                                             "
        "| Tokens | Lines | Ratio | Lat(ms) |"
    )
    sep = (
        "|----------|------------------------|------------------------------------------------------"
        "|--------|-------|-------|---------|"
    )
    rows = [_md_table_row(r) for r in results]
    table = "\n".join([header, sep, *rows])

    print(f"\n\n{table}")

    # results.md 저장
    out = Path(__file__).parent / "results.md"
    with out.open("w") as f:
        f.write("# Pine Script 호환성 실험 결과\n\n")
        f.write("> C-text/C-ast: LLM 없이 AST 슬라이싱만 실행. ")
        f.write("A: 전체 코드 Claude API 직접 전달.\n\n")
        f.write(table)
        f.write("\n\n## 수동 평가 — Signal Accuracy\n\n")
        f.write("| Approach | Script | 원본 조건 | 생성 조건 | 일치율 |\n")
        f.write("|----------|--------|----------|---------|-------|\n")
        f.write("| C-text | DrFXGOD | ta.crossover(close, supertrend) and close >= sma9 | (결과 기입) | ?% |\n")
        f.write("| C-ast  | DrFXGOD | ta.crossover(close, supertrend) and close >= sma9 | (결과 기입) | ?% |\n")
        f.write("| A      | DrFXGOD | ta.crossover(close, supertrend) and close >= sma9 | (결과 기입) | ?% |\n")
        f.write("\n## 결론\n\n")
        f.write("- 추천 프로덕션 방식: (결과 기반 선택)\n")
        f.write("- C-text vs C-ast 정확도 차이: ?%\n")
        f.write("- LLM 없이 직접 실행 가능한 케이스 수: ?/9 (A 제외)\n")

    print(f"\n결과 저장: {out}")


if __name__ == "__main__":
    main()
