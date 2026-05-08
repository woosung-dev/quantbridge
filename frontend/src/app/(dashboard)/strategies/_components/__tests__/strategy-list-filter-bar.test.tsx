// StrategyListFilterBar — 6 chip 렌더 + chip click + 정렬 dropdown + search debounce 검증
import { afterEach, describe, expect, it, vi, beforeEach } from "vitest";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";

import {
  StrategyListFilterBar,
  type SortKey,
  type StatusFilter,
} from "../strategy-list-filter-bar";

function renderBar(
  overrides: Partial<{
    status: StatusFilter;
    sort: SortKey;
    search: string;
    onStatusChange: (v: StatusFilter) => void;
    onSortChange: (v: SortKey) => void;
    onSearchChange: (v: string) => void;
  }> = {},
) {
  const onStatusChange = overrides.onStatusChange ?? vi.fn();
  const onSortChange = overrides.onSortChange ?? vi.fn();
  const onSearchChange = overrides.onSearchChange ?? vi.fn();
  render(
    <StrategyListFilterBar
      status={overrides.status ?? "all"}
      sort={overrides.sort ?? "updated_desc"}
      search={overrides.search ?? ""}
      onStatusChange={onStatusChange}
      onSortChange={onSortChange}
      onSearchChange={onSearchChange}
    />,
  );
  return { onStatusChange, onSortChange, onSearchChange };
}

describe("StrategyListFilterBar", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    cleanup();
  });

  it("6 개 chip 모두 (모두/파싱 성공/미지원/파싱 실패/보관됨/즐겨찾기) 렌더한다", () => {
    renderBar();
    const group = screen.getByRole("radiogroup", { name: "상태 필터" });
    const chips = within(group).getAllByRole("radio");
    expect(chips).toHaveLength(6);
    expect(chips[0]).toHaveTextContent("모두");
    expect(chips[1]).toHaveTextContent("파싱 성공");
    expect(chips[2]).toHaveTextContent("미지원");
    expect(chips[3]).toHaveTextContent("파싱 실패");
    expect(chips[4]).toHaveTextContent("보관됨");
    expect(chips[5]).toHaveTextContent("즐겨찾기");
  });

  it("chip click 시 onStatusChange 가 해당 id 로 호출된다", () => {
    const { onStatusChange } = renderBar({ status: "all" });
    const group = screen.getByRole("radiogroup", { name: "상태 필터" });
    const favorite = within(group).getByRole("radio", { name: /즐겨찾기/ });
    fireEvent.click(favorite);
    expect(onStatusChange).toHaveBeenCalledWith("favorite");
  });

  it("active chip 은 aria-checked=true 로 표시된다", () => {
    renderBar({ status: "ok" });
    const group = screen.getByRole("radiogroup", { name: "상태 필터" });
    const ok = within(group).getByRole("radio", { name: /파싱 성공/ });
    expect(ok).toHaveAttribute("aria-checked", "true");
    const all = within(group).getByRole("radio", { name: /^모두$/ });
    expect(all).toHaveAttribute("aria-checked", "false");
  });

  it("search 입력 후 300ms 경과 시에만 onSearchChange 가 호출된다 (debounce)", () => {
    const { onSearchChange } = renderBar({ search: "" });
    const input = screen.getByPlaceholderText("전략 이름·심볼 검색...");

    fireEvent.change(input, { target: { value: "btc" } });
    // 즉시 호출 X
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(onSearchChange).not.toHaveBeenCalled();

    // 300ms 도달
    act(() => {
      vi.advanceTimersByTime(150);
    });
    expect(onSearchChange).toHaveBeenCalledWith("btc");
  });

  it("정렬 dropdown trigger 가 현재 sort 라벨을 표시한다", () => {
    renderBar({ sort: "name_asc" });
    const trigger = screen.getByRole("button", { name: "정렬 기준" });
    expect(trigger).toHaveTextContent("이름순");
  });
});
