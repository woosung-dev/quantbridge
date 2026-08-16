# CI 워크플로 env 가 앱 Settings 의 인프라 기본값을 따라오는지 감사한다.
"""CI env 드리프트 감사 — 2026-08-01 실측 결함의 재발 방지.

★**왜 필요한가.** `Settings` 의 인프라 URL 기본값은 **docker-compose 서비스명**을 가리킨다
(`redis://redis:6379/*`, `@db:5432/*`). GitHub Actions 러너에서는 서비스가 `localhost` 에
붙으므로, 워크플로가 그 필드를 **명시적으로 주입하지 않으면** 앱이 기본값으로 떨어져
해석 불가 호스트에 연결을 시도한다.

실제로 2026-08-01 CI 에서 그렇게 **5건**이 실패했다 — `CELERY_BROKER_URL` /
`CELERY_RESULT_BACKEND` / `REDIS_LOCK_URL` 이 워크플로 env 에 없어서
"Retry limit exceeded while trying to reconnect to the Celery result store" 로 죽었다.
`REDIS_URL` 만 주입돼 있었는데, celery 는 **별도 설정**을 읽는다.

★**로컬에서는 구조적으로 안 보인다** — `.env.local` 이 그 셋을 모두 `localhost` 로 채우므로
로컬 CI 재현은 통과한다. 그래서 사람이 눈으로 대조하는 대신 이 테스트가 대조한다.
"""

from __future__ import annotations

import pathlib
import re

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci.yml"

# 기본값이 compose 서비스명을 가리키는 호스트 토큰. 러너에서 해석되지 않는다.
_COMPOSE_HOSTS = ("://redis:", "@db:", "://db:")


def _settings_infra_fields() -> dict[str, str]:
    """`Settings` 에서 기본값이 compose 호스트를 가리키는 필드 → 환경변수명."""
    from src.core.config import Settings

    out: dict[str, str] = {}
    for name, field in Settings.model_fields.items():
        default = field.default
        if not isinstance(default, str):
            continue
        if any(tok in default for tok in _COMPOSE_HOSTS):
            out[name] = name.upper()
    return out


def _env_keys_after(text: str, marker: int) -> set[str]:
    """`marker` 위치 뒤에 오는 첫 `env:` 블록의 키 집합."""
    env_start = text.index("env:", marker)
    tail = text[env_start + len("env:") :]
    keys: set[str] = set()
    for line in tail.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^\s{8,}([A-Z][A-Z0-9_]*):", line)
        if m:
            keys.add(m.group(1))
            continue
        # 들여쓰기가 빠지면 env 블록이 끝난 것이다.
        if line.strip() and not line.startswith(" " * 9):
            break
    return keys


def _strip_comment_lines(text: str) -> str:
    """YAML 주석 줄을 **같은 길이의 공백**으로 바꾼다.

    ★길이를 보존하는 이유: 이 모듈의 다른 함수들이 `text.find` 로 얻은 오프셋을 그대로
    `_env_keys_after` 에 넘긴다. 줄을 지워 버리면 오프셋이 밀려 엉뚱한 블록을 읽는다.
    ★줄 **전체**가 주석인 경우만 지운다 — 값 안의 `#`(예: 색상 코드)까지 건드리면 안 된다.
    """
    out: list[str] = []
    for line in text.split("\n"):
        out.append(" " * len(line) if line.lstrip().startswith("#") else line)
    return "\n".join(out)


def _backend_pytest_env_blocks(workflow: pathlib.Path | None = None) -> list[set[str]]:
    """워크플로 안 **모든** pytest 실행 스텝의 `env:` 블록 키 집합.

    YAML 파서를 새로 들이지 않고 텍스트로 읽는다 — 이 감사가 보려는 것은
    "그 키가 거기 적혀 있는가" 하나뿐이다.

    ★**2026-08-06 수리.** 원래는 `text.index("uv run pytest")` 로 **첫 매치 하나**만 봤다.
    backend 잡을 샤드 matrix 로 쪼개면서 pytest 스텝이 늘어날 수 있게 됐고, 그러면 두 번째
    이후 스텝의 env 누락이 **감사되지 않은 채 통과**한다. 이 레포는 열거식·첫매치식 배선이
    조용히 새는 것을 반복해서 밟았다(playwright `testMatch` 고아 spec). 그래서 전수로 바꾼다.

    ★★**2026-08-16 수리 — 주석을 코드로 셌다.** 마커를 원문 전체에서 찾으니 `# … uv run pytest
    … ` 라고 **설명하는 주석**까지 실행 스텝으로 등록됐고, 그 뒤의 남의 `env:` 블록을 pytest
    스텝의 것으로 읽어 두 단언이 함께 red 가 됐다. 실제로 ADR-035 회차가 `backend_static` 에
    OpenAPI drift 스텝을 넣으며 「이 스텝은 pytest 가 아니다」라고 적은 그 문장이 원인이었다 —
    **면제를 주장하는 산문이 면제를 깨뜨렸다.** 감사가 텍스트 기반인 이상 재발하므로,
    스캔 전에 주석 줄을 지운다(길이를 보존해 뒤따르는 `env:` 탐색 위치가 어긋나지 않게 한다).
    """
    text = (workflow or _WORKFLOW).read_text()
    text = _strip_comment_lines(text)
    blocks: list[set[str]] = []
    pos = 0
    while (marker := text.find("uv run pytest", pos)) != -1:
        blocks.append(_env_keys_after(text, marker))
        pos = marker + len("uv run pytest")
    return blocks


@pytest.mark.skipif(not _WORKFLOW.exists(), reason="워크플로 파일이 없는 체크아웃")
def test_ci_injects_every_compose_default_setting() -> None:
    """compose 호스트를 기본값으로 갖는 Settings 필드는 **모든** pytest 스텝 env 에 있어야 한다."""
    required = _settings_infra_fields()
    assert required, "감사 대상이 0개다 — 탐지 로직이 죽었는지 확인해라"

    blocks = _backend_pytest_env_blocks()
    assert blocks, (
        "워크플로에서 `uv run pytest` 스텝을 하나도 못 찾았다 — 배선이 바뀌었는지 확인해라. "
        "이 단언이 없으면 마커가 사라진 순간 감사가 **항상 통과**한다."
    )

    failures = [
        (idx, sorted(env for env in required.values() if env not in injected))
        for idx, injected in enumerate(blocks)
        if any(env not in injected for env in required.values())
    ]

    assert not failures, (
        "CI 워크플로 pytest 스텝 env 에 다음이 빠졌다(스텝 번호 → 누락): "
        f"{failures}\n"
        "이 필드들은 기본값이 docker-compose 서비스명이라, 주입하지 않으면 러너에서 "
        "해석 불가 호스트로 연결을 시도한다(2026-08-01 실측: celery 계열 5건 실패). "
        f"확인 대상 필드 → 환경변수: {required}"
    )


_TRUST_LAYER_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "trust-layer-nightly.yml"


@pytest.mark.parametrize(
    "workflow",
    [_WORKFLOW, _TRUST_LAYER_WORKFLOW],
    ids=lambda p: p.name,
)
def test_every_pytest_step_declares_a_test_database_url(workflow: pathlib.Path) -> None:
    """[BL-451] pytest 스텝 env 에 `TEST_DATABASE_URL` 이 있어야 한다.

    red 면 고장난 것: `tests/_db_guard.py` 가 `DATABASE_URL` 폴백을 거부하므로 그 잡이
    rc=3 으로 **세션 자체를 끝낸다**. 조용한 실패가 아니라 즉시 붉어지지만, 그때는 이미
    푸시된 뒤다 — 이 테스트가 로컬에서 먼저 잡는다.

    ★가드와 워크플로가 **같은 커밋에서** 움직여야 하는 관계다. 착수 시점 실측으로
    `ci.yml` 과 `trust-layer-nightly.yml` 은 `DATABASE_URL` 만 주고 있었다.
    ★`nightly-real-broker.yml` 은 여기서 안 본다 — 잡 레벨 env 라 스텝 스캔에 안 걸리고,
    `test_nightly_workflow_contract.py::test_database_urls_point_at_a_test_database` 가
    이미 두 키를 함께 잰다.
    """
    if not workflow.exists():
        pytest.skip("워크플로 파일이 없는 체크아웃")

    blocks = _backend_pytest_env_blocks(workflow)
    assert blocks, (
        f"{workflow.name} 에서 `uv run pytest` 스텝을 하나도 못 찾았다 — 배선이 바뀌었는지 "
        "확인해라. 이 단언이 없으면 마커가 사라진 순간 감사가 **항상 통과**한다."
    )

    missing = [idx for idx, injected in enumerate(blocks) if "TEST_DATABASE_URL" not in injected]
    assert not missing, (
        f"{workflow.name} 의 pytest 스텝 {missing} 에 TEST_DATABASE_URL 이 없다. "
        "tests/_db_guard.py 가 DATABASE_URL 폴백을 거부하므로 그 잡은 rc=3 으로 끝난다."
    )


@pytest.mark.skipif(not _WORKFLOW.exists(), reason="워크플로 파일이 없는 체크아웃")
def test_audit_detects_compose_hosts_at_all() -> None:
    """★음성 대조 — 탐지 로직 자체가 살아 있는지 고정한다.

    `_settings_infra_fields` 가 조용히 빈 dict 를 돌려주면 위 테스트는 **항상 통과**한다.
    실제로 이 레포는 "가드가 판별력을 증명하지 못한 채 초록" 인 사례를 반복해서 밟았다.
    """
    fields = _settings_infra_fields()
    assert "celery_result_backend" in fields
    assert fields["celery_result_backend"] == "CELERY_RESULT_BACKEND"


def test_comment_lines_are_not_counted_as_pytest_steps(tmp_path: pathlib.Path) -> None:
    """★회귀 고정 (2026-08-16) — **주석이 실행 스텝으로 세어지면 안 된다.**

    ADR-035 회차가 `backend_static` 에 OpenAPI drift 스텝을 넣으며 「이 스텝은 `uv run
    pytest` 가 아니다」라고 주석에 적었고, 그 문자열이 이 감사의 `text.find` 에 걸려
    **유령 pytest 스텝**이 생겼다. 뒤따르는 env 블록(그 스텝의 것)에는 compose 기본값
    3종도 `TEST_DATABASE_URL` 도 없으므로 위 두 단언이 함께 red 가 됐다.

    ★아래 픽스처는 그 모양 그대로다 — 주석 1개 + 진짜 pytest 스텝 1개.
    수리 전이라면 blocks 가 2개(첫째가 엉뚱한 env)이고, 수리 후에는 1개여야 한다.
    """
    fixture = tmp_path / "ci.yml"
    fixture.write_text(
        "jobs:\n"
        "  backend_static:\n"
        "    steps:\n"
        "      # 이 스텝은 uv run pytest 가 아니므로 감사 대상이 아니다\n"
        "      - name: OpenAPI drift check\n"
        "        run: uv run python scripts/export_openapi.py --check\n"
        "        env:\n"
        "          DATABASE_URL: postgresql://x\n"
        "  backend:\n"
        "    steps:\n"
        "      - name: pytest\n"
        "        run: uv run pytest -q\n"
        "        env:\n"
        "          TEST_DATABASE_URL: postgresql://y\n"
        "          CELERY_BROKER_URL: redis://z\n"
    )

    blocks = _backend_pytest_env_blocks(fixture)

    assert len(blocks) == 1, (
        f"주석이 pytest 스텝으로 세어졌다 (blocks={blocks}). "
        "감사가 텍스트 기반이므로 스캔 전에 주석 줄을 지워야 한다."
    )
    assert "TEST_DATABASE_URL" in blocks[0]


def test_strip_comment_lines_preserves_offsets() -> None:
    """★위 수리가 오프셋을 밀지 않는지 고정한다.

    주석 줄을 **삭제**하면 뒤따르는 `env:` 의 위치가 앞으로 당겨져 다른 블록을 읽는다.
    그래서 같은 길이의 공백으로 치환한다 — 이 단언이 그 계약이다.
    """
    src = "a: 1\n  # comment here\nb: 2\n"
    out = _strip_comment_lines(src)
    assert len(out) == len(src)
    assert "comment" not in out
    assert out.startswith("a: 1\n")
    assert out.endswith("b: 2\n")
