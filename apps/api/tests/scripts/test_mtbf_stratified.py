"""층화 도구가 원장을 읽는 방식을 못박는다 — [BL-641].

## 왜 이 파일이 필요한가

`mtbf_stratified.py` 는 자기 안에 `self-check` 를 들고 있지만 그건 **입력 원장이 있을 때만**
돈다(CI 에는 DB 가 없다). 그리고 self-check 이 지키는 것은 「계산법이 안 바뀌었나」이지
「원장을 읽는 규칙이 관대해지지 않았나」가 아니다.

★★★이 도구는 게이트가 **아니지만** 게이트의 결론(「MTBF 가 병목이다」)을 뒷받침하는 숫자를
낸다. 그래서 관대해지는 경로는 여기도 똑같이 막아야 한다 — 원장을 지우거나 망가뜨려서
MTBF 를 좋게 만드는 길이 없어야 한다.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest


def _load_module() -> Any:
    """도구 모듈 동적 import (`tests/scripts` 선례 — `sys.path` 오염 회피)."""
    scripts_dir = Path(__file__).parents[2] / "scripts"
    sys.path.insert(0, str(scripts_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "mtbf_stratified", scripts_dir / "mtbf_stratified.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(scripts_dir))


@pytest.fixture(scope="module")
def tool() -> Any:
    return _load_module()


OPERATIONAL_ROW = (
    '{"at": "2026-08-07T15:10:49.561534+00:00", "kind": "auto_death", '
    '"session": "39484a2c", "cause_class": "operational", "evidence": "BL-633"}'
)


def test_an_operational_death_is_excluded(tool: Any, tmp_path: Path) -> None:
    """원장이 판정한 운영 사고 세션만 집합에 들어간다."""
    ledger = tmp_path / "led.jsonl"
    ledger.write_text(OPERATIONAL_ROW + "\n")
    assert tool.load_operational_sessions(ledger) == {"39484a2c"}


@pytest.mark.parametrize(
    "line",
    [
        pytest.param(
            OPERATIONAL_ROW.replace('"operational"', '"undecided"'),
            id="undecided 는 빼지 않는다",
        ),
        pytest.param(
            OPERATIONAL_ROW.replace('"operational"', '"code_defect"'),
            id="code_defect 는 빼지 않는다",
        ),
        pytest.param(
            OPERATIONAL_ROW.replace('"auto_death"', '"phantom"'),
            id="phantom 은 세션 사망이 아니다",
        ),
        pytest.param(
            OPERATIONAL_ROW.replace('"auto_death"', '"tick_stall"'),
            id="tick_stall 도 세션 사망이 아니다",
        ),
        pytest.param('{"_comment": "설명 행"}', id="주석 행"),
        pytest.param("{깨진 json", id="판독 불가"),
        pytest.param('{"kind": "auto_death", "cause_class": "operational"}', id="세션 누락"),
    ],
)
def test_nothing_else_buys_an_exclusion(tool: Any, tmp_path: Path, line: str) -> None:
    """★fail-open 봉쇄 — `auto_death` + `operational` 이 **동시에** 아니면 안 빠진다.

    이 파라미터 목록이 곧 「관대해지는 경로」의 전수다. 하나라도 통과하면 원장을
    적당히 써서 MTBF 를 좋게 만들 수 있다.
    """
    ledger = tmp_path / "led.jsonl"
    ledger.write_text(line + "\n")
    assert tool.load_operational_sessions(ledger) == set()


def test_a_missing_ledger_excludes_nothing(tool: Any, tmp_path: Path) -> None:
    """★원장을 **지우는 것**이 가장 싼 공격이다 — 없으면 아무것도 안 빠진다."""
    assert tool.load_operational_sessions(tmp_path / "없다.jsonl") == set()
    assert tool.load_operational_sessions(None) == set()


def _rows(tool: Any) -> list[dict[str, Any]]:
    text = "\n".join(
        [
            "39484a2c-0000-4000-8000-000000000001|2026-08-07 09:39:38+00"
            "|2026-08-07 15:10:49+00|position_divergence",
            "c160a1a9-0000-4000-8000-000000000002|2026-08-06 01:06:46+00"
            "|2026-08-06 20:31:48+00|gap_resync_position_mismatch",
        ]
    )
    return tool.parse_rows(text, tool._dt("2026-08-08T00:00:00+00:00"))


def test_exposure_survives_the_exclusion(tool: Any) -> None:
    """★운영 사고는 **사망에서만** 빠진다 — 노출은 그대로 남는다.

    노출까지 빼면 「그 시간엔 코드가 안 돌았다」가 되는데 그건 거짓이다. 그리고 노출을
    빼면 MTBF 가 **양쪽으로** 틀어져 어느 방향이 안전한지도 말할 수 없다.
    """
    rows = _rows(tool)
    base = tool.summarize(rows, "전 이력", None, "")
    excluded = tool.summarize(rows, "제외", None, "", {"39484a2c"})

    assert base["deaths"] == 2
    assert excluded["deaths"] == 1
    assert excluded["exposure"] == pytest.approx(base["exposure"])
    assert excluded["operational_dropped"] == 1
    assert excluded["censored"] == base["censored"] + 1


def test_an_empty_exclusion_set_changes_nothing(tool: Any) -> None:
    """빈 집합을 넘긴 층은 안 넘긴 층과 **같은 값**이다 — 새 인자가 기존 결과를 안 흔든다."""
    rows = _rows(tool)
    assert tool.summarize(rows, "a", None, "") == tool.summarize(rows, "a", None, "", set())


def test_the_shipped_ledger_names_a_real_session(tool: Any) -> None:
    """레포 원장이 지목하는 세션이 8자 접두사 규약을 지키는지.

    ★원장은 사람이 쓰고 `parse_rows` 는 `id[:8]` 로 자른다. 규약이 갈리면 매칭이 조용히
      0 건이 되고, 그러면 이 층은 **아무것도 안 빼면서** 있는 척한다.
    """
    sessions = tool.load_operational_sessions(tool.LEDGER_DEFAULT)
    assert sessions, "레포 원장에 운영 사고 판정이 하나도 없다"
    for session in sessions:
        assert len(session) == 8, session
