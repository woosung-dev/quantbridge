"""Tier-0 렌더링 scope A — 좌표 저장 + getter만 지원.

ADR-011 §2.0.4 "범위 A" 엄수:
- line / box / label / table 객체는 메모리 stub. 실제 차트 렌더링은 NOP.
- 좌표 저장 → LuxAlgo SMC류의 `line.get_price()` 좌표 재참조로 entry 조건 평가 가능.
- 실제 차트 그리기는 QB 프론트엔드(Next.js)가 담당.

각 handle은 dataclass. 추가 kwargs(color/style/extend 등)는 extras에 보관해
직렬화/디버깅용으로만 노출 (매매 로직엔 영향 없음).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LineObject:
    """Pine line 객체 handle — 좌표 + 메타만 보관."""

    x1: float = float("nan")
    y1: float = float("nan")
    x2: float = float("nan")
    y2: float = float("nan")
    deleted: bool = False
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class BoxObject:
    """Pine box 객체 handle."""

    left: float = float("nan")
    top: float = float("nan")
    right: float = float("nan")
    bottom: float = float("nan")
    deleted: bool = False
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class LabelObject:
    """Pine label 객체 handle."""

    x: float = float("nan")
    y: float = float("nan")
    text: str = ""
    deleted: bool = False
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class TableObject:
    """Pine table 객체 handle — 셀 내용만 메모리 보관."""

    position: str = ""
    cells: dict[tuple[int, int], str] = field(default_factory=dict)
    deleted: bool = False
    extras: dict[str, Any] = field(default_factory=dict)


class RenderingRegistry:
    """렌더링 객체 발급·조회 허브. interpreter에 주입되어 line/box/label/table 호출 디스패치.

    좌표 재참조는 handle.y2 같은 속성 직접 접근이 일반적이나, Pine의
    `line.get_price(x)`는 선형보간을 제공하므로 메서드로 래핑.

    positional/keyword 양쪽 수용: `line.new(na, na, na, na)` (Pine 호출) 과
    `reg.line_new(x1=..., y1=...)` (Python 호출) 모두 허용하기 위해 `*` 키워드-only
    구분 없이 정의.
    """

    def __init__(self) -> None:
        self.lines: list[LineObject] = []
        self.boxes: list[BoxObject] = []
        self.labels: list[LabelObject] = []
        self.tables: list[TableObject] = []

    # ---- line ----
    def line_new(
        self, x1: float, y1: float, x2: float, y2: float, **extras: Any
    ) -> LineObject:
        obj = LineObject(x1=x1, y1=y1, x2=x2, y2=y2, extras=dict(extras))
        self.lines.append(obj)
        return obj

    def line_set_xy1(self, line: LineObject, x: float, y: float) -> None:
        line.x1 = x
        line.y1 = y

    def line_set_xy2(self, line: LineObject, x: float, y: float) -> None:
        line.x2 = x
        line.y2 = y

    def line_get_price(self, line: LineObject, x: float) -> float:
        """x 좌표의 y 값 (선형보간). x1==x2이면 y1 반환 (수직선 회피)."""
        if line.x2 == line.x1:
            return line.y1
        t = (x - line.x1) / (line.x2 - line.x1)
        return line.y1 + t * (line.y2 - line.y1)

    def line_delete(self, line: LineObject) -> None:
        line.deleted = True

    # ---- box ----
    def box_new(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        **extras: Any,
    ) -> BoxObject:
        obj = BoxObject(
            left=left, top=top, right=right, bottom=bottom, extras=dict(extras)
        )
        self.boxes.append(obj)
        return obj

    def box_get_top(self, box: BoxObject) -> float:
        return box.top

    def box_get_bottom(self, box: BoxObject) -> float:
        return box.bottom

    def box_set_right(self, box: BoxObject, right: float) -> None:
        box.right = right

    def box_delete(self, box: BoxObject) -> None:
        box.deleted = True

    # ---- label ----
    def label_new(
        self, x: float, y: float, text: str = "", **extras: Any
    ) -> LabelObject:
        obj = LabelObject(x=x, y=y, text=text, extras=dict(extras))
        self.labels.append(obj)
        return obj

    def label_set_xy(self, label: LabelObject, x: float, y: float) -> None:
        label.x = x
        label.y = y

    def label_delete(self, label: LabelObject) -> None:
        label.deleted = True

    # ---- table ----
    def table_new(self, position: str = "", **extras: Any) -> TableObject:
        obj = TableObject(position=position, extras=dict(extras))
        self.tables.append(obj)
        return obj

    def table_cell(
        self, table: TableObject, column: int, row: int, text: str = ""
    ) -> None:
        table.cells[(column, row)] = text

    def table_delete(self, table: TableObject) -> None:
        table.deleted = True
