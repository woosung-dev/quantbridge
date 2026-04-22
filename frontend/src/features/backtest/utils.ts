// Sprint FE-04: Backtest utilities — equity curve downsampling, formatters.
// Sprint X1+X3 W4: 방향(long/short)별 승률·평균 PnL breakdown 추가.

import type { EquityPoint, TradeItem } from "./schemas";

/**
 * 등간격 샘플링으로 equity curve 포인트를 `max` 이하로 축소.
 * - n <= max → 원본 그대로
 * - else → index = round(i * (n - 1) / (max - 1)) 로 첫/끝 포인트 보존
 *
 * MVP: recharts LineChart 성능 보호 (너무 많은 포인트 = 느린 hover/tooltip).
 */
export function downsampleEquity(
  points: readonly EquityPoint[],
  max = 1000,
): EquityPoint[] {
  if (max <= 1) throw new Error("max must be > 1");
  const n = points.length;
  if (n <= max) return [...points];
  const out: EquityPoint[] = [];
  const seen = new Set<number>();
  for (let i = 0; i < max; i += 1) {
    const idx = Math.round((i * (n - 1)) / (max - 1));
    if (seen.has(idx)) continue;
    seen.add(idx);
    const pt = points[idx];
    if (pt !== undefined) out.push(pt);
  }
  return out;
}

/**
 * 숫자를 %로 표시 (소수점 2자리). 0.1523 → "15.23%".
 */
export function formatPercent(value: number, digits = 2): string {
  if (!Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

/**
 * USDT 등 통화 숫자 (소수점 2자리 + 천단위 구분).
 */
export function formatCurrency(value: number, digits = 2): string {
  if (!Number.isFinite(value)) return "—";
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/**
 * ISO datetime → YYYY-MM-DD.
 */
export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/**
 * ISO → YYYY-MM-DD HH:mm (UTC).
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const base = formatDate(iso);
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${base} ${hh}:${mm}`;
}

// --- Direction breakdown (W4) --------------------------------------------

export interface DirectionStats {
  count: number;
  winCount: number;
  /** 0..1 비율 — UI 에서 % 변환은 호출 측 책임. */
  winRate: number;
  /** 평균 PnL (해당 방향 거래의 산술 평균). count=0 이면 0. */
  avgPnl: number;
  totalPnl: number;
}

export interface DirectionBreakdown {
  long: DirectionStats;
  short: DirectionStats;
}

function emptyStats(): DirectionStats {
  return { count: 0, winCount: 0, winRate: 0, avgPnl: 0, totalPnl: 0 };
}

/**
 * 거래 목록을 방향(long/short)별로 집계.
 *
 * - 승리 판정: `pnl > 0` (엄격, 0 은 무승부 처리)
 * - non-finite (NaN/Infinity) pnl 은 0 으로 간주 (totalPnl 합산 제외)
 * - 빈 배열 / 단일 방향 / 혼합 모두 안전 (winRate=0, avgPnl=0)
 *
 * 주의: TradeItemSchema 의 pnl 은 BE 에서 string 으로 직렬화되지만
 * decimalString transform 으로 zod 파싱 직후 number 로 변환됨. 이 함수는
 * number 입력을 가정한다.
 */
export function computeDirectionBreakdown(
  trades: readonly TradeItem[],
): DirectionBreakdown {
  const long = emptyStats();
  const short = emptyStats();

  for (const t of trades) {
    const bucket = t.direction === "long" ? long : short;
    const raw = Number(t.pnl);
    const pnl = Number.isFinite(raw) ? raw : 0;
    bucket.count += 1;
    bucket.totalPnl += pnl;
    if (pnl > 0) bucket.winCount += 1;
  }

  long.winRate = long.count > 0 ? long.winCount / long.count : 0;
  short.winRate = short.count > 0 ? short.winCount / short.count : 0;
  long.avgPnl = long.count > 0 ? long.totalPnl / long.count : 0;
  short.avgPnl = short.count > 0 ? short.totalPnl / short.count : 0;

  return { long, short };
}
