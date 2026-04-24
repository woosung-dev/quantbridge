"""Sprint 10 Phase C — TV webhook → Bybit Demo create_order → filled E2E.

1 시나리오:
1. Bybit Demo Spot BTC/USDT 최소 수량 market BUY 주문
2. TV webhook payload (HMAC 서명 포함) TestClient POST
3. Celery task 가 execute_order → Bybit Demo create_order
4. 5~10s polling 으로 OrderState.filled 확인
5. cleanup: position close + residual cancel (best-effort)

**Nightly only.** 기본 skip. `pytest --run-real-broker` 로만 실행.

**Credentials:** `BYBIT_DEMO_API_KEY_TEST` + `BYBIT_DEMO_API_SECRET_TEST`.

**Rate limit:** Bybit Demo 의 rate limit 은 request/min 수준. 본 테스트는 1일 1회
(nightly) + 수동 trigger 만. flaky 방지로 retry 없음 (실패 시 issue 생성).

**본 파일은 Phase C infra skeleton.** 실제 E2E 로직은 nightly CI 첫 실행 시
credentials + seed data 하에 작성.
"""

from __future__ import annotations

import time
from decimal import Decimal
from uuid import uuid4

import pytest

# pytestmark: 모든 테스트에 real_broker marker 적용
# conftest.py 의 pytest_collection_modifyitems 가 --run-real-broker 없으면 skip.
pytestmark = pytest.mark.real_broker


# Bybit Demo Spot 최소 주문 파라미터
_BTCUSDT_TEST_SYMBOL = "BTC/USDT"
_TEST_QTY = Decimal("0.001")  # Bybit Spot 최소 0.001 BTC


@pytest.fixture
def tv_webhook_payload() -> dict[str, object]:
    """TradingView webhook 표준 payload (HMAC 서명 전).

    실제 E2E 시 strategy_id 는 테스트 DB 에 존재하는 Strategy.id 를 주입해야.
    현재는 skeleton — pytest.skip 으로 종료되므로 실제 실행 경로 없음.
    """
    return {
        "strategy_id": str(uuid4()),  # CI 용 임시 id — 실제 DB 에 존재해야
        "side": "buy",
        "symbol": _BTCUSDT_TEST_SYMBOL,
        "qty": str(_TEST_QTY),
        "alert_time": int(time.time()),
        "price": None,  # market order
    }


@pytest.mark.asyncio
async def test_tv_webhook_to_bybit_demo_filled(
    bybit_demo_test_credentials: tuple[str, str],
    tv_webhook_payload: dict[str, object],
) -> None:
    """E2E: TV webhook → Celery task → Bybit Demo create_order → filled.

    **Guarded:** `@pytest.mark.real_broker` + credentials fixture. local dev 환경에서
    `pytest --run-real-broker` 실행 + env 세팅 필요.

    **Setup (한 번 수동):**
    1. Bybit Demo 계정에 seed USDT ≥ $10 (0.001 BTC @ $50k = $50).
    2. GitHub Secrets 에 BYBIT_DEMO_API_KEY_TEST / BYBIT_DEMO_API_SECRET_TEST 등록.
    3. `nightly-real-broker.yml` workflow 가 Secrets 주입 + pytest --run-real-broker.

    **본 테스트는 구현 skeleton.** 실제 TestClient + Celery worker fixture 결합은
    pytest-celery 의 `celery_worker` + `celery_app` fixture 로 세팅.

    Implementation TODO (nightly 첫 실행 시 작성):
    - `celery_app` fixture — src.tasks.celery_app:celery_app 사용
    - `celery_worker` fixture — pytest-celery in-process spawn
    - FastAPI TestClient — src.main:app
    - strategy_id seed — pytest fixture 로 테스트 user + strategy + exchange_account 생성
    - Bybit Demo credentials 를 ExchangeAccount.api_key_encrypted 로 Fernet 암호화 저장
    - webhook secret HMAC 서명 (WebhookSecret 테이블 참조)
    - polling — order_repo.get_by_id + state 확인 (5s interval × 10 iter)
    - cleanup — Bybit Demo 에서 포지션 close + residual cancel
    """
    # credentials fixture 가 정상 통과하면 (env 존재) 여기까지 도달
    _api_key, _api_secret = bybit_demo_test_credentials

    # TODO: 실제 E2E 구현 — Phase C 는 infra skeleton 만.
    # nightly CI 첫 실행 시 credentials + seed data 하에 implementer 가 작성.
    pytest.skip("Phase C skeleton — full E2E implementation deferred to nightly first-run")
