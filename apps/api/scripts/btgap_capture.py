#!/usr/bin/env python
# btgap — 소크 구간과 대조할 Bybit 공개 kline 을 CSV + manifest 로 **동결**한다
"""백테스트↔라이브 대조(btgap)의 입력 OHLCV 를 한 번 받아 얼린다.

## 왜 스크립트인가

대조에 쓸 1분봉은 DB 에 없고(`ts.ohlcv` 에 `1m` 행이 0건 — 라이브는 `CCXTProvider` 로
직접 받는다) 거래소에서만 온다. 그런데 테스트는 **네트워크를 타면 안 된다**. 그래서
수집은 여기서 **한 번** 하고, 대조(`btgap_compare.py`)와 테스트는 얼린 파일만 읽는다.

같은 창을 다시 받으면 같은 CSV 가 나와야 하므로 `manifest.json` 에 sha256 을 남긴다.
파일이 갈리면 그건 데이터가 갈린 것이지 코드가 갈린 것이 아니다.

## 함정 셋 (전부 이 레포의 실측 기록)

1. ★**Bybit 은 `start`+`end` 를 함께 주면 창의 *뒤쪽*부터 준다**
   (`capture_bl595_death_fixtures.py:80-115` 의 `fetch_closed_bars` 가 적은 것). 그래서
   페이지네이션은 `end` 커서를 **뒤에서 앞으로** 밀고, 받은 뒤 오름차순 정렬 + 절단한다.
2. ★**미종료 봉이 섞여 온다.** 마지막 원소는 아직 닫히지 않은 봉일 수 있다. 그 봉의
   close 는 "지금 값" 이라 다시 받으면 달라진다 — 동결의 뜻이 사라진다. `--out` 에 쓰기
   전에 `captured_at` 기준으로 잘라낸다.
3. ★**검증 실패 시 파일을 쓰지 않는다** (`fetch_qa_ohlcv.py` 관례). 갭이 있는 CSV 를
   써 두면 그 갭이 대조 결과의 격차로 둔갑한다.

## 사용

    cd apps/api && uv run python scripts/btgap_capture.py \\
        --category linear --symbol BTCUSDT --interval 1 \\
        --start 2026-08-05T00:00:00Z --end 2026-08-05T06:00:00Z \\
        --out ../tmp_code/btgap/perp

`--category spot` 로 한 번 더 받으면 `btgap_compare.py s1diff` 의 입력 두 벌이 된다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from itertools import pairwise
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlencode

BYBIT_KLINE_URL = "https://api.bybit.com/v5/market/kline"
# Bybit v5 kline 의 페이지 상한. 이보다 크게 요청해도 1000 으로 잘린다.
PAGE_LIMIT = 1000
# 창 하나에 페이지가 이보다 많이 필요하면 커서가 안 움직이고 있다는 뜻이다.
MAX_PAGES = 500

# Bybit v5 는 분 단위를 숫자 문자열로 받는다. 여기 없는 값은 지원하지 않는다 —
# 조용히 추측하면 step 이 틀린 채로 갭 검증이 통과한다.
INTERVAL_SECONDS: dict[str, int] = {
    "1": 60,
    "3": 180,
    "5": 300,
    "15": 900,
    "30": 1800,
    "60": 3600,
    "120": 7200,
    "240": 14400,
    "360": 21600,
    "720": 43200,
    "D": 86400,
}

CSV_HEADER = "timestamp,open,high,low,close,volume"
# FixtureProvider 가 읽는 timestamp 표기 (`fetch_qa_ohlcv.py:_write_csv` 와 동일).
CSV_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class PageFetcher(Protocol):
    """kline 한 페이지를 거래소 원본 문자열 행으로 돌려주는 호출자."""

    def __call__(
        self,
        *,
        category: str,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
    ) -> Sequence[Sequence[str]]: ...


@dataclass(frozen=True, slots=True)
class Bar:
    """종료된 봉 하나. 가격/수량은 거래소 원본 문자열을 그대로 `Decimal` 로 받는다."""

    ts_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


def interval_seconds(interval: str) -> int:
    """Bybit interval 토큰 → 초. 미지원 토큰은 거부한다."""
    try:
        return INTERVAL_SECONDS[interval]
    except KeyError:
        raise ValueError(f"지원하지 않는 interval: {interval!r}") from None


def interval_label(interval: str) -> str:
    """파일명에 쓰는 사람이 읽는 라벨 (`1` → `1m`, `240` → `4h`, `D` → `1d`)."""
    seconds = interval_seconds(interval)
    if seconds % 86400 == 0:
        return f"{seconds // 86400}d"
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    return f"{seconds // 60}m"


def bybit_symbol(symbol: str) -> str:
    """`BTC/USDT:USDT` 같은 CCXT 표기를 거래소 원본 심볼로 바꾼다."""
    return symbol.replace("/", "").replace(":USDT", "")


def parse_page(rows: Sequence[Sequence[str]]) -> list[Bar]:
    """`result.list` 원본 행을 `Bar` 로 옮긴다. 모양이 어긋나면 거부한다."""
    parsed: list[Bar] = []
    for row in rows:
        if len(row) < 6:
            raise ValueError(f"kline 행의 열이 모자란다: {row!r}")
        try:
            parsed.append(
                Bar(
                    ts_ms=int(row[0]),
                    open=Decimal(str(row[1])),
                    high=Decimal(str(row[2])),
                    low=Decimal(str(row[3])),
                    close=Decimal(str(row[4])),
                    volume=Decimal(str(row[5])),
                )
            )
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise ValueError(f"kline 행을 읽을 수 없다: {row!r}") from exc
    return parsed


def sort_ascending(bars: Iterable[Bar]) -> list[Bar]:
    """오름차순 정렬 + 같은 timestamp 중복 제거(먼저 본 것 보존).

    ★Bybit 응답은 내림차순이고 페이지가 겹칠 수 있다. 정렬을 소비자에게 미루면
    갭 검증이 "정렬 안 된 배열" 을 갭으로 오인한다.
    """
    unique: dict[int, Bar] = {}
    for bar in bars:
        unique.setdefault(bar.ts_ms, bar)
    return [unique[ts] for ts in sorted(unique)]


def drop_unclosed(bars: Sequence[Bar], *, captured_at_ms: int, step_ms: int) -> list[Bar]:
    """`captured_at` 시점에 **아직 안 닫힌** 봉을 버린다.

    봉 `ts` 는 `ts + step` 에 닫힌다. 그 시각이 캡처 시각보다 뒤면 그 봉의 close 는
    "지금 값" 이라 다시 받으면 달라진다 — 동결 대상이 아니다.
    """
    return [bar for bar in bars if bar.ts_ms + step_ms <= captured_at_ms]


def clip_window(bars: Sequence[Bar], *, start_ms: int, end_ms: int) -> list[Bar]:
    """요청 창 `[start, end)` 으로 절단한다 (end 는 배타)."""
    return [bar for bar in bars if start_ms <= bar.ts_ms < end_ms]


def validate_bars(bars: Sequence[Bar], *, step_ms: int) -> list[str]:
    """단조증가 · 갭 0 · OHLC 불변식을 본다. 빈 리스트 = 통과.

    OHLC 불변식은 `low <= open/close <= high` 다. 값이 전부 거래소 원본 문자열에서 온
    `Decimal` 이라 부동소수 허용오차가 필요 없다 — 어긋나면 그건 진짜로 어긋난 것이다.
    """
    if not bars:
        return ["봉이 0건이다"]

    errors: list[str] = []
    non_monotonic = 0
    gaps: list[tuple[int, int]] = []
    for previous, current in pairwise(bars):
        delta = current.ts_ms - previous.ts_ms
        if delta <= 0:
            non_monotonic += 1
        elif delta != step_ms:
            gaps.append((previous.ts_ms, current.ts_ms))
    if non_monotonic:
        errors.append(f"timestamp 단조증가 위반 {non_monotonic}건")
    if gaps:
        head = ", ".join(f"{a}->{b}" for a, b in gaps[:3])
        errors.append(f"timestamp 갭 {len(gaps)}건 (step={step_ms}ms): {head}")

    invariant_violations = [
        bar
        for bar in bars
        if not (
            bar.low <= bar.open <= bar.high
            and bar.low <= bar.close <= bar.high
            and bar.low <= bar.high
        )
    ]
    if invariant_violations:
        errors.append(
            f"OHLC 불변식 위반 {len(invariant_violations)}건 "
            f"(첫 봉 ts={invariant_violations[0].ts_ms})"
        )
    return errors


def fetch_window(
    fetch_page: PageFetcher,
    *,
    category: str,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
) -> list[Bar]:
    """`[start, end)` 창을 전부 받아 오름차순으로 돌려준다.

    ★커서를 **뒤에서 앞으로** 민다. Bybit 이 `start`+`end` 동시 지정 시 창 뒤쪽부터
    주기 때문이다. 페이지가 앞으로 안 나아가면(같은 봉만 반복) 즉시 멈춘다 — 그렇지
    않으면 조용히 무한 루프에 들어간다.
    """
    step_ms = interval_seconds(interval) * 1000
    collected: dict[int, Bar] = {}
    cursor_end = end_ms
    for _ in range(MAX_PAGES):
        if cursor_end < start_ms:
            break
        page = parse_page(
            fetch_page(
                category=category,
                symbol=symbol,
                interval=interval,
                start_ms=start_ms,
                end_ms=cursor_end,
            )
        )
        if not page:
            break
        for bar in page:
            collected.setdefault(bar.ts_ms, bar)
        oldest = min(bar.ts_ms for bar in page)
        if oldest <= start_ms:
            break
        next_end = oldest - step_ms
        if next_end >= cursor_end:
            # 커서가 안 움직였다 = 거래소가 같은 페이지를 다시 줬다.
            break
        cursor_end = next_end
    return sort_ascending(collected.values())


def _decimal_text(value: Decimal) -> str:
    """지수 표기 없이 고정 소수점 문자열로. CSV 가 표현에 민감하기 때문이다."""
    return format(value, "f")


def bars_to_csv(bars: Sequence[Bar]) -> str:
    """FixtureProvider 컬럼 규약(`timestamp,open,high,low,close,volume`) CSV 텍스트."""
    lines = [CSV_HEADER]
    for bar in bars:
        moment = datetime.fromtimestamp(bar.ts_ms / 1000, tz=UTC)
        lines.append(
            ",".join(
                (
                    moment.strftime(CSV_TIMESTAMP_FORMAT),
                    _decimal_text(bar.open),
                    _decimal_text(bar.high),
                    _decimal_text(bar.low),
                    _decimal_text(bar.close),
                    _decimal_text(bar.volume),
                )
            )
        )
    return "\n".join(lines) + "\n"


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_manifest(
    bars: Sequence[Bar],
    csv_text: str,
    *,
    csv_filename: str,
    category: str,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    captured_at: datetime,
) -> dict[str, Any]:
    """동결 증서. 같은 창을 다시 받아 sha256 이 다르면 데이터가 갈린 것이다."""
    return {
        "csv_filename": csv_filename,
        "sha256": hashlib.sha256(csv_text.encode("utf-8")).hexdigest(),
        "captured_at": _iso(captured_at),
        "category": category,
        "symbol": symbol,
        "interval": interval,
        "interval_seconds": interval_seconds(interval),
        "window_start": _iso(datetime.fromtimestamp(start_ms / 1000, tz=UTC)),
        "window_end": _iso(datetime.fromtimestamp(end_ms / 1000, tz=UTC)),
        "bar_count": len(bars),
        "first_bar": _iso(datetime.fromtimestamp(bars[0].ts_ms / 1000, tz=UTC)) if bars else None,
        "last_bar": _iso(datetime.fromtimestamp(bars[-1].ts_ms / 1000, tz=UTC)) if bars else None,
    }


def _http_fetch_page(
    *,
    category: str,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
) -> Sequence[Sequence[str]]:
    """Bybit v5 공개 kline 한 페이지. 이 함수만 네트워크를 탄다."""
    query = urlencode(
        {
            "category": category,
            "symbol": symbol,
            "interval": interval,
            "start": start_ms,
            "end": end_ms,
            "limit": PAGE_LIMIT,
        }
    )
    # 억제 사유: URL 은 위 상수(https 고정) + urlencode 결과뿐이라 스킴이 바뀔 경로가 없다.
    with urllib.request.urlopen(f"{BYBIT_KLINE_URL}?{query}", timeout=30) as response:  # noqa: S310
        payload = json.loads(response.read())
    if payload.get("retCode") != 0:
        raise RuntimeError(f"bybit kline 실패: {payload.get('retMsg')}")
    rows: Sequence[Sequence[str]] = payload["result"]["list"]
    return rows


def _parse_iso(raw: str) -> datetime:
    moment = datetime.fromisoformat(raw)
    if moment.tzinfo is None:
        raise ValueError(f"tz 없는 시각은 받지 않는다(UTC 를 명시해라): {raw!r}")
    return moment.astimezone(UTC)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="btgap 대조용 Bybit 공개 kline 을 CSV + manifest 로 동결한다.",
    )
    parser.add_argument("--category", choices=("linear", "spot"), required=True)
    parser.add_argument("--symbol", required=True, help="예: BTCUSDT (CCXT 표기도 받는다)")
    parser.add_argument("--interval", default="1", help="Bybit interval 토큰 (1 = 1분봉)")
    parser.add_argument("--start", required=True, help="창 시작 ISO8601 (tz 필수, 포함)")
    parser.add_argument("--end", required=True, help="창 끝 ISO8601 (tz 필수, 배타)")
    parser.add_argument("--out", required=True, help="출력 디렉토리")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    symbol = bybit_symbol(args.symbol)
    step_ms = interval_seconds(args.interval) * 1000
    start = _parse_iso(args.start)
    end = _parse_iso(args.end)
    if end <= start:
        sys.stderr.write("ERROR: --end 는 --start 보다 뒤여야 한다\n")
        return 1
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)

    captured_at = datetime.now(UTC)
    raw_bars = fetch_window(
        _http_fetch_page,
        category=args.category,
        symbol=symbol,
        interval=args.interval,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    bars = clip_window(
        drop_unclosed(
            raw_bars, captured_at_ms=int(captured_at.timestamp() * 1000), step_ms=step_ms
        ),
        start_ms=start_ms,
        end_ms=end_ms,
    )

    errors = validate_bars(bars, step_ms=step_ms)
    if errors:
        sys.stderr.write("VALIDATION FAILED — 파일 미기록:\n")
        for error in errors:
            sys.stderr.write(f"  - {error}\n")
        return 1

    csv_filename = f"{symbol}_{args.category}_{interval_label(args.interval)}.csv"
    csv_text = bars_to_csv(bars)
    manifest = build_manifest(
        bars,
        csv_text,
        csv_filename=csv_filename,
        category=args.category,
        symbol=symbol,
        interval=args.interval,
        start_ms=start_ms,
        end_ms=end_ms,
        captured_at=captured_at,
    )

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / csv_filename).write_text(csv_text, encoding="utf-8")
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[write] {csv_filename}: {len(bars)} bars, sha256={manifest['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
