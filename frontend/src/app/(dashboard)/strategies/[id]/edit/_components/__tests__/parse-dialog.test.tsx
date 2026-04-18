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
});
