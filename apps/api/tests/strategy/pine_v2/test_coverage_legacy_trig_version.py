"""기존 실행 별칭과 실제 버전 주석을 정적 검사에서도 같은 의미로 판정한다."""

import pytest

from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.pine_v2.interpreter import _V4_ALIASES


@pytest.mark.parametrize("name", ["sin", "cos", "tan", "asin", "acos", "atan"])
def test_existing_legacy_trig_calls_match_namespaced_coverage(name):
    target = _V4_ALIASES[name]
    assert target == f"math.{name}"
    bare = analyze_coverage(f'//@version=4\nstudy("fixture")\nx={name}(close)\n')
    namespaced = analyze_coverage(f'//@version=5\nindicator("fixture")\nx={target}(close)\n')
    assert name in bare.used_functions and target in namespaced.used_functions
    assert bare.is_runnable and namespaced.is_runnable


@pytest.mark.parametrize("name", ["sin", "cos", "tan", "asin", "acos", "atan"])
def test_legacy_trig_does_not_hide_an_unsupported_dependency(name):
    report = analyze_coverage(
        f'//@version=4\nstudy("fixture")\nx={name}(close)\n'
        'y=math.unknown_dependency(close)\n'
    )
    assert not report.is_runnable
    assert name not in report.unsupported_functions
    assert "math.unknown_dependency" in report.unsupported_functions


@pytest.mark.parametrize("version", [4, 5, 6])
@pytest.mark.parametrize("cast", ["int", "float", "bool"])
def test_comment_apostrophe_before_real_version_does_not_disable_cast(version, cast):
    source = (
        "// Author's license: a comment, not a string delimiter.\r\n"
        f"\t//@version={version}\r\n"
        f"indicator('fixture')\r\nx={cast}(close)\r\n"
    )
    report = analyze_coverage(source)
    assert cast in report.used_functions
    assert report.is_runnable


@pytest.mark.parametrize("version", [1, 2, 3])
def test_comment_apostrophe_does_not_promote_old_version_casts(version):
    report = analyze_coverage(
        f"// Author's license\n//@version={version}\nstudy('fixture')\nx=int(close)\n"
    )
    assert "int" in report.unsupported_functions


@pytest.mark.parametrize(
    "literal", ["'prefix\n//@version=6\nsuffix'", '"prefix\n//@version=6\nsuffix"']
)
def test_version_text_inside_a_string_cannot_enable_a_cast(literal):
    report = analyze_coverage(f"message={literal}\nx=int(close)\n")
    assert "int" in report.unsupported_functions


def test_inline_comment_version_example_does_not_enable_a_cast():
    report = analyze_coverage('// example: //@version=6\nstudy("fixture")\nx=int(close)\n')
    assert "int" in report.unsupported_functions
