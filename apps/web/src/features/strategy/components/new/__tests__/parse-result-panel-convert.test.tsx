import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { ParseResultPanel } from "@/features/strategy/components/new/parse-result-panel";
import type { ParsePreviewResponse } from "@/features/strategy/schemas";

vi.mock("@/features/backtest/components/ConvertWithAIButton", () => ({
  ConvertWithAIButton: ({ indicatorCode }: { indicatorCode: string }) => (
    <button type="button" data-testid="convert-with-ai-button">
      {indicatorCode}
    </button>
  ),
}));

function makeResult(kind: "strategy" | "indicator" | "library" | "unknown"): ParsePreviewResponse {
  return {
    status: "ok",
    pine_version: "v5",
    warnings: [],
    errors: [],
    entry_count: 0,
    exit_count: 0,
    functions_used: [],
    unsupported_builtins: [],
    unsupported_calls: [],
    is_runnable: true,
    declaration: {
      kind,
      title: null,
      default_qty_type: null,
      default_qty_value: null,
      pyramiding: null,
    },
    inputs: [],
    dogfood_only_warning: null,
  };
}

describe("ParseResultPanel — indicator 변환 진입점", () => {
  afterEach(cleanup);

  it("indicator 결과와 두 prop이 있으면 변환 버튼을 보인다", () => {
    render(
      <ParseResultPanel
        result={makeResult("indicator")}
        loading={false}
        indicatorCode={'indicator("Example")'}
        onConverted={vi.fn()}
      />,
    );

    expect(screen.getByTestId("convert-with-ai-button")).toBeTruthy();
  });

  it("strategy 결과면 변환 버튼을 보이지 않는다", () => {
    render(
      <ParseResultPanel
        result={makeResult("strategy")}
        loading={false}
        indicatorCode={'strategy("Example")'}
        onConverted={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("convert-with-ai-button")).toBeNull();
  });

  it("두 prop이 없으면 변환 버튼을 보이지 않는다", () => {
    render(<ParseResultPanel result={makeResult("indicator")} loading={false} />);

    expect(screen.queryByTestId("convert-with-ai-button")).toBeNull();
  });
});
