# MP-4 데모 검증 — 실제 Bybit demo 거래소의 instrument precision 으로 amount/price 변환을 확인하는 일회성 스크립트
"""MP-4 (Decimal→float CCXT 경계) 데모 검증 스크립트.

mock 테스트는 거래소가 precision 문자열을 실제로 수락하는지 검증할 수 없다(false
confidence). 본 스크립트는 **Bybit demo(api-demo.bybit.com)** 의 실제 instrument
precision 으로 변환을 확인한다.

- 기본(read-only): load_markets() 후 샘플 수량/가격에 대해 (구) float() vs (신)
  amount_to_precision/price_to_precision 결과를 비교 출력. 주문 발주 없음.
- `--place-and-cancel`: 시장에서 멀리 떨어진 limit 주문 1건을 실제 발주(체결 안 됨)
  → 거래소 수락 확인 → 즉시 취소. 실 주문 side-effect 가 있으므로 opt-in.

시크릿 하드코딩 금지 — 환경변수로 주입:
    BYBIT_DEMO_API_KEY=... BYBIT_DEMO_API_SECRET=... \
      uv run python scripts/archive/verify_mp4_precision_demo.py [--symbol BTC/USDT] [--place-and-cancel]
"""

from __future__ import annotations

import argparse
import asyncio
import os
from decimal import Decimal

import ccxt.async_support as ccxt_async

from src.trading.models import ExchangeMode, OrderSide, OrderType
from src.trading.providers import BybitDemoProvider, Credentials, OrderSubmit


async def _run(symbol: str, place: bool) -> None:
    api_key = os.environ.get("BYBIT_DEMO_API_KEY")
    api_secret = os.environ.get("BYBIT_DEMO_API_SECRET")
    if not api_key or not api_secret:
        raise SystemExit(
            "BYBIT_DEMO_API_KEY / BYBIT_DEMO_API_SECRET 환경변수가 필요합니다 (하드코딩 금지)."
        )

    # 정밀도보다 더 세밀한 입력 — float() 경유 시 손실, precision 경유 시 거래소 step 으로 반올림.
    qty = Decimal("0.00123456789")
    price = Decimal("12345.6789012")

    exchange = ccxt_async.bybit(
        {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot", "testnet": False},
        }
    )
    exchange.enable_demo_trading(True)
    try:
        await exchange.load_markets()
        market = exchange.market(symbol)
        amount_prec = exchange.amount_to_precision(symbol, qty)
        price_prec = exchange.price_to_precision(symbol, price)

        print(f"\n[{symbol}] market precision = {market['precision']}")
        print(f"  quantity Decimal      : {qty}")
        print(f"  (구) float(quantity)   : {float(qty)!r}  ← 정밀도 손실 경로")
        print(f"  (신) amount_to_precision: {amount_prec!r}  (type={type(amount_prec).__name__})")
        print(f"  price Decimal         : {price}")
        print(f"  (구) float(price)      : {float(price)!r}")
        print(f"  (신) price_to_precision : {price_prec!r}")
        assert isinstance(amount_prec, str) and isinstance(price_prec, str)
        print("\n✅ precision 변환이 거래소 spec 기반 문자열을 산출합니다 (float 미경유).")

        if place:
            # 시장에서 충분히 낮은 limit BUY → 미체결 resting → 거래소 수락 여부만 확인.
            ticker = await exchange.fetch_ticker(symbol)
            last = Decimal(str(ticker["last"]))
            far_price = (last * Decimal("0.5")).quantize(Decimal("1"))
            order = OrderSubmit(
                symbol=symbol,
                side=OrderSide.buy,
                type=OrderType.limit,
                quantity=qty,
                price=far_price,
            )
            provider = BybitDemoProvider()
            creds = Credentials(
                api_key=api_key, api_secret=api_secret, environment=ExchangeMode.demo
            )
            print(
                f"\n[place-and-cancel] limit BUY qty={qty} price={far_price} (시장가 {last} 대비 -50%)"
            )
            receipt = await provider.create_order(creds, order)
            print(f"  → 거래소 수락: order_id={receipt.exchange_order_id} status={receipt.status}")
            await provider.cancel_order(creds, receipt.exchange_order_id)
            print("  → 즉시 취소 완료. ✅ 실거래소가 precision 문자열 주문을 수락했습니다.")
    finally:
        await exchange.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="MP-4 Bybit demo precision 검증")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument(
        "--place-and-cancel",
        action="store_true",
        help="실제 demo 주문 1건 발주 후 즉시 취소 (end-to-end 확인, side-effect 있음)",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.symbol, args.place_and_cancel))


if __name__ == "__main__":
    main()
