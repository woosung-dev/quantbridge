"""라이브 청산 결과 parity 조회를 조합한다."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from src.backtest.engine.types import BacktestConfig
from src.trading.models import ExchangeName
from src.trading.outcome_parity import ParitySummary, summarize_parity
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository
from src.trading.repositories.live_signal_session_repository import (
    LiveSignalSessionRepository,
)
from src.trading.repositories.order_repository import SessionScope
from src.trading.repositories.parity_repository import (
    LedgerOnlyDiagnostics,
    ParityRepository,
)
from src.trading.schemas import (
    OutcomeParityAssumption,
    OutcomeParityResponse,
    OutcomeParityScope,
)


class OutcomeParitySessionNotFound(Exception):
    """요청 사용자가 읽을 수 없는 라이브 세션이다."""


class OutcomeParityService:
    """세션과 전략 누적 parity 요약을 읽기 전용으로 제공한다."""

    def __init__(
        self,
        session_repo: LiveSignalSessionRepository,
        parity_repo: ParityRepository,
        exchange_account_repo: ExchangeAccountRepository,
    ) -> None:
        self._session_repo = session_repo
        self._parity_repo = parity_repo
        self._exchange_account_repo = exchange_account_repo

    async def get_parity(self, user_id: UUID, session_id: UUID) -> OutcomeParityResponse:
        """요청 세션과 동일 전략 축의 누적 parity를 함께 반환한다."""
        session = await self._session_repo.get_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise OutcomeParitySessionNotFound

        account = await self._exchange_account_repo.get_by_id(session.exchange_account_id)
        ledger_supported = account is not None and account.exchange == ExchangeName.bybit

        strategy_sessions = await self._session_repo.list_by_strategy_account_symbol(
            user_id=user_id,
            strategy_id=session.strategy_id,
            exchange_account_id=session.exchange_account_id,
            symbol=session.symbol,
        )

        session_scopes = [SessionScope.from_live_session(session)]
        strategy_scopes = [
            SessionScope.from_live_session(strategy_session)
            for strategy_session in strategy_sessions
        ]
        account_diagnostics = await self._parity_repo.load_account_ledger_diagnostics(
            session_scopes
        )
        session_ledger_diagnostics = await self._parity_repo.load_scoped_ledger_only_diagnostics(
            session_scopes
        )
        strategy_ledger_diagnostics = await self._parity_repo.load_scoped_ledger_only_diagnostics(
            strategy_scopes
        )
        session_summary = await self._load_summary(
            [session.id], session_scopes, session_ledger_diagnostics
        )
        strategy_summary = await self._load_summary(
            [strategy_session.id for strategy_session in strategy_sessions],
            strategy_scopes,
            strategy_ledger_diagnostics,
        )

        return OutcomeParityResponse(
            session_id=session.id,
            session=_to_scope(session_summary),
            strategy=_to_scope(strategy_summary),
            unattributed_count=account_diagnostics.unattributed_count,
            ledger_supported=ledger_supported,
            strategy_session_count=len(strategy_sessions),
            assumption=_house_default_assumption(),
        )

    async def _load_summary(
        self,
        session_ids: list[UUID],
        scopes: list[SessionScope],
        ledger_diagnostics: LedgerOnlyDiagnostics,
    ) -> ParitySummary:
        observations, buckets = await self._parity_repo.load_parity_inputs(
            session_ids=session_ids,
            scopes=scopes,
        )
        return summarize_parity(
            observations,
            replace(
                buckets,
                ledger_only_count=ledger_diagnostics.ledger_only_count,
                ledger_only_net=ledger_diagnostics.ledger_only_net,
            ),
        )


def _to_scope(summary: ParitySummary) -> OutcomeParityScope:
    """도메인 요약을 HTTP 응답 스키마에 평탄화한다."""
    return OutcomeParityScope(
        matched_count=summary.matched_count,
        expected_gross=summary.expected_gross,
        actual_net=summary.actual_net,
        decomposable_count=summary.decomposable_count,
        decomposable_expected_gross=summary.decomposable_expected_gross,
        execution_gap=summary.execution_gap,
        cost=summary.cost,
        decomposable_actual_net=summary.decomposable_actual_net,
        actual_gross=summary.actual_gross,
        round_trip_notional=summary.round_trip_notional,
        effective_cost_pct_per_leg=summary.effective_cost_pct_per_leg,
        effective_cost_pct_round_trip=summary.effective_cost_pct_round_trip,
        edge_pct_round_trip=summary.edge_pct_round_trip,
        cost_to_edge_ratio=summary.cost_to_edge_ratio,
        undecomposed_count=summary.undecomposed_count,
        undecomposed_net=summary.undecomposed_net,
        expected_only_count=summary.buckets.expected_only_count,
        expected_only_gross=summary.buckets.expected_only_gross,
        expected_only_pending_count=summary.buckets.expected_only_pending_count,
        expected_only_failed_count=summary.buckets.expected_only_failed_count,
        expected_only_dispatched_count=summary.buckets.expected_only_dispatched_count,
        actual_only_count=summary.buckets.actual_only_count,
        actual_only_net=summary.buckets.actual_only_net,
        ledger_only_count=summary.buckets.ledger_only_count,
        ledger_only_net=summary.buckets.ledger_only_net,
        match_coverage_pct=summary.match_coverage_pct,
        decomposition_coverage_pct=summary.decomposition_coverage_pct,
        sample_n=summary.sample.n,
        sample_mean_net=summary.sample.mean_net,
        sample_sd_net=summary.sample.sd_net,
        sample_required_n=summary.sample.required_n,
        sample_sufficient=summary.sample.sufficient,
    )


def _house_default_assumption() -> OutcomeParityAssumption:
    """BacktestConfig 기본 비용 가정을 응답 단위인 백분율로 변환한다."""
    config = BacktestConfig()
    taker_fee_pct = Decimal(str(config.fees)) * Decimal("100")
    slippage_pct = Decimal(str(config.slippage)) * Decimal("100")
    maker_fee_pct = Decimal(str(config.maker_fee)) * Decimal("100")
    return OutcomeParityAssumption(
        source="house_default",
        taker_fee_pct=taker_fee_pct,
        slippage_pct=slippage_pct,
        maker_fee_pct=maker_fee_pct,
        implied_round_trip_pct=(taker_fee_pct + slippage_pct) * Decimal("2"),
    )
