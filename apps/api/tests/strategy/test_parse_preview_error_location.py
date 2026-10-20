"""실제 Pine 파서의 구조화된 오류 행이 프리뷰 응답에 보존되는지 검증한다."""

from unittest.mock import MagicMock

import pytest

from src.strategy.models import ParseStatus
from src.strategy.service import StrategyService


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source", "expected_line"),
    [
        ('//@version=5\nstrategy("location")\nx = (1 + )\n', 3),
        ('//@version=5\nstrategy("location")\n\n\nplot(1 + )\n', 5),
    ],
)
async def test_parse_preview_preserves_parser_error_line(source: str, expected_line: int) -> None:
    """문자열 위치를 추측하지 않고 실제 파서가 보고한 행을 사용한다."""
    service = StrategyService(repo=MagicMock())

    result = await service.parse_preview(source)

    assert result.status == ParseStatus.error
    assert len(result.errors) == 1
    assert result.errors[0].code == "SyntaxError"
    assert result.errors[0].line == expected_line
    assert result.declaration is None
    assert result.inputs == []
