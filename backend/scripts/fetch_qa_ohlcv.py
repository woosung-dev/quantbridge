#!/usr/bin/env python
# Pine 배치 QA 용 실제 Bybit OHLCV 4 세트(2024·최근1년 × 1h·4h) 수집 + 검증 스크립트
"""Pine 코퍼스 배치 백테스트용 고정 OHLCV 데이터 수집.

배경 (2026-07-12 QA, docs/qa/2026-07-12-pine-batch-1h4h):
- 기존 `data/fixtures/ohlcv/BTCUSDT_1h.csv` 는 Sprint 4 합성 데이터 —
  8,760봉 중 ~77% 가 OHLC 불변식(high>=max(o,c), low<=min(o,c)) 위반.
  실제 전략 백테스트 결과가 무의미하고 stop 주문 fill 로직이 왜곡됨.
- 본 스크립트는 Bybit USDT-Perpetual 실데이터로 교체 + 4h/최근1년 세트 추가.

수집 세트 (모두 BTC/USDT:USDT):
- 2024 전체:   2024-01-01 ~ 2025-01-01 (exclusive) — 1h 8,784봉 / 4h 2,196봉 (윤년)
- 최근 1년:    2025-07-01 ~ 2026-07-01 (exclusive) — 1h 8,760봉 / 4h 2,190봉

출력 (FixtureProvider `{SYMBOL}_{TIMEFRAME}.csv` 규칙):
- data/fixtures/ohlcv/BTCUSDT_1h.csv          (기존 합성 파일 교체)
- data/fixtures/ohlcv/BTCUSDT_4h.csv          (신규)
- data/fixtures/ohlcv/BTCUSDT-RECENT_1h.csv   (신규)
- data/fixtures/ohlcv/BTCUSDT-RECENT_4h.csv   (신규)

검증 (실패 시 파일 미기록):
1. 봉수 정확 일치 + timestamp 단조증가 + 갭 없음
2. OHLC 불변식 위반 0건
3. 1h→4h pandas 리샘플 vs Bybit 4h 직접 수집 대조 (OHLC 일치, volume 오차 허용)
4. 2024 1~6월 구간 vs tests/fixtures/pine_corpus_v2/corpus_ohlcv_frozen.parquet 대조
   (기존 trust-layer 고정 데이터와 동일 소스임을 증명)

사용법::

    uv run python scripts/fetch_qa_ohlcv.py --confirm

`--confirm` 없이는 실행 거부 (generate_corpus_ohlcv_frozen.py 관례).
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

SYMBOL = "BTC/USDT:USDT"  # Bybit USDT-Perpetual (corpus frozen parquet 과 동일 소스)

PERIODS: dict[str, tuple[datetime, datetime]] = {
    "2024": (
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2025, 1, 1, tzinfo=UTC),  # exclusive
    ),
    "recent": (
        datetime(2025, 7, 1, tzinfo=UTC),
        datetime(2026, 7, 1, tzinfo=UTC),  # exclusive
    ),
}

TIMEFRAME_MS = {"1h": 3_600_000, "4h": 14_400_000}

FETCH_LIMIT = 1000
SLEEP_BETWEEN_REQUESTS_SECONDS = 0.25

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "data" / "fixtures" / "ohlcv"
FROZEN_PARQUET = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "pine_corpus_v2"
    / "corpus_ohlcv_frozen.parquet"
)

# (period key, timeframe) → 출력 파일명. RECENT 는 FixtureProvider 규칙상 별도 심볼로 취급.
OUTPUTS: dict[tuple[str, str], str] = {
    ("2024", "1h"): "BTCUSDT_1h.csv",
    ("2024", "4h"): "BTCUSDT_4h.csv",
    ("recent", "1h"): "BTCUSDT-RECENT_1h.csv",
    ("recent", "4h"): "BTCUSDT-RECENT_4h.csv",
}


def _fetch_ohlcv(exchange: Any, timeframe: str, since: datetime, until: datetime) -> pd.DataFrame:
    """Bybit klines 를 paginate 수집해 고정 스키마 DataFrame 으로 반환."""
    since_ms = int(since.timestamp() * 1000)
    until_ms = int(until.timestamp() * 1000)
    step_ms = TIMEFRAME_MS[timeframe]

    all_bars: list[list[Any]] = []
    cursor = since_ms
    while cursor < until_ms:
        bars = exchange.fetch_ohlcv(SYMBOL, timeframe=timeframe, since=cursor, limit=FETCH_LIMIT)
        if not bars:
            break
        all_bars.extend(b for b in bars if b[0] < until_ms)
        last_ts = bars[-1][0]
        if last_ts >= until_ms:
            break
        cursor = last_ts + step_ms
        time.sleep(SLEEP_BETWEEN_REQUESTS_SECONDS)

    df = pd.DataFrame(all_bars, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = (
        df.drop_duplicates(subset="timestamp", keep="first")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype("float64")
    return df


def _validate_basic(df: pd.DataFrame, timeframe: str, since: datetime, until: datetime) -> list[str]:
    """봉수/단조/갭/OHLC 불변식 검증. 위반 메시지 리스트 반환 (빈 리스트 = PASS)."""
    errors: list[str] = []
    step_ms = TIMEFRAME_MS[timeframe]
    expected = int((until - since).total_seconds() * 1000) // step_ms
    if len(df) != expected:
        errors.append(f"bar count {len(df)} != expected {expected}")
    if df["timestamp"].iloc[0] != since:
        errors.append(f"first ts {df['timestamp'].iloc[0]} != {since}")
    diffs = df["timestamp"].diff().dropna().dt.total_seconds() * 1000
    if not (diffs == step_ms).all():
        gap_count = int((diffs != step_ms).sum())
        errors.append(f"{gap_count} timestamp gaps (expected uniform {step_ms}ms)")
    high_bad = int((df["high"] < df[["open", "close"]].max(axis=1) - 1e-9).sum())
    low_bad = int((df["low"] > df[["open", "close"]].min(axis=1) + 1e-9).sum())
    if high_bad or low_bad:
        errors.append(f"OHLC invariant violations: high={high_bad} low={low_bad}")
    return errors


def _cross_check_resample(df_1h: pd.DataFrame, df_4h: pd.DataFrame) -> list[str]:
    """1h→4h 리샘플이 Bybit 4h 직접 수집과 일치하는지 대조."""
    errors: list[str] = []
    resampled = (
        df_1h.set_index("timestamp")
        .resample("4h", label="left", closed="left")
        .agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
        )
        .reset_index()
    )
    if len(resampled) != len(df_4h):
        return [f"resample length {len(resampled)} != fetched {len(df_4h)}"]
    for col, tol in (("open", 1e-6), ("high", 1e-6), ("low", 1e-6), ("close", 1e-6), ("volume", 1.0)):
        max_diff = float((resampled[col] - df_4h[col]).abs().max())
        if max_diff > tol:
            errors.append(f"resample vs fetched 4h: max|{col} diff|={max_diff} > {tol}")
    return errors


def _cross_check_frozen(df_1h_2024: pd.DataFrame) -> list[str]:
    """2024 1~6월 구간을 trust-layer frozen parquet 과 대조."""
    if not FROZEN_PARQUET.exists():
        return [f"frozen parquet missing: {FROZEN_PARQUET}"]
    frozen = pd.read_parquet(FROZEN_PARQUET)
    frozen["timestamp"] = pd.to_datetime(frozen["timestamp"], utc=True)
    merged = df_1h_2024.merge(frozen, on="timestamp", suffixes=("_new", "_fz"))
    if len(merged) != len(frozen):
        return [f"frozen overlap {len(merged)} != frozen rows {len(frozen)}"]
    errors: list[str] = []
    for col in ("open", "high", "low", "close", "volume"):
        max_diff = float((merged[f"{col}_new"] - merged[f"{col}_fz"]).abs().max())
        if max_diff > 1e-6:
            errors.append(f"frozen parquet mismatch: max|{col} diff|={max_diff}")
    return errors


def _write_csv(df: pd.DataFrame, path: Path) -> str:
    """FixtureProvider 스키마(ISO-Z timestamp) 로 CSV 기록 후 sha256 반환."""
    out = df.copy()
    out["timestamp"] = out["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False)
    hasher = hashlib.sha256()
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch real Bybit OHLCV sets for Pine batch QA.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="필수. 네트워크 API 호출 + fixture 파일 덮어쓰기를 의도했음을 명시.",
    )
    args = parser.parse_args()

    if not args.confirm:
        sys.stderr.write(
            "ERROR: --confirm 플래그가 필요합니다.\n"
            "이 스크립트는 외부 API 호출 + BTCUSDT_1h.csv 교체를 수행합니다.\n"
            "사용법: uv run python scripts/fetch_qa_ohlcv.py --confirm\n"
        )
        return 1

    import ccxt

    exchange = ccxt.bybit({"options": {"defaultType": "linear"}})

    frames: dict[tuple[str, str], pd.DataFrame] = {}
    failures: list[str] = []

    for period_key, (since, until) in PERIODS.items():
        for timeframe in ("1h", "4h"):
            print(f"[fetch] {SYMBOL} {timeframe} {since:%Y-%m-%d} ~ {until:%Y-%m-%d} ({period_key})")
            df = _fetch_ohlcv(exchange, timeframe, since, until)
            print(f"        → {len(df)} bars")
            errors = _validate_basic(df, timeframe, since, until)
            for e in errors:
                failures.append(f"{period_key}/{timeframe}: {e}")
            frames[(period_key, timeframe)] = df

    print("[check] 1h→4h resample cross-check")
    for period_key in PERIODS:
        for e in _cross_check_resample(frames[(period_key, "1h")], frames[(period_key, "4h")]):
            failures.append(f"{period_key}: {e}")

    print("[check] 2024 Jan-Jun vs corpus_ohlcv_frozen.parquet")
    for e in _cross_check_frozen(frames[("2024", "1h")]):
        failures.append(f"2024/frozen: {e}")

    if failures:
        sys.stderr.write("VALIDATION FAILED — 파일 미기록:\n")
        for f in failures:
            sys.stderr.write(f"  - {f}\n")
        return 1

    print("[write] all validations passed")
    for key, filename in OUTPUTS.items():
        path = FIXTURE_DIR / filename
        digest = _write_csv(frames[key], path)
        print(f"        {filename}: {len(frames[key])} bars, sha256={digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
