# CI backend 잡의 pytest 샤드 경계 — `tests/shards.json` 을 pytest 인자로 펼친다.
"""샤드 정의(`tests/shards.json`)의 유일한 소비자.

★**왜 쪼개나.** CI backend 잡 23분 중 pytest 한 스텝이 **1313s(94%)** 다. 커버리지 계측만
떼면(실측 배율 **1.770배** — 로컬 무계측 298.97s vs 계측 529.16s) ~9.3분이 빠지지만,
BL-308/309 의 trading money-path 래칫은 **full suite 로 측정한 transitive 커버**를 요구하므로
계측을 없앨 수 없다. 그래서 계측을 **끄는 대신 병렬로 쪼갠다** — 샤드마다 부분 커버리지
데이터를 남기고 `coverage combine` 으로 합치면 래칫이 재는 값은 **정확히 같다**(합집합).

★**경계는 추측이 아니라 실측이다.** `pytest --durations=0` 전수 측정 결과 `tests/strategy/pine_v2`
혼자 로컬 **164.0s / 56.3%** 였고, CI 는 CPU 바운드 구간이 **5.0배**(스위트 평균 4.27배)라
CI 기준으로는 `tests/strategy` 가 **~837s / 1278s** 다. 그래서 샤드 `b` 는 파일 **두 개**뿐이다 —
그 두 파일이 스위트의 35% 이기 때문이지 편의가 아니다.

★**여기서 균형을 손보면 `tests/test_pytest_shard_partition.py` 가 잡는다** — 모든
`test_*.py` 가 **정확히 한 샤드**에 속하는지, `ci.yml` matrix 의 id 집합이 이 파일의 키와
같은지를 강제한다. 열거식 배선이 조용히 새는 것을 이 레포는 이미 두 번 밟았다
(playwright `testMatch` · `text.index("uv run pytest")`).

사용:
    uv run python -m tests.shard_paths a
    # → tests/strategy --ignore=tests/strategy/pine_v2/test_alert_hook.py --ignore=...
"""

from __future__ import annotations

import json
import pathlib
import sys

SHARDS_JSON = pathlib.Path(__file__).resolve().parent / "shards.json"


def load_shards() -> dict[str, dict[str, list[str]]]:
    """`shards.json` 을 읽어 `{shard_id: {"paths": [...], "ignore": [...]}}` 로 준다."""
    raw = json.loads(SHARDS_JSON.read_text())
    out: dict[str, dict[str, list[str]]] = {}
    for shard_id, spec in raw.items():
        out[shard_id] = {
            "paths": list(spec.get("paths", [])),
            "ignore": list(spec.get("ignore", [])),
        }
    return out


def pytest_args(shard_id: str) -> list[str]:
    """샤드 하나의 pytest 위치인자 + `--ignore` 플래그.

    ★출력은 **공백으로 이어 붙여** 셸의 word-splitting 으로 펼쳐진다(`ci.yml`). 그래서
    경로에 공백이 있으면 인자가 조용히 쪼개진다 — 여기서 거부해 그 가정을 집행한다.
    (CI 는 bash 라 split 되지만 **zsh 는 기본적으로 안 한다** — 로컬에서 이 스크립트를
    검증할 땐 반드시 `bash -c` 로 돌려라. 실측으로 한 번 속았다.)
    """
    shards = load_shards()
    if shard_id not in shards:
        raise SystemExit(
            f"알 수 없는 샤드 id: {shard_id!r} — 아는 것: {sorted(shards)}. "
            f"정의는 {SHARDS_JSON} 에 있다."
        )
    spec = shards[shard_id]
    # ★빈 `paths` 는 「아무것도 안 돈다」가 아니라 **전체 스위트 재실행**이다 (codex P2).
    #   위치인자가 없으면 pytest 가 `pyproject.toml` 의 `testpaths = ["tests"]` 로 떨어져
    #   그 샤드가 조용히 full suite 를 한 번 더 돈다. 분할 감사는 선언 JSON 만 보므로
    #   빈 샤드를 고아로 세지 못한다 — 그래서 여기서 거부한다.
    if not spec["paths"]:
        raise SystemExit(
            f"샤드 {shard_id!r} 의 paths 가 비었다 — 위치인자 없이 pytest 를 부르면 "
            f"testpaths 기본값으로 **전체 스위트**가 다시 돈다. {SHARDS_JSON} 를 고쳐라."
        )
    args = [*spec["paths"], *(f"--ignore={p}" for p in spec["ignore"])]
    bad = [a for a in args if a != "".join(a.split())]
    if bad:
        raise SystemExit(f"샤드 경로에 공백이 있다 — word-splitting 이 깨진다: {bad}")
    return args


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            f"사용법: python -m tests.shard_paths <{'|'.join(sorted(load_shards()))}>",
            file=sys.stderr,
        )
        return 2
    print(" ".join(pytest_args(argv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
