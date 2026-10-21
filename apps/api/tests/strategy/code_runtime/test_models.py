"""생성 원문과 언어·모델 근거를 잃지 않는 공통 계약."""

import pytest
from pydantic import ValidationError

from src.strategy.code_runtime.models import (
    CodeRuntimeError,
    GeneratedCodeArtifact,
    validate_code_intent,
)


def test_generated_artifact_retains_code_without_executing_it() -> None:
    artifact = GeneratedCodeArtifact(
        language="python", source_code="raise RuntimeError()", model="sol"
    )
    assert artifact.source_code == "raise RuntimeError()"
    with pytest.raises(ValidationError):
        artifact.model = "another"


@pytest.mark.parametrize("intent", [{"action": "long", "stop_loss": "90"}, {}, {"action": []}])
def test_intent_rejects_order_fields_and_invalid_actions(intent: object) -> None:
    with pytest.raises(CodeRuntimeError):
        validate_code_intent(intent)
