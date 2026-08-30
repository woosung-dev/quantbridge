"""Bybit Demo smoke test — 데모 주문 경로 검증.

★**직접 부르지 마라 — `tools/scripts/bybit-smoke.sh` 가 정문이다.** 그 셸이
`--dry-run` 기본과 시크릿 파일 권한 검사를 제공한다. 이 모듈은 Bybit Demo endpoint만
선택하며 mainnet을 선택하는 인자나 fallback이 없다.

실행 예 (셸을 거치는 정문):
    tools/scripts/bybit-smoke.sh --dry-run
    tools/scripts/bybit-smoke.sh --confirm

검증 경로 (`--market linear`):
    1. fetch_balance → USDT > 0 확인
    2. set_margin_mode (cross) 성공
    3. set_leverage 성공
    4. fetch_ticker → best_bid
    5. create_order (limit, best_bid - 1%) → exchange_order_id 수신
    6. cancel_order 정상 종료

`--market spot` 은 2·3(마진/레버리지)을 건너뛴다 — spot 계정에 없는 개념이라 거래소가 거부한다.
★perp 최소 주문은 spot보다 클 수 있으므로 기본 smoke는 호출자가 market/symbol/quantity를
명시적으로 조정할 수 있게 둔다. 어느 경우에도 Bybit Demo만 사용한다.

모든 단계 JSON으로 로깅. 실패 시 exit code 1.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
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
    market: str = "linear",
) -> int:
    """Return exit code (0=success, 1=failure)."""
    exchange = ccxt_async.bybit(
        {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "timeout": 30000,
            "options": {"defaultType": market, "testnet": False},
        }
    )
    # enable_demo_trading(True) = URL 교체 + enableDemoTrading 플래그 세팅.
    # URL만 바꾸면 retCode:10032 (/v5/user/query-api 미지원 엔드포인트 호출).
    exchange.enable_demo_trading(True)
    log_event("smoke_config", endpoint="api-demo.bybit.com", mode="demo", market=market)

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

        # 2·3. Margin mode / leverage — spot 계정에는 없는 개념이라 거래소가 거부한다.
        if market == "spot":
            log_event("smoke_step_skip", step="set_margin_mode", reason="spot_market")
            log_event("smoke_step_skip", step="set_leverage", reason="spot_market")
        else:
            log_event("smoke_step_start", step="set_margin_mode")
            await exchange.set_margin_mode("cross", symbol)
            log_event("smoke_step_ok", step="set_margin_mode", mode="cross")

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
            mode="demo",
            market=market,
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
        description="Bybit smoke test — 주문 경로 검증 (정문은 tools/scripts/bybit-smoke.sh)"
    )
    # ★credentials 는 **env 가 정문**이다 — argv 로 넘기면 같은 호스트의 아무 프로세스나
    # `ps` 로 평문 키를 읽는다.
    # `--api-key`/`--api-secret` 은 로컬 임시 검증용으로 남겨 두되 env 를 우선한다.
    parser.add_argument(
        "--api-key",
        default=os.environ.get("BYBIT_SMOKE_API_KEY"),
        help="Bybit API key. ★기본 경로는 env BYBIT_SMOKE_API_KEY (argv 는 ps 노출)",
    )
    parser.add_argument(
        "--api-secret",
        default=os.environ.get("BYBIT_SMOKE_API_SECRET"),
        help="Bybit API secret. ★기본 경로는 env BYBIT_SMOKE_API_SECRET",
    )
    parser.add_argument(
        "--symbol",
        default="BTC/USDT:USDT",
        help="심볼. linear perp 은 BTC/USDT:USDT · spot 은 BTC/USDT (default: BTC/USDT:USDT)",
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
        "--market",
        choices=["spot", "linear"],
        default="linear",
        help=(
            "spot 이면 margin_mode/leverage 단계를 건너뛴다(spot 계정에 없는 개념). "
            "default: linear — rename 이전 동작 보존"
        ),
    )
    args = parser.parse_args()

    # fail-closed — credentials 부재는 「데모로 폴백」이 아니라 즉시 거부다.
    if not args.api_key or not args.api_secret:
        print(
            "credentials missing — set BYBIT_SMOKE_API_KEY / BYBIT_SMOKE_API_SECRET "
            "(정문: tools/scripts/bybit-smoke.sh)",
            file=sys.stderr,
        )
        return 2

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
            market=args.market,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
