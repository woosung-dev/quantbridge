// 옵티마이저 run 결과에서 최적 파라미터(input override)를 추출 — kind별 분기.

import type { OptimizationResult } from "./schemas";

export function extractBestParams(
  result: OptimizationResult | null | undefined,
): Record<string, number> | null {
  if (result == null) return null;
  if (result.kind === "grid_search") {
    if (result.best_cell_index === null) return null;
    return result.cells[result.best_cell_index]?.param_values ?? null;
  }
  // bayesian | genetic — best_params 는 Record | null.
  return result.best_params;
}
