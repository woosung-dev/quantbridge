# 거래소 청산 원장 스윕의 DB 불요 회귀 계약을 검증한다.

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.trading.models import ExchangeMode, ExchangeName, ExitClassification, OrderSide
from src.trading.providers import ClosedOrderMeta, ClosedPnlSnapshot


def _account() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"k",
        api_secret_encrypted=b"s",
        passphrase_encrypted=None,
    )


def _snapshot(
    order_id: str,
    *,
    created_at_ms: int | None,
    closed_pnl: str = "1",
    # ★거래소 원문이 기본값이다. Bybit closed-pnl 은 `BTCUSDT` 를 돌려준다(실측 —
    # trading.exchange_exits 4행 전부 symbol='BTCUSDT'). 예전 기본값 `BTC/USDT` 는
    # 우리 canonical 표기라, 원장 쪽 피연산자를 우리 표기로 위장해 BL-464(귀속 축이
    # 심볼 공간 불일치로 죽어 있음)를 한 스프린트 내내 안 보이게 만들었다.
    symbol: str | None = "BTCUSDT",
) -> ClosedPnlSnapshot:
    raw = {
        "orderId": order_id,
        "createdTime": str(created_at_ms) if created_at_ms is not None else None,
        "updatedTime": str(created_at_ms or 0),
        "closedSize": "1",
        "closedPnl": closed_pnl,
        "avgEntryPrice": "100",
        "avgExitPrice": "101",
        "cumExitValue": "101",
    }
    return ClosedPnlSnapshot(
        order_id=order_id,
        closed_pnl=Decimal(closed_pnl),
        closed_size=Decimal("1"),
        avg_exit_price=Decimal("101"),
        updated_at_ms=created_at_ms,
        symbol=symbol,
        side="Sell",
        avg_entry_price=Decimal("100"),
        created_at_ms=created_at_ms,
        raw=raw,
    )


def _order(
    account_id: UUID,
    exchange_order_id: str,
    *,
    synced: bool = False,
    reduce_only: bool = True,
    strategy_id: UUID | None = None,
) -> SimpleNamespace:
    # symbol 은 우리 canonical(ccxt unified) 이다. 거래소 원문(`_snapshot`)과 다른
    # 공간이라는 것이 BL-464 의 요점이므로 여기서 임의로 맞추지 않는다.
    return SimpleNamespace(
        id=uuid4(),
        strategy_id=strategy_id or uuid4(),
        exchange_account_id=account_id,
        exchange_order_id=exchange_order_id,
        symbol="BTC/USDT",
        side=OrderSide.buy,
        reduce_only=reduce_only,
        quantity=Decimal("1"),
        filled_price=Decimal("100"),
        filled_at=datetime(2026, 7, 1, tzinfo=UTC),
        realized_pnl_synced_at=datetime(2026, 7, 1, tzinfo=UTC) if synced else None,
        realized_pnl=Decimal("0"),
    )


class _State:
    def __init__(self, accounts: list[SimpleNamespace]) -> None:
        self.accounts = accounts
        self.rows = []
        self.pending_rows: list[SimpleNamespace] = []
        self.commits = 0
        self.row_hashes: set[str] = set()
        self.matched_orders: list[SimpleNamespace] = []
        self.attribution_orders: list[SimpleNamespace] = []
        # BL-457 — 실재하는 우리 Order.id 집합. 비어 있으면 link-id 만으로는
        # 소유를 주장하지 못한다.
        self.existing_order_ids: set[UUID] = set()
        self.unsynced_orders: list[SimpleNamespace] = []
        self.synced_orders: list[SimpleNamespace] = []
        self.backfills: list[tuple[UUID, Decimal]] = []
        self.resyncs: list[tuple[UUID, Decimal]] = []


def _sessionmaker(state: _State):
    @asynccontextmanager
    async def context():
        session = MagicMock()

        async def commit() -> None:
            # ★적재는 커밋으로만 원장에 보인다. 스윕이 upsert 뒤 commit 을 빼먹으면
            # 알림·백필이 새 세션으로 되읽어 아무것도 못 찾는데, 페이크가 커밋과
            # 무관하게 행을 노출하면 그 결함이 테스트를 통과한다.
            state.commits += 1
            state.rows.extend(state.pending_rows)
            state.pending_rows.clear()

        session.commit = AsyncMock(side_effect=commit)
        yield session

    class SessionMaker:
        def __call__(self):
            return context()

    return SessionMaker()


def _install_repositories(monkeypatch: pytest.MonkeyPatch, state: _State) -> None:
    import src.tasks.trading as trading_mod

    class AccountRepository:
        def __init__(self, session: MagicMock) -> None:
            self.session = session

        async def list_by_exchange(self, exchange: ExchangeName):
            return state.accounts

    class ExitRepository:
        def __init__(self, session: MagicMock) -> None:
            self.session = session

        async def upsert_rows(self, rows):
            added = []
            for row in rows:
                if row.row_hash not in state.row_hashes:
                    state.row_hashes.add(row.row_hash)
                    state.pending_rows.append(row)
                    added.append(row.row_hash)
            return added

        async def aggregate_closed_pnl(self, account_id: UUID, order_ids):
            sums: dict[str, Decimal] = {}
            for row in state.rows:
                if row.exchange_order_id in order_ids:
                    sums[row.exchange_order_id] = sums.get(
                        row.exchange_order_id, Decimal("0")
                    ) + row.closed_pnl
            return sums

        async def list_by_row_hashes(self, account_id: UUID, hashes):
            return [row for row in state.rows if row.row_hash in hashes]

    class OrderRepository:
        def __init__(self, session: MagicMock) -> None:
            self.session = session

        async def list_by_exchange_order_ids(self, account_id: UUID, order_ids):
            return [order for order in state.matched_orders if order.exchange_order_id in order_ids]

        async def list_filled_for_attribution(self, account_id: UUID):
            return state.attribution_orders

        async def list_existing_ids(self, account_id: UUID, order_ids) -> frozenset[UUID]:
            # ★기본이 빈 집합이다. link-id 로 `ours` 를 주장하려는 테스트는 반드시
            # `state.existing_order_ids` 에 명시적으로 넣어야 한다 — 엄격함이 하네스에
            # 드러나야 BL-457 회귀가 조용히 통과하지 못한다.
            return frozenset(state.existing_order_ids) & frozenset(order_ids)

        async def list_unsynced_reduce_only(self, account_id: UUID):
            return state.unsynced_orders

        async def backfill_exchange_realized_pnl(self, order_id: UUID, *, realized_pnl, synced_at):
            state.backfills.append((order_id, realized_pnl))
            return 1

        async def list_synced_reduce_only(self, account_id: UUID):
            return state.synced_orders

        async def resync_exchange_realized_pnl(self, order_id: UUID, *, realized_pnl, synced_at):
            # 실제 CAS 는 값이 같으면 rowcount 0 이다. 페이크도 같은 계약을 흉내낸다.
            stored = next(
                (o.realized_pnl for o in state.synced_orders if o.id == order_id), None
            )
            if stored == realized_pnl:
                return 0
            state.resyncs.append((order_id, realized_pnl))
            return 1

    monkeypatch.setattr(trading_mod, "ExchangeAccountRepository", AccountRepository)
    monkeypatch.setattr(trading_mod, "ExchangeExitRepository", ExitRepository)
    monkeypatch.setattr(trading_mod, "OrderRepository", OrderRepository)
    monkeypatch.setattr(
        trading_mod,
        "EncryptionService",
        MagicMock(return_value=SimpleNamespace(decrypt=lambda value: "secret")),
    )


@pytest.mark.asyncio
async def test_sweep_reads_only_the_recent_seven_day_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """범위 축소 — 계정당 창은 [now-7d, now] 하나뿐이다.

    과거로 훑는 창과 워터마크를 걷어냈으므로 계정당 조회는 정확히 1회여야 한다.
    """
    import src.tasks.trading as trading_mod
    from src.tasks.trading import _EXIT_WINDOW_MS, _datetime_to_ms

    now = datetime(2026, 7, 25, tzinfo=UTC)
    now_ms = _datetime_to_ms(now)
    state = _State([_account()])
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(return_value=[]),
        fetch_closed_order_meta=AsyncMock(),
    )

    await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=now
    )

    assert provider.fetch_closed_pnl_window.await_count == 1
    kwargs = provider.fetch_closed_pnl_window.await_args.kwargs
    assert (kwargs["start_ms"], kwargs["end_ms"]) == (now_ms - _EXIT_WINDOW_MS, now_ms)


@pytest.mark.asyncio
async def test_sweep_skips_meta_when_every_row_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod

    account = _account()
    state = _State([account])
    state.matched_orders = [_order(account.id, "our-close")]
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(return_value=[_snapshot("our-close", created_at_ms=1)]),
        fetch_closed_order_meta=AsyncMock(),
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    assert provider.fetch_closed_order_meta.await_count == 0
    assert summary == {
        "accounts": 1,
        "inserted": 1,
        "backfilled": 0,
        "resynced": 0,
        "alerted": 0,
    }
    assert state.rows[0].classification == ExitClassification.ours
    # 원장 커밋 + 백필/재동기화 커밋. 어느 쪽이 빠져도 후속 세션이 빈 원장을 읽는다.
    assert state.commits == 2


@pytest.mark.asyncio
async def test_sweep_continues_when_meta_lookup_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod

    state = _State([_account()])
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(return_value=[_snapshot("external", created_at_ms=1)]),
        fetch_closed_order_meta=AsyncMock(side_effect=RuntimeError("metadata unavailable")),
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    # 미매칭 행이 있으면 창당 한 번 보강을 시도한다 — 창이 하나이므로 1회.
    assert provider.fetch_closed_order_meta.await_count == 1
    assert summary["inserted"] == 1
    assert state.rows[0].classification == ExitClassification.unknown


@pytest.mark.asyncio
async def test_sweep_aggregates_ledger_rows_before_backfill(monkeypatch: pytest.MonkeyPatch) -> None:
    """백필은 이번 조회 결과가 아니라 **원장 전체**를 집계해야 한다.

    한 청산 주문이 여러 행으로 쪼개지고 그 행들이 서로 다른 주기에 적재되면, 이번
    조회에는 일부만 담긴다. 단일 fetch 결과를 CAS 하면 부분합이 영구 고정된다.
    → 이전 주기 행을 원장에 미리 심어두고, 이번 창은 나머지 한 행만 돌려준다.
    합계 -0.05 는 원장을 집계할 때만 나온다.
    """
    import src.tasks.trading as trading_mod

    now = datetime(2026, 7, 25, tzinfo=UTC)
    account = _account()
    state = _State([account])
    state.unsynced_orders = [_order(account.id, "split-close")]
    # 이전 주기에 이미 커밋된 분할 행. 이번 조회에는 나타나지 않는다.
    state.rows.append(
        SimpleNamespace(
            exchange_order_id="split-close",
            closed_pnl=Decimal("-0.02"),
            row_hash="previous-cycle-row",
        )
    )
    state.row_hashes.add("previous-cycle-row")
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(
            return_value=[_snapshot("split-close", created_at_ms=2, closed_pnl="-0.03")]
        ),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=now
    )

    assert summary["inserted"] == 1, "이번 창의 행 하나만 새로 들어가야 한다"
    assert summary["backfilled"] == 1
    assert state.backfills == [(state.unsynced_orders[0].id, Decimal("-0.05"))]


@pytest.mark.asyncio
async def test_sweep_alerts_only_new_external_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod

    state = _State([_account()])
    _install_repositories(monkeypatch, state)
    send_alert = AsyncMock(return_value={"slack": True, "telegram": True})
    monkeypatch.setattr(trading_mod, "send_rule_alert", send_alert)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(return_value=[_snapshot("external", created_at_ms=1)]),
        fetch_closed_order_meta=AsyncMock(return_value={"external": ClosedOrderMeta("external", "CreateByUser", None, None)}),
    )

    first = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )
    second = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    assert first["alerted"] == 1
    assert second["alerted"] == 0
    assert send_alert.await_count == 1


@pytest.mark.asyncio
async def test_sweep_skips_rows_without_created_or_updated_time(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod

    state = _State([_account()])
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(return_value=[_snapshot("missing-time", created_at_ms=None), _snapshot("valid", created_at_ms=1)]),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    assert summary["inserted"] == 1
    assert [row.exchange_order_id for row in state.rows] == ["valid"]


@pytest.mark.asyncio
async def test_sweep_isolates_one_account_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.tasks.trading as trading_mod

    state = _State([_account(), _account()])
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(side_effect=[RuntimeError("first failed"), []]),
        fetch_closed_order_meta=AsyncMock(),
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    # 첫 계정은 조회에서 죽고, 둘째 계정은 자기 창을 정상 처리한다(계정당 1창).
    assert provider.fetch_closed_pnl_window.await_count == 2
    assert summary == {
        "accounts": 2,
        "inserted": 0,
        "backfilled": 0,
        "resynced": 0,
        "alerted": 0,
    }


@pytest.mark.asyncio
async def test_sweep_corrects_a_partial_sum_frozen_by_the_post_fill_refresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """체결 직후 refresh 는 원장을 거치지 않고 단일 조회 결과를 CAS 한다.

    분할 행 중 첫 행만 보이는 순간에 걸리면 부분합이 synced 로 고정되고, 미동기화
    술어를 쓰는 백필 경로는 그 주문을 영영 건너뛴다. 원장 합계와 다르면 정정해야 한다.
    """
    import src.tasks.trading as trading_mod

    account = _account()
    state = _State([account])
    frozen = _order(account.id, "split-close", synced=True)
    frozen.realized_pnl = Decimal("-0.02")  # refresh 가 고정한 부분합
    state.matched_orders = [frozen]
    state.synced_orders = [frozen]
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(
            return_value=[
                _snapshot("split-close", created_at_ms=1, closed_pnl="-0.02"),
                _snapshot("split-close", created_at_ms=2, closed_pnl="-0.03"),
            ]
        ),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    assert summary["resynced"] == 1
    assert state.resyncs == [(frozen.id, Decimal("-0.05"))]


@pytest.mark.asyncio
async def test_sweep_does_not_resync_when_the_ledger_agrees(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """값이 같으면 CAS rowcount 가 0 이라 정정 경로는 멱등하다."""
    import src.tasks.trading as trading_mod

    account = _account()
    state = _State([account])
    agreed = _order(account.id, "settled", synced=True)
    agreed.realized_pnl = Decimal("1")
    state.matched_orders = [agreed]
    state.synced_orders = [agreed]
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(return_value=[_snapshot("settled", created_at_ms=1)]),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    assert summary["resynced"] == 0
    assert state.resyncs == []


@pytest.mark.asyncio
async def test_sweep_counts_rows_it_cannot_persist_as_malformed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """원장 필수 필드를 못 만든 행은 로그만 남기면 소실이 관측되지 않는다."""
    import src.tasks.trading as trading_mod

    state = _State([_account()])
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(
            return_value=[_snapshot("no-time", created_at_ms=None)]
        ),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )
    counter = trading_mod.qb_closed_pnl_backfill_total.labels(outcome="malformed_row")
    before = counter._value.get()

    await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    assert counter._value.get() == before + 1
    assert state.rows == []


@pytest.mark.asyncio
async def test_sweep_does_not_claim_an_unmatched_row_as_ours_without_an_order_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BL-457 — UUID 모양 orderLinkId 만으로는 소유를 주장하지 못한다.

    핵심은 라벨이 아니라 **알림**이다. `_alert_new_exchange_exits` 는
    `classification != ours` 로 거르므로, 형식만 보고 `ours` 를 붙이면 UUID 모양 client
    order id 를 단 외부 청산이 운영자 알림에서 조용히 빠진다. 그래서 라벨과 함께
    알림이 실제로 발화하는 것까지 단정한다.
    """
    import src.tasks.trading as trading_mod

    state = _State([_account()])
    _install_repositories(monkeypatch, state)
    send_alert = AsyncMock(return_value={"slack": True, "telegram": True})
    monkeypatch.setattr(trading_mod, "send_rule_alert", send_alert)
    # 우리 DB 에 없는 UUID — 외부 도구가 UUID 모양 client id 를 단 경우다.
    foreign_uuid = str(uuid4())
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(
            return_value=[_snapshot("exchange-exit", created_at_ms=1)]
        ),
        fetch_closed_order_meta=AsyncMock(
            return_value={
                "exchange-exit": ClosedOrderMeta("exchange-exit", "CreateByUser", None, foreign_uuid)
            }
        ),
    )

    unverified = trading_mod.qb_exchange_exit_link_unverified_total
    before = unverified._value.get()

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    # `external_manual` 도 아니다 — 사람은 UUID4 를 타이핑하지 않는다.
    assert state.rows[0].classification == ExitClassification.unknown
    assert summary["alerted"] == 1
    assert send_alert.await_count == 1
    # 라벨이 소유를 주장하지 않고 떨어진 사실 자체가 관측돼야 한다. 이게 없으면
    # "우리 주문 이력이 사라졌다" 와 "외부 도구가 UUID 를 쓴다" 를 구분할 수 없다.
    assert unverified._value.get() == before + 1


@pytest.mark.asyncio
async def test_sweep_claims_an_unmatched_row_as_ours_when_the_order_row_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """실재 확인이 되면 거래소 주문 id 매칭이 없어도 우리 것이다.

    ★이 경로가 살아 있어야 하는 이유 — 도달하는 행은 정의상 `state == filled` 매칭에
    실패한 주문(`submitted` 등)이다. membership 쿼리에 `state` 필터를 넣으면 바로 이
    테스트가 깨진다.
    """
    import src.tasks.trading as trading_mod

    account = _account()
    state = _State([account])
    our_order = _order(account.id, "not-yet-reconciled")
    state.existing_order_ids = {our_order.id}
    _install_repositories(monkeypatch, state)
    send_alert = AsyncMock(return_value={"slack": True, "telegram": True})
    monkeypatch.setattr(trading_mod, "send_rule_alert", send_alert)
    provider = SimpleNamespace(
        fetch_closed_pnl_window=AsyncMock(
            return_value=[_snapshot("exchange-exit", created_at_ms=1)]
        ),
        fetch_closed_order_meta=AsyncMock(
            return_value={
                "exchange-exit": ClosedOrderMeta(
                    "exchange-exit", "CreateByUser", None, str(our_order.id)
                )
            }
        ),
    )

    summary = await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=datetime(2026, 7, 25, tzinfo=UTC)
    )

    assert state.rows[0].classification == ExitClassification.ours
    assert summary["alerted"] == 0
    assert send_alert.await_count == 0


@pytest.mark.asyncio
async def test_sweep_infers_the_strategy_across_the_exchange_symbol_space(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BL-464 — 귀속 비교는 거래소 표기와 우리 표기를 같은 공간에서 해야 한다.

    원장 쪽 심볼은 Bybit 원문(`BTCUSDT`)이고 우리 주문 심볼은 canonical
    (`BTC/USDT`)이다. `attribute_exit` 이 두 문자열을 그대로 동등 비교하면 어떤
    표본에서도 매칭이 성립하지 않아 `inferred` 축이 **구조적으로 죽는다** — 데이터가
    있어도 항상 `none` 이다. 그래서 "0행이라 0" 과 구분되는 실패다.

    이 테스트는 매칭 가능한 진입 주문을 실제로 넣고 `inferred` 를 요구한다.
    """
    import src.tasks.trading as trading_mod
    from src.tasks.trading import _datetime_to_ms
    from src.trading.models import ExitAttribution

    now = datetime(2026, 7, 25, tzinfo=UTC)
    exit_at_ms = _datetime_to_ms(datetime(2026, 7, 20, tzinfo=UTC))
    account = _account()
    strategy_id = uuid4()
    state = _State([account])
    # 진입 주문 — reduce_only=False + filled_price == snapshot.avg_entry_price(100).
    # 순포지션이 0 이 아니어야 하므로 buy 1 계약만 둔다.
    state.attribution_orders = [
        _order(account.id, "entry-order", reduce_only=False, strategy_id=strategy_id)
    ]
    _install_repositories(monkeypatch, state)
    provider = SimpleNamespace(
        # 매칭되지 않는 청산 행 — 그래서 귀속 추정 경로로 들어간다.
        fetch_closed_pnl_window=AsyncMock(
            return_value=[_snapshot("exchange-exit", created_at_ms=exit_at_ms)]
        ),
        fetch_closed_order_meta=AsyncMock(return_value={}),
    )

    await trading_mod._sweep_closed_pnl_with_session(
        _sessionmaker(state), provider=provider, now=now
    )

    assert len(state.rows) == 1
    assert state.rows[0].attribution_confidence == ExitAttribution.inferred
    assert state.rows[0].attributed_strategy_id == strategy_id
