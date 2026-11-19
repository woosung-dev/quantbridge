"""Pine 원본 길이 상한 — 보안 감사 2026-11-19.

파싱 비용이 길이에 초선형으로 늘고 API 프로세스 안에서 돈다. 입구 4곳(생성·수정·파싱·지표 변환)이
같은 상한을 쓰는지, 그리고 레포의 실전 최대 스크립트는 여전히 통과하는지 잰다.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.strategy.convert.schemas import ConvertIndicatorRequest
from src.strategy.schemas import (
    MAX_PINE_SOURCE_CHARS,
    CreateStrategyRequest,
    ParseRequest,
    UpdateStrategyRequest,
)

_LARGEST_FIXTURE = Path(__file__).parents[1] / "fixtures" / "pine_corpus_v2" / "i3_drfx.pine"


def _build(model: str, source: str) -> object:
    if model == "create":
        return CreateStrategyRequest(name="s", pine_source=source)
    if model == "update":
        return UpdateStrategyRequest(pine_source=source)
    if model == "parse":
        return ParseRequest(pine_source=source)
    return ConvertIndicatorRequest(code=source)


@pytest.mark.parametrize("model", ["create", "update", "parse", "convert"])
def test_over_cap_is_rejected(model: str) -> None:
    with pytest.raises(ValidationError):
        _build(model, "x" * (MAX_PINE_SOURCE_CHARS + 1))


@pytest.mark.parametrize("model", ["create", "update", "parse", "convert"])
def test_at_cap_is_accepted(model: str) -> None:
    _build(model, "x" * MAX_PINE_SOURCE_CHARS)


@pytest.mark.parametrize("model", ["create", "update", "parse", "convert"])
def test_largest_real_script_still_fits(model: str) -> None:
    _build(model, _LARGEST_FIXTURE.read_text())
