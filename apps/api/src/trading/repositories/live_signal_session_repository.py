# trading repository — LiveSignalSession (전략 활성 세션) 영속화 단독 책임

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import String, and_, func, or_, select, text, update
from sqlalchemy import cast as sql_cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from src.common.normalized_symbol import normalize_symbol_input
from src.trading.models import (
    LiveRiskState,
    LiveSignalEvent,
    LiveSignalSession,
    LiveSignalState,
    Order,
    OrderState,
)
from src.trading.repositories.exchange_account_repository import ExchangeAccountRepository

# 창 조회가 훑을 세션 상한. 호출부가 **절단을 감지**할 수 있어야 하므로 조회는 이 값 + 1 건을
# 가져온다 (BL-536 R3-⑥ — 주문 쪽 `ENTRY_ATTEMPT_SCAN_LIMIT` 와 같은 규율).
SESSION_WINDOW_SCAN_LIMIT = 200

# interval → seconds CASE expression (list_active_due 에서 SQL-side 필터)
_INTERVAL_SECONDS_CASE = (
    "CASE interval "
    "WHEN '1m'  THEN INTERVAL '60 seconds' "
    "WHEN '5m'  THEN INTERVAL '300 seconds' "
    "WHEN '15m' THEN INTERVAL '900 seconds' "
    "WHEN '1h'  THEN INTERVAL '3600 seconds' "
    "END"
)

_RECENT_INACTIVE_LIST_LIMIT = 20


class LiveSignalSessionRepository:
    """Sprint 26 — Pine signal evaluate session CRUD + race-safe bar claim.

    LESSON-019 commit-spy 의무 — Service mutation 메서드 마다 await commit().
    """

    async def acquire_code_symbol_admission(
        self,
        account_id: UUID,
        symbol: str,
        *,
        is_code: bool,
        session_id: UUID | None = None,
    ) -> bool:
        """등록/새 코드 진입의 공통 xact 락. 보호·축소에는 호출하지 않는다.

        True 뒤 INSERT 또는 prepare_entry의 commit까지 같은 트랜잭션이어야 한다.
        legacy끼리는 기존 정책을 유지하고 한쪽이 code_v1일 때만 배타적이다.
        """
        scope = await ExchangeAccountRepository(self.session).physical_scope(account_id)
        if scope is None:
            return False
        key, _ = scope
        symbol = normalize_symbol_input(symbol)
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"code-position:{key}:{symbol}"},
        )
        # 락 대기 중 추가된 UID 형제도 포함한다. UID 정체성이 바뀌면 새 요청이 필요하다.
        refreshed = await ExchangeAccountRepository(self.session).physical_scope(account_id)
        if refreshed is None or refreshed[0] != key:
            return False
        _, account_ids = refreshed
        if session_id is not None:
            own_session = await self.session.scalar(
                select(LiveSignalSession).where(
                    col(LiveSignalSession.id) == session_id,
                    col(LiveSignalSession.exchange_account_id) == account_id,
                    col(LiveSignalSession.symbol) == symbol,
                    col(LiveSignalSession.is_active).is_(True),
                    col(LiveSignalSession.execution_snapshot)["source_policy"].astext == "code_v1",
                )
            )
            if own_session is None:
                return False
        code = col(LiveSignalSession.execution_snapshot)["source_policy"].astext == "code_v1"
        unfinished = and_(
            code,
            or_(
                col(LiveRiskState.position_quantity) > 0,
                col(LiveRiskState.entry_terminal).is_(False),
                col(LiveRiskState.cancels_confirmed).is_(False),
                col(LiveRiskState.unsettled_exit_quantity) > 0,
            ),
        )
        # 오래된 영속 행의 raw 표기도 canonical 입력과 같은 소유권으로 묶는다.
        aliases = [symbol, symbol.replace("/", ""), f"{symbol}:{symbol.split('/')[1]}"]
        query = (
            select(LiveSignalSession)
            .outerjoin(LiveRiskState, col(LiveRiskState.session_id) == col(LiveSignalSession.id))
            .where(
                col(LiveSignalSession.exchange_account_id).in_(account_ids),
                col(LiveSignalSession.symbol).in_(aliases),
                or_(col(LiveSignalSession.is_active).is_(True), unfinished),
            )
        )
        if session_id is not None:
            query = query.where(col(LiveSignalSession.id) != session_id)
        if not is_code:
            query = query.where(code)
        if await self.session.scalar(select(query.exists())):
            return False
        entries = select(Order).where(
            col(Order.exchange_account_id).in_(account_ids),
            col(Order.symbol).in_(aliases),
            col(Order.reduce_only).is_(False),
            col(Order.state).in_([OrderState.pending, OrderState.submitted]),
        )
        if not is_code:
            entries = entries.join(
                LiveSignalSession,
                col(Order.risk_context)["session_id"].astext
                == sql_cast(col(LiveSignalSession.id), String),
            ).where(code)
        if session_id is not None:
            own_entry = select(col(LiveRiskState.entry_order_id)).where(
                col(LiveRiskState.session_id) == session_id
            )
            own_generation = (
                select(sql_cast(col(LiveRiskState.generation), String))
                .where(col(LiveRiskState.session_id) == session_id)
                .scalar_subquery()
            )
            # 최종 venue 재검사에서 이미 준비된 자기 세대 진입만 제외한다.
            # COALESCE는 NULL risk_context의 legacy 주문이 NOT(NULL)로 사라지는 것을 막는다.
            own = and_(
                col(Order.id).in_(own_entry),
                col(Order.risk_context)["session_id"].astext == str(session_id),
                col(Order.risk_context)["role"].astext == "entry",
                col(Order.risk_context)["generation"].astext == own_generation,
            )
            entries = entries.where(~func.coalesce(own, False))
        return not bool(await self.session.scalar(select(entries.exists())))

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def save(self, sess: LiveSignalSession) -> LiveSignalSession:
        self.session.add(sess)
        await self.session.flush()
        return sess

    async def get_by_id(self, session_id: UUID) -> LiveSignalSession | None:
        result = await self.session.execute(
            select(LiveSignalSession).where(LiveSignalSession.id == session_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(self, session_id: UUID, user_id: UUID) -> LiveSignalSession | None:
        """ID와 사용자 소유권을 한 질의로 함께 확인한다.

        라우터에서 별도 비교하면 재사용 경로가 소유권 검사를 조용히 빼먹을 수 있다.
        """
        result = await self.session.execute(
            select(LiveSignalSession)
            .where(LiveSignalSession.id == session_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.user_id == user_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def find_active_by_order_id(self, order_id: UUID) -> LiveSignalSession | None:
        """LiveSignalEvent.order_id에 정확히 귀속된 활성 세션을 찾는다."""
        result = await self.session.execute(
            select(LiveSignalSession)
            .join(LiveSignalEvent, LiveSignalEvent.session_id == LiveSignalSession.id)  # type: ignore[arg-type]
            .where(LiveSignalEvent.order_id == order_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712
        )
        return result.scalars().first()

    async def list_active_by_user(self, user_id: UUID) -> Sequence[LiveSignalSession]:
        result = await self.session.execute(
            select(LiveSignalSession)
            .where(LiveSignalSession.user_id == user_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712  # type: ignore[arg-type]
            .order_by(LiveSignalSession.created_at.desc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def list_active_strategy_ids(self, strategy_ids: Sequence[UUID]) -> set[UUID]:
        """주어진 전략 중 활성 라이브 세션이 있는 전략 ID를 집계한다."""
        if not strategy_ids:
            return set()
        result = await self.session.execute(
            select(LiveSignalSession.strategy_id)  # type: ignore[call-overload]
            .where(LiveSignalSession.strategy_id.in_(strategy_ids))  # type: ignore[attr-defined]
            .where(LiveSignalSession.is_active == True)  # noqa: E712
            .distinct()
        )
        return set(result.scalars().all())

    async def list_recent_inactive_by_user(
        self, user_id: UUID, *, limit: int = _RECENT_INACTIVE_LIST_LIMIT
    ) -> Sequence[LiveSignalSession]:
        """사용자의 최근 종료 세션을 화면용으로 제한해 조회한다."""
        if limit <= 0:
            return []

        # 세션은 계속 누적되므로, 회고 화면 목록은 최근 20건을 넘기지 않는다.
        result = await self.session.execute(
            select(LiveSignalSession)
            .where(LiveSignalSession.user_id == user_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == False)  # type: ignore[arg-type]  # noqa: E712
            .order_by(LiveSignalSession.deactivated_at.desc().nullslast())  # type: ignore[union-attr]
            .limit(min(limit, _RECENT_INACTIVE_LIST_LIMIT))
        )
        return result.scalars().all()

    async def list_active_by_account(self, account_id: UUID) -> Sequence[LiveSignalSession]:
        result = await self.session.execute(
            select(LiveSignalSession)
            .where(LiveSignalSession.exchange_account_id == account_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712
            .order_by(LiveSignalSession.created_at.desc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def list_by_account(
        self, account_id: UUID, *, user_id: UUID
    ) -> Sequence[LiveSignalSession]:
        """BL-498 — 계정의 세션을 **활성 여부 무관**하게 최신순으로 조회한다.

        계정 스코프 포지션의 청산 귀속에 쓴다. fail-closed 종료는 세션을 비활성으로
        만들고 포지션은 남기므로, 활성만 보면 정작 그 포지션을 만든 세션을 놓친다.

        ★`user_id` 를 함께 요구한다. 호출자가 계정 소유를 이미 검증하더라도
        `LiveSignalSession.user_id` 와 `exchange_account_id` 는 독립 FK 라 둘의
        소유자가 같다는 DB 제약이 없다. 귀속을 결정하는 조회이므로 방어한다.
        """
        result = await self.session.execute(
            select(LiveSignalSession)
            .where(LiveSignalSession.exchange_account_id == account_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.user_id == user_id)  # type: ignore[arg-type]
            .order_by(LiveSignalSession.created_at.desc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def list_overlapping_window(
        self,
        *,
        since: datetime,
        until: datetime | None = None,
        limit: int = SESSION_WINDOW_SCAN_LIMIT,
    ) -> Sequence[LiveSignalSession]:
        """`[since, until)` 과 생존 구간이 겹치는 세션 (BL-536 오프라인 분해용).

        진입 완결성 CLI 가 `--session-id` 없이 창만 받았을 때 쓴다. 겹침 판정은
        `session.created_at < until AND (deactivated_at IS NULL OR deactivated_at > since)`
        - 활성 세션은 상한이 없으므로 NULL 을 "아직 살아 있다" 로 읽는다.

        ★사용자·계정 스코프가 없다. 운영자가 셸에서 도는 진단 경로 전용이며 HTTP 표면에
        연결하지 않는다. 연결한다면 그때 소유 검증을 반드시 함께 넣어야 한다.

        ★`limit + 1` 건을 가져온다 (BL-536 R3-⑥). 호출부가 `len(rows) > limit` 으로 절단을
        감지해야 한다. 주문 쪽(`list_entry_attempts`)은 이미 그 규율을 지키는데 세션 집합만
        조용히 잘리면, 리포트는 "이 창의 전부" 라고 말하면서 **세션 몇 개를 통째로 빠뜨린다** —
        절단된 분모는 유실률을 낙관적으로 왜곡한다.
        """
        stmt = select(LiveSignalSession).where(
            or_(
                cast(Any, LiveSignalSession.deactivated_at).is_(None),
                cast(Any, LiveSignalSession.deactivated_at) > since,
            )
        )
        if until is not None:
            stmt = stmt.where(cast(Any, LiveSignalSession.created_at) < until)
        stmt = stmt.order_by(LiveSignalSession.created_at.asc()).limit(limit + 1)  # type: ignore[attr-defined]
        return (await self.session.execute(stmt)).scalars().all()

    async def list_by_strategy_account_symbol(
        self,
        *,
        user_id: UUID,
        strategy_id: UUID,
        exchange_account_id: UUID,
        symbol: str,
    ) -> Sequence[LiveSignalSession]:
        """전략 누적 parity용 세션을 활성 여부와 무관하게 읽는다."""
        result = await self.session.execute(
            select(LiveSignalSession)
            .where(LiveSignalSession.user_id == user_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.strategy_id == strategy_id)  # type: ignore[arg-type]
            .where(cast(Any, LiveSignalSession.exchange_account_id) == exchange_account_id)
            .where(LiveSignalSession.symbol == symbol)  # type: ignore[arg-type]
            .order_by(LiveSignalSession.created_at.asc())  # type: ignore[attr-defined]
        )
        return result.scalars().all()

    async def count_active_by_user(self, user_id: UUID) -> int:
        """Sprint 26 quota check — 사용자별 active session ≤ 5."""
        result = await self.session.execute(
            select(func.count(LiveSignalSession.id))  # type: ignore[arg-type]
            .where(LiveSignalSession.user_id == user_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712  # type: ignore[arg-type]
        )
        return int(result.scalar_one() or 0)

    async def list_distinct_active_symbols(self) -> list[str]:
        """활성 라이브 세션이 요구하는 중복 없는 ticker 심볼을 반환한다."""
        result = await self.session.execute(
            select(cast(Any, LiveSignalSession.symbol))
            .where(cast(Any, LiveSignalSession.is_active) == True)  # noqa: E712
            .distinct()
            .order_by(cast(Any, LiveSignalSession.symbol))
        )
        return list(result.scalars().all())

    async def acquire_quota_lock(self, user_id: UUID) -> None:
        """PG advisory xact lock — quota race 방어 (codex G.0 P3 #3 + plan §3 A.4).

        partial unique index 와 함께 이중 방어 (Sprint 11 advisory pattern).
        """
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": f"live_session_quota:{user_id}"},
        )

    async def list_active_due(self, now: datetime) -> Sequence[LiveSignalSession]:
        """interval 별 due session list — codex G.0 P2 #3 패턴 + plan §3 A.4.

        is_active=true AND (last_evaluated_bar_time IS NULL
                            OR last_evaluated_bar_time + interval_seconds <= now).
        Beat task evaluate_live_signals 가 1분 fire 마다 호출.
        """
        # _INTERVAL_SECONDS_CASE 는 module-level constant (사용자 input X) — S608 false positive
        stmt = text(
            "SELECT * FROM trading.live_signal_sessions "  # noqa: S608
            "WHERE is_active = true "
            "AND (last_evaluated_bar_time IS NULL "
            f"     OR last_evaluated_bar_time + ({_INTERVAL_SECONDS_CASE}) <= :now) "
            "ORDER BY id"
        )
        result = await self.session.execute(stmt, {"now": now})
        rows = result.mappings().all()
        return [LiveSignalSession(**dict(row)) for row in rows]

    async def try_claim_bar(self, session_id: UUID, bar_time: datetime, claim_token: UUID) -> bool:
        """codex G.0 P2 #3 — winner-only bar claim.

        UPDATE WHERE id=session_id AND is_active=true AND
        (last_evaluated_bar_time IS NULL OR last_evaluated_bar_time < bar_time).
        rowcount==1 → True (claim 성공). 0 → False (다른 task 가 이미 claim 또는 같은 bar).

        race-safe: 두 worker 가 같은 bar_time 으로 동시 호출해도 1번만 True 반환.
        """
        result = await self.session.execute(
            update(LiveSignalSession)
            .where(LiveSignalSession.id == session_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712
            .where(
                or_(
                    LiveSignalSession.last_evaluated_bar_time.is_(None),  # type: ignore[union-attr]
                    LiveSignalSession.last_evaluated_bar_time < bar_time,  # type: ignore[operator,arg-type]
                )
            )
            .values(
                last_evaluated_bar_time=bar_time,
                bar_claim_token=claim_token,
                updated_at=datetime.now(UTC),
            )
        )
        return (result.rowcount or 0) == 1  # type: ignore[attr-defined]

    async def deactivate(self, session_id: UUID, *, at: datetime, reason: str) -> int:
        """is_active=False + deactivated_at + deactivated_reason. Service 가 commit 책임.

        ★BL-484 — `reason` 은 **기본값 없는 필수 키워드**다. 기본값을 주면 새 종료 경로가
        사유를 빼먹어도 조용히 통과해, 화면에 "왜 죽었는지 모르는 세션" 이 다시 생긴다.
        누락을 타입으로 잡는다(`TypeError` at call time / mypy 에서 `call-arg`).

        값 집합의 정본은 `src.trading.models.SessionDeactivationReason` 이다.
        """
        result = await self.session.execute(
            update(LiveSignalSession)
            .where(LiveSignalSession.id == session_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712
            .values(is_active=False, deactivated_at=at, deactivated_reason=reason)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def deactivate_all_by_owner(self, user_id: UUID, *, at: datetime, reason: str) -> int:
        """소유자의 **활성 세션 전량**을 한 번의 UPDATE 로 내린다 (2026-08-15 surface-truth · S3).

        ★왜 `list_active_by_user` + 루프가 아닌가 — 탈퇴 처리는 「하나도 남으면 안 되는」
        경계다. 루프는 그 사이에 새로 만들어진 세션을 놓치고, 개별 UPDATE 는 부분 성공을
        허용한다. 여기서는 **원장에게 술어를 주고** 한 문장으로 닫는다.

        `deactivate()` 와 같은 술어(`is_active = true`)를 쓰므로 이미 죽은 세션은 건드리지
        않고, 사유·시각도 덮어쓰지 않는다. commit 책임은 호출한 Service 에 있다.

        값 집합의 정본은 `src.trading.models.SessionDeactivationReason` 이다.
        """
        result = await self.session.execute(
            update(LiveSignalSession)
            .where(LiveSignalSession.user_id == user_id)  # type: ignore[arg-type]
            .where(LiveSignalSession.is_active == True)  # type: ignore[arg-type]  # noqa: E712
            .values(is_active=False, deactivated_at=at, deactivated_reason=reason)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def get_state(self, session_id: UUID) -> LiveSignalState | None:
        result = await self.session.execute(
            select(LiveSignalState).where(LiveSignalState.session_id == session_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def upsert_state(
        self,
        *,
        session_id: UUID,
        last_strategy_state_report: dict[str, object],
        total_closed_trades: int,
        total_realized_pnl: Decimal,
        equity_curve: list[dict[str, object]] | None = None,
    ) -> LiveSignalState:
        """INSERT ON CONFLICT DO UPDATE on session_id (1:1 with sessions).

        Service 가 같은 트랜잭션에서 events INSERT + state upsert + commit (codex G.0 P1 #3).

        Sprint 28 Slice 3 (BL-140b): equity_curve 신규 (optional, default None = 갱신 안함).
        Task 가 calculator 로 새 datapoint append 후 전체 array 전달.
        """
        existing = await self.get_state(session_id)
        if existing is None:
            state = LiveSignalState(
                session_id=session_id,
                last_strategy_state_report=last_strategy_state_report,
                total_closed_trades=total_closed_trades,
                total_realized_pnl=total_realized_pnl,
                equity_curve=equity_curve if equity_curve is not None else [],
                updated_at=datetime.now(UTC),
            )
            self.session.add(state)
            await self.session.flush()
            return state
        existing.last_strategy_state_report = last_strategy_state_report
        existing.total_closed_trades = total_closed_trades
        existing.total_realized_pnl = total_realized_pnl
        if equity_curve is not None:
            existing.equity_curve = equity_curve
        existing.updated_at = datetime.now(UTC)
        await self.session.flush()
        return existing
