"""Sprint 26 — LiveSignalSessionService LESSON-019 commit-spy 회귀 테스트.

Sprint 6 (webhook_secret) → Sprint 13 (OrderService) → Sprint 15-A (ExchangeAccount)
패턴 4번째 재발 방어. AsyncMock spy 가 commit 누락 broken bug 의 본질을 직접 검증.

표준 reference: backend/tests/trading/test_webhook_secret_commits.py + test_strategy_commits.py.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.strategy.exceptions import StrategyNotFoundError
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.exceptions import (
    AccountModeNotAllowed,
    InvalidStrategySettings,
    LiveSessionQuotaExceeded,
    StrategySettingsRequired,
)
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
)
from src.trading.schemas import AccountBalanceResponse, RegisterLiveSessionRequest

_VALID_SETTINGS = {
    "schema_version": 1,
    "leverage": 2,
    "margin_mode": "cross",
    "position_size_pct": 10.0,
}


def _make_balance_service(
    *,
    total: Decimal | None = Decimal("10000"),
    free: Decimal | None = Decimal("10000"),
    supported: bool = True,
    reason: str | None = None,
) -> AsyncMock:
    """AccountBalanceService 스텁 — get_balance 가 AccountBalanceResponse 를 돌려준다."""
    service = AsyncMock()
    service.get_balance = AsyncMock(
        return_value=AccountBalanceResponse(
            account_id=uuid4(),
            asset="USDT",
            supported=supported,
            reason=reason,
            total=total,
            free=free,
            fetched_at=datetime.now(UTC),
        )
    )
    return service


def _make_strategy(user_id, settings=_VALID_SETTINGS) -> Strategy:
    return Strategy(
        id=uuid4(),
        user_id=user_id,
        name="t",
        pine_source="//@version=5\nstrategy('t')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
        settings=settings,
    )


def _make_account(user_id, *, exchange=ExchangeName.bybit, mode=ExchangeMode.demo) -> ExchangeAccount:
    return ExchangeAccount(
        id=uuid4(),
        user_id=user_id,
        exchange=exchange,
        mode=mode,
        api_key_encrypted=b"x",
        api_secret_encrypted=b"y",
    )


def _make_session(user_id, strategy_id, account_id) -> LiveSignalSession:
    return LiveSignalSession(
        id=uuid4(),
        user_id=user_id,
        strategy_id=strategy_id,
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        interval=LiveSignalInterval.m5,
    )


def _make_req(strategy_id, account_id) -> RegisterLiveSessionRequest:
    # ★`BTCUSDT` 는 이제 load-bearing 이다 — 미정규화 원문을 넣어야 ingress 정규화가
    # 실제로 도는지 검증된다(BL-454). canonical 로 바꾸지 말 것.
    return RegisterLiveSessionRequest(
        strategy_id=strategy_id,
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        interval="5m",
    )


def test_register_request_normalizes_the_symbol_at_the_boundary() -> None:
    """BL-454 — 스키마 경계에서 한 번 정규화하면 하류는 재검증하지 않아도 된다.

    이 단정이 없으면 `NormalizedSymbol` 타입이 실제로 배선됐는지 아무도 증명하지 못한다.
    """
    req = _make_req(uuid4(), uuid4())
    assert req.symbol == "BTC/USDT"


def test_register_request_rejects_a_symbol_it_cannot_normalize() -> None:
    """정규화 불가 표기는 422 로 거부된다 — 신규 예외 배관 없이 Pydantic 이 처리한다."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RegisterLiveSessionRequest(
            strategy_id=uuid4(),
            exchange_account_id=uuid4(),
            symbol="BTCUSDT.P",
            interval="5m",
        )


@pytest.mark.asyncio
async def test_register_calls_repo_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    """LESSON-019 spy: register() 정상 path 에서 repo.commit() 호출 강제.

    Sprint 6 (webhook_secret) / 13 (OrderService) / 15-A (ExchangeAccount) 4번째 재발 방어.
    """
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    strategy = _make_strategy(user_id)
    account = _make_account(user_id)
    saved = _make_session(user_id, strategy.id, account.id)

    repo = AsyncMock()
    repo.acquire_quota_lock = AsyncMock(return_value=None)
    repo.count_active_by_user = AsyncMock(return_value=0)
    repo.save = AsyncMock(return_value=saved)

    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(return_value=account)

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo,
        balance_service=_make_balance_service(),
    )
    from src.tasks.websocket_task import run_bybit_public_ticker_stream

    delay = MagicMock()
    monkeypatch.setattr(run_bybit_public_ticker_stream, "delay", delay)

    req = _make_req(strategy.id, account.id)
    result = await svc.register(user_id, req)

    repo.save.assert_awaited_once()
    repo.commit.assert_awaited_once()  # ← broken bug 재발 방어
    delay.assert_called_once_with()
    assert result is saved
    # BL-454 — 경계에서 정규화한 값이 실제로 **영속 모델까지** 간다.
    # 스키마 단정만으로는 서비스가 원문을 어딘가 따로 들고 있지 않다는 보장이 없다.
    assert repo.save.await_args is not None
    assert repo.save.await_args.args[0].symbol == "BTC/USDT"


@pytest.mark.asyncio
async def test_register_strategy_not_found_does_not_commit() -> None:
    """ownership 위반 / 미존재 → StrategyNotFoundError + commit 0 (의도치 않은 변경 차단)."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    repo = AsyncMock()
    account_repo = AsyncMock()
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=None)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo,
        balance_service=_make_balance_service(),
    )

    req = _make_req(uuid4(), uuid4())
    with pytest.raises(StrategyNotFoundError):
        await svc.register(user_id, req)

    repo.save.assert_not_called()
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_settings_required_does_not_commit() -> None:
    """codex G.0 P2 #4: strategy.settings is None → StrategySettingsRequired + commit 0."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    strategy = _make_strategy(user_id, settings=None)

    repo = AsyncMock()
    account_repo = AsyncMock()
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo,
        balance_service=_make_balance_service(),
    )

    req = _make_req(strategy.id, uuid4())
    with pytest.raises(StrategySettingsRequired):
        await svc.register(user_id, req)

    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_invalid_settings_does_not_commit() -> None:
    """codex G.0 P2 #4: malformed JSONB → InvalidStrategySettings + commit 0."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    # leverage 가 string — Pydantic ValidationError
    strategy = _make_strategy(user_id, settings={"leverage": "invalid", "margin_mode": "cross"})

    repo = AsyncMock()
    account_repo = AsyncMock()
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo,
        balance_service=_make_balance_service(),
    )

    req = _make_req(strategy.id, uuid4())
    with pytest.raises(InvalidStrategySettings):
        await svc.register(user_id, req)

    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_account_mode_live_rejected() -> None:
    """codex G.0 P2 #1: mode=live → AccountModeNotAllowed (Bybit Demo 한정)."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    strategy = _make_strategy(user_id)
    # mode=live → AccountModeNotAllowed
    account = _make_account(user_id, mode=ExchangeMode.live)

    repo = AsyncMock()
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)
    # W4 게이트가 AccountModeNotAllowed 보다 앞서므로, stub-block 을 검증하려면
    # stable user_repo 를 주입해 demo-stability 게이트를 통과시킨다.
    user_repo = AsyncMock()
    user_repo.get_created_at = AsyncMock(
        return_value=datetime.now(UTC) - timedelta(days=3650)
    )

    svc = LiveSignalSessionService(
        repo=repo,
        account_repo=account_repo,
        strategy_repo=strategy_repo,
        balance_service=_make_balance_service(),
        user_repo=user_repo,
    )

    req = _make_req(strategy.id, account.id)
    with pytest.raises(AccountModeNotAllowed):
        await svc.register(user_id, req)

    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_exchange_okx_rejected() -> None:
    """codex G.0 P2 #1: exchange=okx → AccountModeNotAllowed (Bybit only)."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    strategy = _make_strategy(user_id)
    account = _make_account(user_id, exchange=ExchangeName.okx, mode=ExchangeMode.demo)

    repo = AsyncMock()
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo,
        balance_service=_make_balance_service(),
    )

    req = _make_req(strategy.id, account.id)
    with pytest.raises(AccountModeNotAllowed):
        await svc.register(user_id, req)

    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_quota_exceeded_does_not_commit() -> None:
    """codex G.0 P3 #3: 사용자별 active session ≥ 5 → LiveSessionQuotaExceeded."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    strategy = _make_strategy(user_id)
    account = _make_account(user_id)

    repo = AsyncMock()
    repo.acquire_quota_lock = AsyncMock(return_value=None)
    repo.count_active_by_user = AsyncMock(return_value=5)  # 한도 초과

    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo,
        balance_service=_make_balance_service(),
    )

    req = _make_req(strategy.id, account.id)
    with pytest.raises(LiveSessionQuotaExceeded):
        await svc.register(user_id, req)

    repo.save.assert_not_called()
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_deactivate_calls_repo_commit() -> None:
    """LESSON-019 spy: deactivate() 가 repo.commit() 호출 강제 (rowcount > 0 시)."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    sess = _make_session(user_id, uuid4(), uuid4())

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=sess)
    repo.deactivate = AsyncMock(return_value=1)

    account_repo = AsyncMock()
    strategy_repo = AsyncMock()

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo,
        balance_service=_make_balance_service(),
    )

    await svc.deactivate(user_id, sess.id)

    repo.deactivate.assert_awaited_once()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_deactivate_already_inactive_no_commit() -> None:
    """idempotent: rowcount=0 (이미 deactivated) → commit 0. error 도 안 함."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    sess = _make_session(user_id, uuid4(), uuid4())
    sess.is_active = False

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=sess)
    repo.deactivate = AsyncMock(return_value=0)  # 이미 deactivated

    account_repo = AsyncMock()
    strategy_repo = AsyncMock()

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo,
        balance_service=_make_balance_service(),
    )

    await svc.deactivate(user_id, sess.id)

    repo.deactivate.assert_awaited_once()
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_deactivate_ownership_violation_404() -> None:
    """다른 user 의 session deactivate 시도 → StrategyNotFoundError (정보 누설 방어)."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    other_user = uuid4()
    sess = _make_session(other_user, uuid4(), uuid4())  # 다른 user 소유

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=sess)

    account_repo = AsyncMock()
    strategy_repo = AsyncMock()

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo,
        balance_service=_make_balance_service(),
    )

    with pytest.raises(StrategyNotFoundError):
        await svc.deactivate(user_id, sess.id)

    repo.deactivate.assert_not_called()
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_survives_ticker_kick_failure(monkeypatch) -> None:
    """ticker 킥은 best-effort — broker 장애로 delay 가 죽어도 등록은 성공한다.

    실패 시 beat reconcile(5분)이 기동을 보증하므로 500 오염 금지 (codex 최종
    diff 리뷰 반영).
    """
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    strategy = _make_strategy(user_id)
    account = _make_account(user_id)
    saved = _make_session(user_id, strategy.id, account.id)

    repo = AsyncMock()
    repo.acquire_quota_lock = AsyncMock(return_value=None)
    repo.count_active_by_user = AsyncMock(return_value=0)
    repo.save = AsyncMock(return_value=saved)

    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(return_value=account)

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo,
        balance_service=_make_balance_service(),
    )
    from src.tasks.websocket_task import run_bybit_public_ticker_stream

    delay = MagicMock(side_effect=RuntimeError("broker down"))
    monkeypatch.setattr(run_bybit_public_ticker_stream, "delay", delay)

    result = await svc.register(user_id, _make_req(strategy.id, account.id))

    repo.commit.assert_awaited_once()
    delay.assert_called_once_with()
    assert result is saved
