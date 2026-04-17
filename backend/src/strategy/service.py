"""strategy Service. Pine 파싱 + CRUD 조율."""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

# asyncpg FK violation 타입 — 드라이버 부재 시 None으로 fallback (단위 테스트 호환)
try:
    from asyncpg.exceptions import ForeignKeyViolationError as _AsyncpgFKViolation
except ImportError:
    _AsyncpgFKViolation = None

import pandas as pd
from sqlalchemy.exc import IntegrityError

from src.strategy.exceptions import StrategyHasBacktests, StrategyNotFoundError
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.pine import parse_and_run
from src.strategy.repository import StrategyRepository
from src.strategy.schemas import (
    CreateStrategyRequest,
    ParseError,
    ParsePreviewResponse,
    StrategyListItem,
    StrategyListResponse,
    StrategyResponse,
    UpdateStrategyRequest,
)

if TYPE_CHECKING:
    from src.backtest.repository import BacktestRepository


def _empty_ohlcv() -> pd.DataFrame:
    """파싱만 수행하기 위한 최소 OHLCV (길이 1)."""
    idx = pd.date_range("2026-01-01", periods=1, freq="h")
    return pd.DataFrame(
        {"open": [0.0], "high": [0.0], "low": [0.0], "close": [0.0], "volume": [0.0]},
        index=idx,
    )


def _parse(
    source: str,
) -> tuple[
    ParseStatus,
    PineVersion,
    list[str],
    list[ParseError],
    int,
    int,
    list[str],
]:
    """parse_and_run → (status, version, warnings, errors, entry_count, exit_count, functions_used).

    ParseOutcome 실제 속성:
      - source_version: Literal["v4", "v5"]
      - error: PineError | None  (단수 — 복수 아님)
      - result: SignalResult | None  (signals property alias)
      - warnings: list[str]
      - supported_feature_report: dict[str, list[str]]  ({"functions_used": sorted names})
    """
    try:
        outcome = parse_and_run(source, _empty_ohlcv())
    except Exception as exc:  # 파싱 중 모든 예외를 error로 변환
        return (
            ParseStatus.error,
            PineVersion.v5,
            [],
            [ParseError(code=type(exc).__name__, message=str(exc))],
            0,
            0,
            [],
        )

    # warnings: ParseOutcome 레벨 + SignalResult 레벨 병합
    warnings: list[str] = list(outcome.warnings)
    if outcome.signals is not None:
        warnings.extend(outcome.signals.warnings)

    # errors: ParseOutcome.error 는 단수 PineError | None
    errors: list[ParseError] = []
    if outcome.error is not None:
        e = outcome.error
        errors.append(
            ParseError(
                code=getattr(e, "category", type(e).__name__),
                message=str(e),
                line=getattr(e, "line", None),
            )
        )

    status = (
        ParseStatus(outcome.status)
        if outcome.status in {"ok", "unsupported", "error"}
        else ParseStatus.error
    )
    version = (
        PineVersion(outcome.source_version)
        if outcome.source_version in {"v4", "v5"}
        else PineVersion.v5
    )

    entry_count = int(outcome.signals.entries.sum()) if outcome.signals is not None else 0
    exit_count = int(outcome.signals.exits.sum()) if outcome.signals is not None else 0
    functions_used = list(outcome.supported_feature_report.get("functions_used", []))

    return status, version, warnings, errors, entry_count, exit_count, functions_used


class StrategyService:
    def __init__(
        self,
        repo: StrategyRepository,
        # backtest_repo: Sprint 3 호환을 위한 optional. 프로덕션 DI(get_strategy_service)는
        # 항상 주입; None은 unit test 또는 background CLI 경로에서만 허용.
        # None일 경우 backtest 선조회 스킵 — DB FK RESTRICT가 최종 안전망.
        backtest_repo: BacktestRepository | None = None,
    ) -> None:
        self.repo = repo
        self.backtest_repo = backtest_repo

    async def parse_preview(self, pine_source: str) -> ParsePreviewResponse:
        status, version, warnings, errors, entry_count, exit_count, functions_used = (
            _parse(pine_source)
        )
        return ParsePreviewResponse(
            status=status,
            pine_version=version,
            warnings=warnings,
            errors=errors,
            entry_count=entry_count,
            exit_count=exit_count,
            functions_used=functions_used,
        )

    async def create(
        self, data: CreateStrategyRequest, *, owner_id: UUID
    ) -> StrategyResponse:
        status, version, _warnings, errors, _e, _x, _fu = _parse(data.pine_source)
        parse_errors = [e.model_dump() for e in errors] if errors else None
        strategy = Strategy(
            user_id=owner_id,
            name=data.name,
            description=data.description,
            pine_source=data.pine_source,
            pine_version=version,
            parse_status=status,
            parse_errors=parse_errors,
            timeframe=data.timeframe,
            symbol=data.symbol,
            tags=list(data.tags),
        )
        saved = await self.repo.create(strategy)
        await self.repo.commit()
        return StrategyResponse.model_validate(saved)

    async def list(
        self,
        *,
        owner_id: UUID,
        limit: int,
        offset: int,
        parse_status: ParseStatus | None,
        is_archived: bool,
    ) -> StrategyListResponse:
        items, total = await self.repo.list_by_owner(
            owner_id,
            limit=limit,
            offset=offset,
            parse_status=parse_status,
            is_archived=is_archived,
        )

        # response 호환성: page/total_pages는 limit/offset에서 역산.
        total_pages = (total + limit - 1) // limit if total > 0 else 0
        page = (offset // limit) + 1 if limit > 0 else 1
        return StrategyListResponse(
            items=[StrategyListItem.model_validate(s) for s in items],
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )

    async def get(self, *, strategy_id: UUID, owner_id: UUID) -> StrategyResponse:
        strategy = await self.repo.find_by_id_and_owner(strategy_id, owner_id)
        if strategy is None:
            raise StrategyNotFoundError()
        return StrategyResponse.model_validate(strategy)

    async def update(
        self,
        *,
        strategy_id: UUID,
        owner_id: UUID,
        data: UpdateStrategyRequest,
    ) -> StrategyResponse:
        strategy = await self.repo.find_by_id_and_owner(strategy_id, owner_id)
        if strategy is None:
            raise StrategyNotFoundError()

        if data.name is not None:
            strategy.name = data.name
        if data.description is not None:
            strategy.description = data.description
        if data.timeframe is not None:
            strategy.timeframe = data.timeframe
        if data.symbol is not None:
            strategy.symbol = data.symbol
        if data.tags is not None:
            strategy.tags = list(data.tags)
        if data.is_archived is not None:
            strategy.is_archived = data.is_archived
        if data.pine_source is not None:
            status, version, _w, errors, _e, _x, _fu = _parse(data.pine_source)
            strategy.pine_source = data.pine_source
            strategy.pine_version = version
            strategy.parse_status = status
            strategy.parse_errors = [e.model_dump() for e in errors] if errors else None

        updated = await self.repo.update(strategy)
        await self.repo.commit()
        return StrategyResponse.model_validate(updated)

    async def delete(self, *, strategy_id: UUID, owner_id: UUID) -> None:
        strategy = await self.repo.find_by_id_and_owner(strategy_id, owner_id)
        if strategy is None:
            raise StrategyNotFoundError()

        # 선조회 — Sprint 4부터 backtest_repo 주입됨
        if self.backtest_repo is not None and await self.backtest_repo.exists_for_strategy(strategy_id):
            raise StrategyHasBacktests()

        # TOCTOU 방어: FK RESTRICT가 race loser를 DB 레벨에서 catch
        try:
            await self.repo.delete(strategy.id)
            await self.repo.commit()
        except IntegrityError as exc:
            # Note: rollback은 명시적 호출 (get_async_session의 catch-all과 redundant이지만
            # 의도 명확화 + 트랜잭션 lifecycle 책임 분명히).
            await self.repo.rollback()
            # asyncpg FK violation → StrategyHasBacktests 변환 (substring 매칭 대신 isinstance)
            # exc.orig: 직접 asyncpg FKViolationError (unit test mock) 또는
            #           SQLAlchemy asyncpg dialect DBAPI IntegrityError (실제 DB 경로).
            #           후자의 경우 __cause__가 asyncpg 원본 에러.
            _orig_cause = getattr(exc.orig, "__cause__", None)
            is_fk_violation = _AsyncpgFKViolation is not None and (
                isinstance(exc.orig, _AsyncpgFKViolation)
                or isinstance(_orig_cause, _AsyncpgFKViolation)
            )
            if is_fk_violation:
                raise StrategyHasBacktests() from exc
            raise
