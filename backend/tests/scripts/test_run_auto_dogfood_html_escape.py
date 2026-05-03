"""Sprint 25 BL-115 — `run_auto_dogfood.py` 의 HTML output XSS 회귀 가드.

codex G.0 iter 1 P2 #7 + P3 #1: html.escape 가 stdout_tail / stderr_tail / table cells /
헤더 모든 dynamic insertion site 적용. 본 test 가 `<script>` 주입 → escaped 검증.

신규 dynamic 부분 추가 시 회귀 case 추가 의무 (dev-log Lessons 명시).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _load_module() -> Any:
    """run_auto_dogfood.py 동적 import (sys.path 미등록 회피)."""
    script_path = Path(__file__).parents[2] / "scripts" / "run_auto_dogfood.py"
    spec = importlib.util.spec_from_file_location("run_auto_dogfood", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_html_escape_stdout_injection(tmp_path: Path, monkeypatch) -> None:
    """stdout_tail 에 `<script>alert(1)</script>` 주입 → HTML 안 escaped."""
    module = _load_module()

    # 격리된 _REPORT_DIR (현재 디렉토리 오염 회피)
    monkeypatch.setattr(module, "_REPORT_DIR", tmp_path)

    malicious_stdout = (
        "tests/integration/test_auto_dogfood.py::test_scenario1_strategy_with_webhook_secret_atomic PASSED\n"
        "<script>alert('xss')</script>\n"
    )
    summary = module._build_summary(rc=0, stdout=malicious_stdout, stderr="")
    _, html_path = module._write_outputs(summary)

    html_content = html_path.read_text()
    # raw script tag 가 HTML 안에 그대로 들어가면 안 됨
    assert "<script>alert" not in html_content, (
        "HTML escape 누락 — XSS 가능성. html.escape 적용 검증 필요."
    )
    # escaped 형태로는 존재
    assert "&lt;script&gt;" in html_content


def test_html_escape_stderr_injection(tmp_path: Path, monkeypatch) -> None:
    """stderr_tail 에도 escape 적용."""
    module = _load_module()
    monkeypatch.setattr(module, "_REPORT_DIR", tmp_path)

    malicious_stderr = "<img src=x onerror=alert(1)>"
    summary = module._build_summary(rc=1, stdout="", stderr=malicious_stderr)
    _, html_path = module._write_outputs(summary)

    html_content = html_path.read_text()
    assert "<img src=x onerror=alert(1)>" not in html_content
    assert "&lt;img src=x onerror=alert(1)&gt;" in html_content


def test_html_escape_no_breakage_for_safe_content(tmp_path: Path, monkeypatch) -> None:
    """일반적인 안전한 stdout 도 정상 렌더 (escape 가 정상 텍스트 깨뜨리지 않음)."""
    module = _load_module()
    monkeypatch.setattr(module, "_REPORT_DIR", tmp_path)

    safe_stdout = (
        "tests/integration/test_auto_dogfood.py::test_scenario1_strategy_with_webhook_secret_atomic PASSED\n"
        "===== 6 passed in 1.5s =====\n"
    )
    summary = module._build_summary(rc=0, stdout=safe_stdout, stderr="")
    _, html_path = module._write_outputs(summary)

    html_content = html_path.read_text()
    # 시나리오 이름 정상 포함
    assert "strategy_with_webhook_secret_atomic" in html_content
    # passed 결과 표시
    assert "PASSED" in html_content
