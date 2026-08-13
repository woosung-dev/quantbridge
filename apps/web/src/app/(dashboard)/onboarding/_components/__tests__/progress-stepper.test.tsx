// 온보딩 ProgressStepper 단위 테스트 — Sprint 42-polish W2
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProgressStepper } from "../progress-stepper";

const STEPS = [
  { id: 1, label: "환영" },
  { id: 2, label: "샘플 전략" },
  { id: 3, label: "백테스트" },
  { id: 4, label: "결과" },
] as const;

describe("ProgressStepper", () => {
  it("currentStep=1 → step 1 active, 2/3/4 pending", () => {
    render(<ProgressStepper currentStep={1} steps={STEPS} />);
    const step1 = screen.getByTestId("progress-step-circle-1");
    const step2 = screen.getByTestId("progress-step-circle-2");
    expect(step1.parentElement?.parentElement?.dataset.state).toBe("active");
    expect(step2.parentElement?.parentElement?.dataset.state).toBe("pending");
    // progressbar aria
    const nav = screen.getByRole("progressbar");
    expect(nav).toHaveAttribute("aria-valuenow", "1");
    expect(nav).toHaveAttribute("aria-valuemax", "4");
  });

  it("currentStep=2 → step 1 completed (✓), step 2 active, line 1 success", () => {
    render(<ProgressStepper currentStep={2} steps={STEPS} />);
    const step1Li = screen.getByTestId("progress-step-circle-1").parentElement
      ?.parentElement;
    const step2Li = screen.getByTestId("progress-step-circle-2").parentElement
      ?.parentElement;
    expect(step1Li?.dataset.state).toBe("completed");
    expect(step2Li?.dataset.state).toBe("active");
    // 단계 카운터 텍스트
    expect(screen.getByText(/단계 2 \/ 4/)).toBeInTheDocument();
  });

  it("currentStep=4 → step 1/2/3 completed, step 4 active", () => {
    render(<ProgressStepper currentStep={4} steps={STEPS} />);
    expect(
      screen.getByTestId("progress-step-circle-1").parentElement?.parentElement
        ?.dataset.state,
    ).toBe("completed");
    expect(
      screen.getByTestId("progress-step-circle-3").parentElement?.parentElement
        ?.dataset.state,
    ).toBe("completed");
    expect(
      screen.getByTestId("progress-step-circle-4").parentElement?.parentElement
        ?.dataset.state,
    ).toBe("active");
  });
});
