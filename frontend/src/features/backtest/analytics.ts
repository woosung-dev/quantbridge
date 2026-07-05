// 백테스트 리포트 FE 파생 계산 — 분포 histogram/승패 donut/커브 range/B&H 파생 (순수 함수)
//
// TV Strategy Tester 정보 구조 대응: BE 필드가 없는 표면(분포/벤치마킹 range)을
// trades/equity 커브에서 파생한다. 전부 순수 함수 — vitest 단위 테스트 대상.
// 빈 입력 계약: 배열 → [], 단일값 → null (호출측 empty state 처리).

export interface ReturnBin {
  /** 버킷 하한 (return_pct 비율, 0.01 = 1%) */
  from: number;
  /** 버킷 상한 */
  to: number;
  /** 버킷 내 거래 수 */
  count: number;
}

/**
 * 수익률 분포 histogram 버킷 (TV "수익 분포").
 * 등폭 버킷 — [min, max] 를 binCount 등분. 단일 값이면 1버킷.
 */
export function binReturnDistribution(
  returnsPct: readonly number[],
  binCount = 10,
): ReturnBin[] {
  const finite = returnsPct.filter((v) => Number.isFinite(v));
  if (finite.length === 0 || binCount < 1) {
    return [];
  }
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  if (min === max) {
    return [{ from: min, to: max, count: finite.length }];
  }
  const width = (max - min) / binCount;
  const bins: ReturnBin[] = Array.from({ length: binCount }, (_, i) => ({
    from: min + width * i,
    to: min + width * (i + 1),
    count: 0,
  }));
  for (const v of finite) {
    const idx = Math.min(Math.floor((v - min) / width), binCount - 1);
    const bin = bins[idx];
    if (bin !== undefined) {
      bin.count += 1;
    }
  }
  return bins;
}

export interface OutcomeCounts {
  wins: number;
  losses: number;
  breakeven: number;
  total: number;
}

/** 승/패/손익분기 카운트 (TV "거래 분포" donut). */
export function computeOutcomeCounts(pnls: readonly number[]): OutcomeCounts {
  let wins = 0;
  let losses = 0;
  let breakeven = 0;
  for (const pnl of pnls) {
    if (!Number.isFinite(pnl) || pnl === 0) {
      breakeven += 1;
    } else if (pnl > 0) {
      wins += 1;
    } else {
      losses += 1;
    }
  }
  return { wins, losses, breakeven, total: pnls.length };
}

export interface CurveRange {
  /** 첫 값 대비 최대 수익률 (비율) */
  maxPct: number;
  /** 첫 값 대비 최소 수익률 */
  minPct: number;
  /** 첫 값 대비 현재(마지막) 수익률 */
  currentPct: number;
}

/** 커브의 최대/현재/최소 % (TV "벤치마킹" floating bar). 기준 = 첫 값. */
export function computeCurveRange(values: readonly number[]): CurveRange | null {
  const base = values[0];
  const last = values[values.length - 1];
  if (
    values.length < 2 ||
    base === undefined ||
    last === undefined ||
    !Number.isFinite(base) ||
    base === 0
  ) {
    return null;
  }
  let max = -Infinity;
  let min = Infinity;
  for (const v of values) {
    if (!Number.isFinite(v)) {
      return null;
    }
    const pct = (v - base) / base;
    if (pct > max) max = pct;
    if (pct < min) min = pct;
  }
  return {
    maxPct: max,
    minPct: min,
    currentPct: (last - base) / base,
  };
}

export interface BuyAndHoldMetrics {
  /** 총 수익률 (비율) */
  returnPct: number;
  /** 최대 낙폭 (음수 비율, 종가 기준) */
  maxDrawdownPct: number;
}

/** B&H 커브 → 수익률/MDD 파생 (TV "벤치마킹" 테이블). */
export function deriveBuyAndHoldMetrics(
  values: readonly number[],
): BuyAndHoldMetrics | null {
  const base = values[0];
  const last = values[values.length - 1];
  if (
    values.length < 2 ||
    base === undefined ||
    last === undefined ||
    !Number.isFinite(base) ||
    base === 0
  ) {
    return null;
  }
  let peak = -Infinity;
  let maxDrawdown = 0;
  for (const v of values) {
    if (!Number.isFinite(v)) {
      return null;
    }
    if (v > peak) peak = v;
    if (peak > 0) {
      const dd = (v - peak) / peak;
      if (dd < maxDrawdown) maxDrawdown = dd;
    }
  }
  return {
    returnPct: (last - base) / base,
    maxDrawdownPct: maxDrawdown,
  };
}

export interface ExcessReturn {
  /** 전략 - B&H 절대 금액 차 */
  abs: number;
  /** 전략 - B&H 수익률 차 (비율 포인트) */
  pct: number;
}

/** 전략 초과 수익 vs B&H (TV 오버뷰 "전략 초과 수익"). */
export function computeExcessReturn(
  equityFinal: number,
  buyAndHoldFinal: number,
  initialCapital: number,
): ExcessReturn | null {
  if (
    !Number.isFinite(equityFinal) ||
    !Number.isFinite(buyAndHoldFinal) ||
    !Number.isFinite(initialCapital) ||
    initialCapital === 0
  ) {
    return null;
  }
  const abs = equityFinal - buyAndHoldFinal;
  return { abs, pct: abs / initialCapital };
}
