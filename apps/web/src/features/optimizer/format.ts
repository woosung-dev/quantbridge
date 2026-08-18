// 목표값(objective_value 계열) 표기 SSOT — 단위는 objective_metric 이 정한다.
// ratio 지표(total_return·max_drawdown — 엔진 컨벤션 -0.25 = -25%)는 formatPercent 로 % 인쇄,
// 무단위 지표(sharpe_ratio)는 기존 소수 표기를 유지한다. 같은 화면에서 「최적 목표값 0.87」과
// 「총 수익률 87.40%」가 공존하던 단위 불일치를 이 분기 하나로 닫는다.

import { formatPercent } from "@/features/backtest/utils";
import type { OptimizationObjectiveMetric } from "@/features/optimizer/schemas";

// % 로 인쇄해야 하는 ratio 지표 집합 (승률류 지표가 생기면 여기에 추가).
const RATIO_METRICS: ReadonlySet<OptimizationObjectiveMetric> = new Set([
  "total_return",
  "max_drawdown",
]);

export function formatObjectiveValue(
  metric: OptimizationObjectiveMetric,
  value: number,
  {
    percentDigits = 2,
    plainDigits = 2,
  }: { percentDigits?: number; plainDigits?: number } = {},
): string {
  if (RATIO_METRICS.has(metric)) return formatPercent(value, percentDigits);
  return value.toFixed(plainDigits);
}
