# 파괴적 DB 경로가 가드를 **실제로 지나는지** 잰다 — 배선 테스트 (BL-451).
"""[BL-451] 파괴적 마이그레이션 가드의 배선 검증.

★**왜 「가드를 직접 호출」로는 부족한가.** `AGENTS.md` §10-2 — 순수 함수 정확성은 배선이
아니다. 가드 함수를 직접 부르는 테스트는 **호출부에서 그 가드를 떼어내는 변이에 red 0** 을
낸다. 실제로 이 회차 착수 시점 실측이 그 상태였다:

    DATABASE_URL=<개발 DB> (TEST_DATABASE_URL 없음) 로 수집하면
      pytest tests/real_broker/     → rc=3   (가드 발동)
      pytest tests/trading/         → rc=0   ← 1088건 수집. 실행하면 개발 DB 에 drop_all
      pytest tests/test_migrations.py → rc=0 ← 수집 통과

  `tests/real_broker/conftest.py` 의 `pytest_configure` 가드는 **그 디렉터리를 수집할 때만**
  로드된다. 그래서 `_assert_disposable_database` 가 있는데도 `tests/trading/` 는 맨몸이었다.

★**실 DB 를 건드리지 않고 재는 방법.** 두 축이다.

1. 대상 DSN 의 포트를 **1**(붙지 않는 포트)로 둔다. 가드가 뚫려도 연결이 성립하지 않는다.
2. `--collect-only` 로 돈다. `pytest_configure` 는 수집 단계에서 **이미** 실행되므로 가드는
   재지고, 세션 픽스처(`_test_engine` 의 `drop_all`)는 실행되지 않는다.

★**음성 대조가 이 파일의 절반이다.** rc≠0 은 무증거다 — 가드가 발동해서 죽은 것과 그냥 DB 가
없어서 죽은 것을 구분하지 못하면 아무것도 증명하지 못한다. alembic 축(⑷/⑷′/⑷″)은 그래서
**종료 코드가 아니라 마커 문자열의 유무**로 판정한다.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests._db_guard import GUARD_EXIT_CODE as _GUARD_EXIT_CODE

_BACKEND_ROOT = Path(__file__).resolve().parent.parent

# 붙지 않는 엔드포인트. 가드가 통째로 사라져도 여기로는 아무것도 파괴되지 않는다.
_UNREACHABLE = "127.0.0.1:1"
_DEV_DSN = f"postgresql+asyncpg://u:p@{_UNREACHABLE}/quantbridge"
_TEST_DSN = f"postgresql+asyncpg://u:p@{_UNREACHABLE}/quantbridge_test"

# ★rc 만으로 판정하지 않는다. `pytest_configure` 안에서 **아무 예외나** 터져도 pytest 는
# INTERNALERROR 로 같은 rc=3 을 낸다 — 그러면 「가드가 막았다」와 「가드가 깨졌다」가 같은
# 신호가 된다. 그래서 아래 케이스들은 rc 와 **이 접두**를 함께 본다(`conftest.py:111`).
_PYTEST_GUARD_MARKER = "[db-guard]"

# `alembic/env.py` 의 파괴 가드가 stderr 에 남기는 토큰. ★이 리터럴이 두 곳에 있다 —
# 여기와 `apps/api/alembic/env.py`. 그 결합을 지키는 것이 이 파일의 ⑷ 계열이다.
_ALEMBIC_GUARD_MARKER = "QB-GUARD-DESTRUCTIVE-ALEMBIC"


def _env(**overrides: str | None) -> dict[str, str]:
    """현재 env 를 물려받되 DB 관련 두 키는 **명시한 것만** 남긴다.

    ★`.env.local` 의 dotenv 로딩은 `os.environ` 을 바꾸지 않는다(pydantic-settings 는 자기
    Settings 안에서만 읽는다). 가드가 보는 것은 process env 뿐이므로 여기서 정한 것이 전부다.
    """
    env = os.environ.copy()
    for key in ("DATABASE_URL", "TEST_DATABASE_URL"):
        env.pop(key, None)
    for key, value in overrides.items():
        if value is not None:
            env[key] = value
    return env


def _collect(target: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """`--collect-only` 로 pytest 를 띄운다 — 가드는 돌고 DB 는 안 건드린다."""
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            target,
            "--collect-only",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=_BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _alembic(*argv: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """alembic CLI 를 **실제 CLI 진입점으로** 띄운다.

    ★`command.downgrade(cfg, ...)` 를 파이썬에서 부르면 `config.cmd_opts` 가 없어 방향을
    감지할 수 없다. 그래서 CLI 경로를 재려면 **CLI 로 띄워야 한다** — 이 함수가 그 이유다.
    """
    return subprocess.run(
        [sys.executable, "-m", "alembic", *argv],
        cwd=_BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


# ---------------------------------------------------------------------------
# ⑴ 폴백 배선 — `TEST_DATABASE_URL` 없이 `DATABASE_URL` 만 있으면 세션이 끝나야 한다
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target",
    ["tests/test_migrations.py", "tests/trading/"],
    ids=["destructive-module", "ordinary-directory"],
)
def test_falling_back_to_database_url_ends_the_session(target: str) -> None:
    """red 면 고장난 것: `DATABASE_URL` 만 export 된 셸에서 스위트가 그대로 수집된다.

    ★`tests/trading/` 이 파라미터에 있는 이유 — 착수 시점에 그 경로는 rc=0 으로 1088건을
    수집했다. `real_broker/conftest.py` 의 가드는 그 디렉터리를 수집할 때만 로드되기
    때문이다. 파괴적인 것은 `test_migrations.py` 만이 아니다: `tests/conftest.py` 의
    `_test_engine` 세션 픽스처가 `SQLModel.metadata.drop_all` 을 돈다.
    """
    result = _collect(target, _env(DATABASE_URL=_DEV_DSN))

    blob = result.stdout + result.stderr
    assert result.returncode == _GUARD_EXIT_CODE, (
        f"{target} 수집이 rc={result.returncode} 로 끝났다 (기대 {_GUARD_EXIT_CODE}). "
        "폴백 가드가 이 경로에 배선되지 않았다.\n"
        f"--- stdout ---\n{result.stdout[-2000:]}\n--- stderr ---\n{result.stderr[-2000:]}"
    )
    assert _PYTEST_GUARD_MARKER in blob, (
        f"rc 는 {_GUARD_EXIT_CODE} 인데 {_PYTEST_GUARD_MARKER} 마커가 없다 — 가드가 막은 것이 "
        f"아니라 pytest 가 INTERNALERROR 로 죽었을 수 있다.\n--- 출력 ---\n{blob[-2000:]}"
    )
    assert "TEST_DATABASE_URL" in blob, (
        "중단은 했지만 메시지가 해소 방법(TEST_DATABASE_URL)을 안 알려준다"
    )


def test_an_explicit_test_database_url_is_not_refused() -> None:
    """⑴ 의 음성 대조 — 정상 배치를 막으면 그 가드는 못 쓴다.

    red 면 고장난 것: `set -a; . .env.local; set +a` 를 한 정상 셸에서도 스위트가 안 돈다.
    """
    result = _collect(
        "tests/test_migrations.py",
        _env(DATABASE_URL=_DEV_DSN, TEST_DATABASE_URL=_TEST_DSN),
    )

    assert result.returncode != _GUARD_EXIT_CODE, (
        "TEST_DATABASE_URL 이 명시된 정상 배치를 가드가 막았다 — 거짓 중단이다.\n"
        f"--- stdout ---\n{result.stdout[-2000:]}"
    )


# ---------------------------------------------------------------------------
# ⑵ 접미사 배선 — `TEST_DATABASE_URL` 이 있어도 버려도 되는 DB 가 아니면 거부
# ---------------------------------------------------------------------------


def test_a_test_database_url_that_is_not_disposable_ends_the_session() -> None:
    """red 면 고장난 것: `TEST_DATABASE_URL` 에 개발 DB 를 넣어도 스위트가 돈다.

    폴백을 막아도 이 축이 남는다 — 사람이 `TEST_DATABASE_URL=$DATABASE_URL` 을 export 하는
    경로가 실재한다(실사고의 서브에이전트가 정확히 env 를 손으로 조립했다).
    """
    result = _collect("tests/test_migrations.py", _env(TEST_DATABASE_URL=_DEV_DSN))

    blob = result.stdout + result.stderr
    assert result.returncode == _GUARD_EXIT_CODE and _PYTEST_GUARD_MARKER in blob, (
        f"rc={result.returncode} · 마커={_PYTEST_GUARD_MARKER in blob} "
        f"(기대 rc={_GUARD_EXIT_CODE} + 마커 있음). "
        "database='quantbridge' 는 버려도 되는 DB 가 아니다.\n"
        f"--- 출력 ---\n{blob[-2000:]}"
    )


def test_the_suffix_check_reads_the_database_name_not_the_whole_dsn() -> None:
    """red 면 고장난 것: substring 검사로 퇴화해 user/host 의 `_test` 에 속는다.

    `tests/tasks/test_prefork_smoke_integration.py:30-62` 의 codex G.2 P1 #2 교훈 —
    `make_url().database` 를 봐야 하고 `"_test" in dsn` 을 보면 안 된다. 아래 DSN 은
    **사용자 이름**에만 `_test` 가 있고 database 는 개발 DB 다.
    """
    sneaky = f"postgresql+asyncpg://user_test:p@{_UNREACHABLE}/quantbridge"
    result = _collect("tests/test_migrations.py", _env(TEST_DATABASE_URL=sneaky))

    blob = result.stdout + result.stderr
    assert result.returncode == _GUARD_EXIT_CODE and _PYTEST_GUARD_MARKER in blob, (
        f"rc={result.returncode} · 마커={_PYTEST_GUARD_MARKER in blob} — "
        "username 의 '_test' 에 속았다. 판정은 make_url().database 로 해야 한다.\n"
        f"--- 출력 ---\n{blob[-2000:]}"
    )


# ---------------------------------------------------------------------------
# ⑷ alembic CLI 배선 — downgrade 만 막고 upgrade 는 통과해야 한다
# ---------------------------------------------------------------------------


def test_alembic_downgrade_against_a_dev_database_is_refused() -> None:
    """red 면 고장난 것: `alembic downgrade base` 가 개발 DB 를 향해 그대로 돈다.

    ★`_assert_disposable_database` 는 pytest 경로만 막는다. `alembic/env.py:40` 이
    `settings.database_url` 을 주입하므로 수동 CLI 는 가드 없이 개발 DB 를 향했다.
    """
    result = _alembic("downgrade", "base", env=_env(DATABASE_URL=_DEV_DSN))

    assert _ALEMBIC_GUARD_MARKER in result.stdout + result.stderr, (
        "가드 마커가 없다 — downgrade 가 가드를 지나지 않았다. "
        f"rc={result.returncode}\n--- stderr ---\n{result.stderr[-2000:]}"
    )


def test_alembic_upgrade_against_the_same_dsn_is_not_refused() -> None:
    """⑷ 의 **판별력 검사** — 이 파일에서 가장 중요한 케이스다.

    같은 DSN, 같은 명령어 계열인데 방향만 다르다. 가드가 여기서도 발동하면 그것은
    「파괴를 막는 가드」가 아니라 「alembic 을 막는 가드」다 — `make migrate` ·
    docker entrypoint · `scripts/final-gates.sh` · `worktree-bootstrap.sh` 가 전부 죽는다.

    red 면 고장난 것: 가드가 방향을 안 보고 발동한다.
    """
    result = _alembic("upgrade", "head", env=_env(DATABASE_URL=_DEV_DSN))

    assert _ALEMBIC_GUARD_MARKER not in result.stdout + result.stderr, (
        "upgrade 가 파괴 가드에 막혔다 — make migrate · entrypoint · CI 가 함께 죽는다.\n"
        f"--- stderr ---\n{result.stderr[-2000:]}"
    )


def test_the_destructive_escape_hatch_is_wired() -> None:
    """red 면 고장난 것: 정당한 개발 DB 롤백을 되돌릴 방법이 없다.

    ★env 변수가 아니라 alembic `-x` 인자다 — `.env.example` 에 없는 환경 변수를 코드에서
    참조하지 않는다(AGENTS.md Golden Rule).
    """
    result = _alembic(
        "-x",
        "allow_destructive=1",
        "downgrade",
        "base",
        env=_env(DATABASE_URL=_DEV_DSN),
    )

    assert _ALEMBIC_GUARD_MARKER not in result.stdout + result.stderr, (
        "-x allow_destructive=1 를 줬는데도 가드가 막았다 — 탈출구가 배선되지 않았다.\n"
        f"--- stderr ---\n{result.stderr[-2000:]}"
    )


# ---------------------------------------------------------------------------
# ⑸ 2층 방어 — 판정이 뚫려도 겨냥 대상 자체가 개발 DB 가 아니어야 한다
# ---------------------------------------------------------------------------


def test_the_targeted_dsn_never_falls_back_to_database_url() -> None:
    """`effective_dsn()` 은 `DATABASE_URL` 을 **읽지 않는다**.

    red 면 고장난 것: `refusal_reason()` 이 어떤 이유로든 뚫렸을 때(변이·리팩터·미래의
    광범위한 `except`) 겨냥 대상이 곧바로 개발 DB 가 된다. 그 두 층이 서로의 구멍을 막는다는
    것이 `tests/_db_guard.py` 모듈 독스트링의 주장이고, **이 테스트가 그 주장의 유일한 근거다.**

    ★이 케이스는 배선이 아니라 **속성**을 잰다. 그래도 필요한 이유 — 코드 리뷰에서
    `effective_dsn` 에 `or os.environ.get("DATABASE_URL")` 을 되살리는 변이가 심어졌을 때
    이 파일의 다른 9건이 **전부 green** 이었다. `refusal_reason()` 이 env 를 독립적으로 먼저
    보므로 어떤 배선 테스트도 그 층을 지나지 않는다 ⇒ 도달 0 인 층은 무증거다
    (`apps/api/AGENTS.md` §10-2).
    """
    import os as _os
    from unittest import mock

    from tests import _db_guard

    with mock.patch.dict(_os.environ, {"DATABASE_URL": _DEV_DSN}, clear=False):
        _os.environ.pop("TEST_DATABASE_URL", None)
        resolved = _db_guard.effective_dsn()

    assert resolved == _db_guard.DEFAULT_TEST_DSN, (
        f"effective_dsn() 이 '{resolved}' 를 돌려줬다 — DATABASE_URL 로 폴백했다. "
        "판정이 뚫리는 순간 파괴 대상이 개발 DB 가 된다."
    )


@pytest.mark.parametrize("denial", ["0", "false", "no", "off"])
def test_a_negative_escape_hatch_value_does_not_allow_destruction(denial: str) -> None:
    """`-x allow_destructive=0` 은 허용이 아니라 **거부**로 읽혀야 한다.

    red 면 고장난 것: 초안이 `bool(...get("allow_destructive"))` 였고 `bool("0")` 은 참이라
    **`=0` 이 파괴를 허용**했다. 값 없는 `-x allow_destructive` 는 `""` 라 거꾸로 막혔다 —
    두 표기의 결과가 정반대였다. 코드 리뷰(spec 축)가 실측으로 잡았다.
    """
    result = _alembic(
        "-x",
        f"allow_destructive={denial}",
        "downgrade",
        "base",
        env=_env(DATABASE_URL=_DEV_DSN),
    )

    assert _ALEMBIC_GUARD_MARKER in result.stdout + result.stderr, (
        f"-x allow_destructive={denial} 가 파괴를 허용했다.\n"
        f"--- stderr ---\n{result.stderr[-2000:]}"
    )


def test_alembic_downgrade_against_a_disposable_database_is_not_refused() -> None:
    """⑵ 의 alembic 판 음성 대조 — `_test` DB 의 downgrade 는 정상 작업이다.

    red 면 고장난 것: `tests/test_migrations.py` 의 round-trip 이 CLI 로도 불가능해진다.
    """
    result = _alembic("downgrade", "base", env=_env(DATABASE_URL=_TEST_DSN))

    assert _ALEMBIC_GUARD_MARKER not in result.stdout + result.stderr, (
        "버려도 되는 DB 의 downgrade 를 막았다 — 거짓 중단이다.\n"
        f"--- stderr ---\n{result.stderr[-2000:]}"
    )
