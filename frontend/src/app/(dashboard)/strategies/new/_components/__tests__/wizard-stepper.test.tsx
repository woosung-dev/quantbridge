// WizardStepper — current=1/2/3 별 completed/active/pending state 검증 (Sprint 42-polish W3)

import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { WizardStepper } from "../wizard-stepper";

describe("WizardStepper", () => {
  afterEach(() => {
    cleanup();
  });

  it("current=1 → 1번 active, 2/3 pending", () => {
    render(<WizardStepper current={1} />);

    // 1번이 aria-current="step"
    expect(screen.getByLabelText(/1단계 진행 중/)).toBeInTheDocument();
    expect(screen.getByLabelText(/2단계 대기/)).toBeInTheDocument();
    expect(screen.getByLabelText(/3단계 대기/)).toBeInTheDocument();

    // 라벨 3개 모두 노출
    expect(screen.getByText("업로드 방식")).toBeInTheDocument();
    expect(screen.getByText("코드 입력")).toBeInTheDocument();
    expect(screen.getByText("확인")).toBeInTheDocument();
  });

  it("current=2 → 1 completed (체크), 2 active, 3 pending", () => {
    render(<WizardStepper current={2} />);

    expect(screen.getByLabelText(/1단계 완료/)).toBeInTheDocument();
    expect(screen.getByLabelText(/2단계 진행 중/)).toBeInTheDocument();
    expect(screen.getByLabelText(/3단계 대기/)).toBeInTheDocument();
  });

  it("current=3 → 1/2 completed, 3 active", () => {
    render(<WizardStepper current={3} />);

    expect(screen.getByLabelText(/1단계 완료/)).toBeInTheDocument();
    expect(screen.getByLabelText(/2단계 완료/)).toBeInTheDocument();
    expect(screen.getByLabelText(/3단계 진행 중/)).toBeInTheDocument();
  });
});
