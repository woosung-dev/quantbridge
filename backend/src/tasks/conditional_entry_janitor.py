# 오래된 조건부 진입의 거래소 상태를 확인해 안전하게 수리하거나 종결하는 Celery 정리 작업.

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime, timedelta

from celery import shared_task

from src.common.metrics import qb_active_orders
from src.core.config import settings
from src.tasks._worker_engine import create_worker_engine_and_sm
from src.tasks.orphan_scanner import _SCAN_STUCK_THRESHOLD_MINUTES

logger = logging.getLogger(__name__)


@shared_task(name="live_signal.janitor_conditional_entries", max_retries=0)  # type: ignore[untyped-decorator]
def conditional_entry_janitor_task() -> dict[str, int]:
    """오래된 submitted 조건부 진입을 거래소 확인 뒤에만 정리한다."""
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_conditional_entry_janitor())


async def _async_conditional_entry_janitor() -> dict[str, int]:
    """거래소 부재는 CAS reject, 발견된 주문은 수리 또는 terminal 전이한다."""
    from src.trading.encryption import EncryptionService
    from src.trading.providers import BybitFuturesProvider
    from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
    from src.trading.repositories.order_repository import OrderRepository
    from src.trading.services.account_service import ExchangeAccountService

    cutoff = datetime.now(UTC) - timedelta(minutes=_SCAN_STUCK_THRESHOLD_MINUTES)
    engine, sm = create_worker_engine_and_sm()
    repaired = 0
    rejected = 0
    terminal = 0
    try:
        async with sm() as session:
            order_repo = OrderRepository(session)
            account_repo = ExchangeAccountRepository(session)
            provider = BybitFuturesProvider()
            exchange_service = ExchangeAccountService(
                repo=account_repo,
                crypto=EncryptionService(settings.trading_encryption_keys),
                bybit_futures_provider=provider,
            )
            for order in await order_repo.list_stale_conditional_entries(cutoff):
                # rollback 뒤 ORM 객체의 lazy refresh가 MissingGreenlet을 내지 않게 미리 보관한다.
                order_id = order.id
                account_id = order.exchange_account_id
                symbol = order.symbol
                exchange_order_id = order.exchange_order_id
                try:
                    creds = await exchange_service.get_credentials_for_order(account_id)
                    if exchange_order_id is None:
                        probe = await provider.fetch_order_by_client_id(
                            creds, str(order_id), symbol, trigger=True
                        )
                        if probe is None:
                            rows = await order_repo.transition_submitted_without_exchange_id_to_rejected(
                                order_id,
                                error_message="Conditional entry was not found on exchange",
                                failed_at=datetime.now(UTC),
                            )
                            if rows == 1:
                                await order_repo.commit()
                                rejected += 1
                                qb_active_orders.dec()
                            continue
                        exchange_order_id = probe.exchange_order_id
                        if probe.status == "submitted":
                            if (
                                await order_repo.attach_exchange_order_id(
                                    order_id, exchange_order_id
                                )
                                == 1
                            ):
                                await order_repo.commit()
                                repaired += 1
                            continue
                        if (
                            await order_repo.attach_exchange_order_id(order_id, exchange_order_id)
                            != 1
                        ):
                            continue
                        await order_repo.commit()
                    else:
                        probe = await provider.fetch_order(
                            creds, exchange_order_id, symbol, trigger=True
                        )
                        if probe.status == "submitted":
                            continue

                    now = datetime.now(UTC)
                    if probe.status == "filled":
                        rows = await order_repo.transition_to_filled(
                            order_id,
                            exchange_order_id=probe.exchange_order_id,
                            filled_price=probe.filled_price,
                            filled_quantity=probe.filled_quantity,
                            filled_at=now,
                        )
                    elif probe.status == "cancelled":
                        rows = await order_repo.transition_to_cancelled(order_id, cancelled_at=now)
                    elif probe.status == "rejected":
                        rows = await order_repo.transition_to_rejected(
                            order_id,
                            error_message="Conditional entry rejected on exchange",
                            failed_at=now,
                        )
                    else:
                        continue
                    if rows == 1:
                        await order_repo.commit()
                        terminal += 1
                        qb_active_orders.dec()
                except Exception:
                    with contextlib.suppress(Exception):
                        await session.rollback()
                    logger.exception(
                        "conditional_entry_janitor_probe_failed",
                        extra={"order_id": str(order_id)},
                    )
        return {"repaired": repaired, "rejected": rejected, "terminal": terminal}
    finally:
        await engine.dispose()
