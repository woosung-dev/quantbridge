"""공개 Bybit 페이지와 검증된 이전 시세로 고정 5기간을 별도 동결한다."""

from __future__ import annotations

import csv
import gzip
import io
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from tools.research.data import load_candles, load_funding, public_api
from tools.research.period_study.schema import PERIODS, TIMEFRAMES
from tools.research.period_study.state import checked, immutable, now, read, sha, write

FIELDS = ("timestamp", "open", "high", "low", "close", "volume")


def milliseconds(value: str) -> int:
    return int(datetime.fromisoformat(value).timestamp() * 1000)


def timestamp(value: int) -> str:
    return datetime.fromtimestamp(value // 1000, UTC).isoformat()


def validate_row(row: list[str]) -> None:
    prices = [Decimal(value) for value in row[1:6]]
    if len(prices) != 5 or not all(value.is_finite() for value in prices):
        raise ValueError("유한한 OHLCV 5개가 필요합니다")
    open_, high, low, close, volume = prices
    if min(open_, high, low, close) <= 0 or volume < 0:
        raise ValueError("OHLCV 가격·거래량 부호 위반")
    if high < max(open_, low, close) or low > min(open_, high, close):
        raise ValueError("OHLC 가격 범위 위반")


def seed_rows(path: Path | None, start: int, end: int, *, funding=False) -> dict:
    rows = {}
    if path is None:
        return rows
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="") as stream:
        reader = csv.DictReader(stream)
        for value in reader:
            when = milliseconds(value["timestamp"])
            if start <= when < end:
                if when in rows:
                    raise ValueError("재사용 데이터에 중복 시각이 있습니다")
                rows[when] = (
                    [str(when), value["rate"]]
                    if funding else [str(when), *[value[name] for name in FIELDS[1:]]]
                )
    return rows


def missing_ranges(start: int, end: int, width: int, rows: dict) -> list[tuple[int, int]]:
    result, left = [], None
    for when in range(start, end, width):
        if when not in rows and left is None:
            left = when
        elif when in rows and left is not None:
            result.append((left, when))
            left = None
    if left is not None:
        result.append((left, end))
    return result


def page_rows(root: Path, interval: str, start: int, end: int, *, funding=False) -> dict:
    rows, cursor = {}, end - 1
    while cursor >= start:
        request = {"category": "linear", "symbol": "BTCUSDT"}
        if funding:
            request.update(startTime=start, endTime=cursor, limit=200)
        else:
            request.update(interval=interval, start=start, end=cursor, limit=1000)
        path = root / "pages" / interval / f"{start}-{cursor}.json.gz"
        if path.exists():
            cached = read(path)
            if cached["request"] != request:
                raise ValueError("공개 페이지 캐시의 요청이 다릅니다")
            page = cached["rows"]
        else:
            endpoint = "funding/history" if funding else "kline"
            response = public_api(endpoint, **request)
            if not funding and response.get("symbol") != "BTCUSDT":
                raise ValueError("다른 심볼의 시세 응답입니다")
            page = response["list"]
            write(path, {"request": request, "rows": page, "observed_at": now()})
        if not page:
            raise ValueError(f"요청 구간을 채우기 전에 {interval} 페이지가 비었습니다")
        for value in page:
            when = int(value["fundingRateTimestamp"] if funding else value[0])
            if not start <= when <= cursor or when in rows:
                raise ValueError("공개 페이지 시각·중복 위반")
            if funding:
                if value["symbol"] != "BTCUSDT":
                    raise ValueError("다른 심볼의 펀딩입니다")
                rows[when] = [str(when), value["fundingRate"]]
            else:
                rows[when] = value[:6]
        next_cursor = min(int(row[0]) for row in rows.values()) - 1
        if next_cursor >= cursor:
            raise ValueError("공개 API 페이지가 진전되지 않습니다")
        cursor = next_cursor
        write(root / "progress.json", {
            "status": "fetching", "interval": interval, "cursor": timestamp(cursor + 1),
            "range_start": timestamp(start), "range_end_exclusive": timestamp(end),
            "pages_cached": len(list((root / "pages" / interval).glob("*.gz"))),
            "last_normal_at": now(),
        })
    return rows


def csv_bytes(rows: dict, *, funding=False) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(("timestamp", "rate") if funding else FIELDS)
    for when, row in sorted(rows.items()):
        writer.writerow([timestamp(when), *row[1:]])
    return gzip.compress(stream.getvalue().encode(), mtime=0)


def freeze(root: Path, *, warmup_bars: int = 1000, seed_dir: Path | None = None) -> dict:
    if not 2 <= warmup_bars <= 10000:
        raise ValueError("준비봉은 2~10000 범위여야 합니다")
    root.mkdir(parents=True, exist_ok=True)
    immutable(root / "request.json", {
        "schema_version": 1, "symbol": "BTCUSDT", "category": "linear",
        "warmup_bars": warmup_bars,
        "periods": [period.__dict__ for period in PERIODS],
    })
    seeds = {}
    if seed_dir:
        previous = read(seed_dir / "dataset.json")
        if previous.get("symbol") != "BTCUSDT":
            raise ValueError("재사용 시세는 BTCUSDT여야 합니다")
        for key, value in previous["files"].items():
            seeds[key] = checked(seed_dir, value["path"], value["sha256"])
    instrument = public_api("instruments-info", category="linear", symbol="BTCUSDT")["list"]
    if len(instrument) != 1 or instrument[0].get("contractType") != "LinearPerpetual":
        raise ValueError("Bybit BTCUSDT 무기한 상품을 확인할 수 없습니다")
    interval_minutes = int(instrument[0]["fundingInterval"])
    # 현재 간격은 누락 검출용 가정이며 과거 일정의 독립 검증으로 표시하지 않는다.
    manifest = {
        "schema_version": 1, "symbol": "BTCUSDT", "warmup_bars": warmup_bars,
        "funding_status": "observed_settlements_only",
        "historical_schedule_independently_verified": False,
        "funding_grid_assumption_minutes": interval_minutes,
        "files": {}, "seed_dataset_sha256": sha((seed_dir / "dataset.json").read_bytes()) if seed_dir else None,
    }
    for period in PERIODS:
        start, end = milliseconds(period.start), milliseconds(period.end_exclusive)
        manifest["files"][period.id] = {}
        specs = [(name, code, minutes, False) for name, (code, minutes) in TIMEFRAMES.items()]
        specs += [("1min", "1", 1, False), ("funding", "funding", interval_minutes, True)]
        for name, code, minutes, funding in specs:
            width = minutes * 60_000
            first = start - warmup_bars * width if name in TIMEFRAMES else start
            path = root / period.id / f"{name}.csv.gz"
            receipt_path = root / period.id / f"{name}.json"
            if receipt_path.exists():
                record = read(receipt_path)
                checked(root, record["path"], record["sha256"])
                if (record["start"], record["end_exclusive"]) != (timestamp(first), timestamp(end)):
                    raise ValueError("완료 시세 파일의 경계가 다릅니다")
            else:
                rows = seed_rows(seeds.get(name), first, end, funding=funding)
                reused = len(rows)
                for left, right in missing_ranges(first, end, width, rows):
                    for when, row in page_rows(root, code, left, right, funding=funding).items():
                        if when in rows:
                            raise ValueError("재사용·신규 공개 시세가 중복됩니다")
                        rows[when] = row
                expected = range(first, end, width)
                if sorted(rows) != list(expected):
                    raise ValueError(f"{period.id}/{name} 정확한 시각 grid가 아닙니다")
                for row in rows.values():
                    if funding:
                        if not Decimal(row[1]).is_finite():
                            raise ValueError("비유한 펀딩입니다")
                    else:
                        validate_row(row)
                content = csv_bytes(rows, funding=funding)
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(".tmp")
                temporary.write_bytes(content)
                temporary.replace(path)
                record = {
                    "path": str(path.relative_to(root)), "sha256": sha(content), "rows": len(rows),
                    "start": timestamp(first), "end_exclusive": timestamp(end),
                    "evaluation_start": period.start, "evaluation_end_exclusive": period.end_exclusive,
                    "seed_rows": reused, "new_public_rows": len(rows) - reused, "validated_at": now(),
                }
                write(receipt_path, record)
                print(f"data {period.id}/{name}: {len(rows)} rows; seed={reused}", flush=True)
            manifest["files"][period.id][name] = record
            write(root / "partial-dataset.json", manifest)
    write(root / "dataset.json", manifest)
    write(root / "progress.json", {"status": "completed", "last_normal_at": now(), "files": 25})
    return manifest


def load_period(root: Path, period_id: str, timeframe: str, warmup_bars: int):
    manifest = read(root / "dataset.json")
    period = next(value for value in PERIODS if value.id == period_id)
    record = dict(manifest["files"][period_id])
    if warmup_bars > manifest["warmup_bars"]:
        extension = root / "extensions" / period_id / f"{timeframe}-{warmup_bars}.json"
        if not extension.exists():
            raise ValueError(f"warmup_extension_missing:{period_id}/{timeframe}/{warmup_bars}")
        record[timeframe] = read(extension)
    parent = load_candles(checked(root, record[timeframe]["path"], record[timeframe]["sha256"]))
    width = timedelta(minutes=TIMEFRAMES[timeframe][1])
    parent = parent.loc[datetime.fromisoformat(period.start) - warmup_bars * width:]
    execution = load_candles(checked(root, record["1min"]["path"], record["1min"]["sha256"]))
    funding = load_funding(checked(root, record["funding"]["path"], record["funding"]["sha256"]))
    return parent, execution, funding, record


def extend(root: Path, period_id: str, timeframe: str, warmup_bars: int) -> dict:
    """기존 데이터는 보존하고 더 긴 준비 이력만 별도 파일에 추가한다."""
    if timeframe not in TIMEFRAMES or not 2 <= warmup_bars <= 10000:
        raise ValueError("추가 준비봉의 주기 또는 길이가 올바르지 않습니다")
    manifest = read(root / "dataset.json")
    period = next(value for value in PERIODS if value.id == period_id)
    interval, minutes = TIMEFRAMES[timeframe]
    first = milliseconds(period.start) - warmup_bars * minutes * 60_000
    end = milliseconds(period.end_exclusive)
    folder = root / "extensions" / period_id
    receipt_path = folder / f"{timeframe}-{warmup_bars}.json"
    if receipt_path.exists():
        record = read(receipt_path)
        checked(root, record["path"], record["sha256"])
        return record
    base = manifest["files"][period_id][timeframe]
    rows = seed_rows(checked(root, base["path"], base["sha256"]), first, end)
    reused = len(rows)
    for left, right in missing_ranges(first, end, minutes * 60_000, rows):
        rows.update(page_rows(root, interval, left, right))
    if sorted(rows) != list(range(first, end, minutes * 60_000)):
        raise ValueError("추가 준비 이력을 실제 시세로 확보하지 못했습니다")
    for row in rows.values():
        validate_row(row)
    content = csv_bytes(rows)
    path = folder / f"{timeframe}-{warmup_bars}.csv.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    record = {"path": str(path.relative_to(root)), "sha256": sha(content), "rows": len(rows),
              "warmup_bars": warmup_bars, "start": timestamp(first), "end_exclusive": timestamp(end),
              "seed_rows": reused, "new_public_rows": len(rows) - reused, "validated_at": now(),
              "base_file_sha256": base["sha256"]}
    immutable(receipt_path, record)
    return record
