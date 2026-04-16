"""trading HTTP 라우터 — ExchangeAccount endpoints (T18).

URL prefix 없음 — main.py에서 /api/v1로 include.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Path

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.trading.dependencies import get_exchange_account_service
from src.trading.schemas import (
    ExchangeAccountResponse,
    PaginatedExchangeAccounts,
    RegisterAccountRequest,
    mask_api_key,
)
from src.trading.service import ExchangeAccountService

router = APIRouter(tags=["trading"])


@router.post(
    "/exchange-accounts",
    status_code=201,
    response_model=ExchangeAccountResponse,
)
async def register_exchange_account(
    body: RegisterAccountRequest,
    current_user: CurrentUser = Depends(get_current_user),
    svc: ExchangeAccountService = Depends(get_exchange_account_service),
) -> ExchangeAccountResponse:
    account = await svc.register(user_id=current_user.id, req=body)
    await svc._repo.commit()
    # Decrypt api_key for masking (plain text never stored, only encrypted)
    plaintext_key = svc._crypto.decrypt(account.api_key_encrypted)
    return ExchangeAccountResponse(
        id=account.id,
        exchange=account.exchange,
        mode=account.mode,
        label=account.label,
        api_key_masked=mask_api_key(plaintext_key),
        created_at=account.created_at,
    )


@router.get(
    "/exchange-accounts",
    response_model=PaginatedExchangeAccounts,
)
async def list_exchange_accounts(
    current_user: CurrentUser = Depends(get_current_user),
    svc: ExchangeAccountService = Depends(get_exchange_account_service),
) -> PaginatedExchangeAccounts:
    accounts = await svc._repo.list_by_user(current_user.id)
    items: list[ExchangeAccountResponse] = []
    for acct in accounts:
        plaintext_key = svc._crypto.decrypt(acct.api_key_encrypted)
        items.append(
            ExchangeAccountResponse(
                id=acct.id,
                exchange=acct.exchange,
                mode=acct.mode,
                label=acct.label,
                api_key_masked=mask_api_key(plaintext_key),
                created_at=acct.created_at,
            )
        )
    return PaginatedExchangeAccounts(items=items, total=len(items))


@router.delete(
    "/exchange-accounts/{account_id}",
    status_code=204,
)
async def delete_exchange_account(
    account_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    svc: ExchangeAccountService = Depends(get_exchange_account_service),
) -> None:
    # Ownership check: only delete if the account belongs to the current user
    account = await svc._repo.get_by_id(account_id)
    if account is None or account.user_id != current_user.id:
        from src.trading.exceptions import AccountNotFound

        raise AccountNotFound(account_id)
    await svc._repo.delete(account_id)
    await svc._repo.commit()
