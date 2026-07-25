// 샤프 지수 표시 기준과 하위호환 문구를 단일화한다.
import { EMPTY_CELL } from "@/lib/labels";

export const SHARPE_CONVENTION = {
  monthly: "tv_monthly_rfr2",
  daily: "tv_daily_rfr2",
  unavailable: "unavailable",
} as const;

export interface SharpeDisplay {
  display: string;
  foot: string;
  isLegacy: boolean;
  isUnavailable: boolean;
}

const UNAVAILABLE_FOOT = "변동이 없거나 기간이 짧아 산출되지 않았습니다";
const LEGACY_FOOT = "구 기준(봉 수익률 · 무위험 0%) - 현재 기준과 비교 불가";

export function describeSharpe(
  convention: string | null | undefined,
  value: number | null | undefined,
): SharpeDisplay {
  if (
    convention === SHARPE_CONVENTION.unavailable ||
    value == null ||
    !Number.isFinite(value)
  ) {
    return {
      display: EMPTY_CELL,
      foot: UNAVAILABLE_FOOT,
      isLegacy: false,
      isUnavailable: true,
    };
  }

  if (convention === SHARPE_CONVENTION.monthly) {
    return {
      display: value.toFixed(2),
      foot: "무위험 2%/년 · 월간 수익률 기준",
      isLegacy: false,
      isUnavailable: false,
    };
  }

  if (convention === SHARPE_CONVENTION.daily) {
    return {
      display: value.toFixed(2),
      foot: "무위험 2%/년 · 봉 단위 기간 기준(2개월 미만)",
      isLegacy: false,
      isUnavailable: false,
    };
  }

  return {
    display: value.toFixed(2),
    foot: LEGACY_FOOT,
    isLegacy: true,
    isUnavailable: false,
  };
}
