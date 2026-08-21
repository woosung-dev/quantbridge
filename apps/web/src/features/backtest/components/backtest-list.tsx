"use client";

// 백테스트 목록 — C 디자인 언어 이식 (S5). 프로토타입 screen-03 의 시맨틱 CSS 를 소비하고,
// list projection 의 metrics_summary 와 전략 목록 이름 맵으로 성과 4칸과 전략명을 정직하게 그린다.
// 목록 API가 정렬 결과를 돌려주므로 페이지 내 client sort 는 하지 않는다.
// 상태 라벨·톤은 S4 용어 SSOT(BACKTEST_STATUS_LABEL) → CHIP_TONE_CLASS 로 파생한다.

import Link from "next/link";
import { useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangleIcon,
  ArrowDownUpIcon,
  CheckIcon,
  InboxIcon,
  PlusIcon,
  RefreshCwIcon,
} from "lucide-react";

import {
  BACKTEST_LIST_HEADER,
  BACKTEST_LIST_SORT_LABEL,
  BACKTEST_STATUS_FILTER_LABEL,
  BACKTEST_STATUS_LABEL,
  NEW_BACKTEST_LABEL,
} from "@/features/backtest/labels";
import { useBacktests } from "@/features/backtest/hooks";
import {
  buildBacktestListQuery,
  resolveBacktestSort,
  type BacktestOrder,
  type BacktestOrderBy,
} from "@/features/backtest/list-query";
import type { BacktestStatus, BacktestSummary } from "@/features/backtest/schemas";
import { describeSharpe } from "@/features/backtest/sharpe-convention";
import { formatDateTime, formatPercent } from "@/features/backtest/utils";
import { useStrategies } from "@/features/strategy/hooks";
import { StateBox } from "@/components/state-box";
import { CHIP_TONE_CLASS, EMPTY_CELL } from "@/lib/labels";

// 목록 조회 엔드포인트 — 에러 상태에 실제 경로를 노출한다 (프로토타입 state-code 관례).
const LIST_ENDPOINT = "GET /api/v1/backtests";
const STRATEGY_FETCH_LIMIT = 100;
const RETURN_METRIC = "total_return";
const UNFINISHED_METRICS_TITLE = "아직 끝나지 않은 실행은 수익률을 채우지 않습니다.";
const LIST_SKELETON_ROWS = ["row-1", "row-2", "row-3", "row-4", "row-5", "row-6"] as const;
const LIST_SKELETON_CELLS = [
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
] as const;

// 라벨은 용어 SSOT(BACKTEST_STATUS_FILTER_LABEL)에서 파생 — 배지 표기와 불일치 방지.
const STATUS_FILTERS: ReadonlyArray<{ id: "all" | BacktestStatus }> = [
  { id: "all" },
  { id: "completed" },
  { id: "running" },
  { id: "queued" },
  { id: "failed" },
  { id: "cancelled" },
];

export function BacktestList() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const statusParam = searchParams.get("status") ?? "all";
  const orderByParam = searchParams.get("order_by");
  const orderParam = searchParams.get("order");
  const activeStatus: "all" | BacktestStatus = STATUS_FILTERS.some((f) => f.id === statusParam)
    ? (statusParam as "all" | BacktestStatus)
    : "all";
  const { order_by: orderBy, order } = resolveBacktestSort(orderByParam, orderParam);

  // BE 가 status 필터를 list endpoint 에서 지원하지 않으므로 client-side filter (현재 페이지 한정).
  // sort 축·방향은 URL 스칼라에만 의존해 queryKey 와 서버 정렬을 동기화한다(H-1/H-2 정합).
  // ★queryKey 는 페이지(Server Component)의 prefetch 키와 **같은 생성자**로 만든다 — 두 곳에서
  //   각자 조립하던 것이 [BL-786] 의 중복 요청 절반이었다.
  const query = useMemo(
    () => buildBacktestListQuery(orderByParam, orderParam),
    [orderByParam, orderParam],
  );
  const { data, isLoading, isError, error, refetch } = useBacktests(query);
  const strategiesQ = useStrategies({
    limit: STRATEGY_FETCH_LIMIT,
    offset: 0,
    is_archived: false,
  });

  // useMemo dep 안정성을 위해 items reference 자체를 memoize (H-1 정합 — RQ data 를 직접 dep 금지).
  const items = useMemo<readonly BacktestSummary[]>(() => data?.items ?? [], [data?.items]);
  const strategyItems = useMemo(() => strategiesQ.data?.items ?? [], [strategiesQ.data?.items]);
  const strategyNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const strategy of strategyItems) map.set(strategy.id, strategy.name);
    return map;
  }, [strategyItems]);
  // Sprint 41-B2 (codex review P2): client-side status 필터는 현재 페이지(limit 20)에만 적용 가능.
  // total > items.length 면 후속 페이지의 매칭이 누락 → chip(전체 제외) 비활성 + 안내 문구 표시.
  const total = data?.total ?? 0;
  const hasMorePages = total > items.length;
  const filtered = activeStatus === "all" ? items : items.filter((b) => b.status === activeStatus);
  const counts = useMemo(() => buildStatusCounts(items), [items]);
  const hasMixedSharpeConventions =
    orderBy === "sharpe_ratio" &&
    filtered.some(
      (b) => b.metrics_summary?.sharpe_ratio != null && b.metrics_summary.sharpe_convention == null,
    ) &&
    filtered.some(
      (b) => b.metrics_summary?.sharpe_ratio != null && b.metrics_summary.sharpe_convention != null,
    );

  const pushStatus = (id: "all" | BacktestStatus) => {
    const params = new URLSearchParams(searchParams.toString());
    if (id === "all") params.delete("status");
    else params.set("status", id);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname);
  };

  const pushSort = (nextOrderBy: BacktestOrderBy) => {
    const params = new URLSearchParams(searchParams.toString());
    const nextOrder: BacktestOrder = nextOrderBy === orderBy && order === "desc" ? "asc" : "desc";
    params.set("order_by", nextOrderBy);
    params.set("order", nextOrder);
    router.replace(`${pathname}?${params.toString()}`);
  };

  // 헤더 라벨은 스칼라로 푼다. BACKTEST_LIST_HEADER.status 는 enum 값이 아닌 헤더 문자열이지만,
  // no-raw-enum-labels 가드가 `.status`/`.state` 로 끝나는 JSX 멤버 체인을 전부 잡으므로 우회한다.
  const {
    runId: hRunId,
    strategy: hStrategy,
    symbolTimeframe: hSymbolTf,
    period: hPeriod,
    totalReturn: hTotalReturn,
    maxDrawdown: hMaxDrawdown,
    sharpeRatio: hSharpeRatio,
    numTrades: hNumTrades,
    status: hStatus,
    startedAt: hStartedAt,
    action: hAction,
  } = BACKTEST_LIST_HEADER;

  return (
    <main className="page">
      {/* ===== 목록 헤더 카드 ===== */}
      <section className="card" aria-label="백테스트 목록 개요">
        <div className="report">
          <div>
            <h1 className="report-title">백테스트</h1>
            <div className="report-meta">
              <span className="chip">실행 {total}건</span>
              <span className="chip">Bybit</span>
              <span className="chip accent">바 단위 이벤트 루프</span>
            </div>
          </div>
          <div className="report-actions">
            <button className="btn" type="button" onClick={() => refetch()}>
              <RefreshCwIcon aria-hidden="true" />
              목록 새로고침
            </button>
            <Link className="btn btn-primary" href="/backtests/new">
              <PlusIcon aria-hidden="true" />
              {NEW_BACKTEST_LABEL.entry}
            </Link>
          </div>
        </div>
      </section>

      {/* ===== 01 목록 ===== */}
      <section className="section" aria-label="실행 목록">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">01</span> 목록
          </p>
          <h2 className="section-title">실행 {total}건</h2>
          <p className="section-desc">
            최근에 실행한 순서로 정렬했습니다. 심볼과 주기는 전략의 기본값이 아니라 그 실행에 실제로
            쓴 값입니다.
          </p>
        </header>

        <div className="card">
          <div className="card-head">
            <div>
              <h3 className="card-title">실행 목록</h3>
              <p className="card-sub">
                {items.length}건 표시{hasMorePages ? ` · 전체 ${total}건 중` : ""}
              </p>
            </div>
            <div className="chart-head-actions">
              <fieldset className="tabs m-0 min-w-0 border-0 p-0" aria-label="상태 필터">
                {STATUS_FILTERS.map((f) => {
                  const active = f.id === activeStatus;
                  const isDisabled = hasMorePages && f.id !== "all";
                  return (
                    <button
                      key={f.id}
                      type="button"
                      className={`tab${active ? " active" : ""}`}
                      aria-pressed={active}
                      aria-disabled={isDisabled || undefined}
                      disabled={isDisabled}
                      title={
                        isDisabled
                          ? "현재 페이지(20건)만 필터되므로 비활성화됩니다. Beta 에 서버 필터 추가 예정"
                          : undefined
                      }
                      data-testid={`backtest-filter-${f.id}`}
                      onClick={() => {
                        if (isDisabled) return;
                        pushStatus(f.id);
                      }}
                    >
                      {BACKTEST_STATUS_FILTER_LABEL[f.id]}
                    </button>
                  );
                })}
              </fieldset>
            </div>
          </div>

          {/* total 은 BE 전역 건수지만 상태 분해는 client-side counts 라 현재 페이지(≤20)만
              반영한다. 페이지가 더 있으면 '이 페이지 기준' 을 붙여 전역 집계로 오인하지 않게
              한다. 대기(queued)는 실행 중(running)에 합치지 않고, 취소(cancelled)도 함께 센다. */}
          <p className="runs-summary">
            <span className="mono">{total}</span>건 · {hasMorePages ? "이 페이지 기준 " : ""}완료{" "}
            <span className="mono">{counts.completed}</span> · 실행 중{" "}
            <span className="mono">{counts.running}</span> · 대기{" "}
            <span className="mono">{counts.queued}</span> · 실패{" "}
            <span className="mono">{counts.failed}</span> · 취소{" "}
            <span className="mono">{counts.cancelled}</span>
          </p>
          {hasMorePages ? (
            <p className="runs-summary" data-testid="backtest-filter-notice">
              현재 페이지(20건)만 필터됩니다. Beta 에 서버 필터가 추가될 예정입니다.
            </p>
          ) : null}

          {isLoading ? (
            <ListSkeleton />
          ) : isError ? (
            <div className="card-body">
              <StateBox
                tone="failed"
                testId="backtest-error"
                icon={<AlertTriangleIcon />}
                title="목록을 불러오지 못했습니다."
                body={error ? error.message : "네트워크 또는 서버 상태 일시적 오류일 수 있습니다."}
                code={LIST_ENDPOINT}
              >
                <button className="btn btn-ghost" type="button" onClick={() => refetch()}>
                  <RefreshCwIcon aria-hidden="true" />
                  다시 시도
                </button>
              </StateBox>
            </div>
          ) : filtered.length === 0 ? (
            <div className="card-body">
              <StateBox
                testId="backtest-empty"
                icon={<InboxIcon />}
                title={
                  items.length === 0
                    ? "첫 백테스트를 시작하세요"
                    : "해당 상태의 백테스트가 없습니다"
                }
                body={
                  items.length === 0
                    ? "전략을 선택하고 기간을 설정하면 결과를 받을 수 있습니다."
                    : "다른 상태를 선택하거나 새 백테스트를 실행하세요."
                }
              >
                {items.length === 0 ? (
                  <Link className="btn btn-primary btn-xs" href="/backtests/new">
                    첫 백테스트 실행
                  </Link>
                ) : (
                  <button
                    className="btn btn-ghost btn-xs"
                    type="button"
                    onClick={() => pushStatus("all")}
                  >
                    전체 보기
                  </button>
                )}
              </StateBox>
            </div>
          ) : (
            <>
              <div className="table-wrap">
                <table
                  className="trades runs-table"
                  aria-label={`백테스트 실행 목록 ${filtered.length}건`}
                >
                  <thead>
                    <tr>
                      <th scope="col">{hRunId}</th>
                      <th scope="col">{hStrategy}</th>
                      <th scope="col">{hSymbolTf}</th>
                      <th scope="col">{hPeriod}</th>
                      <SortHeader
                        orderBy="total_return"
                        label={hTotalReturn}
                        ariaLabel={BACKTEST_LIST_SORT_LABEL.totalReturn}
                        activeOrderBy={orderBy}
                        order={order}
                        onClick={pushSort}
                      />
                      <SortHeader
                        orderBy="max_drawdown"
                        label={hMaxDrawdown}
                        ariaLabel={BACKTEST_LIST_SORT_LABEL.maxDrawdown}
                        activeOrderBy={orderBy}
                        order={order}
                        onClick={pushSort}
                      />
                      <SortHeader
                        orderBy="sharpe_ratio"
                        label={hSharpeRatio}
                        ariaLabel={BACKTEST_LIST_SORT_LABEL.sharpeRatio}
                        activeOrderBy={orderBy}
                        order={order}
                        onClick={pushSort}
                      />
                      <SortHeader
                        orderBy="num_trades"
                        label={hNumTrades}
                        ariaLabel={BACKTEST_LIST_SORT_LABEL.numTrades}
                        activeOrderBy={orderBy}
                        order={order}
                        onClick={pushSort}
                      />
                      <th scope="col" className="col-status">
                        {hStatus}
                      </th>
                      <SortHeader
                        orderBy="created_at"
                        label={hStartedAt}
                        ariaLabel={BACKTEST_LIST_SORT_LABEL.startedAt}
                        activeOrderBy={orderBy}
                        order={order}
                        onClick={pushSort}
                      />
                      <th scope="col">{hAction}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((b) => {
                      // 라벨·톤은 S4 용어 SSOT 에서만 온다 (원시 enum 렌더 금지 — no-raw-enum-labels 가드).
                      const { label, tone, showCheckIcon } = BACKTEST_STATUS_LABEL[b.status];
                      const sharpe = describeSharpe(
                        b.metrics_summary?.sharpe_convention,
                        b.metrics_summary?.sharpe_ratio,
                      );
                      return (
                        <tr key={b.id} data-testid={`backtest-row-${b.id}`} data-status={b.status}>
                          <td className="mono-l run-id">
                            <Link href={`/backtests/${b.id}`}>{b.id.slice(0, 8)}</Link>
                          </td>
                          <td>{strategyNameById.get(b.strategy_id) ?? EMPTY_CELL}</td>
                          <td className="mono-l">
                            {b.symbol} · {b.timeframe}
                          </td>
                          <td className="mono-l">
                            {formatDateTime(b.period_start)}
                            <span className="run-sub">~ {formatDateTime(b.period_end)}</span>
                          </td>
                          <MetricCell
                            value={b.metrics_summary?.[RETURN_METRIC]}
                            missing={b.metrics_summary == null}
                            format={(value) => formatPercent(value)}
                            note={b.metrics_summary?.total_open_trades}
                          />
                          <MetricCell
                            value={b.metrics_summary?.max_drawdown}
                            missing={b.metrics_summary == null}
                            format={(value) => formatPercent(value)}
                          />
                          <td
                            className="num"
                            title={
                              b.metrics_summary == null ? UNFINISHED_METRICS_TITLE : sharpe.foot
                            }
                          >
                            {b.metrics_summary == null ? EMPTY_CELL : sharpe.display}
                          </td>
                          <MetricCell
                            value={b.metrics_summary?.num_trades}
                            missing={b.metrics_summary == null}
                            format={(value) => value.toLocaleString("en-US")}
                          />
                          <td className="col-status">
                            <span className={CHIP_TONE_CLASS[tone]}>
                              {showCheckIcon ? <CheckIcon aria-hidden="true" /> : null}
                              {label}
                            </span>
                          </td>
                          <td className="mono-l dim">{formatDateTime(b.created_at)}</td>
                          <td>
                            <Link className="btn btn-ghost btn-xs" href={`/backtests/${b.id}`}>
                              상세
                            </Link>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {hasMixedSharpeConventions ? (
                <p className="runs-summary" data-testid="backtest-sharpe-sort-notice">
                  구 기준 샤프는 현재 기준과 비교할 수 없어 정렬 시 비교 가능한 결과 뒤로
                  분리됩니다.
                </p>
              ) : null}
            </>
          )}
        </div>
      </section>
    </main>
  );
}

function SortHeader({
  orderBy,
  label,
  ariaLabel,
  activeOrderBy,
  order,
  onClick,
}: {
  orderBy: BacktestOrderBy;
  label: string;
  ariaLabel: string;
  activeOrderBy: BacktestOrderBy;
  order: BacktestOrder;
  onClick: (orderBy: BacktestOrderBy) => void;
}) {
  const active = orderBy === activeOrderBy;
  return (
    <th
      scope="col"
      className="num"
      aria-sort={active ? (order === "asc" ? "ascending" : "descending") : undefined}
    >
      <button
        className="th-sort"
        type="button"
        aria-label={ariaLabel}
        onClick={() => onClick(orderBy)}
      >
        {label}
        <ArrowDownUpIcon aria-hidden="true" />
      </button>
    </th>
  );
}

function MetricCell({
  value,
  missing,
  format,
  note,
}: {
  value: number | null | undefined;
  missing: boolean;
  format: (value: number) => string;
  note?: number | null;
}) {
  if (value == null) {
    return (
      <td className="num" title={missing ? UNFINISHED_METRICS_TITLE : undefined}>
        {EMPTY_CELL}
      </td>
    );
  }
  return (
    <td className="num">
      {format(value)}
      {note != null && note > 0 ? <span className="run-sub">미청산 포함</span> : null}
    </td>
  );
}

function buildStatusCounts(items: readonly BacktestSummary[]) {
  const result = { completed: 0, running: 0, queued: 0, failed: 0, cancelled: 0 };
  for (const b of items) {
    switch (b.status) {
      case "completed":
        result.completed += 1;
        break;
      case "running":
      case "cancelling":
        result.running += 1;
        break;
      case "queued":
        result.queued += 1;
        break;
      case "failed":
        result.failed += 1;
        break;
      case "cancelled":
        result.cancelled += 1;
        break;
    }
  }
  return result;
}

// 다음 페이지를 불러오는 동안의 스켈레톤 — 프로토타입 aria-busy tbody 관례 (.sk .sk-cell).
function ListSkeleton() {
  return (
    <div className="table-wrap" data-testid="backtest-skeleton" aria-hidden="true">
      <table className="trades runs-table">
        <tbody>
          {LIST_SKELETON_ROWS.map((rowKey) => (
            <tr key={rowKey}>
              {LIST_SKELETON_CELLS.map((cellKey) => (
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
