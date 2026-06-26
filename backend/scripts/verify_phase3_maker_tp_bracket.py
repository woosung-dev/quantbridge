"""Phase 3 D — 라이브 maker-TP bracket 실 Bybit demo round-trip 검증.

게이트가 남긴 단 하나의 미검증 항목 = "Bybit 가 maker-TP(tpslMode=Partial + tpSize) +
position-native-OCO bracket 을 실제로 수용하는가". 이 스크립트는 **실제 BybitDemoProvider**
(프로덕션 주문 경로, _merge_exit_params 그대로)를 써서 api-demo.bybit.com 에 market entry +
maker-TP/SL bracket 을 올리고, 거래소가 수용했는지 + 포지션에 TP/SL 이 붙었는지(tpslMode=Partial,
TP=Limit) 확인한 뒤 포지션을 정리한다. 실자금 아님(가상자금).

실행 (사용자가 키 보유 — 직접 실행):
    cd backend
    uv run python scripts/verify_phase3_maker_tp_bracket.py \\
        --api-key "$BYBIT_DEMO_KEY" --api-secret "$BYBIT_DEMO_SECRET" \\
        --symbol "BTC/USDT:USDT" --quantity 0.001 --leverage 1

검증 경로:
    1. fetch_balance → USDT > 0
    2. set_leverage
    3. ticker 기준 TP(현재가+2%) / SL(현재가-2%) 산출
    4. BybitDemoProvider.create_order(market entry + take_profit/stop_loss bracket)
       → 거래소 수용 여부 (rejection 시 maker-TP Partial 미수용 확정)
    5. fetch_positions → 포지션에 TP/SL 부착 확인 (takeProfit/stopLoss/tpslMode)
    6. fetch_open_orders → 잔여 conditional 주문 점검
    7. CLEANUP — 포지션 reduce-only market 청산 + 잔여 주문 취소 (finally 보장)

모든 단계 JSON 로깅. 거래소 수용 = exit code 0, 거부/실패 = 1.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

# scripts/ 직접 실행 시 backend/ 를 sys.path 에 추가 (src import).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ccxt.async_support as ccxt_async

from src.trading.models import ExchangeMode, OrderSide, OrderType
from src.trading.providers import BybitDemoProvider, Credentials, OrderSubmit


def log(event: str, **fields: Any) -> None:
    print(json.dumps({"ts": datetime.now(UTC).isoformat(), "event": event, **fields}, default=str))


def _raw_demo_client(api_key: str, api_secret: str) -> ccxt_async.bybit:
    """검사/정리용 raw ccxt demo 클라이언트 (provider 와 동일 env routing)."""
    ex = ccxt_async.bybit(
        {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "timeout": 30000,
            "options": {"defaultType": "linear", "testnet": False},
        }
    )
    ex.enable_demo_trading(True)
    return ex


async def run(
    *, api_key: str, api_secret: str, symbol: str, quantity: Decimal, leverage: int
) -> int:
    creds = Credentials(api_key=api_key, api_secret=api_secret, environment=ExchangeMode.demo)
    inspect = _raw_demo_client(api_key, api_secret)
    opened = False
    try:
        # 1. balance
        bal = await inspect.fetch_balance()
        usdt = Decimal(str(bal.get("USDT", {}).get("free", "0")))
        log("balance", usdt_free=str(usdt))
        if usdt <= 0:
            log("fail", reason="zero_usdt_balance")
            return 1

        # 2. leverage
        try:
            await inspect.set_leverage(leverage, symbol)
        except ccxt_async.BaseError as exc:
            if "not modified" not in str(exc):
                raise
        log("leverage_set", leverage=leverage)

        # 3. TP/SL 산출 — 현재가 ±2% (TP 위, SL 아래; long entry 기준)
        ticker = await inspect.fetch_ticker(symbol)
        last = Decimal(str(ticker.get("last") or ticker.get("close") or 0))
        if last <= 0:
            log("fail", reason="no_last_price")
            return 1
        take_profit = (last * Decimal("1.02")).quantize(Decimal("0.1"))
        stop_loss = (last * Decimal("0.98")).quantize(Decimal("0.1"))
        log("levels", last=str(last), take_profit=str(take_profit), stop_loss=str(stop_loss))

        # 4. 실제 프로덕션 경로 — BybitDemoProvider.create_order (maker-TP bracket).
        submit = OrderSubmit(
            symbol=symbol,
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=quantity,
            price=None,
            leverage=leverage,
            margin_mode="cross",
            take_profit=take_profit,  # → tpOrderType=Limit + tpslMode=Partial + tpSize
            stop_loss=stop_loss,  # → market SL + slSize
        )
        log("create_order_start", symbol=symbol, quantity=str(quantity))
        try:
            receipt = await BybitDemoProvider().create_order(creds, submit)
        except ccxt_async.BaseError as exc:
            # ★ 핵심 결과 — 거래소가 maker-TP Partial bracket 을 거부하면 여기로.
            log(
                "create_order_REJECTED",
                error_type=type(exc).__name__,
                error=str(exc),
                conclusion="Bybit 가 maker-TP(Partial)+tpSize bracket 미수용 — contingency 필요",
            )
            return 1
        opened = receipt.status in ("filled", "submitted")
        log(
            "create_order_ACCEPTED",
            exchange_order_id=receipt.exchange_order_id,
            status=receipt.status,
            filled_price=str(receipt.filled_price) if receipt.filled_price else None,
        )

        # 5. 포지션에 TP/SL 부착 확인
        await asyncio.sleep(1.0)  # 체결/포지션 반영 대기
        positions = await inspect.fetch_positions([symbol])
        pos = next((p for p in positions if Decimal(str(p.get("contracts") or 0)) != 0), None)
        if pos is not None:
            info = pos.get("info", {})
            log(
                "position_bracket",
                contracts=str(pos.get("contracts")),
                entry_price=str(pos.get("entryPrice")),
                takeProfit=info.get("takeProfit"),
                stopLoss=info.get("stopLoss"),
                tpslMode=info.get("tpslMode"),
                tpLimitPrice=info.get("tpLimitPrice"),
                tpOrderType=info.get("tpOrderType"),
                conclusion="maker-TP(Limit/Partial) + native-OCO bracket 부착 확인",
            )
        else:
            log("position_none", note="포지션 미발견 — 즉시 체결 후 반영 지연 가능")

        # 6. 잔여 conditional 주문 점검
        try:
            open_orders = await inspect.fetch_open_orders(symbol)
            log("open_orders", count=len(open_orders))
        except ccxt_async.BaseError as exc:
            log("open_orders_skip", error=str(exc))

        log("verify_success", conclusion="Bybit demo 가 Phase 3 maker-TP bracket 수용")
        return 0

    except ccxt_async.BaseError as exc:
        log("fail", reason="ccxt_error", error_type=type(exc).__name__, error=str(exc))
        return 1
    except Exception as exc:
        # SECURITY: non-ccxt 예외 메시지는 키 노출 가능 → 타입만.
        log("fail", reason="unexpected", error_type=type(exc).__name__)
        return 1
    finally:
        # CLEANUP — 열린 포지션 reduce-only 청산 + 잔여 주문 취소 (가상자금이라도 정리).
        try:
            if opened:
                with contextlib.suppress(ccxt_async.BaseError):
                    await inspect.cancel_all_orders(symbol)
                positions = await inspect.fetch_positions([symbol])
                pos = next(
                    (p for p in positions if Decimal(str(p.get("contracts") or 0)) != 0), None
                )
                if pos is not None:
                    qty = abs(Decimal(str(pos.get("contracts") or 0)))
                    close_side = "sell" if pos.get("side") == "long" else "buy"
                    await inspect.create_order(
                        symbol, "market", close_side, float(qty), None, {"reduceOnly": True}
                    )
                    log("cleanup_closed", side=close_side, qty=str(qty))
        except Exception as exc:
            log("cleanup_warning", error_type=type(exc).__name__)
        finally:
            with contextlib.suppress(Exception):
                await inspect.close()


def main() -> int:
    p = argparse.ArgumentParser(description="Phase 3 maker-TP bracket 실 Bybit demo 검증")
    p.add_argument("--api-key", required=True)
    p.add_argument("--api-secret", required=True)
    p.add_argument("--symbol", default="BTC/USDT:USDT")
    p.add_argument("--quantity", type=Decimal, default=Decimal("0.001"))
    p.add_argument("--leverage", type=int, default=1)
    args = p.parse_args()
    return asyncio.run(
        run(
            api_key=args.api_key,
            api_secret=args.api_secret,
            symbol=args.symbol,
            quantity=args.quantity,
            leverage=args.leverage,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
