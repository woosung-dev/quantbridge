"""pre-push ref guard 순수 술어를 POSIX sh 계약으로 검증한다."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

LIB = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "lib" / "pre-push-ref-guard.sh"


def call(fn: str, *args: str, shell: str = "sh") -> subprocess.CompletedProcess[str]:
    """술어를 1회 호출한다. 판정은 종료 코드다 (stdout은 verdict 함수에서만 쓴다)."""
    script = f'. "$1"; shift; {fn} "$@"'
    return subprocess.run(
        [shell, "-c", script, "x", str(LIB), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.parametrize("ref", ["refs/heads/main", "refs/heads/master", "main", "master"])
def test_protected_refs_accept_main_and_master(ref: str) -> None:
    """main/master는 refs 접두사 유무와 무관하게 보호한다."""
    result = call("qb_ref_is_protected", ref)

    assert result.returncode == 0


@pytest.mark.parametrize(
    "ref",
    ["refs/heads/mainline", "refs/heads/main-2", "refs/heads/feat/main", "refs/heads/notmain"],
)
def test_protected_refs_reject_prefix_and_nested_matches(ref: str) -> None:
    """보호 분기는 정확한 브랜치 이름만 받는다."""
    result = call("qb_ref_is_protected", ref)

    assert result.returncode == 1


@pytest.mark.parametrize(
    ("ref", "expected_returncode"),
    [
        ("refs/heads/x", 0),
        ("refs/heads/", 1),
        ("refs/tags/v1", 1),
        ("HEAD", 1),
    ],
)
def test_head_ref_requires_a_nonempty_heads_name(ref: str, expected_returncode: int) -> None:
    """브랜치 ref는 refs/heads/ 아래의 비어 있지 않은 이름이어야 한다."""
    result = call("qb_ref_is_head_ref", ref)

    assert result.returncode == expected_returncode


@pytest.mark.parametrize(
    ("ref", "expected_returncode"),
    [
        ("refs/tags/v1", 0),
        ("refs/tags/", 1),
        ("refs/heads/v1", 1),
    ],
)
def test_tag_ref_requires_a_nonempty_tag_name(ref: str, expected_returncode: int) -> None:
    """태그 ref는 refs/tags/ 아래의 비어 있지 않은 이름이어야 한다."""
    result = call("qb_ref_is_tag_ref", ref)

    assert result.returncode == expected_returncode


@pytest.mark.parametrize(
    "ref",
    [
        "refs/heads/stage/x",
        "refs/heads/feat/x",
        "refs/heads/fix/x",
        "refs/heads/chore/x",
        "refs/heads/docs/x",
        "refs/heads/test/x",
        "refs/heads/refactor/x",
        "refs/heads/hotfix/x",
    ],
)
def test_whitelisted_refs_accept_every_configured_prefix(ref: str) -> None:
    """허용 목록의 여덟 prefix를 빠짐없이 고정한다."""
    result = call("qb_ref_is_whitelisted", ref)

    assert result.returncode == 0


@pytest.mark.parametrize("ref", ["refs/heads/feature/x", "refs/heads/wip-x", "main", ""])
def test_whitelisted_refs_reject_unconfigured_prefixes(ref: str) -> None:
    """feature/와 임의 이름은 허용 목록이 아니다."""
    result = call("qb_ref_is_whitelisted", ref)

    assert result.returncode == 1


@pytest.mark.parametrize(
    ("local_ref", "local_sha", "expected_returncode"),
    [
        ("(delete)", "arbitrary", 0),
        ("refs/heads/feat/x", "0" * 40, 0),
        ("refs/heads/feat/x", "000", 1),
        ("refs/heads/feat/x", "0" * 39, 1),
        ("refs/heads/feat/x", f"{'0' * 39}1", 1),
        ("refs/heads/feat/x", "0" * 41, 0),
    ],
)
def test_delete_requires_delete_marker_or_a_full_zero_sha(
    local_ref: str,
    local_sha: str,
    expected_returncode: int,
) -> None:
    """G1 P2: 짧거나 비영인 SHA가 삭제 판정을 fail-open하지 못하게 한다."""
    result = call("qb_ref_is_delete", local_ref, local_sha)

    assert result.returncode == expected_returncode


def test_sourcing_defines_all_predicates_and_verdict() -> None:
    """양성 대조: 진짜 라이브러리를 소싱해 여섯 함수를 모두 찾는다."""
    functions = [
        "qb_ref_is_protected",
        "qb_ref_is_head_ref",
        "qb_ref_is_tag_ref",
        "qb_ref_is_whitelisted",
        "qb_ref_is_delete",
        "qb_push_ref_verdict",
    ]
    result = subprocess.run(
        [
            "sh",
            "-c",
            '. "$1"; shift; for fn do type "$fn" >/dev/null || exit 1; done',
            "x",
            str(LIB),
            *functions,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0


def test_sourcing_is_safe_under_sh_e_when_predicate_returns_false() -> None:
    """sh -e에서도 소싱은 끝나고, 음성 술어의 1만 반환한다."""
    script = '. "$1"; shift; qb_ref_is_whitelisted "$@"'
    result = subprocess.run(
        ["sh", "-e", "-c", script, "x", str(LIB), "refs/heads/wip-x"],
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 1
    assert "syntax" not in result.stderr.lower()
