"""에디터 픽의 좌표 읽기·문자열 상태·표 범위를 실제 객체 상태로 검증한다."""

import pytest

from src.strategy.pine_v2.rendering import RenderingRegistry


def test_independent_coordinate_updates_change_line_interpolation():
    registry = RenderingRegistry()
    line = registry.line_new(0, 10, 4, 30)
    registry.line_set_x1(line, 2)
    registry.line_set_y2(line, 50)
    assert (registry.line_get_x1(line), registry.line_get_y1(line)) == (2, 10)
    assert (registry.line_get_x2(line), registry.line_get_y2(line)) == (4, 50)
    assert registry.line_get_price(line, 3) == 30
    registry.line_set_color(line, "#ff0000")
    assert registry.line_get_price(line, 3) == 30
    assert line.extras["color"] == "#ff0000"


def test_label_text_and_coordinate_getters_preserve_signal_references():
    registry = RenderingRegistry()
    label = registry.label_new(1, 10, "pending")
    registry.label_set_text(label, "bull")
    registry.label_set_y(label, 20)
    registry.label_set_color(label, "#00ff00")
    registry.label_set_textcolor(label, "#ffffff")
    assert registry.label_get_text(label) == "bull"
    assert registry.label_get_y(label) == 20
    assert label.extras == {"color": "#00ff00", "textcolor": "#ffffff"}


def test_table_clear_includes_endpoints_and_defaults_to_one_cell():
    registry = RenderingRegistry()
    table = registry.table_new("top_right", 3, 3)
    for column in range(3):
        for row in range(3):
            registry.table_cell(table, column, row, f"{column}:{row}")
    registry.table_clear(table, 1, 1)
    assert len(table.cells) == 8 and (1, 1) not in table.cells
    registry.table_clear(table, 0, 0, 1, 2)
    assert table.cells == {(2, row): f"2:{row}" for row in range(3)}


def test_table_merge_keeps_anchor_and_rejects_overlapping_ranges():
    registry = RenderingRegistry()
    table = registry.table_new("top_right", 4, 4)
    registry.table_cell(table, 0, 0, "header")
    registry.table_merge_cells(table, 0, 0, 2, 0)
    assert table.cells[(0, 0)] == "header"
    assert table.merged_cells == [(0, 0, 2, 0)]
    with pytest.raises(ValueError, match="겹칠"):
        registry.table_merge_cells(table, 2, 0, 3, 0)
    registry.table_merge_cells(table, 0, 1, 2, 1)
    assert len(table.merged_cells) == 2


@pytest.mark.parametrize("end", [(-1, 0), (0, -1)])
def test_table_operations_reject_reversed_ranges(end):
    registry = RenderingRegistry()
    table = registry.table_new("top_right", 2, 2)
    with pytest.raises(ValueError):
        registry.table_clear(table, 0, 0, *end)
    with pytest.raises(ValueError):
        registry.table_merge_cells(table, 0, 0, *end)
