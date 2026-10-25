"""v5/v6 실제 색상 출력·동등성·NA 관측을 순수 계산 함수와 대조한다."""

import json
from pathlib import Path

import pytest

from src.strategy.pine_v2._names import COLOR_NAMES
from src.strategy.pine_v2.rendering import color_call, color_literal, color_named
from src.strategy.pine_v2.stdlib import _is_na

FIXTURE = Path(__file__).parents[2] / "fixtures/pine_native/color_controls_v5_v6.json"
PROBES = json.loads(FIXTURE.read_text())["probes"]


def call(version, name, **values):
    return color_call(name, values, version)


def channels(version, prefix, value):
    return {
        f"{prefix}_{channel}": call(version, f"color.{channel}", color=value)
        for channel in ("r", "g", "b", "t")
    }


@pytest.mark.parametrize("probe", PROBES, ids=[p["name"] for p in PROBES])
def test_color_outputs_equal_every_unique_native_control(probe):
    version = int(probe["name"][-1])

    def lit(value):
        return color_literal(value, version)

    def rgb(r, g, b, t=0):
        return call(version, "color.rgb", red=r, green=g, blue=b, transp=t)

    def new(c, t):
        return call(version, "color.new", color=c, transp=t)

    def gradient(v, a, b):
        return call(
            version,
            "color.from_gradient",
            value=v,
            bottom_value=0,
            top_value=4,
            bottom_color=a,
            top_color=b,
        )

    absent = float("nan")
    for expected in probe["observations"]:
        if probe["name"].startswith("named"):
            actual = {}
            for name in COLOR_NAMES:
                color = color_named(name, version)
                actual.update(
                    {
                        f"{name}_{c}": call(version, f"color.{c}", color=color)
                        for c in ("r", "g", "b")
                    }
                )
            actual.update(
                red_t=call(version, "color.t", color=color_named("red", version)),
                white_t=call(version, "color.t", color=color_named("white", version)),
            )
        elif probe["name"].startswith("functions"):
            phase = expected["phase"]
            values = [
                new(lit("#010305"), 50),
                rgb(1, 3, 5, 50),
                gradient(phase, lit("#000000"), lit("#010305")),
                gradient(phase, absent, lit("#010305")),
                gradient(phase, lit("#010305"), absent),
                new(lit("#01030580"), 0),
                rgb(0.5, 1.5, 2.5, 49.5),
            ]
            actual = {
                "phase": phase,
                "new_rgb_equal": int(values[0] == values[1]),
                "rgb_hex_equal": int(rgb(1, 3, 5) == lit("#010305")),
            }
            for index, value in enumerate(values):
                actual.update(channels(version, f"c{index}", value))
        else:
            cast = call(version, "color", x=absent)
            actual = {
                "phase": expected["phase"],
                "new_rgb": int(new(lit("#010305"), 0) == rgb(1, 3, 5)),
                "new_hex": int(new(lit("#010305"), 0) == lit("#010305")),
                "hex_case": int(lit("#aabbcc") == lit("#AABBCC")),
                "red_legacy": int(color_named("red", version) == lit("#FF5252")),
                "red_current": int(color_named("red", version) == lit("#F23645")),
                "rgb_float": int(rgb(0.5, 1.5, 2.5) == rgb(0, 1, 2)),
                "rgb_transp_float": int(rgb(1, 3, 5, 49.5) == rgb(1, 3, 5, 49)),
                "new_transp_float": int(new(lit("#010305"), 49.5) == new(lit("#010305"), 49)),
                "cast_na": int(_is_na(cast)),
            }
            for prefix, value in {
                "cast": cast,
                "hex8": lit("#01030580"),
                "value_na": gradient(absent, lit("#000000"), lit("#010305")),
                "new_na": new(cast, 0),
                "both_na": gradient(expected["phase"], absent, absent),
                "transparent": new(lit("#010305"), 100),
            }.items():
                actual.update(channels(version, prefix, value))
        assert actual == expected
    assert sum(probe["phase_counts"].values()) == probe["closed_rows"]
