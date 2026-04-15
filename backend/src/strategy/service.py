"""strategy Service. Pine 파싱 + CRUD 조율."""
from __future__ import annotations

from uuid import UUID

import pandas as pd

from src.strategy.exceptions import StrategyNotFoundError
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


def _empty_ohlcv() -> pd.DataFrame:
    """파싱만 수행하기 위한 최소 OHLCV (길이 1)."""
    idx = pd.date_range("2026-01-01", periods=1, freq="h")
    return pd.DataFrame(
        {"open": [0.0], "high": [0.0], "low": [0.0], "close": [0.0], "volume": [0.0]},
        index=idx,
    )


def _parse(
    source: str,
) -> tuple[ParseStatus, PineVersion, list[str], list[ParseError], int, int]:
    """parse_and_run → (status, version, warnings, errors, entry_count, exit_count).

    ParseOutcome 실제 속성:
      - source_version: Literal["v4", "v5"]
      - error: PineError | None  (단수 — 복수 아님)
      - result: SignalResult | None  (signals property alias)
      - warnings: list[str]
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

    return status, version, warnings, errors, entry_count, exit_count


class StrategyService:
    def __init__(self, repo: StrategyRepository) -> None:
        self.repo = repo

    async def parse_preview(self, pine_source: str) -> ParsePreviewResponse:
        status, version, warnings, errors, entry_count, exit_count = _parse(pine_source)
        return ParsePreviewResponse(
            status=status,
            pine_version=version,
            warnings=warnings,
            errors=errors,
            entry_count=entry_count,
            exit_count=exit_count,
        )

    async def create(
        self, data: CreateStrategyRequest, *, owner_id: UUID
    ) -> StrategyResponse:
        status, version, _warnings, errors, _e, _x = _parse(data.pine_source)
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
        page: int,
        limit: int,
        parse_status: ParseStatus | None,
        is_archived: bool,
    ) -> StrategyListResponse:
        items, total = await self.repo.list_by_owner(
            owner_id,
            page=page,
            limit=limit,
            parse_status=parse_status,
            is_archived=is_archived,
        )

        total_pages = (total + limit - 1) // limit if total > 0 else 0
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
            status, version, _w, errors, _e, _x = _parse(data.pine_source)
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
        await self.repo.delete(strategy.id)
        await self.repo.commit()
