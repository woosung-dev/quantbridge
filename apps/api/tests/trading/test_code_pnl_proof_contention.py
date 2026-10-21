"""별도 DB 연결의 실제 rowlock 대기와 strict PnL 증거 충돌 보존을 검증한다."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from uuid import uuid4

import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    Order,
    OrderSide,
    OrderState,
    OrderType,
)
from src.trading.providers import CodeClosedPnlEvidence, closed_pnl_raw_hash
from src.trading.repositories.order_repository import OrderRepository


@pytest.mark.parametrize("first_commits", [True, False], ids=["commit", "rollback"])
async def test_concurrent_code_pnl_proofs_preserve_committed_context(_test_engine, first_commits):
    """A가 잡은 rowlock을 서버가 증언한 뒤 B를 진행시킨다. seed는 자기 UUID만 정리한다."""
    maker = async_sessionmaker(_test_engine, expire_on_commit=False)
    user_id, strategy_id, account_id, order_id = (uuid4() for _ in range(4))
    first_time = datetime(2026, 10, 22, tzinfo=UTC)
    second_time = first_time + timedelta(seconds=1)
    raw = {
        "orderId": str(order_id),
        "symbol": "BTCUSDT",
        "side": "Sell",
        "execType": "Trade",
        "closedSize": "0.3",
        "closedPnl": "-1.25",
        "updatedTime": "1",
    }
    proof_a = CodeClosedPnlEvidence(
        account_id,
        str(order_id),
        "BTCUSDT",
        OrderSide.sell,
        D(".3"),
        D("-1.25"),
        closed_pnl_raw_hash(raw),
    )
    proof_b = replace(proof_a, raw_hash=closed_pnl_raw_hash({**raw, "updatedTime": "2"}))
    ready = asyncio.Event()
    waiter_pid = None
    waiter = None
    try:
        async with maker() as seed:
            seed.add(User(id=user_id, auth_subject=f"pnl-contention-{user_id}"))
            await seed.flush()
            seed.add(
                Strategy(
                    id=strategy_id,
                    user_id=user_id,
                    name="PnL proof contention",
                    pine_source="// fake",
                    parse_status=ParseStatus.ok,
                    pine_version=PineVersion.v5,
                )
            )
            seed.add(
                ExchangeAccount(
                    id=account_id,
                    user_id=user_id,
                    exchange=ExchangeName.bybit,
                    mode=ExchangeMode.demo,
                    api_key_encrypted=b"fake",
                    api_secret_encrypted=b"fake",
                )
            )
            await seed.flush()
            seed.add(
                Order(
                    id=order_id,
                    strategy_id=strategy_id,
                    exchange_account_id=account_id,
                    symbol="BTC/USDT",
                    side=OrderSide.sell,
                    type=OrderType.market,
                    quantity=D(1),
                    filled_quantity=D(".3"),
                    filled_price=D(100),
                    filled_at=first_time,
                    state=OrderState.cancelled,
                    reduce_only=True,
                    exchange_order_id=str(order_id),
                    risk_context={
                        "session_id": str(uuid4()),
                        "generation": 1,
                        "role": "close",
                        "fixture_metadata": {"preserved": True},
                    },
                )
            )
            await seed.commit()

        async def competing_proof():
            nonlocal waiter_pid
            async with maker() as second:
                await second.execute(text("SET LOCAL statement_timeout = '5000ms'"))
                waiter_pid = await second.scalar(text("SELECT pg_backend_pid()"))
                repo = OrderRepository(second)
                # identity map에 A commit 전의 context를 일부러 보관한다.
                stale = await repo.get_by_id(order_id)
                assert stale is not None and stale.realized_pnl_synced_at is None
                assert "code_pnl_evidence" not in stale.risk_context
                ready.set()
                changed = await repo.backfill_exchange_realized_pnl(
                    order_id,
                    realized_pnl=proof_b.pnl,
                    synced_at=second_time,
                    code_evidence=proof_b,
                )
                await second.commit()
                return changed

        async with maker() as first:
            await first.execute(text("SET LOCAL statement_timeout = '5000ms'"))
            blocker_pid = await first.scalar(text("SELECT pg_backend_pid()"))
            assert (
                await OrderRepository(first).backfill_exchange_realized_pnl(
                    order_id,
                    realized_pnl=proof_a.pnl,
                    synced_at=first_time,
                    code_evidence=proof_a,
                )
                == 1
            )
            waiter = asyncio.create_task(competing_proof())
            await asyncio.wait_for(ready.wait(), timeout=3)
            assert waiter_pid is not None and waiter_pid != blocker_pid
            async with asyncio.timeout(3):
                while True:
                    blockers = await first.scalar(
                        text("SELECT pg_blocking_pids(:pid)"), {"pid": waiter_pid}
                    )
                    if blocker_pid in blockers:
                        break
                    if waiter.done():
                        await waiter
                        pytest.fail("두 번째 연결이 첫 번째 rowlock을 기다리지 않았습니다")
                    await asyncio.sleep(0.01)
            assert not waiter.done()
            if first_commits:
                await first.commit()
            else:
                await first.rollback()
            assert await asyncio.wait_for(waiter, timeout=5) == (0 if first_commits else 1)

        async with maker() as verification:
            actual = await OrderRepository(verification).get_by_id(order_id)
            assert actual is not None and actual.realized_pnl == proof_a.pnl
            assert actual.risk_context["fixture_metadata"] == {"preserved": True}
            if first_commits:
                assert actual.realized_pnl_synced_at == first_time
                assert actual.risk_context["code_pnl_evidence"]["raw_hash"] == proof_a.raw_hash
                assert set(actual.risk_context["pnl_evidence_conflict"]["raw_hashes"]) == {
                    proof_a.raw_hash,
                    proof_b.raw_hash,
                }
            else:
                assert actual.realized_pnl_synced_at == second_time
                assert actual.risk_context["code_pnl_evidence"]["raw_hash"] == proof_b.raw_hash
                assert actual.risk_context["code_pnl_observed_hashes"] == [proof_b.raw_hash]
                assert "pnl_evidence_conflict" not in actual.risk_context
    finally:
        if waiter is not None and not waiter.done():
            waiter.cancel()
            await asyncio.wait_for(asyncio.gather(waiter, return_exceptions=True), timeout=5)
        # 전용 seed의 UUID 네 개만 지운다. 공유 테스트 DB의 다른 행은 건드리지 않는다.
        async with maker() as cleanup:
            await cleanup.execute(delete(Order).where(Order.id == order_id))
            await cleanup.execute(delete(Strategy).where(Strategy.id == strategy_id))
            await cleanup.execute(delete(ExchangeAccount).where(ExchangeAccount.id == account_id))
            await cleanup.execute(delete(User).where(User.id == user_id))
            await cleanup.commit()
