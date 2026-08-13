# 세션 소유권을 확인하고 알림 규칙 생명주기를 처리하는 서비스

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from src.strategy.exceptions import StrategyNotFoundError
from src.trading.exceptions import AlertRuleAlreadyActive
from src.trading.models import AlertRule, AlertRuleType
from src.trading.repositories.alert_rule_repository import AlertRuleRepository
from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
from src.trading.schemas import AlertRuleCreateRequest


class AlertRuleService:
    def __init__(
        self,
        repo: AlertRuleRepository,
        session_repo: LiveSignalSessionRepository,
    ) -> None:
        self._repo = repo
        self._session_repo = session_repo

    async def list_active(self, user_id: UUID, session_id: UUID) -> list[AlertRule]:
        await self._require_owned_session(user_id, session_id)
        return list(await self._repo.list_by_session(session_id))

    async def create(
        self, user_id: UUID, session_id: UUID, request: AlertRuleCreateRequest
    ) -> AlertRule:
        await self._require_owned_session(user_id, session_id)
        rule = AlertRule(
            session_id=session_id,
            rule_type=AlertRuleType(request.rule_type),
            threshold_percent=request.threshold_percent,
            channel=request.channel,
        )
        try:
            saved = await self._repo.create(rule)
        except IntegrityError as exc:
            await self._repo.rollback()
            raise AlertRuleAlreadyActive(
                "Active alert rule type already exists for this session"
            ) from exc
        await self._repo.commit()
        return saved

    async def deactivate(self, user_id: UUID, session_id: UUID, rule_id: UUID) -> None:
        await self._require_owned_session(user_id, session_id)
        rule = await self._repo.get_active_by_id(rule_id)
        if rule is None or rule.session_id != session_id:
            raise StrategyNotFoundError()
        if await self._repo.deactivate(rule_id):
            await self._repo.commit()

    async def _require_owned_session(self, user_id: UUID, session_id: UUID) -> None:
        session = await self._session_repo.get_by_id(session_id)
        if session is None or session.user_id != user_id:
            raise StrategyNotFoundError()
