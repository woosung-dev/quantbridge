import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ParseDialog } from "../parse-dialog";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";

const sample: ParsePreviewResponse = {
  status: "ok",
  pine_version: "v5",
  warnings: [],
  errors: [],
  entry_count: 1,
  exit_count: 1,
  functions_used: ["ta.rsi", "strategy.entry"],
};

describe("ParseDialog", () => {
  it("renders intro step first when opened", () => {
    render(
      <ParseDialog
        open={true}
        onOpenChange={() => {}}
        result={sample}
        onSave={() => {}}
      />,
    );
    expect(screen.getByText(/파싱 결과를 함께 살펴/)).toBeInTheDocument();
  });

  it("walks to function step on next click with description", () => {
    render(
      <ParseDialog
        open={true}
        onOpenChange={() => {}}
        result={sample}
        onSave={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    expect(screen.getByText("ta.rsi")).toBeInTheDocument();
    expect(screen.getByText(/RSI|상대.*강도/)).toBeInTheDocument();
  });

  it("fires onSave on final save button when status ok", () => {
    const onSave = vi.fn();
    const onOpenChange = vi.fn();
    render(
      <ParseDialog
        open={true}
        onOpenChange={onOpenChange}
        result={sample}
        onSave={onSave}
      />,
    );
    // intro -> ta.rsi -> strategy.entry -> final
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    const saveBtn = screen.getByRole("button", { name: /이 전략 저장/ });
    expect(saveBtn).not.toBeDisabled();
    fireEvent.click(saveBtn);
    expect(onSave).toHaveBeenCalledOnce();
  });

  it("disables save when status is error", () => {
    const errored: ParsePreviewResponse = {
      ...sample,
      status: "error",
      errors: [{ code: "syntax", message: "bad", line: 3 }],
      functions_used: [],
    };
    render(
      <ParseDialog
        open={true}
        onOpenChange={() => {}}
        result={errored}
        onSave={() => {}}
      />,
    );
    // intro -> error -> final
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    const saveBtn = screen.getByRole("button", { name: /이 전략 저장/ });
    expect(saveBtn).toBeDisabled();
  });

  // T-A: result prop 변경 시 index 리셋 + counter clamp (BUG-A regression guard)
  it("resets index and counter when result prop changes mid-walkthrough", () => {
    const longer: ParsePreviewResponse = { ...sample, functions_used: ["ta.rsi", "ta.ema"] };
    const shorter: ParsePreviewResponse = { ...sample, functions_used: [] };
    const { rerender } = render(
      <ParseDialog
        open={true}
        onOpenChange={() => {}}
        result={longer}
        onSave={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    fireEvent.click(screen.getByRole("button", { name: /다음/ })); // at function 2/2
    rerender(
      <ParseDialog
        open={true}
        onOpenChange={() => {}}
        result={shorter}
        onSave={() => {}}
      />,
    );
    // shorter에는 intro + final (2 steps), index reset to 0 → "1 / 2 단계"
    expect(screen.getByText(/1 \/ 2 단계/)).toBeInTheDocument();
    expect(screen.getByText(/파싱 결과를 함께 살펴/)).toBeInTheDocument();
  });

  // T-C: 이중 클릭으로 save 중복 호출 방지
  it("calls onSave exactly once on rapid double-click at final step", () => {
    const onSave = vi.fn();
    const onOpenChange = vi.fn();
    render(
      <ParseDialog
        open={true}
        onOpenChange={onOpenChange}
        result={sample}
        onSave={onSave}
      />,
    );
    // intro -> ta.rsi -> strategy.entry -> final
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    const saveBtn = screen.getByRole("button", { name: /이 전략 저장/ });
    fireEvent.click(saveBtn);
    fireEvent.click(saveBtn); // 2nd rapid click — should be no-op
    expect(onSave).toHaveBeenCalledTimes(1);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  // T-D: error.line === 0 정상 렌더 ("L0:" 표시)
  it("renders L0: prefix when error.line is 0 (truthy/nullish guard pin)", () => {
    const withLineZero: ParsePreviewResponse = {
      ...sample,
      status: "error",
      errors: [{ code: "syntax", message: "bad start", line: 0 }],
      functions_used: [],
    };
    render(
      <ParseDialog
        open={true}
        onOpenChange={() => {}}
        result={withLineZero}
        onSave={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /다음/ })); // intro -> error step
    expect(screen.getByText(/L0:/)).toBeInTheDocument();
  });

  // T-B render: status="unsupported"일 때 final step 문구가 errorCount=0 조건에 맞는지
  it("shows unsupported-specific message on final when status=unsupported and no errors", () => {
    const unsupported: ParsePreviewResponse = {
      ...sample,
      status: "unsupported",
      errors: [],
      functions_used: [],
    };
    render(
      <ParseDialog
        open={true}
        onOpenChange={() => {}}
        result={unsupported}
        onSave={() => {}}
      />,
    );
    // intro -> final (2 steps)
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    expect(screen.getByText(/지원되지 않는 기능/)).toBeInTheDocument();
    expect(screen.queryByText(/에러가 0건/)).not.toBeInTheDocument();
    const saveBtn = screen.getByRole("button", { name: /이 전략 저장/ });
    expect(saveBtn).toBeDisabled();
  });
});
