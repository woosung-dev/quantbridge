"""`btgap_compare.py run` — 엔진 재실행 산출물의 **결정론**과 필드 계약.

## 왜 digest 인가

대조의 모든 결론은 `trades.json` 위에 선다. 그 파일이 같은 입력에서 두 번 다르게
나오면 뒤의 4단 분해는 **무엇을 재는지 모르는 채로** 숫자를 낸다. digest 는 그것을
한 줄로 잡는 장치다 — 창을 바꾸거나 데이터를 바꾸면 반드시 바뀌고, 아무것도 안 바꾸면
반드시 같아야 한다.

★네트워크도 DB 도 celery 도 타지 않는다. 엔진(`run_backtest_v2`)만 직접 호출한다 —
이건 celery 경유가 아니라 in-process 순수 실행이라 워크트리에서도 내 코드가 돈다.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from tests.scripts.btgap_fixtures import load_script

BASE = datetime(2026, 8, 5, 0, 0, tzinfo=UTC)

FIXTURE_PINE = """//@version=5
strategy("btgap fixture")
if bar_index == 1
    strategy.entry("L", strategy.long)
if bar_index == 4
    strategy.close("L")
if bar_index == 5
    strategy.entry("S", strategy.short)
if bar_index == 7
    strategy.close("S")
"""

# (open, high, low, close) — OHLC 불변식을 만족하는 결정적 8봉.
FIXTURE_BARS = [
    (100, 101, 99, 100),
    (100, 102, 99, 101),
    (101, 103, 100, 102),
    (102, 104, 101, 103),
    (103, 105, 102, 104),
    (104, 106, 103, 105),
    (105, 107, 104, 104),
    (104, 106, 103, 103),
]


@pytest.fixture(scope="module")
def btgap() -> Any:
    return load_script("btgap_compare")


def _bar_time(index: int) -> str:
    return (BASE + timedelta(minutes=index)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_inputs(
    tmp_path: Path,
    *,
    bars: list[tuple[int, int, int, int]] | None = None,
    pine: str = FIXTURE_PINE,
) -> Path:
    rows = FIXTURE_BARS if bars is None else bars
    lines = ["timestamp,open,high,low,close,volume"]
    for index, (open_, high, low, close) in enumerate(rows):
        lines.append(f"{_bar_time(index)},{open_},{high},{low},{close},10")
    (tmp_path / "ohlcv.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (tmp_path / "strategy.pine").write_text(pine, encoding="utf-8")
    return tmp_path


def _argv(
    tmp_path: Path,
    *,
    out_name: str,
    start: str | None,
    end: str | None,
    allow_empty: bool,
    extra: list[str] | None = None,
) -> list[str]:
    argv = [
        "run",
        "--pine-source",
        str(tmp_path / "strategy.pine"),
        "--ohlcv-csv",
        str(tmp_path / "ohlcv.csv"),
        "--freq",
        "1m",
        "--leverage",
        "2.0",
        "--out",
        str(tmp_path / out_name),
    ]
    if start is not None:
        argv += ["--start", start]
    if end is not None:
        argv += ["--end", end]
    if allow_empty:
        argv.append("--allow-empty-trades")
    argv += extra or []
    return argv


def _run(
    btgap: Any,
    tmp_path: Path,
    *,
    out_name: str = "trades.json",
    start: str | None = None,
    end: str | None = None,
    allow_empty: bool = False,
    extra: list[str] | None = None,
) -> dict[str, Any]:
    argv = _argv(
        tmp_path,
        out_name=out_name,
        start=start,
        end=end,
        allow_empty=allow_empty,
        extra=extra,
    )
    assert btgap.main(argv) == 0
    payload: dict[str, Any] = json.loads((tmp_path / out_name).read_text(encoding="utf-8"))
    return payload


# --------------------------------------------------------------------------
# 결정론
# --------------------------------------------------------------------------


def test_same_input_yields_same_digest(btgap: Any, tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    first = _run(btgap, tmp_path, out_name="a.json")
    second = _run(btgap, tmp_path, out_name="b.json")
    assert first["trades_digest"] == second["trades_digest"]
    assert first["trades"] == second["trades"]


def test_changed_ohlcv_changes_digest(btgap: Any, tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    baseline = _run(btgap, tmp_path, out_name="a.json")
    moved = list(FIXTURE_BARS)
    moved[4] = (103, 109, 102, 108)
    _write_inputs(tmp_path, bars=moved)
    changed = _run(btgap, tmp_path, out_name="b.json")
    assert changed["trades_digest"] != baseline["trades_digest"]


def test_digest_is_stable_under_key_order(btgap: Any) -> None:
    """직렬화 정렬이 고정이라 dict 키 순서는 digest 를 흔들지 못한다."""
    forward = [{"a": "1", "b": "2"}]
    shuffled = [{"b": "2", "a": "1"}]
    assert btgap.trades_digest(forward) == btgap.trades_digest(shuffled)
    assert btgap.trades_digest(forward) != btgap.trades_digest([{"a": "1", "b": "3"}])


# --------------------------------------------------------------------------
# 필드 계약
# --------------------------------------------------------------------------


def test_trades_carry_every_required_field(btgap: Any, tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    payload = _run(btgap, tmp_path)
    assert payload["trades_total"] == 2
    required = {
        "trade_index",
        "direction",
        "status",
        "entry_time",
        "exit_time",
        "entry_price",
        "exit_price",
        "size",
        "pnl",
        "fees",
        "fee_paid",
        "slippage_paid",
        "comment",
        "exit_kind",
    }
    for trade in payload["trades"]:
        assert required <= set(trade)
    directions = [trade["direction"] for trade in payload["trades"]]
    assert directions == ["long", "short"]
    assert payload["trades"][0]["entry_time"] == _bar_time(1)
    assert payload["trades"][0]["exit_time"] == _bar_time(4)
    assert payload["metrics"]["num_trades"] == 2
    assert payload["leverage"] == 2.0
    assert payload["bars"] == len(FIXTURE_BARS)


def test_cost_split_reconstructs_the_combined_fee(btgap: Any, tmp_path: Path) -> None:
    """`fee_paid + slippage_paid == fees` — 3단 계약의 비용 불변식."""
    from decimal import Decimal

    _write_inputs(tmp_path)
    payload = _run(btgap, tmp_path)
    for trade in payload["trades"]:
        assert Decimal(trade["fee_paid"]) + Decimal(trade["slippage_paid"]) == Decimal(
            trade["fees"]
        )


def test_run_output_feeds_match_parser(btgap: Any, tmp_path: Path) -> None:
    """`run` 산출물이 `match` 의 파서로 그대로 들어간다 (두 명령의 계약 일치)."""
    _write_inputs(tmp_path)
    payload = _run(btgap, tmp_path)
    trades = btgap.parse_backtest_trades(payload["trades"])
    assert [trade.direction for trade in trades] == ["long", "short"]
    assert trades[0].expected_gross - trades[0].fees == trades[0].pnl


# --------------------------------------------------------------------------
# 채점 창
# --------------------------------------------------------------------------


def test_scoring_window_filters_trades_but_keeps_the_total(btgap: Any, tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    payload = _run(btgap, tmp_path, start=_bar_time(3).replace("Z", "+00:00"))
    assert payload["trades_total"] == 2
    assert payload["trades_in_window"] == 1
    assert [trade["direction"] for trade in payload["trades"]] == ["short"]
    assert payload["scoring_window"]["start"] == _bar_time(3)


def test_scoring_window_end_is_exclusive(btgap: Any, tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    payload = _run(btgap, tmp_path, end=_bar_time(5).replace("Z", "+00:00"))
    # 숏 진입은 bar 5 다 — end 가 배타이므로 빠진다.
    assert [trade["direction"] for trade in payload["trades"]] == ["long"]


def test_window_changes_digest(btgap: Any, tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    whole = _run(btgap, tmp_path, out_name="a.json")
    windowed = _run(btgap, tmp_path, out_name="b.json", start=_bar_time(3).replace("Z", "+00:00"))
    assert whole["trades_digest"] != windowed["trades_digest"]


# --------------------------------------------------------------------------
# ★거짓 0 차단 — leverage > 1 의 격리 증거금 게이트
# --------------------------------------------------------------------------

NO_ENTRY_PINE = """//@version=5
strategy("btgap no entry")
plot(close)
"""

# 자본 10,000 · qty 1.0 · leverage 2 → required_margin = 30,000 > 10,000 ⇒ 전건 거절.
HIGH_PRICE_BARS = [
    (60000, 60100, 59900, 60000),
    (60000, 60200, 59900, 60100),
    (60100, 60300, 60000, 60200),
    (60200, 60400, 60100, 60300),
    (60300, 60500, 60200, 60400),
    (60400, 60600, 60300, 60500),
    (60500, 60700, 60400, 60400),
    (60400, 60600, 60300, 60300),
]


def test_zero_trade_run_is_refused_and_writes_nothing(btgap: Any, tmp_path: Path) -> None:
    """거래 0 건짜리 산출물은 뒤의 `match` 를 「라이브에만 있다」로 도배한다."""
    _write_inputs(tmp_path, pine=NO_ENTRY_PINE)
    argv = _argv(tmp_path, out_name="trades.json", start=None, end=None, allow_empty=False)
    assert btgap.main(argv) == 1
    assert not (tmp_path / "trades.json").exists()


def test_zero_trade_run_can_be_opted_into(btgap: Any, tmp_path: Path) -> None:
    _write_inputs(tmp_path, pine=NO_ENTRY_PINE)
    payload = _run(btgap, tmp_path, allow_empty=True)
    assert payload["trades_total"] == 0
    assert payload["warnings"]["margin_insufficient"] == 0


def test_margin_gate_zero_is_named_not_silent(btgap: Any, tmp_path: Path, capsys: Any) -> None:
    """★leverage=2.0 + 기본 사이징은 BTC 가격에서 **전건 거절**된다 (실측)."""
    _write_inputs(tmp_path, bars=HIGH_PRICE_BARS)
    argv = _argv(tmp_path, out_name="trades.json", start=None, end=None, allow_empty=False)
    assert btgap.main(argv) == 1
    assert not (tmp_path / "trades.json").exists()
    stderr = capsys.readouterr().err
    assert "증거금" in stderr
    assert "leverage" in stderr


def test_margin_gate_count_is_recorded_in_the_output(btgap: Any, tmp_path: Path) -> None:
    _write_inputs(tmp_path, bars=HIGH_PRICE_BARS)
    payload = _run(btgap, tmp_path, allow_empty=True)
    assert payload["trades_total"] == 0
    assert payload["warnings"]["margin_insufficient"] > 0
    assert payload["warnings"]["total"] >= payload["warnings"]["margin_insufficient"]
    assert any("증거금" in line for line in payload["warnings"]["sample"])


def test_same_bars_at_leverage_one_do_trade(btgap: Any, tmp_path: Path) -> None:
    """음성 대조 — 게이트가 꺼지면(leverage=1) 같은 데이터가 거래를 낸다."""
    _write_inputs(tmp_path, bars=HIGH_PRICE_BARS)
    argv = _argv(tmp_path, out_name="trades.json", start=None, end=None, allow_empty=False)
    argv[argv.index("--leverage") + 1] = "1.0"
    assert btgap.main(argv) == 0
    payload = json.loads((tmp_path / "trades.json").read_text(encoding="utf-8"))
    assert payload["trades_total"] == 2
    assert payload["warnings"]["margin_insufficient"] == 0


# --------------------------------------------------------------------------
# 라이브 미러 사이징 (R9) — 1x 기준 percent_of_equity
# --------------------------------------------------------------------------

# 세션 equity baseline 실측 대역(190,220~190,330)의 아래끝.
LIVE_BASELINE = "190220"
LIVE_MIRROR = ["--init-cash", LIVE_BASELINE, "--live-position-size-pct", "1.0"]


def test_default_run_keeps_fallback_sizing(btgap: Any, tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    sizing = _run(btgap, tmp_path)["sizing"]
    assert sizing["sizing_source"] == "fallback"
    assert sizing["live_position_size_pct"] is None
    assert Decimal(sizing["init_cash"]) == Decimal("10000")


def test_live_mirror_flags_reach_the_engine_config(btgap: Any, tmp_path: Path) -> None:
    _write_inputs(tmp_path)
    sizing = _run(btgap, tmp_path, extra=LIVE_MIRROR)["sizing"]
    assert sizing["sizing_source"] == "live"
    assert sizing["sizing_basis"] == "live_available_balance_approx_equity"
    assert sizing["live_position_size_pct"] == 1.0
    assert Decimal(sizing["init_cash"]) == Decimal(LIVE_BASELINE)


def test_live_mirror_sizing_clears_the_margin_gate(btgap: Any, tmp_path: Path) -> None:
    """★§4 의 거짓 0 을 **사이징으로** 푼다 — leverage 는 2.0 그대로다."""
    _write_inputs(tmp_path, bars=HIGH_PRICE_BARS)
    argv = _argv(
        tmp_path,
        out_name="trades.json",
        start=None,
        end=None,
        allow_empty=False,
        extra=LIVE_MIRROR,
    )
    assert argv[argv.index("--leverage") + 1] == "2.0"
    assert btgap.main(argv) == 0
    payload = json.loads((tmp_path / "trades.json").read_text(encoding="utf-8"))
    assert payload["trades_total"] == 2
    assert payload["warnings"]["margin_insufficient"] == 0


def test_live_mirror_qty_tracks_equity_times_pct(btgap: Any, tmp_path: Path) -> None:
    """qty ≈ equity × pct / 진입가 — 라이브 명목(≈1,856 USDT)과 같은 자리에 온다."""
    _write_inputs(tmp_path, bars=HIGH_PRICE_BARS)
    payload = _run(btgap, tmp_path, extra=LIVE_MIRROR)
    trade = payload["trades"][0]
    notional = Decimal(trade["size"]) * Decimal(trade["entry_price"])
    assert Decimal("1800") < notional < Decimal("2000")


def test_live_mirror_changes_the_digest(btgap: Any, tmp_path: Path) -> None:
    """사이징이 결과를 바꾸므로 digest 도 바뀌어야 한다 — 안 바뀌면 플래그가 죽은 것이다."""
    _write_inputs(tmp_path)
    baseline = _run(btgap, tmp_path, out_name="a.json")
    mirrored = _run(btgap, tmp_path, out_name="b.json", extra=LIVE_MIRROR)
    assert baseline["trades_digest"] != mirrored["trades_digest"]
