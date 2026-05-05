"""strategy Service. Pine 파싱 + CRUD 조율."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING
from uuid import UUID

# asyncpg FK violation 타입 — 드라이버 부재 시 None으로 fallback (단위 테스트 호환)
try:
    from asyncpg.exceptions import ForeignKeyViolationError as _AsyncpgFKViolation
except ImportError:
    _AsyncpgFKViolation = None

from sqlalchemy.exc import IntegrityError

from src.strategy.exceptions import StrategyHasBacktests, StrategyNotFoundError
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.repository import StrategyRepository
from src.strategy.schemas import (
    CreateStrategyRequest,
    ParseError,
    ParsePreviewResponse,
    StrategyCreateResponse,
    StrategyListItem,
    StrategyListResponse,
    StrategyResponse,
    StrategySettings,
    UnsupportedCallResponse,
    UpdateStrategyRequest,
)

if TYPE_CHECKING:
    from src.backtest.repository import BacktestRepository
    from src.trading.service import WebhookSecretService


_VERSION_RE = re.compile(r"//\s*@version\s*=\s*(\d+)", re.MULTILINE)
_STRATEGY_ENTRY_RE = re.compile(r"\bstrategy\.entry\s*\(", re.MULTILINE)
_STRATEGY_EXIT_RE = re.compile(
    r"\bstrategy\.(?:close(?:_all)?|exit)\s*\(", re.MULTILINE
)
_CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*\(")
_COMMENT_RE = re.compile(r"//[^\n]*")


def _detect_version(source: str) -> PineVersion:
    m = _VERSION_RE.search(source)
    if m is None:
        return PineVersion.v5
    try:
        v = int(m.group(1))
    except ValueError:
        return PineVersion.v5
    return PineVersion.v4 if v == 4 else PineVersion.v5


def _strip_comments(source: str) -> str:
    return _COMMENT_RE.sub("", source)


def _collect_functions(source: str) -> list[str]:
    """소스 텍스트에서 호출된 함수명 best-effort 수집. 주석 제거 후 토큰 매칭."""
    clean = _strip_comments(source)
    # python/pine 공통 예약어 중 call-like 로 잡히는 것 제거
    skip = {
        "if",
        "for",
        "while",
        "and",
        "or",
        "not",
        "in",
        "true",
        "false",
        "input",
    }
    found: dict[str, None] = {}
    for m in _CALL_RE.finditer(clean):
        name = m.group(1)
        if name.lower() in skip:
            continue
        found.setdefault(name, None)
    return sorted(found.keys())


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
    """pine_v2 `parse_to_ast` 로 파싱 → (status, version, warnings, errors, entry_count, exit_count, functions_used).

    AST 생성에 성공하면 status=ok. entry/exit 개수와 함수 사용 목록은 원본
    소스에서 regex 로 근사 수집 (실행 없이 정적 분석).
    """
    version = _detect_version(source)
    clean = _strip_comments(source)
    entry_count = len(_STRATEGY_ENTRY_RE.findall(clean))
    exit_count = len(_STRATEGY_EXIT_RE.findall(clean))
    functions_used = _collect_functions(source)

    try:
        parse_to_ast(source)
    except Exception as exc:  # pynescript / lexer / classifier 오류 전부 error
        return (
            ParseStatus.error,
            version,
            [],
            [
                ParseError(
                    code=type(exc).__name__,
                    message=str(exc),
                    line=getattr(exc, "line", None),
                )
            ],
            entry_count,
            exit_count,
            functions_used,
        )

    return (
        ParseStatus.ok,
        version,
        [],
        [],
        entry_count,
        exit_count,
        functions_used,
    )


class StrategyService:
    def __init__(
        self,
        repo: StrategyRepository,
        # backtest_repo: Sprint 3 호환을 위한 optional. 프로덕션 DI(get_strategy_service)는
        # 항상 주입; None은 unit test 또는 background CLI 경로에서만 허용.
        # None일 경우 backtest 선조회 스킵 — DB FK RESTRICT가 최종 안전망.
        backtest_repo: BacktestRepository | None = None,
        # Sprint 13 Phase A.1.3: webhook_secret atomic auto-issue. 동일 session 으로
        # 주입되면 create() 가 strategy + secret 을 단일 트랜잭션으로 commit.
        # None 이면 auto-issue 스킵 (테스트 / CLI 경로 호환).
        secret_svc: WebhookSecretService | None = None,
    ) -> None:
        self.repo = repo
        self.backtest_repo = backtest_repo
        self._secret_svc = secret_svc

    async def parse_preview(self, pine_source: str) -> ParsePreviewResponse:
        status, version, warnings, errors, entry_count, exit_count, functions_used = (
            _parse(pine_source)
        )
        # Sprint Y1: pre-flight coverage analyzer — 미지원 built-in 식별
        coverage = analyze_coverage(pine_source)
        return ParsePreviewResponse(
            status=status,
            pine_version=version,
            warnings=warnings,
            errors=errors,
            entry_count=entry_count,
            exit_count=exit_count,
            functions_used=functions_used,
            unsupported_builtins=list(coverage.all_unsupported),
            # Sprint 29 Slice B: line 번호 + workaround 포함 상세 응답
            unsupported_calls=[UnsupportedCallResponse(**c) for c in coverage.unsupported_calls],
            # Sprint 29 Slice A: heikinashi Trust Layer 위반 경고
            dogfood_only_warning=coverage.dogfood_only_warning,
            is_runnable=(status == ParseStatus.ok and coverage.is_runnable),
        )

    async def create(
        self, data: CreateStrategyRequest, *, owner_id: UUID
    ) -> StrategyCreateResponse:
        """Sprint 13 Phase A.1.2: webhook_secret atomic auto-issue.

        secret_svc 주입 시 strategy + webhook_secret 단일 트랜잭션. issue(commit=False)
        가 add+flush 만 하고, repo.commit() 이 둘 다 영구 저장. repo.commit() 실패 시
        plaintext 응답 X (둘 다 rollback).
        """
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
            trading_sessions=list(data.trading_sessions),
        )
        saved = await self.repo.create(strategy)

        webhook_secret_plaintext: str | None = None
        if self._secret_svc is not None:
            # commit=False: 동일 session 내 add+flush 만. repo.commit() 이 atomic.
            webhook_secret_plaintext = await self._secret_svc.issue(
                saved.id, commit=False
            )

        await self.repo.commit()  # strategy + webhook_secret 동일 트랜잭션 commit
        base = StrategyResponse.model_validate(saved)
        return StrategyCreateResponse(
            **base.model_dump(),
            webhook_secret=webhook_secret_plaintext,
        )

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
        if data.trading_sessions is not None:
            strategy.trading_sessions = list(data.trading_sessions)
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

    async def update_settings(
        self,
        *,
        strategy_id: UUID,
        owner_id: UUID,
        settings: StrategySettings,
    ) -> StrategyResponse:
        """Sprint 26 — Live Signal Auto-Trading prereq.

        leverage / margin_mode / position_size_pct 저장. None = unset (Live Signal 시작 차단).
        StrategySettings.model_validate 가 router 단에서 통과 → service 는 dump 후 저장만.
        LESSON-019 commit-spy 의무 — repo.commit() 호출.
        """
        strategy = await self.repo.find_by_id_and_owner(strategy_id, owner_id)
        if strategy is None:
            raise StrategyNotFoundError()

        strategy.settings = settings.model_dump()
        updated = await self.repo.update(strategy)
        await self.repo.commit()  # LESSON-019 — broken bug 재발 방어 (Sprint 6/13/15-A 패턴)
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
