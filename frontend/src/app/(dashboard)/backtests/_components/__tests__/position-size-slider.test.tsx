// 포지션 사이즈 슬라이더 onChange / 값 표시 테스트 — Sprint 42-polish W4
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PositionSizeSlider } from "../position-size-slider";

describe("PositionSizeSlider", () => {
  it("slider 변경 시 onChange numeric 호출", () => {
    const onChange = vi.fn();
    render(<PositionSizeSlider value={10} onChange={onChange} />);

    const slider = screen.getByTestId(
      "position-size-slider-input",
    ) as HTMLInputElement;
    fireEvent.change(slider, { target: { value: "50" } });

    expect(onChange).toHaveBeenCalledWith(50);
  });

  it("값 표시는 `{value}{unit}` 포맷 + monospace 스타일", () => {
    render(<PositionSizeSlider value={25} onChange={() => {}} />);

    const valueEl = screen.getByTestId("position-size-slider-value");
    expect(valueEl).toHaveTextContent("25%");
    expect(valueEl.className).toContain("font-mono");
  });

  it("capitalUsd 지정 시 자기자본 환산 표시 (≈ $...)", () => {
    render(
      <PositionSizeSlider value={10} onChange={() => {}} capitalUsd={10000} />,
    );

    expect(screen.getByTestId("position-size-slider-value")).toHaveTextContent(
      "≈ $1,000",
    );
  });

  it("aria-valuenow 가 value 와 동기화됨", () => {
    render(<PositionSizeSlider value={75} onChange={() => {}} />);
    expect(screen.getByTestId("position-size-slider-input")).toHaveAttribute(
      "aria-valuenow",
      "75",
    );
  });

  // Sprint 44 W F3 — hover/focus tooltip
  it("hover 시 tooltip 노출 (opacity-100), 미상호작용 시 숨김 (opacity-0)", () => {
    render(<PositionSizeSlider value={40} onChange={() => {}} />);

    const tooltip = screen.getByTestId("position-size-slider-tooltip");
    const input = screen.getByTestId("position-size-slider-input");

    // 초기 상태: opacity-0
    expect(tooltip.className).toContain("opacity-0");

    // mouseEnter 시 opacity-100
    fireEvent.mouseEnter(input);
    expect(tooltip.className).toContain("opacity-100");

    // mouseLeave 시 opacity-0 복귀
    fireEvent.mouseLeave(input);
    expect(tooltip.className).toContain("opacity-0");

    // focus 시 opacity-100 (키보드 사용자도 보장)
    fireEvent.focus(input);
    expect(tooltip.className).toContain("opacity-100");
  });
});
