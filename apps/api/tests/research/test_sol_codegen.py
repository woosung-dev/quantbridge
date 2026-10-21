"""실험의 실패 분모·도구 격리·증거 손상을 확인한다."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research.sol_codegen import (  # noqa: E402
    digest,
    generate,
    generation_usage,
    strict_schema,
)


def test_tools_are_detected_even_when_generation_finishes():
    events = [
        {"type": "item.completed", "item": {"type": "command_execution"}},
        {"type": "turn.completed", "usage": {"input_tokens": 10, "output_tokens": 5}},
    ]
    assert generation_usage("\n".join(json.dumps(x) for x in events)) == (
        {"input_tokens": 10, "output_tokens": 5},
        True,
    )


def test_request_identity_includes_schema_and_model():
    assert digest({"model": "a", "schema": {"a": 1}}) != digest({"model": "b", "schema": {"a": 1}})


def test_defaulted_nested_spec_fields_are_explicit_without_losing_nullability():
    schema = {
        "type": "object",
        "properties": {
            "version": {"type": "integer", "default": 1},
            "value": {"anyOf": [{"type": "number"}, {"type": "null"}], "default": None},
        },
    }
    result = strict_schema(schema)
    assert result["required"] == ["version", "value"]
    assert result["additionalProperties"] is False
    assert "default" not in result["properties"]["value"]
    assert result["properties"]["value"]["anyOf"][-1] == {"type": "null"}


def test_different_cached_request_is_refused(tmp_path):
    (tmp_path / "generation.json").write_text(json.dumps({"job_hash": "different"}))
    with pytest.raises(ValueError, match="덮어쓸"):
        generate("prompt", tmp_path)


def test_failed_generation_is_not_retried_in_place(tmp_path):
    from tools.research.sol_codegen import CODE_SCHEMA, EFFORT, MODEL, OUTPUT_TOKEN_BUDGET

    request = {
        "model": MODEL,
        "effort": EFFORT,
        "prompt": "prompt",
        "schema": CODE_SCHEMA,
        "timeout": 180,
        "output_token_budget": OUTPUT_TOKEN_BUDGET,
        "token_limit_enforcement": "post_response_cli_usage",
    }
    cached = {"job_hash": digest(request), "status": "timeout"}
    (tmp_path / "generation.json").write_text(json.dumps(cached))
    assert generate("prompt", tmp_path) == cached


def test_interrupted_request_is_not_silently_generated_twice(tmp_path):
    from tools.research.sol_codegen import CODE_SCHEMA, EFFORT, MODEL, OUTPUT_TOKEN_BUDGET

    request = {
        "model": MODEL,
        "effort": EFFORT,
        "prompt": "prompt",
        "schema": CODE_SCHEMA,
        "timeout": 180,
        "output_token_budget": OUTPUT_TOKEN_BUDGET,
        "token_limit_enforcement": "post_response_cli_usage",
    }
    (tmp_path / "request.json").write_text(json.dumps(request))
    result = generate("prompt", tmp_path)
    assert result["status"] == "interrupted"
    assert result["usage_unavailable"]
