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

    **본 테스트는 구현 skeleton.** 실주문 leg 은 전용 Bybit demo 키(`BYBIT_DEMO_API_KEY_TEST`
    / `BYBIT_DEMO_API_SECRET_TEST`)가 발급된 뒤에 작성한다 — 지금은 repo secret 에도
    `backend/.env.local` 에도 없다.

    Implementation TODO (자격증명 도착 후):
    - strategy_id seed — 테스트 user + strategy + exchange_account(demo) 생성
    - Bybit Demo credentials 를 ExchangeAccount.api_key_encrypted 로 Fernet 암호화 저장
    - ★**진입 주문을 내기 전에** `broker_flat_guard(account_id=…, symbol=…,
      live_session_id=…)` 로 등록해라. 등록이 주문보다 늦으면 그 사이에 죽은 세션은
      아무도 청산하지 않는다 (`tests/real_broker/_harness.py`).
    - ★`ClosePositionService` 가 `LiveSignalSession` 을 요구하므로 **진입 전에 세션을
      등재**한다. 덤으로 `live_session_service.py:109-113` 의 demo 강제 게이트를 얻는다.
    - webhook secret HMAC 서명 (WebhookSecret 테이블 참조)
    - ★**체결 확인을 polling 으로 짜지 마라 — 영원히 red 인 테스트가 된다.**
      Bybit demo 시장가는 `create_order` 응답에서 **`submitted`** 로 온다
      (`providers.py:2213-2225` `_map_ccxt_status`). 체결 확정은 WS 가 나중에 한다.
      그런데 `conftest.py` 의 autouse `_no_op_enqueue` 가 celery enqueue 를 전부 막으므로
      (로컬 워커가 앱 DB 를 보며 우리 태스크를 집어가는 것을 막는 안전장치다)
      **`_async_fetch_order_status`(`tasks/trading.py:685-707`)를 명시적으로 태우는**
      설계여야 한다.
    """
    # credentials fixture 가 정상 통과하면 (env 존재) 여기까지 도달
    _api_key, _api_secret = bybit_demo_test_credentials

    # TODO: 실제 E2E 구현 — Phase C 는 infra skeleton 만.
    # nightly CI 첫 실행 시 credentials + seed data 하에 implementer 가 작성.
    pytest.skip("Phase C skeleton — full E2E implementation deferred to nightly first-run")
