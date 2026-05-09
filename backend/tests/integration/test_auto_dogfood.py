"""Sprint 24b — Backend E2E 자동 dogfood (codex G.0 P1 #5 + P2 #2 반영).

dogfood Day 2-7 critical path 6 시나리오 자동 회귀:
1. Strategy + WebhookSecret atomic create (DB row 검증, Sprint 13 broken bug 회귀 방어)
2. Backtest engine smoke (run_backtest_v2 직접 호출 + status="ok")
3. Order create + DispatchSnapshot 검증 (Sprint 22+23 BL-091/102)
4. Snapshot drift detection (Sprint 23 G.2 P1 #1)
5. Multi-account dispatch (Sprint 24a BL-011/012)
6. 자동 summary parser smoke (codex G.0 P1 #5 — dogfood_report 와 분리)

mark.integration + `--run-integration` flag (Sprint 19 BL-085 패턴).
격리 stack (5433/6380) 강제 + DSN guard.

Service direct call 패턴 — Clerk auth 우회. HTTP route + Clerk JWT 는 별도 e2e
(test_trading_e2e.py) 가 가드.
"""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.core.config import settings
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.tasks.trading import _provider_from_order_snapshot_or_fallback
from src.trading.encryption import EncryptionService
from src.trading.exceptions import UnsupportedExchangeError
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
    WebhookSecret,
)
from src.trading.providers import BybitDemoProvider, OkxDemoProvider
from src.trading.schemas import OrderRequest

pytestmark = pytest.mark.integration

_crypto = EncryptionService(settings.trading_encryption_keys)


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------


@pytest.fixture
async def dogfood_user(db_session: AsyncSession) -> User:
    user = User(
        clerk_user_id=f"dogfood_{uuid4().hex[:8]}",
        email=f"dogfood-{uuid4().hex[:8]}@test.local",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.fixture
async def dogfood_strategy(db_session: AsyncSession, dogfood_user: User) -> Strategy:
    s = Strategy(
        user_id=dogfood_user.id,
        name="Dogfood RsiD",
        pine_source=(
            "//@version=5\n"
            "strategy('Dogfood RsiD', overlay=true)\n"
            "rsi = ta.rsi(close, 14)\n"
            "if rsi < 30\n"
            "    strategy.entry('L', strategy.long)\n"
            "if rsi > 70\n"
            "    strategy.close('L')\n"
        ),
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(s)
    await db_session.flush()
    return s


@pytest.fixture
async def bybit_demo_account(db_session: AsyncSession, dogfood_user: User) -> ExchangeAccount:
    acct = ExchangeAccount(
        user_id=dogfood_user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=_crypto.encrypt("dogfood-bybit-key"),
        api_secret_encrypted=_crypto.encrypt("dogfood-bybit-secret"),
        label="Dogfood Bybit Demo",
    )
    db_session.add(acct)
    await db_session.flush()
    return acct


@pytest.fixture
async def okx_demo_account(db_session: AsyncSession, dogfood_user: User) -> ExchangeAccount:
    acct = ExchangeAccount(
        user_id=dogfood_user.id,
        exchange=ExchangeName.okx,
        mode=ExchangeMode.demo,
        api_key_encrypted=_crypto.encrypt("dogfood-okx-key"),
        api_secret_encrypted=_crypto.encrypt("dogfood-okx-secret"),
        passphrase_encrypted=_crypto.encrypt("dogfood-okx-passphrase"),
        label="Dogfood OKX Demo",
    )
    db_session.add(acct)
    await db_session.flush()
    return acct


# ----------------------------------------------------------------------
# Scenario 1: Strategy + WebhookSecret atomic create (Sprint 13 회귀 방어)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario1_strategy_with_webhook_secret_atomic(
    db_session: AsyncSession,
    dogfood_strategy: Strategy,
) -> None:
    """Sprint 13 broken bug 회귀 방어 — Strategy + WebhookSecret 동일 transaction commit.

    Service layer 의 commit 누락은 별도 commit-spy test (LESSON-019). 본 test 는
    DB row 가 두 row 모두 존재 + FK 정합 검증 (integration 시점 검증).
    """
    # WebhookSecret 직접 INSERT (service layer 가 atomic 으로 한다는 가정)
    secret = WebhookSecret(
        strategy_id=dogfood_strategy.id,
        secret_encrypted=_crypto.encrypt("dogfood-webhook-secret"),
    )
    db_session.add(secret)
    await db_session.flush()

    # 두 row 모두 commit 가능 (FK 정합)
    strategy_row = await db_session.get(Strategy, dogfood_strategy.id)
    secret_stmt = select(WebhookSecret).where(WebhookSecret.strategy_id == dogfood_strategy.id)
    secret_result = await db_session.execute(secret_stmt)
    secret_row = secret_result.scalar_one_or_none()

    assert strategy_row is not None
    assert secret_row is not None


# ----------------------------------------------------------------------
# Scenario 2: Backtest engine smoke (run_backtest_v2 직접 호출)
# ----------------------------------------------------------------------


def test_scenario2_backtest_engine_smoke(dogfood_strategy: Strategy) -> None:
    """Sprint 25 BL-112 — run_backtest_v2 실 호출 + 강한 assert.

    Sprint 24b 의 stub (`callable(run_backtest_v2)` + version smoke) 를 실 backtest
    로 승격. codex G.0 iter 2 가 plan v2 의 fixture 가설 (기존 EMA fixture 재사용)
    을 코드 실측으로 refute (num_trades=0) → 신규 `make_trending_ohlcv` 사용.

    fixture 자체의 trade 발생 보장은 `tests/fixtures/test_backtest_ohlcv_precondition`
    이 num_trades >= 3 으로 검증. 본 scenario 는 보수적으로 num_trades >= 1.
    """
    from src.backtest.engine.types import BacktestConfig
    from src.backtest.engine.v2_adapter import _detect_version, run_backtest_v2
    from tests.fixtures.backtest_ohlcv import (
        EMA_CROSS_PINE_SOURCE,
        make_trending_ohlcv,
    )

    # version detect — dogfood_strategy 의 Pine v5 인식 (Sprint 24b 보존)
    assert _detect_version(dogfood_strategy.pine_source) == "v5"

    # 실 backtest 실행 — fixture (8 segments × 25 bars = 200 bars) + EMA cross
    outcome = run_backtest_v2(
        EMA_CROSS_PINE_SOURCE,
        make_trending_ohlcv(),
        BacktestConfig(init_cash=Decimal("10000")),
    )

    assert outcome.status == "ok", f"backtest status={outcome.status}, error={outcome.error}"
    assert outcome.result is not None
    assert len(outcome.result.equity_curve) > 0
    assert outcome.result.metrics.num_trades >= 1


# ----------------------------------------------------------------------
# Scenario 3: Order create + DispatchSnapshot (Sprint 22+23 BL-091/102)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario3_order_dispatch_snapshot(
    db_session: AsyncSession,
    dogfood_strategy: Strategy,
    bybit_demo_account: ExchangeAccount,
    request: pytest.FixtureRequest,
) -> None:
    """Sprint 25 BL-113 — OrderService.execute() 통한 dispatch_snapshot 자동 채움.

    Sprint 24b 의 Order ORM 직접 INSERT 우회 → service layer 호출. codex G.0 iter 2
    P1 #7 (`repo=` param 이름) + P1 #10 (fake dispatcher Celery 우회) + iter 1 P2 #1
    (uuid4 idempotency_key per test) 모두 반영.

    검증: OrderService 가 (1) exchange_service 통해 account fetch → snapshot 자동 채움
    + (2) commit + (3) fake dispatcher 호출.
    """
    import uuid as _uuid

    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.services.account_service import ExchangeAccountService
    from src.trading.services.order_service import OrderService

    # DI — same db_session 공유 (트랜잭션 통일)
    order_repo = OrderRepository(db_session)
    exchange_repo = ExchangeAccountRepository(db_session)
    exchange_svc = ExchangeAccountService(exchange_repo, _crypto)

    # FakeOrderDispatcher — Celery enqueue 우회 (codex iter 2 P1 #10)
    class _FakeOrderDispatcher:
        def __init__(self) -> None:
            self.dispatched_count = 0
            self.dispatched_ids: list[UUID] = []

        async def dispatch_order_execution(self, order_id: UUID) -> None:
            self.dispatched_count += 1
            self.dispatched_ids.append(order_id)

    fake_dispatcher = _FakeOrderDispatcher()

    # NoopKillSwitch — gate 통과 (KS 평가는 별도 시나리오에서 가드)
    class _NoopKillSwitch:
        async def ensure_not_gated(self, strategy_id: UUID, account_id: UUID) -> None:
            return

    service = OrderService(
        session=db_session,
        repo=order_repo,
        dispatcher=fake_dispatcher,
        kill_switch=_NoopKillSwitch(),
        exchange_service=exchange_svc,  # 핵심 — dispatch_snapshot 자동 채움 prereq
    )

    req = OrderRequest(
        strategy_id=dogfood_strategy.id,
        exchange_account_id=bybit_demo_account.id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
    )

    # codex iter 1 P2 #1 — uuid4 per test (replay 방지)
    idempotency_key = f"{request.node.name}:{_uuid.uuid4().hex}"

    response, is_replayed = await service.execute(req, idempotency_key=idempotency_key)

    assert is_replayed is False
    assert fake_dispatcher.dispatched_count == 1
    assert fake_dispatcher.dispatched_ids == [response.id]

    # DB 에서 재조회 — dispatch_snapshot 자동 채움 검증
    refreshed = await order_repo.get_by_id(response.id)
    assert refreshed is not None
    assert refreshed.dispatch_snapshot is not None
    assert refreshed.dispatch_snapshot["exchange"] == "bybit"
    assert refreshed.dispatch_snapshot["mode"] == "demo"
    assert refreshed.dispatch_snapshot["has_leverage"] is False

    # Sprint 22+23 dispatch helper 정합 — refreshed snapshot → BybitDemoProvider
    provider = _provider_from_order_snapshot_or_fallback(refreshed, bybit_demo_account, submit=None)
    assert isinstance(provider, BybitDemoProvider)


# ----------------------------------------------------------------------
# Scenario 4: Snapshot drift detection (Sprint 23 G.2 P1 #1)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario4_snapshot_drift_rejected(
    db_session: AsyncSession,
    dogfood_strategy: Strategy,
    bybit_demo_account: ExchangeAccount,
) -> None:
    """직접 SQL UPDATE 로 account.mode demo→live → snapshot drift → reject.

    Sprint 23 codex G.2 P1 #1 (security critical) — snapshot vs current account
    mismatch 시 silent broker bypass 위험 차단.
    """
    order = Order(
        strategy_id=dogfood_strategy.id,
        exchange_account_id=bybit_demo_account.id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        state=OrderState.pending,
        dispatch_snapshot={
            "exchange": "bybit",
            "mode": "demo",
            "has_leverage": False,
        },
    )
    db_session.add(order)
    await db_session.flush()

    # account.mode mutation (DB level 만 가능, 실 endpoint 부재)
    await db_session.execute(
        text("UPDATE trading.exchange_accounts SET mode='live' WHERE id = :acc_id"),
        {"acc_id": bybit_demo_account.id},
    )
    await db_session.flush()
    await db_session.refresh(bybit_demo_account)

    with pytest.raises(UnsupportedExchangeError) as exc_info:
        _provider_from_order_snapshot_or_fallback(order, bybit_demo_account, submit=None)
    assert "snapshot" in str(exc_info.value)


# ----------------------------------------------------------------------
# Scenario 5: Multi-account dispatch (Sprint 24a BL-011/012)
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario5_multi_account_dispatch(
    db_session: AsyncSession,
    bybit_demo_account: ExchangeAccount,
    okx_demo_account: ExchangeAccount,
) -> None:
    """두 ExchangeAccount → 두 dispatch 모두 정확 + lease key 충돌 없음.

    Sprint 24a BL-011/012 의 multi-account scaling 핵심.
    """
    bybit_order = Order(
        strategy_id=uuid4(),
        exchange_account_id=bybit_demo_account.id,
        symbol="BTCUSDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        state=OrderState.pending,
        dispatch_snapshot={
            "exchange": "bybit",
            "mode": "demo",
            "has_leverage": False,
        },
    )
    okx_order = Order(
        strategy_id=uuid4(),
        exchange_account_id=okx_demo_account.id,
        symbol="BTC-USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        state=OrderState.pending,
        dispatch_snapshot={
            "exchange": "okx",
            "mode": "demo",
            "has_leverage": False,
        },
    )

    bybit_provider = _provider_from_order_snapshot_or_fallback(
        bybit_order, bybit_demo_account, submit=None
    )
    okx_provider = _provider_from_order_snapshot_or_fallback(
        okx_order, okx_demo_account, submit=None
    )

    assert isinstance(bybit_provider, BybitDemoProvider)
    assert isinstance(okx_provider, OkxDemoProvider)

    # 두 lease key 충돌 없음 (Sprint 24a BL-011)
    from src.tasks._ws_lease import _lease_key

    assert _lease_key(str(bybit_demo_account.id)) != _lease_key(str(okx_demo_account.id))


# ----------------------------------------------------------------------
# Scenario 6: 자동 summary parser smoke (codex G.0 P1 #5)
# ----------------------------------------------------------------------


def test_scenario6_summary_parse_smoke() -> None:
    """codex G.2 P1 #3 fix — `run_auto_dogfood.py` 의 `_build_summary` 직접 호출.

    sample pytest stdout 으로 6 시나리오 (5 PASS + 1 FAIL) 시뮬 → schema 검증.
    """
    import importlib.util
    from pathlib import Path

    # backend/scripts/run_auto_dogfood.py 동적 import (sys.path 미등록 회피)
    script_path = Path(__file__).parents[2] / "scripts" / "run_auto_dogfood.py"
    spec = importlib.util.spec_from_file_location("run_auto_dogfood", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # 6 scenarios 모의 pytest stdout (5 PASS + 1 FAIL)
    fake_stdout = (
        "tests/integration/test_auto_dogfood.py::test_scenario1_strategy_with_webhook_secret_atomic PASSED\n"
        "tests/integration/test_auto_dogfood.py::test_scenario2_backtest_engine_smoke PASSED\n"
        "tests/integration/test_auto_dogfood.py::test_scenario3_order_dispatch_snapshot PASSED\n"
        "tests/integration/test_auto_dogfood.py::test_scenario4_snapshot_drift_rejected FAILED\n"
        "tests/integration/test_auto_dogfood.py::test_scenario5_multi_account_dispatch PASSED\n"
        "tests/integration/test_auto_dogfood.py::test_scenario6_summary_parse_smoke PASSED\n"
        "===== 5 passed, 1 failed in 0.5s =====\n"
    )
    summary = module._build_summary(rc=1, stdout=fake_stdout, stderr="")

    # schema 검증 — counts (PASSED / FAILED 정확) + 6 scenarios + exit_code
    assert summary["counts"]["passed"] == 5, f"counts={summary['counts']}"
    assert summary["counts"]["failed"] == 1, f"counts={summary['counts']}"
    assert len(summary["scenarios"]) == 6
    # exit_code propagated
    assert summary["exit_code"] == 1
    # 모든 시나리오가 status 필드 보유 (정확한 값은 stdout 파싱 fragility 로 별도 BL)
    assert all("status" in sc for sc in summary["scenarios"])
    # JSON 직렬화 가능
    json.dumps(summary)
