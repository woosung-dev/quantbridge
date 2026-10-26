"""코드 전략의 불변 입력과 legacy Pine 경계. 실행 정책을 버전 해시로 고정한다."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from src.strategy.code_runtime.models import CodeLanguage
from src.strategy.exceptions import CodeStrategyPolicyError
from src.strategy.python_runtime.protocol import validate_source_and_params
from src.strategy.research_contract import ResearchExecution

if TYPE_CHECKING:
    from src.strategy.models import Strategy, StrategyVersion


CodeExecutionPolicy = Literal["code_v1", "code_research_v1"]
CODE_EXECUTION_POLICIES: tuple[CodeExecutionPolicy, ...] = ("code_v1", "code_research_v1")


class CodeSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    execution_policy: CodeExecutionPolicy
    language: CodeLanguage
    source_code: str = Field(min_length=1, max_length=131072)
    warmup_bars: int = Field(ge=1, le=10000)
    params: dict[str, JsonValue] = Field(default_factory=dict)
    provenance: dict[str, JsonValue]

    @model_validator(mode="after")
    def bounded_json(self) -> CodeSnapshot:
        validate_source_and_params(self.source_code, self.params)
        provenance = json.dumps(self.provenance, allow_nan=False, ensure_ascii=False)
        if len(provenance.encode()) > 32768:
            raise ValueError("provenance는 32768 bytes 이하여야 합니다")
        if self.execution_policy == "code_research_v1":
            ResearchExecution.model_validate(self.provenance.get("research_execution"))
        return self

    @property
    def research_execution(self) -> ResearchExecution | None:
        if self.execution_policy == "code_research_v1":
            return ResearchExecution.model_validate(self.provenance["research_execution"])
        return None

    @property
    def source_hash(self) -> str:
        return hashlib.sha256(self.source_code.encode()).hexdigest()

    @property
    def execution_hash(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode()
        ).hexdigest()


def legacy_pine_source(value: Strategy | StrategyVersion) -> str:
    """NULL이나 code 버전을 Pine로 해석하거나 현재 소스로 대체하지 않는다."""
    source = value.pine_source
    if getattr(value, "execution_policy", None) is not None or not isinstance(source, str):
        raise CodeStrategyPolicyError()
    return source


def read_code_version(version: StrategyVersion, *, strategy_id: UUID | None = None) -> CodeSnapshot:
    if strategy_id is not None and version.strategy_id != strategy_id:
        raise CodeStrategyPolicyError()
    try:
        snapshot = CodeSnapshot.model_validate(
            {
                "execution_policy": version.execution_policy,
                "language": version.language,
                "source_code": version.source_code,
                "warmup_bars": version.warmup_bars,
                "params": version.params,
                "provenance": version.provenance,
            }
        )
    except ValueError as exc:
        raise CodeStrategyPolicyError() from exc
    if (
        snapshot.source_hash != version.source_hash
        or snapshot.execution_hash != version.execution_hash
    ):
        raise CodeStrategyPolicyError()
    return snapshot
