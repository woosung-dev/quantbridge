# 완료된 Backtest 재실행 입력 판정(rerun_input) 의 interface 테스트 — DB 없이 fake repo 로 잰다
"""stress_test · optimizer 가 함께 쓰는 판정부를 한 곳에서 고정한다.

호출자별 표면(예외 타입·문구·로그명)은 각 도메인 테스트가 고정한다
(tests/stress_test/test_execute_rerun_input.py · tests/optimizer/test_execute_rerun_input.py).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from src.backtest.engine import PINE_V2_ENGINE_VERSION
from src.backtest.rerun_input import (
    RerunSourceUnavailable,
    is_rerunnable_engine_version,
    resolve_pinned_pine_source,
)

_PINNED = "//@version=5\n// pinned snapshot"
_CURRENT = "//@version=5\n// current strategy"


def _source(pine_source: str) -> SimpleNamespace:
    # MagicMock 은 execution_policy 가 non-None 이라 legacy_pine_source 가 code 정책으로 거부한다.
    return SimpleNamespace(pine_source=pine_source, execution_policy=None)


class _FakeStrategyRepo:
    """호출 순서를 `events` 에 남긴다 — 경고 콜백과 fallback 조회의 선후를 재기 위해서다."""

    def __init__(self, *, version: Any, strategy: Any, events: list[Any]) -> None:
        self._version = version
        self._strategy = strategy
        self._events = events

    async def get_version_by_id(self, version_id: Any, *, strategy_id: Any) -> Any:
        self._events.append(("get_version_by_id", version_id, strategy_id))
        return self._version

    async def find_by_id_and_owner(self, strategy_id: Any, owner_id: Any) -> Any:
        self._events.append(("find_by_id_and_owner", strategy_id, owner_id))
        return self._strategy


def _bt(*, pinned: bool) -> Any:
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        strategy_version_id=uuid4() if pinned else None,
    )


async def _resolve(bt: Any, *, version: Any, strategy: Any) -> tuple[Any, list[Any]]:
    events: list[Any] = []
    repo = _FakeStrategyRepo(version=version, strategy=strategy, events=events)
    outcome = await resolve_pinned_pine_source(
        bt,
        repo,  # type: ignore[arg-type]
        on_legacy_fallback=lambda: events.append("legacy_fallback"),
    )
    return outcome, events


async def test_pinned_version_found_returns_snapshot_without_fallback() -> None:
    bt = _bt(pinned=True)

    outcome, events = await _resolve(bt, version=_source(_PINNED), strategy=_source(_CURRENT))

    assert outcome == _PINNED
    assert events == [("get_version_by_id", bt.strategy_version_id, bt.strategy_id)]


async def test_pinned_version_missing_never_falls_back_to_current_strategy() -> None:
    bt = _bt(pinned=True)

    outcome, events = await _resolve(bt, version=None, strategy=_source(_CURRENT))

    assert outcome is RerunSourceUnavailable.STRATEGY_VERSION_MISSING
    assert events == [("get_version_by_id", bt.strategy_version_id, bt.strategy_id)]


async def test_legacy_row_warns_before_falling_back_to_current_strategy() -> None:
    bt = _bt(pinned=False)

    outcome, events = await _resolve(bt, version=None, strategy=_source(_CURRENT))

    assert outcome == _CURRENT
    assert events == [
        ("get_version_by_id", None, bt.strategy_id),
        "legacy_fallback",
        ("find_by_id_and_owner", bt.strategy_id, bt.user_id),
    ]


async def test_legacy_row_with_missing_strategy_still_warns() -> None:
    bt = _bt(pinned=False)

    outcome, events = await _resolve(bt, version=None, strategy=None)

    assert outcome is RerunSourceUnavailable.STRATEGY_MISSING
    assert "legacy_fallback" in events


@pytest.mark.parametrize(
    ("engine_version", "expected"),
    [
        (None, True),
        (PINE_V2_ENGINE_VERSION, True),
        ("code_v1", False),
        ("", False),
    ],
)
def test_is_rerunnable_engine_version(engine_version: str | None, expected: bool) -> None:
    bt: Any = SimpleNamespace(engine_version=engine_version)

    assert is_rerunnable_engine_version(bt) is expected
