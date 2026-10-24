"""HTTP·WS·워커가 같은 새 정책 실행기를 조립하는 경계다."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.providers import BybitFuturesProvider
from src.trading.repositories.code_risk_repository import CodeRiskRepository
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.account_service import ExchangeAccountService
from src.trading.services.code_order_observation_service import CodeOrderObservationService
from src.trading.services.code_risk_executor import CodeRiskExecutor
from src.trading.services.code_risk_service import CodeRiskService
from src.trading.services.code_risk_venue import BybitCodeRiskVenue


def build_code_risk_executor(
    session: AsyncSession, accounts: ExchangeAccountService, provider: BybitFuturesProvider
) -> tuple[CodeRiskService, CodeRiskExecutor]:
    repo = CodeRiskRepository(session)
    risk = CodeRiskService(repo)
    orders = OrderRepository(session)
    observer = CodeOrderObservationService(orders, risk, risk_repo=repo)
    venue = BybitCodeRiskVenue(repo, orders, risk, accounts, provider, observer=observer)
    return risk, CodeRiskExecutor(repo, risk, venue)
