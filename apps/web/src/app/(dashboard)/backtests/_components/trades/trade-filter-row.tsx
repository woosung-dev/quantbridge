// 거래 목록 필터 툴바 — C 디자인 언어 이식(S6). 공용 .toolbar/.input/.select 를 소비한다.
// 부모(TradeDetailTable)가 상태 owner. 본 컴포넌트는 controlled inputs.
// 방향 옵션 라벨은 S4 용어 SSOT(TRADE_DIRECTION_LABEL)에서 온다.
"use client";

import { TRADE_DIRECTION_LABEL } from "@/features/backtest/labels";
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

const DIRECTION_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: "all", label: "방향 전체" },
  { value: "long", label: TRADE_DIRECTION_LABEL.long },
  { value: "short", label: TRADE_DIRECTION_LABEL.short },
];

const RESULT_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: "all", label: "결과 전체" },
  { value: "win", label: "수익" },
  { value: "loss", label: "손실" },
];

const SORT_OPTIONS: ReadonlyArray<{
  value: `${TradeSortField}:${TradeSortDir}`;
  label: string;
}> = [
  { value: "entry_time:desc", label: "최신순 (진입)" },
  { value: "entry_time:asc", label: "오래된순 (진입)" },
  { value: "pnl:desc", label: "수익 큰 순" },
  { value: "pnl:asc", label: "손실 큰 순" },
  { value: "return_pct:desc", label: "수익률 높은순" },
  { value: "size:desc", label: "수량 많은순" },
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

  const sortValue =
    `${sortField}:${sortDir}` as `${TradeSortField}:${TradeSortDir}`;

  return (
    <div
      className="toolbar"
      role="group"
      aria-label="거래 필터"
      data-testid="trade-filter-row"
    >
      {/* 1. 검색 */}
      <input
        className="input"
        type="search"
        aria-label="거래 검색"
        placeholder="거래 번호, 방향 검색"
        value={filters.search}
        onChange={(e) => update("search", e.target.value)}
      />

      {/* 2. 방향 */}
      <select
        className="select"
        aria-label="방향 필터"
        value={filters.direction}
        onChange={(e) =>
          update("direction", e.target.value as TradeFilters["direction"])
        }
      >
        {DIRECTION_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      {/* 3. 결과 */}
      <select
        className="select"
        aria-label="결과 필터"
        value={filters.result}
        onChange={(e) =>
          update("result", e.target.value as TradeFilters["result"])
        }
      >
        {RESULT_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      {/* 4. 기간 (entry_time 기준) */}
      <input
        className="input input-date"
        type="date"
        aria-label="기간 시작"
        value={filters.periodStart}
        onChange={(e) => update("periodStart", e.target.value)}
      />
      <span aria-hidden className="filter-sep">
        ~
      </span>
      <input
        className="input input-date"
        type="date"
        aria-label="기간 종료"
        value={filters.periodEnd}
        onChange={(e) => update("periodEnd", e.target.value)}
      />

      {/* 5. 손익률 범위 (decimal, e.g. -0.05 = -5%) */}
      <input
        className="input input-num"
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
      />
      <span aria-hidden className="filter-sep">
        ~
      </span>
      <input
        className="input input-num"
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
      />

      {/* 6. 정렬 */}
      <select
        className="select"
        aria-label="정렬"
        value={sortValue}
        onChange={(e) => {
          const [f, d] = e.target.value.split(":") as [
            TradeSortField,
            TradeSortDir,
          ];
          onSortChange(f, d);
        }}
      >
        {SORT_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      {/* 활성 pill + 초기화 */}
      {activeCount > 0 ? (
        <>
          <span className="chip accent" aria-label={`활성 필터 ${activeCount}개`}>
            필터 {activeCount}개
          </span>
          <button
            type="button"
            className="btn btn-ghost btn-xs"
            onClick={onReset}
          >
            초기화
          </button>
        </>
      ) : null}
    </div>
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
