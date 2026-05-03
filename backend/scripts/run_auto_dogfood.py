#!/usr/bin/env python3
"""Sprint 24b — Auto dogfood entry script (codex G.0 P1 #5 + P2 #3 반영).

Backend E2E 자동 dogfood 6 시나리오 실행 + 별도 summary HTML/JSON 생성.

dogfood_report._async_generate() 와 분리 (codex G.0 P1 #5):
- dogfood_report → PnL/order/KS HTML (운영 일일 리포트)
- 본 스크립트 → 시나리오 검증 결과 + DB row 검증 (자동 회귀 가드)

Sprint 25 변경:
- BL-114: pytest-json-report 도입 — `importlib.util.find_spec` 으로 plugin detect 후
  `--json-report --json-report-file=...` flag 명시. plugin 부재 시 graceful fallback
  (stdout 파싱). `_build_summary(rc, stdout, stderr, json_report=None)` 시그니처 유지
  (scenario6 호환).
- BL-115: HTML escape full coverage — stdout_tail / stderr_tail / table cells / header
  의 모든 dynamic 부분 `html.escape` 적용.

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
- docs/reports/auto-dogfood/<YYYY-MM-DD>.html — 사람 친화적 요약 (escaped)

codex G.0 P2 #3: subprocess.run 으로 `pytest --run-integration` 명시 호출.
"""

from __future__ import annotations

import html
import importlib.util
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Sprint 25 — script 실행 cwd 무관하게 동작 (repo root / backend/ 어디서든 OK).
_BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/
_REPO_ROOT = _BACKEND_DIR.parent
_REPORT_DIR = _REPO_ROOT / "docs" / "reports" / "auto-dogfood"
_TEST_PATH = "tests/integration/test_auto_dogfood.py"

_SCENARIOS: list[dict[str, Any]] = [
    {"id": 1, "name": "strategy_with_webhook_secret_atomic", "covers": "Sprint 13 broken bug 회귀"},
    {"id": 2, "name": "backtest_engine_smoke", "covers": "v2_adapter 실 호출 (Sprint 25 BL-112)"},
    {"id": 3, "name": "order_dispatch_snapshot", "covers": "OrderService.execute (Sprint 25 BL-113)"},
    {"id": 4, "name": "snapshot_drift_rejected", "covers": "Sprint 23 G.2 P1 #1 split-brain"},
    {"id": 5, "name": "multi_account_dispatch", "covers": "Sprint 24a BL-011/012 multi-account"},
    {"id": 6, "name": "summary_parse_smoke", "covers": "본 스크립트 자체 검증"},
]


def _has_pytest_json_report() -> bool:
    """codex G.0 iter 2 P1 #9 — plugin availability detect first.

    pytest CLI 가 unknown `--json-report` flag 받으면 CLI failure (Python exception
    아님). importlib.util.find_spec 으로 plugin 존재 확인 후만 flag 추가.
    """
    return importlib.util.find_spec("pytest_jsonreport") is not None


def _run_pytest() -> tuple[int, str, str, dict[str, Any] | None]:
    """codex G.0 P2 #3 — pytest --run-integration subprocess 명시 호출.

    Returns:
        (rc, stdout, stderr, json_report) — plugin 부재 시 json_report=None,
        graceful fallback. rc / stdout / stderr 는 항상 채워짐.
    """
    json_path: Path | None = None
    cmd = [
        "uv",
        "run",
        "pytest",
        "--run-integration",
        _TEST_PATH,
        "-v",
        "--tb=short",
    ]

    if _has_pytest_json_report():
        # tempfile — 다중 invocation 격리 + 사용 후 자동 정리 (with 안 끝)
        json_path = Path(tempfile.mkstemp(suffix=".json", prefix="pytest-report-")[1])
        cmd += ["--json-report", f"--json-report-file={json_path}"]

    # cmd 는 hard-coded list (사용자 입력 무관) — S603 false positive.
    # cwd 는 동적 — script 자체 위치 기반 (repo root / backend/ 어디서든 호출 가능).
    proc = subprocess.run(  # noqa: S603
        cmd, capture_output=True, text=True, cwd=_BACKEND_DIR, check=False
    )

    json_report: dict[str, Any] | None = None
    if json_path is not None and json_path.exists():
        try:
            json_report = json.loads(json_path.read_text())
        except (OSError, json.JSONDecodeError):
            json_report = None
        finally:
            json_path.unlink(missing_ok=True)

    return proc.returncode, proc.stdout, proc.stderr, json_report


def _parse_pytest_output(stdout: str) -> dict[str, int]:
    """pytest -v 출력 → 시나리오별 PASS/FAIL 카운트 (간단 텍스트 파싱).

    BL-114 fallback path — plugin 부재 시 사용.
    """
    passed = stdout.count("PASSED")
    failed = stdout.count("FAILED")
    errors = stdout.count("ERROR")
    return {
        "total": passed + failed + errors,
        "passed": passed,
        "failed": failed,
        "errors": errors,
    }


def _counts_from_json_report(json_report: dict[str, Any]) -> dict[str, int]:
    """pytest-json-report 결과 → counts schema (legacy stdout 파싱과 동일 schema)."""
    summary = json_report.get("summary", {})
    return {
        "total": summary.get("total", 0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "errors": summary.get("error", 0),
    }


def _scenario_status_from_json(json_report: dict[str, Any], scenario_id: int) -> str:
    """JSON 결과에서 특정 scenario 의 status 추출.

    `tests` array 의 nodeid 매칭. outcome: passed / failed / error / skipped.
    """
    marker = f"test_scenario{scenario_id}_"
    for test_entry in json_report.get("tests", []):
        nodeid = test_entry.get("nodeid", "")
        if marker in nodeid:
            outcome = test_entry.get("outcome", "")
            if outcome == "passed":
                return "PASS"
            if outcome in ("failed", "error"):
                return "FAIL"
            if outcome == "skipped":
                return "SKIP"
            return "UNKNOWN"
    return "MISSING"


def _scenario_status_from_stdout(stdout: str, scenario_id: int) -> str:
    """fallback path — stdout substring 파싱."""
    marker = f"test_scenario{scenario_id}_"
    if marker not in stdout:
        return "MISSING"
    idx = stdout.find(marker)
    chunk = stdout[idx : idx + 200]
    if "PASSED" in chunk:
        return "PASS"
    if "FAILED" in chunk or "ERROR" in chunk:
        return "FAIL"
    return "UNKNOWN"


def _build_summary(
    rc: int,
    stdout: str,
    stderr: str,
    json_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """시나리오 결과 + metadata 통합 summary.

    Sprint 25 BL-114 — `json_report` kwarg 추가. None 이면 legacy stdout 파싱 (scenario6
    + 기존 호출자 호환). dict 면 JSON-based 정확한 counts/status.
    """
    if json_report is not None:
        counts = _counts_from_json_report(json_report)
        scenarios_with_status = [
            {**sc, "status": _scenario_status_from_json(json_report, int(sc["id"]))}
            for sc in _SCENARIOS
        ]
    else:
        counts = _parse_pytest_output(stdout)
        scenarios_with_status = [
            {**sc, "status": _scenario_status_from_stdout(stdout, int(sc["id"]))}
            for sc in _SCENARIOS
        ]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "exit_code": rc,
        "scenarios": scenarios_with_status,
        "counts": counts,
        "stdout_tail": stdout[-2000:] if stdout else "",
        "stderr_tail": stderr[-500:] if stderr else "",
        "json_report_used": json_report is not None,
    }


def _write_outputs(summary: dict[str, Any]) -> tuple[Path, Path]:
    """JSON + HTML 두 산출물 생성. Sprint 25 BL-115 — html.escape full coverage."""
    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    json_path = _REPORT_DIR / f"{date_str}.json"
    html_path = _REPORT_DIR / f"{date_str}.html"

    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    # BL-115 — 모든 dynamic insertion site escape (stdout_tail / stderr_tail /
    # scenario name / covers / status / 헤더 date / counts).
    rows = "\n".join(
        f"<tr><td>{html.escape(str(sc['id']))}</td>"
        f"<td>{html.escape(sc['name'])}</td>"
        f"<td>{html.escape(sc['covers'])}</td>"
        f"<td class='{html.escape(sc['status'].lower())}'>{html.escape(sc['status'])}</td></tr>"
        for sc in summary["scenarios"]
    )

    safe_date = html.escape(date_str)
    safe_exit_code = html.escape(str(summary["exit_code"]))
    safe_passed = html.escape(str(summary["counts"]["passed"]))
    safe_failed = html.escape(str(summary["counts"]["failed"]))
    safe_stdout_tail = html.escape(summary["stdout_tail"])
    safe_stderr_tail = html.escape(summary["stderr_tail"])

    html_doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Auto Dogfood Report — {safe_date}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2em auto; padding: 0 1em; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 0.5em; text-align: left; }}
  th {{ background: #f5f5f5; }}
  .pass {{ color: #0a0; font-weight: bold; }}
  .fail {{ color: #c00; font-weight: bold; }}
  .unknown, .missing, .skip {{ color: #888; }}
  pre {{ background: #f8f8f8; padding: 1em; overflow-x: auto; font-size: 0.85em; }}
</style></head><body>
<h1>Auto Dogfood Report — {safe_date}</h1>
<p><strong>Exit code</strong>: {safe_exit_code} | <strong>Passed</strong>: {safe_passed} | <strong>Failed</strong>: {safe_failed}</p>
<table>
  <thead><tr><th>#</th><th>Scenario</th><th>Covers</th><th>Status</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<h2>pytest stdout (tail)</h2><pre>{safe_stdout_tail}</pre>
{"<h2>pytest stderr (tail)</h2><pre>" + safe_stderr_tail + "</pre>" if summary["stderr_tail"] else ""}
</body></html>
"""
    html_path.write_text(html_doc)
    return json_path, html_path


def main() -> int:
    print(f"Auto dogfood — running {_TEST_PATH} with --run-integration ...")
    if _has_pytest_json_report():
        print("  pytest-json-report plugin detected — using JSON parse path (BL-114)")
    else:
        print("  pytest-json-report plugin not installed — falling back to stdout parse")

    rc, stdout, stderr, json_report = _run_pytest()
    summary = _build_summary(rc, stdout, stderr, json_report=json_report)
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
