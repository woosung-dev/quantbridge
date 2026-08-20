"""`notify-telegram.sh` seam·HTTP 판정·토큰 비노출 계약을 고정한다."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

LIB = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "lib" / "notify-telegram.sh"


def notify(
    body: str,
    env: dict[str, str],
    path_prepend: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """실제 source-only 라이브러리를 `set -uo pipefail` 계약 아래 호출한다."""
    environment = {**os.environ, **env}
    if path_prepend is not None:
        environment["PATH"] = f"{path_prepend}:{environment['PATH']}"
    return subprocess.run(
        ["bash", "-c", 'set -uo pipefail; . "$1"; qb_notify_telegram "$2"', "x", str(LIB), body],
        capture_output=True,
        check=False,
        text=True,
        timeout=60,
        env=environment,
    )


def _write_stubs(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """macOS·Linux 모두에서 curl/timeout을 실제 실행 없이 결정론적으로 대체한다."""
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    curl_args = tmp_path / "curl-args.txt"

    curl = stub_bin / "curl"
    curl.write_text(
        r"""#!/usr/bin/env bash
printf '%s\n' "$@" > "${CURL_STUB_ARGS_FILE:?}"
if [ "${CURL_STUB_CODE+x}" = x ]; then
  printf '%s' "${CURL_STUB_CODE}"
else
  printf '200'
fi
""",
        encoding="utf-8",
    )
    curl.chmod(0o755)

    timeout = stub_bin / "timeout"
    timeout.write_text(
        """#!/usr/bin/env bash
shift
exec "$@"
""",
        encoding="utf-8",
    )
    timeout.chmod(0o755)

    return stub_bin, {"CURL_STUB_ARGS_FILE": str(curl_args)}


def _write_credentials(
    tmp_path: Path,
    *,
    token: str = "TEST-TOKEN",
    chat_id: str = "12345",
) -> Path:
    """실제 자격증명 없이 라이브러리가 source할 최소 env 파일을 만든다."""
    credentials = tmp_path / "telegram.env"
    credentials.write_text(
        f"TELEGRAM_BOT_TOKEN={token}\nTELEGRAM_CHAT_ID={chat_id}\n",
        encoding="utf-8",
    )
    return credentials


def test_missing_env_file_returns_one_without_calling_curl(tmp_path: Path) -> None:
    """자격증명 파일 설정이 없으면 전송 전에 fail-closed한다."""
    stub_bin, stub_env = _write_stubs(tmp_path)

    result = notify(
        "missing env file",
        {**stub_env, "QB_NOTIFY_ENV_FILE": "", "QB_NOTIFY_CMD": ""},
        stub_bin,
    )

    assert result.returncode == 1
    assert "QB_NOTIFY_ENV_FILE" in result.stderr
    assert not (tmp_path / "curl-args.txt").exists()


def test_absent_credential_file_returns_one_with_path(tmp_path: Path) -> None:
    """지정했지만 없는 자격증명 파일 경로는 오류에 남긴다."""
    stub_bin, stub_env = _write_stubs(tmp_path)
    missing = tmp_path / "missing-telegram.env"

    result = notify(
        "missing credential path",
        {**stub_env, "QB_NOTIFY_ENV_FILE": str(missing), "QB_NOTIFY_CMD": ""},
        stub_bin,
    )

    assert result.returncode == 1
    assert str(missing) in result.stderr


@pytest.mark.parametrize(
    ("token", "chat_id"),
    [("", "12345"), ("TEST-TOKEN", "")],
    ids=["empty-token", "empty-chat-id"],
)
def test_empty_credentials_return_one(tmp_path: Path, token: str, chat_id: str) -> None:
    """토큰·챗 ID는 각각 독립적으로 빈 값이면 전송하지 않는다."""
    stub_bin, stub_env = _write_stubs(tmp_path)
    credentials = _write_credentials(tmp_path, token=token, chat_id=chat_id)

    result = notify(
        "empty credential",
        {**stub_env, "QB_NOTIFY_ENV_FILE": str(credentials), "QB_NOTIFY_CMD": ""},
        stub_bin,
    )

    assert result.returncode == 1
    assert "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID" in result.stderr


@pytest.mark.parametrize("command_code", [0, 17], ids=["success", "failure"])
def test_notify_command_seam_passes_stdin_and_preserves_exit_code(
    tmp_path: Path,
    command_code: int,
) -> None:
    """seam은 자격증명 검사보다 먼저 본문만 stdin으로 넘긴다."""
    stub_bin, stub_env = _write_stubs(tmp_path)
    capture = tmp_path / "seam-body.txt"
    seam = tmp_path / "capture-seam"
    seam.write_text(
        """#!/usr/bin/env bash
cat > "${QB_NOTIFY_CAPTURE_FILE:?}"
exit "${QB_NOTIFY_COMMAND_CODE:?}"
""",
        encoding="utf-8",
    )
    seam.chmod(0o755)

    result = notify(
        "seam body",
        {
            **stub_env,
            "QB_NOTIFY_CAPTURE_FILE": str(capture),
            "QB_NOTIFY_CMD": str(seam),
            "QB_NOTIFY_COMMAND_CODE": str(command_code),
            "QB_NOTIFY_ENV_FILE": "",
        },
        stub_bin,
    )

    assert result.returncode == command_code
    assert capture.read_text(encoding="utf-8") == "seam body\n"
    assert not (tmp_path / "curl-args.txt").exists()


@pytest.mark.parametrize(
    ("http_code", "expected_returncode"),
    [("200", 0), ("404", 1), ("", 1)],
    ids=["ok", "not-found", "empty"],
)
def test_http_status_code_is_decided_directly(
    tmp_path: Path,
    http_code: str,
    expected_returncode: int,
) -> None:
    """curl 종료 코드가 아니라 출력된 HTTP 코드만으로 성공을 판정한다."""
    stub_bin, stub_env = _write_stubs(tmp_path)
    credentials = _write_credentials(tmp_path)

    result = notify(
        "HTTP status",
        {
            **stub_env,
            "CURL_STUB_CODE": http_code,
            "QB_NOTIFY_ENV_FILE": str(credentials),
            "QB_NOTIFY_CMD": "",
        },
        stub_bin,
    )

    assert result.returncode == expected_returncode
    if http_code == "404":
        assert "HTTP 404" in result.stderr


def test_curl_hides_response_body_and_receives_required_arguments(tmp_path: Path) -> None:
    """curl 호출은 응답 본문을 버리고 chat_id·text를 data-urlencode로 넘긴다."""
    stub_bin, stub_env = _write_stubs(tmp_path)
    credentials = _write_credentials(tmp_path, token="ARGUMENT-TOKEN", chat_id="98765")

    result = notify(
        "curl argument body",
        {
            **stub_env,
            "CURL_STUB_CODE": "200",
            "QB_NOTIFY_ENV_FILE": str(credentials),
            "QB_NOTIFY_CMD": "",
        },
        stub_bin,
    )
    args = (tmp_path / "curl-args.txt").read_text(encoding="utf-8").splitlines()

    assert result.returncode == 0
    assert "--output" in args
    assert "/dev/null" in args
    assert "--data-urlencode" in args
    assert "chat_id=98765" in args
    assert "text=curl argument body" in args
    assert "--max-time" in args


def test_token_and_host_are_silent_on_http_failure(tmp_path: Path) -> None:
    """양성 대조가 있는 404 실패도 URL 구성 요소를 stdout/stderr에 남기지 않는다."""
    stub_bin, stub_env = _write_stubs(tmp_path)
    token = "SEKRET-DO-NOT-LEAK-0000"
    credentials = _write_credentials(tmp_path, token=token)

    result = notify(
        "silent failure",
        {
            **stub_env,
            "CURL_STUB_CODE": "404",
            "QB_NOTIFY_ENV_FILE": str(credentials),
            "QB_NOTIFY_CMD": "",
        },
        stub_bin,
    )

    output = result.stdout + result.stderr
    host = ".".join(("api", "telegram", "org"))
    assert result.returncode == 1
    assert result.stderr
    assert "HTTP 404" in result.stderr
    assert token not in output
    assert host not in output


def test_token_and_host_are_silent_on_http_success(tmp_path: Path) -> None:
    """성공 경로도 URL 구성 요소를 stdout/stderr에 남기지 않는다."""
    stub_bin, stub_env = _write_stubs(tmp_path)
    token = "SEKRET-DO-NOT-LEAK-0000"
    credentials = _write_credentials(tmp_path, token=token)

    result = notify(
        "silent success",
        {
            **stub_env,
            "CURL_STUB_CODE": "200",
            "QB_NOTIFY_ENV_FILE": str(credentials),
            "QB_NOTIFY_CMD": "",
        },
        stub_bin,
    )

    output = result.stdout + result.stderr
    host = ".".join(("api", "telegram", "org"))
    assert result.returncode == 0
    assert token not in output
    assert host not in output
