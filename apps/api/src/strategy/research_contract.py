"""연구 청산·재진입·신호 모드를 불변 실행 해시에 포함하는 계약."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchExecution(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    contract_version: Literal[1]
    exit_policy: Literal["signal_only_v1", "swing_two_bar_v1"]
    reentry_policy: Literal["close_then_reenter_v1"]
    signal_mode: Literal["shared_events", "position_feedback"]
    signal_mapping_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("contract_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("contract_version은 정수 1이어야 합니다")
        return value
