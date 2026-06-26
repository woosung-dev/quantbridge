"""Phase 3 D — 라이브 maker-TP bracket 실 Bybit demo round-trip 검증.

게이트가 남긴 단 하나의 미검증 항목 = "Bybit 가 maker-TP(tpslMode=Partial + tpSize) +
position-linked OCO bracket 을 실제로 수용하는가". 이 스크립트는 **실 라이브 dispatch 가 쓰는
BybitFuturesProvider**(set_margin_mode → set_leverage → _merge_exit_params 그대로)를 써서
api-demo.bybit.com 에 market entry + maker-TP/SL bracket 을 올리고, 거래소가 수용했는지 +
TP/SL 이 reduce-only position-linked 주문으로 부착됐는지 데이터로 확정한 뒤 포지션을 정리한다.
실자금 아님(가상자금).

★ Bybit V5 Partial-mode attached TP/SL 은 position 의 takeProfit/stopLoss 필드를 채우지 않고
별도 reduce-only conditional 주문 2개(stopOrderType=PartialTakeProfit/PartialStopLoss)로 생성된다.
따라서 검증은 fetch_open_orders 상세를 data-driven 으로 판정한다(빈 position 필드 ≠ 실패).

실행 (사용자가 키 보유 — 직접 실행):
    cd backend
    uv run python scripts/verify_phase3_maker_tp_bracket.py \\
        --api-key "$BYBIT_DEMO_KEY" --api-secret "$BYBIT_DEMO_SECRET" \\
        --symbol "BTC/USDT:USDT" --quantity 0.001 --leverage 1
    # verdict 로직만 (네트워크/키 불필요): --selftest

검증 경로:
    1. fetch_balance → USDT > 0
    2. set_leverage (provider 가 set_margin_mode/set_leverage 도 재수행)
    3. ticker 기준 TP(현재가+2%) / SL(현재가-2%) 산출
    4. BybitFuturesProvider.create_order(market entry + take_profit/stop_loss bracket,
       client_order_id=orderLinkId) → 거래소 수용 여부 (ProviderError/ccxt 거부 시 미수용 확정)
    5. fetch_positions → position 필드 로깅 (Partial 모드는 비어있음이 정상)
    6. fetch_open_orders → 각 주문 상세 dump + classify_bracket data-driven verdict
       (PartialTakeProfit reduce-only Limit @≈+2% + PartialStopLoss reduce-only @≈-2%,
        parentOrderLinkId == entry orderLinkId = OCO-linkage)
    7. CLEANUP — 포지션 reduce-only market 청산 + 잔여 주문 취소 (finally 보장)

모든 단계 JSON 로깅. verdict PASS = exit code 0, FAIL/거부/실패 = 1.
OCO-on-fill(형제 자동취소)은 maker-TP limit 이 시장 위 rest 라 결정적 증명 불가 → 정직 이연.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

# scripts/ 직접 실행 시 backend/ 를 sys.path 에 추가 (src import).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ccxt.async_support as ccxt_async

from src.trading.exceptions import ProviderError
from src.trading.models import ExchangeMode, OrderSide, OrderType
from src.trading.providers import BybitFuturesProvider, Credentials, OrderSubmit


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


def _is_true(val: Any) -> bool:
    """Bybit raw reduceOnly 가 bool 또는 'true'/'false' 문자열 둘 다 가능 → 정규화."""
    return val is True or str(val).lower() == "true"


def _approx(actual: Any, expected: Decimal, *, tol: Decimal = Decimal("0.005")) -> bool:
    """가격 근접 비교 (상대 오차 ≤ tol). +2%/-2% 를 구분할 만큼 타이트(0.5%)."""
    try:
        a = Decimal(str(actual))
    except (InvalidOperation, TypeError, ValueError):
        return False
    if expected == 0:
        return a == 0
    return abs(a - expected) / expected <= tol


def _order_details(open_orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """ccxt open order → verdict 에 필요한 raw Bybit 필드 추출 (info 우선)."""
    out: list[dict[str, Any]] = []
    for o in open_orders:
        info = o.get("info", {}) or {}
        out.append(
            {
                "id": o.get("id"),
                "side": o.get("side") or info.get("side"),
                "orderType": info.get("orderType") or o.get("type"),
                "stopOrderType": info.get("stopOrderType"),
                "reduceOnly": info.get("reduceOnly", o.get("reduceOnly")),
                "triggerPrice": info.get("triggerPrice") or o.get("triggerPrice"),
                "price": info.get("price") or o.get("price"),
                "tpslMode": info.get("tpslMode"),
                "parentOrderLinkId": info.get("parentOrderLinkId"),
                "orderLinkId": info.get("orderLinkId"),
            }
        )
    return out


def classify_bracket(
    details: list[dict[str, Any]],
    *,
    take_profit: Decimal,
    stop_loss: Decimal,
    entry_link_id: str,
) -> tuple[bool, str]:
    """Falsifiable verdict — Partial maker-TP + SL 가 reduce-only position-linked OCO 로 부착됐는가.

    PASS = 두 레그 모두 존재 +
      (a) TP: stopOrderType=="PartialTakeProfit", reduceOnly, orderType==Limit,
          triggerPrice≈take_profit, **limit price≈take_profit**(maker TP),
          **parentOrderLinkId==entry orderLinkId**
      (b) SL: stopOrderType=="PartialStopLoss", reduceOnly, triggerPrice≈stop_loss,
          **parentOrderLinkId==entry orderLinkId**
    stopOrderType 정확 일치 = Full/standalone 과 구분. parentOrderLinkId 일치 = entry-attached OCO.
    우리 경로는 항상 Partial(tpLimitPrice 주입) → Full-mode fallback 없음(false-PASS 차단, codex gate).
    parentOrderLinkId/price 미충족 시 해당 leg 미매칭 → FAIL (per-order dump 으로 사유 가시화).
    """
    tp = next(
        (
            d
            for d in details
            if d.get("stopOrderType") == "PartialTakeProfit"
            and _is_true(d.get("reduceOnly"))
            and str(d.get("orderType")).lower() == "limit"
            and _approx(d.get("triggerPrice"), take_profit)
            and _approx(d.get("price"), take_profit)
            and d.get("parentOrderLinkId") == entry_link_id
        ),
        None,
    )
    sl = next(
        (
            d
            for d in details
            if d.get("stopOrderType") == "PartialStopLoss"
            and _is_true(d.get("reduceOnly"))
            and _approx(d.get("triggerPrice"), stop_loss)
            and d.get("parentOrderLinkId") == entry_link_id
        ),
        None,
    )
    if tp is not None and sl is not None:
        return True, "partial_bracket_attached (parentOrderLinkId 일치)"

    missing = []
    if tp is None:
        missing.append("PartialTakeProfit")
    if sl is None:
        missing.append("PartialStopLoss")
    return False, f"bracket_not_attached_or_unlinked missing={','.join(missing) or 'none'}"


def _selftest() -> int:
    """네트워크/키 없이 classify_bracket verdict 로직 검증 (fabricated orders)."""
    tp, sl, link = Decimal("61000"), Decimal("59000"), "entry-link-1"
    good_tp = {
        "stopOrderType": "PartialTakeProfit",
        "reduceOnly": True,
        "orderType": "Limit",
        "triggerPrice": "61000",
        "price": "61000",  # maker limit price ≈ TP
        "parentOrderLinkId": link,
    }
    good_sl = {
        "stopOrderType": "PartialStopLoss",
        "reduceOnly": True,
        "orderType": "Market",
        "triggerPrice": "59000",
        "price": "0",
        "parentOrderLinkId": link,
    }

    def passes(orders: list[dict[str, Any]]) -> bool:
        return classify_bracket(orders, take_profit=tp, stop_loss=sl, entry_link_id=link)[0]

    def fails(orders: list[dict[str, Any]]) -> bool:
        return not passes(orders)

    # PASS: 정상 Partial bracket
    ok, reason = classify_bracket(
        [good_tp, good_sl], take_profit=tp, stop_loss=sl, entry_link_id=link
    )
    assert ok and "일치" in reason, reason

    # FAIL: non-Partial stopOrderType (= standalone, position-linked 아님)
    assert fails(
        [dict(good_tp, stopOrderType="TakeProfit"), dict(good_sl, stopOrderType="StopLoss")]
    )
    # FAIL: SL leg 누락
    assert fails([good_tp])
    # FAIL: TP 가 reduce-only 아님 (over-fill 위험)
    assert fails([dict(good_tp, reduceOnly=False), good_sl])
    # FAIL: TP triggerPrice 엉뚱 (±2% 밖)
    assert fails([dict(good_tp, triggerPrice="70000"), good_sl])
    # FAIL: TP limit price 엉뚱 (maker price 불일치 — codex BLOCKER)
    assert fails([dict(good_tp, price="70000"), good_sl])
    # FAIL: parentOrderLinkId 불일치 (OCO-linkage 미증명 — codex BLOCKER, 하드 게이트)
    assert fails(
        [dict(good_tp, parentOrderLinkId="other"), dict(good_sl, parentOrderLinkId="other")]
    )
    # FAIL: parentOrderLinkId 미설정 (빈 문자열)
    assert fails([dict(good_tp, parentOrderLinkId=""), dict(good_sl, parentOrderLinkId="")])
    # FAIL: Partial leg 없음 (Full-mode fallback 제거 — codex BLOCKER)
    assert fails([])
    # PASS: reduceOnly 문자열 'true' 도 인정
    assert passes([dict(good_tp, reduceOnly="true"), dict(good_sl, reduceOnly="true")])

    print(json.dumps({"selftest": "OK", "cases": 10}))
    return 0


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

        # 4. 실 라이브 dispatch 경로 — BybitFuturesProvider.create_order (maker-TP bracket).
        #    client_order_id=orderLinkId 설정 → 부착 TP/SL 의 parentOrderLinkId 매칭으로
        #    entry-attached(독립 standalone 아님) OCO-linkage 확인.
        entry_link_id = str(uuid4())
        submit = OrderSubmit(
            symbol=symbol,
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=quantity,
            price=None,
            leverage=leverage,
            margin_mode="cross",
            client_order_id=entry_link_id,  # → Bybit orderLinkId (parentOrderLinkId 매칭용)
            take_profit=take_profit,  # → tpOrderType=Limit + tpslMode=Partial + tpSize
            stop_loss=stop_loss,  # → market SL + slSize
        )
        log(
            "create_order_start", symbol=symbol, quantity=str(quantity), order_link_id=entry_link_id
        )
        try:
            receipt = await BybitFuturesProvider().create_order(creds, submit)
        except (ProviderError, ccxt_async.BaseError) as exc:
            # ★ 핵심 결과 — provider 는 ccxt 에러를 ProviderError 로 wrap. 거부 시 여기로 정확 라우팅.
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

        # 5. 포지션 조회 — Partial 모드는 position TP/SL 필드가 비어있음이 정상.
        await asyncio.sleep(1.5)  # 체결/포지션/주문 반영 대기
        positions = await inspect.fetch_positions([symbol])
        pos = next((p for p in positions if Decimal(str(p.get("contracts") or 0)) != 0), None)
        position_info: dict[str, Any] = pos.get("info", {}) if pos is not None else {}
        if pos is not None:
            log(
                "position",
                contracts=str(pos.get("contracts")),
                entry_price=str(pos.get("entryPrice")),
                takeProfit=position_info.get("takeProfit"),
                stopLoss=position_info.get("stopLoss"),
                tpslMode=position_info.get("tpslMode"),
            )
        else:
            log("position_none", note="포지션 미발견 — 즉시 체결 후 반영 지연 가능")

        # 6. 부착 TP/SL = 별도 reduce-only conditional 주문. 상세 dump + data-driven verdict.
        try:
            open_orders = await inspect.fetch_open_orders(symbol)
        except ccxt_async.BaseError as exc:
            log("open_orders_skip", error=str(exc))
            open_orders = []
        details = _order_details(open_orders)
        for d in details:
            log("open_order", **d)

        verdict_pass, reason = classify_bracket(
            details,
            take_profit=take_profit,
            stop_loss=stop_loss,
            entry_link_id=entry_link_id,
        )
        log(
            "verdict",
            result="PASS" if verdict_pass else "FAIL",
            reason=reason,
            open_orders_count=len(details),
            conclusion=(
                "Bybit demo 가 Phase 3 maker-TP(Partial) bracket 을 reduce-only "
                "position-linked TP/SL 로 수용·부착 (OCO-on-fill 은 정직 이연)"
                if verdict_pass
                else "부착 미확인 — maker-TP 설계(Full vs Partial / 부착 vs 별도 OCO) 재검토 필요"
            ),
        )
        return 0 if verdict_pass else 1

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
    p.add_argument("--api-key")
    p.add_argument("--api-secret")
    p.add_argument("--symbol", default="BTC/USDT:USDT")
    p.add_argument("--quantity", type=Decimal, default=Decimal("0.001"))
    p.add_argument("--leverage", type=int, default=1)
    p.add_argument(
        "--selftest", action="store_true", help="verdict 로직만 검증 (네트워크/키 불필요)"
    )
    args = p.parse_args()
    if args.selftest:
        return _selftest()
    if not args.api_key or not args.api_secret:
        p.error("--api-key 와 --api-secret 필수 (또는 --selftest)")
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
