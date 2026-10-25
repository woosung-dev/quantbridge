"""검토한 전역 조건의 append-only 진단 바인딩과 출처를 확인한다."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.editor_picks import catalogue
from tools.research.editor_picks.common import read, sha, write

from scripts.pine_validation.strategy_adapter import adapt_strategy

SOURCE = '''//@version=5
indicator("검토한 추세", overlay=true)
fast=ta.sma(close,2)
slow=ta.sma(close,3)
f(x) =>
    x > 0
plot(fast)
'''
EXPRESSIONS = [
    {"direction": "long", "expression": "ta.crossover(fast, slow)"},
    {"direction": "short", "expression": "ta.crossunder(fast, slow)"},
]


@pytest.mark.parametrize("source", [SOURCE, SOURCE.rstrip("\n"), SOURCE.replace("\n", "\r\n")])
def test_append_only_diagnostics_keep_original_bytes_and_split_provenance(source):
    augmented, bindings, provenance = catalogue.augment_expression_signals(source, EXPRESSIONS)
    assert augmented.encode().startswith(source.encode())
    assert augmented.splitlines()[:len(source.splitlines())] == source.splitlines()
    assert provenance["original_source_sha256"] == sha(source.encode())
    assert provenance["augmented_source_sha256"] == sha(augmented.encode())
    assert provenance["native_verified"] is False
    assert provenance["original_line_count"] == len(source.splitlines())
    for binding, diagnostic in zip(bindings, provenance["diagnostics"], strict=True):
        assert binding["line"] == diagnostic["line"]
        assert binding["expression"] == diagnostic["expression"]
        assert diagnostic["expression"] in augmented.splitlines()[binding["line"] - 1]
        assert diagnostic["title"] == diagnostic["message"]
    adapted = catalogue.raw_signal_strategy(adapt_strategy(augmented, bindings, fixed_quantity=None))
    assert adapted.source_sha256 == provenance["augmented_source_sha256"]
    assert "strategy.entry" in adapted.strategy_source
    assert "and strategy.position_size" not in adapted.strategy_source


@pytest.mark.parametrize(
    "expression",
    [
        "unknown > 0", "f(fast)", "input.bool(true)", "pa.push(fast)",
        "strategy.position_size > 0", "array.push(fast,1)", "fast[slow] > 0",
        "fast[-1] > 0", "fast[10001] > 0", "fast\nslow", "fast), plot(close), alertcondition(true",
        "ta.sma(fast,2) > 0", "math.random(0,1) > 0",
        "ta.crossover(source2=slow,source1=fast)", "math.pow(exponent=2,base=fast) > 0",
    ],
)
def test_expression_rejects_unknown_calls_state_mutation_and_statement_injection(expression):
    bindings = [{"direction": "long", "expression": expression}, EXPRESSIONS[1]]
    with pytest.raises(Exception):
        catalogue.augment_expression_signals(SOURCE, bindings)


def test_source_local_variable_cannot_escape_udf_scope():
    source = SOURCE + "g() =>\n    secret=1\n    secret\n"
    with pytest.raises(ValueError, match="전역 이름"):
        catalogue.augment_expression_signals(source, [
            {"direction": "long", "expression": "secret > 0"}, EXPRESSIONS[1],
        ])


def test_history_boolean_and_read_only_math_are_allowed():
    augmented, _, _ = catalogue.augment_expression_signals(SOURCE, [
        {"direction": "long", "expression": "fast > slow and not (fast[1] > slow[1])"},
        {"direction": "short", "expression": "math.abs(fast - slow) > 0 and close < open"},
    ])
    assert augmented.startswith(SOURCE)


def test_ribbon_na_guard_is_read_only_and_cannot_call_shadowing_udf():
    bindings = [
        {"direction": "long", "expression": "not na(slow[1]) and fast > slow and fast[1] <= slow[1]"},
        {"direction": "short", "expression": "not na(slow[1]) and fast < slow and fast[1] >= slow[1]"},
    ]
    augmented, generated, _ = catalogue.augment_expression_signals(SOURCE, bindings)
    assert augmented.startswith(SOURCE) and generated[0]["expression"] == bindings[0]["expression"]
    with pytest.raises(ValueError, match="호출"):
        catalogue.augment_expression_signals(SOURCE + "na(x) =>\n    true\n", bindings)


def test_crlf_library_cannot_pass_screening_as_unknown_object_methods(tmp_path):
    source = b'//@version=5\r\nimport Owner/Library/1 as pa\r\nindicator("t")\r\n'
    (tmp_path / "source.pine").write_bytes(source)
    write(tmp_path / "catalogue.json", {"items": [{
        "id": "abcdefgh", "status": "captured", "source_file": "source.pine",
        "source_sha256": sha(source),
    }]})
    result = catalogue.screen_one(tmp_path, "abcdefgh")
    assert result["status"] == "unsupported" and "import Owner/Library/1" in result["detail"]
    assert result["source_sha256"] == sha(source)
    assert (tmp_path / "source.pine").read_bytes() == source


def setup_review(root, binding_type="expression"):
    (root / "source.pine").write_bytes(SOURCE.encode())
    write(root / "catalogue.json", {"items": [{
        "id": "abcdefgh", "status": "captured", "source_file": "source.pine",
        "source_sha256": sha(SOURCE.encode()),
    }]})
    review = {
        "source_sha256": sha(SOURCE.encode()), "reviewed_by": "test-reviewer",
        "basis": "원문 fast/slow 교차", "family": "trend", "warmup_bars": 1000,
    }
    if binding_type == "expression":
        review.update(binding_type="expression", expression_bindings=EXPRESSIONS)
    else:
        review["signal_bindings"] = [
            {"direction": "long", "function": "plotshape", "line": 8},
            {"direction": "short", "function": "plotshape", "line": 9},
        ]
    write(root / "reviews/abcdefgh.json", review)
    return review


def test_screen_expression_records_generated_binding_without_overwriting_original(tmp_path):
    setup_review(tmp_path)
    result = catalogue.screen_one(tmp_path, "abcdefgh")
    assert result["status"] == "static_eligible"
    assert result["source_sha256"] == sha(SOURCE.encode())
    assert result["execution_verified"] is False
    provenance = result["expression_provenance"]
    augmented = (tmp_path / provenance["augmented_file"]).read_bytes()
    assert provenance["augmented_source_sha256"] == sha(augmented)
    assert result["adaptation"]["source_sha256"] == sha(augmented)
    assert (tmp_path / "source.pine").read_bytes() == SOURCE.encode()
    assert read(tmp_path / "reviews/abcdefgh.json")["expression_bindings"] == EXPRESSIONS
    assert catalogue.screen_one(tmp_path, "abcdefgh") == result
    (tmp_path / provenance["augmented_file"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="변경"):
        catalogue.screen_one(tmp_path, "abcdefgh")


def test_duplicate_direction_is_rejected():
    with pytest.raises(ValueError):
        catalogue.augment_expression_signals(SOURCE, [EXPRESSIONS[0], EXPRESSIONS[0]])


def test_existing_call_binding_keeps_identical_adapter_output(tmp_path):
    review = setup_review(tmp_path, binding_type="call")
    source = SOURCE + "plotshape(fast > slow)\nplotshape(fast < slow)\n"
    (tmp_path / "source.pine").write_bytes(source.encode())
    listing = read(tmp_path / "catalogue.json")
    listing["items"][0]["source_sha256"] = sha(source.encode())
    write(tmp_path / "catalogue.json", listing)
    review["source_sha256"] = sha(source.encode())
    write(tmp_path / "reviews/abcdefgh.json", review)
    expected = catalogue.raw_signal_strategy(
        adapt_strategy(source, review["signal_bindings"], fixed_quantity=None)
    )
    result = catalogue.screen_one(tmp_path, "abcdefgh")
    assert result["status"] == "static_eligible"
    assert "expression_provenance" not in result
    assert not (tmp_path / "augmented").exists()
    assert (tmp_path / result["adapted_file"]).read_bytes() == expected.strategy_source.encode()
    assert result["adaptation"] == expected.to_dict()
