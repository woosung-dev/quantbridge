// 샤프 지수 표시 기준의 계약 분기를 검증한다.
import { describe, expect, it } from "vitest";

import {
  describeSharpe,
  SHARPE_CONVENTION,
} from "@/features/backtest/sharpe-convention";
import { EMPTY_CELL } from "@/lib/labels";

describe("describeSharpe", () => {
  it.each([
    [
      SHARPE_CONVENTION.monthly,
      1.234,
      "1.23",
      "무위험 2%/년 · 월간 수익률 기준",
      false,
      false,
    ],
    [
      SHARPE_CONVENTION.daily,
      -1.234,
      "-1.23",
      "무위험 2%/년 · 일간 수익률 기준(2개월 미만)",
      false,
      false,
    ],
    [
      SHARPE_CONVENTION.unavailable,
      0,
      EMPTY_CELL,
      "변동이 없거나 기간이 짧아 산출되지 않았습니다",
      false,
      true,
    ],
    [
      null,
      1.234,
      "1.23",
      "구 기준(봉 수익률 · 무위험 0%) - 현재 기준과 비교 불가",
      true,
      false,
    ],
  ])("%s 기준을 표시 계약으로 변환한다", (convention, value, display, foot, isLegacy, isUnavailable) => {
    expect(describeSharpe(convention, value)).toEqual({
      display,
      foot,
      isLegacy,
      isUnavailable,
    });
  });

  it.each([null, Number.NaN, Number.POSITIVE_INFINITY])("값 %s는 산출 불가로 처리한다", (value) => {
    expect(describeSharpe(SHARPE_CONVENTION.monthly, value)).toMatchObject({
      display: EMPTY_CELL,
      isUnavailable: true,
    });
  });
});
