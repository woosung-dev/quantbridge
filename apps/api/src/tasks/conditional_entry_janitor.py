# 오래된 조건부 진입의 거래소 상태를 확인해 안전하게 수리하거나 종결하는 Celery 정리 작업.

from __future__ import annotations

import contextlib
import logging
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from celery import shared_task

from src.common.metrics import qb_active_orders, qb_live_conditional_reconcile_errors_total
from src.common.metrics_multiproc import record_metric_safely
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
    from src.tasks.trading import (
        _enqueue_closed_pnl_refresh,
        _enqueue_conditional_reversal_measure,
        _enqueue_trailing_if_intended,
        _has_leverage,
    )
    from src.trading.encryption import EncryptionService
    from src.trading.registry import dispatch
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
            exchange_service = ExchangeAccountService(
                repo=account_repo,
                crypto=EncryptionService(settings.trading_encryption_keys),
            )
            orders = [
                (
                    order.id,
                    order.exchange_account_id,
                    order.symbol,
                    order.exchange_order_id,
                    _has_leverage(order),
                    SimpleNamespace(
                        id=order.id,
                        trailing_stop=order.trailing_stop,
                        reduce_only=order.reduce_only,
                        # BL-562 — 반전 계측 hook 이 조건부 진입 판별에 쓴다. 빠지면
                        # 이 경로의 체결이 **조용히 미계측**으로 남는다(예약 자체가 안 된다).
                        idempotency_key=order.idempotency_key,
                    ),
                )
                for order in await order_repo.list_stale_conditional_entries(cutoff)
            ]
            for order_id, account_id, symbol, exchange_order_id, has_leverage, hook_order in orders:
                try:
                    account = await account_repo.get_by_id(account_id)
                    if account is None:
                        raise RuntimeError("conditional entry account missing")
                    provider = dispatch(account.exchange, account.mode, has_leverage)
                    creds = await exchange_service.get_credentials_for_order(account_id)
                    probe = await provider.fetch_order_by_client_id(
                        creds, str(order_id), symbol, trigger=True
                    )
                    if probe is None:
                        if exchange_order_id is None:
                            rows = await order_repo.transition_submitted_without_exchange_id_to_rejected(
                                order_id,
                                error_message="Conditional entry was not found on exchange",
                                failed_at=datetime.now(UTC),
                            )
                            if rows == 1:
                                await order_repo.commit()
                                rejected += 1
                                record_metric_safely(qb_active_orders.dec)
                            else:
                                qb_live_conditional_reconcile_errors_total.labels(
                                    stage="janitor_race"
                                ).inc()
                            continue
                        rows = await order_repo.transition_to_rejected(
                            order_id,
                            error_message="Conditional entry was not found on exchange",
                            failed_at=datetime.now(UTC),
                        )
                        if rows == 1:
                            await order_repo.commit()
                            rejected += 1
                            record_metric_safely(qb_active_orders.dec)
                        else:
                            qb_live_conditional_reconcile_errors_total.labels(
                                stage="janitor_race"
                            ).inc()
                        continue
                    if probe.status == "submitted":
                        if exchange_order_id != probe.exchange_order_id:
                            rows = await order_repo.attach_exchange_order_id(
                                order_id, probe.exchange_order_id
                            )
                            if rows == 1:
                                await order_repo.commit()
                                repaired += 1
                            else:
                                qb_live_conditional_reconcile_errors_total.labels(
                                    stage="janitor_race"
                                ).inc()
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
                        rows = await order_repo.transition_to_cancelled(
                            order_id,
                            cancelled_at=now,
                            filled_price=probe.filled_price,
                            filled_quantity=probe.filled_quantity,
                        )
                    elif probe.status == "rejected":
                        rows = await order_repo.transition_to_rejected(
                            order_id,
                            error_message="Conditional entry rejected on exchange",
                            failed_at=now,
                            filled_price=probe.filled_price,
                            filled_quantity=probe.filled_quantity,
                        )
                    else:
                        continue
                    if rows == 1:
                        await order_repo.commit()
                        terminal += 1
                        record_metric_safely(qb_active_orders.dec)
                        if probe.status == "filled":
                            _enqueue_trailing_if_intended(hook_order)
                            _enqueue_closed_pnl_refresh(hook_order)
                            _enqueue_conditional_reversal_measure(hook_order)
                    else:
                        qb_live_conditional_reconcile_errors_total.labels(
                            stage="janitor_race"
                        ).inc()
                except Exception:
                    with contextlib.suppress(Exception):
                        await session.rollback()
                    qb_live_conditional_reconcile_errors_total.labels(stage="janitor_probe").inc()
                    logger.exception(
                        "conditional_entry_janitor_probe_failed",
                        extra={"order_id": str(order_id)},
                    )
        return {"repaired": repaired, "rejected": rejected, "terminal": terminal}
    finally:
        await engine.dispose()
