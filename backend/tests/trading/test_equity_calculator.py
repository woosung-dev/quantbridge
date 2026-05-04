"""Equity Calculator — Sprint 28 Slice 3 (BL-140b) unit test.

Decimal-first 합산 영구 규칙 + JSONB 직렬화 + edge case (동일 timestamp / 음수 PnL /
빈 curve / Decimal precision).
"""

from __future__ import annotations

from decimal import Decimal


def test_append_to_empty_curve_initializes():
    """빈 curve 에 첫 point append → cumulative_pnl = pnl_delta."""
    from src.trading.equity_calculator import append_equity_point

    result = append_equity_point(
        [], timestamp_ms=1700000000000, pnl_delta=Decimal("100.50")
    )

    assert len(result) == 1
    assert result[0]["timestamp_ms"] == 1700000000000
    assert result[0]["cumulative_pnl"] == "100.50"


def test_append_accumulates_decimal_correctly():
    """Decimal 합산 영구 규칙 (Sprint 4 D8) 정합."""
    from src.trading.equity_calculator import append_equity_point

    curve = append_equity_point(
        [], timestamp_ms=1700000000000, pnl_delta=Decimal("100.50")
    )
    curve = append_equity_point(
        curve, timestamp_ms=1700000060000, pnl_delta=Decimal("-30.25")
    )
    curve = append_equity_point(
        curve, timestamp_ms=1700000120000, pnl_delta=Decimal("0.001")
    )

    assert len(curve) == 3
    assert curve[0]["cumulative_pnl"] == "100.50"
    assert curve[1]["cumulative_pnl"] == "70.25"
    assert curve[2]["cumulative_pnl"] == "70.251"


def test_negative_pnl_decreases_cumulative():
    """음수 PnL 손실 시 cumulative 감소."""
    from src.trading.equity_calculator import append_equity_point

    curve = append_equity_point(
        [], timestamp_ms=1700000000000, pnl_delta=Decimal("500")
    )
    curve = append_equity_point(
        curve, timestamp_ms=1700000060000, pnl_delta=Decimal("-700")
    )

    assert curve[1]["cumulative_pnl"] == "-200"


def test_decimal_precision_long_tail():
    """8자리+ 소수 누적 시 precision 보존 (Numeric(18,8) 정합)."""
    from src.trading.equity_calculator import append_equity_point

    curve: list = []
    for i in range(10):
        curve = append_equity_point(
            curve,
            timestamp_ms=1700000000000 + i * 60000,
            pnl_delta=Decimal("0.12345678"),
        )

    # 0.12345678 × 10 = 1.23456780 (Decimal 정확)
    assert curve[-1]["cumulative_pnl"] == "1.23456780"


def test_same_timestamp_accumulates_not_overwrites():
    """동일 timestamp_ms 두 번 들어와도 누적 (P2 fix — race 방어)."""
    from src.trading.equity_calculator import append_equity_point

    curve = append_equity_point([], timestamp_ms=1700000000000, pnl_delta=Decimal("50"))
    curve = append_equity_point(curve, timestamp_ms=1700000000000, pnl_delta=Decimal("30"))

    assert len(curve) == 2  # 두 point 모두 보존
    assert curve[0]["cumulative_pnl"] == "50"
    assert curve[1]["cumulative_pnl"] == "80"  # 누적
    assert curve[0]["timestamp_ms"] == curve[1]["timestamp_ms"]


def test_recompute_from_closed_events():
    """전체 시퀀스 재계산 (manual recompute UI / migration backfill 사용)."""
    from src.trading.equity_calculator import recompute_equity_curve

    closed_pnls = [
        (1700000000000, Decimal("100")),
        (1700000060000, Decimal("-50")),
        (1700000120000, Decimal("25")),
        (1700000180000, Decimal("0")),
    ]

    curve = recompute_equity_curve(closed_pnls)

    assert len(curve) == 4
    assert curve[0]["cumulative_pnl"] == "100"
    assert curve[1]["cumulative_pnl"] == "50"
    assert curve[2]["cumulative_pnl"] == "75"
    assert curve[3]["cumulative_pnl"] == "75"  # 0 delta = 그대로


def test_jsonb_serializable_dict():
    """결과 dict 가 TypedDict 정합 — JSONB 직렬화 친화적 (int + str 만)."""
    import json

    from src.trading.equity_calculator import append_equity_point

    curve = append_equity_point(
        [], timestamp_ms=1700000000000, pnl_delta=Decimal("1.234")
    )

    serialized = json.dumps(curve)
    deserialized = json.loads(serialized)

    assert deserialized == [{"timestamp_ms": 1700000000000, "cumulative_pnl": "1.234"}]
