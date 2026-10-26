"""연구 정책의 엄격한 불변 입력과 기존 코드 경로의 직렬화 호환성."""

import hashlib
import json
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.backtest.service import BacktestService
from src.strategy.code_contract import read_code_version
from src.strategy.code_schemas import SaveCodeStrategyRequest
from src.strategy.code_service import CodeStrategyService
from src.strategy.exceptions import CodeStrategyPolicyError
from src.strategy.models import StrategyVersion
from src.strategy.research_contract import ResearchExecution
from tests.strategy.test_code_strategy_commits import snapshot


def research(**changes):
    return {
        "contract_version": 1,
        "exit_policy": "signal_only_v1",
        "reentry_policy": "close_then_reenter_v1",
        "signal_mode": "shared_events",
        "signal_mapping_hash": "a" * 64,
        **changes,
    }


def code(**changes):
    return snapshot(
        execution_policy="code_research_v1",
        provenance={"research_execution": research(**changes)},
    )


def pinned(strategy_id, value):
    return StrategyVersion(
        strategy_id=strategy_id,
        pine_source=None,
        source_hash=value.source_hash,
        parser_version=value.execution_policy,
        language=value.language.value,
        source_code=value.source_code,
        execution_policy=value.execution_policy,
        warmup_bars=value.warmup_bars,
        params=value.params,
        provenance=value.provenance,
        execution_hash=value.execution_hash,
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"contract_version": True},
        {"contract_version": "1"},
        {"contract_version": 2},
        {"exit_policy": "signal_only"},
        {"reentry_policy": "ignore_same_direction"},
        {"signal_mode": "unknown"},
        {"signal_mapping_hash": "A" * 64},
        {"signal_mapping_hash": "a" * 63},
        {"extra": "not_allowed"},
    ],
)
def test_research_contract_rejects_unknown_or_coerced_values(changes):
    with pytest.raises(ValidationError):
        code(**changes)


def test_research_requires_contract_and_is_frozen():
    with pytest.raises(ValidationError):
        snapshot(execution_policy="code_research_v1")
    value = ResearchExecution.model_validate(research())
    with pytest.raises(ValidationError):
        value.exit_policy = "swing_two_bar_v1"


def test_existing_code_snapshot_serialization_and_hash_are_unchanged():
    value = snapshot()
    expected = {
        "schema_version": 1,
        "execution_policy": "code_v1",
        "language": "python",
        "source_code": 'def on_bar(ctx, state):\n    return {"action": "hold"}\n',
        "warmup_bars": 50,
        "params": {"length": 20},
        "provenance": {"model": "sol-6.1"},
    }
    assert value.model_dump(mode="json") == expected
    assert (
        value.execution_hash
        == hashlib.sha256(
            json.dumps(expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
    )
    assert value.research_execution is None


def test_every_research_policy_input_participates_in_hash_and_version_restore():
    baseline = code()
    variants = [
        code(exit_policy="swing_two_bar_v1"),
        code(signal_mode="position_feedback"),
        code(signal_mapping_hash="b" * 64),
    ]
    assert len({v.execution_hash for v in [baseline, *variants]}) == 4
    version = pinned(uuid4(), baseline)
    assert read_code_version(version) == baseline
    version.provenance = {"research_execution": research(exit_policy="swing_two_bar_v1")}
    with pytest.raises(CodeStrategyPolicyError):
        read_code_version(version)


@pytest.mark.asyncio
async def test_research_create_update_get_list_preserve_contract_and_commit_once():
    repo = AsyncMock()
    repo.create.side_effect = lambda item: item
    repo.create_code_version.side_effect = lambda *, strategy_id, code: pinned(strategy_id, code)
    owner = uuid4()
    service = CodeStrategyService(repo)
    created = await service.create(SaveCodeStrategyRequest(name="A", code=code()), owner_id=owner)
    strategy = repo.create.call_args.args[0]
    assert strategy.execution_policy == "code_research_v1"
    repo.commit.assert_awaited_once()
    # 저장된 원문으로 불변 버전을 다시 구성한다.
    version = pinned(strategy.id, code())
    strategy.strategy_version_id = version.id
    repo.find_by_id_and_owner.return_value = strategy
    repo.get_version_by_id.return_value = version
    repo.list_code_by_owner.return_value = ([(strategy, version)], 1)
    assert (await service.get(strategy.id, owner_id=owner)).version.provenance == code().provenance
    listed = await service.list(owner_id=owner, limit=20, offset=0)
    assert listed.total == 1 and listed.items[0].version.execution_policy == "code_research_v1"
    repo.commit.reset_mock()
    updated = await service.update(
        strategy.id,
        SaveCodeStrategyRequest(name="B", code=code(exit_policy="swing_two_bar_v1")),
        owner_id=owner,
    )
    assert created.version.execution_hash != updated.version.execution_hash
    assert updated.version.execution_policy == "code_research_v1"
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_research_backtest_dispatch_preserves_policy_and_rejects_legacy_label():
    from src.strategy.models import Strategy
    from tests.backtest.test_code_strategy_version_selection import _request

    value = code()
    strategy = Strategy(user_id=uuid4(), name="A", execution_policy=value.execution_policy)
    version = pinned(strategy.id, value)
    strategy.strategy_version_id = version.id
    repo, strategy_repo, dispatcher = AsyncMock(), AsyncMock(), Mock()
    strategy_repo.find_by_id_and_owner.return_value = strategy
    strategy_repo.get_version_by_id.return_value = version
    service = BacktestService(
        repo=repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=AsyncMock(),
        dispatcher=dispatcher,
    )
    with pytest.raises(CodeStrategyPolicyError):
        await service.submit(_request(strategy.id), user_id=strategy.user_id)
    repo.create.assert_not_awaited()
    await service.submit(
        _request(
            strategy.id,
            execution_policy="code_research_v1",
            strategy_version_id=version.id,
        ),
        user_id=strategy.user_id,
    )
    stored = repo.create.call_args.args[0]
    assert stored.engine_version == "code_research_v1"
    assert stored.config["risk_policy"] == "signal_only_v1"
    assert stored.config["maker_fee"] == "0.00010"
    assert stored.config["research_execution"] == research()
    assert stored.strategy_version_id == version.id
    assert repo.commit.await_count == 2
    detail = service._to_detail(stored)
    assert detail.strategy_version_id == version.id
    assert detail.config.execution_policy == "code_research_v1"
    assert detail.config.research_execution == value.research_execution


@pytest.mark.asyncio
@pytest.mark.parametrize("source_policy", [None, "code_v1"])
async def test_research_policy_never_registers_demo_or_reads_account(source_policy):
    from src.strategy.models import Strategy
    from src.trading.exceptions import InvalidStrategySettings
    from src.trading.schemas import RegisterLiveSessionRequest
    from src.trading.services.live_session_service import LiveSignalSessionService

    owner = uuid4()
    strategy = Strategy(user_id=owner, name="research", execution_policy="code_research_v1")
    repo, accounts, strategies, balance = (
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
    )
    strategies.find_by_id_and_owner.return_value = strategy
    service = LiveSignalSessionService(
        repo,
        accounts,
        strategies,
        balance_service=balance,
        exclusivity_service=AsyncMock(),
    )
    with pytest.raises(InvalidStrategySettings):
        await service.register(
            owner,
            RegisterLiveSessionRequest(
                strategy_id=strategy.id,
                exchange_account_id=uuid4(),
                symbol="BTCUSDT",
                interval="1h",
                source_policy=source_policy,
            ),
        )
    accounts.get_by_id.assert_not_awaited()
    balance.get_balance.assert_not_awaited()
    repo.save.assert_not_awaited()
    repo.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("requested", [None, "0", "0.00030"])
async def test_research_maker_cost_reaches_config_mapper_and_response(requested):
    from decimal import Decimal

    from src.backtest.config_mapper import build_engine_config_from_db
    from src.strategy.models import Strategy
    from tests.backtest.test_code_strategy_version_selection import _request

    value = code(exit_policy="swing_two_bar_v1")
    strategy = Strategy(user_id=uuid4(), name="B", execution_policy=value.execution_policy)
    version = pinned(strategy.id, value)
    strategy.strategy_version_id = version.id
    repo, strategies = AsyncMock(), AsyncMock()
    strategies.find_by_id_and_owner.return_value = strategy
    strategies.get_version_by_id.return_value = version
    service = BacktestService(
        repo=repo,
        strategy_repo=strategies,
        ohlcv_provider=AsyncMock(),
        dispatcher=Mock(),
    )
    request = _request(strategy.id, execution_policy="code_research_v1", maker_fee_pct=requested)
    await service.submit(request, user_id=strategy.user_id)
    stored = repo.create.call_args.args[0]
    expected = Decimal(requested) if requested is not None else Decimal("0.00010")
    assert Decimal(stored.config["maker_fee"]) == expected
    assert Decimal(str(build_engine_config_from_db(stored).maker_fee)) == expected
    assert Decimal(str(service._to_detail(stored).config.maker_fee)) == expected
    assert repo.commit.await_count == 2
