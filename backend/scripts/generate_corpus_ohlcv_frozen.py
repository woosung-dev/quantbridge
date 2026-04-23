#!/usr/bin/env python
"""Path β Trust Layer CI — P-3 Execution Golden 을 위한 고정 OHLCV 데이터 생성.

ADR-013 §4.3 명세:
- BTCUSDT 1h, 2024-01-01 00:00:00 UTC ~ 2024-06-30 23:00:00 UTC (~4,320 bars)
- Bybit public klines API (무인증)
- 출력: `backend/tests/fixtures/pine_corpus_v2/corpus_ohlcv_frozen.parquet`
- sha256 hex 를 stdout 으로 출력 — baseline_metrics.json 의 `ohlcv_sha256` 에 기록

사용법::

    uv run python scripts/generate_corpus_ohlcv_frozen.py --confirm

`--confirm` 플래그 없이는 실행 거부 (opus Gate-1 W-1 방지 정신 연장).
재현성: 동일 날짜 범위 → 동일 bar 집합 (Bybit 서버의 historical 불변 전제).

환경 요구:
- ccxt >= 4.5
- pandas >= 2.0
- pyarrow (parquet)
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

# Symbol / timeframe / date range (ADR-013 §4.3 고정)
SYMBOL = "BTC/USDT:USDT"  # Bybit USDT-Perpetual
TIMEFRAME = "1h"
SINCE_UTC = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
UNTIL_UTC = datetime(2024, 7, 1, 0, 0, 0, tzinfo=UTC)  # exclusive

# Bybit API 한번에 가져올 수 있는 최대 kline 수
FETCH_LIMIT = 1000
# 속도 제한 보호
SLEEP_BETWEEN_REQUESTS_SECONDS = 0.25

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "pine_corpus_v2"
OUTPUT_PATH = FIXTURE_DIR / "corpus_ohlcv_frozen.parquet"


def _fetch_ohlcv_bybit() -> list[list[Any]]:
    """Bybit spot public klines 를 paginate 로 수집.

    ccxt 는 opt-in dependency — 이 스크립트 실행 시 설치된 환경에서만 import.
    """
    import ccxt

    exchange = ccxt.bybit({"options": {"defaultType": "linear"}})
    since_ms = int(SINCE_UTC.timestamp() * 1000)
    until_ms = int(UNTIL_UTC.timestamp() * 1000)

    all_bars: list[list[Any]] = []
    cursor = since_ms
    while cursor < until_ms:
        bars = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, since=cursor, limit=FETCH_LIMIT)
        if not bars:
            break
        # bars: [[timestamp, open, high, low, close, volume], ...]
        # 마지막 bar 가 until_ms 를 넘으면 자르기
        bars_in_range = [b for b in bars if b[0] < until_ms]
        all_bars.extend(bars_in_range)
        last_ts = bars[-1][0]
        if last_ts >= until_ms:
            break
        # 다음 요청의 since 는 마지막 timestamp + 1h (중복 방지)
        cursor = last_ts + 60 * 60 * 1000
        time.sleep(SLEEP_BETWEEN_REQUESTS_SECONDS)
    return all_bars


def _to_dataframe(bars: list[list[Any]]) -> pd.DataFrame:
    """OHLCV bars 를 고정 스키마 DataFrame 으로 변환."""
    df = pd.DataFrame(bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = (
        df.drop_duplicates(subset="timestamp", keep="first")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    # float 직렬화는 parquet 에서 자동 처리 — Decimal 변환은 baseline 생성 시점에 수행
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype("float64")
    return df


def _file_sha256(path: Path) -> str:
    """parquet 파일의 sha256 hex."""
    hasher = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate fixed BTCUSDT 1h OHLCV for Path β P-3.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="필수. 네트워크 API 호출 + fixture 파일 덮어쓰기를 의도했음을 명시.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help=f"출력 parquet 경로. 기본: {OUTPUT_PATH.relative_to(Path.cwd()) if OUTPUT_PATH.is_relative_to(Path.cwd()) else OUTPUT_PATH}",
    )
    args = parser.parse_args()

    if not args.confirm:
        sys.stderr.write(
            "ERROR: --confirm 플래그가 필요합니다.\n"
            "이 스크립트는 외부 API 호출 + fixture 덮어쓰기를 수행하므로 의도된 실행임을 명시해야 합니다.\n"
            "사용법: uv run python scripts/generate_corpus_ohlcv_frozen.py --confirm\n"
        )
        return 1

    print(
        f"[1/4] Fetching {SYMBOL} {TIMEFRAME} {SINCE_UTC:%Y-%m-%d} ~ {UNTIL_UTC:%Y-%m-%d} from Bybit..."
    )
    bars = _fetch_ohlcv_bybit()
    print(f"      → {len(bars)} bars")

    print("[2/4] Normalizing to DataFrame...")
    df = _to_dataframe(bars)
    expected_hours = int((UNTIL_UTC - SINCE_UTC).total_seconds() // 3600)
    print(f"      → {len(df)} unique bars (expected ~{expected_hours})")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"[3/4] Writing parquet to {args.output}")
    df.to_parquet(args.output, engine="pyarrow", compression="snappy", index=False)

    digest = _file_sha256(args.output)
    print(f"[4/4] sha256 = {digest}")
    print()
    print("이 해시를 baseline_metrics.json 의 `ohlcv_sha256` 필드에 기록하세요.")
    print("그 후 `scripts/regen_trust_layer_baseline.py --confirm` 으로 baseline 재생성.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
