// Sprint 52 BL-223 — ParamStabilityForm MVP 폼 검증
// 2개 var_name x 3 value preset + 제출 페이로드 + invalid 상태.

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ParamStabilityForm } from "../param-stability-form";

describe("ParamStabilityForm (Sprint 52 BL-223)", () => {
  it("기본 preset 으로 렌더 + 제출 시 9-cell payload 생성", () => {
    const onSubmit = vi.fn();
    render(
      <ParamStabilityForm
        backtestId="bt-1"
        onSubmit={onSubmit}
        isSubmitting={false}
        onCancel={() => {}}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Param Stability 실행" }),
    );
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      backtest_id: "bt-1",
      params: {
        param_grid: {
          emaPeriod: ["10", "20", "30"],
          stopLossPct: ["1.0", "2.0", "3.0"],
        },
      },
    });
  });

  it("사용자 변수명 변경 시 payload key 갱신", () => {
    const onSubmit = vi.fn();
    render(
      <ParamStabilityForm
        backtestId="bt-2"
        onSubmit={onSubmit}
        isSubmitting={false}
        onCancel={() => {}}
      />,
    );

    const var1NameInput = screen.getByLabelText("변수 1 변수명") as HTMLInputElement;
    fireEvent.change(var1NameInput, { target: { value: "rsiLen" } });

    fireEvent.click(
      screen.getByRole("button", { name: "Param Stability 실행" }),
    );
    expect(onSubmit).toHaveBeenCalledWith({
      backtest_id: "bt-2",
      params: {
        param_grid: {
          rsiLen: ["10", "20", "30"],
          stopLossPct: ["1.0", "2.0", "3.0"],
        },
      },
    });
  });

  it("같은 변수명 2회 → 제출 버튼 disabled + 에러 메시지", () => {
    render(
      <ParamStabilityForm
        backtestId="bt-3"
        onSubmit={vi.fn()}
        isSubmitting={false}
        onCancel={() => {}}
      />,
    );

    const var2NameInput = screen.getByLabelText("변수 2 변수명") as HTMLInputElement;
    fireEvent.change(var2NameInput, { target: { value: "emaPeriod" } });

    const submitBtn = screen.getByRole("button", {
      name: "Param Stability 실행",
    }) as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
    expect(screen.getByText(/두 변수 이름은 서로 달라야 합니다/)).toBeInTheDocument();
  });

  it("isSubmitting=true 면 제출 버튼 disabled + 텍스트 갱신", () => {
    render(
      <ParamStabilityForm
        backtestId="bt-4"
        onSubmit={vi.fn()}
        isSubmitting={true}
        onCancel={() => {}}
      />,
    );

    const submitBtn = screen.getByRole("button", {
      name: "제출 중…",
    }) as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
  });

  it("취소 버튼 클릭 시 onCancel 호출", () => {
    const onCancel = vi.fn();
    render(
      <ParamStabilityForm
        backtestId="bt-5"
        onSubmit={vi.fn()}
        isSubmitting={false}
        onCancel={onCancel}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "취소" }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("빈 변수명 → 제출 버튼 disabled", () => {
    render(
      <ParamStabilityForm
        backtestId="bt-6"
        onSubmit={vi.fn()}
        isSubmitting={false}
        onCancel={() => {}}
      />,
    );

    const var1NameInput = screen.getByLabelText("변수 1 변수명") as HTMLInputElement;
    fireEvent.change(var1NameInput, { target: { value: "" } });

    const submitBtn = screen.getByRole("button", {
      name: "Param Stability 실행",
    }) as HTMLButtonElement;
    expect(submitBtn.disabled).toBe(true);
  });
});
