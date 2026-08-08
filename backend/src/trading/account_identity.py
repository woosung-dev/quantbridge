# 거래소 계정 **행**과 **실제 거래소 계정**을 구분하는 단독 책임 (BL-605 / BL-651)

from __future__ import annotations

from typing import Protocol, TypeVar

__all__ = ["dedupe_accounts_by_exchange_uid"]


class _AccountLike(Protocol):
    """`exchange_uid` 로 실제 계정을 식별할 수 있는 최소 형태."""

    @property
    def exchange_uid(self) -> str | None: ...

    @property
    def read_only(self) -> bool | None: ...


_A = TypeVar("_A", bound=_AccountLike)


def dedupe_accounts_by_exchange_uid(accounts: list[_A]) -> list[_A]:
    """같은 실제 거래소 계정을 가리키는 행들 중 **대표 1행**만 남긴다.

    ## 왜 필요한가

    `trading.exchange_accounts` 는 **행**의 집합이고, 거래소는 `exchange_uid` 단위로
    **하나의 계정**이다. 두 축은 1:1 이 아니다 — 실측(2026-08-08)으로 `exchange_uid`
    **558689281** 을 공유하는 행이 2개 있다(`19a8166a` `bybit demo` · `0277c150`
    `bybit demo- aaa` `read_only=t` — [BL-517]). 계정 **행**마다 거래소를 조회하는
    루프는 같은 것을 두 번 세고, 그 배수는 「행 수」이지 실체가 아니다.

    실측 피해 2건:

    - [BL-605] 청산 원장 스윕 — `exchange_exits` 574행 = 287 event x **정확히 2**.
      `row_hash` 입력 8개가 전부 거래소 원본이라 두 행의 해시는 같은데, UNIQUE 축이
      `(exchange_account_id, row_hash)` 라 충돌하지 않고 둘 다 들어간다.
    - [BL-651] 배타성 판정 — `RESTING_CONDITIONAL=2` 인데 실제 미체결 조건부 주문은
      **1건**이었다(같은 `link` 가 두 계정으로 계상). 존재 판정(`EXCLUSIVE`)은 배수에
      불변이지만 **개수를 문턱으로 쓰는 순간** 틀린다.

    ## 대표 행 선택 규칙

    ⑴ `exchange_uid` 가 `None` 인 행은 **실체를 모른다** — 서로 묶지 않고 전부 남긴다.
       미상인 것들을 한 덩어리로 접으면 서로 다른 실제 계정이 조용히 사라진다.
    ⑵ 같은 `uid` 안에서는 `read_only` 가 아닌 행을 우선한다. `read_only` 행은 주문을
       낼 수 없으므로 그 계정의 원장·소유권을 대표할 수 없다(그 행을 대표로 뽑으면
       스윕 결과가 전량 `unknown` 이 된다).
    ⑶ 그 외에는 **입력 순서**를 따른다. 호출부의 `list_by_exchange` ·
       `list_by_exchange_uid` 가 모두 `created_at asc` 라 「먼저 등록된 행」이 대표다.

    출력 순서는 각 uid 가 **처음 등장한 자리**를 지킨다 — 대표가 뒤 행으로 교체돼도
    자리는 앞에 남으므로 호출부의 순서 가정이 흔들리지 않는다.
    """
    chosen_index: dict[str, int] = {}
    result: list[_A] = []
    for account in accounts:
        uid = account.exchange_uid
        if uid is None:
            result.append(account)
            continue
        index = chosen_index.get(uid)
        if index is None:
            chosen_index[uid] = len(result)
            result.append(account)
            continue
        if result[index].read_only is True and account.read_only is not True:
            result[index] = account
    return result
