"""고정 OHLCV CSV 생성기.

BTCUSDT 현물 1H 2025-04-18 ~ 2026-04-17 (1년치 약 8,760 bars)를 CCXT Binance에서 수집하여
재현 가능한 CSV로 저장한다. 여러 엔진(E1 PyneCore, E4~E7 LLM 변환본)이 동일 입력을 공유하기 위함.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

import ccxt
import pandas as pd

SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
START_UTC = datetime(2025, 4, 18, 0, 0, tzinfo=timezone.utc)
END_UTC = datetime(2026, 4, 17, 23, 0, tzinfo=timezone.utc)
OUT_PATH = Path(__file__).resolve().parents[1] / "ohlcv" / "btc_usdt_1h_frozen.csv"
SHA_PATH = OUT_PATH.with_suffix(".sha256")


def fetch_all() -> pd.DataFrame:
    exchange = ccxt.binance({"enableRateLimit": True})
    since_ms = int(START_UTC.timestamp() * 1000)
    end_ms = int(END_UTC.timestamp() * 1000)
    limit = 1000

    all_rows: list[list[float]] = []
    cursor = since_ms
    while cursor <= end_ms:
        batch = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, since=cursor, limit=limit)
        if not batch:
            break
        all_rows.extend(batch)
        last_ts = batch[-1][0]
        if last_ts <= cursor:
            break
        cursor = last_ts + 60 * 60 * 1000
        time.sleep(exchange.rateLimit / 1000)

    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    df = df[(df["timestamp"] >= since_ms) & (df["timestamp"] <= end_ms)]
    df["datetime_utc"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = fetch_all()
    df.to_csv(OUT_PATH, index=False)
    sha = hashlib.sha256(OUT_PATH.read_bytes()).hexdigest()
    SHA_PATH.write_text(sha + "\n")
    print(f"rows={len(df)} first={df['datetime_utc'].iloc[0]} last={df['datetime_utc'].iloc[-1]}")
    print(f"out={OUT_PATH}")
    print(f"sha256={sha}")


if __name__ == "__main__":
    main()
