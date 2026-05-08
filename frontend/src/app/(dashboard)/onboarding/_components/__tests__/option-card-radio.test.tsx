// 온보딩 OptionCardRadio 단위 테스트 — Sprint 42-polish W2
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OptionCardRadio } from "../option-card-radio";

describe("OptionCardRadio", () => {
  it("selected=true 상태에서 aria-checked + data-selected 반영", () => {
    const onSelect = vi.fn();
    render(
      <OptionCardRadio
        value="paste"
        label="Pine Script 붙여넣기"
        description="TradingView에서 코드 복사"
        icon={<svg data-testid="icon-paste" />}
        selected
        onSelect={onSelect}
      />,
    );
    const btn = screen.getByTestId("option-card-paste");
    expect(btn).toHaveAttribute("aria-checked", "true");
    expect(btn).toHaveAttribute("role", "radio");
    expect(btn.dataset.selected).toBe("true");
    expect(screen.getByText("Pine Script 붙여넣기")).toBeInTheDocument();
    expect(screen.getByText("TradingView에서 코드 복사")).toBeInTheDocument();
  });

  it("클릭 시 onSelect(value) 호출", () => {
    const onSelect = vi.fn();
    render(
      <OptionCardRadio
        value="template"
        label="템플릿"
        description="추천 전략 5개"
        icon={<svg />}
        selected={false}
        onSelect={onSelect}
        badge="추천"
      />,
    );
    const btn = screen.getByTestId("option-card-template");
    fireEvent.click(btn);
    expect(onSelect).toHaveBeenCalledWith("template");
    // badge 노출
    expect(screen.getByText("추천")).toBeInTheDocument();
  });
});
