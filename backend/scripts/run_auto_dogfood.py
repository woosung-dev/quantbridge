#!/usr/bin/env python3
"""Sprint 24b — Auto dogfood entry script (codex G.0 P1 #5 + P2 #3 반영).

Backend E2E 자동 dogfood 6 시나리오 실행 + 별도 summary HTML/JSON 생성.

dogfood_report._async_generate() 와 분리 (codex G.0 P1 #5):
- dogfood_report → PnL/order/KS HTML (운영 일일 리포트)
- 본 스크립트 → 시나리오 검증 결과 + DB row 검증 (자동 회귀 가드)

사용법:
```bash
# 격리 stack 가동 후
make up-isolated

# Auto dogfood 실행 (env 명시)
TEST_DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5433/quantbridge \\
TEST_REDIS_LOCK_URL=redis://localhost:6380/3 \\
python backend/scripts/run_auto_dogfood.py
```

출력:
- stdout: 시나리오별 PASS/FAIL 요약
- docs/reports/auto-dogfood/<YYYY-MM-DD>.json — pytest 결과 + 시나리오 metadata
- docs/reports/auto-dogfood/<YYYY-MM-DD>.html — 사람 친화적 요약

codex G.0 P2 #3: subprocess.run 으로 `pytest --run-integration` 명시 호출.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

_REPORT_DIR = Path("docs/reports/auto-dogfood")
_TEST_PATH = "tests/integration/test_auto_dogfood.py"

_SCENARIOS = [
    {"id": 1, "name": "strategy_with_webhook_secret_atomic", "covers": "Sprint 13 broken bug 회귀"},
    {"id": 2, "name": "backtest_engine_smoke", "covers": "v2_adapter import + Pine v5 detection"},
    {"id": 3, "name": "order_dispatch_snapshot", "covers": "Sprint 22+23 BL-091/102"},
    {"id": 4, "name": "snapshot_drift_rejected", "covers": "Sprint 23 G.2 P1 #1 split-brain"},
    {"id": 5, "name": "multi_account_dispatch", "covers": "Sprint 24a BL-011/012 multi-account"},
    {"id": 6, "name": "summary_parse_smoke", "covers": "본 스크립트 자체 검증"},
]


def _run_pytest() -> tuple[int, str, str]:
    """codex G.0 P2 #3 — pytest --run-integration subprocess 명시 호출."""
    cmd = [
        "uv",
        "run",
        "pytest",
        "--run-integration",
        _TEST_PATH,
        "-v",
        "--tb=short",
    ]
    # cmd 는 hard-coded list (사용자 입력 무관) — S603 false positive.
    proc = subprocess.run(  # noqa: S603
        cmd, capture_output=True, text=True, cwd="backend", check=False
    )
    return proc.returncode, proc.stdout, proc.stderr


def _parse_pytest_output(stdout: str) -> dict:
    """pytest -v 출력 → 시나리오별 PASS/FAIL 카운트 (간단 텍스트 파싱)."""
    passed = stdout.count("PASSED")
    failed = stdout.count("FAILED")
    errors = stdout.count("ERROR")
    return {
        "total": passed + failed + errors,
        "passed": passed,
        "failed": failed,
        "errors": errors,
    }


def _build_summary(rc: int, stdout: str, stderr: str) -> dict:
    """시나리오 결과 + metadata 통합 summary."""
    counts = _parse_pytest_output(stdout)
    scenarios_with_status = []
    for sc in _SCENARIOS:
        # 단순화: pytest stdout 안에 "test_scenario{id}" 가 PASSED 면 PASS
        marker = f"test_scenario{sc['id']}_"
        if marker in stdout:
            # 다음 라인의 PASSED/FAILED 확인 (단순 substring)
            idx = stdout.find(marker)
            chunk = stdout[idx : idx + 200]
            if "PASSED" in chunk:
                status = "PASS"
            elif "FAILED" in chunk or "ERROR" in chunk:
                status = "FAIL"
            else:
                status = "UNKNOWN"
        else:
            status = "MISSING"
        scenarios_with_status.append({**sc, "status": status})

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "exit_code": rc,
        "scenarios": scenarios_with_status,
        "counts": counts,
        "stdout_tail": stdout[-2000:] if stdout else "",
        "stderr_tail": stderr[-500:] if stderr else "",
    }


def _write_outputs(summary: dict) -> tuple[Path, Path]:
    """JSON + HTML 두 산출물 생성."""
    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    json_path = _REPORT_DIR / f"{date_str}.json"
    html_path = _REPORT_DIR / f"{date_str}.html"

    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    rows = "\n".join(
        f"<tr><td>{sc['id']}</td><td>{sc['name']}</td>"
        f"<td>{sc['covers']}</td>"
        f"<td class='{sc['status'].lower()}'>{sc['status']}</td></tr>"
        for sc in summary["scenarios"]
    )
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Auto Dogfood Report — {date_str}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2em auto; padding: 0 1em; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 0.5em; text-align: left; }}
  th {{ background: #f5f5f5; }}
  .pass {{ color: #0a0; font-weight: bold; }}
  .fail {{ color: #c00; font-weight: bold; }}
  .unknown, .missing {{ color: #888; }}
  pre {{ background: #f8f8f8; padding: 1em; overflow-x: auto; font-size: 0.85em; }}
</style></head><body>
<h1>Auto Dogfood Report — {date_str}</h1>
<p><strong>Exit code</strong>: {summary["exit_code"]} | <strong>Passed</strong>: {summary["counts"]["passed"]} | <strong>Failed</strong>: {summary["counts"]["failed"]}</p>
<table>
  <thead><tr><th>#</th><th>Scenario</th><th>Covers</th><th>Status</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<h2>pytest stdout (tail)</h2><pre>{summary["stdout_tail"]}</pre>
{"<h2>pytest stderr (tail)</h2><pre>" + summary["stderr_tail"] + "</pre>" if summary["stderr_tail"] else ""}
</body></html>
"""
    html_path.write_text(html)
    return json_path, html_path


def main() -> int:
    print(f"Auto dogfood — running {_TEST_PATH} with --run-integration ...")
    rc, stdout, stderr = _run_pytest()
    summary = _build_summary(rc, stdout, stderr)
    json_path, html_path = _write_outputs(summary)

    print("\n=== Summary ===")
    for sc in summary["scenarios"]:
        print(f"  {sc['id']}. {sc['name']:<48} {sc['status']}")
    print(
        f"\nTotal: {summary['counts']['passed']}/{summary['counts']['total']} PASS "
        f"(failed={summary['counts']['failed']}, errors={summary['counts']['errors']})"
    )
    print(f"\nJSON: {json_path}")
    print(f"HTML: {html_path}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
