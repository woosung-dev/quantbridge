"""`btgap_compare.py replay` — 라이브 프로토콜 재생이 **무엇을 재는지** 못박는다.

R 은 「롤링 300봉 창의 몫」을 분리하려고 만든 집합이다. 그래서 이 파일이 지키는 것은
정확도가 아니라 **통제**다 — 통제가 깨지면 숫자는 나오지만 그 숫자가 무엇의 몫인지
아무도 모른다.

1. **마지막 봉만 채택.** 창 중간 봉의 이벤트가 섞이면 R 은 「매 tick 재생」이 아니라
   「전 구간 백테스트를 창 단위로 자른 것」이 된다 — 그건 B 와 같은 것이다.
2. **창 크기 준수.** 창이 안 차는 초기 봉을 평가하면 라이브가 본 적 없는 과거로
   신호를 만든다.
3. ★**원장 인자 4종 미주입.** 이게 실험의 통제 그 자체다. `ledger_conditional_fills`
   가 하나라도 들어가면 조건부 체결 권한이 원장으로 넘어가(ADR-025) R 은
   「롤링 창 + 원장 권한」의 몫이 된다. **호출 kwargs 를 직접 본다** — 산문으로
   "안 넣었다" 를 적는 것과 호출을 보는 것은 다르다.
4. **결정론.** 같은 입력 2회 → 같은 digest (사전등록 ④(a)).

★DB 도 네트워크도 celery 도 타지 않는다. 엔진(`run_live`)만 in-process 로 부른다.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.scripts.btgap_fixtures import load_script

BASE = datetime(2026, 8, 5, 0, 0, tzinfo=UTC)

# 창의 **마지막** 봉에서만 진입한다 — 창 크기 4 면 매 평가마다 1건.
LAST_BAR_PINE = """//@version=5
strategy("replay fixture — last bar")
if bar_index == 3
    strategy.entry("L", strategy.long)
"""

# 창의 **두 번째** 봉에서만 진입한다 — 창 크기 4 면 마지막 봉이 아니라 절대 안 잡힌다.
MID_BAR_PINE = """//@version=5
strategy("replay fixture — mid bar")
if bar_index == 1
    strategy.entry("L", strategy.long)
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

WINDOW_BARS = 4


@pytest.fixture(scope="module")
def btgap() -> Any:
    return load_script("btgap_compare")


def _bar_time(index: int) -> str:
    return (BASE + timedelta(minutes=index)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_inputs(tmp_path: Path, *, pine: str = LAST_BAR_PINE) -> None:
    lines = ["timestamp,open,high,low,close,volume"]
    for index, (open_, high, low, close) in enumerate(FIXTURE_BARS):
        lines.append(f"{_bar_time(index)},{open_},{high},{low},{close},10")
    (tmp_path / "ohlcv.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (tmp_path / "strategy.pine").write_text(pine, encoding="utf-8")


def _argv(tmp_path: Path, *, out_name: str, extra: list[str] | None = None) -> list[str]:
    return [
        "replay",
        "--pine-source",
        str(tmp_path / "strategy.pine"),
        "--ohlcv-csv",
        str(tmp_path / "ohlcv.csv"),
        "--freq",
        "1m",
        "--leverage",
        "1.0",
        "--window-bars",
        str(WINDOW_BARS),
        "--out",
        str(tmp_path / out_name),
    ] + (extra or [])


def _replay(
    btgap: Any,
    tmp_path: Path,
    *,
    pine: str = LAST_BAR_PINE,
    out_name: str = "replay.json",
    extra: list[str] | None = None,
) -> dict[str, Any]:
    _write_inputs(tmp_path, pine=pine)
    assert btgap.main(_argv(tmp_path, out_name=out_name, extra=extra)) == 0
    payload: dict[str, Any] = json.loads((tmp_path / out_name).read_text(encoding="utf-8"))
    return payload


# --------------------------------------------------------------------------
# 1. 마지막 봉만 채택
# --------------------------------------------------------------------------


def test_last_bar_signal_is_adopted(btgap: Any, tmp_path: Path) -> None:
    """창의 마지막 봉에서 나는 진입은 평가한 봉 수만큼 잡힌다."""
    payload = _replay(btgap, tmp_path)

    assert payload["bars_evaluated"] == len(FIXTURE_BARS) - WINDOW_BARS + 1
    entry_rows = [row for row in payload["entries"] if row["kind"] == "entry"]
    assert len(entry_rows) == payload["bars_evaluated"]
    # 신호봉 = 창의 마지막 봉이다. 첫 평가는 index 3.
    assert entry_rows[0]["bar_time"] == _bar_time(WINDOW_BARS - 1)


def test_mid_window_signal_is_not_adopted(btgap: Any, tmp_path: Path) -> None:
    """★음성 대조 — 창 **중간** 봉의 이벤트는 하나도 새지 않는다.

    같은 CSV·같은 창인데 Pine 이 보는 봉만 다르다. 이 짝이 갈리지 않으면
    「마지막 봉만 채택」은 검증된 적이 없는 문장이다.
    """
    payload = _replay(btgap, tmp_path, pine=MID_BAR_PINE)

    assert payload["bars_evaluated"] == len(FIXTURE_BARS) - WINDOW_BARS + 1
    assert payload["entries"] == []
    assert payload["entries_by_kind"] == {"cond": 0, "entry": 0, "fill": 0}


# --------------------------------------------------------------------------
# 2. 창 크기
# --------------------------------------------------------------------------


def test_short_window_bars_are_not_evaluated(btgap: Any, tmp_path: Path) -> None:
    """창이 안 차는 초기 봉(index < window−1)은 평가 대상이 아니다."""
    payload = _replay(btgap, tmp_path)

    assert payload["bars_total"] == len(FIXTURE_BARS)
    assert payload["bars_skipped_short_window"] == WINDOW_BARS - 1
    assert payload["bars_evaluated"] + payload["bars_skipped_short_window"] == len(FIXTURE_BARS)
    evaluated_epochs = {row["bar_time"] for row in payload["entries"]}
    assert all(time >= _bar_time(WINDOW_BARS - 1) for time in evaluated_epochs)


def test_scoring_window_limits_evaluated_bars(btgap: Any, tmp_path: Path) -> None:
    """`--start`/`--end` 는 **평가하는 봉**을 자른다 (산출 뒤 필터가 아니다)."""
    payload = _replay(
        btgap,
        tmp_path,
        extra=["--start", _bar_time(5), "--end", _bar_time(7)],
    )

    assert payload["bars_evaluated"] == 2
    assert payload["bars_outside_scoring_window"] == 3
    assert {row["bar_time"] for row in payload["entries"]} == {_bar_time(5), _bar_time(6)}


def test_window_slice_length_is_exactly_window_bars(
    btgap: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """엔진이 실제로 받은 프레임의 길이가 창 크기와 같다.

    `bars_evaluated` 만 보면 「창을 잘랐다」가 아니라 「루프를 돌았다」만 증명된다.
    """
    from src.strategy.pine_v2 import event_loop

    seen: list[int] = []
    real_run_live = event_loop.run_live

    def _spy(source: str, ohlcv: Any, **kwargs: Any) -> Any:
        seen.append(len(ohlcv))
        return real_run_live(source, ohlcv, **kwargs)

    monkeypatch.setattr(event_loop, "run_live", _spy)
    _replay(btgap, tmp_path)

    assert seen == [WINDOW_BARS] * (len(FIXTURE_BARS) - WINDOW_BARS + 1)


# --------------------------------------------------------------------------
# 3. ★원장 인자 4종 미주입 — 실험의 통제
# --------------------------------------------------------------------------

LEDGER_ARGUMENTS = (
    "ledger_seed_legs",
    "ledger_conditional_fills",
    "position_epoch",
    "emit_from_bar_time",
)


def _capture_run_live_kwargs(
    btgap: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> list[dict[str, Any]]:
    from src.strategy.pine_v2 import event_loop

    calls: list[dict[str, Any]] = []
    real_run_live = event_loop.run_live

    def _spy(source: str, ohlcv: Any, **kwargs: Any) -> Any:
        calls.append(dict(kwargs))
        return real_run_live(source, ohlcv, **kwargs)

    monkeypatch.setattr(event_loop, "run_live", _spy)
    _replay(btgap, tmp_path)
    return calls


def test_ledger_arguments_are_never_passed_to_run_live(
    btgap: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """★원장 인자 4종은 **키 자체가 없어야** 한다.

    `None` 을 넘기는 것과 안 넘기는 것은 `run_live` 안에서 다르다:
    `ledger_conditional_fills=None` 은 「원장을 못 읽었다」라는 3-상태의 한 값이고,
    미주입은 호출 형태가 기존과 byte-identical 이라는 계약이다
    (`event_loop.py:508-513`). 그래서 값이 아니라 **키**를 본다.
    """
    calls = _capture_run_live_kwargs(btgap, tmp_path, monkeypatch)

    assert calls, "run_live 가 한 번도 안 불렸다 — 이 테스트는 아무것도 증명하지 못한다"
    for kwargs in calls:
        for name in LEDGER_ARGUMENTS:
            assert name not in kwargs, f"{name} 이 run_live 호출에 실렸다"


def test_injected_arguments_are_exactly_the_five(
    btgap: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """주입 5종만 넘어간다 — 세트가 자라면 여기서 걸린다."""
    calls = _capture_run_live_kwargs(btgap, tmp_path, monkeypatch)

    assert calls
    for kwargs in calls:
        assert set(kwargs) == {
            "initial_capital",
            "live_position_size_pct",
            "leverage",
            "pyramiding",
            "fill_timing",
        }


def test_ledger_arguments_are_named_in_the_output(btgap: Any, tmp_path: Path) -> None:
    """산출물만 봐도 「무엇을 안 넣었나」를 알 수 있어야 한다."""
    payload = _replay(btgap, tmp_path)

    assert payload["params"]["ledger_arguments_omitted"] == list(LEDGER_ARGUMENTS)


# --------------------------------------------------------------------------
# 4. 결정론 (사전등록 ④(a))
# --------------------------------------------------------------------------


def test_same_input_yields_same_digest(btgap: Any, tmp_path: Path) -> None:
    first = _replay(btgap, tmp_path, out_name="a.json")
    second = _replay(btgap, tmp_path, out_name="b.json")

    assert first["digest"] == second["digest"]
    assert first["entries"] == second["entries"]


def test_window_size_change_moves_the_digest(btgap: Any, tmp_path: Path) -> None:
    """★음성 대조 — digest 가 **아무것에도 안 반응하면** 결정론 증명이 공허하다."""
    first = _replay(btgap, tmp_path, out_name="a.json")
    second = _replay(btgap, tmp_path, out_name="b.json", extra=["--window-bars", "5"])

    assert first["digest"] != second["digest"]
