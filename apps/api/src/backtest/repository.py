"""BacktestRepository — AsyncSession 유일 보유, DB 접근 전담."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Numeric, and_, case, delete, func, literal, or_, select, text, update
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from src.backtest.engine.metrics import (
    SHARPE_CONVENTION_DAILY,
    SHARPE_CONVENTION_MONTHLY,
    SHARPE_CONVENTION_NONPOSITIVE_EQUITY,
    SHARPE_CONVENTION_UNAVAILABLE,
)
from src.backtest.models import Backtest, BacktestStatus, BacktestTrade

# --- [BL-462] Sharpe 정렬 등급 — 값 하나로는 의미가 다른 것들이 한 순위로 섞인다 ---
#
# 등급은 `metrics->>'sharpe_convention'` 으로만 판정한다. 값(`sharpe_ratio`)은 등급을
# 정하지 않는다 — 파산 계좌의 0 과 무거래 계좌의 0 은 같은 숫자지만 같은 사실이 아니다.
_SHARPE_GRADE_COMPARABLE = 0  # 척도를 아는 값 (tv_daily_rfr2 · tv_monthly_rfr2)
_SHARPE_GRADE_UNKNOWN_SCALE = 1  # 컨벤션 키 부재 = 구 행. 어떤 척도인지 모른다
_SHARPE_GRADE_DEGENERATE = 2  # 산출 불가. 저장된 0 은 「0 점」이 아니라 「없음」이다
# 값 자체가 없다 — 미완료 실행(QUEUED/RUNNING/FAILED)은 `metrics` 가 NULL 이다.
# ★종전 `sharpe DESC NULLS LAST` 는 이 행들을 **전체 맨 뒤**에 뒀다. 등급을 컨벤션으로만
#   정하면 이 행들이 등급 1 로 떨어져 **완료된 degenerate 행보다 위로 올라온다** — 회귀다.
#   `list_by_user` 에는 status 필터가 없어서 실제로 섞여 들어온다.
_SHARPE_GRADE_NO_VALUE = 3

# 정렬 비교 **전용** 연율화 계수. `metrics.sharpe_ratio()` 의 "연율화하지 않는다" 는
# 저장·표시 규약이고 그대로 유지된다 — 이 계수는 ORDER BY 안에만 있고 응답 payload 의
# `sharpe_ratio` 에 닿지 않는다.
#
# ★분모는 **엔진이 쓰는 주기 정의와 같아야 한다** — `engine/metrics.py:70,74` 가
#   monthly = `_RFR_ANNUAL / 12`, daily = `_RFR_ANNUAL / 365` 이고 daily 표본은
#   `equity.resample("D")` 즉 **달력일**이다. 그래서 일간 계수는 √365 다.
# ★★**거래일 252 를 쓰지 마라.** 2026-08-11 의 첫 구현이 √252 였고(동결 스펙의 오류),
#   그러면 RFR 은 365 로 나누고 연율화는 252 로 하는 **서로 다른 축**이 된다. 이 레포는
#   24/7 crypto 이고 문자열 `252` 는 `apps/api/src` 어디에도 없다 — 관례가 아니었다.
#   순위가 실제로 갈리는 구간은 monthly/daily ∈ (√(252/12), √(365/12)) = (4.583, 5.514) 이고
#   그 구간을 겨눈 단위 테스트가 없으면 계수를 되돌려도 아무것도 빨개지지 않는다.
_SHARPE_ANNUALIZATION_FACTORS: dict[str, Decimal] = {
    SHARPE_CONVENTION_DAILY: Decimal(365).sqrt(),
    SHARPE_CONVENTION_MONTHLY: Decimal(12).sqrt(),
}
# 알려진 degenerate 컨벤션 2종 — 명시적으로 적는다(무엇을 재는지 코드에서 읽혀야 한다).
_SHARPE_DEGENERATE_CONVENTIONS = (
    SHARPE_CONVENTION_UNAVAILABLE,
    SHARPE_CONVENTION_NONPOSITIVE_EQUITY,
)
# ★그리고 **접두 규칙을 함께** 쓴다 — 정확일치만 두면 `engine/metrics.py` 에 5번째
#   `unavailable_*` 컨벤션이 추가되는 순간 **조용히 등급 1**(= 정직한 음수보다 위)로 떨어진다.
#   둘을 OR 로 묶으면 오늘의 2종은 명시적이고 내일의 추가분은 자동으로 잡힌다.
_SHARPE_DEGENERATE_PREFIX = "unavailable"


def sharpe_sort_criteria(
    value: Any,
    *,
    order: str,
    convention: Any | None = None,
) -> list[Any]:
    """[BL-462] Sharpe 정렬 키 = `(등급 ASC, 정규화값 order방향)`.

    ★**등급은 `order` 와 무관하게 항상 ASC 다.** `order=asc`(나쁜 것 먼저)에서도
    degenerate 는 맨 뒤다 — 「모르는 것」은 「가장 나쁜 것」이 아니다. 등급을 `order` 에
    딸려 뒤집으면 파산 계좌가 -0.3 을 낸 정직한 전략보다 위로 올라온다.

    컨벤션이 NULL(키 부재)이거나 알 수 없는 문자열이면 등급 1 — 척도 미상이다.
    `serializers.metrics_to_jsonb` 가 None 필드의 키를 아예 생략하므로 구 행에는
    `sharpe_convention` 키 자체가 없다.
    ★**「키 부재」와 「키가 JSON null」은 `->>` 로는 구분되지 않는다** — 둘 다 SQL NULL 이고
    `?` 연산자만 갈라 준다(psql 실측 `t|t|f|t`). 둘을 같은 등급으로 두는 것은 의도다.

    ★**값이 없는 행은 등급 3 으로 전체 맨 뒤**다. 종전 `nulls_last()` 가 하던 일이고,
    등급을 컨벤션으로만 정하면 미완료 실행이 완료된 degenerate 행을 앞지른다.
    """
    if convention is None:
        convention = Backtest.metrics["sharpe_convention"].astext  # type: ignore[index]
    grade = case(
        (value.is_(None), _SHARPE_GRADE_NO_VALUE),
        (convention.in_(list(_SHARPE_ANNUALIZATION_FACTORS)), _SHARPE_GRADE_COMPARABLE),
        (
            or_(
                convention.in_(list(_SHARPE_DEGENERATE_CONVENTIONS)),
                convention.like(f"{_SHARPE_DEGENERATE_PREFIX}%"),
            ),
            _SHARPE_GRADE_DEGENERATE,
        ),
        else_=_SHARPE_GRADE_UNKNOWN_SCALE,
    )
    normalized = case(
        *[
            (convention == name, value * literal(factor, Numeric))
            for name, factor in _SHARPE_ANNUALIZATION_FACTORS.items()
        ],
        else_=value,
    )
    normalized_order = normalized.asc() if order == "asc" else normalized.desc()
    return [grade.asc(), normalized_order.nulls_last()]


class BacktestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- 트랜잭션 제어 ---

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    # --- CRUD ---

    async def create(self, bt: Backtest) -> Backtest:
        self.session.add(bt)
        await self.session.flush()
        return bt

    async def get_by_id(
        self,
        backtest_id: UUID,
        *,
        user_id: UUID | None = None,
        defer_equity_curve: bool = False,
    ) -> Backtest | None:
        stmt = select(Backtest).where(Backtest.id == backtest_id)  # type: ignore[arg-type]
        if user_id is not None:
            stmt = stmt.where(Backtest.user_id == user_id)  # type: ignore[arg-type]
        if defer_equity_curve:
            # 소유권/메타만 필요한 경로(예: 거래 OHLCV)에서 무거운 equity_curve 미로드.
            stmt = stmt.options(defer(Backtest.equity_curve))  # type: ignore[arg-type]
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
        order_by: str = "created_at",
        order: str = "desc",
    ) -> tuple[Sequence[Backtest], int]:
        total_stmt = (
            select(func.count())
            .select_from(Backtest)
            .where(
                Backtest.user_id == user_id  # type: ignore[arg-type]
            )
        )
        total = (await self.session.execute(total_stmt)).scalar_one()

        sort_columns: dict[str, Any] = {
            "created_at": Backtest.created_at,
            "total_return": Backtest.metrics["total_return"].astext.cast(Numeric),  # type: ignore[index]
            "max_drawdown": Backtest.metrics["max_drawdown"].astext.cast(Numeric),  # type: ignore[index]
            "sharpe_ratio": Backtest.metrics["sharpe_ratio"].astext.cast(Numeric),  # type: ignore[index]
            "num_trades": Backtest.metrics["num_trades"].astext.cast(Numeric),  # type: ignore[index]
        }
        sort_expression = sort_columns[order_by]
        if order_by == "sharpe_ratio":
            order_criteria = sharpe_sort_criteria(sort_expression, order=order)
        else:
            primary_order = sort_expression.asc() if order == "asc" else sort_expression.desc()
            if order_by != "created_at":
                primary_order = primary_order.nulls_last()
            order_criteria = [primary_order]

        stmt = (
            select(Backtest)
            .options(defer(Backtest.equity_curve))  # type: ignore[arg-type]
            .where(Backtest.user_id == user_id)  # type: ignore[arg-type]
            .order_by(
                *order_criteria,
                Backtest.created_at.desc(),  # type: ignore[attr-defined]
                Backtest.id.desc(),  # type: ignore[attr-defined]
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def count_completed_by_strategy_ids(
        self, strategy_ids: Sequence[UUID]
    ) -> dict[UUID, int]:
        """전략별 완료 백테스트 수를 단일 GROUP BY 쿼리로 집계한다."""
        if not strategy_ids:
            return {}
        stmt = (
            select(Backtest.strategy_id, func.count())  # type: ignore[call-overload]
            .where(Backtest.status == BacktestStatus.COMPLETED)
            .where(Backtest.strategy_id.in_(strategy_ids))  # type: ignore[attr-defined]
            .group_by(Backtest.strategy_id)
        )
        result = await self.session.execute(stmt)
        return {strategy_id: int(count) for strategy_id, count in result.all()}

    async def latest_completed_by_strategy_ids(
        self, strategy_ids: Sequence[UUID]
    ) -> dict[UUID, Row[Any]]:
        """전략별 가장 최근 완료 백테스트를 단일 DISTINCT ON 쿼리로 조회한다."""
        if not strategy_ids:
            return {}
        stmt = (
            select(  # type: ignore[call-overload]
                Backtest.strategy_id,
                Backtest.id,
                Backtest.completed_at,
                Backtest.metrics,
            )
            .where(Backtest.status == BacktestStatus.COMPLETED)
            .where(Backtest.strategy_id.in_(strategy_ids))  # type: ignore[attr-defined]
            .distinct(Backtest.strategy_id)
            .order_by(
                Backtest.strategy_id,
                Backtest.completed_at.desc().nulls_last(),  # type: ignore[union-attr]
                Backtest.created_at.desc(),  # type: ignore[attr-defined]
                Backtest.id.desc(),  # type: ignore[attr-defined]
            )
        )
        result = await self.session.execute(stmt)
        return {row.strategy_id: row for row in result.all()}

    async def delete(self, backtest_id: UUID) -> int:
        result = await self.session.execute(
            delete(Backtest).where(Backtest.id == backtest_id)  # type: ignore[arg-type]
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    # --- 조건부 상태 전이 (3-guard cancel logic §5.1) ---

    async def transition_to_running(self, backtest_id: UUID, *, started_at: datetime) -> int:
        """queued → running. 조건부 UPDATE. Returns affected rows."""
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)  # type: ignore[arg-type]
            .where(Backtest.status == BacktestStatus.QUEUED)  # type: ignore[arg-type]
            .values(status=BacktestStatus.RUNNING, started_at=started_at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def complete(
        self,
        backtest_id: UUID,
        *,
        metrics: dict[str, Any],
        equity_curve: list[Any],
        where_status: BacktestStatus = BacktestStatus.RUNNING,
    ) -> int:
        """Running → completed. 조건부. Returns affected rows."""
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)  # type: ignore[arg-type]
            .where(Backtest.status == where_status)  # type: ignore[arg-type]
            .values(
                status=BacktestStatus.COMPLETED,
                metrics=metrics,
                equity_curve=equity_curve,
                completed_at=datetime.now(UTC),
            )
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def fail(
        self,
        backtest_id: UUID,
        *,
        error: str,
        where_status: BacktestStatus = BacktestStatus.RUNNING,
    ) -> int:
        """Running → failed. 조건부."""
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)  # type: ignore[arg-type]
            .where(Backtest.status == where_status)  # type: ignore[arg-type]
            .values(
                status=BacktestStatus.FAILED,
                error=error[:2000],  # defensive truncation
                completed_at=datetime.now(UTC),
            )
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def request_cancel(self, backtest_id: UUID) -> int:
        """queued/running → cancelling. 조건부."""
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)  # type: ignore[arg-type]
            .where(
                Backtest.status.in_(  # type: ignore[attr-defined]
                    [BacktestStatus.QUEUED, BacktestStatus.RUNNING]
                )
            )
            .values(status=BacktestStatus.CANCELLING)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    async def finalize_cancelled(self, backtest_id: UUID, *, completed_at: datetime) -> int:
        """cancelling → cancelled. 조건부. Worker guards에서 호출."""
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)  # type: ignore[arg-type]
            .where(Backtest.status == BacktestStatus.CANCELLING)  # type: ignore[arg-type]
            .values(status=BacktestStatus.CANCELLED, completed_at=completed_at)
        )
        return result.rowcount or 0  # type: ignore[attr-defined]

    # --- Trades ---

    async def insert_trades_bulk(self, trades: list[BacktestTrade]) -> None:
        """Bulk insert. Transaction 내에서 호출 (service가 commit)."""
        self.session.add_all(trades)
        await self.session.flush()

    async def list_trades(
        self, backtest_id: UUID, *, limit: int, offset: int
    ) -> tuple[Sequence[BacktestTrade], int]:
        total_stmt = (
            select(func.count())
            .select_from(BacktestTrade)
            .where(
                BacktestTrade.backtest_id == backtest_id  # type: ignore[arg-type]
            )
        )
        total = (await self.session.execute(total_stmt)).scalar_one()

        stmt = (
            select(BacktestTrade)
            .where(BacktestTrade.backtest_id == backtest_id)  # type: ignore[arg-type]
            .order_by(BacktestTrade.trade_index.asc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def get_trade_by_index(self, backtest_id: UUID, trade_index: int) -> BacktestTrade | None:
        """백테스트의 거래 인덱스로 단일 거래를 조회한다."""
        stmt = select(BacktestTrade).where(
            BacktestTrade.backtest_id == backtest_id,  # type: ignore[arg-type]
            BacktestTrade.trade_index == trade_index,  # type: ignore[arg-type]
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_trades_by_direction(self, backtest_id: UUID) -> tuple[int, int, int]:
        """방향별 거래 수 집계 (open + closed 모두 포함).

        Sprint 31-E (BL-155): metrics.long_count/short_count 가 **closed only** 만
        집계해 FE 거래 목록 (open + closed = trades.length) 과 1건 mismatch 발생.
        (구 vectorbt `trades.long.count()` 시절의 의미를 pine_v2 `v2_adapter` 가
        그대로 이어받았다 — 엔진만 바뀌었고 집계 모수는 같다.) service layer
        에서 본 helper 로 재계산해 사용자 시점 일관성 유지.

        Returns:
            (total, long, short) — 모두 open + closed 포함.
        """
        from src.backtest.models import TradeDirection

        total_stmt = (
            select(func.count())
            .select_from(BacktestTrade)
            .where(BacktestTrade.backtest_id == backtest_id)  # type: ignore[arg-type]
        )
        long_stmt = (
            select(func.count())
            .select_from(BacktestTrade)
            .where(BacktestTrade.backtest_id == backtest_id)  # type: ignore[arg-type]
            .where(BacktestTrade.direction == TradeDirection.LONG)  # type: ignore[arg-type]
        )
        short_stmt = (
            select(func.count())
            .select_from(BacktestTrade)
            .where(BacktestTrade.backtest_id == backtest_id)  # type: ignore[arg-type]
            .where(BacktestTrade.direction == TradeDirection.SHORT)  # type: ignore[arg-type]
        )
        total = (await self.session.execute(total_stmt)).scalar_one()
        long_n = (await self.session.execute(long_stmt)).scalar_one()
        short_n = (await self.session.execute(short_stmt)).scalar_one()
        return int(total), int(long_n), int(short_n)

    # --- Sprint 41 Worker H — share token lookup (public read-only) ---

    async def get_by_share_token(self, token: str) -> Backtest | None:
        """share_token 으로 Backtest 조회. owner check 없음 (토큰이 capability).

        본 endpoint 만 user_id filter 없는 SELECT — public read-only share view 용.
        revoke 판정은 service layer 에서 share_revoked_at 검사.
        """
        result = await self.session.execute(
            select(Backtest).where(Backtest.share_token == token)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, backtest_id: UUID, *, user_id: UUID) -> Backtest | None:
        """SELECT ... FOR UPDATE — codex P2 race condition fix.

        share_token 발급 시 동시 POST 2개가 둘 다 NULL 읽고 다른 토큰 commit 하는
        last-writer-wins race 차단. 첫 요청이 row lock 잡으면 두번째 요청은 commit
        대기 → 다시 read 시 첫 토큰 보임 → 멱등 반환.
        """
        stmt = (
            select(Backtest)
            .where(Backtest.id == backtest_id)  # type: ignore[arg-type]
            .where(Backtest.user_id == user_id)  # type: ignore[arg-type]
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # --- Idempotency (Sprint 9-6) ---

    async def get_by_idempotency_key(self, key: str) -> Backtest | None:
        result = await self.session.execute(
            select(Backtest).where(Backtest.idempotency_key == key)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()

    async def acquire_idempotency_lock(self, key: str) -> None:
        """PG advisory lock (tx-scoped) — final authority 로서 correctness 보장.

        Sprint 10 Phase A2 에서 Redis contention-detect wrapping (SET NX + 즉시 DEL) 을
        본 메서드 직전에 두었으나 **lock hold ≈ 1 RTT 로 mutual exclusion 미성립**.
        Sprint 11 Phase E 에서 Service layer 로 이동하여 real distributed mutex 승격:
        `async with RedisLock(...): await service.submit(...)` 패턴. Repository 는
        PG advisory lock 만 담당 (tx 경계 + UNIQUE 제약 + IntegrityError fallback).
        """
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:k))"),
            {"k": key},
        )

    # --- Cross-domain query (§4.8 Strategy delete 선조회) ---

    async def exists_for_strategy(self, strategy_id: UUID) -> bool:
        stmt = (
            select(func.count())
            .select_from(Backtest)
            .where(
                Backtest.strategy_id == strategy_id  # type: ignore[arg-type]
            )
        )
        count = (await self.session.execute(stmt)).scalar_one()
        return count > 0

    # --- Stale reclaim (§8.3) ---

    async def reclaim_stale(self, *, threshold_seconds: int, now: datetime) -> tuple[int, int]:
        """running/cancelling 중 stale → terminal.

        Running: started_at + threshold < now → failed.
        Cancelling: started_at 있으면 그 기준, 없으면 (QUEUED→CANCELLING 케이스)
                    created_at + threshold < now 기준으로 reclaim → cancelled.
                    후자 없으면 worker가 pickup 못 한 queued-cancel이 영영 stuck.

        Returns (reclaimed_running, reclaimed_cancelling).
        """
        cutoff = now - timedelta(seconds=threshold_seconds)

        running_result = await self.session.execute(
            update(Backtest)
            .where(Backtest.status == BacktestStatus.RUNNING)  # type: ignore[arg-type]
            .where(Backtest.started_at < cutoff)  # type: ignore[arg-type,operator]
            .values(
                status=BacktestStatus.FAILED,
                error="Stale running — reclaimed by worker startup",
                completed_at=now,
            )
        )
        cancelling_result = await self.session.execute(
            update(Backtest)
            .where(Backtest.status == BacktestStatus.CANCELLING)  # type: ignore[arg-type]
            .where(
                or_(
                    Backtest.started_at < cutoff,  # type: ignore[arg-type,operator]
                    and_(
                        Backtest.started_at.is_(None),  # type: ignore[union-attr]
                        Backtest.created_at < cutoff,  # type: ignore[arg-type]
                    ),
                )
            )
            .values(
                status=BacktestStatus.CANCELLED,
                completed_at=now,
            )
        )
        return (
            running_result.rowcount or 0,  # type: ignore[attr-defined]
            cancelling_result.rowcount or 0,  # type: ignore[attr-defined]
        )
