"""Tier-0 렌더링 scope A — 좌표 저장 + getter만 지원.

ADR-011 §2.0.4 "범위 A" 엄수:
- line / box / label / table 객체는 메모리 stub. 실제 차트 렌더링은 NOP.
- 좌표 저장 → LuxAlgo SMC류의 `line.get_price()` 좌표 재참조로 entry 조건 평가 가능.
- 실제 차트 그리기는 QB 프론트엔드(Next.js)가 담당.

각 handle은 dataclass. 추가 kwargs(color/style/extend 등)는 extras에 보관해
직렬화/디버깅용으로만 노출 (매매 로직엔 영향 없음).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PineColor:
    """v5의 표기별 동등성과 v6의 채널별 동등성을 함께 보존한다."""

    identity: tuple[Any, ...]
    red: int
    green: int
    blue: int
    alpha: float
    version: int


_COLOR_HEX = {
    "aqua": "00BCD4",
    "black": "363A45",
    "blue": "2962FF",
    "fuchsia": "E040FB",
    "gray": "787B86",
    "green": "4CAF50",
    "lime": "00E676",
    "maroon": "880E4F",
    "navy": "311B92",
    "olive": "808000",
    "orange": "FF9800",
    "purple": "9C27B0",
    "red": "FF5252",
    "silver": "B2B5BE",
    "teal": "00897B",
    "white": "FFFFFF",
    "yellow": "FFEB3B",
}


def _color_absent(value: Any) -> bool:
    return isinstance(value, float) and math.isnan(value)


def _color_rgba(red: float, green: float, blue: float, alpha: float, version: int) -> PineColor:
    r, g, b = (int(max(0, min(255, x))) for x in (red, green, blue))
    alpha = max(0.0, min(1.0, alpha))
    if version >= 6:
        byte = int(alpha * 255 + 0.5)
        return PineColor(("packed", r, g, b, byte), r, g, b, byte / 255, version)
    return PineColor(("rgba", r, g, b, alpha), r, g, b, alpha, version)


def color_literal(value: str, version: int) -> PineColor:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?", value):
        raise ValueError("color literal은 hex6 또는 hex8이어야 합니다")
    r, g, b = (int(value[i : i + 2], 16) for i in (1, 3, 5))
    byte = int(value[7:9], 16) if len(value) == 9 else 255
    if version >= 6:
        return _color_rgba(r, g, b, byte / 255, version)
    return PineColor(("hex", value), r, g, b, byte / 255, version)


def color_named(name: str, version: int) -> PineColor:
    values = _COLOR_HEX | (
        {"red": "F23645", "teal": "089981", "yellow": "FDD835"} if version >= 6 else {}
    )
    if name not in values:
        raise ValueError(f"지원하지 않는 color 상수: {name}")
    return color_literal("#" + values[name], version)


def _color_value(value: Any, version: int) -> PineColor:
    if _color_absent(value):
        return _color_rgba(0, 0, 0, 0, version)
    if not isinstance(value, PineColor):
        raise ValueError("color 함수는 색 값만 받습니다")
    return value


def _color_number(value: Any) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("color 수치 인자는 유한한 숫자여야 합니다")
    return float(value)


def color_call(name: str, values: dict[str, Any], version: int) -> Any:
    """실제 native로 확인한 색 구성·투명도·gradient·추출을 계산한다."""
    if name == "color":
        value = values["x"]
        return (
            float("nan") if version >= 6 and _color_absent(value) else _color_value(value, version)
        )
    if name in {"color.r", "color.g", "color.b", "color.t"}:
        value = _color_value(values["color"], version)
        if name == "color.t":
            raw = (1 - value.alpha) * 100
            if version >= 6 or value.identity[0] == "hex":
                return float(int(raw + 0.5))
            return float(int(round(raw, 10)))
        return float({"color.r": value.red, "color.g": value.green, "color.b": value.blue}[name])
    if name == "color.rgb":
        red, green, blue = (_color_number(values[key]) for key in ("red", "green", "blue"))
        transparency = _color_number(values.get("transp", 0))
        if not all(0 <= x <= 255 for x in (red, green, blue)) or not 0 <= transparency <= 100:
            raise ValueError("color.rgb의 채널·투명도가 지원 범위 밖입니다")
        return _color_rgba(red, green, blue, (100 - transparency) / 100, version)
    if name == "color.new":
        base = values["color"]
        if version >= 6 and _color_absent(base):
            return float("nan")
        color = _color_value(base, version)
        transparency = _color_number(values["transp"])
        if not 0 <= transparency <= 100:
            raise ValueError("color.new의 투명도가 지원 범위 밖입니다")
        return _color_rgba(
            color.red, color.green, color.blue, (100 - int(transparency)) / 100, version
        )
    if name != "color.from_gradient":
        raise ValueError(f"지원하지 않는 color 함수: {name}")
    value, bottom, top = (values[key] for key in ("value", "bottom_value", "top_value"))
    first, last = values["bottom_color"], values["top_color"]
    if any(_color_absent(x) for x in (value, bottom, top)) or (
        _color_absent(first) and _color_absent(last)
    ):
        return float("nan") if version >= 6 else _color_rgba(0, 0, 0, 0, version)
    value, bottom, top = (_color_number(x) for x in (value, bottom, top))
    if top <= bottom:
        raise ValueError("관측한 gradient 범위는 top_value가 bottom_value보다 커야 합니다")
    if value <= bottom:
        return color_call("color", {"x": first}, version)
    if value >= top:
        return color_call("color", {"x": last}, version)
    fraction = (value - bottom) / (top - bottom)
    if _color_absent(first):
        color = _color_value(last, version)
        return _color_rgba(color.red, color.green, color.blue, color.alpha * fraction, version)
    if _color_absent(last):
        color = _color_value(first, version)
        return _color_rgba(
            color.red, color.green, color.blue, color.alpha * (1 - fraction), version
        )
    low, high = _color_value(first, version), _color_value(last, version)
    return _color_rgba(
        low.red + (high.red - low.red) * fraction,
        low.green + (high.green - low.green) * fraction,
        low.blue + (high.blue - low.blue) * fraction,
        low.alpha + (high.alpha - low.alpha) * fraction,
        version,
    )


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
    merged_cells: list[tuple[int, int, int, int]] = field(default_factory=list)


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
    def line_new(self, x1: float, y1: float, x2: float, y2: float, **extras: Any) -> LineObject:
        obj = LineObject(x1=x1, y1=y1, x2=x2, y2=y2, extras=dict(extras))
        self.lines.append(obj)
        return obj

    def line_set_xy1(self, line: LineObject, x: float, y: float) -> None:
        if line.deleted:
            # 삭제된 line에 대한 좌표 수정은 no-op (Pine 관례: 에러 회피 + 좌표 동결)
            return
        line.x1 = x
        line.y1 = y

    def line_set_xy2(self, line: LineObject, x: float, y: float) -> None:
        if line.deleted:
            return
        line.x2 = x
        line.y2 = y

    def line_get_price(self, line: LineObject, x: float) -> float:
        """x 좌표의 y 값 (선형보간). x1==x2이면 y1 반환 (수직선 회피).

        삭제된 line은 nan 반환 (Pine TV의 `line is na` 오동작 패턴 방어).
        """
        if line.deleted:
            return float("nan")
        if line.x2 == line.x1:
            return line.y1
        t = (x - line.x1) / (line.x2 - line.x1)
        return line.y1 + t * (line.y2 - line.y1)

    def line_delete(self, line: LineObject) -> None:
        line.deleted = True

    def line_get_x1(self, line: LineObject) -> float:
        return line.x1

    def line_get_x2(self, line: LineObject) -> float:
        return line.x2

    def line_get_y1(self, line: LineObject) -> float:
        return line.y1

    def line_get_y2(self, line: LineObject) -> float:
        return line.y2

    def line_set_x1(self, line: LineObject, x: float) -> None:
        self.line_set_xy1(line, x, line.y1)

    def line_set_x2(self, line: LineObject, x: float) -> None:
        self.line_set_xy2(line, x, line.y2)

    def line_set_y1(self, line: LineObject, y: float) -> None:
        self.line_set_xy1(line, line.x1, y)

    def line_set_y2(self, line: LineObject, y: float) -> None:
        self.line_set_xy2(line, line.x2, y)

    def line_set_color(self, line: LineObject, color: Any) -> None:
        line.extras["color"] = color

    # ---- box ----
    def box_new(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        **extras: Any,
    ) -> BoxObject:
        obj = BoxObject(left=left, top=top, right=right, bottom=bottom, extras=dict(extras))
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
    def label_new(self, x: float, y: float, text: str = "", **extras: Any) -> LabelObject:
        obj = LabelObject(x=x, y=y, text=text, extras=dict(extras))
        self.labels.append(obj)
        return obj

    def label_set_xy(self, label: LabelObject, x: float, y: float) -> None:
        label.x = x
        label.y = y

    def label_set_x(self, label: LabelObject, x: float) -> None:
        label.x = x

    def label_set_y(self, label: LabelObject, y: float) -> None:
        label.y = y

    def label_get_y(self, label: LabelObject) -> float:
        return label.y

    def label_set_text(self, label: LabelObject, text: str) -> None:
        label.text = text

    def label_get_text(self, label: LabelObject) -> str:
        return label.text

    def label_set_color(self, label: LabelObject, color: Any) -> None:
        label.extras["color"] = color

    def label_set_textcolor(self, label: LabelObject, textcolor: Any) -> None:
        label.extras["textcolor"] = textcolor

    def label_delete(self, label: LabelObject) -> None:
        # label[1]은 첫 봉에서 na다. 지울 이전 라벨이 없는 정상 경로다.
        if isinstance(label, float) and math.isnan(label):
            return
        label.deleted = True

    # ---- table ----
    def table_new(self, position: str = "", *args: Any, **extras: Any) -> TableObject:
        # G4 (2026-07-12 pine-batch QA): Pine `table.new(position, columns, rows, ...)`
        # 는 columns/rows 를 positional 로 전달 — 시각 NOP 이므로 흡수만 하고 미보관.
        obj = TableObject(position=position, extras=dict(extras))
        self.tables.append(obj)
        return obj

    def table_cell(
        self, table: TableObject, column: int, row: int, text: str = "", *args: Any, **extras: Any
    ) -> None:
        # G4: Pine `table.cell(..., width, height, text_color, ...)` positional/kwargs 흡수.
        table.cells[(column, row)] = text

    def table_delete(self, table: TableObject) -> None:
        table.deleted = True

    def table_clear(
        self,
        table: TableObject,
        start_column: int,
        start_row: int,
        end_column: int | None = None,
        end_row: int | None = None,
    ) -> None:
        """생략한 종료 좌표는 시작 좌표와 같으며 양끝을 포함한다."""
        right = start_column if end_column is None else end_column
        bottom = start_row if end_row is None else end_row
        if min(start_column, start_row) < 0 or right < start_column or bottom < start_row:
            raise ValueError("table.clear의 셀 범위가 올바르지 않습니다")
        for column, row in list(table.cells):
            if start_column <= column <= right and start_row <= row <= bottom:
                del table.cells[column, row]

    def table_merge_cells(
        self,
        table: TableObject,
        start_column: int,
        start_row: int,
        end_column: int,
        end_row: int,
    ) -> None:
        """병합 범위는 화면 메타데이터이며 왼쪽 위 셀의 값을 보존한다."""
        if min(start_column, start_row) < 0 or end_column < start_column or end_row < start_row:
            raise ValueError("table.merge_cells의 셀 범위가 올바르지 않습니다")
        for left, top, right, bottom in table.merged_cells:
            if not (
                end_column < left or start_column > right or end_row < top or start_row > bottom
            ):
                raise ValueError("이미 병합한 셀과 겹칠 수 없습니다")
        table.merged_cells.append((start_column, start_row, end_column, end_row))
