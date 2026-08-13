// 샤프 지수 표시 기준과 하위호환 문구를 단일화한다.
import { EMPTY_CELL } from "@/lib/labels";

export const SHARPE_CONVENTION = {
  monthly: "tv_monthly_rfr2",
  daily: "tv_daily_rfr2",
  unavailable: "unavailable",
  /** 자본이 0 이하로 내려간 구간이 있어 산출을 거부한 경우. */
  nonpositiveEquity: "unavailable_nonpositive_equity",
} as const;

export interface SharpeDisplay {
  display: string;
  foot: string;
  isLegacy: boolean;
  isUnavailable: boolean;
}

const UNAVAILABLE_FOOT = "변동이 없거나 기간이 짧아 산출되지 않았습니다";
// ★`unavailable` 과 합치지 않는다 — 계좌가 파산한 것과 잔잔한 것은 다른 사실이고,
//   전자에 "변동이 없어서" 라고 쓰면 적극적으로 틀린 말이 된다.
const NONPOSITIVE_EQUITY_FOOT =
  "자본이 0 이하로 내려간 구간이 있어 위험조정수익을 산출하지 않았습니다";
const LEGACY_FOOT = "구 기준(봉 수익률 · 무위험 0%) - 현재 기준과 비교 불가";

export function describeSharpe(
  convention: string | null | undefined,
  value: number | null | undefined,
): SharpeDisplay {
  if (convention === SHARPE_CONVENTION.nonpositiveEquity) {
    return {
      display: EMPTY_CELL,
      foot: NONPOSITIVE_EQUITY_FOOT,
      isLegacy: false,
      isUnavailable: true,
    };
  }

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
      foot: "무위험 2%/년 · 일간 수익률 기준(2개월 미만)",
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
