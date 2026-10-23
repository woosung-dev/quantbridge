"""code_v1 전용 봉 평가 조립. 기존 Pine replay와 주문 outbox를 섞지 않는다."""

from datetime import UTC, datetime, timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Any

from ccxt import TICK_SIZE

from src.core.config import settings
from src.market_data.constants import TIMEFRAME_SECONDS, to_ccxt_perpetual_symbol
from src.strategy.code_contract import read_code_version
from src.strategy.code_runtime.models import CodeRuntimeError
from src.strategy.schemas import StrategySettings
from src.trading.code_execution_snapshot import validate_code_snapshot
from src.trading.code_risk_composition import build_code_risk_executor
from src.trading.dependencies import get_kill_switch_service
from src.trading.encryption import EncryptionService
from src.trading.models import LiveSignalSession
from src.trading.providers import BybitFuturesProvider
from src.trading.repositories.code_checkpoint_repository import CodeCheckpointRepository
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.account_service import ExchangeAccountService
from src.trading.services.code_evaluation_service import FLAT, CodeEvaluationService
from src.trading.services.code_live_execution_service import CodeLiveExecutionService
from src.trading.services.code_risk_service import CodeRiskReconciliationPending


def code_quantity(
    *, capital: Decimal, percent: Decimal, price: Decimal, step: Decimal, minimum: Decimal
) -> Decimal:
    """compute_qty percent_of_equity와 같은 식을 Decimal로 계산하고 거래소 step에 내린다."""
    if (
        any(
            not number.is_finite() or number <= 0
            for number in (capital, percent, price, step, minimum)
        )
        or percent > 100
    ):
        raise CodeRuntimeError("고정 기준선·비율·가격·수량 규칙이 유효하지 않습니다")
    split_step = 2 * step
    quantity = (capital * percent / 100 / price / split_step).to_integral_value(
        rounding=ROUND_DOWN
    ) * split_step
    if quantity / 2 < minimum:
        raise CodeRuntimeError("50% 익절과 잔여 수량이 모두 거래소 최소 수량 이상이어야 합니다")
    return quantity


def completed_code_bars(
    raw: list[list[Any]], *, now: datetime, interval_seconds: int
) -> list[dict[str, Any]]:
    """포지션 평가·수량 추정·손절 기준은 같은 완료 봉만 사용한다."""
    return [
        {
            "timestamp": datetime.fromtimestamp(int(row[0]) / 1000, tz=UTC).isoformat(),
            **{
                key: str(value)
                for key, value in zip(
                    ("open", "high", "low", "close", "volume"), row[1:6], strict=True
                )
            },
        }
        for row in raw
        if datetime.fromtimestamp(int(row[0]) / 1000, tz=UTC) + timedelta(seconds=interval_seconds)
        <= now
    ]


async def evaluate_code_session(
    session: Any, live: LiveSignalSession, *, now: datetime | None = None
) -> dict[str, Any]:
    """현재 실제 포지션 확인 후 완료 봉만 평가한다. 네트워크 호출은 이 제품 경계에서만 한다."""
    from src.tasks.celery_app import get_ccxt_provider_for_worker

    at = now or datetime.now(UTC)
    repo = CodeRiskRepository(session)
    account = await repo.get_account(live.exchange_account_id)
    version = await repo.get_version(live.strategy_version_id) if live.strategy_version_id else None
    if account is None or account.user_id != live.user_id:
        raise CodeRuntimeError("코드 실행 소유자·계정·버전이 일치하지 않습니다")
    provider = BybitFuturesProvider()
    accounts = ExchangeAccountService(
        ExchangeAccountRepository(session),
        EncryptionService(settings.trading_encryption_keys),
        provider,
    )
    risk, executor = build_code_risk_executor(session, accounts, provider)
    # 소스·설정 오류도 이미 열린 포지션의 보호·취소 복구를 막지 않는다.
    try:
        await executor.drain(live.id)
    except CodeRiskReconciliationPending:
        return {"code_action": "awaiting_fill_reconciliation", "session_id": str(live.id)}
    if version is None or version.strategy_id != live.strategy_id:
        raise CodeRuntimeError("코드 실행 버전이 없습니다")
    snapshot = validate_code_snapshot(
        live.execution_snapshot,
        version=version,
        version_id=live.strategy_version_id,
        account=account,
    )
    code = read_code_version(version, strategy_id=live.strategy_id)
    frozen = StrategySettings.model_validate(snapshot.get("execution_settings"))
    if frozen.fill_timing != "next_bar_open" or frozen.leverage != 1 or str(live.interval) != "1h":
        raise CodeRuntimeError("현재 code_v1 demo는 1h·next_bar_open·1X 실행 설정이 필요합니다")
    state = await repo.get(live.id)
    credentials = await accounts.get_credentials_for_order(live.exchange_account_id)
    actual = await provider.fetch_position(credentials, live.symbol)
    quantity = state.position_quantity if state is not None else Decimal(0)
    if quantity == 0:
        if actual is not None and actual.size > 0:
            raise CodeRuntimeError("flat 원장과 거래소 포지션이 일치하지 않습니다")
        position = dict(FLAT)
    else:
        if (
            state is None
            or actual is None
            or actual.side != state.direction
            or actual.size != quantity
        ):
            raise CodeRuntimeError("관찰 포지션과 확정 체결 원장이 일치하지 않습니다")
        if state.cumulative_quantity <= 0:
            raise CodeRuntimeError("확정 체결 평균가가 없습니다")
        average = state.entry_vwap or state.cumulative_value / state.cumulative_quantity
        position = {
            "direction": state.direction,
            "size": str(quantity),
            "average_price": str(average),
        }
    market_provider = get_ccxt_provider_for_worker()
    symbol = to_ccxt_perpetual_symbol(live.symbol)
    raw = await market_provider.fetch_ohlcv(
        symbol, str(live.interval), limit_bars=code.warmup_bars + 2
    )
    bars = completed_code_bars(raw, now=at, interval_seconds=TIMEFRAME_SECONDS[str(live.interval)])
    if len(bars) < 2:
        raise CodeRuntimeError("완료 봉과 손절 기준 2봉이 필요합니다")
    await market_provider.exchange.load_markets()
    market = market_provider.exchange.market(symbol)
    if market_provider.exchange.precisionMode != TICK_SIZE:
        raise CodeRuntimeError("수량 precision이 tick size가 아닙니다")
    step = Decimal(str(market["precision"]["amount"]))
    minimum = Decimal(str(market["limits"]["amount"]["min"]))
    price = Decimal(bars[-1]["close"])
    capital = live.equity_baseline_usdt
    if capital is None:
        raise CodeRuntimeError("세션 자본 기준선이 없습니다")
    try:
        qty: Decimal | None = code_quantity(
            capital=capital,
            percent=Decimal(str(frozen.position_size_pct)),
            price=price,
            step=step,
            minimum=minimum,
        )
    except CodeRuntimeError:
        # 새 진입은 coordinator가 거부하되 hold/무효화 close는 최소 수량 오류에 막지 않는다.
        qty = None
    kill_switch = await get_kill_switch_service(session, accounts)
    coordinator = CodeLiveExecutionService(
        repo, OrderRepository(session), risk, executor, entry_gate=kill_switch.ensure_not_gated
    )
    evaluator = CodeEvaluationService(CodeCheckpointRepository(session), coordinator)
    try:
        action = await evaluator.evaluate(
            session_id=live.id,
            code=code,
            bars=bars,
            position=position,
            activated_at=live.created_at,
            now=at,
            interval_seconds=TIMEFRAME_SECONDS[str(live.interval)],
            execution_args={
                "estimated_entry": price,
                "quantity": qty,
                "qty_step": step,
                "min_qty": minimum,
                "previous_bars": [
                    {key: Decimal(str(bar[key])) for key in ("open", "high", "low", "close")}
                    for bar in bars[-2:]
                ],
            },
        )
    except CodeRiskReconciliationPending:
        return {"code_action": "awaiting_fill_reconciliation", "session_id": str(live.id)}
    return {"code_action": action, "session_id": str(live.id)}
