"""Tier-0 렌더링 scope A — 좌표 저장 + getter 단위 테스트 (ADR-011 §2.0.4)."""
from __future__ import annotations

import math

import pytest

from src.strategy.pine_v2.rendering import (
    BoxObject,
    LabelObject,
    LineObject,
    RenderingRegistry,
    TableObject,
)


def test_line_new_registers_and_holds_coords() -> None:
    reg = RenderingRegistry()
    line = reg.line_new(
        x1=float("nan"), y1=float("nan"), x2=float("nan"), y2=float("nan")
    )
    assert isinstance(line, LineObject)
    assert line in reg.lines
    assert math.isnan(line.x1)
    assert math.isnan(line.y1)


def test_line_set_xy1_updates_coords() -> None:
    reg = RenderingRegistry()
    line = reg.line_new(x1=0.0, y1=0.0, x2=0.0, y2=0.0)
    reg.line_set_xy1(line, x=10, y=100.5)
    assert line.x1 == 10
    assert line.y1 == 100.5


def test_line_get_price_linearly_interpolates() -> None:
    """line.get_price(x)는 (x1,y1) ~ (x2,y2) 선형보간 (Pine 관례)."""
    reg = RenderingRegistry()
    line = reg.line_new(x1=0, y1=100.0, x2=10, y2=200.0)
    assert reg.line_get_price(line, x=5) == pytest.approx(150.0)
    assert reg.line_get_price(line, x=0) == pytest.approx(100.0)
    assert reg.line_get_price(line, x=10) == pytest.approx(200.0)


def test_line_get_price_handles_vertical_line() -> None:
    """x1==x2면 y1 반환 (division by zero 방지)."""
    reg = RenderingRegistry()
    line = reg.line_new(x1=5, y1=100.0, x2=5, y2=200.0)
    assert reg.line_get_price(line, x=5) == 100.0


def test_line_delete_marks_deleted() -> None:
    reg = RenderingRegistry()
    line = reg.line_new(x1=0, y1=0, x2=1, y2=1)
    reg.line_delete(line)
    assert line.deleted is True


def test_box_new_and_getters() -> None:
    reg = RenderingRegistry()
    box = reg.box_new(left=0, top=100.0, right=10, bottom=50.0)
    assert isinstance(box, BoxObject)
    assert reg.box_get_top(box) == 100.0
    assert reg.box_get_bottom(box) == 50.0
    reg.box_set_right(box, right=20)
    assert box.right == 20


def test_label_new_and_set_xy() -> None:
    reg = RenderingRegistry()
    label = reg.label_new(x=0, y=100.0, text="Entry")
    assert isinstance(label, LabelObject)
    reg.label_set_xy(label, x=5, y=110.0)
    assert label.x == 5 and label.y == 110.0
    assert label.text == "Entry"


def test_table_new_and_cell() -> None:
    reg = RenderingRegistry()
    table = reg.table_new(position="top_right")
    assert isinstance(table, TableObject)
    reg.table_cell(table, column=0, row=0, text="PnL")
    reg.table_cell(table, column=1, row=0, text="123.45")
    assert table.cells[(0, 0)] == "PnL"
    assert table.cells[(1, 0)] == "123.45"
