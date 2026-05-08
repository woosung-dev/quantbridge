// Sprint 43 W11 — 거래 상세 표 (행 expand + CSV + pageSize 50 페이지네이션).
// 기존 trade-table.tsx 의 sort/filter/CSV 패턴 재사용 + 6 필터 + 행 클릭 expand.
"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import type { TradeItem } from "@/features/backtest/schemas";
import {
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

import {
  DEFAULT_FILTERS,
  type ExtendedTradeFilters,
  TradeFilterRow,
  countActiveFilters,
} from "./trade-filter-row";

const PAGE_SIZE = 50;

interface TradeDetailTableProps {
  trades: readonly TradeItem[];
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  filenamePrefix: string;
}

export function TradeDetailTable({
  trades,
  isLoading,
  isError,
  errorMessage,
  filenamePrefix,
}: TradeDetailTableProps) {
  const [filters, setFilters] = useState<ExtendedTradeFilters>(DEFAULT_FILTERS);
  const [sortField, setSortField] = useState<TradeSortField>("entry_time");
  const [sortDir, setSortDir] = useState<TradeSortDir>("desc");
  const [page, setPage] = useState(0);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  // 기본 sort/filter (방향/결과) → 추가 filter (검색/기간/PnL) 적용.
  const filtered = useMemo(() => {
    const base = applyTradeFilterSort(
      trades,
      { direction: filters.direction, result: filters.result },
      sortField,
      sortDir,
    );

    return base.filter((t) => {
      // 검색: trade_index 또는 direction string match
      if (filters.search.trim() !== "") {
        const q = filters.search.trim().toLowerCase();
        const idxStr = t.trade_index.toString();
        if (!idxStr.includes(q) && !t.direction.toLowerCase().includes(q)) {
          return false;
        }
      }
      // 기간 필터 (entry_time 기준)
      if (filters.periodStart !== "") {
        if (t.entry_time.slice(0, 10) < filters.periodStart) return false;
      }
      if (filters.periodEnd !== "") {
        if (t.entry_time.slice(0, 10) > filters.periodEnd) return false;
      }
      // PnL 범위
      if (filters.pnlMinPct !== null && Number.isFinite(filters.pnlMinPct)) {
        if (t.return_pct < filters.pnlMinPct) return false;
      }
      if (filters.pnlMaxPct !== null && Number.isFinite(filters.pnlMaxPct)) {
        if (t.return_pct > filters.pnlMaxPct) return false;
      }
      return true;
    });
  }, [trades, filters, sortField, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const pageItems = useMemo(
    () => filtered.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE),
    [filtered, safePage],
  );

  const activeCount = countActiveFilters(filters);

  const handleResetFilters = () => {
    setFilters(DEFAULT_FILTERS);
    setPage(0);
  };

  const handleExport = () => {
    const csv = tradesToCsv(filtered);
    const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
    downloadCsv(`${filenamePrefix}-${ts}.csv`, csv);
  };

  const handleToggleExpand = (idx: number) => {
    setExpandedIndex((prev) => (prev === idx ? null : idx));
  };

  if (isLoading) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        거래 불러오는 중…
      </p>
    );
  }

  if (isError) {
    return (
      <p className="py-12 text-center text-sm text-destructive">
        거래 기록 로드 실패: {errorMessage ?? "알 수 없는 오류"}
      </p>
    );
  }

  return (
    <div className="space-y-3" data-testid="trade-detail-table">
      <TradeFilterRow
        filters={filters}
        onFiltersChange={(next) => {
          setFilters(next);
          setPage(0);
        }}
        sortField={sortField}
        sortDir={sortDir}
        onSortChange={(f, d) => {
          setSortField(f);
          setSortDir(d);
        }}
        activeCount={activeCount}
        onReset={handleResetFilters}
      />

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {filtered.length} / {trades.length} 건 ·{" "}
          {totalPages > 1 ? `페이지 ${safePage + 1} / ${totalPages}` : null}
        </span>
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

      <div className="overflow-x-auto rounded-lg border bg-card shadow-sm">
        <table className="w-full text-sm" role="table">
          <caption className="sr-only">
            백테스트 거래 내역 표. 컬럼 정렬 가능, 행 클릭으로 상세 확장.
          </caption>
          <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th scope="col" className="px-3 py-2 text-right">
                #
              </th>
              <th scope="col" className="px-3 py-2 text-left">
                진입
              </th>
              <th scope="col" className="px-3 py-2 text-left">
                청산
              </th>
              <th scope="col" className="px-3 py-2 text-center">
                방향
              </th>
              <th scope="col" className="px-3 py-2 text-right">
                진입가
              </th>
              <th scope="col" className="px-3 py-2 text-right">
                청산가
              </th>
              <th scope="col" className="px-3 py-2 text-right">
                수량
              </th>
              <th scope="col" className="px-3 py-2 text-right">
                수익
              </th>
              <th scope="col" className="px-3 py-2 text-right">
                수익(%)
              </th>
              <th scope="col" className="px-3 py-2 text-right">
                수수료
              </th>
              <th scope="col" className="px-3 py-2 text-center" aria-label="상세">
                {""}
              </th>
            </tr>
          </thead>
          <tbody>
            {pageItems.length === 0 ? (
              <tr>
                <td
                  colSpan={11}
                  className="px-3 py-12 text-center text-sm text-muted-foreground"
                >
                  <div className="flex flex-col items-center gap-2">
                    <span>필터 조건에 일치하는 거래가 없습니다</span>
                    {activeCount > 0 ? (
                      <button
                        type="button"
                        onClick={handleResetFilters}
                        className="text-xs font-semibold text-primary underline underline-offset-2 hover:text-primary/80"
                        data-testid="trade-empty-reset"
                      >
                        모든 필터 초기화
                      </button>
                    ) : null}
                  </div>
                </td>
              </tr>
            ) : (
              pageItems.flatMap((t) => {
                const isExpanded = expandedIndex === t.trade_index;
                const isProfit = t.pnl >= 0;
                return [
                  <tr
                    key={`row-${t.trade_index}`}
                    onClick={() => handleToggleExpand(t.trade_index)}
                    className={cn(
                      "qb-trade-row cursor-pointer border-t hover:bg-muted/40",
                      isExpanded && "bg-primary/5",
                    )}
                    data-direction={t.direction}
                  >
                    <td className="px-3 py-2 text-right font-mono text-xs text-muted-foreground">
                      {t.trade_index}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                      {formatDateTime(t.entry_time)}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                      {t.exit_time ? formatDateTime(t.exit_time) : "—"}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <span
                        className={cn(
                          "inline-flex rounded px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider",
                          t.direction === "long"
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-rose-100 text-rose-700",
                        )}
                      >
                        {t.direction}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums">
                      {formatCurrency(t.entry_price)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums">
                      {t.exit_price !== null ? formatCurrency(t.exit_price) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums">
                      {formatCurrency(t.size, 4)}
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2 text-right font-mono font-semibold tabular-nums",
                        isProfit ? "text-emerald-600" : "text-rose-600",
                      )}
                    >
                      {formatCurrency(t.pnl)}
                    </td>
                    <td
                      className={cn(
                        "px-3 py-2 text-right font-mono tabular-nums",
                        isProfit ? "text-emerald-600" : "text-rose-600",
                      )}
                    >
                      {formatPercent(t.return_pct)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-xs text-rose-500/80">
                      {formatCurrency(t.fees)}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <button
                        type="button"
                        onClick={(e) => {
                          // row click 과 동일 동작이지만 propagation 방지로 button 단독
                          // 키보드 활성화 (Enter/Space) 시에도 toggle 1회만 발생.
                          e.stopPropagation();
                          handleToggleExpand(t.trade_index);
                        }}
                        aria-expanded={isExpanded}
                        aria-label={
                          isExpanded
                            ? `거래 #${t.trade_index} 상세 닫기`
                            : `거래 #${t.trade_index} 상세 보기`
                        }
                        className={cn(
                          "inline-flex h-6 w-6 items-center justify-center rounded text-muted-foreground transition-all hover:bg-muted hover:text-primary",
                          isExpanded && "rotate-90 text-primary",
                        )}
                      >
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          aria-hidden
                        >
                          <polyline points="9 18 15 12 9 6" />
                        </svg>
                      </button>
                    </td>
                  </tr>,
                  isExpanded ? (
                    <tr key={`detail-${t.trade_index}`} aria-live="polite">
                      <td colSpan={11} className="border-t bg-primary/5 px-3 pb-4 pt-1">
                        <ExpandedDetail trade={t} />
                      </td>
                    </tr>
                  ) : null,
                ];
              })
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 ? (
        <div className="flex items-center justify-between text-xs">
          <Button
            variant="outline"
            size="sm"
            disabled={safePage === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            aria-label="이전 페이지"
          >
            ← 이전
          </Button>
          <span className="text-muted-foreground">
            {safePage + 1} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={safePage >= totalPages - 1}
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            aria-label="다음 페이지"
          >
            다음 →
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function ExpandedDetail({ trade }: { trade: TradeItem }) {
  const isProfit = trade.pnl >= 0;
  const holdMinutes = trade.exit_time
    ? Math.max(
        0,
        Math.round(
          (new Date(trade.exit_time).getTime() -
            new Date(trade.entry_time).getTime()) /
            60000,
        ),
      )
    : null;
  return (
    <div
      role="region"
      aria-label={`거래 #${trade.trade_index} 상세 정보`}
      className="grid grid-cols-1 gap-4 rounded-md border border-primary/20 bg-card p-4 sm:grid-cols-3"
      data-testid="trade-detail-expanded"
    >
      <DetailSection title="진입 정보">
        <DetailItem label="시간" value={formatDateTime(trade.entry_time)} />
        <DetailItem label="진입가" value={formatCurrency(trade.entry_price)} />
        <DetailItem
          label="수량"
          value={`${formatCurrency(trade.size, 4)}`}
        />
        <DetailItem
          label="방향"
          value={trade.direction.toUpperCase()}
        />
      </DetailSection>
      <DetailSection title="청산 정보">
        <DetailItem
          label="시간"
          value={trade.exit_time ? formatDateTime(trade.exit_time) : "—"}
        />
        <DetailItem
          label="청산가"
          value={
            trade.exit_price !== null ? formatCurrency(trade.exit_price) : "—"
          }
        />
        <DetailItem
          label="상태"
          value={trade.status === "closed" ? "청산 완료" : "보유 중"}
        />
        <DetailItem
          label="보유 시간"
          value={holdMinutes !== null ? formatHoldMinutes(holdMinutes) : "—"}
        />
      </DetailSection>
      <DetailSection title="성과">
        <DetailItem
          label="손익"
          value={formatCurrency(trade.pnl)}
          tone={isProfit ? "pos" : "neg"}
        />
        <DetailItem
          label="수익률"
          value={formatPercent(trade.return_pct)}
          tone={isProfit ? "pos" : "neg"}
        />
        <DetailItem
          label="수수료"
          value={formatCurrency(trade.fees)}
          tone="neg"
        />
      </DetailSection>
    </div>
  );
}

function DetailSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="mb-2 font-display text-xs font-bold uppercase tracking-wider text-primary">
        {title}
      </h3>
      <ul className="flex flex-col gap-1.5">{children}</ul>
    </div>
  );
}

function DetailItem({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string;
  tone?: "pos" | "neg" | "neutral";
}) {
  const toneClass =
    tone === "pos"
      ? "text-emerald-600"
      : tone === "neg"
        ? "text-rose-600"
        : "text-foreground";
  return (
    <li className="flex items-baseline justify-between gap-3 text-xs text-muted-foreground">
      <span>{label}</span>
      <span className={`font-mono font-semibold ${toneClass}`}>{value}</span>
    </li>
  );
}

function formatHoldMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h}h ${m}m`;
}
