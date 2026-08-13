"""`btgap_compare.py s1diff` — 스팟/perp 진입가 차 분포의 산술과 「미판정」 규율.

## 왜 「미판정」이 규율인가

쌍이 0 건일 때 격차를 `0` 으로 내면 읽는 사람은 **"차이가 없다"** 로 읽는다. 실제로는
**"잴 표본이 없다"** 이고 그 둘은 다르다. 이 레포는 같은 함정을 이미 밟았다 —
작은 창의 0 은 0 이 아니다. 그래서 여기서 `verdict` 를 명시 필드로 고정한다.

★DB 도 네트워크도 타지 않는다.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from tests.scripts.btgap_fixtures import collect_floats, load_script, trade_row

BASE = datetime(2026, 8, 5, 0, 0, tzinfo=UTC)
BAR_SECONDS = 60


def iso(minutes: int, seconds: int = 0) -> str:
    return (BASE + timedelta(minutes=minutes, seconds=seconds)).isoformat()


@pytest.fixture(scope="module")
def btgap() -> Any:
    return load_script("btgap_compare")


def _trades(btgap: Any, rows: list[dict[str, Any]]) -> Any:
    return btgap.parse_backtest_trades(rows)


# --------------------------------------------------------------------------
# 중앙값 산술
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([], None),
        (["1"], Decimal("1")),
        (["3", "1", "2"], Decimal("2")),
        (["10", "-50"], Decimal("-20")),
        (["1", "2", "3", "4"], Decimal("2.5")),
    ],
)
def test_median_decimal(btgap: Any, values: list[str], expected: Decimal | None) -> None:
    assert btgap.median_decimal([Decimal(v) for v in values]) == expected


def test_median_stays_in_decimal_space(btgap: Any) -> None:
    """float 로 새면 0.1 + 0.2 류의 잔차가 중앙값에 실린다."""
    result = btgap.median_decimal([Decimal("0.1"), Decimal("0.2")])
    assert isinstance(result, Decimal)
    assert result == Decimal("0.15")


# --------------------------------------------------------------------------
# 신호봉 쌍짓기
# --------------------------------------------------------------------------


def test_pairs_only_when_both_sides_entered_the_same_bar(btgap: Any) -> None:
    spot = _trades(
        btgap,
        [
            trade_row(trade_index=0, entry_time=iso(10), entry_price="60010"),
            trade_row(trade_index=1, entry_time=iso(12), entry_price="61000"),
            trade_row(trade_index=2, entry_time=iso(20), entry_price="62000"),
        ],
    )
    perp = _trades(
        btgap,
        [
            trade_row(trade_index=0, entry_time=iso(10), entry_price="60000"),
            trade_row(trade_index=1, entry_time=iso(20), entry_price="62050"),
            trade_row(trade_index=2, entry_time=iso(30), entry_price="63000"),
        ],
    )
    pairs = btgap.pair_by_signal_bar(spot, perp, bar_seconds=BAR_SECONDS)
    assert [(s.trade_index, p.trade_index) for s, p in pairs] == [(0, 0), (2, 1)]


def test_entry_within_the_same_bar_is_the_same_signal(btgap: Any) -> None:
    """봉 안의 초 단위 차이는 같은 신호봉이다 — floor 로 정렬한다."""
    spot = _trades(btgap, [trade_row(trade_index=0, entry_time=iso(10, 5), entry_price="60010")])
    perp = _trades(btgap, [trade_row(trade_index=0, entry_time=iso(10, 59), entry_price="60000")])
    assert len(btgap.pair_by_signal_bar(spot, perp, bar_seconds=BAR_SECONDS)) == 1


def test_adjacent_bars_do_not_pair(btgap: Any) -> None:
    spot = _trades(btgap, [trade_row(trade_index=0, entry_time=iso(10), entry_price="60010")])
    perp = _trades(btgap, [trade_row(trade_index=0, entry_time=iso(11), entry_price="60000")])
    assert btgap.pair_by_signal_bar(spot, perp, bar_seconds=BAR_SECONDS) == []


# --------------------------------------------------------------------------
# 부호 · 분포 · 미판정
# --------------------------------------------------------------------------


def test_sign_and_median_of_the_difference(btgap: Any) -> None:
    spot = _trades(
        btgap,
        [
            trade_row(trade_index=0, entry_time=iso(10), entry_price="60010"),
            trade_row(trade_index=1, entry_time=iso(20), entry_price="62000"),
        ],
    )
    perp = _trades(
        btgap,
        [
            trade_row(trade_index=0, entry_time=iso(10), entry_price="60000"),
            trade_row(trade_index=1, entry_time=iso(20), entry_price="62050"),
        ],
    )
    payload = btgap.build_s1diff(spot, perp, bar_seconds=BAR_SECONDS)
    assert payload["pairs"]["n"] == 2
    assert payload["pairs"]["verdict"] == "measured"
    assert payload["pairs"]["median_spot_minus_perp"] == "-20"
    assert payload["pairs"]["min_spot_minus_perp"] == "-50"
    assert payload["pairs"]["max_spot_minus_perp"] == "10"
    assert payload["pairs"]["sign"] == {"positive": 1, "negative": 1, "zero": 0}


def test_zero_difference_is_counted_as_zero_not_positive(btgap: Any) -> None:
    spot = _trades(btgap, [trade_row(trade_index=0, entry_time=iso(10), entry_price="60000")])
    perp = _trades(btgap, [trade_row(trade_index=0, entry_time=iso(10), entry_price="60000.00")])
    payload = btgap.build_s1diff(spot, perp, bar_seconds=BAR_SECONDS)
    assert payload["pairs"]["sign"] == {"positive": 0, "negative": 0, "zero": 1}


def test_no_pairs_is_undetermined_not_zero(btgap: Any) -> None:
    """★쌍이 없으면 「격차 0」이 아니라 「미판정」이다."""
    spot = _trades(btgap, [trade_row(trade_index=0, entry_time=iso(10), entry_price="60000")])
    perp = _trades(btgap, [trade_row(trade_index=0, entry_time=iso(30), entry_price="63000")])
    payload = btgap.build_s1diff(spot, perp, bar_seconds=BAR_SECONDS)
    assert payload["pairs"]["n"] == 0
    assert payload["pairs"]["verdict"] == "undetermined"
    assert payload["pairs"]["median_spot_minus_perp"] is None
    assert payload["pairs"]["min_spot_minus_perp"] is None
    assert payload["pairs"]["max_spot_minus_perp"] is None
    assert payload["pairs"]["sign"] == {"positive": 0, "negative": 0, "zero": 0}


def test_both_sides_empty_is_undetermined(btgap: Any) -> None:
    payload = btgap.build_s1diff([], [], bar_seconds=BAR_SECONDS)
    assert payload["pairs"]["verdict"] == "undetermined"
    assert payload["instruments"]["spot"]["entries"] == 0
    assert payload["instruments"]["spot"]["fee_paid_total"] is None


# --------------------------------------------------------------------------
# 계기별 요약
# --------------------------------------------------------------------------


def test_instrument_stats_sum_in_decimal_space(btgap: Any) -> None:
    trades = _trades(
        btgap,
        [
            trade_row(
                trade_index=0,
                entry_time=iso(10),
                pnl="0.1",
                fees="0.6",
                fee_paid="0.4",
                slippage_paid="0.2",
            ),
            trade_row(
                trade_index=1,
                entry_time=iso(20),
                pnl="0.2",
                fees="0.4",
                fee_paid="0.25",
                slippage_paid="0.15",
            ),
        ],
    )
    stats = btgap.instrument_stats(trades)
    assert stats["entries"] == 2
    assert stats["net_profit_abs"] == "0.3"
    assert stats["cost_total"] == "1.0"
    assert stats["fee_paid_total"] == "0.65"
    assert stats["slippage_paid_total"] == "0.35"


def test_partial_cost_split_is_reported_as_missing(btgap: Any) -> None:
    """한 건이라도 분해가 없으면 합계를 만들지 않는다 — 0 으로 메우면 비용이 준다."""
    trades = _trades(
        btgap,
        [
            trade_row(trade_index=0, entry_time=iso(10), fee_paid="0.4", slippage_paid="0.2"),
            trade_row(trade_index=1, entry_time=iso(20), fee_paid=None, slippage_paid=None),
        ],
    )
    stats = btgap.instrument_stats(trades)
    assert stats["fee_paid_total"] is None
    assert stats["slippage_paid_total"] is None
    assert stats["cost_total"] is not None


def test_s1diff_payload_has_no_floats(btgap: Any) -> None:
    spot = _trades(btgap, [trade_row(trade_index=0, entry_time=iso(10), entry_price="60010")])
    perp = _trades(btgap, [trade_row(trade_index=0, entry_time=iso(10), entry_price="60000")])
    payload = btgap.build_s1diff(spot, perp, bar_seconds=BAR_SECONDS)
    assert collect_floats(json.loads(json.dumps(payload))) == []


def test_cli_s1diff_writes_output(btgap: Any, tmp_path: Any) -> None:
    spot_rows = [trade_row(trade_index=0, entry_time=iso(10), entry_price="60010")]
    perp_rows = [trade_row(trade_index=0, entry_time=iso(10), entry_price="60000")]
    (tmp_path / "spot.json").write_text(json.dumps({"trades": spot_rows}), encoding="utf-8")
    (tmp_path / "perp.json").write_text(json.dumps({"trades": perp_rows}), encoding="utf-8")
    out = tmp_path / "s1.json"
    assert (
        btgap.main(
            [
                "s1diff",
                "--spot",
                str(tmp_path / "spot.json"),
                "--perp",
                str(tmp_path / "perp.json"),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["pairs"]["n"] == 1
    assert payload["pairs"]["median_spot_minus_perp"] == "10"


# --------------------------------------------------------------------------
# R14 — 짝짓기 커버리지 (무보고 탈락은 선택 편향 검증을 막는다)
# --------------------------------------------------------------------------


def test_unpaired_counts_and_nets_are_reported(btgap: Any) -> None:
    """★실측 144쌍 = spot 193 의 75% · perp 210 의 69% — 나머지를 안 세면
    「짝지어진 것들끼리 비슷하다」가 선택 편향인지 아무도 못 가린다."""
    spot = _trades(
        btgap,
        [
            trade_row(trade_index=0, entry_time=iso(10), entry_price="60010", pnl="1.0"),
            trade_row(trade_index=1, entry_time=iso(12), entry_price="61000", pnl="2.0"),
        ],
    )
    perp = _trades(
        btgap,
        [
            trade_row(trade_index=0, entry_time=iso(10), entry_price="60000", pnl="1.5"),
            trade_row(trade_index=1, entry_time=iso(30), entry_price="63000", pnl="-3.0"),
            trade_row(trade_index=2, entry_time=iso(40), entry_price="64000", pnl="0.5"),
        ],
    )
    pairs = btgap.build_s1diff(spot, perp, bar_seconds=BAR_SECONDS)["pairs"]
    assert pairs["n"] == 1
    assert pairs["unpaired_spot"] == 1
    assert pairs["unpaired_perp"] == 2
    assert pairs["unpaired_spot_net"] == "2.0"
    assert pairs["unpaired_perp_net"] == "-2.5"
    assert Decimal(pairs["spot_pair_coverage_pct"]) == Decimal("50")
    assert Decimal(pairs["perp_pair_coverage_pct"]) < Decimal("34")


def test_full_coverage_reports_zero_unpaired(btgap: Any) -> None:
    spot = _trades(btgap, [trade_row(trade_index=0, entry_time=iso(10), entry_price="60010")])
    perp = _trades(btgap, [trade_row(trade_index=0, entry_time=iso(10), entry_price="60000")])
    pairs = btgap.build_s1diff(spot, perp, bar_seconds=BAR_SECONDS)["pairs"]
    assert pairs["unpaired_spot"] == 0
    assert pairs["unpaired_perp"] == 0
    assert Decimal(pairs["spot_pair_coverage_pct"]) == Decimal("100")


def test_empty_sides_have_no_coverage_percentage(btgap: Any) -> None:
    """0/0 을 100% 로 내면 「전건 짝지었다」로 읽힌다."""
    pairs = btgap.build_s1diff([], [], bar_seconds=BAR_SECONDS)["pairs"]
    assert pairs["spot_pair_coverage_pct"] is None
    assert pairs["perp_pair_coverage_pct"] is None


# --------------------------------------------------------------------------
# 소소 — cost_total 은 정의가 하나뿐이다
# --------------------------------------------------------------------------


def test_cost_total_has_a_single_definition(btgap: Any) -> None:
    trades = _trades(
        btgap,
        [
            trade_row(
                trade_index=0, entry_time=iso(10), fees="0.6", fee_paid="0.4", slippage_paid="0.2"
            ),
            trade_row(
                trade_index=1, entry_time=iso(20), fees="0.4", fee_paid="0.25", slippage_paid="0.15"
            ),
        ],
    )
    stats = btgap.instrument_stats(trades)
    assert stats["cost_total_definition"] == "sum(RawTrade.fees)"
    assert stats["cost_total"] == "1.0"
    assert Decimal(stats["split_residual"]) == Decimal("0")


def test_split_residual_exposes_a_drifting_decomposition(btgap: Any) -> None:
    """분해가 결합 필드와 어긋나면 **보이게** 남긴다 — 조용히 두 정의를 두지 않는다."""
    trades = _trades(
        btgap,
        [
            trade_row(
                trade_index=0,
                entry_time=iso(10),
                fees="0.6",
                fee_paid="0.4",
                slippage_paid="0.30000001",
            )
        ],
    )
    stats = btgap.instrument_stats(trades)
    assert stats["cost_total"] == "0.6"
    assert Decimal(stats["split_residual"]) == Decimal("0.10000001")


def test_missing_split_leaves_the_residual_undefined(btgap: Any) -> None:
    trades = _trades(
        btgap,
        [trade_row(trade_index=0, entry_time=iso(10), fee_paid=None, slippage_paid=None)],
    )
    stats = btgap.instrument_stats(trades)
    assert stats["split_residual"] is None
    assert stats["cost_total"] is not None
