"""외부 라이브러리를 로컬 객체 메서드로 오인해 실행 적격으로 세지 않는다."""

import pytest

from src.strategy.pine_v2.coverage import analyze_coverage


@pytest.mark.parametrize(
    "declaration,body",
    [
        ("import HeWhoMustNotBeNamed/arrayutils/10 as pa", "pa.push(a,close,10)"),
        ("import TradingView/ta/7", ""),
        ("import TradingView/ta/7 as custom", ""),
    ],
)
@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_import_is_unsupported_even_if_namespace_is_unknown_or_unused(declaration, body, newline):
    source = newline.join(["//@version=5", declaration, "indicator('t')", body, ""])
    report = analyze_coverage(source)
    assert not report.is_runnable
    expected = " ".join(declaration.split()[:2])
    assert expected in report.unsupported_functions
    assert any(item["name"] == expected and item["line"] == 2 for item in report.unsupported_calls)


def test_import_text_in_comments_or_strings_is_not_an_external_dependency():
    source = """//@version=5
indicator("import TradingView/ta/7 as custom")
// import HeWhoMustNotBeNamed/arrayutils/10 as pa
plot(close)
"""
    assert analyze_coverage(source).is_runnable
