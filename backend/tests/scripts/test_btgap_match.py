"""`btgap_compare.py match` 의 4단 분해를 합성 픽스처로 못박는다.

## 이 대조가 조용히 거짓말할 수 있는 자리들

1. **원장 2배 계상.** `exits.json` 은 한 청산이 **2행**으로 온다 — 순진한 Σ 는 손익을
   정확히 2배로 만든다. dedup 전/후가 둘 다 보고서에 남아야 한다.
2. **존재 격차를 가격 격차에 접는 것.** 엔진에만 있는 거래를 매칭 관측에 섞으면
   "신호가 라이브에선 아예 안 났다" 가 "체결가가 조금 달랐다" 로 둔갑한다.
3. **가격으로 매칭하는 것.** 0.1% 창 안에 남의 체결가가 늘 들어온다 — 가격은 판별자가
   아니라 매칭 **뒤** 잔차다. 과잉 매칭은 fail-**open** 이라 모호하면 안 붙인다.
4. **gross 복원을 뒤집는 것.** `RawTrade.pnl` 은 net 이라 기대 gross 는 `pnl + fees` 다.
5. **비율을 합계 뒤 절대값으로 재는 것.** 부호 상쇄가 분모를 0 쪽으로 끌어 비율이
   폭발한다 — 그래도 판정은 사전등록 정의로 하고 상쇄 정도를 병기한다.
6. **세션 경계.** 반전 전략이라 진입창 ≠ 청산창이 실재한다.

★DB 도 네트워크도 celery 도 타지 않는다. 전부 순수 함수 + 합성 JSON 이다.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest

from tests.scripts.btgap_fixtures import (
    SESSION_ID,
    as_dumped_rows,
    collect_floats,
    conditional_entry_key,
    exit_row,
    load_script,
    market_entry_key,
    order_row,
    session_row,
    trade_row,
)

BASE = datetime(2026, 8, 5, 0, 0, tzinfo=UTC)
BAR_SECONDS = 60
SESSION_B_ID = UUID("11111111-0000-4000-8000-0000000000b2")


def at(minutes: int, seconds: int = 0) -> datetime:
    return BASE + timedelta(minutes=minutes, seconds=seconds)


def epoch(minutes: int) -> int:
    return int(at(minutes).timestamp())


def iso(minutes: int, seconds: int = 0) -> str:
    return at(minutes, seconds).isoformat()


@pytest.fixture(scope="module")
def btgap() -> Any:
    return load_script("btgap_compare")


# --------------------------------------------------------------------------
# 표준 시나리오 — 두 세션 + 그 사이 무세션 구간
#
#   세션 A  00:00 ~ 00:40      갭 00:40 ~ 01:00      세션 B  01:00 ~ 01:40
#
#   e1(+1분)  strict 쌍   · 청산 x1(+5분,  A)
#   e2(+10분) loose  쌍   · 청산 x2(+15분, A)   ← 백테 진입봉이 +2봉 뒤
#   e3(+30분) live_only   · 청산 x3(+35분, A)
#   e4(+38분) strict 쌍   · 청산 x4(+50분, **갭**)  ← cross_window
#   백테 idx2(+20분)      backtest_only
#   x5(+70분, B) orphan flatten (orders 에 없는 link)
#   x6(+75분, B) flatten  (o-flat 링크)
# --------------------------------------------------------------------------


def _sessions() -> list[dict[str, Any]]:
    session_a = session_row(created_at=iso(0), deactivated_at=iso(40))
    session_b = {
        **session_row(created_at=iso(60), deactivated_at=iso(100)),
        "id": str(SESSION_B_ID),
    }
    return [session_a, session_b]


def _orders() -> list[dict[str, Any]]:
    return [
        order_row(
            order_id="o-e1",
            side="buy",
            idempotency_key=conditional_entry_key(
                bar_epoch=epoch(1), trigger="60000", quantity="0.01"
            ),
            filled_price="60005",
            filled_quantity="0.01",
            filled_at=iso(1, 40),
        ),
        order_row(
            order_id="o-c1",
            side="sell",
            idempotency_key=f"live:{SESSION_ID}:close:{epoch(5)}:PbR",
            filled_price="60150",
            filled_quantity="0.01",
            reduce_only=True,
            # ★R2 대조 — 원장(1.3) 과 **다른** 값을 일부러 넣는다. 보고서가 이 값을
            #   따라가면 actual 축이 원장이 아니라 주문에서 온 것이다.
            realized_pnl="99.9",
            realized_pnl_synced_at=iso(6),
            filled_at=iso(5, 10),
        ),
        order_row(
            order_id="o-e2",
            side="buy",
            idempotency_key=conditional_entry_key(
                bar_epoch=epoch(10), trigger="61000", quantity="0.02"
            ),
            filled_price="61005",
            filled_quantity="0.02",
            filled_at=iso(12, 30),
        ),
        order_row(
            order_id="o-c2",
            side="sell",
            idempotency_key=f"live:{SESSION_ID}:close:{epoch(15)}:PbR",
            filled_quantity="0.02",
            reduce_only=True,
            filled_at=iso(15, 10),
        ),
        order_row(
            order_id="o-e3",
            side="sell",
            idempotency_key=conditional_entry_key(
                bar_epoch=epoch(30), trigger="62000", quantity="0.01"
            ),
            filled_price="61995",
            filled_quantity="0.01",
            filled_at=iso(30, 20),
        ),
        order_row(
            order_id="o-c3",
            side="buy",
            idempotency_key=f"live:{SESSION_ID}:close:{epoch(35)}:PbR",
            filled_quantity="0.01",
            reduce_only=True,
            filled_at=iso(35, 10),
        ),
        order_row(
            order_id="o-e4",
            side="buy",
            idempotency_key=conditional_entry_key(
                bar_epoch=epoch(38), trigger="62000", quantity="0.04"
            ),
            filled_price="62002",
            filled_quantity="0.04",
            filled_at=iso(38, 30),
        ),
        order_row(
            order_id="o-c4",
            side="sell",
            idempotency_key=f"live:{SESSION_ID}:close:{epoch(50)}:PbR",
            filled_quantity="0.04",
            reduce_only=True,
            filled_at=iso(50, 10),
        ),
        # 수동 정리 — 빈 key + reduce_only.
        order_row(
            order_id="o-flat",
            side="sell",
            idempotency_key=None,
            filled_quantity="0.01",
            reduce_only=True,
            filled_at=iso(75),
        ),
    ]


def _events() -> list[dict[str, Any]]:
    """dedup **후** 의 event 목록. 입력에는 `as_dumped_rows` 로 부풀려 넣는다."""
    return [
        exit_row(
            exit_id="x1",
            order_link_id="o-c1",
            side="Sell",
            closed_pnl="1.3",
            closed_size="0.01",
            avg_entry_price="60000",
            avg_exit_price="60150",
            exchange_created_at=iso(5),
        ),
        exit_row(
            exit_id="x2",
            order_link_id="o-c2",
            side="Sell",
            closed_pnl="0.5",
            closed_size="0.02",
            avg_entry_price="61000",
            avg_exit_price="61030",
            exchange_created_at=iso(15),
        ),
        exit_row(
            exit_id="x3",
            order_link_id="o-c3",
            side="Buy",
            closed_pnl="-0.5",
            closed_size="0.01",
            avg_entry_price="62000",
            avg_exit_price="62050",
            exchange_created_at=iso(35),
        ),
        exit_row(
            exit_id="x4",
            order_link_id="o-c4",
            side="Sell",
            closed_pnl="0.2",
            closed_size="0.04",
            avg_entry_price="62000",
            avg_exit_price="62010",
            exchange_created_at=iso(50),  # ★세션 사이 갭
        ),
        exit_row(
            exit_id="x5",
            order_link_id="o-ghost",  # orders 에 없다 — exits 에만 있는 청산
            side="Sell",
            closed_pnl="-1.1",
            closed_size="0.01",
            avg_entry_price="63000",
            avg_exit_price="62890",
            exchange_created_at=iso(70),
        ),
        exit_row(
            exit_id="x6",
            order_link_id="o-flat",
            side="Sell",
            closed_pnl="-0.1",
            closed_size="0.01",
            avg_entry_price="63000",
            avg_exit_price="62990",
            exchange_created_at=iso(75),
        ),
    ]


def _trades() -> list[dict[str, Any]]:
    return [
        # e1 과 strict — 신호봉 정확 일치 · 수량 일치 · comment == trade_id.
        trade_row(
            trade_index=0,
            direction="long",
            entry_time=iso(1),
            exit_time=iso(5),
            entry_price="60000",
            exit_price="60150",
            size="0.01",
            pnl="0.4",
            fees="0.6",
            fee_paid="0.4",
            slippage_paid="0.2",
        ),
        # e2 와 loose — 진입봉이 신호봉보다 **2봉 뒤**라 1차 키가 안 선다.
        trade_row(
            trade_index=1,
            direction="long",
            entry_time=iso(12),
            exit_time=iso(15),
            entry_price="61000",
            exit_price="61030",
            size="0.02",
            pnl="0.3",
            fees="0.3",
            fee_paid="0.2",
            slippage_paid="0.1",
        ),
        # 엔진에만 있는 거래.
        trade_row(
            trade_index=2,
            direction="long",
            entry_time=iso(20),
            exit_time=iso(24),
            entry_price="61500",
            exit_price="61700",
            size="0.03",
            pnl="1.0",
            fees="0.5",
            fee_paid="0.35",
            slippage_paid="0.15",
        ),
        # e4 와 strict — 청산이 세션 갭으로 넘어간다.
        trade_row(
            trade_index=3,
            direction="long",
            entry_time=iso(38),
            exit_time=iso(50),
            entry_price="62000",
            exit_price="62010",
            size="0.04",
            pnl="0.1",
            fees="0.3",
            fee_paid="0.2",
            slippage_paid="0.1",
        ),
    ]


def _build(
    btgap: Any,
    *,
    orders: list[dict[str, Any]] | None = None,
    events: list[dict[str, Any]] | None = None,
    trades: list[dict[str, Any]] | None = None,
    sessions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    sessions_raw = _sessions() if sessions is None else sessions
    windows = btgap.parse_sessions(sessions_raw)
    corpus = btgap.parse_orders(
        _orders() if orders is None else orders,
        session_ids=[UUID(window.session_id) for window in windows],
    )
    dedup = btgap.dedupe_ledger_rows(
        btgap.parse_ledger_rows(as_dumped_rows(_events() if events is None else events))
    )
    parsed_trades = btgap.parse_backtest_trades(_trades() if trades is None else trades)
    match = btgap.match_entries(parsed_trades, corpus.entries, bar_seconds=BAR_SECONDS)
    decomposition = btgap.decompose(match, corpus=corpus, dedup=dedup)
    report = btgap.build_report(
        decomposition,
        match,
        windows=windows,
        sessions_raw=sessions_raw,
        corpus=corpus,
        dedup=dedup,
        trades=parsed_trades,
    )
    return {
        "corpus": corpus,
        "dedup": dedup,
        "match": match,
        "decomposition": decomposition,
        "report": report,
        "trades": parsed_trades,
        "windows": windows,
    }


# --------------------------------------------------------------------------
# R6 — 원장 dedup (한 청산이 2행으로 온다)
# --------------------------------------------------------------------------


def test_each_exit_event_arrives_as_two_rows_and_collapses_to_one(btgap: Any) -> None:
    rows = btgap.parse_ledger_rows(as_dumped_rows(_events()))
    assert len(rows) == 12
    dedup = btgap.dedupe_ledger_rows(rows)
    assert len(dedup.events) == 6
    assert dedup.rows_in == 12
    assert dedup.rows_dropped == 6
    assert dedup.duplicate_groups == 6


def test_naive_sum_over_raw_rows_is_exactly_double(btgap: Any) -> None:
    """★dedup 을 건너뛰면 손익이 **정확히 2배**가 된다 (실측 −289.13 vs −144.57)."""
    rows = btgap.parse_ledger_rows(as_dumped_rows(_events()))
    dedup = btgap.dedupe_ledger_rows(rows)
    raw_total = btgap.sum_decimals([row.closed_pnl for row in rows])
    event_total = btgap.sum_decimals([event.closed_pnl for event in dedup.events])
    assert raw_total == event_total * Decimal("2")


def test_dedup_prefers_the_ours_row_and_is_deterministic(btgap: Any) -> None:
    rows = btgap.parse_ledger_rows(as_dumped_rows(_events()))
    dedup = btgap.dedupe_ledger_rows(rows)
    assert {event.classification for event in dedup.events} == {"ours"}
    assert [event.exit_id for event in dedup.events] == [
        event.exit_id for event in btgap.dedupe_ledger_rows(list(reversed(rows))).events
    ]


def test_rows_without_link_collapse_on_payload(btgap: Any) -> None:
    """`order_link_id` 가 없으면 payload 동등성으로 묶는다 — `id` 는 행마다 다르다."""
    event = exit_row(exit_id="x", order_link_id=None, closed_pnl="1.0")
    dedup = btgap.dedupe_ledger_rows(btgap.parse_ledger_rows(as_dumped_rows([event])))
    assert len(dedup.events) == 1


def test_report_records_dedup_counts(btgap: Any) -> None:
    report = _build(btgap)["report"]
    assert report["inputs"]["ledger_rows_in"] == 12
    assert report["inputs"]["ledger_events"] == 6
    assert report["inputs"]["ledger_rows_dropped"] == 6


# --------------------------------------------------------------------------
# R10 — 방향 부호는 원장 자신의 side 에서 온다
# --------------------------------------------------------------------------


def test_ledger_gross_sign_comes_from_the_exit_row_side(btgap: Any) -> None:
    long_close = btgap.parse_ledger_rows(
        [exit_row(exit_id="x", side="Sell", closed_pnl="1.0", avg_exit_price="60150")]
    )[0]
    short_close = btgap.parse_ledger_rows(
        [exit_row(exit_id="x", side="Buy", closed_pnl="1.0", avg_exit_price="60150")]
    )[0]
    assert btgap.derive_ledger_values(long_close) == (Decimal("1.50"), Decimal("1201.50"))
    assert btgap.derive_ledger_values(short_close)[0] == Decimal("-1.50")


def test_ledger_decomposes_without_any_close_order(btgap: Any) -> None:
    """★`matched_order_id` 우회가 사라졌다 — 청산 주문이 없어도 분해된다."""
    row = btgap.parse_ledger_rows(
        [exit_row(exit_id="x", matched_order_id=None, order_link_id=None, closed_pnl="1.0")]
    )[0]
    actual_gross, notional = btgap.derive_ledger_values(row)
    assert actual_gross is not None
    assert notional is not None


@pytest.mark.parametrize(
    "missing",
    [{"side": None}, {"closed_size": None}, {"avg_entry_price": None}, {"avg_exit_price": None}],
)
def test_missing_field_blocks_decomposition(btgap: Any, missing: dict[str, Any]) -> None:
    row = btgap.parse_ledger_rows([exit_row(exit_id="x", closed_pnl="1.0", **missing)])[0]
    assert btgap.derive_ledger_values(row) == (None, None)


def test_unknown_side_is_not_guessed(btgap: Any) -> None:
    row = btgap.parse_ledger_rows([exit_row(exit_id="x", side="???", closed_pnl="1.0")])[0]
    assert btgap.derive_ledger_values(row) == (None, None)


# --------------------------------------------------------------------------
# R7 — exits→orders 직결 · 수량은 Decimal 비교 · 가격은 판별자가 아니다
# --------------------------------------------------------------------------


def test_ledger_links_to_orders_by_order_link_id(btgap: Any) -> None:
    built = _build(btgap)
    linked = btgap.link_ledger_to_orders(built["dedup"].events, built["corpus"].by_id)
    assert linked["x1"].order_id == "o-c1"
    assert "x5" not in linked  # orders 에 없는 link 는 되짚지 못한다


@pytest.mark.parametrize("key_quantity", ["0.058", "0.05800000", "5.8E-2"])
def test_quantity_is_compared_as_decimal_not_string(btgap: Any, key_quantity: str) -> None:
    """★표기가 4가지다 — 문자열로 비교하면 같은 수량이 서로 다른 것이 된다."""
    corpus = btgap.parse_orders(
        [
            order_row(
                order_id="o-1",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(10), trigger="60000", quantity=key_quantity
                ),
                filled_quantity="0.058",
            )
        ],
        session_ids=[SESSION_ID],
    )
    trade = btgap.parse_backtest_trades(
        [trade_row(trade_index=0, entry_time=iso(10), size="0.05800000")]
    )[0]
    assert btgap.strict_key_matches(trade, corpus.entries[0], bar_seconds=BAR_SECONDS) is True


def test_price_is_not_a_matching_predicate(btgap: Any) -> None:
    """★가격이 트리거에서 크게 벗어나도 1차 키가 서면 붙는다 (판별력이 없기 때문)."""
    corpus = btgap.parse_orders(
        [
            order_row(
                order_id="o-1",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(10), trigger="60000", quantity="0.01"
                ),
            )
        ],
        session_ids=[SESSION_ID],
    )
    far = btgap.parse_backtest_trades(
        [trade_row(trade_index=0, entry_time=iso(10), entry_price="99999", size="0.01")]
    )[0]
    assert btgap.strict_key_matches(far, corpus.entries[0], bar_seconds=BAR_SECONDS) is True


def test_price_residual_is_reported_after_matching(btgap: Any) -> None:
    report = _build(btgap)["report"]
    residual = report["matching"]["price_residual"]
    assert residual["verdict"] == "measured"
    assert residual["n"] == 3
    assert residual["tolerance_pct"] == "0.100"


def test_price_residual_without_triggers_is_undetermined(btgap: Any) -> None:
    """트리거가 없으면 잔차 0% 가 아니라 「미판정」이다."""
    assert btgap.price_residuals([])["verdict"] == "undetermined"
    assert btgap.price_residuals([])["median_pct"] is None


# --------------------------------------------------------------------------
# R1 — strict / loose / ambiguous
# --------------------------------------------------------------------------


def test_strict_and_loose_pairs_are_graded_separately(btgap: Any) -> None:
    match = _build(btgap)["match"]
    assert [(pair.entry.order_id, pair.grade) for pair in match.pairs] == [
        ("o-e1", "strict"),
        ("o-e2", "loose"),
        ("o-e4", "strict"),
    ]
    assert [entry.order_id for entry in match.live_only] == ["o-e3"]
    assert [trade.trade_index for trade in match.backtest_only] == [2]


def test_judgement_uses_strict_only_and_loose_is_sensitivity(btgap: Any) -> None:
    built = _build(btgap)
    report = built["report"]
    # strict 2건만 판정 표본이다.
    assert report["sample"]["strict_pairs"] == 2
    assert report["sample"]["realized_observations"] == 2
    assert report["loose_sensitivity"]["matched_count"] == 3
    assert report["loose_sensitivity"]["note"].startswith("판정은 strict")


def test_trade_id_mismatch_blocks_both_grades(btgap: Any) -> None:
    corpus = btgap.parse_orders(
        [
            order_row(
                order_id="o-1",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(10), trigger="60000", quantity="0.01", trade_id="PivRevLE"
                ),
            )
        ],
        session_ids=[SESSION_ID],
    )
    other = btgap.parse_backtest_trades(
        [trade_row(trade_index=0, entry_time=iso(10), comment="PivRevSE")]
    )[0]
    entry = corpus.entries[0]
    assert btgap.strict_key_matches(other, entry, bar_seconds=BAR_SECONDS) is False
    assert btgap.loose_key_matches(other, entry, bar_seconds=BAR_SECONDS) is False


def test_missing_comment_cannot_be_strict(btgap: Any) -> None:
    """★없는 술어를 통과로 치지 않는다 — comment 가 없으면 1차 키를 세울 수 없다."""
    corpus = btgap.parse_orders(
        [
            order_row(
                order_id="o-1",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(10), trigger="60000", quantity="0.01"
                ),
            )
        ],
        session_ids=[SESSION_ID],
    )
    trade = btgap.parse_backtest_trades(
        [trade_row(trade_index=0, entry_time=iso(10), comment=None)]
    )[0]
    assert btgap.strict_key_matches(trade, corpus.entries[0], bar_seconds=BAR_SECONDS) is False


def test_quantity_mismatch_falls_out_of_strict_into_loose(btgap: Any) -> None:
    corpus = btgap.parse_orders(
        [
            order_row(
                order_id="o-1",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(10), trigger="60000", quantity="0.01"
                ),
            )
        ],
        session_ids=[SESSION_ID],
    )
    trade = btgap.parse_backtest_trades(
        [trade_row(trade_index=0, entry_time=iso(10), size="0.02")]
    )[0]
    entry = corpus.entries[0]
    assert btgap.strict_key_matches(trade, entry, bar_seconds=BAR_SECONDS) is False
    assert btgap.loose_key_matches(trade, entry, bar_seconds=BAR_SECONDS) is True


@pytest.mark.parametrize(
    ("offset_bars", "expected"),
    [(-4, False), (-3, True), (0, True), (3, True), (4, False)],
)
def test_loose_window_is_symmetric_three_bars(btgap: Any, offset_bars: int, expected: bool) -> None:
    corpus = btgap.parse_orders(
        [
            order_row(
                order_id="o-1",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(10), trigger="60000", quantity="0.01"
                ),
            )
        ],
        session_ids=[SESSION_ID],
    )
    trade = btgap.parse_backtest_trades(
        [trade_row(trade_index=0, entry_time=iso(10 + offset_bars))]
    )[0]
    assert btgap.loose_key_matches(trade, corpus.entries[0], bar_seconds=BAR_SECONDS) is expected


def test_two_strict_candidates_are_ambiguous_not_matched(btgap: Any) -> None:
    """★과잉 매칭은 fail-open — 억지로 하나 고르면 격차가 조용히 줄어든다."""
    corpus = btgap.parse_orders(
        [
            order_row(
                order_id="o-1",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(10), trigger="60000", quantity="0.01"
                ),
            )
        ],
        session_ids=[SESSION_ID],
    )
    trades = btgap.parse_backtest_trades(
        [
            trade_row(trade_index=0, entry_time=iso(10), entry_price="60000"),
            trade_row(trade_index=1, entry_time=iso(10), entry_price="60001"),
        ]
    )
    match = btgap.match_entries(trades, corpus.entries, bar_seconds=BAR_SECONDS)
    assert match.pairs == []
    assert [item.reason for item in match.ambiguous] == ["multiple_strict"]
    assert match.ambiguous[0].candidate_trade_indexes == [0, 1]


def test_two_live_entries_on_the_same_signal_bar_are_ambiguous(btgap: Any) -> None:
    corpus = btgap.parse_orders(
        [
            order_row(
                order_id="o-a",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(10), trigger="60000", quantity="0.01", trade_id="A"
                ),
            ),
            order_row(
                order_id="o-b",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(10), trigger="60000", quantity="0.01", trade_id="B"
                ),
            ),
        ],
        session_ids=[SESSION_ID],
    )
    trades = btgap.parse_backtest_trades([trade_row(trade_index=0, entry_time=iso(10))])
    match = btgap.match_entries(trades, corpus.entries, bar_seconds=BAR_SECONDS)
    assert match.pairs == []
    assert {item.reason for item in match.ambiguous} == {"live_key_collision"}
    assert len(match.ambiguous) == 2


def test_strict_pass_runs_before_loose_takes_candidates(btgap: Any) -> None:
    """loose 후보가 strict 쌍이 쓸 거래를 먼저 집어가면 판정 표본이 순서에 흔들린다."""
    corpus = btgap.parse_orders(
        [
            order_row(
                order_id="o-loose",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(9), trigger="60000", quantity="0.09"
                ),
            ),
            order_row(
                order_id="o-strict",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(10), trigger="60000", quantity="0.01"
                ),
            ),
        ],
        session_ids=[SESSION_ID],
    )
    trades = btgap.parse_backtest_trades(
        [trade_row(trade_index=0, entry_time=iso(10), size="0.01")]
    )
    match = btgap.match_entries(trades, corpus.entries, bar_seconds=BAR_SECONDS)
    assert [(pair.entry.order_id, pair.grade) for pair in match.pairs] == [("o-strict", "strict")]
    assert [entry.order_id for entry in match.live_only] == ["o-loose"]


def test_partial_fill_is_recorded_not_rejected(btgap: Any) -> None:
    corpus = btgap.parse_orders(
        [
            order_row(
                order_id="o-1",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(10), trigger="60000", quantity="0.05"
                ),
                filled_quantity="0.02",
            )
        ],
        session_ids=[SESSION_ID],
    )
    assert corpus.entries[0].partially_filled is True


# --------------------------------------------------------------------------
# 진입 판별 — 정본 술어 유지
# --------------------------------------------------------------------------


def test_close_orders_are_not_counted_as_entries(btgap: Any) -> None:
    corpus = _build(btgap)["corpus"]
    assert [entry.order_id for entry in corpus.entries] == ["o-e1", "o-e2", "o-e3", "o-e4"]
    assert [order.order_id for order in corpus.manual_flatten] == ["o-flat"]


def test_unfilled_entry_is_not_an_entry(btgap: Any) -> None:
    """`state == 'filled'` 가 아니라 `filled_quantity > 0` 이 판정자다 (레포 정본)."""
    corpus = btgap.parse_orders(
        [
            order_row(
                order_id="o-null-qty",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(1), trigger="60000", quantity="0.01"
                ),
                filled_quantity=None,
                state="filled",
            ),
            order_row(
                order_id="o-cancelled-with-fill",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(2), trigger="60000", quantity="0.01"
                ),
                filled_quantity="0.01",
                state="cancelled",
            ),
        ],
        session_ids=[SESSION_ID],
    )
    assert [entry.order_id for entry in corpus.entries] == ["o-cancelled-with-fill"]


def test_other_session_entry_is_ignored(btgap: Any) -> None:
    foreign = UUID("99999999-0000-4000-8000-000000000009")
    corpus = btgap.parse_orders(
        [
            order_row(
                order_id="o-foreign",
                side="buy",
                idempotency_key=conditional_entry_key(
                    bar_epoch=epoch(1), trigger="60000", quantity="0.01", session_id=foreign
                ),
            )
        ],
        session_ids=[SESSION_ID],
    )
    assert corpus.entries == []
    assert [order.order_id for order in corpus.other] == ["o-foreign"]


def test_market_entry_key_has_no_trigger(btgap: Any) -> None:
    corpus = btgap.parse_orders(
        [
            order_row(
                order_id="o-mkt",
                side="buy",
                idempotency_key=market_entry_key(bar_time_iso=iso(10)),
            )
        ],
        session_ids=[SESSION_ID],
    )
    entry = corpus.entries[0]
    assert entry.trigger is None
    assert entry.key_quantity is None
    assert entry.bar_epoch == epoch(10)
    # 수량을 안 싣는 key 는 1차 키를 세울 수 없다 → 보조 후보로만 붙는다.
    trade = btgap.parse_backtest_trades([trade_row(trade_index=0, entry_time=iso(10))])[0]
    assert btgap.strict_key_matches(trade, entry, bar_seconds=BAR_SECONDS) is False
    assert btgap.loose_key_matches(trade, entry, bar_seconds=BAR_SECONDS) is True


# --------------------------------------------------------------------------
# R2 — actual 축은 원장 순수 산술이다
# --------------------------------------------------------------------------


def test_actual_net_comes_from_the_ledger_not_the_order(btgap: Any) -> None:
    """`o-c1.realized_pnl = 99.9` 를 일부러 넣었다 — 보고서가 그걸 따라가면 안 된다."""
    report = _build(btgap)["report"]
    assert report["waterfall"]["stage_4_actual_net"] == "1.5"
    assert "99.9" not in json.dumps(report, ensure_ascii=False)


# --------------------------------------------------------------------------
# 존재 격차 · gross 복원 · 워터폴
# --------------------------------------------------------------------------


def test_existence_gap_never_folds_into_price_gap(btgap: Any) -> None:
    base = _build(btgap, trades=_trades()[:2] + _trades()[3:])["decomposition"]
    widened = _build(btgap)["decomposition"]
    assert base.summary.execution_gap == widened.summary.execution_gap
    assert base.backtest_only_expected_gross == Decimal("0")
    assert widened.backtest_only_expected_gross == Decimal("1.5")


def test_waterfall_closes_on_decomposable_strict_observations(btgap: Any) -> None:
    summary = _build(btgap)["decomposition"].summary
    # e1: gross 1.0 → agross 1.50 → net 1.3 · e4: gross 0.4 → agross 0.40 → net 0.2
    assert summary.decomposable_expected_gross == Decimal("1.4")
    assert summary.execution_gap == Decimal("0.5")
    assert summary.cost == Decimal("-0.4")
    assert summary.decomposable_actual_net == Decimal("1.5")
    assert (
        summary.decomposable_expected_gross + summary.execution_gap + summary.cost
        == summary.decomposable_actual_net
    )


def test_expected_gross_restores_net_plus_fees(btgap: Any) -> None:
    trade = btgap.parse_backtest_trades([trade_row(trade_index=0, pnl="0.4", fees="0.6")])[0]
    assert trade.expected_gross == Decimal("1.0")
    assert trade.expected_gross - trade.fees == trade.pnl


def test_expected_gross_holds_for_losing_trade(btgap: Any) -> None:
    trade = btgap.parse_backtest_trades([trade_row(trade_index=0, pnl="-1.5", fees="0.6")])[0]
    assert trade.expected_gross == Decimal("-0.9")
    assert trade.expected_gross - trade.fees == trade.pnl


def test_matched_pair_without_ledger_is_not_zero_filled(btgap: Any) -> None:
    decomposition = _build(btgap, events=[])["decomposition"]
    assert decomposition.strict_pairs == 2
    assert decomposition.observation_set.unrealized == 2
    assert decomposition.summary.matched_count == 0
    assert decomposition.summary.decomposable_expected_gross is None


# --------------------------------------------------------------------------
# R3 — ③ 이중 보고 + 상쇄 지수
# --------------------------------------------------------------------------


def test_cost_explanation_reports_both_definitions(btgap: Any) -> None:
    """★상쇄가 분모를 지워 사전등록 비율이 폭발한다 — 그래도 판정은 사전등록으로 한다."""
    ratio = _build(btgap)["report"]["waterfall"]["stage_3_cost"]["explanation_ratio"]
    # cost 항 = [-0.20, -0.20] · gap 항 = [-0.3, 0.2]
    assert ratio["n"] == 2
    assert Decimal(ratio["preregistered"]) == Decimal("4")
    assert Decimal(ratio["row_abs"]) == Decimal("0.8")
    assert Decimal(ratio["cancellation_index"]["numerator"]) == Decimal("0")
    assert Decimal(ratio["cancellation_index"]["denominator"]) == Decimal("0.8")
    assert ratio["verdict_definition"] == "preregistered"


def test_cancellation_index_is_undefined_on_an_all_zero_sample(btgap: Any) -> None:
    """0 으로 내면 「상쇄가 없다」로 읽힌다 — 그건 「잴 것이 없다」와 다르다."""
    assert btgap.cancellation_index([]) is None
    assert btgap.cancellation_index([Decimal("0"), Decimal("0")]) is None
    assert btgap.cancellation_index([Decimal("1"), Decimal("-1")]) == Decimal("1")
    assert btgap.cancellation_index([Decimal("1"), Decimal("1")]) == Decimal("0")


# --------------------------------------------------------------------------
# R4 — 커버리지 병기
# --------------------------------------------------------------------------


def test_coverage_is_reported_in_count_and_amount(btgap: Any) -> None:
    coverage = _build(btgap)["report"]["coverage"]
    assert coverage["matched_count"] == 2
    assert coverage["decomposable_count"] == 2
    assert Decimal(coverage["decomposable_count_pct"]) == Decimal("100")
    assert Decimal(coverage["decomposable_abs_net_pct"]) == Decimal("100")


def test_coverage_drops_when_an_event_cannot_be_decomposed(btgap: Any) -> None:
    events = _events()
    events[0] = {**events[0], "avg_exit_price": None}
    coverage = _build(btgap, events=events)["report"]["coverage"]
    assert coverage["matched_count"] == 2
    assert coverage["decomposable_count"] == 1
    assert Decimal(coverage["decomposable_count_pct"]) == Decimal("50")
    # 금액 커버리지는 절대값 기준 — 0.2 / (1.3 + 0.2).
    assert Decimal(coverage["decomposable_abs_net_pct"]) < Decimal("50")


# --------------------------------------------------------------------------
# R5 · R8 — 세션 경계 회계
# --------------------------------------------------------------------------


def test_session_json_accepts_one_object_or_a_list(btgap: Any) -> None:
    single = btgap.parse_sessions(session_row())
    listed = btgap.parse_sessions(_sessions())
    assert len(single) == 1
    assert [window.session_id for window in listed] == [str(SESSION_ID), str(SESSION_B_ID)]


def test_gap_exit_bucket_catches_the_no_session_interval(btgap: Any) -> None:
    accounting = _build(btgap)["report"]["session_accounting"]
    assert accounting["gap_exit"]["count"] == 1
    assert accounting["gap_exit"]["exit_ids"] == ["x4"]
    assert accounting["gap_exit"]["net"] == "0.2"


def test_unattributed_bucket_counts_rows_outside_every_window(btgap: Any) -> None:
    accounting = _build(btgap)["report"]["session_accounting"]
    assert accounting["unattributed"]["ledger_events"] == 1
    assert accounting["unattributed"]["ledger_net"] == "0.2"


def test_cross_window_event_is_named_with_its_holding_time(btgap: Any) -> None:
    """★반전 전략이라 진입창 ≠ 청산창이 실재한다 (실측 6건 · 최장 211분 보유)."""
    cross = _build(btgap)["report"]["session_accounting"]["cross_window"]
    assert cross["count"] == 1
    event = cross["events"][0]
    assert event["order_id"] == "o-e4"
    assert event["entry_session"] == str(SESSION_ID)
    assert event["exit_session"] is None
    assert event["held_seconds"] == 12 * 60


def test_attribution_defaults_to_exit_time_and_shows_the_alternative(btgap: Any) -> None:
    accounting = _build(btgap)["report"]["session_accounting"]
    assert accounting["attribution_rule"] == "exit_time"
    sensitivity = accounting["attribution_sensitivity"]
    # e4 의 0.2 는 청산시각 귀속에서 창 밖, 진입시각 귀속에서 세션 A 다.
    assert sensitivity["by_exit_window"]["__outside__"] == "0.2"
    assert str(SESSION_ID) not in sensitivity["by_exit_window"] or sensitivity[
        "by_exit_window"
    ].get(str(SESSION_ID)) != sensitivity["by_entry_window"].get(str(SESSION_ID))
    assert Decimal(sensitivity["max_abs_session_delta"]) > Decimal("0")


def test_carry_reports_both_ledgers_at_every_boundary(btgap: Any) -> None:
    carry = _build(btgap)["report"]["session_accounting"]["carry"]
    assert [row["session_id"] for row in carry] == [str(SESSION_ID), str(SESSION_B_ID)]
    assert carry[0]["live_net_at_start"] == "0"
    assert carry[0]["backtest_open_at_start"] == "0"
    # 세션 A 가 끝나는 00:40 에는 e4(0.04 롱)가 아직 열려 있다.
    assert Decimal(carry[0]["live_net_at_end"]) == Decimal("0.04")
    assert Decimal(carry[0]["backtest_open_at_end"]) == Decimal("0.04")


def test_between_windows_excludes_before_first_and_after_last(btgap: Any) -> None:
    windows = btgap.parse_sessions(_sessions())
    assert btgap.is_between_windows(at(50), windows) is True
    assert btgap.is_between_windows(at(-5), windows) is False
    assert btgap.is_between_windows(at(200), windows) is False
    assert btgap.is_between_windows(at(20), windows) is False


def test_flatten_is_counted_from_exits_not_orders(btgap: Any) -> None:
    """★실측: flatten 3 event 중 2건이 orders 에 없다 — orders 로 세면 과소계상된다."""
    flatten = _build(btgap)["report"]["buckets"]["manual_flatten"]
    assert flatten["count"] == 2
    assert flatten["from_order"] == 1  # o-flat 링크
    assert flatten["orphan_in_exits_only"] == 1  # o-ghost 링크 (orders 에 없다)
    assert flatten["net"] == "-1.2"


# --------------------------------------------------------------------------
# 보고서 계약
# --------------------------------------------------------------------------


def test_report_carries_every_required_section(btgap: Any) -> None:
    report = _build(btgap)["report"]
    assert report["sample"]["strict_pairs"] == 2
    assert report["sample"]["net_sample"]["n"] == 2
    assert report["time_range"]["backtest_first_entry"] == "2026-08-05T00:01:00Z"
    assert report["time_range"]["ledger_last"] == "2026-08-05T01:15:00Z"
    assert set(report["buckets"]) == {
        "matched",
        "backtest_only",
        "live_only",
        "manual_flatten",
        "ledger_only",
    }
    waterfall = report["waterfall"]
    assert waterfall["stage_1_expected_gross"] == "1.4"
    assert waterfall["stage_2_execution_gap"]["price_gap"] == "0.50"
    assert waterfall["stage_2_execution_gap"]["existence_gap"] == {
        "backtest_only_expected_gross": "1.5",
        "live_only_actual_net": "-0.5",
        "ledger_only_net": "-1.2",
    }
    assert waterfall["stage_3_cost"]["live_derived_cost"] == "-0.40"
    assert waterfall["stage_4_actual_net"] == "1.5"
    assert report["inputs"]["entry_kinds"] == {"cond": 4}


def test_report_carries_no_floats(btgap: Any) -> None:
    report = _build(btgap)["report"]
    assert collect_floats(json.loads(json.dumps(report))) == []


def test_cli_match_writes_report(btgap: Any, tmp_path: Any) -> None:
    (tmp_path / "orders.json").write_text(json.dumps(_orders()), encoding="utf-8")
    (tmp_path / "exits.json").write_text(json.dumps(as_dumped_rows(_events())), encoding="utf-8")
    (tmp_path / "session.json").write_text(json.dumps(_sessions()), encoding="utf-8")
    (tmp_path / "trades.json").write_text(json.dumps({"trades": _trades()}), encoding="utf-8")
    out = tmp_path / "report.json"
    assert (
        btgap.main(
            [
                "match",
                "--trades",
                str(tmp_path / "trades.json"),
                "--orders",
                str(tmp_path / "orders.json"),
                "--exits",
                str(tmp_path / "exits.json"),
                "--session",
                str(tmp_path / "session.json"),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["sample"]["strict_pairs"] == 2
    assert report["inputs"]["ledger_events"] == 6
    assert report["waterfall"]["stage_4_actual_net"] == "1.5"


def test_cli_match_rejects_mixed_intervals(btgap: Any, tmp_path: Any) -> None:
    sessions = _sessions()
    sessions[1] = {**sessions[1], "interval": "5m"}
    (tmp_path / "orders.json").write_text(json.dumps(_orders()), encoding="utf-8")
    (tmp_path / "exits.json").write_text(json.dumps(as_dumped_rows(_events())), encoding="utf-8")
    (tmp_path / "session.json").write_text(json.dumps(sessions), encoding="utf-8")
    (tmp_path / "trades.json").write_text(json.dumps({"trades": _trades()}), encoding="utf-8")
    with pytest.raises(ValueError, match="interval 이 갈린다"):
        btgap.main(
            [
                "match",
                "--trades",
                str(tmp_path / "trades.json"),
                "--orders",
                str(tmp_path / "orders.json"),
                "--exits",
                str(tmp_path / "exits.json"),
                "--session",
                str(tmp_path / "session.json"),
                "--out",
                str(tmp_path / "report.json"),
            ]
        )
