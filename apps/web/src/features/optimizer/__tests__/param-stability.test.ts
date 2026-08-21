// 파라미터 안정성 파생 hand-computed oracle 테스트 (LESSON-039 circular oracle 금지).
// 외부 진실 2종으로 검증한다.
//   1) 2x2 셀 픽스처 — 값별 평균을 손으로 계산해 정확 대조 (엔진 출력 아님).
//   2) _KIT.md §4.5 opt_3a90 원장(SSOT 문서, 손으로 작성됨) — 문서화된 평균/폭 재현.

import { describe, expect, it } from "vitest";

import { deriveParamStability } from "@/features/optimizer/param-stability";
import type { GridSearchCell } from "@/features/optimizer/schemas";

// 파싱 후 형태(number)로 셀을 만든다. deriveParamStability 는 GridSearchCell(파싱 완료 타입)을 받는다.
function cell(
  params: Record<string, number>,
  objective: number | null,
  numTrades: number,
): GridSearchCell {
  return {
    param_values: params,
    sharpe: objective,
    total_return: objective ?? 0,
    max_drawdown: objective ?? 0,
    num_trades: numTrades,
    is_degenerate: numTrades === 0,
    objective_value: objective,
  };
}

describe("deriveParamStability — 2x2 hand-computed oracle", () => {
  // fast ∈ {10, 20}, slow ∈ {40, 50}. (20,50) 은 축퇴(거래 0).
  //   손계산(최대화):
  //     fast 10 = (2.0 + 1.0) / 2 = 1.5   (2셀)
  //     fast 20 = 4.0 / 1        = 4.0   (1유효셀, (20,50) 제외)
  //     slow 40 = (2.0 + 4.0) / 2 = 3.0   (2셀)
  //     slow 50 = 1.0 / 1        = 1.0   (1유효셀)
  //   globalMaxAverage = 4.0 → 폭%: fast10 37.5, fast20 100, slow40 75, slow50 25
  const cells: GridSearchCell[] = [
    cell({ fast: 10, slow: 40 }, 2.0, 10),
    cell({ fast: 10, slow: 50 }, 1.0, 10),
    cell({ fast: 20, slow: 40 }, 4.0, 10),
    cell({ fast: 20, slow: 50 }, null, 0), // 축퇴
  ];

  const result = deriveParamStability(cells, ["fast", "slow"], "maximize");

  it("전역 최고 평균 = 4.0, 데이터 있음, 막대 렌더 가능", () => {
    expect(result.globalMaxAverage).toBe(4.0);
    expect(result.hasData).toBe(true);
    expect(result.canRenderBars).toBe(true);
  });

  it("fast 값별 평균은 손계산과 정확히 일치한다 (축퇴 제외)", () => {
    const fast = result.params.find((p) => p.paramName === "fast")!;
    const byVal = new Map(fast.values.map((v) => [v.value, v]));
    expect(byVal.get(10)!.average).toBe(1.5);
    expect(byVal.get(10)!.validCellCount).toBe(2);
    expect(byVal.get(20)!.average).toBe(4.0);
    expect(byVal.get(20)!.validCellCount).toBe(1); // (20,50) 축퇴 제외
    // 폭% (globalMax 4.0 기준)
    expect(byVal.get(10)!.widthPct).toBe(37.5);
    expect(byVal.get(20)!.widthPct).toBe(100);
    // 최적 = 최고 평균 (최대화)
    expect(byVal.get(20)!.isBest).toBe(true);
    expect(byVal.get(10)!.isBest).toBe(false);
    // 폭 = 4.0 - 1.5 = 2.5
    expect(fast.spread).toBe(2.5);
    expect(fast.highest).toEqual({ value: 20, average: 4.0 });
    expect(fast.lowest).toEqual({ value: 10, average: 1.5 });
  });

  it("slow 값별 평균도 손계산과 일치한다", () => {
    const slow = result.params.find((p) => p.paramName === "slow")!;
    const byVal = new Map(slow.values.map((v) => [v.value, v]));
    expect(byVal.get(40)!.average).toBe(3.0);
    expect(byVal.get(50)!.average).toBe(1.0);
    expect(byVal.get(40)!.widthPct).toBe(75);
    expect(byVal.get(50)!.widthPct).toBe(25);
    expect(byVal.get(40)!.isBest).toBe(true);
    expect(slow.spread).toBe(2.0);
  });
});

describe("deriveParamStability — _KIT.md §4.5 opt_3a90 원장(SSOT 외부 진실)", () => {
  // (fast/slow: sharpe, trades). 30/60 은 축퇴(거래 0).
  const cells: GridSearchCell[] = [
    cell({ fastLength: 20, slowLength: 50 }, 1.84, 186),
    cell({ fastLength: 20, slowLength: 60 }, 1.61, 163),
    cell({ fastLength: 20, slowLength: 40 }, 1.53, 224),
    cell({ fastLength: 30, slowLength: 40 }, 1.29, 149),
    cell({ fastLength: 30, slowLength: 50 }, 1.21, 96),
    cell({ fastLength: 10, slowLength: 40 }, 1.12, 312),
    cell({ fastLength: 10, slowLength: 50 }, 0.94, 268),
    cell({ fastLength: 10, slowLength: 60 }, 0.71, 241),
    cell({ fastLength: 30, slowLength: 60 }, null, 0), // 축퇴
  ];

  const result = deriveParamStability(cells, ["fastLength", "slowLength"], "maximize");

  it("문서화된 fastLength 평균 0.92 / 1.66 / 1.25 를 재현한다", () => {
    const fast = result.params.find((p) => p.paramName === "fastLength")!;
    const byVal = new Map(fast.values.map((v) => [v.value, v]));
    expect(byVal.get(10)!.average).toBeCloseTo(0.9233, 3); // (1.12+0.94+0.71)/3
    expect(byVal.get(20)!.average).toBeCloseTo(1.66, 6); // (1.84+1.61+1.53)/3
    expect(byVal.get(30)!.average).toBeCloseTo(1.25, 6); // (1.29+1.21)/2, 축퇴 제외
    expect(byVal.get(30)!.validCellCount).toBe(2);
    // 문서 폭 0.74 = 1.66 - 0.92(반올림). 원값 spread 를 소수 2자리로 보면 0.74.
    expect(Number(fast.spread.toFixed(2))).toBe(0.74);
  });

  it("문서화된 slowLength 평균 1.31 / 1.33 / 1.16 + 폭 0.17 을 재현한다", () => {
    const slow = result.params.find((p) => p.paramName === "slowLength")!;
    const byVal = new Map(slow.values.map((v) => [v.value, v]));
    expect(byVal.get(40)!.average).toBeCloseTo(1.3133, 3); // (1.53+1.29+1.12)/3
    expect(byVal.get(50)!.average).toBeCloseTo(1.33, 6); // (1.84+1.21+0.94)/3
    expect(byVal.get(60)!.average).toBeCloseTo(1.16, 6); // (1.61+0.71)/2
    expect(Number(slow.spread.toFixed(2))).toBe(0.17);
  });

  it("전역 최고 평균 = 1.66 (fastLength 20), 막대 100% 기준", () => {
    expect(result.globalMaxAverage).toBeCloseTo(1.66, 6);
    const fast = result.params.find((p) => p.paramName === "fastLength")!;
    expect(fast.values.find((v) => v.value === 20)!.widthPct).toBe(100);
  });
});

describe("deriveParamStability — 방향/경계", () => {
  it("최소화면 최저 평균 값을 best 로 표시한다", () => {
    const cells: GridSearchCell[] = [
      cell({ p: 1 }, 10, 5),
      cell({ p: 2 }, 4, 5),
      cell({ p: 3 }, 7, 5),
    ];
    const result = deriveParamStability(cells, ["p"], "minimize");
    const p = result.params[0]!;
    const byVal = new Map(p.values.map((v) => [v.value, v]));
    expect(byVal.get(2)!.isBest).toBe(true); // 최소화 → 4가 최적
    expect(byVal.get(1)!.isBest).toBe(false);
  });

  it("음수 평균이 섞이면 0 기준 막대를 그리지 않는다 (canRenderBars=false)", () => {
    const cells: GridSearchCell[] = [cell({ p: 1 }, -11, 5), cell({ p: 2 }, -24, 5)];
    const result = deriveParamStability(cells, ["p"], "minimize");
    expect(result.canRenderBars).toBe(false);
    expect(result.hasData).toBe(true);
    // 평균 자체는 정확히 계산된다.
    const p = result.params[0]!;
    expect(p.values.find((v) => v.value === 1)!.average).toBe(-11);
  });

  it("전 셀 축퇴면 데이터 없음", () => {
    const cells: GridSearchCell[] = [cell({ p: 1 }, null, 0), cell({ p: 2 }, null, 0)];
    const result = deriveParamStability(cells, ["p"], "maximize");
    expect(result.hasData).toBe(false);
    expect(result.canRenderBars).toBe(false);
  });
});
