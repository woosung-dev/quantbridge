"""Python 연구 전략 HTTP 경계. 사용자 코드 실행은 별도 실행기에만 위임한다."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.common.rate_limit import limiter
from src.python_strategy.dependencies import get_python_strategy_service
from src.python_strategy.schemas import (
    PythonBacktestRequest,
    PythonCapabilities,
    PythonRunDetail,
    PythonRunList,
    PythonStrategyDetail,
    PythonStrategyList,
    SavePythonStrategy,
)
from src.python_strategy.service import PythonStrategyService

router = APIRouter(prefix="/python-strategies", tags=["python-strategies"])


@router.get("/capabilities", response_model=PythonCapabilities)
async def capabilities(
    user: CurrentUser = Depends(get_current_user),
    service: PythonStrategyService = Depends(get_python_strategy_service),
) -> PythonCapabilities:
    return await service.capabilities()


@router.get("", response_model=PythonStrategyList)
async def list_strategies(
    user: CurrentUser = Depends(get_current_user),
    service: PythonStrategyService = Depends(get_python_strategy_service),
) -> PythonStrategyList:
    return PythonStrategyList(items=await service.list_strategies(user.id))


@router.post("", response_model=PythonStrategyDetail, status_code=201)
@limiter.limit("10/minute")
async def create_strategy(
    request: Request,
    data: SavePythonStrategy,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    service: PythonStrategyService = Depends(get_python_strategy_service),
) -> PythonStrategyDetail:
    return await service.save(data, user.id)


@router.get("/backtests/{run_id}", response_model=PythonRunDetail)
async def get_run(
    run_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: PythonStrategyService = Depends(get_python_strategy_service),
) -> PythonRunDetail:
    return await service.get_run(run_id, user.id)


@router.post("/backtests/{run_id}/cancel", response_model=PythonRunDetail)
async def cancel_run(
    run_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: PythonStrategyService = Depends(get_python_strategy_service),
) -> PythonRunDetail:
    return await service.cancel(run_id, user.id)


@router.get("/{strategy_id}", response_model=PythonStrategyDetail)
async def get_strategy(
    strategy_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: PythonStrategyService = Depends(get_python_strategy_service),
) -> PythonStrategyDetail:
    return await service.get(strategy_id, user.id)


@router.put("/{strategy_id}", response_model=PythonStrategyDetail)
@limiter.limit("10/minute")
async def update_strategy(
    request: Request,
    strategy_id: UUID,
    data: SavePythonStrategy,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    service: PythonStrategyService = Depends(get_python_strategy_service),
) -> PythonStrategyDetail:
    return await service.save(data, user.id, strategy_id)


@router.get("/{strategy_id}/backtests", response_model=PythonRunList)
async def list_runs(
    strategy_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: PythonStrategyService = Depends(get_python_strategy_service),
) -> PythonRunList:
    return PythonRunList(items=await service.runs(strategy_id, user.id))


@router.post("/{strategy_id}/backtests", response_model=PythonRunDetail, status_code=202)
@limiter.limit("5/minute")
async def submit_run(
    request: Request,
    strategy_id: UUID,
    data: PythonBacktestRequest,
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    service: PythonStrategyService = Depends(get_python_strategy_service),
) -> PythonRunDetail:
    return await service.submit(strategy_id, data, user.id)
