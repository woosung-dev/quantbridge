"""BTC 부모봉·1분봉·관측 펀딩을 페이지 체크포인트로 동결한다."""

from __future__ import annotations

import gzip
import json
from decimal import Decimal
from pathlib import Path

import pandas as pd
from tools.research.data import public_api, validate_candles, validate_funding
from tools.research.editor_picks.common import (
    TIMEFRAMES,
    checked_file,
    immutable,
    lock,
    now,
    read,
    sha,
    write,
)


def candle_pages(
    root: Path, interval: str, start: pd.Timestamp, end: pd.Timestamp
) -> list:
    request = {
        "symbol": "BTCUSDT",
        "interval": interval,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
    immutable(root / "request.json", request)
    cursor, start_ms = int(end.timestamp() * 1000) - 1, int(start.timestamp() * 1000)
    rows = {}
    while cursor >= start_ms:
        path = root / f"{cursor}.json.gz"
        if path.exists():
            page = json.loads(gzip.decompress(path.read_bytes()))
        else:
            result = public_api(
                "kline",
                category="linear",
                symbol="BTCUSDT",
                interval=interval,
                start=start_ms,
                end=cursor,
                limit=1000,
            )
            if result.get("symbol") != "BTCUSDT":
                raise ValueError("다른 심볼의 시세입니다")
            page = result["list"]
            path.write_bytes(gzip.compress(json.dumps(page).encode(), mtime=0))
        if not page:
            raise ValueError("요청 기간을 채우기 전에 시세 페이지가 비었습니다")
        for row in page:
            timestamp = int(row[0])
            if not start_ms <= timestamp <= cursor or timestamp in rows:
                raise ValueError("페이지 시각 범위 또는 중복 봉 오류")
            rows[timestamp] = row
        next_cursor = min(int(row[0]) for row in page) - 1
        if next_cursor >= cursor:
            raise ValueError("시세 페이지가 진전되지 않습니다")
        cursor = next_cursor
    return [rows[key] for key in sorted(rows)]


def frame(rows: list) -> pd.DataFrame:
    return pd.DataFrame(
        [row[1:6] for row in rows],
        columns=["open", "high", "low", "close", "volume"],
        index=pd.to_datetime([int(row[0]) for row in rows], unit="ms", utc=True),
    )


def validate_minutes(
    data: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp
) -> None:
    expected = pd.date_range(start, end, freq="1min", inclusive="left")
    if not data.index.equals(expected):
        raise ValueError("1분봉 누락·중복·기간 불일치")
    numeric = data.map(lambda x: Decimal(str(x)))
    if not numeric.map(lambda x: x.is_finite()).all().all():
        raise ValueError("비유한 1분봉 가격")
    if (
        (numeric[["open", "high", "low", "close"]] <= 0).any().any()
        or (numeric["volume"] < 0).any()
        or (numeric["high"] < numeric[["open", "close", "low"]].max(axis=1)).any()
        or (numeric["low"] > numeric[["open", "close", "high"]].min(axis=1)).any()
    ):
        raise ValueError("1분봉 가격·수량 불변식 위반")


def aggregate_minutes(data: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    freq = {"1h": "1h", "4h": "4h", "1d": "1D"}[timeframe]
    numeric = data.map(lambda x: Decimal(str(x)))
    return numeric.resample(freq).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )


def freeze(root: Path, end: pd.Timestamp, warmup: int = 1000) -> dict:
    if (
        end.tz is None
        or str(end.tz) != "UTC"
        or end != end.floor("1D")
        or end > pd.Timestamp.now(tz="UTC").floor("1D")
        or not 200 <= warmup <= 10000
    ):
        raise ValueError("확정 UTC 일봉 경계와 200~10000 준비봉이 필요합니다")
    folder = root / "data"
    request = {
        "end": end.isoformat(),
        "months": 24,
        "warmup": warmup,
        "symbol": "BTCUSDT",
    }
    with lock(folder / ".lock"):
        immutable(folder / "request.json", request)
        if (folder / "dataset.json").exists():
            return validate(root)
        start = end - pd.DateOffset(months=24)
        files = {}
        frequencies = {"1h": ("60", "1h"), "4h": ("240", "4h"), "1d": ("D", "1D")}
        for timeframe, (interval, freq) in frequencies.items():
            first = start - warmup * pd.Timedelta(freq)
            data = frame(
                candle_pages(folder / "pages" / timeframe, interval, first, end)
            )
            validate_candles(data, timeframe, first, end)
            path = folder / f"{timeframe}.csv.gz"
            data.to_csv(path, index_label="timestamp", compression="gzip")
            files[timeframe] = {"path": path.name, "sha256": sha(path.read_bytes())}
        minutes = frame(candle_pages(folder / "pages" / "1min", "1", start, end))
        validate_minutes(minutes, start, end)
        minutes.to_csv(
            folder / "1min.csv.gz", index_label="timestamp", compression="gzip"
        )
        files["1min"] = {
            "path": "1min.csv.gz",
            "sha256": sha((folder / "1min.csv.gz").read_bytes()),
        }
        # 펀딩은 응답 페이지를 그대로 보존하며 현재 간격을 과거에 적용한 가정도 기록한다.
        instrument = public_api(
            "instruments-info", category="linear", symbol="BTCUSDT"
        )["list"]
        if (
            len(instrument) != 1
            or instrument[0]["symbol"] != "BTCUSDT"
            or instrument[0]["contractType"] != "LinearPerpetual"
        ):
            raise ValueError("BTC USDT 무기한 상품 확인 실패")
        cursor, rows = int(end.timestamp() * 1000) - 1, {}
        while cursor >= int(start.timestamp() * 1000):
            path = folder / "pages" / f"funding-{cursor}.json"
            if path.exists():
                page = read(path)
            else:
                page = public_api(
                    "funding/history",
                    category="linear",
                    symbol="BTCUSDT",
                    startTime=int(start.timestamp() * 1000),
                    endTime=cursor,
                    limit=200,
                )["list"]
                write(path, page)
            if not page:
                break
            for row in page:
                ts = int(row["fundingRateTimestamp"])
                if row["symbol"] != "BTCUSDT" or ts in rows or ts > cursor:
                    raise ValueError("펀딩 심볼·중복·시각 오류")
                rows[ts] = row["fundingRate"]
            cursor = min(int(row["fundingRateTimestamp"]) for row in page) - 1
        funding = pd.Series(
            [rows[k] for k in sorted(rows)],
            index=pd.to_datetime(sorted(rows), unit="ms", utc=True),
        )
        interval = int(instrument[0]["fundingInterval"])
        validate_funding(funding, start, end, interval)
        pd.DataFrame({"timestamp": funding.index, "rate": funding.tolist()}).to_csv(
            folder / "funding.csv", index=False
        )
        files["funding"] = {
            "path": "funding.csv",
            "sha256": sha((folder / "funding.csv").read_bytes()),
        }
        manifest = {
            "schema_version": 1,
            **request,
            "start": start.isoformat(),
            "files": files,
            "funding_interval_minutes": interval,
            "observed_at": now(),
            "funding_status": "observed_settlements_only",
            "historical_schedule_independently_verified": False,
            "holdout_status": "retrospective_not_untouched",
        }
        write(folder / "dataset.json", manifest)
        return validate(root)


def validate(root: Path) -> dict:
    from tools.research.data import load_candles, load_funding

    folder = root / "data"
    manifest = read(folder / "dataset.json")
    if manifest["schema_version"] != 1 or manifest["symbol"] != "BTCUSDT":
        raise ValueError("다른 동결 시세 계약입니다")
    paths = {
        key: checked_file(folder, item["path"], item["sha256"])
        for key, item in manifest["files"].items()
    }
    start, end = pd.Timestamp(manifest["start"]), pd.Timestamp(manifest["end"])
    minutes = load_candles(paths["1min"])
    validate_minutes(minutes, start, end)
    for timeframe in TIMEFRAMES:
        data = load_candles(paths[timeframe])
        freq = {"1h": "1h", "4h": "4h", "1d": "1D"}[timeframe]
        validate_candles(
            data, timeframe, start - manifest["warmup"] * pd.Timedelta(freq), end
        )
        rebuilt = aggregate_minutes(minutes, timeframe)
        expected = data.loc[(data.index >= start) & (data.index < end)].map(
            lambda x: Decimal(str(x))
        )
        if not rebuilt[["open", "high", "low", "close"]].equals(
            expected[["open", "high", "low", "close"]]
        ):
            raise ValueError(f"1분봉 재집계와 {timeframe} 부모 OHLC가 다릅니다")
    validate_funding(
        load_funding(paths["funding"]), start, end, manifest["funding_interval_minutes"]
    )
    return manifest
