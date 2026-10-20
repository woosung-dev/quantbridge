"""Pine 호출이 실제 실행된 봉의 관찰값. 매매 방향은 호출자가 명시한다."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

SignalFunction = Literal["plotshape", "plotchar", "plotarrow", "alertcondition", "alert"]


@dataclass(frozen=True)
class SignalObservation:
    """소스 줄은 1-based, 열은 AST와 같은 0-based다. na는 None으로 보존한다."""

    function: SignalFunction
    source_line: int
    source_column: int
    bar_index: int
    bar_open_time: datetime | None
    value: bool | int | float | None
    marker_offset: int = 0
