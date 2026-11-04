"""Backtest REST API — 엔드포인트 10개 (자체 소유 7개 + Sprint 41 공유(share) 3개)."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Response

from src.auth.dependencies import CurrentUserDep
from src.backtest.dependencies import BacktestServiceDep
from src.backtest.schemas import (
    BacktestCancelResponse,
    BacktestCreatedResponse,
    BacktestDetail,
    BacktestProgressResponse,
    BacktestSummary,
    CreateBacktestRequest,
    ShareTokenResponse,
    TradeItem,
    TradeOhlcvResponse,
)
from src.common.pagination import Page
from src.common.rate_limit import limiter

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("", status_code=202)
@limiter.limit("10/minute")
async def submit_backtest(
    request: Request,  # slowapi 가 IP/key 추출에 사용 (첫 번째 위치)
    data: CreateBacktestRequest,
    response: Response,
    user: CurrentUserDep,
    service: BacktestServiceDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> BacktestCreatedResponse:
    """POST /backtests.

    Sprint 9-6 E2: Idempotency-Key + 동일 body → `replayed=True` 반환 +
    응답 헤더 `X-Idempotency-Replayed: true`. 상태 코드는 replay/신규 모두
    202 유지 ("Accepted" 의미 — 신규 or 기존 queued 둘 다 async).
    """
    result = await service.submit(data, user_id=user.id, idempotency_key=idempotency_key)
    if result.replayed:
        response.headers["X-Idempotency-Replayed"] = "true"
    return result


@router.get("")
async def list_backtests(
    user: CurrentUserDep,
    service: BacktestServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    order_by: Annotated[
        Literal["created_at", "total_return", "max_drawdown", "sharpe_ratio", "num_trades"], Query()
    ] = "created_at",
    order: Annotated[Literal["asc", "desc"], Query()] = "desc",
) -> Page[BacktestSummary]:
    return await service.list(
        user_id=user.id,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order=order,
    )


@router.get("/{backtest_id}")
async def get_backtest(
    backtest_id: UUID,
    user: CurrentUserDep,
    service: BacktestServiceDep,
) -> BacktestDetail:
    return await service.get(backtest_id, user_id=user.id)


@router.get("/{backtest_id}/trades")
async def list_backtest_trades(
    backtest_id: UUID,
    user: CurrentUserDep,
    service: BacktestServiceDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[TradeItem]:
    return await service.list_trades(backtest_id, user_id=user.id, limit=limit, offset=offset)


@router.get("/{backtest_id}/trades/{trade_index}/ohlcv")
async def get_trade_ohlcv(
    backtest_id: UUID,
    trade_index: int,
    user: CurrentUserDep,
    service: BacktestServiceDep,
) -> TradeOhlcvResponse:
    return await service.trade_ohlcv(backtest_id, trade_index, user_id=user.id)


@router.get("/{backtest_id}/progress")
async def get_backtest_progress(
    backtest_id: UUID,
    user: CurrentUserDep,
    service: BacktestServiceDep,
) -> BacktestProgressResponse:
    return await service.progress(backtest_id, user_id=user.id)


@router.post(
    "/{backtest_id}/cancel",
    status_code=202,
)
async def cancel_backtest(
    backtest_id: UUID,
    user: CurrentUserDep,
    service: BacktestServiceDep,
) -> BacktestCancelResponse:
    return await service.cancel(backtest_id, user_id=user.id)


@router.delete("/{backtest_id}", status_code=204)
async def delete_backtest(
    backtest_id: UUID,
    user: CurrentUserDep,
    service: BacktestServiceDep,
) -> None:
    await service.delete(backtest_id, user_id=user.id)


# Sprint 41 Worker H — share read-only public link (revoke 가능). PDF P1 deferral.


@router.post("/{backtest_id}/share")
async def create_share(
    backtest_id: UUID,
    user: CurrentUserDep,
    service: BacktestServiceDep,
) -> ShareTokenResponse:
    """Owner 가 share_token 생성. 멱등 — active token 있으면 그대로 반환.

    secrets.token_urlsafe(32) = 256-bit entropy. revoke 후 재생성 시 새 토큰 발급.
    """
    return await service.create_share(backtest_id, user_id=user.id)


@router.delete("/{backtest_id}/share", status_code=204)
async def revoke_share(
    backtest_id: UUID,
    user: CurrentUserDep,
    service: BacktestServiceDep,
) -> None:
    """Owner 가 share_token 비활성화. 토큰 자체는 유지 — 재활성화 불가.

    이후 view_share 가 410 Gone. 새 share 생성 시 새 토큰 발급.
    """
    await service.revoke_share(backtest_id, user_id=user.id)


@router.get("/share/{token}")
async def view_share(
    token: str,
    service: BacktestServiceDep,
) -> BacktestDetail:
    """Public read-only — 인증 미사용 (`get_current_user` 의존성 X).

    422 risk 없음 (path param str). 응답:
    - 200: token active → BacktestDetail (error 필드 strip)
    - 404: token 매칭 row 없음
    - 410: row 있으나 share_revoked_at NOT NULL
    """
    return await service.view_share(token)
