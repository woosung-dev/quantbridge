"""TaskDispatcher 구현체 테스트."""
from __future__ import annotations

from uuid import uuid4

import pytest

from src.backtest.dispatcher import (
    FakeTaskDispatcher,
    NoopTaskDispatcher,
)


class TestNoopTaskDispatcher:
    def test_raises_on_dispatch(self) -> None:
        d = NoopTaskDispatcher()
        with pytest.raises(RuntimeError, match="must not dispatch"):
            d.dispatch_backtest(uuid4())


class TestFakeTaskDispatcher:
    def test_returns_fixed_id(self) -> None:
        d = FakeTaskDispatcher(task_id="fake-task-42")
        assert d.dispatch_backtest(uuid4()) == "fake-task-42"

    def test_records_calls(self) -> None:
        d = FakeTaskDispatcher()
        id1, id2 = uuid4(), uuid4()
        d.dispatch_backtest(id1)
        d.dispatch_backtest(id2)
        assert d.dispatched == [id1, id2]
