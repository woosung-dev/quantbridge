"""슬롯 DB의 제품 service 여정. 거래소·언어 transport·Celery는 명시적 fake다."""

from datetime import timedelta
from decimal import Decimal as D
from unittest.mock import AsyncMock

import pytest

from src.strategy.code_contract import CodeSnapshot, read_code_version
from src.strategy.code_schemas import SaveCodeStrategyRequest
from src.strategy.code_service import CodeStrategyService
from src.strategy.repository import StrategyRepository
from src.strategy.schemas import StrategySettings
from src.trading.code_price_rules import protection_prices
from src.trading.models import ExchangeAccount, ExchangeMode, ExchangeName, OrderSide, OrderType
from src.trading.providers import Credentials, OrderReceipt, OrderStatusFetch, PositionInfo
from src.trading.repositories.code_checkpoint_repository import CodeCheckpointRepository
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.repositories.order_repository import OrderRepository
from src.trading.schemas import RegisterLiveSessionRequest
from src.trading.services.code_evaluation_service import FLAT, CodeEvaluationService
from src.trading.services.code_live_execution_service import CodeLiveExecutionService
from src.trading.services.code_risk_executor import CodeRiskExecutor
from src.trading.services.code_risk_service import CodeRiskService
from src.trading.services.code_risk_venue import BybitCodeRiskVenue
from src.trading.services.live_session_service import LiveSignalSessionService

SOURCE = """def on_bar(ctx, state):
    index = ctx['bar']['index']
    action = 'long' if index == 2 else 'short' if index in (4,5) else 'close' if index == 6 else 'hold'
    return {'action': action}
"""


class ScriptedTransport:
    """소스를 호스트에서 실행하지 않는다. sandbox 실제 실행 검증은 별도 스위트다."""

    def exchange(self, value):
        if value["type"] == "init":
            assert value["source"] == SOURCE
            return {"ready": 1}
        index = value["bar"]["index"]
        return {
            "intent": {
                "action": "long"
                if index == 2
                else "short"
                if index in (4, 5)
                else "close"
                if index == 6
                else "hold"
            }
        }

    def close(self):
        pass


class FakeBybit:
    def __init__(self):
        self.statuses = {}
        self.signed = D(0)
        self.average = D("100.05")
        self.submissions = []
        self.protection = []

    async def get_code_market_rules(self, *_):
        return {"price_tick": D("0.1"), "qty_step": D("0.1"), "min_qty": D("0.1")}

    async def fetch_order_by_client_id(self, _credentials, identifier, _symbol):
        return self.statuses.get(identifier)

    async def fetch_order(self, _credentials, identifier, _symbol):
        return self.statuses[identifier]

    async def create_order(self, _credentials, request):
        self.submissions.append(request)
        identifier = request.client_order_id
        if request.type == OrderType.limit:
            status = OrderStatusFetch(
                exchange_order_id=identifier, status="submitted", filled_quantity=D(0)
            )
        else:
            sign = D(1) if request.side == OrderSide.buy else D(-1)
            assert not request.reduce_only or sign * self.signed < 0
            self.signed += sign * request.quantity
            status = OrderStatusFetch(
                exchange_order_id=identifier,
                status="filled",
                filled_price=self.average,
                filled_quantity=request.quantity,
                raw={"info": {"cumExecValue": str(self.average * request.quantity)}},
            )
        self.statuses[identifier] = status
        return OrderReceipt(
            exchange_order_id=identifier,
            status=status.status,
            filled_price=status.filled_price,
            filled_quantity=status.filled_quantity,
            raw=status.raw,
        )

    async def cancel_order(self, _credentials, identifier, _symbol):
        previous = self.statuses[identifier]
        self.statuses[identifier] = OrderStatusFetch(
            exchange_order_id=identifier,
            status="cancelled",
            filled_price=previous.filled_price,
            filled_quantity=previous.filled_quantity,
        )

    async def fetch_position(self, *_):
        return (
            PositionInfo(size=abs(self.signed), side="long" if self.signed > 0 else "short")
            if self.signed
            else None
        )

    async def fetch_open_conditional_orders(self, *_):
        return []

    async def set_code_protection(self, _credentials, **values):
        applied = protection_prices(
            direction=values["direction"],
            entry_price=values["entry_price"],
            stop_loss=values["stop_loss"],
            tick=D("0.1"),
            distance=values["distance"],
            activation=values["active_price"],
            breakeven_required=values["breakeven_required"],
        )
        applied.update(
            accepted=True,
            verified_stop_loss=applied["stop_loss"],
            active_price_readback_available=False,
        )
        self.protection.append(applied)
        return applied


@pytest.mark.asyncio
@pytest.mark.parametrize("native", [False, True], ids=["fake_protocol", "native_python"])
async def test_source_snapshot_checkpoints_and_risk_survive_delivery_ack_loss(
    db_session, user, monkeypatch, request, native
):
    if native and not request.config.getoption("--run-integration"):
        pytest.skip("native gVisor 여정은 --run-integration과 명시 Docker endpoint로 실행합니다")

    launched = []

    def factory():
        if native:
            from src.strategy.code_runtime.sandbox import create_transport

            transport = create_transport("python", timeout=30)
            launched.append({"name": transport.name, "image_id": transport.image_id})
            return transport
        return ScriptedTransport()

    strategy_repo = StrategyRepository(db_session)
    storage = CodeStrategyService(strategy_repo)
    code = CodeSnapshot(
        execution_policy="code_v1",
        language="python",
        source_code=SOURCE,
        warmup_bars=2,
        params={},
        provenance={"provider": "test"},
    )
    settings = StrategySettings(
        leverage=1, margin_mode="cross", position_size_pct=20, fill_timing="next_bar_open"
    )
    created = await storage.create(
        SaveCodeStrategyRequest(
            name="journey", symbol="BTC/USDT", timeframe="1h", code=code, settings=settings
        ),
        owner_id=user.id,
    )
    version = await strategy_repo.get_version_by_id(created.version.id, strategy_id=created.id)
    assert version is not None and read_code_version(version).execution_hash == code.execution_hash
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"fake",
        api_secret_encrypted=b"fake",
        read_only=False,
    )
    db_session.add(account)
    await db_session.flush()
    repo = CodeRiskRepository(db_session)
    orders = OrderRepository(db_session)
    risk = CodeRiskService(repo)
    accounts = AsyncMock()
    accounts.get_credentials_for_order.return_value = Credentials("fake", "fake")
    provider = FakeBybit()
    venue = BybitCodeRiskVenue(repo, orders, risk, accounts, provider)
    executor = CodeRiskExecutor(repo, risk, venue)
    balance = AsyncMock()
    balance.get_balance.return_value = type("Balance", (), {"supported": True, "total": D(1000)})()
    monkeypatch.setattr(
        "src.tasks.websocket_task.run_bybit_public_ticker_stream.delay", lambda: None
    )
    sessions = LiveSignalSessionService(
        LiveSignalSessionRepository(db_session),
        ExchangeAccountRepository(db_session),
        strategy_repo,
        balance_service=balance,
        exclusivity_service=AsyncMock(),
        risk_service=risk,
        risk_executor=executor,
    )
    live = await sessions.register(
        user.id,
        RegisterLiveSessionRequest(
            strategy_id=created.id,
            exchange_account_id=account.id,
            symbol="BTC/USDT",
            interval="1h",
            source_policy="code_v1",
            strategy_version_id=version.id,
        ),
    )
    session_id = live.id
    assert live.execution_snapshot["execution_hash"] == code.execution_hash
    assert live.execution_snapshot["sizing_policy"] == "session_initial_equity_percent_v1"
    gate = AsyncMock()
    coordinator = CodeLiveExecutionService(repo, orders, risk, executor, entry_gate=gate)
    checkpoints = CodeCheckpointRepository(db_session)
    evaluator = CodeEvaluationService(checkpoints, coordinator, transport_factory=factory)
    start = live.created_at.replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
    activated = live.created_at
    bars = []
    for index in range(7):
        close = "100" if index < 3 else "106"
        bars.append(
            {
                "timestamp": (start + timedelta(hours=index)).isoformat(),
                "open": close,
                "high": "107",
                "low": "98",
                "close": close,
                "volume": "20",
            }
        )
    # 첫 진입은 완료 2봉 low=98, 추정100→실제VWAP100.05로 R을 확정한다.
    original = checkpoints.delivered

    async def lost_ack(_):
        raise RuntimeError("simulated process loss after external delivery")

    checkpoints.delivered = lost_ack
    args = {
        "estimated_entry": D(100),
        "quantity": D(2),
        "qty_step": D("0.1"),
        "min_qty": D("0.1"),
        "previous_bars": [{"low": D(98), "high": D(107)}, {"low": D(98), "high": D(107)}],
    }
    now = start + timedelta(hours=3, seconds=1)
    with pytest.raises(RuntimeError, match="simulated process loss"):
        await evaluator.evaluate(
            session_id=session_id,
            code=code,
            bars=bars[:3],
            position=FLAT,
            activated_at=activated,
            now=now,
            interval_seconds=3600,
            execution_args=args,
        )
    assert len(provider.submissions) == 2
    state = await repo.get(session_id)
    assert state is not None and state.fixed_r == D("2.255")
    assert state.protection_applied["venue"]["stop_loss"] == "97.7"
    rows = await checkpoints.history(session_id)
    assert rows[-1].status == "prepared" and rows[-1].position == FLAT
    checkpoints.delivered = original
    restarted = CodeEvaluationService(
        CodeCheckpointRepository(db_session), coordinator, transport_factory=factory
    )
    assert (
        await restarted.evaluate(
            session_id=session_id,
            code=code,
            bars=bars[:3],
            position={"direction": "long", "size": "2", "average_price": "100.05"},
            activated_at=activated,
            now=now,
            interval_seconds=3600,
            execution_args={**args, "quantity": D(9)},
        )
        == "long"
    )
    assert len(provider.submissions) == 2
    # 전략의 현재 버전 갱신도 실행 중 세션의 불변 버전을 바꾸지 않는다.
    updated = await storage.update(
        created.id,
        SaveCodeStrategyRequest(name="changed", code=code, settings=settings),
        owner_id=user.id,
    )
    assert updated.version.id != version.id
    pinned = await repo.get_session(session_id)
    assert pinned.strategy_version_id == version.id
    tp = provider.submissions[1]
    assert tp.price == D("103.5") and tp.quantity == D(1)
    provider.signed = D(1)
    provider.statuses[tp.client_order_id] = OrderStatusFetch(
        exchange_order_id=tp.client_order_id,
        status="filled",
        filled_price=tp.price,
        filled_quantity=D(1),
    )
    await executor.drain(session_id)
    assert (
        await restarted.evaluate(
            session_id=session_id,
            code=code,
            bars=bars[:4],
            position={"direction": "long", "size": "1", "average_price": "100.05"},
            activated_at=activated,
            now=start + timedelta(hours=4, seconds=1),
            interval_seconds=3600,
            execution_args={**args, "estimated_entry": D(106)},
        )
        == "hold"
    )
    state = await repo.get(session_id)
    assert (
        state.trailing_active
        and D(state.protection_applied["venue"]["stop_loss"]) >= provider.average
    )
    assert (
        await restarted.evaluate(
            session_id=session_id,
            code=code,
            bars=bars[:5],
            position={"direction": "long", "size": "1", "average_price": "100.05"},
            activated_at=activated,
            now=start + timedelta(hours=5, seconds=1),
            interval_seconds=3600,
            execution_args=args,
        )
        == "short"
    )
    state = await repo.get(session_id)
    assert (
        state.position_quantity == 0
        and state.cancels_confirmed
        and state.pending_reversal == "short"
    )
    assert (
        await restarted.evaluate(
            session_id=session_id,
            code=code,
            bars=bars[:6],
            position=FLAT,
            activated_at=activated,
            now=start + timedelta(hours=6, seconds=1),
            interval_seconds=3600,
            execution_args=args,
        )
        == "short"
    )
    state = await repo.get(session_id)
    assert state.generation == 2 and state.direction == "short" and state.position_quantity == 2
    assert (
        await restarted.evaluate(
            session_id=session_id,
            code=code,
            bars=bars,
            position={"direction": "short", "size": "2", "average_price": "100.05"},
            activated_at=activated,
            now=start + timedelta(hours=7, seconds=1),
            interval_seconds=3600,
            execution_args=args,
        )
        == "close"
    )
    state = await repo.get(session_id)
    assert (
        state.position_quantity == 0 and state.cancels_confirmed and not state.new_entries_blocked
    )
    count = len(provider.submissions)
    assert (
        await restarted.evaluate(
            session_id=session_id,
            code=code,
            bars=bars,
            position=FLAT,
            activated_at=activated,
            now=start + timedelta(hours=7, seconds=2),
            interval_seconds=3600,
        )
        == "no_new_bar"
    )
    assert len(provider.submissions) == count
    history = await checkpoints.history(session_id)
    assert [row.position["direction"] for row in history] == [
        "flat",
        "flat",
        "flat",
        "long",
        "long",
        "flat",
        "short",
    ]
    assert all(row.status in {"warmup", "delivered"} for row in history)

    if native:
        print(
            {
                "native_journey_language": "python",
                "containers_created": len(launched),
                "max_concurrent": 1,
                "image_ids": sorted({item["image_id"] for item in launched}),
                "container_names": [item["name"] for item in launched],
            }
        )
