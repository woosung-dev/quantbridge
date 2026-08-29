import { renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { InputDecl } from "@/features/strategy/schemas";

import { useStrategyInputs } from "../use-strategy-inputs";

const mockUseStrategy = vi.fn();
const mockUsePreviewParse = vi.fn();

vi.mock("@/features/strategy/hooks", () => ({
  useStrategy: (...args: unknown[]) => mockUseStrategy(...args),
  usePreviewParse: (...args: unknown[]) => mockUsePreviewParse(...args),
}));

afterEach(() => {
  vi.clearAllMocks();
});

describe("useStrategyInputs", () => {
  it("strategyId가 없으면 빈 input 목록을 돌려준다", () => {
    mockUseStrategy.mockReturnValue({ data: undefined, isLoading: false, error: null });
    mockUsePreviewParse.mockReturnValue({ data: undefined, isLoading: false, error: null });

    const { result } = renderHook(() => useStrategyInputs(undefined));

    expect(result.current.inputs).toEqual([]);
    expect(mockUseStrategy).toHaveBeenCalledWith(undefined);
    expect(mockUsePreviewParse).toHaveBeenCalledWith("");
  });

  it("조회한 pine_source를 그대로 파싱해 input 선언을 돌려준다", () => {
    const pineSource = "strategy('RSI')\nlength = input.int(14)";
    const inputs = [
      { input_type: "int", var_name: "length", defval: "14", title: "RSI Length" },
    ] satisfies InputDecl[];
    mockUseStrategy.mockReturnValue({
      data: { pine_source: pineSource },
      isLoading: false,
      error: null,
    });
    mockUsePreviewParse.mockReturnValue({ data: { inputs }, isLoading: false, error: null });

    const { result } = renderHook(() => useStrategyInputs("strategy-1"));

    expect(mockUsePreviewParse).toHaveBeenCalledWith(pineSource);
    expect(result.current.inputs).toEqual(inputs);
  });

  it.each([
    ["전략 조회", new Error("strategy unavailable"), null],
    ["Pine 파싱", null, new Error("parse unavailable")],
  ])("%s 오류를 그대로 노출한다", (_stage, strategyError, previewError) => {
    mockUseStrategy.mockReturnValue({
      data: previewError ? { pine_source: "strategy('RSI')" } : undefined,
      isLoading: false,
      error: strategyError,
    });
    mockUsePreviewParse.mockReturnValue({ data: undefined, isLoading: false, error: previewError });

    const { result } = renderHook(() => useStrategyInputs("strategy-1"));

    expect(result.current.error).toBe(strategyError ?? previewError);
  });
});
