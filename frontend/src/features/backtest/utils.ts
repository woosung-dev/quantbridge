// Sprint FE-04: Backtest utilities — equity curve downsampling, formatters.

import type { EquityPoint } from "./schemas";

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
