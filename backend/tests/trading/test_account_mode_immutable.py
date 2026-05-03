"""Sprint 22 BL-091 P1 #5 audit — ExchangeAccount.mode mutation endpoint 부재.

codex G.0 P1 #5: dispatch 가 (account.exchange, account.mode, has_leverage)
3-tuple 기반이므로 ExchangeAccount.mode 가 in-flight Celery task 도중 변경되면
주문 의도와 다른 provider 로 라우팅 가능. 본 audit 는 router 에 mode 변경
endpoint 가 부재함을 회귀 가드로 검증.

PUT/PATCH 추가 시 본 test fail → 신규 BL 등록 (Order 에 mode snapshot 저장).
"""
from __future__ import annotations


def test_no_exchange_account_mutation_endpoint() -> None:
    """ExchangeAccount /exchange-accounts route 에 PUT/PATCH 부재 회귀 가드.

    Sprint 22 시점 router (`backend/src/trading/router.py:127-192`):
    - POST /exchange-accounts (register)
    - GET /exchange-accounts (list)
    - DELETE /exchange-accounts/{id} (remove)

    PUT/PATCH 추가 시 본 test fail → 신규 BL (Order 에 (exchange, mode) snapshot
    저장) 등록 강제. Order 행이 dispatch 시점의 ExchangeAccount 상태를 캡쳐해야
    race-free.

    codex G.2 P2 #1 fix (Sprint 22): substring `/accounts` 만 검사하면 cousin
    module 의 `/admin-accounts` 같은 라우트도 잘못 catch. 명확한 prefix
    `/exchange-accounts` 매칭으로 좁힘.
    """
    from src.trading.router import router

    forbidden_methods = {"PUT", "PATCH"}
    found_violations: list[str] = []

    for route in router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None or methods is None:
            continue
        # 정확한 prefix `/exchange-accounts` 매칭 (path == "/exchange-accounts"
        # 또는 path == "/exchange-accounts/{...}")
        if path == "/exchange-accounts" or path.startswith("/exchange-accounts/"):
            offending = methods.intersection(forbidden_methods)
            if offending:
                found_violations.append(f"{path}: {offending}")

    assert found_violations == [], (
        "Sprint 22 BL-091 가정 위반 — ExchangeAccount mutation endpoint 추가됨: "
        f"{found_violations}. dispatch 가 account 상태 기반이므로 in-flight order "
        "race 회피 위해 Order 에 (exchange, mode) snapshot 저장 BL 신규 등록 필요."
    )
