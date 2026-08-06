"""`btgap_capture.py` 의 수집·검증 규칙을 canned 응답으로 못박는다.

## 무엇이 위험한가

이 스크립트의 결함은 **조용하다**. 역순 응답을 정렬하지 않으면 갭 검증이 통과하고
(diff 가 음수라 `!= step` 분기로 안 들어가는 구현도 있다), 미종료 봉을 안 자르면 다시
받을 때마다 마지막 봉의 close 가 달라지는데 파일은 멀쩡해 보인다. 둘 다 **대조 결과의
격차로 둔갑**한다 — 그래서 여기서 실행 전에 고정한다.

★네트워크를 타지 않는다. 페이지 수집기는 Bybit 의 실제 계약
(`start`+`end` 동시 지정 시 창 **뒤쪽**부터, 내림차순, `limit` 개)을 흉내 낸 함수다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from tests.scripts.btgap_fixtures import load_script

MINUTE_MS = 60_000
BASE_MS = 1_754_352_000_000  # 2025-08-05T00:00:00Z 근방 — 값 자체에 의미는 없다.


@pytest.fixture(scope="module")
def capture() -> Any:
    return load_script("btgap_capture")


def _row(ts_ms: int, *, close: str = "100", high: str = "101", low: str = "99") -> list[str]:
    return [str(ts_ms), "100", high, low, close, "1.5"]


def _series(count: int, *, start_ms: int = BASE_MS, step_ms: int = MINUTE_MS) -> list[list[str]]:
    return [_row(start_ms + index * step_ms) for index in range(count)]


def _bybit_like_fetcher(rows: list[list[str]], *, page_limit: int) -> Any:
    """Bybit v5 kline 의 실제 계약을 흉내 낸다 — 창 뒤쪽부터, 내림차순, limit 개."""

    def fetch(
        *, category: str, symbol: str, interval: str, start_ms: int, end_ms: int
    ) -> list[list[str]]:
        window = [row for row in rows if start_ms <= int(row[0]) <= end_ms]
        window.sort(key=lambda row: int(row[0]), reverse=True)
        return window[:page_limit]

    return fetch


# --------------------------------------------------------------------------
# 역순 응답 정렬
# --------------------------------------------------------------------------


def test_descending_response_is_sorted_ascending(capture: Any) -> None:
    descending = list(reversed(_series(5)))
    bars = capture.sort_ascending(capture.parse_page(descending))
    assert [bar.ts_ms for bar in bars] == [BASE_MS + i * MINUTE_MS for i in range(5)]


def test_duplicate_timestamps_collapse(capture: Any) -> None:
    rows = _series(3) + _series(3)  # 페이지가 겹쳐 온 경우
    bars = capture.sort_ascending(capture.parse_page(rows))
    assert len(bars) == 3


def test_pagination_walks_backwards_and_covers_window(capture: Any) -> None:
    rows = _series(10)
    bars = capture.fetch_window(
        _bybit_like_fetcher(rows, page_limit=4),
        category="linear",
        symbol="BTCUSDT",
        interval="1",
        start_ms=BASE_MS,
        end_ms=BASE_MS + 9 * MINUTE_MS,
    )
    assert [bar.ts_ms for bar in bars] == [BASE_MS + i * MINUTE_MS for i in range(10)]


def test_pagination_stops_when_cursor_cannot_advance(capture: Any) -> None:
    """거래소가 같은 페이지를 계속 주면 멈춘다 — 무한 루프는 침묵 정지와 같다."""
    stuck_row = _row(BASE_MS + 5 * MINUTE_MS)

    def stuck_fetch(**_kwargs: Any) -> list[list[str]]:
        return [stuck_row]

    bars = capture.fetch_window(
        stuck_fetch,
        category="linear",
        symbol="BTCUSDT",
        interval="1",
        start_ms=BASE_MS,
        end_ms=BASE_MS + 9 * MINUTE_MS,
    )
    assert [bar.ts_ms for bar in bars] == [BASE_MS + 5 * MINUTE_MS]


# --------------------------------------------------------------------------
# 미종료 봉 절단 · 창 절단
# --------------------------------------------------------------------------


def test_drop_unclosed_removes_the_bar_still_open(capture: Any) -> None:
    bars = capture.parse_page(_series(3))
    # 마지막 봉(BASE+2m)은 BASE+3m 에 닫힌다. 캡처가 그 30초 전이면 아직 안 닫혔다.
    captured_at_ms = BASE_MS + 3 * MINUTE_MS - 30_000
    kept = capture.drop_unclosed(bars, captured_at_ms=captured_at_ms, step_ms=MINUTE_MS)
    assert [bar.ts_ms for bar in kept] == [BASE_MS, BASE_MS + MINUTE_MS]


def test_drop_unclosed_keeps_bar_closing_exactly_at_capture(capture: Any) -> None:
    """경계는 포함이다 — `ts + step == captured_at` 이면 그 봉은 닫혔다."""
    bars = capture.parse_page(_series(3))
    kept = capture.drop_unclosed(bars, captured_at_ms=BASE_MS + 3 * MINUTE_MS, step_ms=MINUTE_MS)
    assert len(kept) == 3


def test_clip_window_end_is_exclusive(capture: Any) -> None:
    bars = capture.parse_page(_series(5))
    clipped = capture.clip_window(
        bars, start_ms=BASE_MS + MINUTE_MS, end_ms=BASE_MS + 4 * MINUTE_MS
    )
    assert [bar.ts_ms for bar in clipped] == [
        BASE_MS + MINUTE_MS,
        BASE_MS + 2 * MINUTE_MS,
        BASE_MS + 3 * MINUTE_MS,
    ]


# --------------------------------------------------------------------------
# 검증 — 갭 · 단조 · OHLC 불변식
# --------------------------------------------------------------------------


def test_validate_passes_clean_series(capture: Any) -> None:
    bars = capture.parse_page(_series(5))
    assert capture.validate_bars(bars, step_ms=MINUTE_MS) == []


def test_validate_detects_gap(capture: Any) -> None:
    rows = _series(5)
    del rows[2]
    errors = capture.validate_bars(capture.parse_page(rows), step_ms=MINUTE_MS)
    assert any("갭" in error for error in errors)


def test_validate_detects_non_monotonic(capture: Any) -> None:
    bars = capture.parse_page(list(reversed(_series(4))))
    errors = capture.validate_bars(bars, step_ms=MINUTE_MS)
    assert any("단조증가" in error for error in errors)


@pytest.mark.parametrize(
    ("high", "low", "close"),
    [
        ("99", "99", "100"),  # high < close
        ("101", "101", "100"),  # low > close
        ("99.5", "99", "99.2"),  # high < open(100)
    ],
)
def test_validate_detects_ohlc_violation(capture: Any, high: str, low: str, close: str) -> None:
    rows = _series(3)
    rows[1] = _row(BASE_MS + MINUTE_MS, close=close, high=high, low=low)
    errors = capture.validate_bars(capture.parse_page(rows), step_ms=MINUTE_MS)
    assert any("OHLC" in error for error in errors)


def test_validate_rejects_empty(capture: Any) -> None:
    assert capture.validate_bars([], step_ms=MINUTE_MS) != []


def test_parse_page_rejects_short_row(capture: Any) -> None:
    with pytest.raises(ValueError, match="열이 모자란다"):
        capture.parse_page([["1", "2", "3"]])


# --------------------------------------------------------------------------
# CSV · manifest
# --------------------------------------------------------------------------


def test_csv_uses_fixture_provider_columns(capture: Any) -> None:
    bars = capture.parse_page(_series(2))
    text = capture.bars_to_csv(bars)
    lines = text.strip().split("\n")
    assert lines[0] == "timestamp,open,high,low,close,volume"
    assert lines[1].split(",")[0].endswith("Z")
    assert len(lines) == 3


def test_csv_keeps_decimal_representation(capture: Any) -> None:
    """지수 표기가 새 나가면 pandas 가 읽는 값이 달라진다."""
    bar = capture.Bar(
        ts_ms=BASE_MS,
        open=Decimal("0.00000123"),
        high=Decimal("0.00000123"),
        low=Decimal("0.00000123"),
        close=Decimal("0.00000123"),
        volume=Decimal("1"),
    )
    assert "0.00000123" in capture.bars_to_csv([bar])
    assert "E-" not in capture.bars_to_csv([bar])


def test_manifest_digest_tracks_content(capture: Any) -> None:
    bars = capture.parse_page(_series(3))
    csv_text = capture.bars_to_csv(bars)

    def _manifest() -> Any:
        return capture.build_manifest(
            bars,
            csv_text,
            csv_filename="BTCUSDT_linear_1m.csv",
            category="linear",
            symbol="BTCUSDT",
            interval="1",
            start_ms=BASE_MS,
            end_ms=BASE_MS + 3 * MINUTE_MS,
            captured_at=datetime.fromtimestamp(BASE_MS / 1000, tz=UTC),
        )

    manifest = _manifest()
    assert manifest["bar_count"] == 3
    assert manifest["interval_seconds"] == 60
    assert manifest["sha256"] == _manifest()["sha256"]

    changed = capture.parse_page(_series(3))
    changed[-1] = capture.Bar(
        ts_ms=changed[-1].ts_ms,
        open=changed[-1].open,
        high=changed[-1].high,
        low=changed[-1].low,
        close=Decimal("100.5"),
        volume=changed[-1].volume,
    )
    assert capture.bars_to_csv(changed) != csv_text


# --------------------------------------------------------------------------
# interval 토큰
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("token", "label"), [("1", "1m"), ("15", "15m"), ("240", "4h"), ("D", "1d")]
)
def test_interval_label(capture: Any, token: str, label: str) -> None:
    assert capture.interval_label(token) == label


def test_unsupported_interval_is_rejected(capture: Any) -> None:
    with pytest.raises(ValueError, match="지원하지 않는 interval"):
        capture.interval_seconds("7")


def test_bybit_symbol_normalizes_ccxt_form(capture: Any) -> None:
    assert capture.bybit_symbol("BTC/USDT:USDT") == "BTCUSDT"
