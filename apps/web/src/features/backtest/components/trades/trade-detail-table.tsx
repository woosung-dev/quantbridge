// 거래 상세 표 — C 디자인 언어 이식(S6). 표·페이저·필터 프리미티브를 여기서 확립한다.
// 공용 table.trades / .side / .pager / .pg / .toolbar / .state-box / .sk 를 소비한다.
// 방향 라벨은 S4 용어 SSOT(TRADE_DIRECTION_LABEL), 무데이터 셀은 EMPTY_CELL(lib/labels).
"use client";

import { AlertTriangleIcon, DownloadIcon, InboxIcon, RefreshCwIcon } from "lucide-react";
import { useMemo, useState } from "react";

import {
  TRADE_DIRECTION_LABEL,
  TRADE_STATUS_LABEL,
  exitReasonLabel,
} from "@/features/backtest/labels";
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
import { useDebouncedValue } from "@/features/strategy/utils";
import { EMPTY_CELL } from "@/lib/labels";
import { StateBox } from "@/components/state-box";

import {
  DEFAULT_FILTERS,
  type ExtendedTradeFilters,
  TradeFilterRow,
  countActiveFilters,
} from "@/features/backtest/components/trades/trade-filter-row";
import { TradeRangeChart } from "@/features/backtest/components/trades/trade-range-chart";

const PAGE_SIZE = 50;
// BL-665 — 검색 디바운스. 선례는 diagnostics-strip(500ms)·new-strategy-wizard(300ms) 인데
// 그 둘은 **네트워크 파싱**을 늦추고 여기는 **로컬 정렬**이라 체감 지연을 더 짧게 잡는다.
const SEARCH_DEBOUNCE_MS = 200;
// 번호·방향·진입시각·청산시각·진입가·청산가·수량·손익·수익률·수수료·청산사유·펼침
const COL_COUNT = 12;
const TABLE_SKELETON_ROWS = [
  "row-1",
  "row-2",
  "row-3",
  "row-4",
  "row-5",
  "row-6",
  "row-7",
  "row-8",
] as const;
const TABLE_SKELETON_CELLS = [
  "cell-1",
  "cell-2",
  "cell-3",
  "cell-4",
  "cell-5",
  "cell-6",
  "cell-7",
  "cell-8",
  "cell-9",
  "cell-10",
  "cell-11",
  "cell-12",
] as const;

interface TradeDetailTableProps {
  backtestId?: string;
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
  backtestId,
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

  // BL-665 — 검색은 **입력 즉시** 반영하되(입력창은 계속 `filters.search` 를 그린다) 2000건
  // 정렬·필터를 다시 도는 것은 늦춘다. 레포에 이미 있는 훅을 쓴다(선례: diagnostics-strip 500ms).
  const debouncedSearch = useDebouncedValue(filters.search, SEARCH_DEBOUNCE_MS);

  // 기본 sort/filter(방향/결과) → 추가 filter(검색/기간/PnL) 적용.
  // ★dep 은 객체 `filters` 가 아니라 **스칼라 필드**다(H-1 "scalar dep 선호"). 객체를 쓰면
  //   키 한 글자마다 identity 가 갈려 이 memo 가 사실상 없는 것과 같아진다.
  const filtered = useMemo(() => {
    const base = applyTradeFilterSort(
      trades,
      { direction: filters.direction, result: filters.result },
      sortField,
      sortDir,
    );
    return base.filter((t) => {
      if (debouncedSearch.trim() !== "") {
        const q = debouncedSearch.trim().toLowerCase();
        const idxStr = t.trade_index.toString();
        // 번호 / 원시 enum(long·short) / 한국어 방향 라벨(롱·숏) 모두 검색 대상.
        const dirLabel = TRADE_DIRECTION_LABEL[t.direction];
        if (
          !idxStr.includes(q) &&
          !t.direction.toLowerCase().includes(q) &&
          !dirLabel.includes(debouncedSearch.trim())
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
  }, [
    trades,
    filters.direction,
    filters.result,
    filters.periodStart,
    filters.periodEnd,
    filters.pnlMinPct,
    filters.pnlMaxPct,
    debouncedSearch,
    sortField,
    sortDir,
  ]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  // render-time clamp (H-1) — page state 를 effect 로 되돌리지 않는다.
  const safePage = Math.min(page, totalPages - 1);
  const pageItems = useMemo(
    () => filtered.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE),
    [filtered, safePage],
  );

  // BL-665 — 배지는 표·CSV 와 **같은 스냅샷**을 세야 한다. 즉시값 `filters` 로 세면 검색어를 친
  // 뒤 디바운스가 끝나기 전 200ms 동안 「필터 1개」라고 말하면서 표와 CSV 는 아직 안 걸린
  // 전량을 보여준다(codex 적대 리뷰가 잡았다). 즉시성이 필요한 것은 **입력창 하나뿐**이다.
  const activeCount = countActiveFilters({ ...filters, search: debouncedSearch });

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
            title={activeCount > 0 ? "조건에 맞는 거래가 없습니다" : "표시할 거래가 없습니다"}
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
                <th scope="col">청산 사유</th>
                <th scope="col" aria-label="상세 펼치기" />
              </tr>
            </thead>
            <tbody>
              {pageItems.flatMap((t) => {
                const isExpanded = expandedIndex === t.trade_index;
                const isProfit = t.pnl >= 0;
                const toneClass = isProfit ? "num pos" : "num neg";
                const sideClass = t.direction === "long" ? "side long" : "side short";
                return [
                  <tr
                    key={`row-${t.trade_index}`}
                    className={isExpanded ? "trade-selected" : undefined}
                    onClick={() => handleToggleExpand(t.trade_index)}
                    data-direction={t.direction}
                  >
                    <td className="num">{t.trade_index}</td>
                    <td>
                      <span className={sideClass}>{TRADE_DIRECTION_LABEL[t.direction]}</span>
                    </td>
                    <td className="mono-l">{formatDateTime(t.entry_time)}</td>
                    <td className="mono-l">
                      {t.exit_time ? formatDateTime(t.exit_time) : EMPTY_CELL}
                    </td>
                    <td className="num">{formatCurrency(t.entry_price)}</td>
                    <td className="num">
                      {t.exit_price !== null ? formatCurrency(t.exit_price) : EMPTY_CELL}
                    </td>
                    <td className="num">{formatCurrency(t.size, 4)}</td>
                    <td className={toneClass}>{formatCurrency(t.pnl)}</td>
                    <td className={toneClass}>{formatPercent(t.return_pct)}</td>
                    <td className="num">{formatCurrency(t.fees)}</td>
                    <td>{t.exit_time ? exitReasonLabel(t.exit_kind) : "보유 중"}</td>
                    <td>
                      <button
                        type="button"
                        className="pg"
                        style={isExpanded ? { transform: "rotate(90deg)" } : undefined}
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
                        <ExpandedDetail backtestId={backtestId} trade={t} />
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

function ExpandedDetail({ backtestId, trade }: { backtestId?: string; trade: TradeItem }) {
  const isProfit = trade.pnl >= 0;
  const holdMinutes = trade.exit_time
    ? Math.max(
        0,
        Math.round(
          (new Date(trade.exit_time).getTime() - new Date(trade.entry_time).getTime()) / 60000,
        ),
      )
    : null;
  const toneP = isProfit ? "pos" : "neg";
  return (
    <>
      <section
        className="trade-detail-metrics"
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
            value={trade.exit_price !== null ? formatCurrency(trade.exit_price) : EMPTY_CELL}
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
      </section>
      {backtestId ? (
        <TradeRangeChart backtestId={backtestId} tradeIndex={trade.trade_index} trade={trade} />
      ) : null}
    </>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "pos" | "neg" }) {
  const valueClass =
    tone === "pos" ? "metric-value pos" : tone === "neg" ? "metric-value neg" : "metric-value";
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
          {pageWindow(page, totalPages).map((p) =>
            typeof p === "string" ? (
              // 생략 기호는 **조작 대상이 아니다** — 버튼이면 aria-hidden 이 상호작용 요소를
              // 숨기는 모양이 된다(a11y/noAriaHiddenOnFocusable). span 이 맞는 마크업이다.
              <span key={p} className="pg" aria-hidden="true">
                …
              </span>
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
function pageWindow(
  page0: number,
  totalPages: number,
): (number | "leading-gap" | "trailing-gap")[] {
  const cur = page0 + 1;
  const want = new Set<number>([1, totalPages, cur, cur - 1, cur + 1]);
  const sorted = [...want].filter((p) => p >= 1 && p <= totalPages).sort((a, b) => a - b);
  const out: (number | "leading-gap" | "trailing-gap")[] = [];
  let prev = 0;
  for (const p of sorted) {
    if (p - prev > 1) out.push(prev === 1 ? "leading-gap" : "trailing-gap");
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
          {TABLE_SKELETON_ROWS.map((rowKey) => (
            <tr key={rowKey}>
              {TABLE_SKELETON_CELLS.map((cellKey) => (
                <td key={cellKey}>
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
