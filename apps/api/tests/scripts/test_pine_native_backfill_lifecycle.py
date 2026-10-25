"""정상 UI 범위 확대의 명시적 재계산은 기존 확정 행과 합집합을 이룬다.

실측 근거: expansion-v5/browser-queue/native-101-basic-hz-prefixrange.result.json
SHA256 faf965e2fd8075352bbe9cc56c75d079caf6e4db6b74bf7d465872f44fa187c8.
동일 create/token의 1860행 뒤 184행 prefix를 받았고, 겹친 100행은 모두 같아
합집합은 1944행이었다. 마지막 lifecycle만 남기면 정상 이력을 잃는다.
아래는 기존 공개 synthetic fixture를 축약하며 비공개 IL/원문을 복제하지 않는다.
"""

import copy

import pytest

from scripts.pine_validation.native_capture import _frames
from tests.scripts.test_pine_native_account_limit import parse
from tests.scripts.test_pine_validation_native_capture import T0, _frame, _payload

TOKEN = "s2_st1"


def _wire(direction, *messages):
    return {"direction": direction, "data": "".join(_frame(message) for message in messages)}


def _loading(token=TOKEN):
    return {"m": "study_loading", "p": ["cs", "study", token]}


def _completed(token=TOKEN):
    return {"m": "study_completed", "p": ["cs", "study", token]}


def _modify(timeframe="60", chart="chart"):
    return {
        "m": "modify_series",
        "p": ["cs", chart, "s2", "symbol", timeframe, f"r,{T0 - 3600}:{T0 + 7200}"],
    }


def _two_cycles():
    raw = _payload(price_method="timescale_update")
    complete, study, prices = _frames(raw["wire"][1]["data"])
    assert complete == _completed()
    study["p"][1]["study"]["t"] = TOKEN
    prices["p"][1]["chart"]["t"] = "s2"
    prefix_study = {
        "m": "du",
        "p": [
            "cs",
            {"study": {"t": TOKEN, "st": [{"i": -1, "v": [T0 - 3600, 0, 100, 100]}]}},
        ],
    }
    prefix_prices = {
        "m": "timescale_update",
        "p": [
            "cs",
            {"chart": {"t": "s2", "s": [{"i": -1, "v": [T0 - 3600, 99, 101, 98, 100, 9]}]}},
        ],
    }
    initial = _modify()
    initial["p"][5] = ""
    raw["wire"][0:0] = [_wire("sent", initial)]
    raw["wire"][2:] = [
        _wire("received", _loading(), study, prices, _completed()),
        _wire("sent", _modify()),
        _wire("received", _loading(), prefix_study, prefix_prices, _completed()),
    ]
    return raw


def _replace_last(raw, messages):
    raw["wire"][-1] = _wire("received", *messages)


def test_explicit_same_token_backfill_keeps_both_completed_lifecycles():
    native = parse(_two_cycles())
    assert len(native.ohlcv) == 3
    assert native.ohlcv["close"].tolist() == [100, 101, 102]
    assert native.metadata["total_received_bars"] == 3
    assert native.metadata["full_study_prefix_covered"] is True


def test_identical_overlap_between_lifecycles_is_not_a_conflicting_duplicate():
    raw = _two_cycles()
    messages = _frames(raw["wire"][-1]["data"])
    original = _frames(raw["wire"][2]["data"])[1]["p"][1]["study"]["st"][0]
    messages[1]["p"][1]["study"]["st"].append(copy.deepcopy(original))
    _replace_last(raw, messages)
    assert len(parse(raw).ohlcv) == 3


def test_two_completions_without_second_explicit_loading_are_rejected():
    raw = _two_cycles()
    messages = _frames(raw["wire"][-1]["data"])
    _replace_last(raw, messages[1:])
    with pytest.raises(ValueError):
        parse(raw)


def test_unfinished_second_loading_cannot_fall_back_to_previous_completion():
    raw = _two_cycles()
    messages = _frames(raw["wire"][-1]["data"])
    _replace_last(raw, messages[:-1])
    with pytest.raises(ValueError):
        parse(raw)


def test_loading_and_completion_token_mismatch_is_rejected():
    raw = _two_cycles()
    messages = _frames(raw["wire"][-1]["data"])
    messages[-1] = _completed("different-token")
    _replace_last(raw, messages)
    with pytest.raises(ValueError):
        parse(raw)


def test_closed_study_conflict_remains_rejected_across_explicit_loading():
    raw = _two_cycles()
    messages = _frames(raw["wire"][-1]["data"])
    original = copy.deepcopy(_frames(raw["wire"][2]["data"])[1]["p"][1]["study"]["st"][0])
    original["v"][1] = 0
    messages[1]["p"][1]["study"]["st"].append(original)
    _replace_last(raw, messages)
    with pytest.raises(ValueError):
        parse(raw)


@pytest.mark.parametrize("change", ["missing_request", "wrong_timeframe", "wrong_chart"])
def test_backfill_requires_matching_chart_timeframe_ui_request(change):
    raw = _two_cycles()
    if change == "missing_request":
        raw["wire"].pop(-2)
    else:
        raw["wire"][-2] = _wire(
            "sent",
            _modify(
                timeframe="240" if change == "wrong_timeframe" else "60",
                chart="other" if change == "wrong_chart" else "chart",
            ),
        )
    with pytest.raises(ValueError):
        parse(raw)


def test_generic_single_completion_without_loading_keeps_legacy_contract():
    assert len(parse(_payload()).ohlcv) == 2
