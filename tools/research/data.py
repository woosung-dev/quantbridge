"""Bybit 공개 linear 시세를 DB 없이 동결하고 정확한 봉·펀딩 누락을 차단한다."""

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd

from tools.research.sources import read_url

ASSETS = ("BTCUSDT", "ETHUSDT")
TIMEFRAMES = {"1h": ("60", "1h"), "4h": ("240", "4h"), "1d": ("D", "1D")}


def json_write(path: Path, value: dict | list) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def public_api(endpoint: str, **params) -> dict:
    payload = json.loads(
        read_url(
            "https://api.bybit.com/v5/market/" + endpoint + "?" + urlencode(params)
        )
    )
    if payload.get("retCode") != 0:
        raise ValueError(
            f"Bybit {endpoint}: {payload.get('retCode')} {payload.get('retMsg')}"
        )
    result = payload["result"]
    if params.get("category") != result.get("category"):
        raise ValueError("Bybit가 다른 상품 유형을 반환했습니다")
    time.sleep(0.06)
    return result


def fetch_candles(
    symbol: str, timeframe: str, start: pd.Timestamp, end: pd.Timestamp
) -> list:
    rows = {}
    cursor = int(end.timestamp() * 1000) - 1
    start_ms = int(start.timestamp() * 1000)
    while cursor >= start_ms:
        payload = public_api(
            "kline",
            category="linear",
            symbol=symbol,
            interval=TIMEFRAMES[timeframe][0],
            start=start_ms,
            end=cursor,
            limit=1000,
        )
        if payload.get("symbol") != symbol:
            raise ValueError("Bybit가 다른 symbol을 반환했습니다")
        page = payload["list"]
        if not page:
            break
        for row in page:
            timestamp = int(row[0])
            if timestamp in rows:
                raise ValueError("페이지 간 중복 봉")
            rows[timestamp] = row
        next_cursor = min(int(row[0]) for row in page) - 1
        if next_cursor >= cursor:
            raise ValueError("Bybit pagination이 진전되지 않습니다")
        cursor = next_cursor
    return [rows[key] for key in sorted(rows)]


def fetch_funding(symbol: str, start: pd.Timestamp, end: pd.Timestamp) -> list:
    rows = {}
    cursor = int(end.timestamp() * 1000) - 1
    start_ms = int(start.timestamp() * 1000)
    while cursor >= start_ms:
        page = public_api(
            "funding/history",
            category="linear",
            symbol=symbol,
            startTime=start_ms,
            endTime=cursor,
            limit=200,
        )["list"]
        if not page:
            break
        for row in page:
            if row["symbol"] != symbol:
                raise ValueError("다른 상품의 펀딩")
            timestamp = int(row["fundingRateTimestamp"])
            if timestamp in rows:
                raise ValueError("페이지 간 중복 펀딩")
            rows[timestamp] = row
        next_cursor = min(int(row["fundingRateTimestamp"]) for row in page) - 1
        if next_cursor >= cursor:
            raise ValueError("Bybit funding pagination이 진전되지 않습니다")
        cursor = next_cursor
    return [rows[key] for key in sorted(rows)]


def validate_candles(
    frame: pd.DataFrame, timeframe: str, start: pd.Timestamp, end: pd.Timestamp
) -> None:
    expected = pd.date_range(
        start, end, freq=TIMEFRAMES[timeframe][1], inclusive="left"
    )
    if not frame.index.equals(expected):
        raise ValueError(
            f"봉 누락·중복·순서·기간 불일치: 요청 {len(expected)}봉 / 실제 {len(frame)}봉"
        )
    numeric = frame.astype(float)
    if not numeric.map(lambda x: pd.notna(x) and abs(x) != float("inf")).all().all():
        raise ValueError("유효하지 않은 OHLCV 숫자")
    if (
        (numeric[["open", "high", "low", "close"]] <= 0).any().any()
        or (numeric["volume"] < 0).any()
        or (numeric["high"] < numeric[["open", "close", "low"]].max(axis=1)).any()
        or (numeric["low"] > numeric[["open", "close", "high"]].min(axis=1)).any()
    ):
        raise ValueError("OHLCV 가격·거래량 불변식 위반")


def validate_funding(
    series: pd.Series, start: pd.Timestamp, end: pd.Timestamp, interval_minutes: int
) -> None:
    frequency = f"{interval_minutes}min"
    expected = pd.date_range(
        start.ceil(frequency), end, freq=frequency, inclusive="left"
    )
    if not series.index.equals(expected):
        raise ValueError(
            f"펀딩 정산 누락·중복·시간 불일치: 요청 {len(expected)}회 / 실제 {len(series)}회; 과거 주기 변경은 별도 확인 필요"
        )
    values = series.astype(float)
    if not values.map(lambda x: pd.notna(x) and abs(x) != float("inf")).all():
        raise ValueError("유효하지 않은 펀딩 값")


def load_candles(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str)
    frame.index = pd.DatetimeIndex(pd.to_datetime(frame.pop("timestamp"), utc=True))
    frame.index.name = None
    return frame


def load_funding(path: Path) -> pd.Series:
    frame = pd.read_csv(path, dtype=str)
    return pd.Series(
        frame["rate"].tolist(),
        index=pd.DatetimeIndex(pd.to_datetime(frame["timestamp"], utc=True)),
    )


def freeze(root: Path, end: pd.Timestamp, months: int = 24) -> dict:
    if (
        months < 24
        or end != end.floor("1D")
        or end > pd.Timestamp.now(tz="UTC").floor("1D")
    ):
        raise ValueError("최소 24개월·UTC 자정·마감된 데이터만 동결할 수 있습니다")
    if (root / "dataset.json").exists():
        raise ValueError("이미 동결된 데이터입니다. 새 디렉터리를 사용하세요")
    root.mkdir(parents=True, exist_ok=True)
    holdout_start = end - pd.DateOffset(months=6)
    manifest = {
        "schema_version": 1,
        "collection_started_at": datetime.now(UTC).isoformat(),
        "exchange": "bybit",
        "category": "linear",
        "quote": "USDT",
        "start": str(end - pd.DateOffset(months=months)),
        "end_exclusive": str(end),
        "holdout_start": str(holdout_start),
        "warmup_bars": 200,
        "holdout_access": "CLI champion-only; 로컬 파일은 암호화하지 않음",
        "holdout_status": "retrospective_not_untouched",
        "preregistration_status": "not_independently_verified",
        "funding_status": "observed_settlements_only",
        "historical_schedule_assumption": "현재 instruments-info fundingInterval을 과거에도 적용한 grid 검사; 과거 전체 일정의 독립 증거가 아님",
        "funding_interval_policy": "동결 시 instruments-info 정산 간격의 완전한 grid를 요구; 과거 주기 변경이면 차단",
        "files": [],
        "funding": {},
    }
    oldest = end - pd.DateOffset(months=months) - pd.Timedelta(days=200)
    for symbol in ASSETS:
        instrument = public_api("instruments-info", category="linear", symbol=symbol)[
            "list"
        ]
        if (
            len(instrument) != 1
            or instrument[0].get("contractType") != "LinearPerpetual"
            or instrument[0].get("quoteCoin") != "USDT"
        ):
            raise ValueError("Bybit USDT linear perpetual 상품 확인 실패")
        interval = int(instrument[0]["fundingInterval"])
        fund_rows = fetch_funding(symbol, oldest, end)
        funding = pd.Series(
            [r["fundingRate"] for r in fund_rows],
            index=pd.to_datetime(
                [int(r["fundingRateTimestamp"]) for r in fund_rows], unit="ms", utc=True
            ),
        )
        validate_funding(funding, oldest, end, interval)
        fund_path = root / f"{symbol}-funding.csv"
        pd.DataFrame({"timestamp": funding.index, "rate": funding.tolist()}).to_csv(
            fund_path, index=False
        )
        manifest["funding"][symbol] = {
            "path": fund_path.name,
            "sha256": digest(fund_path),
            "interval_minutes": interval,
            "count": len(funding),
            "source": "https://api.bybit.com/v5/market/funding/history",
            "observed_at": datetime.now(UTC).isoformat(),
            "instrument": {
                key: instrument[0].get(key)
                for key in ("symbol", "contractType", "quoteCoin", "fundingInterval")
            },
        }
        for timeframe in TIMEFRAMES:
            frequency = TIMEFRAMES[timeframe][1]
            start = (
                end - pd.DateOffset(months=months) - 200 * pd.Timedelta(frequency)
            ).floor(frequency)
            candles = fetch_candles(symbol, timeframe, start, end)
            frame = pd.DataFrame(
                [row[1:6] for row in candles],
                columns=["open", "high", "low", "close", "volume"],
                index=pd.to_datetime(
                    [int(row[0]) for row in candles], unit="ms", utc=True
                ),
            )
            validate_candles(frame, timeframe, start, end)
            file_path = root / f"{symbol}-{timeframe}.csv"
            frame.to_csv(file_path, index_label="timestamp")
            manifest["files"].append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "path": file_path.name,
                    "sha256": digest(file_path),
                    "start": str(start),
                    "end_exclusive": str(end),
                    "bars": len(frame),
                    "source": "https://api.bybit.com/v5/market/kline",
                    "observed_at": datetime.now(UTC).isoformat(),
                }
            )
            print(f"동결: {symbol} {timeframe} {len(frame)}봉", flush=True)
    json_write(root / "dataset.json", manifest)
    return manifest
