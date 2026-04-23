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
  unsupported_builtins: [],
  is_runnable: true,
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
  unsupported_builtins: [],
  is_runnable: true,
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

  // T-A: result prop 축소 시 index는 clamp (BUG-A regression guard).
  // NOTE: 초기에는 useEffect로 index=0 리셋 설계였으나 CPU 100% 무한 루프 사고 발생 후
  //       clamp-only 전략으로 전환. counter는 `clampedIndex + 1`로 항상 steps.length와 동기화.
  it("clamps index and counter when result prop shrinks (stays at last valid step)", () => {
    const longer: ParsePreviewResponse = {
      ...sample,
      functions_used: ["ta.rsi", "ta.ema"],
  unsupported_builtins: [],
  is_runnable: true,
    };
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
    fireEvent.click(screen.getByRole("button", { name: /다음/ }));
    fireEvent.click(screen.getByRole("button", { name: /다음/ })); // at final (index=3 of 4 steps)
    rerender(
      <ParseDialog
        open={true}
        onOpenChange={() => {}}
        result={shorter}
        onSave={() => {}}
      />,
    );
    // shorter: intro + final = 2 steps. clampedIndex = min(3, 1) = 1 → 최종 step, counter "2 / 2"
    expect(screen.getByText(/2 \/ 2 단계/)).toBeInTheDocument();
    // 최종 step에 머무름 (intro 로 튕기지 않음) — save 버튼 가시성으로 검증
    expect(screen.getByRole("button", { name: /이 전략 저장/ })).toBeInTheDocument();
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
  unsupported_builtins: [],
  is_runnable: true,
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
  unsupported_builtins: [],
  is_runnable: true,
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
