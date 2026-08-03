"""OrderService reject paths — qb_order_rejected_total counter 검증 (Sprint 9 Phase D).

각 reject reason 마다 service.execute 가 카운터를 +1 하는지 before/after delta 로 확인.

★**BL-580 (2026-08-03 metric-guard-residual-close) — 고장 주입 10곳을 여기에 얹었다.**
BL-580 이 이 파일의 10 사이트를 뺀 근거는 코드 독해였다 — 「발주 **전** 검증 거절 직후
`raise`. blast radius 0」. 앞부분(발주 전)은 참이다. 뒷부분은 **거짓**이다:

- 10곳 전부 `.inc()` **직후** 도메인 예외를 raise 한다. 계측이 던지면 그 도메인 예외가
  **아예 발생하지 않고** `OSError` 가 대신 올라간다.
- 9종 전부 `AppException` 하위(4xx)라 전역 핸들러(`main.py:222`)가 4xx 로 직렬화하는데,
  `OSError` 는 `main.py:228` 로 가 **HTTP 500** 이 된다 (사전등록 **H5**).
- 그중 6종은 호출자가 **예외 타입으로 분기**한다 — `tasks/live_signal.py:3232`/`:3239`/`:3249`
  가 `mark_failed` + `commit` 을 하고 `:2793` 이 재시도를 막는다. 타입이 바뀌면 그 분기가
  통째로 건너뛰어진다 (사전등록 **H4**). 호출자 쪽 증명은
  `tests/tasks/test_live_signal_metric_failure.py` 가 한다.

주입은 `.inc` 가 아니라 **`.labels` 를 폭파**시킨다 — multiprocess 모드에서 새 라벨 조합이
mmap 파일을 늘리는 시점이 `.labels()` 이기 때문이다(`metrics_multiproc.py` `_count_safely`
docstring, BL-536 R2). `.inc` 만 폭파시키면 `.labels()` 를 감싸지 않은 반쪽 수리가 통과한다.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.common.exceptions import AppException
from src.common.metrics import qb_order_rejected_total
from src.trading.encryption import EncryptionService
from src.trading.exceptions import (
    AccountOwnershipMismatch,
    BalanceUnverified,
    IdempotencyConflict,
    KillSwitchActive,
    LeverageCapExceeded,
    MinNotionalNotMet,
    NotionalExceeded,
    RiskSizingExceeded,
    TradingSessionClosed,
)
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)


@pytest.fixture
def crypto() -> EncryptionService:
    return EncryptionService(SecretStr(Fernet.generate_key().decode()))


@pytest.fixture
async def exchange_account(
    db_session: AsyncSession, user: User, crypto: EncryptionService
) -> ExchangeAccount:
    acct = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("k"),
        api_secret_encrypted=crypto.encrypt("s"),
    )
    db_session.add(acct)
    await db_session.flush()
    return acct


class _NoopKillSwitch:
    async def ensure_not_gated(self, strategy_id: UUID, account_id: UUID) -> None:
        return None


class _ActiveKillSwitch:
    async def ensure_not_gated(self, strategy_id: UUID, account_id: UUID) -> None:
        raise KillSwitchActive("Active kill switch: cumulative_loss")


class _CapturingDispatcher:
    def __init__(self) -> None:
        self.last_id: UUID | None = None

    async def dispatch_order_execution(self, order_id: UUID) -> None:
        self.last_id = order_id


class _ClosedSessionsPort:
    """현재 UTC hour 와 겹치지 않는 세션만 반환 → TradingSessionClosed 유도."""

    async def get_sessions(self, strategy_id: UUID) -> list[str]:
        # "00:00-00:01" — 어떤 실제 hour 에도 매칭되지 않도록 짧은 창 1분
        # is_allowed 는 hour 단위 비교이므로 실제 00시 외 모든 시각에 닫힘
        from datetime import UTC, datetime

        now_hour = datetime.now(UTC).hour
        blocked_hour = (now_hour + 12) % 24  # 반대편 시간대
        return [f"{blocked_hour:02d}:00-{blocked_hour:02d}:01"]


async def test_leverage_cap_reject_increments_metric(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
) -> None:
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    counter = qb_order_rejected_total.labels(exchange="unknown", reason="leverage_cap")
    before = counter._value.get()

    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=50,  # cap=20 (default) 초과
        margin_mode="cross",
    )
    with pytest.raises(LeverageCapExceeded):
        await svc.execute(req, idempotency_key=None)

    after = counter._value.get()
    assert after == before + 1


async def test_notional_reject_increments_metric(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
) -> None:
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    counter = qb_order_rejected_total.labels(exchange="unknown", reason="notional")
    before = counter._value.get()

    exchange_stub = MagicMock()
    exchange_stub.fetch_balance_usdt = AsyncMock(return_value=Decimal("100"))
    # Wave 1 C5 — min-notional 가드 기본 skip(None=fail-open). max-notional reject 검증 회귀 0.
    exchange_stub.fetch_min_notional = AsyncMock(return_value=None)
    # Sprint 23 BL-102: OrderService._execute_inner 가 dispatch snapshot 채움 위해
    # account fetch. notional reject 검증만 하므로 None 반환 OK (snapshot=None → legacy fallback).
    exchange_stub._repo = MagicMock()
    exchange_stub._repo.get_by_id = AsyncMock(return_value=None)

    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
        exchange_service=exchange_stub,
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=Decimal("0.1"),
        price=Decimal("50000"),  # notional=100000 > 100*20*0.95=1900
        leverage=20,
        margin_mode="cross",
    )
    with pytest.raises(NotionalExceeded):
        await svc.execute(req, idempotency_key=None)

    after = counter._value.get()
    assert after == before + 1


async def test_session_closed_reject_increments_metric(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
) -> None:
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    counter = qb_order_rejected_total.labels(exchange="unknown", reason="session_closed")
    before = counter._value.get()

    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
        sessions_port=_ClosedSessionsPort(),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )
    with pytest.raises(TradingSessionClosed):
        await svc.execute(req, idempotency_key=None)

    after = counter._value.get()
    assert after == before + 1


async def test_kill_switch_reject_increments_metric(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
) -> None:
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    counter = qb_order_rejected_total.labels(exchange="unknown", reason="kill_switch")
    before = counter._value.get()

    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_ActiveKillSwitch(),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )
    with pytest.raises(KillSwitchActive):
        await svc.execute(req, idempotency_key=None)

    after = counter._value.get()
    assert after == before + 1


async def test_idempotency_conflict_reject_increments_metric(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount
) -> None:
    """동일 idempotency_key + 다른 body_hash → IdempotencyConflict + metric +1."""
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.schemas import OrderRequest
    from src.trading.services.order_service import OrderService

    # 기존 order 를 직접 INSERT 해 둔다 (idempotency row 선점).
    idem_key = f"test-idem-{uuid4()}"
    existing = Order(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=OrderState.pending,
        idempotency_key=idem_key,
        idempotency_payload_hash=b"original-hash",
    )
    db_session.add(existing)
    await db_session.commit()

    counter = qb_order_rejected_total.labels(
        exchange="unknown", reason="idempotency_conflict"
    )
    before = counter._value.get()

    svc = OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        kill_switch=_NoopKillSwitch(),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )
    with pytest.raises(IdempotencyConflict):
        await svc.execute(req, idempotency_key=idem_key, body_hash=b"different-hash")

    after = counter._value.get()
    assert after == before + 1


# ── BL-580 고장 주입 (A1~A10) ──────────────────────────────────────────────
# 사전등록 postcondition: `svc.execute(...)` 가 **그 자리의 도메인 예외를** raise 한다
# (`OSError` 가 아니라). 그리고 그 예외는 4xx 를 갖는 `AppException` 이다 — 전역 핸들러가
# 4xx 로 직렬화하는 근거이고, 이것이 H5(4xx → 500)를 재는 축이다.


def _explode_labels(calls: list[str]):
    """`.labels()` 만 폭파시킨다 — mmap 할당 실패(새 라벨 조합) 모사."""

    def _labels(*_args: object, **_kwargs: object) -> object:
        calls.append("labels")
        raise OSError("mmap allocation failed")

    return _labels


class _OwnerSessionsPort:
    """ownership gate 를 태우기 위한 port — `get_owner` 가 있어야 게이트가 켜진다."""

    def __init__(self, owner: UUID | None) -> None:
        self._owner = owner

    async def get_sessions(self, strategy_id: UUID) -> list[str]:
        return []

    async def get_owner(self, strategy_id: UUID) -> UUID | None:
        return self._owner


def _account_stub(*, user_id: UUID, mode: ExchangeMode = ExchangeMode.demo) -> MagicMock:
    stub = MagicMock()
    stub.user_id = user_id
    stub.exchange = ExchangeName.bybit
    stub.mode = mode
    return stub


def _exchange_stub(
    *,
    account: MagicMock | None = None,
    balance: Decimal | None = None,
    min_notional: Decimal | None = None,
    mark_price: Decimal | None = None,
) -> MagicMock:
    stub = MagicMock()
    stub.fetch_balance_usdt = AsyncMock(return_value=balance)
    stub.fetch_min_notional = AsyncMock(return_value=min_notional)
    stub.fetch_mark_price = AsyncMock(return_value=mark_price)
    stub._repo = MagicMock()
    stub._repo.get_by_id = AsyncMock(return_value=account)
    return stub


def _assert_domain_rejection(exc_info: pytest.ExceptionInfo, calls: list[str]) -> None:
    """주입 판별력 + H5 축을 한 자리에서 단언한다."""
    assert calls == ["labels"], "프로덕션 계측 라인이 실제로 실행돼야 한다 (주입 판별력)"
    assert isinstance(exc_info.value, AppException), (
        "도메인 예외가 탈출해야 전역 핸들러가 4xx 로 직렬화한다 — "
        "OSError 가 올라가면 main.py 의 unhandled 핸들러가 500 을 낸다"
    )
    assert 400 <= exc_info.value.status_code < 500


def _svc(db_session: AsyncSession, **kwargs):
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.services.order_service import OrderService

    kwargs.setdefault("kill_switch", _NoopKillSwitch())
    return OrderService(
        session=db_session,
        repo=OrderRepository(db_session),
        dispatcher=_CapturingDispatcher(),
        **kwargs,
    )


async def test_risk_sizing_reject_survives_metric_failure(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A1 (`order_service.py:129`) — 서버 권위 risk 사이징 거절 직전의 계측 실패.

    A1/A2 는 이 예외형을 **구체 타입으로 catch 하는 호출자가 코드베이스에 0곳**이다
    (2026-08-03 실측). 따라서 유일한 해로운 귀결은 H5 — 422 가 500 이 된다.
    """
    from src.trading.schemas import OrderRequest

    calls: list[str] = []
    monkeypatch.setattr(qb_order_rejected_total, "labels", _explode_labels(calls))

    svc = _svc(
        db_session,
        exchange_service=_exchange_stub(balance=Decimal("100")),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=Decimal("0.1"),  # max_qty = (100 * 1%) / 1000 = 0.001
        price=Decimal("50000"),
        stop_loss=Decimal("49000"),
        risk_percent=Decimal("1"),
    )

    with pytest.raises(RiskSizingExceeded) as exc_info:
        await svc.execute(req, idempotency_key=None)

    _assert_domain_rejection(exc_info, calls)


async def test_ownership_mismatch_reject_survives_metric_failure(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A2 (`order_service.py:169`) — TRD-4 cross-tenant IDOR 차단 직전의 계측 실패.

    ★이 게이트는 「모든 side-effect 이전」이라고 코드가 적어 둔 자리다. 계측 한 줄이
    거절을 500 으로 바꿔도 차단 자체는 유지된다(예외는 여전히 나간다) — 그래서 H4 가
    아니라 H5 다. 그 구분을 테스트로 고정한다.
    """
    from src.trading.schemas import OrderRequest

    calls: list[str] = []
    monkeypatch.setattr(qb_order_rejected_total, "labels", _explode_labels(calls))

    svc = _svc(
        db_session,
        sessions_port=_OwnerSessionsPort(uuid4()),  # strategy 소유자 ≠ account 소유자
        exchange_service=_exchange_stub(account=_account_stub(user_id=uuid4())),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )

    with pytest.raises(AccountOwnershipMismatch) as exc_info:
        await svc.execute(req, idempotency_key=None)

    _assert_domain_rejection(exc_info, calls)


async def test_leverage_cap_reject_survives_metric_failure(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A3 (`order_service.py:200`) — `LeverageCapExceeded` 는 호출자가 타입으로 분기한다."""
    from src.trading.schemas import OrderRequest

    calls: list[str] = []
    monkeypatch.setattr(qb_order_rejected_total, "labels", _explode_labels(calls))

    svc = _svc(db_session)
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        leverage=50,
        margin_mode="cross",
    )

    with pytest.raises(LeverageCapExceeded) as exc_info:
        await svc.execute(req, idempotency_key=None)

    _assert_domain_rejection(exc_info, calls)


async def test_min_notional_reject_survives_metric_failure(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A4 (`order_service.py:245`) — 최소 주문 cost 미달 거절 직전의 계측 실패."""
    from src.trading.schemas import OrderRequest

    calls: list[str] = []
    monkeypatch.setattr(qb_order_rejected_total, "labels", _explode_labels(calls))

    svc = _svc(
        db_session,
        exchange_service=_exchange_stub(min_notional=Decimal("1000")),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=Decimal("0.001"),
        price=Decimal("50000"),  # notional = 50 < 1000
        leverage=20,
        margin_mode="cross",
    )

    with pytest.raises(MinNotionalNotMet) as exc_info:
        await svc.execute(req, idempotency_key=None)

    _assert_domain_rejection(exc_info, calls)


async def test_notional_reject_survives_metric_failure(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A5 (`order_service.py:264`) — 증거금 초과 거절 직전의 계측 실패."""
    from src.trading.schemas import OrderRequest

    calls: list[str] = []
    monkeypatch.setattr(qb_order_rejected_total, "labels", _explode_labels(calls))

    svc = _svc(
        db_session,
        exchange_service=_exchange_stub(balance=Decimal("100")),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.limit,
        quantity=Decimal("0.1"),
        price=Decimal("50000"),  # notional=5000 > 100*20*0.95=1900
        leverage=20,
        margin_mode="cross",
    )

    with pytest.raises(NotionalExceeded) as exc_info:
        await svc.execute(req, idempotency_key=None)

    _assert_domain_rejection(exc_info, calls)


@pytest.mark.parametrize("market_order", [False, True])
async def test_balance_unverified_reject_survives_metric_failure(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount,
    monkeypatch: pytest.MonkeyPatch, market_order: bool,
) -> None:
    """A6 (`:279`) · A7 (`:291`) — live fail-closed 거절 직전의 계측 실패.

    ★**A6/A7 의 근거를 축소해 적는다** (codex G1 BLOCKING#2 · 코드 대조로 확인).
    `BalanceUnverified` 는 `tasks/live_signal.py:3239` 결정론적-거절 튜플에도,
    `:2793` 무재시도 튜플에도 **없다**. 따라서 dispatch 경로의 재시도 거동은 가드 전후로
    **같다** — 이 두 자리의 해로운 귀결은 **H5(HTTP 표면) 하나**다. 그 이상을 주장하지 않는다.
    """
    from src.trading.schemas import OrderRequest

    calls: list[str] = []
    monkeypatch.setattr(qb_order_rejected_total, "labels", _explode_labels(calls))

    live_account = _account_stub(user_id=uuid4(), mode=ExchangeMode.live)
    svc = _svc(
        db_session,
        # A6 = 가격은 있는데 잔고 조회 실패 / A7 = market 인데 mark price 조회 실패
        exchange_service=_exchange_stub(account=live_account, balance=None, mark_price=None),
    )
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market if market_order else OrderType.limit,
        quantity=Decimal("0.001"),
        price=None if market_order else Decimal("50000"),
        leverage=20,
        margin_mode="cross",
    )

    with pytest.raises(BalanceUnverified) as exc_info:
        await svc.execute(req, idempotency_key=None)

    _assert_domain_rejection(exc_info, calls)


async def test_session_closed_reject_survives_metric_failure(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A8 (`order_service.py:303`) — 거래 시간대 밖 거절 직전의 계측 실패."""
    from src.trading.schemas import OrderRequest

    calls: list[str] = []
    monkeypatch.setattr(qb_order_rejected_total, "labels", _explode_labels(calls))

    svc = _svc(db_session, sessions_port=_ClosedSessionsPort())
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )

    with pytest.raises(TradingSessionClosed) as exc_info:
        await svc.execute(req, idempotency_key=None)

    _assert_domain_rejection(exc_info, calls)


async def test_kill_switch_reject_survives_metric_failure(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A9 (`order_service.py:327`) — kill switch 차단 직전의 계측 실패.

    ★이 자리는 `except KillSwitchActive:` 본문 안의 **bare `raise`** 앞이다. 계측이 던지면
    kill-switch 예외가 **삼켜지고** `OSError` 로 바뀐다. 그러면 `live_signal.py:3232` 의
    `except KillSwitchActive` 가 안 돌아 이벤트가 `kill_switched` 로 기록되지 않고,
    `:2793` 무재시도 튜플도 안 걸려 **차단된 주문을 3회 재시도**한다.
    """
    from src.trading.schemas import OrderRequest

    calls: list[str] = []
    monkeypatch.setattr(qb_order_rejected_total, "labels", _explode_labels(calls))

    svc = _svc(db_session, kill_switch=_ActiveKillSwitch())
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )

    with pytest.raises(KillSwitchActive) as exc_info:
        await svc.execute(req, idempotency_key=None)

    _assert_domain_rejection(exc_info, calls)


async def test_idempotency_conflict_reject_survives_metric_failure(
    db_session: AsyncSession, strategy, exchange_account: ExchangeAccount,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A10 (`order_service.py:341`) — idempotency 충돌 거절 직전의 계측 실패.

    ★BL-580 은 이 자리를 「발주 **전** 검증 거절 직후」라고 적었지만 **그렇지 않다** —
    `async with self._session.begin_nested()`(`:335`) + `acquire_idempotency_lock`(`:337`)
    **안**이다. 그리고 `live_signal.py:3249` 는 이 타입일 때만 재시도 없이 종결한다.
    """
    from src.trading.schemas import OrderRequest

    idem_key = f"test-idem-inject-{uuid4()}"
    existing = Order(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
        state=OrderState.pending,
        idempotency_key=idem_key,
        idempotency_payload_hash=b"original-hash",
    )
    db_session.add(existing)
    await db_session.commit()

    calls: list[str] = []
    monkeypatch.setattr(qb_order_rejected_total, "labels", _explode_labels(calls))

    svc = _svc(db_session)
    req = OrderRequest(
        strategy_id=strategy.id,
        exchange_account_id=exchange_account.id,
        symbol="BTC/USDT:USDT",
        side=OrderSide.buy,
        type=OrderType.market,
        quantity=Decimal("0.001"),
        price=None,
    )

    with pytest.raises(IdempotencyConflict) as exc_info:
        await svc.execute(req, idempotency_key=idem_key, body_hash=b"different-hash")

    _assert_domain_rejection(exc_info, calls)
