# nightly real-broker 워크플로가 「거짓말하지 않는」 계약을 지키는지 감사한다.
"""nightly-real-broker 워크플로 계약 감사 — 2026-08-04 [BL-024] 실측 결함의 재발 방지.

★**무엇이 고장나 있었나.** `.github/workflows/nightly-real-broker.yml` 은 07-25 ~ 08-03
**10/10 실패**했고, 실패 지점은 pytest 가 아니라 `alembic upgrade head` 였다.
`secrets.TRADING_ENCRYPTION_KEYS_TEST` 가 repo 에 없어 env 가 **빈 문자열**이 되고
`Settings` 검증이 import 시점에 죽었다. ⇒ **pytest 는 한 번도 실행된 적이 없다.**
그 10회가 만든 `flaky-real-broker` 이슈 **89건은 broker flakiness 의 증거가 아니다** —
전부 워크플로 자체의 결함이 만든 것이다.

★**그리고 그 수리가 새로운 거짓말을 만들 수 있다.** 자격증명이 없을 때 pytest 를
건너뛰게 만들면 워크플로는 green 이 된다. 그 green 은 "실거래소가 정상" 이 아니라
"아무것도 재지 않았다" 는 뜻이다. `::warning` 과 step summary 로 표면화하지만, 그건
사람이 봐야 보인다. **이 테스트가 그 계약을 기계로 고정한다.**

★**marker 없음** — 매 PR 에서 돌고 자격증명이 필요 없다. 워크플로 텍스트만 읽는다.

`test_ci_workflow_env_parity.py` 가 `ci.yml` 을 보고, 본 파일이 `nightly-real-broker.yml`
을 본다. compose 기본값 주입 감사(`_settings_infra_fields`)는 **같은 탐지기를 재사용**한다 —
탐지기가 죽으면 두 감사가 함께 죽어야지 한쪽만 조용히 통과하면 안 된다.

**YAML 파서를 새로 들이지 않는다** — `pyyaml` 은 `apps/api/pyproject.toml` 에 선언돼 있지
않고(전이 의존), 이 감사가 보려는 것은 "그 스텝의 그 키가 무엇인가" 뿐이다. 대신
스텝 경계는 들여쓰기로 자르고, **자른 결과가 비지 않았는지를 별도 테스트가 단언**한다.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from tests.test_ci_workflow_env_parity import _settings_infra_fields

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "nightly-real-broker.yml"

# 감사가 이름으로 찾는 스텝들. 이름이 바뀌면 파서가 못 찾고 자기검증이 red 가 된다.
_PYTEST_STEP_MARKER = "--run-real-broker"
_ISSUE_STEP_MARKER = "issues.create"

# ★게이트는 **정확한 형태**로 단언한다. `has_creds` 토큰 포함만 보면 `!= 'true'` /
#   `== 'false'` 로 조건을 뒤집어도 감사가 통과한다(2026-08-04 적대 검증 F4).
_HAS_CREDS_TRUE = "steps.preflight.outputs.has_creds == 'true'"


def _normalize(text: str) -> str:
    """줄바꿈·연속 공백을 단일 공백으로 접는다 (YAML 줄 접힘·들여쓰기 무시)."""
    return re.sub(r"\s+", " ", text).strip()

pytestmark = pytest.mark.skipif(not _WORKFLOW.exists(), reason="워크플로 파일이 없는 체크아웃")


def _job_body() -> str:
    """`real_broker_e2e` 잡 본문 텍스트."""
    text = _WORKFLOW.read_text()
    start = text.index("\n  real_broker_e2e:\n")
    return text[start:]


def _steps() -> list[str]:
    """잡의 `steps:` 를 스텝별 raw 텍스트 블록으로 자른다.

    스텝은 `      - ` (6칸 + '- ') 로 시작하고 하위 키는 8칸 이상이다. 들여쓰기가
    6칸 미만인 비어있지 않은 줄이 나오면 steps 블록이 끝난 것이다.

    ★**YAML 주석(들여쓰기 8칸 이하의 `#` 줄)은 버린다.** 스텝 사이의 설명 주석은
    앞 스텝 블록 꼬리에 붙어, 다음 스텝을 설명하는 문구가 **앞 스텝의 내용처럼**
    읽힌다. 실제로 이 감사를 처음 돌렸을 때 `--run-real-broker` 앵커가 2개로 세어졌다.
    `run: |` 안의 셸 본문은 10칸 이상이라 영향받지 않는다.
    """
    body = _job_body()
    marker = "\n    steps:\n"
    tail = body[body.index(marker) + len(marker) :]

    blocks: list[list[str]] = []
    for line in tail.splitlines():
        if line.strip() and not line.startswith(" " * 6):
            break
        if re.match(r"^\s{0,8}#", line):
            continue
        if line.startswith(" " * 6 + "- "):
            blocks.append([line])
        elif blocks:
            blocks[-1].append(line)
    return ["\n".join(b) for b in blocks]


def _scalar(block: str, key: str) -> str | None:
    """스텝 블록에서 top-level 스칼라 키의 값. 없으면 None.

    첫 줄의 `      - key: value` 형태와 이어지는 `        key: value` 형태를 모두 받는다.
    """
    pattern = rf"^(?:\s{{6}}- |\s{{8}}){re.escape(key)}:[ \t]*(.*)$"
    m = re.search(pattern, block, re.MULTILINE)
    if m is None:
        return None
    return m.group(1).strip()


def _find_step(marker: str) -> str:
    """본문에 `marker` 를 포함하는 유일한 스텝 블록."""
    hits = [b for b in _steps() if marker in b]
    assert len(hits) == 1, (
        f"'{marker}' 를 포함하는 스텝이 {len(hits)}개다 (1개여야 한다). "
        "워크플로 구조가 바뀌었거나 스텝 분할 파서가 죽었다."
    )
    return hits[0]


def _job_env() -> dict[str, str]:
    """잡 레벨 `env:` 블록의 키 → 값.

    services 블록의 `env:` 와 섞이지 않도록 **8칸 들여쓰기의 `    env:`** 만 연다
    (잡 레벨 env 는 6칸 키 = `    env:`, service 의 env 는 더 깊다).
    """
    body = _job_body()
    m = re.search(r"^    env:\s*$", body, re.MULTILINE)
    assert m is not None, "잡 레벨 env: 블록을 찾지 못했다 — 파서가 죽었다"
    out: dict[str, str] = {}
    for line in body[m.end() :].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        km = re.match(r"^\s{6}([A-Z][A-Z0-9_]*):[ \t]*(.*)$", line)
        if km:
            out[km.group(1)] = km.group(2).strip()
            continue
        if line.strip() and not line.startswith(" " * 7):
            break
    return out


# --------------------------------------------------------------------------
# ★자기검증 — 감사 대상 집합이 비면 아래 감사들이 **전부 통과해 버린다**.
#   이 레포는 "가드가 판별력을 증명하지 못한 채 초록" 을 반복해서 밟았다.
# --------------------------------------------------------------------------


def test_audit_parses_the_workflow_steps_at_all() -> None:
    """스텝 분할 파서가 살아 있는지 고정한다 (음성 대조)."""
    blocks = _steps()
    assert len(blocks) >= 8, f"스텝을 {len(blocks)}개만 잘랐다 — 파서가 죽었다"
    names = [_scalar(b, "name") for b in blocks]
    assert "Alembic migrate" in names, f"알려진 스텝을 못 찾았다: {names}"
    assert any(_PYTEST_STEP_MARKER in b for b in blocks), "pytest 스텝을 못 찾았다"
    assert any(_ISSUE_STEP_MARKER in b for b in blocks), "이슈 생성 스텝을 못 찾았다"


def test_audit_parses_the_job_env_at_all() -> None:
    """잡 레벨 env 파서가 살아 있는지 고정한다 (음성 대조)."""
    env = _job_env()
    assert "DATABASE_URL" in env, f"잡 env 를 못 읽었다: {sorted(env)}"
    assert "TRADING_ENCRYPTION_KEYS" in env, f"잡 env 를 못 읽었다: {sorted(env)}"


# --------------------------------------------------------------------------
# 감사 항목
# --------------------------------------------------------------------------


def test_encryption_key_is_usable_without_any_repo_secret() -> None:
    """W1 — ★10/10 실패의 실제 원인. 이 값이 secret 에만 의존하면 alembic 부터 죽는다.

    red 면 고장난 것: `apps/api/alembic/env.py:24` 가 `src.core.config` 를 import 하고,
    `Settings` 가 **import 시점에** `TRADING_ENCRYPTION_KEYS` 를 검증한다(빈 문자열 =
    ValidationError) ⇒ `alembic upgrade head` 스텝이 죽고 **pytest 는 실행조차 안 된다**.

    ★이 고장은 **alembic 스텝에만** 해당한다 — `tests/conftest.py:25-28` 은 빈 값을
    감지하면 유효 Fernet 키를 즉석 생성해 채운다. "빈 secret 이면 무조건 죽는다" 가
    아니라 "pytest 밖이라서 죽는다" 다. 이 감사는 그 정확한 경계를 고정한다.

    ★검사 방식: repo secret 이 하나도 없어도 이 값이 **유효한 Fernet 키로 해석되는가**.
    `${{ secrets.X }}` 만 있는 형태는 secret 부재 시 빈 문자열이 되므로 red 다.
    `${{ secrets.X || '리터럴' }}` 형태는 폴백 리터럴을 꺼내 검사한다 — 단 이 레포는
    그 패턴을 쓰지 않는다(GHA 가 빈 문자열을 falsy 로 보는지 이 환경에서 실행으로
    검증할 수 없었다. `ci.yml:153` 과 같은 평범한 리터럴을 쓴다).
    """
    from cryptography.fernet import Fernet

    value = _job_env().get("TRADING_ENCRYPTION_KEYS")
    assert value, "TRADING_ENCRYPTION_KEYS 가 잡 env 에 없다"

    fallback = value
    m = re.fullmatch(r"\$\{\{.*?\|\|\s*'([^']+)'\s*\}\}", value)
    if m:
        fallback = m.group(1)

    assert "${{" not in fallback, (
        "TRADING_ENCRYPTION_KEYS 가 repo secret 에만 의존한다. 그 secret 이 없으면 "
        "이 값은 **빈 문자열**이 되고 `alembic upgrade head` 가 import 시점에 죽는다 — "
        f"2026-08-03 까지 10/10 실패가 정확히 이것이다. 현재 값: {value}"
    )

    key = fallback.strip().strip('"').strip("'")
    try:
        Fernet(key.encode())
    except Exception as exc:  # 어떤 실패든 "쓸 수 없는 키" 다
        pytest.fail(
            f"TRADING_ENCRYPTION_KEYS 값이 유효한 Fernet 키가 아니다: {exc}. "
            "값이 '있다' 는 것과 '쓸 수 있다' 는 것은 다르다 — `Settings` 는 후자를 요구한다."
        )


def test_preflight_step_publishes_has_creds_output() -> None:
    """W2 — 자격증명 부재를 「제3의 상태」로 표면화하는 스텝이 있어야 한다.

    red 면 고장난 것: 아래 두 게이팅 감사(pytest / 이슈)가 참조할 출력이 사라진다 ⇒
    자격증명 부재가 다시 「그냥 실패」로 보고되고 이슈 생산기가 재가동된다.
    """
    preflight = _find_step("has_creds=")
    assert _scalar(preflight, "id") == "preflight", (
        "preflight 스텝에 `id: preflight` 가 없다 — 다른 스텝이 참조할 수 없다"
    )
    assert "$GITHUB_OUTPUT" in preflight, (
        "preflight 가 has_creds 를 `$GITHUB_OUTPUT` 에 쓰지 않는다 — 스텝 출력이 안 생긴다"
    )
    assert "::warning" in preflight, (
        "자격증명 부재 시 `::warning` 어노테이션이 없다 — 미측정이 조용히 green 이 된다"
    )
    assert "$GITHUB_STEP_SUMMARY" in preflight, (
        "step summary 기록이 없다 — 왜 green 인지 실행 페이지에서 알 수 없다"
    )


def test_pytest_step_is_gated_on_credentials() -> None:
    """W3 — 자격증명이 없는데 `--run-real-broker` 를 부르면 conftest 가 `pytest.fail` 한다.

    red 면 고장난 것: `apps/api/tests/real_broker/conftest.py` 의
    `bybit_demo_test_credentials` 가 env 부재 시 `pytest.fail` 로 red 를 낸다(의도된 계약).
    그 red 는 broker 결함이 아니라 **워크플로가 조건 없이 불렀다**는 뜻이다.
    """
    step = _find_step(_PYTEST_STEP_MARKER)
    cond = _scalar(step, "if")
    assert cond is not None, "pytest 스텝에 `if:` 게이트가 없다"
    assert _normalize(cond) == _HAS_CREDS_TRUE, (
        "pytest 스텝의 게이트가 정확히 "
        f"`{_HAS_CREDS_TRUE}` 가 아니다: if={cond!r}\n"
        "★부분문자열(`has_creds` 포함)로 재면 `!= 'true'` / `== 'false'` 로 **뒤집어도** "
        "감사가 통과한다(2026-08-04 적대 검증 F4)."
    )


def test_issue_creation_step_is_gated_on_credentials() -> None:
    """W4 — ★89개 이슈 생산기의 스위치.

    red 면 고장난 것: 자격증명 없이 난 실패(=워크플로 결함)가 다시
    `flaky-real-broker` 이슈로 등재된다. 89건 전부 그렇게 만들어졌고 전부 OPEN 이다 —
    원장이 broker flakiness 를 과대계상한다.
    """
    step = _find_step(_ISSUE_STEP_MARKER)
    cond = _scalar(step, "if")
    assert cond is not None, "이슈 생성 스텝에 `if:` 게이트가 없다"
    assert _normalize(cond) == f"failure() && {_HAS_CREDS_TRUE}", (
        "이슈 생성 스텝의 게이트가 정확히 "
        f"`failure() && {_HAS_CREDS_TRUE}` 가 아니다: if={cond!r}\n"
        "자격증명 없이 난 실패가 다시 flaky 이슈로 등재된다(2026-08-03 까지 89건).\n"
        "★부분문자열로 재면 조건을 **뒤집어도** 감사가 통과한다(적대 검증 F4)."
    )


def test_issue_labels_are_only_flaky_real_broker() -> None:
    """W9 — 스프린트 59 시대에 `sprint-10` 라벨은 원장 오염이다.

    red 면 고장난 것: 이슈 원장의 라벨 필터가 폐기된 스프린트 이름으로 오염된다.
    """
    step = _find_step(_ISSUE_STEP_MARKER)
    assert "sprint-10" not in step, (
        "이슈 스텝이 아직 `sprint-10` 라벨을 붙인다 — 현재 스프린트는 59다"
    )
    assert "flaky-real-broker" in step, "라벨 `flaky-real-broker` 가 사라졌다"


def test_pytest_step_preserves_exit_code_through_the_pipe() -> None:
    """FI-3 앵커 — `| tee` 가 pytest 의 exit code 를 삼키는 것을 막는다.

    실측(2026-08-04):
      `bash -eo pipefail -c 'false | tee /dev/null'` → exit 1  (보존)
      `bash -c 'false | tee /dev/null'`             → exit 0  (유실)

    red 면 고장난 것: pytest 가 실패해도 스텝이 green 이 된다 ⇒ 실거래소 회귀가
    **조용히 통과**하고, 게다가 `if: failure()` 인 이슈 생성도 안 돌아 아무도 모른다.
    """
    step = _find_step(_PYTEST_STEP_MARKER)
    assert "| tee" in step, "pytest 출력 tee 가 사라졌다 — 아티팩트/이슈 인용이 빈다"
    shell = _scalar(step, "shell")
    assert shell is not None and "pipefail" in shell, (
        "pytest 스텝의 shell 에 `pipefail` 이 없다. `| tee` 가 exit code 를 삼켜 "
        f"실패가 green 으로 보고된다. shell={shell!r}"
    )


def test_pytest_step_redirects_stderr_into_the_tee() -> None:
    """★`tee` 는 **stdout 만** 받는다 — RESIDUAL 은 stderr 로 나온다.

    red 면 고장난 것: `apps/api/tests/real_broker/_harness.py:emit_residual_report` 가
    RESIDUAL 블록을 `sys.stderr` 로 쓴다. `2>&1` 이 없으면 그 블록이
    `/tmp/real-broker-output.txt` 에 **한 줄도 들어가지 않는다** ⇒ 아티팩트에도, 이슈
    본문 인용에도 없고, 이슈 triage 4번(「RESIDUAL 블록이 위 출력에 있으면」)이
    **도달 불가**가 된다. 거래소에 포지션이 남았다는 사실이 실행 페이지에서 사라진다.

    실측(2026-08-04):
      `python -c '…stdout…; …stderr…' | tee f`       → f 에 stdout 줄만
      `python -c '…stdout…; …stderr…' 2>&1 | tee f`  → f 에 둘 다 (exit code 1 보존)

    ★`2>&1` 은 파이프 **앞**에 와야 한다. 파이프 뒤에 두면 tee 의 stderr 를 돌리는 것이라
    아무 효과가 없다.
    """
    step = _find_step(_PYTEST_STEP_MARKER)
    body = _normalize(step)
    assert "2>&1 | tee" in body, (
        "pytest 스텝이 stderr 를 tee 로 넘기지 않는다. RESIDUAL 보고가 stderr 라 "
        "아티팩트·이슈 본문에 **절대** 들어가지 않는다(적대 검증 F2). "
        "`2>&1` 을 파이프 앞에 둬라."
    )


def test_pytest_step_uses_signal_timeout_method() -> None:
    """W7 — timeout 이 thread 방식이면 프로세스가 죽어 **cleanup 이 아예 안 돈다**.

    ★이 감사는 살아 있는 버그를 잡는 것이 아니다 — 실측으로
    `pytest_timeout.DEFAULT_METHOD == "signal"` 이라 명시는 동작상 중복이다.
    **의도를 고정하는 것**이 목적이다: 누군가 `thread` 로 바꾸면(또는 상류 기본값이
    바뀌면) `os._exit(1)` 이 돌아 아래가 침묵으로 사라진다.

    red 면 고장난 것: `apps/api/tests/real_broker/conftest.py` 의
    `pytest_sessionfinish` 백스톱(거래소 포지션 청산)이 timeout 시 실행되지 않는다 ⇒
    Bybit demo 계정에 포지션이 남은 채 세션이 "통과" 로 끝난다.
    """
    step = _find_step(_PYTEST_STEP_MARKER)
    assert "--timeout-method=signal" in step, (
        "pytest 스텝에 `--timeout-method=signal` 이 없다 — 기본(thread) 이면 timeout 시 "
        "프로세스가 죽어 `pytest_sessionfinish` 청산 백스톱이 안 돈다"
    )


def test_no_step_is_still_labelled_skeleton() -> None:
    """W5 — 「skeleton」 이라는 이름이 남아 있으면 실행 페이지가 사실과 다르다.

    red 면 고장난 것: 워크플로 실행 페이지가 이 잡을 여전히 미구현 골격으로 표기한다.
    """
    offenders = [
        name
        for name in (_scalar(b, "name") for b in _steps())
        if name and "skeleton" in name.lower()
    ]
    assert not offenders, f"스텝 이름에 'skeleton' 이 남아 있다: {offenders}"


def test_database_urls_point_at_a_test_database() -> None:
    """W6 — `tests/conftest.py` 세션 픽스처의 `drop_all` 이 겨냥할 DB 이름을 고정한다.

    red 면 고장난 것: `apps/api/tests/conftest.py` 가 `TEST_DATABASE_URL` >
    `DATABASE_URL` 순으로 DSN 을 고르고 그 DB 에 `SQLModel.metadata.drop_all` 을 돈다.
    이름이 `_test` 로 끝나지 않으면 `apps/api/tests/real_broker/conftest.py` 의 DSN
    하드가드가 세션을 즉시 중단시킨다(= 실행 자체가 불가능해진다).
    """
    from sqlalchemy.engine import make_url

    env = _job_env()
    for key in ("DATABASE_URL", "TEST_DATABASE_URL"):
        raw = env.get(key)
        assert raw, f"{key} 가 잡 env 에 없다"
        db = make_url(raw).database
        assert db and db.endswith("_test"), (
            f"{key} 의 database='{db}' 가 '_test' 로 끝나지 않는다. "
            "real_broker conftest 의 DSN 가드가 세션을 중단시킨다"
        )

    body = _job_body()
    m = re.search(r"^\s+POSTGRES_DB:\s*(\S+)\s*$", body, re.MULTILINE)
    assert m is not None, "postgres 서비스의 POSTGRES_DB 를 찾지 못했다"
    assert m.group(1).endswith("_test"), (
        f"POSTGRES_DB='{m.group(1)}' 가 '_test' 로 끝나지 않는다 — DATABASE_URL 이 "
        "가리키는 DB 가 생성되지 않아 alembic 이 죽는다"
    )


def test_nightly_injects_every_compose_default_setting() -> None:
    """compose 호스트를 기본값으로 갖는 `Settings` 필드는 nightly env 에도 주입돼야 한다.

    red 면 고장난 것: `apps/api/src/core/config.py` 의 그 필드 기본값이 docker-compose
    서비스명(`redis://redis:6379/*`, `@db:5432/*`)이라 러너에서 해석되지 않는다.
    ci.yml 에서 실제로 이 누락으로 5건이 죽었다(2026-08-01). nightly 는 지금까지
    **감사 대상이 아니었다** — 그게 이 파일이 신설된 이유 중 하나다.
    """
    required = _settings_infra_fields()
    assert required, "감사 대상이 0개다 — 탐지 로직이 죽었는지 확인해라"

    injected = set(_job_env())
    missing = sorted(env for env in required.values() if env not in injected)
    assert not missing, (
        f"nightly-real-broker.yml 잡 env 에 다음이 빠졌다: {missing}\n"
        f"확인 대상 필드 → 환경변수: {required}"
    )
