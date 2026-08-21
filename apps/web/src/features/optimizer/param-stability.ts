// 파라미터 안정성 파생 — GridSearchResult.cells 에서 파라미터 값별 평균 목표값을 계산한다.
// 규약(§4.5): 축퇴 셀(거래 0건 · 목표값 null)은 평균에서 제외 · 막대 폭은 최고 평균을 100% 로 둔
// 비율 · 축 시작 0. "최고 평균" 은 전 파라미터·전 값의 평균 중 최댓값이다(막대 공통 기준).
// direction 은 "최적 값" 표시(best) 판정에만 쓴다(리더보드 정렬과 동일 방향 규약).

import type { GridSearchCell, OptimizationDirection } from "./schemas";

export interface ParamValueStat {
  /** 파라미터 값 (예: 20). GridSearchCell.param_values 는 이미 number 로 파싱돼 있다. */
  value: number;
  /** 이 값을 가진 유효 셀들의 목표값 산술평균. 유효 셀이 없으면 null. */
  average: number | null;
  /** 평균에 반영된 유효 셀 수 (축퇴 제외). */
  validCellCount: number;
  /** 막대 폭(%) = average / globalMaxAverage x 100, [0,100] 클램프. 막대 불가 시 0. */
  widthPct: number;
  /** direction 기준 최적 값 여부. */
  isBest: boolean;
}

export interface ParamStability {
  paramName: string;
  values: ParamValueStat[];
  /** 최고 평균 값(평균이 가장 큰 값). 유효 평균이 없으면 null. */
  highest: { value: number; average: number } | null;
  /** 최저 평균 값. */
  lowest: { value: number; average: number } | null;
  /** 폭 = 최고 평균 - 최저 평균 (부호 없는 크기). */
  spread: number;
}

export interface ParamStabilityResult {
  params: ParamStability[];
  /** 전 파라미터·전 값 평균 중 최댓값. 막대 100% 기준. */
  globalMaxAverage: number;
  /** 계산된 평균이 하나라도 있는가. */
  hasData: boolean;
  /** 0 기준 비율 막대가 의미 있는가(전 평균 ≥ 0 · 최고 평균 > 0). 음수 목표값이면 false. */
  canRenderBars: boolean;
}

function clampPct(n: number): number {
  if (n < 0) return 0;
  if (n > 100) return 100;
  return n;
}

/** 축퇴 셀 = is_degenerate 이거나 거래 0건이거나 목표값이 null. 평균에서 제외한다. */
function isValidCell(cell: GridSearchCell): boolean {
  return !cell.is_degenerate && cell.num_trades > 0 && cell.objective_value !== null;
}

export function deriveParamStability(
  cells: readonly GridSearchCell[],
  paramNames: readonly string[],
  direction: OptimizationDirection,
): ParamStabilityResult {
  const validCells = cells.filter(isValidCell);

  // 1차 패스 — 파라미터별·값별 평균(유효 셀만).
  const drafts = paramNames.map((paramName) => {
    // 축은 전 셀(축퇴 포함)의 값 집합에서 오름차순으로 뽑는다.
    const axis = Array.from(
      new Set(
        cells.map((c) => c.param_values[paramName]).filter((v): v is number => v !== undefined),
      ),
    ).sort((a, b) => a - b);

    const values = axis.map((value) => {
      const group = validCells.filter((c) => c.param_values[paramName] === value);
      const count = group.length;
      const average =
        count > 0 ? group.reduce((sum, c) => sum + (c.objective_value as number), 0) / count : null;
      return { value, average, validCellCount: count };
    });
    return { paramName, values };
  });

  // 전 파라미터·전 값 평균 목록.
  const allAverages = drafts.flatMap((p) =>
    p.values.map((v) => v.average).filter((a): a is number => a !== null),
  );
  const hasData = allAverages.length > 0;
  const globalMaxAverage = hasData ? Math.max(...allAverages) : 0;
  const globalMinAverage = hasData ? Math.min(...allAverages) : 0;
  // 0 기준 막대는 전 평균이 비음수이고 최고 평균이 양수일 때만 정직하다(음수 목표값이면 오도).
  const canRenderBars = hasData && globalMaxAverage > 0 && globalMinAverage >= 0;

  const params: ParamStability[] = drafts.map((p) => {
    const computed = p.values.filter(
      (v): v is { value: number; average: number; validCellCount: number } => v.average !== null,
    );
    const averages = computed.map((v) => v.average);
    const maxAvg = averages.length ? Math.max(...averages) : null;
    const minAvg = averages.length ? Math.min(...averages) : null;
    // 최적 값 = 최대화면 최고 평균, 최소화면 최저 평균(리더보드 정렬 방향과 일치).
    const bestAvg = direction === "minimize" ? minAvg : maxAvg;
    const bestValue =
      bestAvg !== null ? (computed.find((v) => v.average === bestAvg)?.value ?? null) : null;
    const highestEntry = maxAvg !== null ? computed.find((v) => v.average === maxAvg) : undefined;
    const lowestEntry = minAvg !== null ? computed.find((v) => v.average === minAvg) : undefined;

    return {
      paramName: p.paramName,
      values: p.values.map((v) => ({
        value: v.value,
        average: v.average,
        validCellCount: v.validCellCount,
        widthPct:
          canRenderBars && v.average !== null ? clampPct((v.average / globalMaxAverage) * 100) : 0,
        isBest: v.average !== null && v.value === bestValue,
      })),
      highest: highestEntry ? { value: highestEntry.value, average: highestEntry.average } : null,
      lowest: lowestEntry ? { value: lowestEntry.value, average: lowestEntry.average } : null,
      spread: maxAvg !== null && minAvg !== null ? maxAvg - minAvg : 0,
    };
  });

  return { params, globalMaxAverage, hasData, canRenderBars };
}
