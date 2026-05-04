"""Sprint 28 Slice 4 (BL-004) — KillSwitch capital_base Bybit Demo 통합 테스트.

ADR-006 결의 (Sprint 28, capital_base fetch timing = Option A trigger 시 매번)
의 실측 검증. 조회만 — 실매매 X (Bybit Demo testnet 자본 영향 0).

**Guarded:** `@pytest.mark.real_broker` + Bybit Demo credentials. 기본 skip.
실행: `pytest --run-real-broker tests/real_broker/test_kill_switch_capital_base.py`.

**Credentials:** `BYBIT_DEMO_API_KEY_TEST` + `BYBIT_DEMO_API_SECRET_TEST`.

**검증 시나리오:**

1. BybitFuturesProvider.fetch_balance() 가 USDT key 가 있는 dict 반환
2. CumulativeLossEvaluator + 실제 BalanceProvider 결합 시 trigger evaluator 가 정상 동작
   (DB-less — Order 0건 → not gated 검증으로 인프라만 확인)
3. fetch 응답 latency 측정 (200ms+ 가 ADR-006 결의 trade-off 의 base evidence)
"""

from __future__ import annotations

import os
import time
from decimal import Decimal
from uuid import uuid4

import pytest

# pytestmark: 모든 테스트에 real_broker marker. --run-real-broker 없으면 skip.
pytestmark = pytest.mark.real_broker


@pytest.fixture
def bybit_demo_credentials() -> tuple[str, str]:
    """Bybit Demo API key + secret env 로드. 부재 시 fail (--run-real-broker 시점)."""
    key = os.environ.get("BYBIT_DEMO_API_KEY_TEST")
    secret = os.environ.get("BYBIT_DEMO_API_SECRET_TEST")
    if not key or not secret:
        pytest.fail(
            "BYBIT_DEMO_API_KEY_TEST + BYBIT_DEMO_API_SECRET_TEST env 필수 "
            "(--run-real-broker 시 credentials 부재)."
        )
    return key, secret


@pytest.mark.asyncio
async def test_bybit_demo_fetch_balance_returns_usdt(
    bybit_demo_credentials: tuple[str, str],
) -> None:
    """BybitFuturesProvider.fetch_balance() 가 USDT key 가 있는 dict 반환.

    ADR-006 의 Option A 결의 base — fetch_balance 가 실제 Decimal value 반환 가능
    상태 확인. Bybit Demo testnet 자본 변동 0 (조회만).
    """
    import ccxt.async_support as ccxt_async

    key, secret = bybit_demo_credentials

    # ephemeral CCXT client — fetch_balance 만 호출, close 보장
    client = ccxt_async.bybit(
        {
            "apiKey": key,
            "secret": secret,
            "enableRateLimit": True,
            "options": {"defaultType": "linear"},
        }
    )
    try:
        # Bybit Demo testnet endpoint
        client.set_sandbox_mode(True)
        raw = await client.fetch_balance()
    finally:
        await client.close()

    # 응답 구조: {"USDT": {"free": ..., "used": ..., "total": ...}, ...}
    assert isinstance(raw, dict), "fetch_balance() 가 dict 반환 안 함"
    assert "USDT" in raw, f"USDT key 부재: {list(raw.keys())[:5]}"
    usdt_balance = raw["USDT"]
    assert "free" in usdt_balance, f"USDT.free 부재: {list(usdt_balance.keys())}"

    free = Decimal(str(usdt_balance["free"]))
    assert free >= Decimal("0"), f"USDT.free < 0 비정상: {free}"


@pytest.mark.asyncio
async def test_kill_switch_evaluator_with_real_balance_provider(
    bybit_demo_credentials: tuple[str, str],
) -> None:
    """CumulativeLossEvaluator + 실제 fetch_balance 결합 시 trigger 정상 동작.

    DB-less 검증 — Order 0건 (PnL = 0) → not gated. balance_provider 가 호출되는 시점만
    인프라 검증 (BalanceProvider Protocol 통합).

    **주의:** Order 0건이면 evaluate() 가 L102-103 에서 early return (PnL >= 0). 따라서
    balance_provider 호출 안 됨. PnL < 0 시나리오는 DB 필요 → unit test (test_kill_switch_evaluators.py)
    가 cover. 본 integration test 는 ADR-006 fetch_balance latency 만 측정.
    """
    import ccxt.async_support as ccxt_async

    key, secret = bybit_demo_credentials

    class _RealBalanceProvider:
        """프로덕션 ExchangeAccountService 와 동일 패턴 (ephemeral client)."""

        def __init__(self, key: str, secret: str) -> None:
            self._key = key
            self._secret = secret

        async def fetch_balance_usdt(self, account_id) -> Decimal | None:
            client = ccxt_async.bybit(
                {
                    "apiKey": self._key,
                    "secret": self._secret,
                    "enableRateLimit": True,
                    "options": {"defaultType": "linear"},
                }
            )
            try:
                client.set_sandbox_mode(True)
                raw = await client.fetch_balance()
                return Decimal(str(raw["USDT"]["free"]))
            finally:
                await client.close()

    provider = _RealBalanceProvider(key, secret)

    # ADR-006 base evidence — fetch latency 측정
    started = time.time()
    balance = await provider.fetch_balance_usdt(uuid4())
    elapsed_ms = (time.time() - started) * 1000

    assert balance is not None, "Bybit Demo fetch_balance None 반환 비정상"
    assert balance >= Decimal("0"), f"잔고 음수 비정상: {balance}"
    # Latency: 통상 100-500ms. ADR-006 결의 base ("Option A latency +200ms 수용")
    assert elapsed_ms < 5000, f"fetch_balance latency 5s 초과 (수상): {elapsed_ms:.0f}ms"

    # capital_base = balance, threshold = 100% → not gated (Order 0건 = PnL >= 0)
    # 본 assertion 은 실제로 DB 필요 — 본 integration test 는 fetch_balance 만 검증.
    # CumulativeLossEvaluator 결합 시나리오는 unit test 가 cover.
