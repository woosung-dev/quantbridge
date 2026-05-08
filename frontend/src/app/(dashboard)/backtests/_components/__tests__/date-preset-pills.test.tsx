// 날짜 preset pills onSelect / range 계산 테스트 — Sprint 42-polish W4
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DatePresetPills, calcDateRange } from "../date-preset-pills";

describe("DatePresetPills", () => {
  it("1Y 클릭 시 onSelect 가 1y 와 12개월 range 와 함께 호출됨", () => {
    const onSelect = vi.fn();
    render(<DatePresetPills value="6m" onSelect={onSelect} />);

    fireEvent.click(screen.getByTestId("date-preset-1y"));

    expect(onSelect).toHaveBeenCalledTimes(1);
    const firstCall = onSelect.mock.calls[0];
    if (!firstCall) throw new Error("onSelect call missing");
    const [preset, range] = firstCall;
    expect(preset).toBe("1y");
    expect(range).not.toBeNull();
    if (range) {
      // 12개월 차이 — 윤년 / 28일 월 변동 허용 365 ± 5일
      const start = new Date(`${range.startDate}T00:00:00Z`).getTime();
      const end = new Date(`${range.endDate}T00:00:00Z`).getTime();
      const days = (end - start) / (1000 * 60 * 60 * 24);
      expect(days).toBeGreaterThan(360);
      expect(days).toBeLessThan(370);
    }
  });

  it("active pill 은 aria-checked=true 표시", () => {
    const onSelect = vi.fn();
    render(<DatePresetPills value="3m" onSelect={onSelect} />);

    expect(screen.getByTestId("date-preset-3m")).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByTestId("date-preset-1m")).toHaveAttribute(
      "aria-checked",
      "false",
    );
  });

  it("커스텀 클릭 시 range=null 전달", () => {
    const onSelect = vi.fn();
    render(<DatePresetPills value="1m" onSelect={onSelect} />);

    fireEvent.click(screen.getByTestId("date-preset-custom"));

    expect(onSelect).toHaveBeenCalledWith("custom", null);
  });

  // Sprint 44 W F3 — active pill 에 qb-pill-pop entrance class 적용 (inactive 는 미적용)
  it("active pill 만 qb-pill-pop class 추가 (inactive 는 미적용)", () => {
    const onSelect = vi.fn();
    render(<DatePresetPills value="6m" onSelect={onSelect} />);

    expect(screen.getByTestId("date-preset-6m").className).toContain(
      "qb-pill-pop",
    );
    expect(screen.getByTestId("date-preset-1m").className).not.toContain(
      "qb-pill-pop",
    );
  });

  it("calcDateRange — 1m 은 약 30일 range", () => {
    const range = calcDateRange("1m");
    expect(range).not.toBeNull();
    if (range) {
      const days =
        (new Date(`${range.endDate}T00:00:00Z`).getTime() -
          new Date(`${range.startDate}T00:00:00Z`).getTime()) /
        (1000 * 60 * 60 * 24);
      expect(days).toBeGreaterThan(27);
      expect(days).toBeLessThan(33);
    }
  });
});
