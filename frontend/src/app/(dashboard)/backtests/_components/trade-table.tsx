"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { TradeItem } from "@/features/backtest/schemas";
import {
  type TradeFilters,
  type TradeSortDir,
  type TradeSortField,
  applyTradeFilterSort,
  downloadCsv,
  formatCurrency,
  formatDateTime,
  formatPercent,
  tradesToCsv,
} from "@/features/backtest/utils";
import { cn } from "@/lib/utils";

const TRADE_LIMIT = 200;

const SORT_LABEL: Record<TradeSortField, string> = {
  entry_time: "진입",
  exit_time: "청산",
  pnl: "PnL",
  return_pct: "Return",
  size: "Size",
};

interface TradeTableProps {
  trades: readonly TradeItem[];
  /** CSV 파일명 prefix (예: backtest-id 짧은 형태). 미제공 시 "trades". */
  filenamePrefix?: string;
}

export function TradeTable({ trades, filenamePrefix = "trades" }: TradeTableProps) {
  // Sprint 30-δ scope: 200 cap 안에서 필터/정렬/CSV. 1000+ pagination 누적은
  // Sprint 31+ deferred (BL-150 후속).
  const visible = trades.slice(0, TRADE_LIMIT);
  const truncated = trades.length > TRADE_LIMIT;

  // LESSON-004 H-1: scalar dep 만. filters 는 객체이지만 deps 에 .direction /
  // .result primitive 로 분해 사용.
  const [sortField, setSortField] = useState<TradeSortField>("entry_time");
  const [sortDir, setSortDir] = useState<TradeSortDir>("asc");
  const [directionFilter, setDirectionFilter] =
    useState<TradeFilters["direction"]>("all");
  const [resultFilter, setResultFilter] =
    useState<TradeFilters["result"]>("all");

  const filtered = useMemo(
    () =>
      applyTradeFilterSort(
        visible,
        { direction: directionFilter, result: resultFilter },
        sortField,
        sortDir,
      ),
    [visible, directionFilter, resultFilter, sortField, sortDir],
  );

  // 누적 PnL — 정렬/필터 후 결과에 대해 재계산 (사용자 시각 컨텍스트와 일치).
  const tradesWithCumulative = useMemo(
    () =>
      filtered.reduce<Array<TradeItem & { cumulativePnl: number }>>(
        (acc, t) => {
          const prevCum = acc.at(-1)?.cumulativePnl ?? 0;
          const pnl = Number.isFinite(t.pnl) ? t.pnl : 0;
          return [...acc, { ...t, cumulativePnl: prevCum + pnl }];
        },
        [],
      ),
    [filtered],
  );

  const handleSort = (field: TradeSortField) => {
    if (sortField === field) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir(field === "entry_time" ? "asc" : "desc");
    }
  };

  const handleExport = () => {
    const csv = tradesToCsv(filtered);
    const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    downloadCsv(`${filenamePrefix}-${ts}.csv`, csv);
  };

  if (visible.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
        기록된 거래가 없습니다
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={directionFilter}
            onValueChange={(v) =>
              setDirectionFilter(v as TradeFilters["direction"])
            }
          >
            <SelectTrigger className="w-32" aria-label="방향 필터">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">방향: 전체</SelectItem>
              <SelectItem value="long">롱만</SelectItem>
              <SelectItem value="short">숏만</SelectItem>
            </SelectContent>
          </Select>
          <Select
            value={resultFilter}
            onValueChange={(v) =>
              setResultFilter(v as TradeFilters["result"])
            }
          >
            <SelectTrigger className="w-32" aria-label="결과 필터">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">결과: 전체</SelectItem>
              <SelectItem value="win">승리만</SelectItem>
              <SelectItem value="loss">패배만</SelectItem>
            </SelectContent>
          </Select>
          <span className="text-xs text-muted-foreground">
            {filtered.length} / {visible.length} 건
          </span>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleExport}
          disabled={filtered.length === 0}
          aria-label="CSV 내보내기"
        >
          ⬇ CSV
        </Button>
      </div>

      <div className="overflow-x-auto rounded-lg border bg-card">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th scope="col" className="px-3 py-2 text-left">
                #
              </th>
              <th scope="col" className="px-3 py-2 text-left">
                방향
              </th>
              <SortableHeader
                field="entry_time"
                label={SORT_LABEL.entry_time}
                currentField={sortField}
                currentDir={sortDir}
                onSort={handleSort}
                align="left"
              />
              <SortableHeader
                field="exit_time"
                label={SORT_LABEL.exit_time}
                currentField={sortField}
                currentDir={sortDir}
                onSort={handleSort}
                align="left"
              />
              <SortableHeader
                field="size"
                label={SORT_LABEL.size}
                currentField={sortField}
                currentDir={sortDir}
                onSort={handleSort}
                align="right"
              />
              <SortableHeader
                field="pnl"
                label={SORT_LABEL.pnl}
                currentField={sortField}
                currentDir={sortDir}
                onSort={handleSort}
                align="right"
              />
              <SortableHeader
                field="return_pct"
                label={SORT_LABEL.return_pct}
                currentField={sortField}
                currentDir={sortDir}
                onSort={handleSort}
                align="right"
              />
              <th scope="col" className="px-3 py-2 text-right">
                누적 PnL
              </th>
            </tr>
          </thead>
          <tbody>
            {tradesWithCumulative.length === 0 ? (
              <tr>
                <td
                  colSpan={8}
                  className="px-3 py-8 text-center text-sm text-muted-foreground"
                >
                  필터 조건에 일치하는 거래가 없습니다
                </td>
              </tr>
            ) : (
              tradesWithCumulative.map((t) => (
                <tr
                  key={t.trade_index}
                  className="border-t"
                  data-direction={t.direction}
                >
                  <td className="px-3 py-2 tabular-nums">{t.trade_index}</td>
                  <td className="px-3 py-2 uppercase">
                    <span data-dir={t.direction}>{t.direction}</span>
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground tabular-nums">
                    {formatDateTime(t.entry_time)}
                    <div className="text-foreground">
                      {formatCurrency(t.entry_price)}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-xs text-muted-foreground tabular-nums">
                    {formatDateTime(t.exit_time)}
                    <div className="text-foreground">
                      {t.exit_price !== null
                        ? formatCurrency(t.exit_price)
                        : "—"}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {formatCurrency(t.size, 4)}
                  </td>
                  <td className="relative overflow-hidden px-3 py-2 text-right tabular-nums">
                    <div
                      className="absolute inset-y-0 right-0 opacity-15"
                      style={{
                        width: `${Math.min(Math.abs(t.return_pct) * 100, 100)}%`,
                        backgroundColor:
                          t.pnl >= 0 ? "rgb(34,197,94)" : "rgb(239,68,68)",
                      }}
                    />
                    <span
                      className={cn(
                        "relative",
                        t.pnl >= 0 ? "text-green-500" : "text-red-500",
                      )}
                      data-tone={t.pnl >= 0 ? "positive" : "negative"}
                    >
                      {formatCurrency(t.pnl)}
                    </span>
                  </td>
                  <td
                    className="px-3 py-2 text-right tabular-nums"
                    data-tone={t.return_pct >= 0 ? "positive" : "negative"}
                  >
                    {formatPercent(t.return_pct)}
                  </td>
                  <td
                    className={cn(
                      "px-3 py-2 text-right font-mono tabular-nums",
                      t.cumulativePnl >= 0
                        ? "text-green-500"
                        : "text-red-500",
                    )}
                  >
                    {t.cumulativePnl >= 0 ? "+" : ""}
                    {t.cumulativePnl.toFixed(2)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        {truncated ? (
          <p className="border-t bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
            최대 {TRADE_LIMIT}건만 표시됩니다. 전체 결과는 CSV 내보내기로 확인하세요.
          </p>
        ) : null}
      </div>
    </div>
  );
}

interface SortableHeaderProps {
  field: TradeSortField;
  label: string;
  currentField: TradeSortField;
  currentDir: TradeSortDir;
  onSort: (field: TradeSortField) => void;
  align: "left" | "right";
}

function SortableHeader({
  field,
  label,
  currentField,
  currentDir,
  onSort,
  align,
}: SortableHeaderProps) {
  const isActive = currentField === field;
  const indicator = isActive ? (currentDir === "asc" ? "↑" : "↓") : "";

  return (
    <th
      scope="col"
      className={cn(
        "px-3 py-2",
        align === "left" ? "text-left" : "text-right",
      )}
      aria-sort={
        isActive
          ? currentDir === "asc"
            ? "ascending"
            : "descending"
          : "none"
      }
    >
      <button
        type="button"
        onClick={() => onSort(field)}
        className={cn(
          "inline-flex items-center gap-1 hover:text-foreground",
          isActive && "text-foreground",
        )}
      >
        {label}
        {indicator ? (
          <span className="text-[10px]" aria-hidden>
            {indicator}
          </span>
        ) : null}
      </button>
    </th>
  );
}

export { TRADE_LIMIT };
