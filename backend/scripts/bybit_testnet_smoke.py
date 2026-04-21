"""Bybit Testnet Smoke Test — mainnet dogfood 전환 전 전체 경로 검증.

실행 예:
    cd backend
    uv run python scripts/bybit_testnet_smoke.py \\
        --api-key "$BYBIT_TESTNET_KEY" \\
        --api-secret "$BYBIT_TESTNET_SECRET" \\
        --symbol "BTC/USDT:USDT" \\
        --quantity 0.001 \\
        --leverage 1

검증 경로:
    1. fetch_balance → USDT > 0 확인
    2. set_margin_mode (cross) 성공
    3. set_leverage 성공
    4. create_order (limit, best_bid - 1%) → exchange_order_id 수신
    5. cancel_order 정상 종료

모든 단계 JSON으로 로깅. 실패 시 exit code 1.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import ccxt.async_support as ccxt_async

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("bybit_smoke")


def log_event(event: str, **fields: Any) -> None:
    """structured JSON 로그 (관측성 계획과 동일 포맷)."""
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": event,
        **fields,
    }
    print(json.dumps(record, default=str))


async def run_smoke(
    *,
    api_key: str,
    api_secret: str,
    symbol: str,
    quantity: Decimal,
    leverage: int,
    mode: str = "testnet",
) -> int:
    """Return exit code (0=success, 1=failure)."""
    exchange = ccxt_async.bybit(
        {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "timeout": 30000,
            "options": {"defaultType": "linear", "testnet": mode == "testnet"},
        }
    )
    if mode == "demo":
        log_event("smoke_config", endpoint="api-demo.bybit.com")
        api_urls = exchange.urls.get("api", {})
        if isinstance(api_urls, dict):
            exchange.urls["api"] = dict.fromkeys(api_urls, "https://api-demo.bybit.com")
        else:
            exchange.urls["api"] = "https://api-demo.bybit.com"
    else:
        log_event("smoke_config", endpoint="api-testnet.bybit.com")

    try:
        # 1. Balance
        log_event("smoke_step_start", step="fetch_balance")
        balance = await exchange.fetch_balance()
        usdt_free = Decimal(str(balance.get("USDT", {}).get("free", "0")))
        log_event(
            "smoke_step_ok",
            step="fetch_balance",
            usdt_free=str(usdt_free),
        )
        if usdt_free <= Decimal("0"):
            log_event("smoke_fail", reason="zero_usdt_balance")
            return 1

        # 2. Margin mode
        log_event("smoke_step_start", step="set_margin_mode")
        await exchange.set_margin_mode("cross", symbol)
        log_event("smoke_step_ok", step="set_margin_mode", mode="cross")

        # 3. Leverage
        log_event("smoke_step_start", step="set_leverage")
        await exchange.set_leverage(leverage, symbol)
        log_event("smoke_step_ok", step="set_leverage", leverage=leverage)

        # 4. Order price — best_bid - 1% (즉시 체결 방지)
        log_event("smoke_step_start", step="fetch_ticker")
        ticker = await exchange.fetch_ticker(symbol)
        best_bid = Decimal(str(ticker.get("bid", 0)))
        if best_bid <= Decimal("0"):
            log_event("smoke_fail", reason="no_best_bid", ticker=ticker)
            return 1
        order_price = (best_bid * Decimal("0.99")).quantize(Decimal("0.01"))
        log_event(
            "smoke_step_ok",
            step="fetch_ticker",
            best_bid=str(best_bid),
            order_price=str(order_price),
        )

        # 5. Create order (limit, below bid)
        log_event("smoke_step_start", step="create_order")
        order = await exchange.create_order(
            symbol,
            "limit",
            "buy",
            float(quantity),
            float(order_price),
        )
        order_id = str(order.get("id", ""))
        if not order_id:
            log_event("smoke_fail", reason="missing_order_id", response=order)
            return 1
        log_event(
            "smoke_step_ok",
            step="create_order",
            exchange_order_id=order_id,
            status=order.get("status"),
        )

        # 6. Cancel order
        log_event("smoke_step_start", step="cancel_order", order_id=order_id)
        await exchange.cancel_order(order_id, symbol)
        log_event("smoke_step_ok", step="cancel_order", order_id=order_id)

        log_event(
            "smoke_success",
            symbol=symbol,
            quantity=str(quantity),
            leverage=leverage,
            usdt_free=str(usdt_free),
        )
        return 0

    except ccxt_async.BaseError as exc:
        log_event(
            "smoke_fail",
            reason="ccxt_error",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return 1
    except Exception as exc:
        # SECURITY: non-CCXT 예외 메시지는 apiKey 노출 가능. 타입만 기록.
        log_event(
            "smoke_fail",
            reason="unexpected_error",
            error_type=type(exc).__name__,
        )
        return 1
    finally:
        try:
            await exchange.close()
        except Exception:
            logger.warning("exchange_close_failed", exc_info=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bybit testnet smoke test — mainnet 전환 전 전체 경로 검증"
    )
    parser.add_argument("--api-key", required=True, help="Bybit testnet API key")
    parser.add_argument("--api-secret", required=True, help="Bybit testnet API secret")
    parser.add_argument(
        "--symbol",
        default="BTC/USDT:USDT",
        help="Linear perp symbol (default: BTC/USDT:USDT)",
    )
    parser.add_argument(
        "--quantity",
        type=Decimal,
        default=Decimal("0.001"),
        help="Order quantity in base asset (default: 0.001)",
    )
    parser.add_argument(
        "--leverage",
        type=int,
        default=1,
        help="Leverage 1~20 (default: 1)",
    )
    parser.add_argument(
        "--mode",
        choices=["testnet", "demo"],
        default="testnet",
        help="bybit 환경: testnet(api-testnet.bybit.com) 또는 demo(api-demo.bybit.com)",
    )
    args = parser.parse_args()

    if args.leverage < 1 or args.leverage > 20:
        print("leverage must be 1~20 for smoke test", file=sys.stderr)
        return 2

    return asyncio.run(
        run_smoke(
            api_key=args.api_key,
            api_secret=args.api_secret,
            symbol=args.symbol,
            quantity=args.quantity,
            leverage=args.leverage,
            mode=args.mode,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
