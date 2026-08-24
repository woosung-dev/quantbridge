"""live-smoke 워크플로우의 이름과 실제 실행 대상을 고정한다."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "live-smoke.yml"
PLAYWRIGHT_CONFIG_PATH = ROOT / "apps" / "web" / "playwright.config.ts"
HOOKS_DIFF_CLAIM_PATTERN = re.compile(
    r"\bhooks?(?:[\s/][\w-]+){0,3}\s*(?:diff|changes?|변경)\b",
    re.IGNORECASE,
)
PROJECT_ARGUMENT_PATTERN = re.compile(r"--project=([A-Za-z0-9_-]+)")
PLAYWRIGHT_PROJECT_NAME_PATTERN = re.compile(r'^\s*name:\s*"([^"]+)"\s*,?$', re.MULTILINE)


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _workflow_header(text: str) -> str:
    return text.split("\non:", maxsplit=1)[0]


def _has_hooks_diff_claim(text: str) -> bool:
    return HOOKS_DIFF_CLAIM_PATTERN.search(text) is not None


def _load_workflow() -> dict[object, object]:
    workflow = yaml.safe_load(_workflow_text())
    assert isinstance(workflow, dict)
    return workflow


def _pull_request_config(workflow: dict[object, object]) -> dict[object, object]:
    on_config = workflow.get("on", workflow.get(True))
    assert isinstance(on_config, dict)
    pull_request = on_config.get("pull_request")
    assert isinstance(pull_request, dict)
    return pull_request


def _workflow_run_steps(workflow: dict[object, object]) -> list[str]:
    jobs = workflow.get("jobs")
    assert isinstance(jobs, dict)
    live_smoke = jobs.get("live-smoke")
    assert isinstance(live_smoke, dict)
    steps = live_smoke.get("steps")
    assert isinstance(steps, list)

    return [
        step["run"] for step in steps if isinstance(step, dict) and isinstance(step.get("run"), str)
    ]


def _playwright_project_names() -> set[str]:
    return set(
        PLAYWRIGHT_PROJECT_NAME_PATTERN.findall(PLAYWRIGHT_CONFIG_PATH.read_text(encoding="utf-8"))
    )


def test_live_smoke_workflow_name_does_not_claim_an_absent_hooks_predicate() -> None:
    """이름·헤더는 없는 hooks diff 판별식을 약속하지 않는다."""
    assert not _has_hooks_diff_claim(_workflow_header(_workflow_text()))
    assert _has_hooks_diff_claim("name: Live Dev Smoke (frontend hooks diff)")
    assert _has_hooks_diff_claim("# frontend hooks/chart/widget 변경 PR은 PASS 의무")


def test_live_smoke_workflow_triggers_on_main_and_stage_only() -> None:
    """base가 feat/**이면 이 워크플로우가 발화하지 않는 함정을 고정한다."""
    branches = _pull_request_config(_load_workflow()).get("branches")
    assert branches == ["main", "stage/**"]


def test_live_smoke_workflow_runs_the_declared_playwright_project() -> None:
    """워크플로우가 실행하는 project는 Playwright 설정에 실제로 선언돼야 한다."""
    project_arguments = [
        project
        for run_step in _workflow_run_steps(_load_workflow())
        for project in PROJECT_ARGUMENT_PATTERN.findall(run_step)
    ]

    assert project_arguments
    assert set(project_arguments) <= _playwright_project_names()
