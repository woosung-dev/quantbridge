"""[BL-347] `Server: uvicorn` 을 실제로 지우는 것은 **기동 플래그**다.

★★**종전 회귀 테스트는 항진명제였다.** `test_main_security_headers.py::test_server_header_stripped`
는 `TestClient` 로 재는데, `TestClient` 는 uvicorn 의 프로토콜 계층을 안 태우므로 응답에
`server` 헤더가 **애초에 없다.** 그래서 「없다」는 단언이 미들웨어와 무관하게 통과했다.

2026-08-16 로컬 실측 (호스트 uvicorn, 8경로 `/health` `/healthz` `/metrics` `/api/v1/auth/me`
`/api/v1/strategies` `/docs` `/openapi.json` `/nonexistent`):

- `--no-server-header` **없이** → **8/8** 이 `server: uvicorn` 을 냈다 (미들웨어가 있는데도).
- `--no-server-header` **붙여서** → **8/8** 사라졌다.

미들웨어가 못 지우는 이유는 uvicorn 이 그 헤더를 ASGI 바깥에서 붙이기 때문이다 —
`SecurityHeadersMiddleware` 가 보는 `response.headers` 에 그 키가 존재한 적이 없다.

⇒ 재야 할 것은 「응답에 헤더가 없는가」가 아니라 **「우리가 uvicorn 을 그 플래그로 부르는가」**다.
`--server_header False` 같은 gunicorn 식 표기는 이 레포에 해당이 없다 — gunicorn 은 의존성에
**0건**이고 uvicorn 의 실제 플래그 이름은 `--no-server-header` 다(`uvicorn --help` 실측).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]

# uvicorn 을 기동하는 레포 안의 모든 자리. ★서버 systemd 유닛은 레포에 원본이 없다
# (`gates-and-traps.md` §운영) — 그쪽은 `better-auth-setup.md` 의 배포 절차가 책임진다.
# ★2026-08-16 codex 적대 리뷰 P2 — 초판은 아래 두 파일만 봤는데 **README 3종도 같은 명령을
#   안내하고 있었다.** 「레포의 모든 uvicorn 기동」이라는 이 파일의 주장이 그만큼 거짓이었다.
#   문서의 기동 명령도 사람이 그대로 복사하는 실행 경로다.
#   ★서버 systemd 유닛은 레포에 원본이 없다(`gates-and-traps.md` §운영) —
#   그쪽은 `better-auth-setup.md` 의 배포 절차가 책임진다.
_LAUNCH_SITES = [
    _REPO / "apps/api/docker-entrypoint.sh",
    _REPO / "Makefile",
    _REPO / "README.md",
    _REPO / "apps/api/README.md",
    _REPO / "docs/reference/operations/local-setup.md",
]

_UVICORN_CALL = re.compile(r"uvicorn\s+src\.main:app[^\n]*")


def _uvicorn_invocations() -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    for path in _LAUNCH_SITES:
        assert path.exists(), f"기동 자리가 사라졌다: {path}"
        for line in _UVICORN_CALL.findall(path.read_text()):
            found.append((path, line))
    return found


def test_every_uvicorn_invocation_disables_server_header() -> None:
    """레포 안의 `uvicorn src.main:app` 호출 **전부**가 플래그를 갖는다."""
    invocations = _uvicorn_invocations()

    # ★양성 대조 — 찾은 것이 0건이면 아래 루프가 **빈 입력으로 초록**이다.
    #   이 레포에서 빈 입력 통과는 반복된 실패 모드라 개수를 먼저 못 박는다.
    assert len(invocations) >= 6, (
        f"uvicorn 기동 자리를 {len(invocations)}건밖에 못 찾았다 — "
        "정규식이 죽었거나 기동 방식이 바뀌었다. 세는 것을 먼저 고쳐라."
    )
    # ★파일 수도 센다 — 한 파일에서 6건을 찾아도 위 단언은 통과한다.
    assert len({p for p, _ in invocations}) >= 5, (
        "기동 자리가 한두 파일에만 몰려 있다 — `_LAUNCH_SITES` 중 일부가 사라졌거나 "
        "그 파일의 명령 표기가 바뀌었다."
    )

    missing = [
        (str(p.relative_to(_REPO)), line)
        for p, line in invocations
        if "--no-server-header" not in line
    ]
    assert not missing, f"`--no-server-header` 없는 uvicorn 기동: {missing}"


def test_repo_has_no_gunicorn() -> None:
    """★원장 BL-347 이 지시한 `gunicorn --server_header False` 는 **대상이 없다.**

    gunicorn 이 의존성에 들어오면 이 항목의 전제가 바뀌므로 그때 다시 판단하라는 뜻이다.
    """
    pyproject = (_REPO / "apps/api/pyproject.toml").read_text()
    assert "gunicorn" not in pyproject, (
        "gunicorn 이 의존성에 들어왔다 — BL-347 의 수단(uvicorn 플래그)을 다시 판단해라."
    )


@pytest.mark.parametrize("flag", ["--server_header", "--server-header False"])
def test_nonexistent_flag_spellings_are_not_used(flag: str) -> None:
    """★음성 대조 — 존재하지 않는 플래그 표기가 기어들어오면 기동이 죽는다.

    `uvicorn --help` 이 내는 것은 `--server-header / --no-server-header` 쌍이다.
    `--server_header`(밑줄)나 `--server-header False`(별도 인자)는 uvicorn 에 없다.

    ★검사 범위는 **기동 줄**이다 — 파일 전체를 보면 이 사실을 설명하는 주석이 스스로 걸린다
    (초판이 정확히 그렇게 red 였다).
    """
    for path, line in _uvicorn_invocations():
        assert flag not in line, f"{path.name} 기동 줄에 존재하지 않는 플래그 표기: {flag}"
