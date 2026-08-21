// extractBestParams — 옵티마이저 run 결과에서 최적 파라미터(input override) 추출 단위 테스트.

import { describe, expect, it } from "vitest";

import { extractBestParams } from "../best-params";
import type { OptimizationResult } from "../schemas";

describe("extractBestParams", () => {
  it("grid_search: best_cell_index 의 param_values 반환", () => {
    const result = {
      kind: "grid_search",
      best_cell_index: 1,
      cells: [{ param_values: { ema: 10 } }, { param_values: { ema: 20, sl: 2.5 } }],
    } as unknown as OptimizationResult;
    expect(extractBestParams(result)).toEqual({ ema: 20, sl: 2.5 });
  });

  it("grid_search: best_cell_index 가 null 이면 null", () => {
    const result = {
      kind: "grid_search",
      best_cell_index: null,
      cells: [],
    } as unknown as OptimizationResult;
    expect(extractBestParams(result)).toBeNull();
  });

  it("bayesian: best_params 반환", () => {
    const result = {
      kind: "bayesian",
      best_params: { ema: 14, factor: 1.5 },
    } as unknown as OptimizationResult;
    expect(extractBestParams(result)).toEqual({ ema: 14, factor: 1.5 });
  });

  it("genetic: best_params 반환", () => {
    const result = {
      kind: "genetic",
      best_params: { period: 30 },
    } as unknown as OptimizationResult;
    expect(extractBestParams(result)).toEqual({ period: 30 });
  });

  it("bayesian best_params 가 null 이면 null", () => {
    const result = {
      kind: "bayesian",
      best_params: null,
    } as unknown as OptimizationResult;
    expect(extractBestParams(result)).toBeNull();
  });

  it("null / undefined 입력은 null", () => {
    expect(extractBestParams(null)).toBeNull();
    expect(extractBestParams(undefined)).toBeNull();
  });
});
