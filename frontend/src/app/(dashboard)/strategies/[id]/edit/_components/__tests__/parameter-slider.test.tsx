// 파라미터 슬라이더 (Position Size 등) — onChange / aria 동기화 / 진행도 progress (Sprint 43 W9-fidelity)
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ParameterSlider } from "../parameter-slider";

describe("ParameterSlider", () => {
  it("slider 변경 시 onChange numeric 호출", () => {
    const onChange = vi.fn();
    render(<ParameterSlider label="Position Size" value={10} onChange={onChange} />);

    const slider = screen.getByTestId("parameter-slider-input") as HTMLInputElement;
    fireEvent.change(slider, { target: { value: "40" } });

    expect(onChange).toHaveBeenCalledWith(40);
  });

  it("값 표시는 `{value}{unit}` 포맷 + monospace + primary 색상", () => {
    render(
      <ParameterSlider label="Position Size" value={25} onChange={() => {}} unit="%" />,
    );

    const valueEl = screen.getByTestId("parameter-slider-value");
    expect(valueEl).toHaveTextContent("25%");
    expect(valueEl.className).toContain("font-mono");
    expect(valueEl).toHaveAttribute("aria-live", "polite");
  });

  it("aria-valuenow 가 value 와 동기화됨", () => {
    render(
      <ParameterSlider label="Position Size" value={75} onChange={() => {}} />,
    );
    const input = screen.getByTestId("parameter-slider-input");
    expect(input).toHaveAttribute("aria-valuenow", "75");
    expect(input).toHaveAttribute("aria-valuemin", "0");
    expect(input).toHaveAttribute("aria-valuemax", "100");
  });

  it("--qb-slider-progress CSS 변수가 정규화된 백분율로 설정됨", () => {
    render(
      <ParameterSlider
        label="Slow MA"
        value={50}
        onChange={() => {}}
        min={0}
        max={100}
      />,
    );
    const input = screen.getByTestId("parameter-slider-input") as HTMLInputElement;
    // 50 / (100-0) * 100 = 50%
    expect(input.style.getPropertyValue("--qb-slider-progress")).toBe("50%");
  });
});
