# trading service — 세션 시작 전 「그 거래소 계정이 우리 것뿐인가」 단독 책임 (BL-634)

from __future__ import annotations

import logging
from uuid import UUID

from src.trading.exceptions import AccountNotExclusive
from src.trading.models import ExchangeAccount
from src.trading.providers import BybitFuturesProvider
from src.trading.repositories.exchange_account_repository import (
    ExchangeAccountRepository,
)
from src.trading.repositories.order_repository import OrderRepository
from src.trading.services.account_service import ExchangeAccountService

logger = logging.getLogger(__name__)


class AccountExclusivityService:
    """세션 등재 전제조건 — 거래소 계정에 **남의 미체결 조건부 주문**이 없어야 한다.

    ## 왜 DB 가 아니라 거래소를 보는가

    [BL-633] 부검(2026-08-08)이 확정한 사망 원인은 오라클 서버와 맥 로컬이 **같은**
    Bybit demo 계정에 같은 전략·심볼·주기로 동시에 붙은 것이었다. 호스트가 둘이면
    **데이터베이스도 둘**이라 `uq_live_sessions_active_unique` 는 원리상 무력하다 —
    각 DB 안에서 제약은 정상 성립했고, 둘을 합친 상태를 아는 주체가 없었다. 두 호스트가
    공유하는 유일한 상태는 **거래소 계정 그 자체**이므로 판정도 거기서 한다.

    ## 왜 체결 이력이 아니라 **미체결(resting) 조건부 주문**인가

    「원장에 없는 청산 이력이 있으면 남의 호스트다」로 만들면 **상시 거부**가 된다.
    미조인 `exchange_exits` 는 정상 상황에서도 난다([BL-639] — 계정을 좁혀도 287행 중
    25행(8.7%)이 남고 그중 12건이 사용자 수동 청산이다). resting 은 그런 유도 없이
    **지금 이 순간 그 계정에 걸려 있는** 주문이라 「다른 호스트가 붙어 있다」의 직접
    증거다. 정상 상황 실측에서 `FOREIGN_RESTING=0` · 오탐 0 이었다.

    ## `reduce_only=None` 은 협상 불가다

    기본값 `True` 는 TP/SL 만 준다. 오염을 만드는 것은 reduce-only 가 **아닌**
    조건부 진입이므로, 그 기본값으로 물으면 표적을 통째로 놓친다.
    """

    def __init__(
        self,
        *,
        account_repo: ExchangeAccountRepository,
        order_repo: OrderRepository,
        account_service: ExchangeAccountService,
        bybit_futures_provider: BybitFuturesProvider,
    ) -> None:
        self._account_repo = account_repo
        self._order_repo = order_repo
        self._account_service = account_service
        self._bybit_futures_provider = bybit_futures_provider

    async def ensure_exclusive(self, account: ExchangeAccount, symbol: str) -> None:
        """`account` 의 실제 거래소 계정이 이 원장의 것뿐이 아니면 거부한다.

        ★이름을 `assert_*` 로 되돌리지 마라. `unittest.mock` 은 `assert` 로 시작하는
        속성 접근을 **오타 낸 단정**으로 보고 `AttributeError` 를 던진다(mock.py 의
        assertion-name 가드). 이 서비스를 `AsyncMock` 으로 세우는 호출부가 전부
        깨진다 — 실제로 그렇게 깨뜨려 보고 고친 이름이다.

        ★**fail-closed 다.** 거래소 조회가 실패하면 `ProviderError` 가 그대로 올라가
        세션이 안 열린다. 「확인 못 했으니 통과」는 이 가드의 존재 이유를 지운다 —
        이 프로젝트가 fail-open 으로 반복해 데인 자리다.
        """
        creds = await self._account_service.get_credentials_for_order(account.id)
        orders = await self._bybit_futures_provider.fetch_open_conditional_orders(
            creds, symbol, reduce_only=None
        )
        if not orders:
            return

        scope_ids = await self._ownership_scope(account)
        link_ids: set[UUID] = set()
        for order in orders:
            parsed = _as_uuid(order.order_link_id)
            if parsed is not None:
                link_ids.add(parsed)

        owned: set[UUID] = set()
        for account_id in scope_ids:
            owned |= set(await self._order_repo.list_existing_ids(account_id, link_ids))

        foreign: list[str] = []
        for order in orders:
            parsed = _as_uuid(order.order_link_id)
            # link 가 없거나 우리 id 형식이 아니면 **우리 것이 아니다**. 내부 `Order.id` 가
            # 그대로 `orderLinkId` 로 나간다는 규약이 이 대조의 근거다.
            if parsed is None or parsed not in owned:
                foreign.append(f"{order.order_id}:{order.order_link_id or '(link 없음)'}")

        if foreign:
            logger.warning(
                "account_not_exclusive",
                extra={
                    "account_id": str(account.id),
                    "symbol": symbol,
                    "resting_total": len(orders),
                    "foreign_total": len(foreign),
                },
            )
            raise AccountNotExclusive(account_id=account.id, symbol=symbol, foreign=foreign)

    async def _ownership_scope(self, account: ExchangeAccount) -> list[UUID]:
        """소유권 집합 `{Order.id}` 를 어느 **계정 축**으로 좁힐지 결정한다.

        ★결정 = **등재 대상 계정과 `exchange_uid` 를 공유하는 계정 행 전체**. 근거는
        양쪽 극단이 각각 다른 방식으로 틀리기 때문이다([BL-639] 실패 모드 3).

        ⑴ **스코프 없음**(`SELECT id FROM trading.orders` 전량)은 「우리 것」 집합을
           원장 크기만큼 키운다. 다른 실제 계정에 발행한 주문까지 이 계정의 소유로
           세므로, 가드의 거부율이 **이 계정의 상태가 아니라 원장의 크기**를 따라간다.
           같은 축 오류로 「미조인 34행 전량 ⇒ 판별력 0」을 만든 전례가 있다.
        ⑵ **행 하나로 좁힘**(`exchange_account_id == account.id`)은 반대로 너무 좁다.
           [BL-605] 가 증명했듯 같은 실제 계정이 **행 2개**로 존재한다. 우리가 행 A 로
           낸 주문을 행 B 로 등재하며 조회하면 **우리 것을 FOREIGN 으로** 판정해
           정상 재기동을 영구히 막는다(거짓 양성).
        ⇒ 두 실패 모드를 동시에 피하는 축은 uid 형제 집합 하나뿐이다. 그리고 이것이
          [BL-605]·[BL-651] 을 **먼저** 고친 이유다 — 축을 정하려면 행이 접혀 있어야 한다.

        `exchange_uid` 가 `None` 이면 형제를 알 수 없으므로 자기 행만 쓴다. 이때 축은
        ⑵ 로 퇴화하지만, 그것은 「모르는 것을 아는 척하지 않는다」의 결과다.
        """
        if account.exchange_uid is None:
            return [account.id]
        siblings = list(await self._account_repo.list_by_exchange_uid(account.exchange_uid))
        # dedupe 는 대표 1행만 남기므로 여기서는 쓰지 않는다 — 소유권은 **행 전량**을
        # 합집합해야 한다. 형제 행 각각이 자기 이름으로 주문을 낸 이력이 있기 때문이다.
        ids = [sibling.id for sibling in siblings]
        if account.id not in ids:
            ids.append(account.id)
        return ids


def _as_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


__all__ = ["AccountExclusivityService"]
