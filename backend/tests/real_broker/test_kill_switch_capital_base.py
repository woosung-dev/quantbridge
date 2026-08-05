# Kill Switch 의 capital_base 조달 경로를 **프로덕션 provider 로** 실거래소에 대고 잰다.
"""[BL-004]/ADR-006 — `capital_base` 실잔고 조달의 Bybit Demo 검증.

ADR-006 결의(`capital_base` fetch timing = Option A, trigger 시 매번)의 실측 근거.
조회만 한다 — 주문 0건, 자본 변동 0.

**Guarded:** `@pytest.mark.real_broker` + Bybit Demo credentials. 기본 skip.
실행: `pytest --run-real-broker tests/real_broker/test_kill_switch_capital_base.py`

## ★2026-08-04 [BL-024] — 무엇이 바뀌었나

이 파일의 이전 판은 `ccxt_async.bybit(...)` 를 직접 만들고 **`set_sandbox_mode(True)`**
를 불렀다. 그것은 **testnet**(`api-testnet.bybit.com`) 이다. 프로덕션 코드가 쓰는 것은
`providers.py:2202-2210 _apply_bybit_env` 를 경유한 **`enable_demo_trading(True)`**
(`api-demo.bybit.com`) 이고, 둘은 **별개 플랫폼이며 키 네임스페이스도 다르다**.
⇒ "유일한 실거래소 커버리지가 프로덕션이 안 쓰는 엔드포인트를 겨냥" 하고 있었다.

이제 `BybitFuturesProvider.fetch_balance(Credentials(..., environment=demo))` 를 부른다.
`_apply_bybit_env` 를 **경유**하므로 프로덕션과 같은 엔드포인트다. `src` 수정 0줄.

또한 이전 판의 `test_kill_switch_evaluator_with_real_balance_provider` 는 이름과 달리
`CumulativeLossEvaluator` 를 **만들지 않고** 로컬 duck-type 으로 지연시간만 쟀다 —
바로 위 테스트와 같은 것을 재는 동어반복이라 **삭제**했다. 평가자 결합 시나리오는
`tests/trading/test_kill_switch_evaluators.py` 가 커버한다.
"""

from __future__ import annotations

import time
from decimal import Decimal

import pytest

# pytestmark: 모든 테스트에 real_broker marker. --run-real-broker 없으면 skip.
pytestmark = pytest.mark.real_broker


@pytest.mark.asyncio
async def test_bybit_demo_fetch_balance_returns_usdt(
    bybit_demo_test_credentials: tuple[str, str],
) -> None:
    """프로덕션 provider 로 Bybit **demo** 잔고를 읽고 USDT 를 Decimal 로 얻는다.

    ADR-006 Option A 의 근거 — `capital_base` 를 trigger 시점마다 조달할 수 있는가.
    latency 도 함께 잰다(결의문의 "+200ms 수용" 이 여기에 근거한다).
    """
    from src.trading.models import ExchangeMode
    from src.trading.providers import BybitFuturesProvider, Credentials

    api_key, api_secret = bybit_demo_test_credentials
    creds = Credentials(
        api_key=api_key,
        api_secret=api_secret,
        environment=ExchangeMode.demo,  # ★_apply_bybit_env → enable_demo_trading(True)
    )

    started = time.monotonic()
    balances = await BybitFuturesProvider().fetch_balance(creds)
    elapsed_ms = (time.monotonic() - started) * 1000

    assert isinstance(balances, dict), "fetch_balance 가 dict 를 반환하지 않았다"
    assert "USDT" in balances, f"USDT 키 부재: {sorted(balances)[:5]}"

    usdt = balances["USDT"]
    assert isinstance(usdt, Decimal), f"USDT 잔고가 Decimal 이 아니다: {type(usdt)}"
    assert usdt >= Decimal("0"), f"USDT free 가 음수다: {usdt}"

    # ADR-006 base evidence. 통상 100-500ms — 5s 를 넘으면 Option A 전제가 흔들린다.
    assert elapsed_ms < 5000, f"fetch_balance latency 5s 초과: {elapsed_ms:.0f}ms"
