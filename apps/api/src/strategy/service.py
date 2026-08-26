"""strategy Service. Pine 파싱 + CRUD 조율."""

from __future__ import annotations

import asyncio
import hashlib
import re
from typing import TYPE_CHECKING
from uuid import UUID

# asyncpg FK violation 타입 — 드라이버 부재 시 None으로 fallback (단위 테스트 호환)
try:
    from asyncpg.exceptions import ForeignKeyViolationError as _AsyncpgFKViolation
except ImportError:
    _AsyncpgFKViolation = None

from sqlalchemy.exc import IntegrityError

from src.backtest.serializers import metrics_summary_from_jsonb
from src.strategy.exceptions import StrategyHasBacktests, StrategyNotFoundError
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.pine_v2.ast_classifier import classify_script
from src.strategy.pine_v2.ast_extractor import extract_content
from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.py_renderer import render_python
from src.strategy.pine_v2.signal_extractor import SignalExtractor
from src.strategy.repository import StrategyRepository
from src.strategy.schemas import (
    BriefArg,
    BriefOrderCall,
    CreateStrategyRequest,
    DeclarationResponse,
    InputDeclResponse,
    LatestBacktestSummary,
    ParseError,
    ParsePreviewResponse,
    PythonView,
    StrategyBriefResponse,
    StrategyCreateResponse,
    StrategyLifecycle,
    StrategyListItem,
    StrategyListResponse,
    StrategyResponse,
    StrategySettings,
    UnsupportedCallResponse,
    UpdateStrategyRequest,
)

if TYPE_CHECKING:
    from src.backtest.repository import BacktestRepository
    from src.trading.repositories.live_signal_session_repository import LiveSignalSessionRepository
    from src.trading.services.webhook_secret_service import WebhookSecretService


_VERSION_RE = re.compile(r"//\s*@version\s*=\s*(\d+)", re.MULTILINE)
_STRATEGY_ENTRY_RE = re.compile(r"\bstrategy\.entry\s*\(", re.MULTILINE)
_STRATEGY_EXIT_RE = re.compile(r"\bstrategy\.(?:close(?:_all)?|exit)\s*\(", re.MULTILINE)
# ★`_INPUT_RE` 는 `ast_extractor.extract_content().inputs` 의 중복 구현이 **아니다** —
#   두 수는 다른 것을 센다. 정규식 = `input(` **호출 지점** 수, AST = **override 가능한**
#   input 선언 수(= 단순 대입문의 좌변이 있는 것. 엔진이 그 이름으로만 값을 갈아끼운다).
#   실측 2026-08-27 — corpus 9건은 전건 일치하고, 갈리는 것은 대입 없는 `plot(w=input.int(2))` ·
#   중첩 · 사용자함수 본문 · 튜플 좌변 4형태이며 **AST 가 적게 센다**(`tests/strategy/
#   test_param_count_vs_ast_inputs.py` 가 그 4형태를 고정한다).
# ★★그리고 목록 경로는 AST 로 바꿀 수 없다 — 이 함수는 페이지의 **전 전략**에 대해 돌고,
#   콜드 `extract_content` 는 실측 corpus 9건 합계 **72초**다(정규식 5.7ms · 12,700배).
#   `parse_to_ast` 캐시가 비었거나(신규 프로세스·pynescript 업그레이드) LRU 로 밀리면
#   목록 API 가 그 값을 문다. **파라미터 표·Optimizer 드롭다운은 AST 를 쓰고 목록은 이걸 쓴다.**
_INPUT_RE = re.compile(r"\binput(?:\.\w+)?\s*\(", re.MULTILINE)
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


def _strip_string_literals(source: str) -> str:
    chars = list(source)
    quote: str | None = None
    escaped = False
    in_comment = False

    for index, char in enumerate(source):
        if quote is None:
            if in_comment:
                if char == "\n":
                    in_comment = False
                continue
            if source[index : index + 2] == "//":
                in_comment = True
                continue
            if char in {"'", '"'}:
                quote = char
                chars[index] = " "
            continue

        if char == "\n":
            chars[index] = char
            quote = None
            escaped = False
            continue

        chars[index] = " "
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == quote:
            quote = None

    return "".join(chars)


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


async def _parse(
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
    소스에서 regex 로 근사 수집 (실행 없이 정적 분석). CPU 병목인 parse_to_ast
    한 호출만 asyncio.to_thread로 옮긴다. 가벼운 regex 수집은 현재 이벤트 루프에
    남기며, health router의 기존 asyncio.to_thread 선례를 따른다.
    """
    version = _detect_version(source)
    clean = _strip_comments(source)
    entry_count = len(_STRATEGY_ENTRY_RE.findall(clean))
    exit_count = len(_STRATEGY_EXIT_RE.findall(clean))
    functions_used = _collect_functions(source)

    try:
        await asyncio.to_thread(parse_to_ast, source)
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


def _extract_structure(
    source: str,
) -> tuple[DeclarationResponse | None, list[InputDeclResponse]]:
    """[ADR-040] 선언부 + input 선언을 AST 에서 뽑는다. **실패는 조용히 빈 값**이다.

    ★파싱 비용이 여기서 새로 들지 않는다 — 호출 직전 `_parse` 가 부른 `parse_to_ast` 가
    `lru_cache` 로 살아 있어 같은 소스는 L1 hit 다(`pine_v2/parser_adapter.py`).
    ★`extract_content` 는 파싱 실패 시 예외를 던진다(그 모듈이 「호출자가 안전망을 둬야 한다」고
    적어 뒀다). 판정은 이미 `_parse` 가 냈으므로 여기서 삼킨다 — **구조 추출 실패가 파싱
    판정을 뒤집으면 안 된다.**
    """
    try:
        content = extract_content(source)
    except Exception:
        return None, []

    decl = DeclarationResponse(
        kind=content.declaration.kind,
        title=content.declaration.title,
        default_qty_type=content.declaration.default_qty_type,
        default_qty_value=content.declaration.default_qty_value,
        pyramiding=content.declaration.pyramiding,
    )
    inputs = [
        InputDeclResponse(
            input_type=i.input_type,
            var_name=i.var_name,
            defval=i.defval,
            title=i.title,
        )
        for i in content.inputs
    ]
    return decl, inputs


def _render_python_view(source: str) -> PythonView | None:
    """[ADR-042] 읽기 전용 Python 뷰. **실패는 조용히 None** 이다.

    ★렌더는 판정자가 아니다 — 여기서 던지는 예외가 브리핑 전체를 500 으로 만들면
    사용자는 판정조차 못 본다. `_extract_structure` · `_extract_brief_parts` 와 같은 계약이다.
    ★★**이 산출물은 실행되지 않는다.** 응답 스키마 말고 어디로도 흘러가지 않으며,
    그 부재를 `tests/strategy/pine_v2/test_py_renderer_not_executed.py` 가 집행한다.
    """
    try:
        view = render_python(source)
    except Exception:
        return None
    return PythonView(
        code=view.code,
        source_map=list(view.source_map),
        unrendered=view.unrendered,
    )


def _extract_brief_parts(
    source: str,
) -> tuple[str | None, list[BriefOrderCall], list[str]]:
    """[ADR-040] track · 주문 호출(줄번호 포함) · 신호 변수. **실패는 조용히 빈 값**이다.

    ★`_extract_structure` 와 같은 계약이다 — 판정은 `_parse`/`analyze_coverage` 가 이미 냈고
    여기서 던지는 예외가 브리핑 전체를 500 으로 만들면 **사용자는 판정조차 못 본다.**
    ★셋을 한 함수에 묶은 이유는 셋 다 같은 AST 를 읽기 때문이다(파스 1회 · L1 캐시 공유).
    """
    track: str | None = None
    orders: list[BriefOrderCall] = []
    signals: list[str] = []

    try:
        track = classify_script(source).track
    except Exception:
        track = None

    try:
        calls = extract_content(source).strategy_calls
    except Exception:
        calls = []
    for call in calls:
        orders.append(
            BriefOrderCall(
                name=call.name,
                line=call.line,
                args=[BriefArg(name=a.name, value=a.value) for a in call.args],
            )
        )
    # 소스 순서를 보존하되 줄번호가 있으면 그것으로 정렬한다 — 화면이 위에서 아래로 읽힌다.
    orders.sort(key=lambda o: (o.line is None, o.line or 0))

    try:
        signals = list(SignalExtractor().extract(source, mode="ast").signal_vars)
    except Exception:
        signals = []

    return track, orders, signals


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
        live_session_repo: LiveSignalSessionRepository | None = None,
    ) -> None:
        self.repo = repo
        self.backtest_repo = backtest_repo
        self._secret_svc = secret_svc
        self.live_session_repo = live_session_repo

    async def parse_preview(self, pine_source: str) -> ParsePreviewResponse:
        status, version, warnings, errors, entry_count, exit_count, functions_used = await _parse(
            pine_source
        )
        # Sprint Y1: pre-flight coverage analyzer — 미지원 built-in 식별
        coverage = analyze_coverage(pine_source)
        # [ADR-040] Stage 1 — 선언부 + 파라미터 표. `_parse` 의 L1 캐시에 얹히지만
        # 트리 순회는 CPU 라 to_thread 선례(`_parse`)를 그대로 따른다.
        declaration, inputs = await asyncio.to_thread(_extract_structure, pine_source)
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
            declaration=declaration,
            inputs=inputs,
        )

    async def create(
        self, data: CreateStrategyRequest, *, owner_id: UUID
    ) -> StrategyCreateResponse:
        """Sprint 13 Phase A.1.2: webhook_secret atomic auto-issue.

        secret_svc 주입 시 strategy + webhook_secret 단일 트랜잭션. issue(commit=False)
        가 add+flush 만 하고, repo.commit() 이 둘 다 영구 저장. repo.commit() 실패 시
        plaintext 응답 X (둘 다 rollback).
        """
        status, version, _warnings, errors, _e, _x, _fu = await _parse(data.pine_source)
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
        version_snapshot = await self.repo.create_version(
            strategy_id=saved.id,
            pine_source=saved.pine_source,
        )
        await self.repo.set_current_version(saved.id, version_snapshot.id)

        webhook_secret_plaintext: str | None = None
        if self._secret_svc is not None:
            # commit=False: 동일 session 내 add+flush 만. repo.commit() 이 atomic.
            webhook_secret_plaintext = await self._secret_svc.issue(saved.id, commit=False)

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
        order_by: str = "updated_at",
        order: str = "desc",
    ) -> StrategyListResponse:
        items, total = await self.repo.list_by_owner(
            owner_id,
            limit=limit,
            offset=offset,
            parse_status=parse_status,
            is_archived=is_archived,
            order_by=order_by,
            order=order,
        )

        # response 호환성: page/total_pages는 limit/offset에서 역산.
        total_pages = (total + limit - 1) // limit if total > 0 else 0
        page = (offset // limit) + 1 if limit > 0 else 1
        strategy_ids = [s.id for s in items]
        counts = (
            await self.backtest_repo.count_completed_by_strategy_ids([s.id for s in items])
            if self.backtest_repo is not None and items
            else {}
        )
        latest_backtests = (
            await self.backtest_repo.latest_completed_by_strategy_ids([s.id for s in items])
            if self.backtest_repo is not None and items
            else {}
        )
        active_strategy_ids = (
            await self.live_session_repo.list_active_strategy_ids(strategy_ids)
            if self.live_session_repo is not None and items
            else set()
        )
        return StrategyListResponse(
            items=[
                StrategyListItem.model_validate(s).model_copy(
                    update={
                        "backtest_count": counts.get(s.id, 0),
                        "latest_backtest": (
                            LatestBacktestSummary(
                                backtest_id=row.id,
                                completed_at=row.completed_at,
                                metrics=metrics_summary_from_jsonb(row.metrics),
                            )
                            if (row := latest_backtests.get(s.id)) is not None
                            else None
                        ),
                        "param_count": len(
                            _INPUT_RE.findall(
                                _strip_comments(_strip_string_literals(s.pine_source))
                            )
                        ),
                        "lifecycle": (
                            StrategyLifecycle.deployed
                            if s.id in active_strategy_ids
                            else (
                                StrategyLifecycle.validated
                                if counts.get(s.id, 0) > 0
                                else StrategyLifecycle.draft
                            )
                        ),
                    }
                )
                for s in items
            ],
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

    async def brief(self, *, strategy_id: UUID, owner_id: UUID) -> StrategyBriefResponse:
        """[ADR-040] 백테스트 제출 **전에** 보는 결정론 브리핑.

        ★**LLM 이 만든 값이 하나도 없다.** 해설 층은 별 엔드포인트이고, 그쪽이 죽어도
        이 응답만으로 화면이 완결되어야 한다는 것이 [ADR-040] 결정 4 다.
        ★분석 대상은 `Strategy.pine_source` — 백테스트 제출 시 그 소스가 스냅샷으로 고정되므로
        (`_ensure_current_strategy_version`) 「지금 제출하면 무엇이 도는가」와 일치한다.
        """
        strategy = await self.repo.find_by_id_and_owner(strategy_id, owner_id)
        if strategy is None:
            raise StrategyNotFoundError()

        source = strategy.pine_source
        parse = await self.parse_preview(source)
        track, orders, signals = await asyncio.to_thread(_extract_brief_parts, source)
        python_view = await asyncio.to_thread(_render_python_view, source)

        return StrategyBriefResponse(
            strategy_id=strategy.id,
            # `repository.create_version` 과 **같은 식**이어야 한다 — 해설 캐시가 이 값을 키로 쓴다.
            source_hash=hashlib.sha256(source.encode()).hexdigest(),
            track=track,
            parse=parse,
            orders=orders,
            signals=signals,
            python_view=python_view,
        )

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
            status, version, _w, errors, _e, _x, _fu = await _parse(data.pine_source)
            strategy.pine_source = data.pine_source
            strategy.pine_version = version
            strategy.parse_status = status
            strategy.parse_errors = [e.model_dump() for e in errors] if errors else None
            version_snapshot = await self.repo.create_version(
                strategy_id=strategy.id,
                pine_source=data.pine_source,
            )
            await self.repo.set_current_version(strategy.id, version_snapshot.id)

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
        if self.backtest_repo is not None and await self.backtest_repo.exists_for_strategy(
            strategy_id
        ):
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
