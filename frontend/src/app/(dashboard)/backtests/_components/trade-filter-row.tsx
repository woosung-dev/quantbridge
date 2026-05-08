// Sprint 43 W11 — 거래 필터 행 (6 필터: 검색/방향/결과/기간/PnL/정렬).
// 부모 (TradeDetailTable) 가 상태 owner. 본 컴포넌트는 controlled inputs.
"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  TradeFilters,
  TradeSortDir,
  TradeSortField,
} from "@/features/backtest/utils";

export interface ExtendedTradeFilters extends TradeFilters {
  /** 텍스트 검색어 (trade_index 또는 direction match). 빈 문자열 = no filter. */
  search: string;
  /** 기간 시작 (ISO date 부분만, "" = no min). */
  periodStart: string;
  /** 기간 종료 ("" = no max). */
  periodEnd: string;
  /** 최소 return_pct (decimal, e.g., -0.05). null = no min. */
  pnlMinPct: number | null;
  /** 최대 return_pct (decimal, e.g., 0.10). null = no max. */
  pnlMaxPct: number | null;
}

export const DEFAULT_FILTERS: ExtendedTradeFilters = {
  direction: "all",
  result: "all",
  search: "",
  periodStart: "",
  periodEnd: "",
  pnlMinPct: null,
  pnlMaxPct: null,
};

interface TradeFilterRowProps {
  filters: ExtendedTradeFilters;
  onFiltersChange: (next: ExtendedTradeFilters) => void;
  sortField: TradeSortField;
  sortDir: TradeSortDir;
  onSortChange: (field: TradeSortField, dir: TradeSortDir) => void;
  /** 활성 필터 개수 (0 이상). 0이면 reset/pill 숨김. */
  activeCount: number;
  onReset: () => void;
}

const SORT_OPTIONS: Array<{
  value: `${TradeSortField}:${TradeSortDir}`;
  label: string;
}> = [
  { value: "entry_time:desc", label: "최신순 (진입)" },
  { value: "entry_time:asc", label: "오래된순 (진입)" },
  { value: "pnl:desc", label: "수익 큰 순" },
  { value: "pnl:asc", label: "손실 큰 순" },
  { value: "return_pct:desc", label: "수익률 ↓" },
  { value: "size:desc", label: "수량 ↓" },
];

export function TradeFilterRow({
  filters,
  onFiltersChange,
  sortField,
  sortDir,
  onSortChange,
  activeCount,
  onReset,
}: TradeFilterRowProps) {
  const update = <K extends keyof ExtendedTradeFilters>(
    key: K,
    value: ExtendedTradeFilters[K],
  ) => {
    onFiltersChange({ ...filters, [key]: value });
  };

  const sortValue = `${sortField}:${sortDir}` as `${TradeSortField}:${TradeSortDir}`;

  return (
    <section
      aria-label="거래 필터"
      role="group"
      className="flex flex-wrap items-center gap-3 rounded-lg border bg-muted/30 p-4"
      data-testid="trade-filter-row"
    >
      {/* 1. 검색 */}
      <div className="relative flex h-9 w-full items-center rounded-md border bg-card pl-9 pr-3 sm:w-60">
        <svg
          className="pointer-events-none absolute left-3 h-3.5 w-3.5 text-muted-foreground"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          type="search"
          aria-label="거래 검색"
          placeholder="거래 #번호 / long·short 검색"
          value={filters.search}
          onChange={(e) => update("search", e.target.value)}
          className="w-full bg-transparent text-xs outline-none placeholder:text-muted-foreground"
        />
      </div>

      {/* 2. 방향 */}
      <Select
        value={filters.direction}
        onValueChange={(v) => update("direction", v as TradeFilters["direction"])}
      >
        <SelectTrigger className="h-9 w-32 text-xs" aria-label="방향 필터">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">방향: 전체</SelectItem>
          <SelectItem value="long">롱만</SelectItem>
          <SelectItem value="short">숏만</SelectItem>
        </SelectContent>
      </Select>

      {/* 3. 결과 */}
      <Select
        value={filters.result}
        onValueChange={(v) => update("result", v as TradeFilters["result"])}
      >
        <SelectTrigger className="h-9 w-32 text-xs" aria-label="결과 필터">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">결과: 전체</SelectItem>
          <SelectItem value="win">승리만</SelectItem>
          <SelectItem value="loss">패배만</SelectItem>
        </SelectContent>
      </Select>

      {/* 4. 기간 */}
      <div className="flex items-center gap-1.5">
        <input
          type="date"
          aria-label="기간 시작"
          value={filters.periodStart}
          onChange={(e) => update("periodStart", e.target.value)}
          className="h-9 rounded-md border bg-card px-2 font-mono text-xs"
        />
        <span aria-hidden className="text-xs text-muted-foreground">
          ~
        </span>
        <input
          type="date"
          aria-label="기간 종료"
          value={filters.periodEnd}
          onChange={(e) => update("periodEnd", e.target.value)}
          className="h-9 rounded-md border bg-card px-2 font-mono text-xs"
        />
      </div>

      {/* 5. PnL 슬라이더 (단순 min/max numeric 입력) */}
      <div className="flex items-center gap-1.5">
        <input
          type="number"
          step="0.01"
          aria-label="최소 손익 비율 (예: -0.05 = -5%)"
          placeholder="PnL≥"
          value={filters.pnlMinPct === null ? "" : filters.pnlMinPct}
          onChange={(e) =>
            update(
              "pnlMinPct",
              e.target.value === "" ? null : Number.parseFloat(e.target.value),
            )
          }
          className="h-9 w-20 rounded-md border bg-card px-2 font-mono text-xs"
        />
        <span aria-hidden className="text-xs text-muted-foreground">
          ~
        </span>
        <input
          type="number"
          step="0.01"
          aria-label="최대 손익 비율"
          placeholder="≤PnL"
          value={filters.pnlMaxPct === null ? "" : filters.pnlMaxPct}
          onChange={(e) =>
            update(
              "pnlMaxPct",
              e.target.value === "" ? null : Number.parseFloat(e.target.value),
            )
          }
          className="h-9 w-20 rounded-md border bg-card px-2 font-mono text-xs"
        />
      </div>

      {/* 6. 정렬 */}
      <Select
        value={sortValue}
        onValueChange={(v) => {
          if (!v) return;
          const [f, d] = v.split(":") as [TradeSortField, TradeSortDir];
          onSortChange(f, d);
        }}
      >
        <SelectTrigger className="h-9 w-40 text-xs" aria-label="정렬">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SORT_OPTIONS.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* 활성 pill + 초기화 */}
      <div className="ml-auto flex items-center gap-2">
        {activeCount > 0 ? (
          <>
            <span
              aria-label={`활성 필터 ${activeCount}개`}
              className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground"
            >
              필터 {activeCount}개
            </span>
            <button
              type="button"
              onClick={onReset}
              className="text-xs text-muted-foreground underline underline-offset-2 hover:text-primary"
            >
              초기화
            </button>
          </>
        ) : null}
      </div>
    </section>
  );
}

export function countActiveFilters(filters: ExtendedTradeFilters): number {
  let count = 0;
  if (filters.direction !== "all") count++;
  if (filters.result !== "all") count++;
  if (filters.search.trim() !== "") count++;
  if (filters.periodStart !== "") count++;
  if (filters.periodEnd !== "") count++;
  if (filters.pnlMinPct !== null) count++;
  if (filters.pnlMaxPct !== null) count++;
  return count;
}
