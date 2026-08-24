"""Settings와 `.env.example`의 환경 변수 계약 census."""

from __future__ import annotations

import ast
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _BACKEND_ROOT / "src/core/config.py"
_ENV_EXAMPLE_PATH = _BACKEND_ROOT / ".env.example"

_FROZEN_MISSING_FROM_EXAMPLE = frozenset(
    {
        "DOGFOOD_REPORT_OUTPUT_DIR",
        "E2E_RATE_LIMIT_EXEMPT_EMAIL",
        "OPTIMIZER_STALE_THRESHOLD_SECONDS",
        "STRESS_TEST_STALE_THRESHOLD_SECONDS",
    }
)


def _settings_field_env_keys() -> list[str]:
    tree = ast.parse(_CONFIG_PATH.read_text())
    settings_class = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Settings"),
        None,
    )
    assert settings_class is not None, "config.py에 Settings 클래스가 없다"

    env_keys: list[str] = []
    for node in settings_class.body:
        if not isinstance(node, ast.AnnAssign) or not isinstance(node.target, ast.Name):
            continue

        alias = None
        if isinstance(node.value, ast.Call):
            alias = next(
                (
                    keyword.value.value
                    for keyword in node.value.keywords
                    if keyword.arg == "alias"
                    and isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                ),
                None,
            )
        env_keys.append((alias or node.target.id).upper())
    return env_keys


def _env_example_keys() -> set[str]:
    return {
        line.split("=", 1)[0]
        for line in _ENV_EXAMPLE_PATH.read_text().splitlines()
        if line and not line.lstrip().startswith("#") and "=" in line
    }


def test_env_contract_census_is_non_vacuous() -> None:
    assert len(_settings_field_env_keys()) >= 35
    assert len(_env_example_keys()) >= 45


def test_settings_keys_missing_from_env_example_match_frozen_census() -> None:
    actual = set(_settings_field_env_keys()) - _env_example_keys()

    assert actual == _FROZEN_MISSING_FROM_EXAMPLE
