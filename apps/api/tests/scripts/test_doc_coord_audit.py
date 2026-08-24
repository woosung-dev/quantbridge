"""문서 좌표 감사기를 pytest 게이트로 배선한다.

실제 문서 좌표는 CONTROL 소관이므로 이 테스트는 리포지토리를 수정하지 않고 감사기 CLI만 실행한다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "doc-coord-audit.py"
REPO_ROOT = SCRIPT.parents[2]


def run_audit(*arguments: str) -> subprocess.CompletedProcess[str]:
    """실제 리포지토리에서 감사기 한 모드를 제한 시간 안에 실행한다."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_doc_coord_audit_check_passes_on_the_repository() -> None:
    result = run_audit("--check")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "✓ globals.css 줄 번호 인용 0건" in result.stdout


def test_doc_coord_audit_dead_paths_passes_on_the_repository() -> None:
    result = run_audit("--dead-paths")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "✓ 철거된 FE 규칙 문서 경로 0건" in result.stdout


def test_doc_coord_audit_selftest_proves_discriminating_power() -> None:
    result = run_audit("--selftest")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "✓ selftest" in result.stdout


def test_doc_coord_audit_selftest_exercises_all_cases() -> None:
    """고정 대상 CLI에는 임시 위반 문서를 넘길 수 없으므로 selftest 케이스 수를 직접 단언한다.

    `--only`는 감사 대상 두 경로만 받으므로 tmp_path 위반 문서를 검사기에 겨누지 못한다.
    실문서 변이는 CONTROL 소관이라 금지되어 있으며, 감사기 내부 selftest의 네 양성·음성
    케이스가 그 대체 판별력 증거다.
    """
    result = run_audit("--selftest")

    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("✓ selftest") >= 4
