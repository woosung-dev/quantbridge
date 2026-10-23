"""프로세스 재시작·ACK 유실·hold checkpoint. DB·거래소·작업큐를 사용하지 않는다."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.strategy.code_contract import CodeSnapshot
from src.strategy.code_live_replay import replay_code_intents
from src.strategy.code_runtime.models import CodeRuntimeError
from src.trading.services.code_evaluation_service import FLAT, CodeEvaluationService

START = datetime(2026, 1, 1, tzinfo=UTC)


def code():
    return CodeSnapshot(
        execution_policy="code_v1",
        language="python",
        source_code="source",
        warmup_bars=2,
        params={},
        provenance={},
    )


def bars(count):
    return [
        {
            "timestamp": (START + timedelta(hours=index)).isoformat(),
            "open": "100",
            "high": "102",
            "low": "99",
            "close": "101",
            "volume": "20",
        }
        for index in range(count)
    ]


class Transport:
    def __init__(self, seen, action="hold"):
        self.seen, self.action, self.closed = seen, action, False

    def exchange(self, value):
        if value["type"] == "init":
            return {"ready": 1}
        self.seen.append(value)
        return {"intent": {"action": self.action if value["bar"]["index"] >= 2 else "hold"}}

    def close(self):
        self.closed = True


def fixture(action="hold"):
    rows, seen = [], []
    repo, coordinator = AsyncMock(), AsyncMock()
    repo.history.side_effect = lambda _: list(rows)
    repo.add.side_effect = lambda row: rows.append(row)

    async def delivered(identifier):
        next(row for row in rows if row.id == identifier).status = "delivered"

    repo.delivered.side_effect = delivered
    svc = CodeEvaluationService(
        repo, coordinator, transport_factory=lambda: Transport(seen, action)
    )
    args = {
        "session_id": uuid4(),
        "code": code(),
        "bars": bars(3),
        "position": dict(FLAT),
        "activated_at": START + timedelta(hours=2, minutes=5),
        "now": START + timedelta(hours=3),
        "interval_seconds": 3600,
    }
    return svc, repo, coordinator, rows, seen, args


@pytest.mark.asyncio
async def test_hold_bars_persist_before_delivery_and_commit_once_per_stage():
    svc, repo, coordinator, rows, _, args = fixture()

    async def check_order(*_args, **_kwargs):
        assert len(rows) == 3
        assert rows[-1].status == "prepared"
        repo.commit.assert_awaited_once()

    coordinator.on_intent.side_effect = check_order
    assert await svc.evaluate(**args) == "hold"
    assert [row.status for row in rows] == ["warmup", "warmup", "delivered"]
    assert repo.commit.await_count == 2
    coordinator.on_intent.assert_awaited_once()
    await svc.evaluate(**args)
    assert coordinator.on_intent.await_count == 1


@pytest.mark.asyncio
async def test_restart_replays_actual_position_timeline_not_current_position_everywhere():
    svc, repo, coordinator, rows, seen, args = fixture("long")
    await svc.evaluate(**args)
    seen.clear()
    # 새 service가 새 실행기를 만들고 봉별로 관찰했던 실제 포지션만 재주입한다.
    restarted = CodeEvaluationService(
        repo, coordinator, transport_factory=lambda: Transport(seen, "long")
    )
    args.update(
        bars=bars(4),
        now=START + timedelta(hours=4),
        position={"direction": "long", "size": "0.5", "average_price": "101"},
    )
    await restarted.evaluate(**args)
    assert [request["position"]["direction"] for request in seen] == [
        "flat",
        "flat",
        "flat",
        "long",
    ]
    assert rows[-1].position["size"] == "0.5"
    assert coordinator.on_intent.await_count == 2


@pytest.mark.asyncio
async def test_ack_loss_retries_same_intent_key_and_frozen_quantity():
    svc, repo, coordinator, rows, _, args = fixture("long")
    args["execution_args"] = {"quantity": Decimal("0.5"), "estimated_entry": Decimal("101")}
    coordinator.on_intent.side_effect = RuntimeError("ACK lost")
    with pytest.raises(RuntimeError, match="ACK lost"):
        await svc.evaluate(**args)
    assert rows[-1].status == "prepared"
    assert repo.commit.await_count == 1
    first = coordinator.on_intent.call_args
    coordinator.on_intent.side_effect = None
    args.update(
        position={"direction": "long", "size": "0.5", "average_price": "101"},
        execution_args={"quantity": Decimal("99")},
    )
    await svc.evaluate(**args)
    assert coordinator.on_intent.call_args == first
    assert rows[-1].status == "delivered"
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_expired_prepared_entry_cannot_become_fresh_order():
    svc, _, coordinator, rows, _, args = fixture("long")
    coordinator.on_intent.side_effect = RuntimeError("delivery failed")
    with pytest.raises(RuntimeError):
        await svc.evaluate(**args)
    args.update(bars=bars(5), now=START + timedelta(hours=5))
    coordinator.on_intent.side_effect = None
    with pytest.raises(CodeRuntimeError, match="오래된 진입"):
        await svc.evaluate(**args)
    assert rows[-1].status == "prepared" and coordinator.on_intent.await_count == 1


@pytest.mark.asyncio
async def test_unobserved_gap_rejects_without_synthetic_position_or_delivery():
    svc, _repo, coordinator, rows, _, args = fixture()
    await svc.evaluate(**args)
    args.update(bars=bars(5), now=START + timedelta(hours=5))
    with pytest.raises(CodeRuntimeError, match="봉 공백"):
        await svc.evaluate(**args)
    assert len(rows) == 3 and coordinator.on_intent.await_count == 1


@pytest.mark.asyncio
async def test_input_tamper_and_changed_intent_fail_closed():
    svc, _, coordinator, rows, _, args = fixture()
    await svc.evaluate(**args)
    rows[0].position = {"direction": "long", "size": "1", "average_price": "100"}
    with pytest.raises(CodeRuntimeError, match="해시"):
        replay_code_intents(code(), rows, transport_factory=lambda: Transport([]))
    rows[0].position = dict(FLAT)
    with pytest.raises(CodeRuntimeError, match="의도"):
        replay_code_intents(code(), rows, transport_factory=lambda: Transport([], "long"))
    assert coordinator.on_intent.await_count == 1


@pytest.mark.asyncio
async def test_missing_image_does_not_save_checkpoint_or_dispatch():
    svc, repo, coordinator, rows, _, args = fixture()

    def unavailable():
        raise CodeRuntimeError("image unavailable")

    svc.transport_factory = unavailable
    with pytest.raises(CodeRuntimeError, match="image unavailable"):
        await svc.evaluate(**args)
    assert rows == []
    repo.commit.assert_not_awaited()
    coordinator.on_intent.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["nonflat", "warmup", "future", "modified"])
async def test_initial_or_historical_input_boundaries(change):
    svc, _, coordinator, _, _, args = fixture()
    if change == "nonflat":
        args["position"] = {"direction": "long", "size": "1", "average_price": "100"}
    elif change == "warmup":
        args["bars"] = bars(3)[1:]
    elif change == "future":
        args["now"] = START + timedelta(hours=2, minutes=59)
    else:
        await svc.evaluate(**args)
        args["bars"][0]["close"] = "100"
    with pytest.raises(CodeRuntimeError):
        await svc.evaluate(**args)
    assert coordinator.on_intent.await_count == (1 if change == "modified" else 0)
