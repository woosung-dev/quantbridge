"""언어 중립 코드의 소유권·불변 버전·트랜잭션을 조율한다. 코드를 실행하지 않는다."""

from __future__ import annotations

from uuid import UUID

from src.strategy.code_contract import CODE_EXECUTION_POLICIES, read_code_version
from src.strategy.code_schemas import (
    CodeStrategyListResponse,
    CodeStrategyResponse,
    CodeVersionResponse,
    SaveCodeStrategyRequest,
)
from src.strategy.exceptions import CodeStrategyPolicyError, StrategyNotFoundError
from src.strategy.models import ParseStatus, Strategy, StrategyVersion
from src.strategy.repository import StrategyRepository
from src.strategy.schemas import StrategySettings


class CodeStrategyService:
    def __init__(self, repo: StrategyRepository) -> None:
        self.repo = repo

    @staticmethod
    def _response(strategy: Strategy, version: StrategyVersion) -> CodeStrategyResponse:
        code = read_code_version(version, strategy_id=strategy.id)
        return CodeStrategyResponse(
            id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            symbol=strategy.symbol,
            timeframe=strategy.timeframe,
            is_archived=strategy.is_archived,
            settings=StrategySettings.model_validate(strategy.settings)
            if strategy.settings is not None
            else None,
            version=CodeVersionResponse(
                **code.model_dump(),
                id=version.id,
                source_hash=version.source_hash,
                execution_hash=version.execution_hash or "",
                created_at=version.created_at,
            ),
        )

    async def _owned(self, strategy_id: UUID, owner_id: UUID) -> tuple[Strategy, StrategyVersion]:
        strategy = await self.repo.find_by_id_and_owner(strategy_id, owner_id)
        if strategy is None:
            raise StrategyNotFoundError()
        if strategy.execution_policy not in CODE_EXECUTION_POLICIES:
            raise CodeStrategyPolicyError()
        version = await self.repo.get_version_by_id(
            strategy.strategy_version_id, strategy_id=strategy.id
        )
        if version is None:
            raise CodeStrategyPolicyError()
        read_code_version(version, strategy_id=strategy.id)
        return strategy, version

    async def create(
        self, data: SaveCodeStrategyRequest, *, owner_id: UUID
    ) -> CodeStrategyResponse:
        strategy = Strategy(
            user_id=owner_id,
            name=data.name,
            description=data.description,
            symbol=data.symbol,
            timeframe=data.timeframe,
            pine_source=None,
            pine_version=None,
            source_language=data.code.language.value,
            execution_policy=data.code.execution_policy,
            parse_status=ParseStatus.unsupported,
            settings=data.settings.model_dump(mode="json") if data.settings is not None else None,
        )
        strategy = await self.repo.create(strategy)
        version = await self.repo.create_code_version(strategy_id=strategy.id, code=data.code)
        await self.repo.set_current_version(strategy.id, version.id)
        await self.repo.commit()
        return self._response(strategy, version)

    async def update(
        self, strategy_id: UUID, data: SaveCodeStrategyRequest, *, owner_id: UUID
    ) -> CodeStrategyResponse:
        strategy, _ = await self._owned(strategy_id, owner_id)
        strategy.name, strategy.description = data.name, data.description
        strategy.symbol, strategy.timeframe = data.symbol, data.timeframe
        strategy.source_language = data.code.language.value
        strategy.execution_policy = data.code.execution_policy
        if "settings" in data.model_fields_set:
            strategy.settings = (
                data.settings.model_dump(mode="json") if data.settings is not None else None
            )
        version = await self.repo.create_code_version(strategy_id=strategy.id, code=data.code)
        await self.repo.set_current_version(strategy.id, version.id)
        await self.repo.update(strategy)
        await self.repo.commit()
        return self._response(strategy, version)

    async def get(self, strategy_id: UUID, *, owner_id: UUID) -> CodeStrategyResponse:
        strategy, version = await self._owned(strategy_id, owner_id)
        return self._response(strategy, version)

    async def list(self, *, owner_id: UUID, limit: int, offset: int) -> CodeStrategyListResponse:
        rows, total = await self.repo.list_code_by_owner(owner_id, limit=limit, offset=offset)
        return CodeStrategyListResponse(items=[self._response(s, v) for s, v in rows], total=total)
