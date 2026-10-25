"""실제 compiler의 source 기본값·빈 study resolution 자동 slot만 허용한다."""

import hashlib

import pytest

from scripts.pine_validation.native_capture import _plot_bindings, _source_calls
from tests.scripts.test_pine_validation_native_capture import (
    BINDINGS,
    SOURCE,
    _frame,
    _parse,
    _payload,
)


@pytest.mark.parametrize(
    "call", ("input({default})", "input({default}, type=input.source)", "input.source({default})")
)
@pytest.mark.parametrize("default", ("close", "volume"))
def test_builtin_source_names_are_supported_for_generic_and_explicit_input(call, default):
    source = f'//@version=4\nstudy("Source")\nsrc = {call.format(default=default)}\n'
    assert _source_calls(source)[1] == [("src", "src", default)]


@pytest.mark.parametrize("default", ("unknown", "close + open", "hl2[1]"))
def test_source_defaults_still_reject_unknown_names_or_expressions(default):
    for call in (f"input({default})", f"input({default}, type=input.source)"):
        with pytest.raises(ValueError):
            _source_calls(f'//@version=4\nstudy("Source")\nsrc = {call}\n')


def resolution_payload(header='study("demo", resolution="")'):
    source = SOURCE.replace('indicator("demo")', header)
    payload = _payload()
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
    )
    meta = payload["compile_responses"][0]["data"]["result"]["metaInfo"]
    meta["inputs"].append(
        {
            "id": "in_1",
            "name": "Indicator Timeframe",
            "type": "resolution",
            "inline": "study_mtf",
            "isMTFResolution": True,
            "isFake": True,
            "defval": "",
        }
    )
    create = {
        "m": "create_study",
        "p": [
            "cs",
            "study",
            "st1",
            "chart",
            "script",
            {
                "text": "compiled-il",
                "in_0": {"v": 2},
                "in_1": {"v": "", "f": True, "t": "resolution"},
            },
        ],
    }
    payload["wire"][0]["data"] = _frame(create)
    return source, payload, meta, create


def test_only_observed_empty_resolution_slot_is_accepted():
    source, payload, _, _ = resolution_payload()
    assert len(_parse(payload, source=source).events) == 1


@pytest.mark.parametrize(
    "field,value",
    (
        ("defval", "60"),
        ("type", "text"),
        ("isFake", False),
        ("isMTFResolution", 1),
        ("name", "Other"),
        ("inline", "Other"),
    ),
)
def test_resolution_metadata_changes_are_rejected(field, value):
    source, payload, meta, _ = resolution_payload()
    meta["inputs"][-1][field] = value
    with pytest.raises(ValueError, match="resolution"):
        _parse(payload, source=source)


@pytest.mark.parametrize(
    "header",
    ('study("demo")', 'study("demo", resolution="60")', 'indicator("demo", timeframe="60")'),
)
def test_automatic_resolution_requires_the_observed_source_declaration(header):
    source, payload, _, _ = resolution_payload(header)
    with pytest.raises(ValueError, match="입력 개수"):
        _parse(payload, source=source)


@pytest.mark.parametrize("change", ("wire_override", "wire_extra", "meta_extra", "meta_duplicate"))
def test_resolution_override_or_arbitrary_extra_slot_is_rejected(change):
    source, payload, meta, create = resolution_payload()
    if change == "wire_override":
        create["p"][5]["in_1"]["v"] = "60"
    elif change == "wire_extra":
        create["p"][5]["in_2"] = {"v": ""}
    elif change == "meta_extra":
        meta["inputs"].append({"id": "in_2", "defval": ""})
    else:
        meta["inputs"].append(dict(meta["inputs"][-1]))
    payload["wire"][0]["data"] = _frame(create)
    with pytest.raises(ValueError):
        _parse(payload, source=source)


def test_adjacent_shapes_colorer_preserves_native_plot_binding():
    payload = _payload()
    meta = payload["compile_responses"][0]["data"]["result"]["metaInfo"]
    meta["plots"].append({"id": "plot_3", "type": "colorer", "target": "plot_2"})
    calls, _, fills = _source_calls(SOURCE)
    assert _plot_bindings(calls, meta["plots"], meta["styles"], BINDINGS, fills) == [(1, "long", 5)]
    for target in ("plot_0", "plot_999", "fill_0"):
        meta["plots"][-1]["target"] = target
        with pytest.raises(ValueError, match="colorer"):
            _plot_bindings(calls, meta["plots"], meta["styles"], BINDINGS, fills)


def test_untitled_plot_accepts_only_observed_compiler_default_title():
    source = SOURCE.replace('plot(close, title="Line")', "plot(close)")
    payload = _payload()
    payload.update(
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        compiled_source=source,
        compile_request_source=source,
    )
    style = payload["compile_responses"][0]["data"]["result"]["metaInfo"]["styles"]["plot_1"]
    style["title"] = "Plot"
    assert len(_parse(payload, source=source).events) == 1
    style["title"] = "arbitrary"
    with pytest.raises(ValueError, match="title"):
        _parse(payload, source=source)
