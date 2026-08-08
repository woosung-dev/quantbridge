# `live_session_admin status` 의 계정 축 회귀 — 거래소 조회는 계정 **행**이 아니라 **실제 계정** 단위다.

from __future__ import annotations

from contextlib import asynccontextmanager
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

import scripts.live_session_admin as admin
from src.trading.models import ExchangeName


def _account(label: str, *, exchange_uid: str | None, read_only: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        label=label,
        exchange_uid=exchange_uid,
        read_only=read_only,
        exchange=ExchangeName.bybit,
    )


def _resting(order_link_id: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        order_id="ex-order-1",
        order_link_id=order_link_id,
        side="buy",
        kind="other",
        qty=Decimal("0.029"),
        trigger_price=Decimal("100"),
    )


class _Result:
    """`.mappings().all()` 과 `.all()` 두 소비 형태를 모두 흉내낸다."""

    def __init__(self, rows: list) -> None:
        self._rows = rows

    def mappings(self) -> _Result:
        return self

    def all(self) -> list:
        return self._rows


class _Session:
    def __init__(self, ledger_order_ids: list[UUID]) -> None:
        self._ledger_order_ids = ledger_order_ids

    async def execute(self, stmt: object) -> _Result:
        sql = str(stmt)
        if "live_signal_sessions" in sql:
            return _Result([])
        if "trading.orders" in sql:
            return _Result([(str(order_id),) for order_id in self._ledger_order_ids])
        raise AssertionError(f"예상 못 한 질의: {sql}")


def _install(
    monkeypatch: pytest.MonkeyPatch,
    *,
    accounts: list[SimpleNamespace],
    resting: list[SimpleNamespace],
    ledger_order_ids: list[UUID],
) -> list[tuple[UUID, bool | None]]:
    """`_cmd_status` 의 바깥 의존을 전부 페이크로 갈아끼우고 조회 호출을 기록한다.

    ★거래소는 **치지 않는다**. 같은 실제 계정을 가리키는 행이 둘이면 거래소는 두 번 다
    **같은 주문**을 돌려주므로, 프로바이더는 creds 와 무관하게 같은 목록을 준다 —
    그것이 2배 계상의 기전 그 자체다.
    """
    session = _Session(ledger_order_ids)

    @asynccontextmanager
    async def _ctx():
        yield session

    class _SessionMaker:
        def __call__(self):
            return _ctx()

    engine = SimpleNamespace(dispose=AsyncMock())
    monkeypatch.setattr(admin, "create_worker_engine_and_sm", lambda: (engine, _SessionMaker()))

    class _Repo:
        def __init__(self, session: object) -> None:
            self.session = session

        async def list_by_exchange(self, exchange: ExchangeName) -> list[SimpleNamespace]:
            assert exchange is ExchangeName.bybit
            return accounts

    monkeypatch.setattr(admin, "ExchangeAccountRepository", _Repo)

    class _AccountService:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def get_credentials_for_order(self, account_id: UUID) -> SimpleNamespace:
            return SimpleNamespace(account_id=account_id)

    monkeypatch.setattr(admin, "ExchangeAccountService", _AccountService)
    monkeypatch.setattr(admin, "get_encryption_service", lambda: SimpleNamespace())

    calls: list[tuple[UUID, bool | None]] = []

    class _Provider:
        async def fetch_open_positions(self, creds: SimpleNamespace, symbol: str) -> list:
            return []

        async def fetch_open_conditional_orders(
            self, creds: SimpleNamespace, symbol: str, *, reduce_only: bool | None = True
        ) -> list[SimpleNamespace]:
            calls.append((creds.account_id, reduce_only))
            return resting

    monkeypatch.setattr(admin, "get_bybit_futures_provider", lambda: _Provider())
    return calls


@pytest.mark.asyncio
async def test_status_counts_resting_orders_once_per_real_exchange_account(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """[BL-651] — 같은 `exchange_uid` 를 공유하는 계정 행 2개는 거래소 조회 1회다.

    실측(2026-08-08, 소크 down 직전): `RESTING_CONDITIONAL=2` 인데 실제 조건부 주문은
    **1건**이었다 — 같은 `link=464fc5ed` 가 `bybit demo` · `bybit demo- aaa` 두
    계정으로 계상됐다. flatten 직후엔 `=4` 인데 실제 2건으로, **정확히 2배가 두 번**
    재현됐다.

    수리 전 이 테스트는 `RESTING_CONDITIONAL=2` · 조회 2회로 red 다.
    """
    uid = "558689281"
    primary = _account("bybit demo", exchange_uid=uid, read_only=False)
    mirror = _account("bybit demo- aaa", exchange_uid=uid, read_only=True)
    link = uuid4()
    calls = _install(
        monkeypatch,
        accounts=[primary, mirror],
        resting=[_resting(str(link))],
        ledger_order_ids=[link],
    )

    await admin._cmd_status("BTC/USDT")

    out = capsys.readouterr().out
    assert "RESTING_CONDITIONAL=1" in out
    assert "FOREIGN_RESTING=0" in out
    assert "EXCLUSIVE=YES" in out
    assert "QUIET=NO" in out
    # 거래소를 정확히 한 번, **주문을 낼 수 있는 행**의 자격으로 친다.
    # `reduce_only=None` 은 협상 불가다 — 기본값 `True` 는 TP/SL 만 주는데,
    # 오염을 만드는 것은 reduce-only 가 **아닌** 조건부 진입이다.
    assert calls == [(primary.id, None)]


@pytest.mark.asyncio
async def test_status_still_flags_a_foreign_resting_order_after_dedup(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """음성 대조 — 계정 축을 접어도 **판별력은 그대로**다.

    dedup 이 「거부를 못 하게 만드는 완화」가 아니라 「개수를 바로잡는 정정」임을
    보이려면, 원장이 소유를 주장 못 하는 resting 이 그대로 잡혀야 한다.
    """
    uid = "558689281"
    primary = _account("bybit demo", exchange_uid=uid, read_only=False)
    mirror = _account("bybit demo- aaa", exchange_uid=uid, read_only=True)
    _install(
        monkeypatch,
        accounts=[primary, mirror],
        resting=[_resting("a-link-this-ledger-never-issued")],
        ledger_order_ids=[uuid4()],
    )

    await admin._cmd_status("BTC/USDT")

    out = capsys.readouterr().out
    assert "RESTING_CONDITIONAL=1" in out
    assert "FOREIGN_RESTING=1" in out
    assert "EXCLUSIVE=NO" in out


@pytest.mark.asyncio
async def test_status_keeps_accounts_whose_exchange_uid_is_unknown(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`exchange_uid` 가 `None` 인 행은 서로 묶지 않는다 — 실체를 모르기 때문이다."""
    first = _account("uid 미상 A", exchange_uid=None)
    second = _account("uid 미상 B", exchange_uid=None)
    calls = _install(monkeypatch, accounts=[first, second], resting=[], ledger_order_ids=[])

    await admin._cmd_status("BTC/USDT")

    out = capsys.readouterr().out
    assert "RESTING_CONDITIONAL=0" in out
    assert "QUIET=YES" in out
    assert [account_id for account_id, _ in calls] == [first.id, second.id]
