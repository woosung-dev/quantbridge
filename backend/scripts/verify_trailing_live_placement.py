"""STEP B D — 라이브 trailing-stop live-placement 실 Bybit demo round-trip 검증.

게이트가 남긴 단 하나의 미검증 항목 = "Bybit 가 fill 후 set_trading_stop(native trailing)을
실제로 수용하고, 기존 bracket SL 을 덮어쓰지 않으며, 포지션을 reduce 하는 방향으로 부착하는가".

이 스크립트는 **실 라이브가 쓰는 BybitFuturesProvider.set_trading_stop / fetch_position** 을 써서
api-demo.bybit.com 에 market entry(+고정 SL bracket) → trailing 부착 → **독립 fetch_positions**
read-back 으로 data-driven 판정(반환값 신뢰 금지 = false-PASS 차단)한 뒤 포지션을 정리한다.
실자금 아님(가상자금). dispatch provider = BybitFuturesProvider(linear), BybitDemoProvider(spot) 아님.

실행 (사용자가 키 보유 — 직접 실행):
    cd backend
    uv run python scripts/verify_trailing_live_placement.py \\
        --api-key "$BYBIT_DEMO_KEY" --api-secret "$BYBIT_DEMO_SECRET" \\
        --symbol "BTC/USDT:USDT" --quantity 0.001 --leverage 1 --distance 200
    # verdict 로직만 (네트워크/키 불필요): --selftest

검증 경로 (non-circular — 쓰기와 다른 엔드포인트로 read-back):
    1. fetch_balance → USDT > 0
    2. BybitFuturesProvider.create_order(market entry + 고정 stop_loss bracket) → 포지션 open
    3. PRE: raw fetch_positions → size>0(체결 확인) + trailingStop==0(baseline) + sl0 기록
    4. ACT: BybitFuturesProvider.set_trading_stop(distance) (반환값 신뢰 안 함)
    5. POST: fresh fetch_positions → trailingStop>0 + ==distance(±tick) + stopLoss==sl0(미clobber)
       + side/size 불변(미반전·미축소)
    6. CLEANUP — 포지션 reduce-only market 청산 + 잔여 주문 취소 (finally 보장)

verdict PASS = exit 0, FAIL/거부 = 1. (트리거 실발동 reduce 의미증명은 가격 조작 불가라 정직 이연 —
대신 trailingStop>0 부착 + 방향(side) 보존으로 확인.)
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
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ccxt.async_support as ccxt_async

from src.trading.exceptions import ProviderError
from src.trading.models import ExchangeMode, OrderSide, OrderType
from src.trading.providers import BybitFuturesProvider, Credentials, OrderSubmit


def log(event: str, **fields: Any) -> None:
    print(json.dumps({"ts": datetime.now(UTC).isoformat(), "event": event, **fields}, default=str))


def _raw_demo_client(api_key: str, api_secret: str) -> Any:
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


def _ts(pos: dict[str, Any]) -> Decimal:
    """포지션 info 에서 trailingStop 추출(문자열/None → Decimal)."""
    raw = (pos.get("info") or {}).get("trailingStop")
    if raw in (None, "", "0", "0.0", "0.00"):
        return Decimal("0")
    return Decimal(str(raw))


def _sl(pos: dict[str, Any]) -> Decimal:
    raw = (pos.get("info") or {}).get("stopLoss")
    if raw in (None, "", "0", "0.0", "0.00"):
        return Decimal("0")
    return Decimal(str(raw))


def _size(pos: dict[str, Any]) -> Decimal:
    c = pos.get("contracts")
    return Decimal(str(c)) if c is not None else Decimal("0")


def classify_trailing(
    *,
    pre: dict[str, Any] | None,
    post: dict[str, Any] | None,
    expected_distance: Decimal,
    price_tick: Decimal,
) -> tuple[bool, list[str]]:
    """non-circular data-driven verdict. PASS = 모든 불변식 충족.

    독립 fetch_positions 의 PRE→POST delta 로 판정(set_trading_stop 반환값 신뢰 안 함).
    """
    reasons: list[str] = []
    if pre is None or _size(pre) <= 0:
        return False, ["PRE: 포지션 미존재/size<=0 (entry 미체결)"]
    if _ts(pre) != 0:
        reasons.append(f"PRE: trailingStop baseline != 0 ({_ts(pre)}) — 사전 트레일 잔존")
    if post is None or _size(post) <= 0:
        return False, [*reasons, "POST: 포지션 사라짐(size<=0) — 부착 전 청산?"]

    # ★ 핵심 delta — 독립 fetch 로 trailing 부착 확인(stub 불가).
    if _ts(post) <= 0:
        reasons.append(f"POST: trailingStop 미부착 ({_ts(post)})")
    # units/scaling killer — 의도 거리와 일치(±tick).
    if abs(_ts(post) - expected_distance) > price_tick:
        reasons.append(
            f"POST: trailingStop {_ts(post)} != 의도 {expected_distance} (±{price_tick} 초과)"
        )
    # bracket SL 미clobber — trading-stop 호출이 기존 SL 을 덮어쓰면 안 됨.
    if _sl(pre) != 0 and _sl(post) != _sl(pre):
        reasons.append(f"POST: 기존 bracket SL clobber ({_sl(pre)} → {_sl(post)})")
    # 방향/수량 불변 — 반전/축소 없음.
    if post.get("side") != pre.get("side"):
        reasons.append(f"POST: side 변경 {pre.get('side')} → {post.get('side')} (반전)")
    if _size(post) != _size(pre):
        reasons.append(f"POST: size 변경 {_size(pre)} → {_size(post)} (축소/증가)")

    return (len(reasons) == 0), reasons


async def _fetch_one_position(ex: Any, symbol: str) -> dict[str, Any] | None:
    positions = await ex.fetch_positions([symbol])
    for p in positions:
        if _size(p) > 0:
            return p
    return None


async def run(args: argparse.Namespace) -> int:
    creds = Credentials(
        api_key=args.api_key,
        api_secret=args.api_secret,
        environment=ExchangeMode.demo,
    )
    provider = BybitFuturesProvider()
    raw = _raw_demo_client(args.api_key, args.api_secret)
    symbol = args.symbol
    qty = Decimal(str(args.quantity))
    distance = Decimal(str(args.distance))
    price_tick = Decimal(str(args.price_tick))
    entry_order_id: str | None = None
    try:
        bal = await raw.fetch_balance()
        usdt = (bal.get("USDT") or {}).get("free")
        log("balance", usdt_free=usdt)
        if not usdt or Decimal(str(usdt)) <= 0:
            log("verdict", result="FAIL", reason="USDT 잔고 0 — demo 충전 필요")
            return 1

        ticker = await raw.fetch_ticker(symbol)
        last = Decimal(str(ticker["last"]))
        sl_price = (last * Decimal("0.97")).quantize(Decimal("0.1"))
        log("entry_plan", last=last, stop_loss=sl_price, distance=distance)

        # 2. market entry(long) + 고정 SL bracket — SL clobber 검증용.
        entry = OrderSubmit(
            symbol=symbol,
            side=OrderSide.buy,
            type=OrderType.market,
            quantity=qty,
            price=None,
            leverage=args.leverage,
            margin_mode="cross",
            client_order_id=str(uuid4()),
            stop_loss=sl_price,
        )
        receipt = await provider.create_order(creds, entry)
        entry_order_id = receipt.exchange_order_id
        log("entry_filled", exchange_order_id=entry_order_id, status=receipt.status)
        await asyncio.sleep(2)  # 포지션 거래소 정착

        # 3. PRE (독립 fetch)
        pre = await _fetch_one_position(raw, symbol)
        log(
            "pre_position",
            size=_size(pre) if pre else 0,
            trailingStop=str(_ts(pre)) if pre else None,
            stopLoss=str(_sl(pre)) if pre else None,
            side=pre.get("side") if pre else None,
        )

        # 4. ACT — 실 dispatch 가 쓰는 provider.set_trading_stop.
        pos_for_place = await provider.fetch_position(creds, symbol)
        if pos_for_place is None:
            log("verdict", result="FAIL", reason="placement 전 포지션 없음")
            return 1
        exit_side = OrderSide.sell  # long 청산
        await provider.set_trading_stop(
            creds, symbol=symbol, side=exit_side, qty=pos_for_place.size, distance=distance
        )
        log("set_trading_stop_done", qty=str(pos_for_place.size), distance=str(distance))
        await asyncio.sleep(2)

        # 5. POST (fresh 독립 fetch = 검증)
        post = await _fetch_one_position(raw, symbol)
        log(
            "post_position",
            size=_size(post) if post else 0,
            trailingStop=str(_ts(post)) if post else None,
            stopLoss=str(_sl(post)) if post else None,
            side=post.get("side") if post else None,
        )

        ok, reasons = classify_trailing(
            pre=pre, post=post, expected_distance=distance, price_tick=price_tick
        )
        log("verdict", result="PASS" if ok else "FAIL", reasons=reasons)
        return 0 if ok else 1
    except ProviderError as e:
        log("verdict", result="FAIL", reason=f"ProviderError: {e}")
        return 1
    finally:
        # CLEANUP — reduce-only market 청산 + 잔여 주문 취소.
        with contextlib.suppress(Exception):
            pos = await _fetch_one_position(raw, symbol)
            if pos is not None and _size(pos) > 0:
                close_side = "sell" if pos.get("side") == "long" else "buy"
                await raw.create_order(
                    symbol, "market", close_side, float(_size(pos)), None, {"reduceOnly": True}
                )
                log("cleanup_closed", size=str(_size(pos)))
        with contextlib.suppress(Exception):
            for o in await raw.fetch_open_orders(symbol):
                await raw.cancel_order(o["id"], symbol)
        with contextlib.suppress(Exception):
            await raw.close()


def _selftest() -> int:
    """verdict 로직만 (네트워크/키 불필요). false-PASS 차단 케이스 포함."""
    tick = Decimal("0.5")
    dist = Decimal("200")

    def pos(size, ts, sl, side="long"):
        return {"contracts": size, "side": side, "info": {"trailingStop": ts, "stopLoss": sl}}

    cases: list[tuple[str, bool, dict[str, Any]]] = [
        (
            "happy: 부착+SL보존+불변",
            True,
            {"pre": pos("0.001", "0", "47000"), "post": pos("0.001", "200", "47000")},
        ),
        (
            "happy: SL 없는 진입도 OK",
            True,
            {"pre": pos("0.001", "0", "0"), "post": pos("0.001", "200", "0")},
        ),
        (
            "FAIL: 미부착(false-PASS 차단)",
            False,
            {"pre": pos("0.001", "0", "47000"), "post": pos("0.001", "0", "47000")},
        ),
        (
            "FAIL: 거리 10x(units/scaling)",
            False,
            {"pre": pos("0.001", "0", "47000"), "post": pos("0.001", "2000", "47000")},
        ),
        (
            "FAIL: bracket SL clobber",
            False,
            {"pre": pos("0.001", "0", "47000"), "post": pos("0.001", "200", "0")},
        ),
        (
            "FAIL: 방향 반전",
            False,
            {"pre": pos("0.001", "0", "0"), "post": pos("0.001", "200", "0", side="short")},
        ),
        (
            "FAIL: 수량 축소",
            False,
            {"pre": pos("0.001", "0", "0"), "post": pos("0.0005", "200", "0")},
        ),
        ("FAIL: 진입 미체결", False, {"pre": None, "post": None}),
        ("FAIL: 부착 전 청산", False, {"pre": pos("0.001", "0", "0"), "post": pos("0", "0", "0")}),
    ]
    failures = 0
    for name, expect, kw in cases:
        ok, reasons = classify_trailing(expected_distance=dist, price_tick=tick, **kw)
        status = "OK" if ok == expect else "MISMATCH"
        if ok != expect:
            failures += 1
        log("selftest", case=name, got=ok, expect=expect, status=status, reasons=reasons)
    log("selftest_summary", failures=failures, total=len(cases))
    return 0 if failures == 0 else 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api-key")
    p.add_argument("--api-secret")
    p.add_argument("--symbol", default="BTC/USDT:USDT")
    p.add_argument("--quantity", default="0.001")
    p.add_argument("--leverage", type=int, default=1)
    p.add_argument("--distance", default="200", help="trailing 거리(quote)")
    p.add_argument("--price-tick", default="1", help="거리 비교 허용 오차")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    if args.selftest:
        return _selftest()
    if not args.api_key or not args.api_secret:
        log("error", reason="--api-key/--api-secret 필요 (또는 --selftest)")
        return 2
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
