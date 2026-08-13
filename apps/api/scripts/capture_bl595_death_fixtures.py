#!/usr/bin/env python
# [BL-595] `position_divergence` 사망 세션의 라이브 재생 입력을 **얼린다** — 1회성 캡처.
"""`position_divergence` 로 죽은 세션의 `run_live` 입력을 재구성해 JSON 픽스처로 남긴다.

## 왜 스크립트와 테스트를 가르나

테스트는 **네트워크도 DB 도 타면 안 된다**. 그런데 재현에 필요한 1분봉은 DB 에 없고
(`ts.ohlcv` 에 `1m` 행이 0건 — 라이브는 `CCXTProvider` 로 직접 받는다) 거래소에서만 온다.
그래서 캡처는 여기서 **한 번** 하고, 테스트는 얼린 파일만 읽는다.

## 무엇이 오라클인가 (★순환을 피하는 자리)

이 스크립트는 재생 **입력**을 재구성할 때 프로덕션 헬퍼를 쓴다(`_resolve_position_epoch`,
`sum_realized_pnl_before`, `_extract_pyramiding`). 그러면 그 헬퍼가 틀렸을 때 픽스처가 그
버그를 물려받는다. 그래서 **판정의 오라클은 입력 쪽이 아니라 원장 쪽**이다:

    ledger_net = Σ (buy 면 +filled_quantity, sell 면 -filled_quantity)   ... 사망 시각 이전

이 값은 엔진을 한 줄도 안 거친다. 순수 원장 산술이다. 사망 5건 전부에서 이 값과 엔진
포지션의 **부호가 반대**라는 것이 [BL-595] 의 관측 사실이고, 그것이 픽스처의 red 조건이다.

## 봉 시각에 대한 경고 (`LedgerFill` docstring 이 이미 적은 것)

`Order.filled_at` 은 거래소 체결시각이 아니라 **우리 관측시각**이다. 그러므로 이 값으로
"몇 번째 봉에서 체결됐나" 를 정하면 관측 지연만큼 **늦은** 봉을 고른다. 픽스처는 원본
`filled_at` 을 그대로 싣고 봉 귀속은 하지 않는다 — 귀속 규칙은 소비자(설계)의 몫이다.

## 사용

    cd apps/api && set -a; . ./.env.local; set +a; uv run python scripts/capture_bl595_death_fixtures.py

기본은 `deactivated_reason='position_divergence'` 세션 전량. `--session <prefix>` 로 좁힌다.
`--out` 기본값 = `apps/api/tests/fixtures/bl595/`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.request
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from sqlalchemy import text  # noqa: E402

from src.strategy.schemas import validate_strategy_settings  # noqa: E402
from src.tasks._worker_engine import create_worker_engine_and_sm  # noqa: E402

# 라이브 평가가 쓰는 창 크기 (`live_signal.py:2738` 의 `limit_bars=300`).
WINDOW_BARS = 300
# `live_signal.py:134` — 이 값보다 큰 공백은 catch-up 이 아니라 gap-resync 다.
MAX_CATCHUP_GAP = timedelta(minutes=5)
_INTERVAL_SECONDS = {"1m": 60, "3m": 180, "5m": 300, "15m": 900, "1h": 3600}
# Bybit 공개 kline 은 `category=linear` 가 perp 다. 직전 회차가 엔진 `CCXTProvider` perp ·
# 공개 perp · 데모 perp 가 사망 봉에서 **소수점까지 동일**함을 실측했다(2026-08-05 직전 회차).
_BYBIT_KLINE = "https://api.bybit.com/v5/market/kline"


def _bybit_symbol(symbol: str) -> str:
    return symbol.replace("/", "").replace(":USDT", "")


def _bybit_interval(interval: str) -> str:
    """`1m` → `1`. Bybit v5 는 분 단위를 숫자로만 받는다."""
    if interval.endswith("m"):
        return interval[:-1]
    if interval.endswith("h"):
        return str(int(interval[:-1]) * 60)
    raise ValueError(f"지원하지 않는 interval: {interval}")


def fetch_closed_bars(
    *, symbol: str, interval: str, last_bar_time: datetime, bars: int
) -> list[list[Any]]:
    """`last_bar_time` 으로 끝나는 종료 봉 `bars` 개를 CCXT 형식으로 돌려준다.

    반환 = `[[ts_ms, open, high, low, close, volume], ...]` 오름차순 — `_ohlcv_rows_to_dataframe`
    가 받는 것과 같은 모양이다(`live_signal.py:142`).

    ★Bybit 은 `start`+`end` 를 함께 주면 **창 뒤쪽부터** 준다(이 레포의 기록된 함정).
    그래서 넉넉히 받아 오름차순 정렬 후 뒤에서 `bars` 개를 자른다.
    """
    step = _INTERVAL_SECONDS[interval]
    end_ms = int(last_bar_time.timestamp()) * 1000
    start_ms = end_ms - (bars - 1) * step * 1000
    query = urlencode(
        {
            "category": "linear",
            "symbol": _bybit_symbol(symbol),
            "interval": _bybit_interval(interval),
            "start": start_ms,
            "end": end_ms,
            "limit": 1000,
        }
    )
    # 억제 사유: URL 은 위 상수(https 고정) + urlencode 결과뿐이라 스킴이 바뀔 경로가 없다.
    with urllib.request.urlopen(f"{_BYBIT_KLINE}?{query}", timeout=30) as response:  # noqa: S310
        payload = json.loads(response.read())
    if payload.get("retCode") != 0:
        raise RuntimeError(f"bybit kline 실패: {payload.get('retMsg')}")
    rows = [
        [int(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])]
        for row in payload["result"]["list"]
        if int(row[0]) <= end_ms
    ]
    rows.sort(key=lambda row: row[0])
    return rows[-bars:]


def _floor_to_interval(moment: datetime, *, step_seconds: int) -> datetime:
    epoch = int(moment.timestamp())
    return datetime.fromtimestamp((epoch // step_seconds) * step_seconds, tz=UTC)


def death_tick_last_bar(
    deactivated_at: datetime, last_evaluated_bar_time: datetime | None, *, interval: str
) -> datetime:
    """사망 tick 이 본 마지막 **종료** 봉 = `last_evaluated_bar_time`.

    ★**벽시계 공식(`floor(사망시각) - 1봉`)을 쓰면 안 된다 — 실측으로 틀렸다.**
    `market_data/providers/ccxt.py:146` 이 계산하는 `last_closed_ts` 는 **상한**일 뿐이고,
    거래소가 방금 닫힌 봉을 아직 **발행하지 않았으면** 그 tick 은 한 봉 **앞**에서 멈춘다.
    사망 5건 중 2건이 그 경우다(`39731d57` 16:25:01 사망인데 봉은 16:23 · `cc19abd2`
    18:51:01 사망인데 봉은 18:49) — 둘 다 사망 시각이 분 경계 **1.7초 뒤**였다.

    `last_evaluated_bar_time` 이 사망 tick 의 봉이라는 근거는 워커 로그다(`a16aa640`):
    직전 성공 tick 이 `last_bar_time=09:10` 을 반환했는데 세션 행의 값은 **09:11** 이다
    ⇒ 사망 tick 의 `try_claim_bar` 가 **커밋됐다**. 사망은 claim 뒤에 온다.

    NULL 이면(= 성공 평가가 한 번도 없었다) 벽시계 공식으로 떨어진다 — 그때는 다른 근거가 없다.
    """
    if last_evaluated_bar_time is not None:
        return last_evaluated_bar_time.astimezone(UTC)
    step = _INTERVAL_SECONDS[interval]
    return _floor_to_interval(deactivated_at, step_seconds=step) - timedelta(seconds=step)


_SESSION_SELECT = """
    SELECT s.id, s.strategy_id, s.exchange_account_id, s.symbol, s.interval,
           s.created_at, s.deactivated_at, s.last_evaluated_bar_time,
           s.equity_baseline_usdt,
           st.pine_source, st.settings, st.trading_sessions,
           ss.last_strategy_state_report
    FROM trading.live_signal_sessions s
    JOIN strategies st ON st.id = s.strategy_id
    LEFT JOIN trading.live_signal_states ss ON ss.session_id = s.id
    WHERE s.deactivated_reason = 'position_divergence'
"""
_SESSION_ORDER = " ORDER BY s.deactivated_at"
# ★문자열 조립을 여기 두 상수로 가둔다. 값은 전부 바인드 파라미터라 사용자 입력이 SQL 에
#   섞이는 경로가 없다(`--session` 은 `:prefix` 로만 들어간다).
_SESSION_PREFIX_FILTER = " AND left(s.id::text, 8) = :prefix"


async def _load_session(session: Any, prefix_filter: str | None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {}
    statement = _SESSION_SELECT
    if prefix_filter:
        statement += _SESSION_PREFIX_FILTER
        params["prefix"] = prefix_filter
    rows = (await session.execute(text(statement + _SESSION_ORDER), params)).mappings()
    return [dict(row) for row in rows]


async def _ledger_rows(
    session: Any, session_id: Any, deactivated_at: datetime
) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text(
                """
                SELECT id, idempotency_key, side::text AS side, state::text AS state,
                       quantity, filled_quantity, filled_price, filled_at, trigger_price,
                       reduce_only, created_at
                FROM trading.orders
                WHERE idempotency_key LIKE :prefix
                ORDER BY created_at
                """
            ),
            {"prefix": f"live:{session_id}:%"},
        )
    ).mappings()
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        # 사망 시각 이후에 관측된 체결은 그 tick 이 볼 수 없었다. 오라클에서 뺀다.
        item["observed_before_death"] = bool(
            item["filled_at"] is not None and item["filled_at"] < deactivated_at
        )
        out.append(item)
    return out


def _ledger_net(rows: list[dict[str, Any]]) -> Decimal:
    """★오라클 — 엔진을 한 줄도 안 거친 순수 원장 산술."""
    net = Decimal("0")
    for row in rows:
        quantity = row["filled_quantity"]
        if not row["observed_before_death"] or quantity is None or quantity == 0:
            continue
        signed = Decimal(str(quantity))
        net += signed if row["side"] == "buy" else -signed
    return net


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


async def _build_fixture(session: Any, row: dict[str, Any]) -> dict[str, Any]:
    from uuid import UUID

    from src.tasks.live_signal import _extract_pyramiding, _resolve_position_epoch
    from src.trading.repositories.live_signal_event_repository import LiveSignalEventRepository
    from src.trading.services.conditional_entry_planner import parse_live_entry_key

    session_id: UUID = row["id"]
    interval: str = row["interval"]
    step = _INTERVAL_SECONDS[interval]
    last_bar_time = death_tick_last_bar(
        row["deactivated_at"], row["last_evaluated_bar_time"], interval=interval
    )
    ohlcv = fetch_closed_bars(
        symbol=row["symbol"], interval=interval, last_bar_time=last_bar_time, bars=WINDOW_BARS
    )
    if not ohlcv or ohlcv[-1][0] != int(last_bar_time.timestamp()) * 1000:
        raise RuntimeError(
            f"{str(session_id)[:8]}: 마지막 봉이 {last_bar_time.isoformat()} 이 아니다 "
            f"(받은 마지막 = {ohlcv[-1][0] if ohlcv else None})"
        )
    window_start = datetime.fromtimestamp(ohlcv[0][0] / 1000, tz=UTC)

    settings = validate_strategy_settings(row["settings"])
    if settings is None:
        raise RuntimeError(f"{str(session_id)[:8]}: strategy.settings 가 비었다")

    # `live_signal.py:3061-3066` — 공백이 5분 이하면 catch-up watermark 를 싣는다. 그 값은
    # tick 시작 시점의 `last_evaluated_bar_time`, 즉 **직전** tick 의 봉이다. 사망 tick 의
    # claim 이 그 컬럼을 덮어썼으므로 관측할 수 없다 — 한 봉 앞으로 **추론**한다.
    # ★이 값은 `position_size` 에 영향을 주지 않는다: `event_loop.py:490-495` 의 이벤트
    #   필터에만 쓰이고, `position_epoch = min(epoch, emit)` 은 epoch(≈세션 생성)보다
    #   한참 뒤라 min 을 바꾸지 않는다. 아래에서 그 불변식을 실제로 확인한다.
    previous_bar = row["last_evaluated_bar_time"]
    emit_from_bar_time: datetime | None = last_bar_time - timedelta(seconds=step)
    if timedelta(seconds=step) > MAX_CATCHUP_GAP:
        emit_from_bar_time = None

    position_epoch = _resolve_position_epoch(
        row["last_strategy_state_report"],
        session_created_at=row["created_at"],
        last_bar_time=last_bar_time,
        has_previous_state=row["last_strategy_state_report"] is not None,
        realign=False,
    )
    if emit_from_bar_time is not None:
        clamped = min(position_epoch, emit_from_bar_time)
        if clamped != position_epoch:
            raise RuntimeError(
                f"{str(session_id)[:8]}: 추론한 emit_from_bar_time 이 position_epoch 을 당긴다 "
                f"— 추론값이 상태에 영향을 준다는 뜻이므로 이 픽스처는 신뢰할 수 없다"
            )

    event_repo = LiveSignalEventRepository(session)
    carry_cutoff = max(window_start, position_epoch)
    carry_pnl, _ = await event_repo.sum_realized_pnl_before(session_id, bar_time=carry_cutoff)
    effective_capital = Decimal(str(row["equity_baseline_usdt"])) + carry_pnl

    ledger = await _ledger_rows(session, session_id, row["deactivated_at"])
    fills: list[dict[str, Any]] = []
    for item in ledger:
        parsed = parse_live_entry_key(item["idempotency_key"])
        fills.append(
            {
                "order_id": str(item["id"]),
                "idempotency_key": item["idempotency_key"],
                "side": item["side"],
                "state": item["state"],
                "quantity": _json_safe(item["quantity"]),
                "filled_quantity": (
                    None if item["filled_quantity"] is None else _json_safe(item["filled_quantity"])
                ),
                "filled_price": (
                    None if item["filled_price"] is None else _json_safe(item["filled_price"])
                ),
                "filled_at": (None if item["filled_at"] is None else _json_safe(item["filled_at"])),
                "trigger_price": (
                    None if item["trigger_price"] is None else _json_safe(item["trigger_price"])
                ),
                "reduce_only": bool(item["reduce_only"]),
                "created_at": _json_safe(item["created_at"]),
                "observed_before_death": item["observed_before_death"],
                "entry_kind": None if parsed is None else parsed.kind,
                "trade_id": None if parsed is None else parsed.trade_id,
                "bar_epoch": None if parsed is None else parsed.bar_epoch,
            }
        )

    report = row["last_strategy_state_report"] or {}
    return {
        "_comment": (
            "[BL-595] position_divergence 사망 tick 의 run_live 입력. "
            "capture: apps/api/scripts/capture_bl595_death_fixtures.py — 손으로 고치지 마라."
        ),
        "session_id": str(session_id),
        "session_prefix": str(session_id)[:8],
        "symbol": row["symbol"],
        "interval": interval,
        "interval_seconds": step,
        "created_at": _json_safe(row["created_at"]),
        "deactivated_at": _json_safe(row["deactivated_at"]),
        "last_evaluated_bar_time": (None if previous_bar is None else _json_safe(previous_bar)),
        "death_tick_last_bar_time": _json_safe(last_bar_time),
        "window_start": _json_safe(window_start),
        "pine_source_md5": __import__("hashlib")
        .md5(  # 동일성 표식일 뿐 (보안 용도 아님)
            row["pine_source"].encode()
        )
        .hexdigest(),
        "run_live_kwargs": {
            "initial_capital": float(effective_capital),
            "live_position_size_pct": settings.position_size_pct,
            "leverage": float(settings.leverage),
            "sessions_allowed": list(row["trading_sessions"] or ()),
            "pyramiding": _extract_pyramiding(row["pine_source"], session_id=session_id),
            "fill_timing": settings.fill_timing,
            "position_epoch": _json_safe(position_epoch),
            "emit_from_bar_time": (
                None if emit_from_bar_time is None else _json_safe(emit_from_bar_time)
            ),
        },
        "oracle": {
            "ledger_net_at_death": str(_ledger_net(ledger)),
            "_how": "Σ(buy:+filled_quantity, sell:-filled_quantity), filled_at < deactivated_at",
            "engine_position_previous_tick": report.get("position_size"),
            "_engine_note": (
                "직전 tick 의 영속 보고서다. 사망 tick 자체의 상태는 영속되지 않는다."
            ),
        },
        "ledger_orders": fills,
        "ohlcv": ohlcv,
    }


async def _amain(args: argparse.Namespace) -> int:
    engine, session_maker = create_worker_engine_and_sm()
    out_dir = Path(args.out)
    written = 0
    try:
        async with session_maker() as session:
            rows = await _load_session(session, args.session)
            if not rows:
                print("대상 세션이 없다", file=sys.stderr)
                return 1
            for row in rows:
                fixture = await _build_fixture(session, row)
                path = out_dir / f"{fixture['session_prefix']}.json"
                path.write_text(json.dumps(fixture, indent=2, sort_keys=False) + "\n")
                print(
                    f"✓ {fixture['session_prefix']}  마지막봉={fixture['death_tick_last_bar_time']}"
                    f"  원장net={fixture['oracle']['ledger_net_at_death']}"
                    f"  엔진(직전tick)={fixture['oracle']['engine_position_previous_tick']}"
                    f"  → {path.relative_to(REPO_ROOT)}"
                )
                written += 1
    finally:
        await engine.dispose()
    print(f"\n{written} 건 기록")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", help="세션 id 앞 8자리로 좁힌다")
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "apps" / "api" / "tests" / "fixtures" / "bl595"),
        help="픽스처 출력 디렉터리",
    )
    args = parser.parse_args()
    Path(args.out).mkdir(parents=True, exist_ok=True)
    return asyncio.run(_amain(args))


if __name__ == "__main__":
    raise SystemExit(main())
