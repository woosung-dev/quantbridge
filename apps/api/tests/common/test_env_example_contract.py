"""Settings와 `.env.example`의 환경 변수 계약 census."""

from __future__ import annotations

import ast
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _BACKEND_ROOT / "src/core/config.py"
_ENV_EXAMPLE_PATH = _BACKEND_ROOT / ".env.example"

_FROZEN_MISSING_FROM_EXAMPLE = frozenset()

_ALLOWLIST_NON_SETTINGS = frozenset(
    {
        "BYBIT_DEMO_API_KEY_TEST",
        "BYBIT_DEMO_API_SECRET_TEST",
        "BYBIT_DEMO_KEY",
        "BYBIT_DEMO_SECRET",
        "BYBIT_SMOKE_API_KEY",
        "BYBIT_SMOKE_API_SECRET",
        # Settings 를 안 거치고 `src/health/router.py` 가 os.environ 에서 직접 읽는다.
        "HEALTHZ_CELERY_TIMEOUT_S",
        "PINE_ALERT_HEURISTIC_MODE",
        "PROMETHEUS_MULTIPROC_DIR",
        "QB_METRICS_ROLE",
        "TEST_DATABASE_URL",
        "TEST_REDIS_LOCK_URL",
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


def _env_example_keys(path: Path = _ENV_EXAMPLE_PATH) -> set[str]:
    return {
        line.split("=", 1)[0]
        for line in path.read_text().splitlines()
        if line and not line.lstrip().startswith("#") and "=" in line
    }


def test_env_contract_census_is_non_vacuous() -> None:
    assert len(_settings_field_env_keys()) >= 35
    assert len(_env_example_keys()) >= 45


def test_settings_keys_missing_from_env_example_match_frozen_census() -> None:
    actual = set(_settings_field_env_keys()) - _env_example_keys()

    assert actual == _FROZEN_MISSING_FROM_EXAMPLE


def test_env_example_keys_without_settings_match_allowlist() -> None:
    actual = _env_example_keys() - set(_settings_field_env_keys())

    assert actual == _ALLOWLIST_NON_SETTINGS


def test_allowlist_non_settings_keys_exist_in_env_example() -> None:
    assert _env_example_keys() >= _ALLOWLIST_NON_SETTINGS


def test_field_aliases_are_contract_keys_in_both_directions() -> None:
    settings_keys = set(_settings_field_env_keys())
    env_example_keys = _env_example_keys()
    aliases = {"TRUSTED_PROXIES", "WAITLIST_ADMIN_EMAILS"}
    attribute_names = {"TRUSTED_PROXIES_RAW", "WAITLIST_ADMIN_EMAILS_RAW"}

    assert aliases <= settings_keys
    assert aliases <= env_example_keys
    assert aliases.isdisjoint(settings_keys - env_example_keys)
    assert aliases.isdisjoint(env_example_keys - settings_keys)
    assert attribute_names.isdisjoint(settings_keys)
    assert attribute_names.isdisjoint(env_example_keys)


def test_env_example_parser_ignores_commented_assignments(tmp_path: Path) -> None:
    env_example = tmp_path / ".env.example"
    env_example.write_text("# COMMENT_ONLY=ignored\nACTIVE_KEY=accepted\n")

    assert _env_example_keys(env_example) == {"ACTIVE_KEY"}


# ─────────────────────────────────────────────────────────────────────────────
# raw `os.environ` 축 — Settings 를 지나지 않는 읽기
#
# ★위의 census 는 `Settings` 필드만 본다. 라우터·헬퍼 안의 raw `os.environ.get("X")` 는
#   **구조적으로 사각**이라 Golden Rule(「`.env.example` 에 없는 환경 변수를 코드에서 참조 금지」,
#   루트 AGENTS.md §3)이 기계로 지켜지지 않았다. 2026-08-15 `/docs` 인터넷 노출 실사고가 이 축이다.
# ─────────────────────────────────────────────────────────────────────────────

_SOURCE_ROOT = _BACKEND_ROOT / "src"

# OS·런타임이 주는 값이라 `.env.example` 이 선언할 대상이 아니다. 여기 넣을 때는 이유를 적어라.
_ALLOWLIST_OS_PROVIDED = frozenset(
    {
        "HOSTNAME",  # 컨테이너 런타임이 넣는다 — 앱 설정이 아니라 프로세스 신원(metrics_multiproc).
    }
)


def _raw_environ_reads(root: Path | None = None) -> dict[str, list[str]]:
    """`src/**/*.py` 의 `os.environ.get(...)` / `os.getenv(...)` 키 → 발생 위치."""
    reads: dict[str, list[str]] = {}
    for path in sorted((root or _SOURCE_ROOT).rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            func = node.func
            is_getenv = func.attr == "getenv" and isinstance(func.value, ast.Name)
            is_environ_get = (
                func.attr == "get"
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == "environ"
            )
            if not (is_getenv or is_environ_get):
                continue
            if not node.args or not isinstance(node.args[0], ast.Constant):
                continue
            key = node.args[0].value
            if not isinstance(key, str):
                continue
            reads.setdefault(key, []).append(f"{path.name}:{node.lineno}")
    return reads


def test_raw_environ_detector_sees_both_call_shapes(tmp_path: Path) -> None:
    """양성/음성 대조 — 두 호출 형태를 보고, 상수가 아닌 키는 세지 않는다."""
    (tmp_path / "probe.py").write_text(
        "import os\n"
        "os.environ.get('FROM_ENVIRON_GET')\n"
        "os.getenv('FROM_GETENV', 'default')\n"
        "os.environ.get(name)\n"
        "payload.get('NOT_AN_ENV_VAR')\n",
        encoding="utf-8",
    )

    assert set(_raw_environ_reads(tmp_path)) == {"FROM_ENVIRON_GET", "FROM_GETENV"}


def test_raw_environ_census_is_non_vacuous() -> None:
    assert len(_raw_environ_reads()) >= 3


def test_raw_environ_reads_are_declared_in_env_example() -> None:
    reads = _raw_environ_reads()
    undeclared = {
        key: sites
        for key, sites in reads.items()
        if key not in _env_example_keys() and key not in _ALLOWLIST_OS_PROVIDED
    }

    assert undeclared == {}, (
        "Golden Rule(루트 AGENTS.md §3) — `.env.example` 에 없는 환경 변수를 코드가 읽는다: "
        f"{sorted(undeclared.items())}"
    )
