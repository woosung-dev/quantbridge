// 거래 상세 표 — C 디자인 언어 이식(S6). 표·페이저·필터 프리미티브를 여기서 확립한다.
// 공용 table.trades / .side / .pager / .pg / .toolbar / .state-box / .sk 를 소비한다.
// 방향 라벨은 S4 용어 SSOT(TRADE_DIRECTION_LABEL), 무데이터 셀은 EMPTY_CELL(lib/labels).
"use client";

import { AlertTriangleIcon, DownloadIcon, InboxIcon, RefreshCwIcon } from "lucide-react";
import { useMemo, useState } from "react";

import { TRADE_DIRECTION_LABEL, TRADE_STATUS_LABEL } from "@/features/backtest/labels";
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
import { EMPTY_CELL } from "@/lib/labels";
import { StateBox } from "@/components/state-box";

import {
  DEFAULT_FILTERS,
  type ExtendedTradeFilters,
  TradeFilterRow,
  countActiveFilters,
} from "@/app/(dashboard)/backtests/_components/trades/trade-filter-row";

const PAGE_SIZE = 50;
const COL_COUNT = 11;

interface TradeDetailTableProps {
  trades: readonly TradeItem[];
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  /** 에러 상태 state-code 에 노출할 실제 엔드포인트 (프로토타입 관례). */
  endpoint: string;
  /** 에러 상태 다시 시도 핸들러. */
  onRetry?: () => void;
  filenamePrefix: string;
}

export function TradeDetailTable({
  trades,
  isLoading,
  isError,
  errorMessage,
  endpoint,
  onRetry,
  filenamePrefix,
}: TradeDetailTableProps) {
  const [filters, setFilters] = useState<ExtendedTradeFilters>(DEFAULT_FILTERS);
  const [sortField, setSortField] = useState<TradeSortField>("entry_time");
  const [sortDir, setSortDir] = useState<TradeSortDir>("desc");
  const [page, setPage] = useState(0);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  // 기본 sort/filter(방향/결과) → 추가 filter(검색/기간/PnL) 적용.
  const filtered = useMemo(() => {
    const base = applyTradeFilterSort(
      trades,
      { direction: filters.direction, result: filters.result },
      sortField,
      sortDir,
    );
    return base.filter((t) => {
      if (filters.search.trim() !== "") {
        const q = filters.search.trim().toLowerCase();
        const idxStr = t.trade_index.toString();
        // 번호 / 원시 enum(long·short) / 한국어 방향 라벨(롱·숏) 모두 검색 대상.
        const dirLabel = TRADE_DIRECTION_LABEL[t.direction];
        if (
          !idxStr.includes(q) &&
          !t.direction.toLowerCase().includes(q) &&
          !dirLabel.includes(filters.search.trim())
        ) {
          return false;
        }
      }
      if (filters.periodStart !== "" && t.entry_time.slice(0, 10) < filters.periodStart) {
        return false;
      }
      if (filters.periodEnd !== "" && t.entry_time.slice(0, 10) > filters.periodEnd) {
        return false;
      }
      if (
        filters.pnlMinPct !== null &&
        Number.isFinite(filters.pnlMinPct) &&
        t.return_pct < filters.pnlMinPct
      ) {
        return false;
      }
      if (
        filters.pnlMaxPct !== null &&
        Number.isFinite(filters.pnlMaxPct) &&
        t.return_pct > filters.pnlMaxPct
      ) {
        return false;
      }
      return true;
    });
  }, [trades, filters, sortField, sortDir]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  // render-time clamp (H-1) — page state 를 effect 로 되돌리지 않는다.
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

  const subText =
    trades.length === filtered.length
      ? `${trades.length}건`
      : `${filtered.length}건 표시 · 전체 ${trades.length}건`;

  return (
    <div className="card" data-testid="trade-detail-table">
      <div className="card-head">
        <div>
          <h3 className="card-title">거래 목록</h3>
          <p className="card-sub">{subText}</p>
        </div>
        <div className="chart-head-actions">
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
          <button
            type="button"
            className="btn btn-ghost"
            aria-label="CSV 내보내기"
            disabled={filtered.length === 0}
            onClick={handleExport}
          >
            <DownloadIcon aria-hidden="true" />
            CSV
          </button>
        </div>
      </div>

      {isLoading ? (
        <TableSkeleton />
      ) : isError ? (
        <div className="card-body">
          <StateBox
            tone="failed"
            testId="trade-error"
            icon={<AlertTriangleIcon />}
            title="거래 기록을 불러오지 못했습니다."
            body={errorMessage ?? "네트워크 또는 서버 상태 일시적 오류일 수 있습니다."}
            code={endpoint}
          >
            {onRetry ? (
              <button className="btn btn-ghost" type="button" onClick={onRetry}>
                <RefreshCwIcon aria-hidden="true" />
                다시 시도
              </button>
            ) : null}
          </StateBox>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card-body">
          <StateBox
            testId="trade-empty"
            icon={<InboxIcon />}
            title={
              activeCount > 0
                ? "조건에 맞는 거래가 없습니다"
                : "표시할 거래가 없습니다"
            }
            body={
              activeCount > 0
                ? "필터를 완화하거나 초기화하면 거래가 다시 나타납니다."
                : "완료된 실행에서만 체결이 기록됩니다."
            }
          >
            {activeCount > 0 ? (
              <button
                className="btn btn-ghost btn-xs"
                type="button"
                onClick={handleResetFilters}
                data-testid="trade-empty-reset"
              >
                모든 필터 초기화
              </button>
            ) : null}
          </StateBox>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="trades" aria-label={`거래 내역 ${filtered.length}건`}>
            <thead>
              <tr>
                <th scope="col" className="num">
                  번호
                </th>
                <th scope="col">방향</th>
                <th scope="col">진입 시각</th>
                <th scope="col">청산 시각</th>
                <th scope="col" className="num">
                  진입가
                </th>
                <th scope="col" className="num">
                  청산가
                </th>
                <th scope="col" className="num">
                  수량
                </th>
                <th scope="col" className="num">
                  손익
                </th>
                <th scope="col" className="num">
                  수익률
                </th>
                <th scope="col" className="num">
                  수수료
                </th>
                <th scope="col" aria-label="상세 펼치기" />
              </tr>
            </thead>
            <tbody>
              {pageItems.flatMap((t) => {
                const isExpanded = expandedIndex === t.trade_index;
                const isProfit = t.pnl >= 0;
                const toneClass = isProfit ? "num pos" : "num neg";
                const sideClass =
                  t.direction === "long" ? "side long" : "side short";
                return [
                  <tr
                    key={`row-${t.trade_index}`}
                    className={isExpanded ? "trade-selected" : undefined}
                    onClick={() => handleToggleExpand(t.trade_index)}
                    data-direction={t.direction}
                  >
                    <td className="num">{t.trade_index}</td>
                    <td>
                      <span className={sideClass}>
                        {TRADE_DIRECTION_LABEL[t.direction]}
                      </span>
                    </td>
                    <td className="mono-l">{formatDateTime(t.entry_time)}</td>
                    <td className="mono-l">
                      {t.exit_time ? formatDateTime(t.exit_time) : EMPTY_CELL}
                    </td>
                    <td className="num">{formatCurrency(t.entry_price)}</td>
                    <td className="num">
                      {t.exit_price !== null
                        ? formatCurrency(t.exit_price)
                        : EMPTY_CELL}
                    </td>
                    <td className="num">{formatCurrency(t.size, 4)}</td>
                    <td className={toneClass}>{formatCurrency(t.pnl)}</td>
                    <td className={toneClass}>{formatPercent(t.return_pct)}</td>
                    <td className="num">{formatCurrency(t.fees)}</td>
                    <td>
                      <button
                        type="button"
                        className="pg"
                        style={
                          isExpanded ? { transform: "rotate(90deg)" } : undefined
                        }
                        aria-expanded={isExpanded}
                        aria-label={
                          isExpanded
                            ? `거래 #${t.trade_index} 상세 닫기`
                            : `거래 #${t.trade_index} 상세 보기`
                        }
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleExpand(t.trade_index);
                        }}
                      >
                        <svg
                          width="13"
                          height="13"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.4"
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
                      <td className="trade-detail-cell" colSpan={COL_COUNT}>
                        <ExpandedDetail trade={t} />
                      </td>
                    </tr>
                  ) : null,
                ];
              })}
            </tbody>
          </table>
        </div>
      )}

      {!isLoading && !isError && filtered.length > 0 ? (
        <Pager
          page={safePage}
          totalPages={totalPages}
          totalItems={filtered.length}
          pageSize={PAGE_SIZE}
          onPage={setPage}
        />
      ) : null}
    </div>
  );
}

// --- 펼침 상세 — 진입/청산/성과 3열. 공용 .metric-group/.metric 소비. ------------

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
  const toneP = isProfit ? "pos" : "neg";
  return (
    <div
      className="trade-detail-metrics"
      role="region"
      aria-label={`거래 #${trade.trade_index} 상세 정보`}
      data-testid="trade-detail-expanded"
    >
      <div className="metric-group">
        <p className="metric-group-title">진입 정보</p>
        <Metric label="시각" value={formatDateTime(trade.entry_time)} />
        <Metric label="진입가" value={formatCurrency(trade.entry_price)} />
        <Metric label="수량" value={formatCurrency(trade.size, 4)} />
        <Metric label="방향" value={TRADE_DIRECTION_LABEL[trade.direction]} />
      </div>
      <div className="metric-group">
        <p className="metric-group-title">청산 정보</p>
        <Metric
          label="시각"
          value={trade.exit_time ? formatDateTime(trade.exit_time) : EMPTY_CELL}
        />
        <Metric
          label="청산가"
          value={
            trade.exit_price !== null
              ? formatCurrency(trade.exit_price)
              : EMPTY_CELL
          }
        />
        <Metric label="상태" value={TRADE_STATUS_LABEL[trade.status]} />
        <Metric
          label="보유 시간"
          value={holdMinutes !== null ? formatHoldMinutes(holdMinutes) : EMPTY_CELL}
        />
      </div>
      <div className="metric-group">
        <p className="metric-group-title">성과</p>
        <Metric label="손익" value={formatCurrency(trade.pnl)} tone={toneP} />
        <Metric label="수익률" value={formatPercent(trade.return_pct)} tone={toneP} />
        <Metric label="수수료" value={formatCurrency(trade.fees)} />
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "pos" | "neg";
}) {
  const valueClass =
    tone === "pos"
      ? "metric-value pos"
      : tone === "neg"
        ? "metric-value neg"
        : "metric-value";
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <span className={valueClass}>{value}</span>
    </div>
  );
}

// --- 페이저 프리미티브 — 이후 표 화면이 따른다. -------------------------------

interface PagerProps {
  page: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  onPage: (page: number) => void;
}

function Pager({ page, totalPages, totalItems, pageSize, onPage }: PagerProps) {
  const from = page * pageSize + 1;
  const to = Math.min((page + 1) * pageSize, totalItems);
  return (
    <div className="pager">
      <span>
        {totalItems}건 중 {from}번부터 {to}번까지
      </span>
      {totalPages > 1 ? (
        <span className="pager-nums">
          <button
            type="button"
            className="pg"
            aria-label="이전 페이지"
            disabled={page === 0}
            onClick={() => onPage(Math.max(0, page - 1))}
          >
            ‹
          </button>
          {pageWindow(page, totalPages).map((p, i) =>
            p === "gap" ? (
              <button
                key={`gap-${i}`}
                type="button"
                className="pg"
                aria-hidden="true"
                disabled
              >
                …
              </button>
            ) : (
              <button
                key={p}
                type="button"
                className={p - 1 === page ? "pg active" : "pg"}
                aria-current={p - 1 === page ? "page" : undefined}
                onClick={() => onPage(p - 1)}
              >
                {p}
              </button>
            ),
          )}
          <button
            type="button"
            className="pg"
            aria-label="다음 페이지"
            disabled={page >= totalPages - 1}
            onClick={() => onPage(Math.min(totalPages - 1, page + 1))}
          >
            ›
          </button>
        </span>
      ) : null}
    </div>
  );
}

// 1-indexed 페이지 번호 창 — 첫/끝/현재±1 + 사이 gap. prototype: ‹ 1 2 … 19 › 관례.
function pageWindow(page0: number, totalPages: number): (number | "gap")[] {
  const cur = page0 + 1;
  const want = new Set<number>([1, totalPages, cur, cur - 1, cur + 1]);
  const sorted = [...want].filter((p) => p >= 1 && p <= totalPages).sort((a, b) => a - b);
  const out: (number | "gap")[] = [];
  let prev = 0;
  for (const p of sorted) {
    if (p - prev > 1) out.push("gap");
    out.push(p);
    prev = p;
  }
  return out;
}

// 다음 페이지를 불러오는 동안의 스켈레톤 — S5 aria-busy tbody 관례(.sk .sk-cell).
function TableSkeleton() {
  return (
    <div className="table-wrap" data-testid="trade-skeleton" aria-hidden="true">
      <table className="trades">
        <tbody>
          {Array.from({ length: 8 }).map((_, i) => (
            <tr key={i}>
              {Array.from({ length: COL_COUNT }).map((__, j) => (
                <td key={j}>
                  <span className="sk sk-cell" />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatHoldMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h}h ${m}m`;
}
