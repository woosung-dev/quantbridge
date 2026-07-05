"use client";

import { useMemo } from "react";

import { cn } from "@/lib/utils";

interface MonthlyReturnsHeatmapProps {
  /**
   * BE 직렬화 형식: list[tuple[str, decimalString]] → zod transform 후
   * `[ "YYYY-MM", number ]` 배열. null/undefined 시 안내 표시.
   */
  data: ReadonlyArray<readonly [string, number]> | null | undefined;
}

const MONTH_LABELS = [
  "1월",
  "2월",
  "3월",
  "4월",
  "5월",
  "6월",
  "7월",
  "8월",
  "9월",
  "10월",
  "11월",
  "12월",
] as const;

export function MonthlyReturnsHeatmap({ data }: MonthlyReturnsHeatmapProps) {
  // LESSON-004 H-1 — data array reference 만 dep. zod 파싱 직후 stable.
  const grid = useMemo(() => buildGrid(data), [data]);

  if (!grid || grid.years.length === 0) {
    return (
      <p className="text-sm text-[color:var(--text-muted)]">
        월별 수익률 데이터가 없습니다 (이전 버전 백테스트 또는 1개월 미만
        기간).
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-xs">
        <thead>
          <tr>
            <th className="px-2 py-1 text-right text-[color:var(--text-muted)]">
              {/* corner */}
            </th>
            {MONTH_LABELS.map((label) => (
              <th
                key={label}
                className="px-2 py-1 text-center font-medium text-[color:var(--text-muted)]"
                scope="col"
              >
                {label}
              </th>
            ))}
            <th
              scope="col"
              className="px-2 py-1 text-center font-semibold text-[color:var(--text-secondary)]"
            >
              연
            </th>
          </tr>
        </thead>
        <tbody>
          {grid.years.map((year) => {
            const yearTotal = grid.yearTotals[year] ?? 0;
            return (
              <tr key={year}>
                <th
                  scope="row"
                  className="px-2 py-1 text-right font-medium text-[color:var(--text-secondary)]"
                >
                  {year}
                </th>
                {MONTH_LABELS.map((_label, idx) => {
                  const month = idx + 1;
                  const value = grid.cells[`${year}-${String(month).padStart(2, "0")}`];
                  // Sprint 43 W10 — prototype 02 정합. native title hover tooltip 강화 + cell focusable.
                  const tooltipText =
                    value != null
                      ? `${year}년 ${month}월: ${(value * 100).toFixed(2)}%`
                      : `${year}년 ${month}월: 데이터 없음`;
                  return (
                    <td
                      key={month}
                      tabIndex={value != null ? 0 : -1}
                      aria-label={tooltipText}
                      className={cn(
                        "h-9 w-12 cursor-default border border-[color:var(--border)]/50 text-center font-mono tabular-nums transition-colors",
                        "focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--primary)]",
                      )}
                      style={
                        value != null
                          ? toneStyle(value, grid.maxAbs)
                          : { color: "var(--text-muted)" }
                      }
                      title={tooltipText}
                    >
                      {value != null
                        ? `${(value * 100).toFixed(1)}%`
                        : "·"}
                    </td>
                  );
                })}
                <td
                  className="h-9 w-14 border border-[color:var(--border)]/70 bg-[color:var(--muted)]/50 text-center font-mono font-semibold tabular-nums"
                  style={toneStyle(yearTotal, grid.maxAbs)}
                  title={`${year}년 합계: ${(yearTotal * 100).toFixed(2)}%`}
                >
                  {(yearTotal * 100).toFixed(1)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-[color:var(--text-muted)]">
        합계는 산술 합 (복리 아님). 색 강도는 |max| 비례.
      </p>
    </div>
  );
}

interface Grid {
  years: number[];
  cells: Record<string, number>;
  yearTotals: Record<number, number>;
  maxAbs: number;
}

function buildGrid(
  data: MonthlyReturnsHeatmapProps["data"],
): Grid | null {
  if (!data || data.length === 0) return null;

  const cells: Record<string, number> = {};
  const yearTotals: Record<number, number> = {};
  const yearSet = new Set<number>();
  let maxAbs = 0;

  for (const [key, raw] of data) {
    const value = Number.isFinite(raw) ? raw : 0;
    cells[key] = value;
    const year = Number.parseInt(key.slice(0, 4), 10);
    if (Number.isFinite(year)) {
      yearSet.add(year);
      yearTotals[year] = (yearTotals[year] ?? 0) + value;
    }
    if (Math.abs(value) > maxAbs) maxAbs = Math.abs(value);
  }

  if (yearSet.size === 0) return null;

  const years = Array.from(yearSet).sort((a, b) => a - b);

  return { years, cells, yearTotals, maxAbs: maxAbs > 0 ? maxAbs : 1 };
}

function toneStyle(value: number, maxAbs: number): React.CSSProperties {
  if (value === 0 || !Number.isFinite(value)) {
    return { color: "var(--text-muted)" };
  }
  // Sprint 43 W10 — prototype 02 정합. CSS var (success/destructive) + alpha intensity 로
  // 라이트 테마 통일. 0..1 비율로 opacity 조절. 최소 0.15 (시인성).
  const intensity = Math.min(0.85, Math.max(0.15, Math.abs(value) / maxAbs));
  if (value > 0) {
    return {
      backgroundColor: `color-mix(in srgb, var(--success) ${Math.round(intensity * 100)}%, transparent)`,
      color: intensity > 0.5 ? "white" : "var(--success)",
    };
  }
  return {
    backgroundColor: `color-mix(in srgb, var(--destructive) ${Math.round(intensity * 100)}%, transparent)`,
    color: intensity > 0.5 ? "white" : "var(--destructive)",
  };
}
