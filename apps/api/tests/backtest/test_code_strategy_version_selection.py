"""검토한 코드 버전 선택·소유권·기존 요청 해시 호환성 회귀."""

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.dispatcher import FakeTaskDispatcher
from src.backtest.repository import BacktestRepository
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import BacktestService, _compute_body_hash
from src.strategy.code_contract import CodeSnapshot
from src.strategy.code_schemas import SaveCodeStrategyRequest
from src.strategy.code_service import CodeStrategyService
from src.strategy.exceptions import CodeStrategyPolicyError, StrategyNotFoundError
from src.strategy.models import ParseStatus, Strategy
from src.strategy.repository import StrategyRepository


def _request(strategy_id: UUID, **changes: object) -> CreateBacktestRequest:
    return CreateBacktestRequest.model_validate(
        {
            "strategy_id": strategy_id,
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "period_start": datetime(2024, 1, 1, tzinfo=UTC),
            "period_end": datetime(2024, 1, 7, tzinfo=UTC),
            "initial_capital": Decimal("10000"),
            "fill_timing": "next_bar_open",
            "execution_policy": "code_v1",
            **changes,
        }
    )


def _code_request(action: str = "hold") -> SaveCodeStrategyRequest:
    return SaveCodeStrategyRequest(
        name="reviewed-version",
        code=CodeSnapshot(
            execution_policy="code_v1",
            language="python",
            source_code=f'def on_bar(ctx, state):\n    return {{"action": "{action}"}}\n',
            params={},
            warmup_bars=50,
            provenance={"kind": "manual"},
        ),
    )


async def _user(session: AsyncSession) -> User:
    user = User(auth_subject=f"version_{uuid4().hex}", email=f"{uuid4().hex}@example.com")
    session.add(user)
    await session.flush()
    return user


def _service(session: AsyncSession) -> BacktestService:
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=AsyncMock(),
        dispatcher=FakeTaskDispatcher(),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("explicit_version", [True, False])
async def test_reviewed_v1_is_pinned_after_current_moves_to_v2(
    db_session: AsyncSession, explicit_version: bool
) -> None:
    user = await _user(db_session)
    strategy_repo = StrategyRepository(db_session)
    codes = CodeStrategyService(strategy_repo)
    v1 = await codes.create(_code_request(), owner_id=user.id)
    v2 = await codes.update(v1.id, _code_request("long"), owner_id=user.id)
    assert v1.version.id != v2.version.id

    submitted = await _service(db_session).submit(
        _request(v1.id, strategy_version_id=v1.version.id if explicit_version else None),
        user_id=user.id,
    )
    stored = await BacktestRepository(db_session).get_by_id(submitted.backtest_id)
    assert stored is not None
    expected = v1.version if explicit_version else v2.version
    assert stored.strategy_version_id == expected.id
    assert stored.config["execution_hash"] == expected.execution_hash
    current = await strategy_repo.find_by_id_and_owner(v1.id, user.id)
    assert current is not None and current.strategy_version_id == v2.version.id


@pytest.mark.asyncio
@pytest.mark.parametrize("foreign_owner", [False, True])
async def test_version_from_another_strategy_is_rejected(
    db_session: AsyncSession, foreign_owner: bool
) -> None:
    user = await _user(db_session)
    other = await _user(db_session) if foreign_owner else user
    codes = CodeStrategyService(StrategyRepository(db_session))
    owned = await codes.create(_code_request(), owner_id=user.id)
    foreign = await codes.create(_code_request("long"), owner_id=other.id)
    backtests = _service(db_session)
    with pytest.raises(CodeStrategyPolicyError):
        await backtests.submit(
            _request(owned.id, strategy_version_id=foreign.version.id), user_id=user.id
        )
    assert backtests.dispatcher.dispatched == []


@pytest.mark.asyncio
async def test_another_owner_strategy_is_not_found_even_with_its_valid_version(
    db_session: AsyncSession,
) -> None:
    user, other = await _user(db_session), await _user(db_session)
    foreign = await CodeStrategyService(StrategyRepository(db_session)).create(
        _code_request(), owner_id=other.id
    )
    backtests = _service(db_session)
    with pytest.raises(StrategyNotFoundError):
        await backtests.submit(
            _request(foreign.id, strategy_version_id=foreign.version.id),
            user_id=user.id,
        )
    assert backtests.dispatcher.dispatched == []


@pytest.mark.asyncio
async def test_unknown_version_does_not_fall_back_to_current(
    db_session: AsyncSession,
) -> None:
    user = await _user(db_session)
    owned = await CodeStrategyService(StrategyRepository(db_session)).create(
        _code_request(), owner_id=user.id
    )
    backtests = _service(db_session)
    with pytest.raises(CodeStrategyPolicyError):
        await backtests.submit(_request(owned.id, strategy_version_id=uuid4()), user_id=user.id)
    assert backtests.dispatcher.dispatched == []


@pytest.mark.asyncio
async def test_legacy_pine_rejects_explicit_version_instead_of_ignoring_it(
    db_session: AsyncSession,
) -> None:
    user = await _user(db_session)
    strategy = Strategy(
        user_id=user.id,
        name="legacy",
        pine_source='//@version=5\nstrategy("legacy")\n',
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()
    backtests = _service(db_session)
    with pytest.raises(CodeStrategyPolicyError):
        await backtests.submit(
            _request(strategy.id, execution_policy=None, strategy_version_id=uuid4()),
            user_id=user.id,
        )
    assert backtests.dispatcher.dispatched == []


@pytest.mark.parametrize("policy", [None, "code_v1"])
def test_omitted_version_preserves_pre_field_idempotency_hash(
    policy: str | None,
) -> None:
    owner = uuid4()
    request = _request(uuid4(), execution_policy=policy)
    # 새 필드가 없던 요청의 canonical payload를 그대로 구성한다.
    old_payload = {
        **request.model_dump(mode="json", exclude={"strategy_version_id", "maker_fee_pct"}),
        "user_id": str(owner),
    }
    if policy is None:
        old_payload.pop("execution_policy")
    old_hash = hashlib.sha256(
        json.dumps(old_payload, sort_keys=True, separators=(",", ":")).encode()
    ).digest()
    assert _compute_body_hash(request, owner) == old_hash
    assert (
        _compute_body_hash(request.model_copy(update={"strategy_version_id": None}), owner)
        == old_hash
    )


def test_explicit_versions_are_distinct_idempotency_payloads() -> None:
    owner = uuid4()
    request = _request(uuid4())
    hashes = {
        _compute_body_hash(value, owner)
        for value in (
            request,
            request.model_copy(update={"strategy_version_id": uuid4()}),
            request.model_copy(update={"strategy_version_id": uuid4()}),
        )
    }
    assert len(hashes) == 3


@pytest.mark.asyncio
async def test_research_and_legacy_code_roundtrip_list_and_pinned_policies(
    db_session: AsyncSession,
) -> None:
    from tests.strategy.test_research_code_contract import code, research

    user = await _user(db_session)
    other = await _user(db_session)
    repo = StrategyRepository(db_session)
    codes = CodeStrategyService(repo)
    legacy = await codes.create(_code_request(), owner_id=user.id)
    a = await codes.create(
        SaveCodeStrategyRequest(name="research A", code=code()), owner_id=user.id
    )
    b = await codes.update(
        a.id,
        SaveCodeStrategyRequest(name="research B", code=code(exit_policy="swing_two_bar_v1")),
        owner_id=user.id,
    )
    await codes.create(SaveCodeStrategyRequest(name="other owner", code=code()), owner_id=other.id)
    restored = await codes.get(a.id, owner_id=user.id)
    assert restored.version.execution_hash == b.version.execution_hash
    assert restored.version.provenance["research_execution"] == research(
        exit_policy="swing_two_bar_v1"
    )
    listed = await codes.list(owner_id=user.id, limit=100, offset=0)
    assert listed.total == 2
    assert {item.id for item in listed.items} == {legacy.id, a.id}
    backtests = _service(db_session)
    queued = await backtests.submit(
        _request(a.id, execution_policy="code_research_v1", strategy_version_id=a.version.id),
        user_id=user.id,
    )
    stored = await BacktestRepository(db_session).get_by_id(queued.backtest_id)
    assert stored is not None and stored.engine_version == "code_research_v1"
    assert stored.strategy_version_id == a.version.id
    assert stored.config["research_execution"] == research()
    with pytest.raises(CodeStrategyPolicyError):
        await backtests.submit(_request(a.id, strategy_version_id=a.version.id), user_id=user.id)


@pytest.mark.parametrize("policy", [None, "code_v1", "code_research_v1"])
def test_maker_omission_preserves_hash_but_explicit_value_changes_it(policy):
    owner = uuid4()
    request = _request(uuid4(), execution_policy=policy)
    legacy_payload = {
        **request.model_dump(mode="json", exclude={"maker_fee_pct", "strategy_version_id"}),
        "user_id": str(owner),
    }
    if policy is None:
        legacy_payload.pop("execution_policy")
    expected = hashlib.sha256(
        json.dumps(legacy_payload, sort_keys=True, separators=(",", ":")).encode()
    ).digest()
    assert _compute_body_hash(request, owner) == expected
    explicit = request.model_copy(update={"maker_fee_pct": Decimal("0.00010")})
    assert _compute_body_hash(explicit, owner) != expected
