"""세션별 lease outbox를 전달한다. 거래소 중복 요청은 UUID 조회로 수렴한다."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Protocol
from uuid import UUID, uuid4

from src.trading.code_execution_snapshot import validate_code_snapshot
from src.trading.models import CodeRiskCommand, LiveRiskState, LiveSignalSession
from src.trading.product_policy import require_bybit_demo_account
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.services.code_risk_service import (
    CodeRiskError,
    CodeRiskReconciliationPending,
    CodeRiskService,
    RiskCommand,
)


class CodeRiskVenue(Protocol):
    async def execute(
        self, command: CodeRiskCommand, session: LiveSignalSession, state: LiveRiskState
    ) -> dict[str, Any]: ...
    async def reconcile(self, session: LiveSignalSession, state: LiveRiskState) -> bool: ...


class CodeRiskExecutor:
    def __init__(
        self, repo: CodeRiskRepository, risk: CodeRiskService, venue: CodeRiskVenue
    ) -> None:
        self._repo, self._risk, self._venue = repo, risk, venue

    async def drain(self, session_id: UUID, *, limit: int = 20) -> list[RiskCommand]:
        """claim은 IO 전에 commit한다. 응답 유실시 같은 멱등키로 조회 후 재전달한다."""
        session = await self._repo.get_session(session_id)
        state = await self._repo.get(session_id)
        if session is None or state is None:
            return []
        session = LiveSignalSession(**session.model_dump())
        state = LiveRiskState(**state.model_dump())
        loaded_account = await self._repo.get_account(session.exchange_account_id)
        if loaded_account is None:
            raise CodeRiskError("리스크 계정이 없습니다")
        account = SimpleNamespace(
            exchange=loaded_account.exchange,
            mode=loaded_account.mode,
            read_only=loaded_account.read_only,
        )
        require_bybit_demo_account(account.exchange, account.mode)
        # 소스 변조·세션 종료도 기존 포지션 축소·취소를 막지 않는다.
        if await self._venue.reconcile(session, state) is False:
            raise CodeRiskReconciliationPending(
                "주문 체결과 거래소 포지션의 정합 확인을 기다립니다"
            )
        recovered = await self._risk.recover(session_id)
        await self._repo.enqueue_commands(
            [
                CodeRiskCommand(
                    key=c.key,
                    session_id=session_id,
                    generation=state.generation,
                    kind=c.kind,
                    payload=c.payload,
                )
                for c in recovered
            ]
        )
        await self._repo.commit()
        ready: list[RiskCommand] = []
        for _ in range(limit):
            lease = uuid4()
            command = await self._repo.claim_command(session_id, lease)
            await self._repo.commit()
            if command is None:
                break
            loaded = await self._repo.get(session_id)
            state = LiveRiskState(**loaded.model_dump()) if loaded is not None else None
            current = await self._risk.recover(session_id)
            if (
                state is None
                or command.generation != state.generation
                or command.key not in {c.key for c in current}
            ):
                await self._repo.finish_command(command.key, lease, status="superseded")
                await self._repo.commit()
                continue
            try:
                if command.kind in {"submit_entry", "ready_reversal"}:
                    version_id = session.strategy_version_id
                    version = await self._repo.get_version(version_id) if version_id else None
                    validate_code_snapshot(
                        session.execution_snapshot,
                        version=version,
                        version_id=version_id,
                        account=account,
                    )
                    if not session.is_active:
                        raise CodeRiskError("종료된 세션은 새 진입을 할 수 없습니다")
                if command.kind == "halt_new_entries":
                    result: dict[str, Any] = {"halted": True}
                elif command.kind == "ready_reversal":
                    # 새 진입 수량·최근 2봉은 다음 평가에서 다시 산출한다.
                    ready.append(RiskCommand(command.kind, command.key, command.payload))
                    result = {"ready": True}
                else:
                    async with asyncio.timeout(45):
                        result = await self._venue.execute(command, session, state)
                    if command.kind == "apply_protection":
                        await self._risk.acknowledge_protection(
                            session_id,
                            state.generation,
                            token=str(command.payload["token"]),
                            success=True,
                            applied=result.get("protection")
                            if isinstance(result.get("protection"), dict)
                            else None,
                        )
                await self._repo.finish_command(command.key, lease, status="applied", result=result)
                await self._repo.commit()
            except CodeRiskReconciliationPending:
                await self._repo.rollback()
                await self._repo.finish_command(
                    command.key, lease, status="pending", error="CodeRiskReconciliationPending"
                )
                await self._repo.commit()
                raise
            except Exception as exc:
                # 외부 라이브러리 메시지에는 자격증명이 있을 수 있어 타입만 저장한다.
                await self._repo.rollback()
                reason = type(exc).__name__
                if command.kind == "apply_protection":
                    await self._risk.acknowledge_protection(
                        session_id,
                        state.generation,
                        token=str(command.payload["token"]),
                        success=False,
                    )
                elif command.kind in {"submit_entry", "ready_reversal"}:
                    await self._risk.halt(session_id, state.generation, "command_failed:" + reason)
                await self._repo.finish_command(
                    command.key,
                    lease,
                    status="failed"
                    if command.kind in {"apply_protection", "submit_entry", "ready_reversal"}
                    else "pending",
                    error=reason,
                )
                await self._repo.commit()
                # 다음 호출에서 재조회한다. 보호 실패의 축소 명령만 즉시 계속 전달한다.
                if command.kind != "apply_protection":
                    break
        return ready
