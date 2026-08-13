# CI pytest 샤드 분할이 **전수·무중복**인지 감사한다 — 열거식 배선의 조용한 누락 차단.
"""샤드 분할 감사 — `tests/shards.json` 이 모든 테스트 파일을 정확히 한 번 덮는가.

★**왜 필요한가.** CI backend 잡을 3 샤드로 쪼개면서 「어떤 테스트가 어느 샤드에 속하는가」가
**열거식 목록**이 됐다. 이 레포는 열거식 배선이 조용히 새는 것을 이미 두 번 밟았다 —
⑴ playwright `chromium-authed` 의 파일명 열거 `testMatch`(고아 spec 이 발견조차 안 됐다)
⑵ `test_ci_workflow_env_parity.py` 의 `text.index("uv run pytest")`(첫 매치만 봤다).
샤드에서 같은 일이 나면 **테스트가 아무 샤드에서도 안 돌면서 CI 는 초록**이다. 커버리지
래칫도 그만큼 낮아지지만 `--fail-under=90` 아래로 안 내려가면 아무도 모른다.

★**그래서 판정은 「개수」가 아니라 「무엇이」다.** 파일 하나하나에 대해 소유 샤드 집합을
구해 **정확히 1** 인지 본다. 0 이면 미실행, 2 이상이면 중복 실행(커버리지는 맞지만 시간 낭비).

관련: `tests/shard_paths.py`(샤드 정의의 유일한 소비자) · `.github/workflows/ci.yml`(matrix).
"""
from __future__ import annotations

import pathlib
import re

import pytest

from tests.shard_paths import SHARDS_JSON, load_shards, pytest_args

_TESTS_DIR = pathlib.Path(__file__).resolve().parent
_BACKEND = _TESTS_DIR.parent
_WORKFLOW = _BACKEND.parent.parent / ".github" / "workflows" / "ci.yml"


def _all_test_files() -> set[str]:
    """`apps/api/` 기준 상대경로로 `tests/` 아래 모든 `test_*.py`."""
    return {
        str(p.relative_to(_BACKEND))
        for p in _TESTS_DIR.rglob("test_*.py")
        if "__pycache__" not in p.parts
    }


def _is_under(path: str, base: str) -> bool:
    """`path` 가 `base`(파일 또는 디렉터리) 안인가."""
    return path == base or path.startswith(base.rstrip("/") + "/")


def _owners(path: str, shards: dict[str, dict[str, list[str]]]) -> list[str]:
    """그 파일을 실제로 실행하는 샤드 id 목록."""
    out = []
    for shard_id, spec in shards.items():
        if not any(_is_under(path, b) for b in spec["paths"]):
            continue
        if any(_is_under(path, b) for b in spec["ignore"]):
            continue
        out.append(shard_id)
    return out


def test_every_test_file_belongs_to_exactly_one_shard() -> None:
    """★본 판정 — 미실행(0개) 도 중복실행(2개 이상) 도 허용하지 않는다."""
    shards = load_shards()
    files = _all_test_files()

    orphans = sorted(f for f in files if len(_owners(f, shards)) == 0)
    duplicates = sorted(
        (f, _owners(f, shards)) for f in files if len(_owners(f, shards)) > 1
    )

    assert not orphans, (
        f"어느 샤드에서도 안 도는 테스트 파일 {len(orphans)}개 — CI 는 초록인데 실행이 안 된다:\n"
        + "\n".join(f"  {f}" for f in orphans)
        + f"\n\n{SHARDS_JSON} 의 paths 에 추가해라."
    )
    assert not duplicates, (
        "두 샤드 이상에서 중복 실행되는 파일:\n"
        + "\n".join(f"  {f} → {owners}" for f, owners in duplicates)
    )


def test_emitted_pytest_args_carry_every_declared_ignore() -> None:
    """★CI 가 실제로 쓰는 것은 선언 JSON 이 아니라 `pytest_args()` 의 출력이다.

    ★codex P2 로 교체된 판정. 앞선 음성 대조는 `ignore` 배제를 `_owners()` 로 확인했는데,
    `_owners()` 자체가 「ignore 는 제외한다」로 정의돼 있어 **같은 구현에 두 번 묻는
    tautology** 였다 — `pytest_args()` 가 `--ignore=` 를 빼먹어도 통과했다.
    여기서는 CI 스텝에 들어가는 문자열을 직접 본다.
    """
    for shard_id, spec in load_shards().items():
        args = pytest_args(shard_id)
        assert args, f"{shard_id}: 인자가 비었다 — pytest 가 전체 스위트로 떨어진다"
        for ignored in spec["ignore"]:
            assert f"--ignore={ignored}" in args, (
                f"{shard_id}: 선언된 ignore 가 인자에 없다 → {ignored}\n"
                f"실제 인자: {args}\n"
                "이러면 그 파일이 두 샤드에서 중복 실행된다."
            )
        for path in spec["paths"]:
            assert path in args, f"{shard_id}: 선언된 path 가 인자에 없다 → {path}"


def test_no_shard_declares_empty_paths() -> None:
    """★빈 `paths` 는 「안 돈다」가 아니라 **전체 스위트 재실행**이다 (codex P2).

    위치인자 없이 pytest 를 부르면 `pyproject.toml` 의 `testpaths = ["tests"]` 로 떨어진다.
    분할 감사는 빈 샤드를 고아로 세지 못하므로(아무 파일도 소유하지 않을 뿐이다) 별도로 막는다.
    """
    for shard_id, spec in load_shards().items():
        assert spec["paths"], (
            f"샤드 {shard_id!r} 의 paths 가 비었다 — 그 샤드가 조용히 전체 스위트를 다시 돈다"
        )


def test_shard_entries_all_exist_on_disk() -> None:
    """★경로 오타 = 조용한 누락. `paths`/`ignore` 항목이 실재하는지 본다.

    존재하지 않는 경로를 `paths` 에 적으면 pytest 가 그 인자에서 죽고, `ignore` 에 적으면
    **아무것도 제외하지 않은 채 조용히 통과**한다(후자가 위험하다).
    """
    missing: list[str] = []
    for shard_id, spec in load_shards().items():
        for key in ("paths", "ignore"):
            for entry in spec[key]:
                if not (_BACKEND / entry).exists():
                    missing.append(f"{shard_id}.{key}: {entry}")
    assert not missing, "shards.json 이 없는 경로를 가리킨다:\n" + "\n".join(missing)


def test_ci_matrix_shard_ids_match_shards_json() -> None:
    """★`ci.yml` matrix 와 `shards.json` 이 갈라지면 샤드 하나가 통째로 안 돈다."""
    if not _WORKFLOW.exists():  # 워크플로 없는 체크아웃
        pytest.skip("워크플로 파일이 없는 체크아웃")

    text = _WORKFLOW.read_text()
    m = re.search(r"^\s*shard:\s*\[([^\]]*)\]", text, re.M)
    assert m, "ci.yml 에서 `shard: [...]` matrix 를 못 찾았다 — 배선이 바뀌었는지 확인해라"
    matrix_ids = {tok.strip().strip("\"'") for tok in m.group(1).split(",") if tok.strip()}

    assert matrix_ids == set(load_shards()), (
        f"ci.yml matrix={sorted(matrix_ids)} 와 shards.json={sorted(load_shards())} 가 다르다"
    )


def test_partition_audit_detects_anything_at_all() -> None:
    """★음성 대조 — 수집 로직이 죽으면 위 판정들이 **항상 통과**한다.

    이 레포는 「가드가 판별력을 증명하지 못한 채 초록」을 반복해서 밟았다. 그래서 워커가
    실제로 파일을 찾는지, 그리고 소유자 판정이 실제로 무언가를 배제하는지 둘 다 고정한다.
    """
    files = _all_test_files()
    assert len(files) > 100, f"테스트 파일 탐지가 {len(files)}개 — 워커가 죽었다"
    assert "tests/test_pytest_shard_partition.py" in files, "자기 자신을 못 찾는다"
