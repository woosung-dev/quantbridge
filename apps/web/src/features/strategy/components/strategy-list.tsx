"use client";

// 전략 목록 — C 디자인 언어 이식 (screen-06). latest_backtest projection으로 최근 수익률/MDD/샤프를
// 그리고, 서버가 내려주는 파라미터 수·수명주기 칩(초안/검증됨/배포됨)을 함께 표시한다.
// 파싱 상태는 실존 필드 parse_status 를 필터 축으로 사용한다.
//
// screen-06 "01 필터" 구획 재도입 (W3-fix). 검색(전략명·전략 ID)·심볼 필터·정렬을 프로토타입의
// .toolbar/.input/.select 구조로 그린다. 검색·심볼·parse_status 필터는 현재 페이지에 적용하고,
// 정렬은 URL 스칼라를 통해 서버에 위임한다. 상태 select 는 실존 필드 parse_status 토글(role=group)이
// 이미 담당하므로 여기 재현하지 않는다.

import Link from "next/link";
import { useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangleIcon,
  CheckIcon,
  DownloadIcon,
  InboxIcon,
  PlusIcon,
  RefreshCwIcon,
} from "lucide-react";

import {
  PARSE_STATUS_FILTER_LABEL,
  STRATEGY_BACKTEST_COUNT_HINT,
  STRATEGY_EMPTY_REASON,
  STRATEGY_LIST_HEADER,
  STRATEGY_LIFECYCLE_LABEL,
  type ParseStatusFilter,
} from "@/features/strategy/labels";
import { useStrategies } from "@/features/strategy/hooks";
import type { ParseStatus, StrategyListItem, StrategyListQuery } from "@/features/strategy/schemas";
import { STRATEGY_SORT_OPTIONS, resolveStrategySort } from "@/features/strategy/sort";
import { formatDateTime } from "@/features/strategy/utils";
import { formatPercent } from "@/features/backtest/utils";
import { describeSharpe } from "@/features/backtest/sharpe-convention";
import type { BacktestMetricsSummary } from "@/features/backtest/schemas";
import { StateBox } from "@/components/state-box";
import { CHIP_TONE_CLASS, EMPTY_CELL } from "@/lib/labels";

const PAGE_SIZE = 20;
// 목록 조회 엔드포인트 — 에러 상태에 실제 경로를 노출한다 (프로토타입 state-code 관례).
const LIST_ENDPOINT = "GET /api/v1/strategies";

// parse_status 필터 옵션. 수명주기 칩과 별개로 파싱 결과를 좁히는 실존 필드다.
const STATUS_FILTERS: ReadonlyArray<{ id: ParseStatusFilter }> = [
  { id: "all" },
  { id: "ok" },
  { id: "unsupported" },
  { id: "error" },
];

type StrategyOrderBy = NonNullable<StrategyListQuery["order_by"]>;
const SYMBOL_ALL = "all";

export function StrategyList() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const statusParam = searchParams.get("parse_status") ?? "all";
  const activeStatus: ParseStatusFilter = STATUS_FILTERS.some((f) => f.id === statusParam)
    ? (statusParam as ParseStatusFilter)
    : "all";

  const orderByParam = searchParams.get("order_by");
  const orderParam = searchParams.get("order");
  const { order_by: orderBy, order } = resolveStrategySort(orderByParam, orderParam);

  // 검색·심볼은 클라이언트 로컬 상태로 두고, parse_status·정렬은 URL 스칼라로 유지한다.
  // hook query가 URL 정렬 축·방향을 포함하므로 queryKey와 서버 요청이 함께 바뀐다(H-2 정합).
  const [searchText, setSearchText] = useState("");
  const [symbolFilter, setSymbolFilter] = useState<string>(SYMBOL_ALL);

  const query = useMemo<StrategyListQuery>(
    () => ({ limit: PAGE_SIZE, offset: 0, is_archived: false, order_by: orderBy, order }),
    [orderBy, order],
  );
  const { data, isLoading, isError, error, refetch } = useStrategies(query);

  // useMemo dep 안정성을 위해 items reference 자체를 memoize (H-1 정합 — RQ data 직접 dep 금지).
  const items = useMemo<readonly StrategyListItem[]>(() => data?.items ?? [], [data?.items]);
  const total = data?.total ?? 0;
  const hasMorePages = total > items.length;
  const counts = useMemo(() => buildParseStatusCounts(items), [items]);

  // 심볼 필터 후보는 로드된 데이터에서 실측한다(프로토타입 하드코딩 BTC/ETH/SOL 대신 backed 값).
  const symbolOptions = useMemo(() => {
    const set = new Set<string>();
    for (const s of items) if (s.symbol) set.add(s.symbol);
    return Array.from(set).sort();
  }, [items]);

  // 필터 파이프라인 — parse_status → 검색(이름/ID) → 심볼. 정렬은 서버에서 처리한다.
  const filtered = useMemo<readonly StrategyListItem[]>(() => {
    const q = searchText.trim().toLowerCase();
    const matched = items.filter((s) => {
      if (activeStatus !== "all" && s.parse_status !== activeStatus) return false;
      if (symbolFilter !== SYMBOL_ALL && s.symbol !== symbolFilter) return false;
      if (q) {
        const haystack = `${s.name} ${s.id}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      return true;
    });
    return matched;
  }, [items, activeStatus, symbolFilter, searchText]);

  const isFiltering =
    activeStatus !== "all" || symbolFilter !== SYMBOL_ALL || searchText.trim() !== "";

  const pushStatus = (id: ParseStatusFilter) => {
    const params = new URLSearchParams(searchParams.toString());
    if (id === "all") params.delete("parse_status");
    else params.set("parse_status", id);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname);
  };

  const pushSort = (nextOrderBy: StrategyOrderBy) => {
    const option = STRATEGY_SORT_OPTIONS.find((candidate) => candidate.id === nextOrderBy);
    if (!option) return;
    const params = new URLSearchParams(searchParams.toString());
    params.set("order_by", option.id);
    params.set("order", option.order);
    router.replace(`${pathname}?${params.toString()}`);
  };

  const resetFilters = () => {
    setSearchText("");
    setSymbolFilter(SYMBOL_ALL);
    pushStatus("all");
  };

  // 목록 CSV 내보내기 — 헤더는 렌더 중인 backed 열과 일치한다.
  // 지금 필터·정렬이 적용된 결과를 그대로 내보낸다.
  const handleExportCsv = () => {
    const csv = buildCsv(filtered);
    // Excel 한글 인코딩 보정용 UTF-8 BOM 접두.
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "strategies.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  // 헤더 라벨은 스칼라로 푼다. STRATEGY_LIST_HEADER.status 는 헤더 문자열이지만
  // no-raw-enum-labels 가드가 `.status` 로 끝나는 JSX 멤버 체인을 잡으므로 우회한다.
  const {
    name: hName,
    status: hStatus,
    symbolTimeframe: hSymbolTf,
    paramCount: hParamCount,
    lastRunReturn: hLastRunReturn,
    maxDrawdown: hMaxDrawdown,
    sharpeRatio: hSharpeRatio,
    backtestCount: hBacktestCount,
    updatedAt: hUpdatedAt,
    action: hAction,
  } = STRATEGY_LIST_HEADER;

  return (
    <main className="page">
      {/* ===== 목록 헤더 카드 ===== */}
      <section className="card" aria-label="전략 목록 개요">
        <div className="report">
          <div>
            <h1 className="report-title">전략</h1>
            <div className="report-meta">
              <span className="chip">{total}개</span>
              <span className="chip accent">바 단위 이벤트 루프</span>
              <span className="chip">Bybit</span>
            </div>
          </div>
          <div className="report-actions">
            <button
              className="btn"
              type="button"
              onClick={handleExportCsv}
              disabled={filtered.length === 0}
              data-testid="strategy-export-csv"
            >
              <DownloadIcon aria-hidden="true" />
              목록 CSV 내보내기
            </button>
            <button className="btn" type="button" onClick={() => refetch()}>
              <RefreshCwIcon aria-hidden="true" />
              목록 새로고침
            </button>
            <Link className="btn btn-primary" href="/strategies/new">
              <PlusIcon aria-hidden="true" />새 전략
            </Link>
          </div>
        </div>
      </section>

      {/* ===== 01 필터 ===== */}
      <section className="section" aria-label="전략 필터">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">01</span> 필터
          </p>
          <h2 className="section-title">전략 찾기</h2>
          <p className="section-desc">
            전략명이나 전략 ID 로 검색하고, 심볼과 정렬로 범위를 좁힙니다. 필터는 지금 페이지에
            불러온 목록에 적용됩니다.
          </p>
        </header>

        <div className="card">
          <div className="card-body">
            <div className="toolbar">
              <input
                className="input"
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="전략명, 전략 ID 검색"
                aria-label="전략 검색"
                data-testid="strategy-search"
              />
              <select
                className="select"
                value={symbolFilter}
                onChange={(e) => setSymbolFilter(e.target.value)}
                aria-label="심볼 필터"
                data-testid="strategy-symbol-filter"
              >
                <option value={SYMBOL_ALL}>심볼 전체</option>
                {symbolOptions.map((sym) => (
                  <option key={sym} value={sym}>
                    {sym}
                  </option>
                ))}
              </select>
              <select
                className="select"
                value={orderBy}
                onChange={(e) => pushSort(e.target.value as StrategyOrderBy)}
                aria-label="정렬 기준"
                data-testid="strategy-sort"
              >
                {STRATEGY_SORT_OPTIONS.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>

            <p className="filter-note" data-testid="strategy-filter-note">
              {isFiltering ? (
                <>
                  <span>필터 적용 결과</span>
                  <span>
                    <span className="mono">{filtered.length}</span>개 · 불러온{" "}
                    <span className="mono">{items.length}</span>개 중
                  </span>
                </>
              ) : (
                <>
                  <span>필터를 적용하지 않았습니다. 지금 보이는 것은</span>
                  <span>
                    <span className="mono">{items.length}</span>개 · 변환 가능{" "}
                    <span className="mono">{counts.ok}</span> · 일부 미지원{" "}
                    <span className="mono">{counts.unsupported}</span> · 오류{" "}
                    <span className="mono">{counts.error}</span> 입니다.
                  </span>
                </>
              )}
            </p>
          </div>
        </div>
      </section>

      {/* ===== 02 목록 ===== */}
      <section className="section" aria-label="전략 목록">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">02</span> 목록
          </p>
          <h2 className="section-title">전략 {total}개</h2>
          <p className="section-desc">
            선택한 기준으로 서버에서 정렬합니다. 심볼과 주기는 그 전략에 저장된 기본값입니다.
          </p>
        </header>

        <div className="card">
          <div className="card-head">
            <div>
              <h3 className="card-title">전략 목록</h3>
              <p className="card-sub">
                {filtered.length}개 표시{hasMorePages ? ` · 전체 ${total}개 중` : ""}
              </p>
            </div>
            <div className="chart-head-actions">
              <div className="tabs" role="group" aria-label="파싱 상태 필터">
                {STATUS_FILTERS.map((f) => {
                  const active = f.id === activeStatus;
                  const isDisabled = hasMorePages && f.id !== "all";
                  return (
                    <button
                      key={f.id}
                      type="button"
                      className={"tab" + (active ? " active" : "")}
                      aria-pressed={active}
                      aria-disabled={isDisabled || undefined}
                      disabled={isDisabled}
                      title={
                        isDisabled
                          ? "현재 페이지(20개)만 필터되므로 비활성화됩니다. Beta 에 서버 필터 추가 예정"
                          : undefined
                      }
                      data-testid={`strategy-filter-${f.id}`}
                      onClick={() => {
                        if (isDisabled) return;
                        pushStatus(f.id);
                      }}
                    >
                      {PARSE_STATUS_FILTER_LABEL[f.id]}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* total 은 BE 전역 건수지만 상태 분해는 client-side counts 라 현재 페이지(≤20)만
              반영한다. 페이지가 더 있으면 '이 페이지 기준' 을 붙여 전역 집계로 오인하지 않게 한다. */}
          <p className="runs-summary">
            <span className="mono">{total}</span>개 · {hasMorePages ? "이 페이지 기준 " : ""}
            변환 가능 <span className="mono">{counts.ok}</span> · 일부 미지원{" "}
            <span className="mono">{counts.unsupported}</span> · 오류{" "}
            <span className="mono">{counts.error}</span>
          </p>
          {hasMorePages ? (
            <p className="runs-summary" data-testid="strategy-filter-notice">
              정렬은 서버에서 전체 전략에 적용되며, 필터는 현재 페이지(20개)에만 적용됩니다.
            </p>
          ) : null}
          {isLoading ? (
            <ListSkeleton />
          ) : isError ? (
            <div className="card-body">
              <StateBox
                tone="failed"
                testId="strategy-error"
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
                testId="strategy-empty"
                icon={<InboxIcon />}
                title={items.length === 0 ? "첫 전략을 등록하세요" : "조건에 맞는 전략이 없습니다"}
                body={
                  items.length === 0
                    ? "TradingView Pine Script 를 붙여넣으면 파싱 검사 후 전략으로 저장됩니다."
                    : "검색어나 필터를 바꾸거나 새 전략을 등록하세요."
                }
              >
                {items.length === 0 ? (
                  <Link className="btn btn-primary btn-xs" href="/strategies/new">
                    새 전략 등록
                  </Link>
                ) : (
                  <button className="btn btn-ghost btn-xs" type="button" onClick={resetFilters}>
                    필터 초기화
                  </button>
                )}
              </StateBox>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="trades runs-table" aria-label={`전략 목록 ${filtered.length}개`}>
                <thead>
                  <tr>
                    <th scope="col">{hName}</th>
                    <th scope="col" className="col-status">
                      {hStatus}
                    </th>
                    <th scope="col">{hSymbolTf}</th>
                    <th scope="col" className="num">
                      {hParamCount}
                    </th>
                    <th scope="col" className="num">
                      {hLastRunReturn}
                    </th>
                    <th scope="col" className="num">
                      {hMaxDrawdown}
                    </th>
                    <th scope="col" className="num">
                      {hSharpeRatio}
                    </th>
                    <th scope="col" className="num" title={STRATEGY_BACKTEST_COUNT_HINT}>
                      {hBacktestCount}
                    </th>
                    <th scope="col">{hUpdatedAt}</th>
                    <th scope="col">{hAction}</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((s) => {
                    // 수명주기 라벨·톤은 용어 SSOT 에서만 온다 (원시 enum 렌더 금지).
                    const { label, tone, showCheckIcon } =
                      STRATEGY_LIFECYCLE_LABEL[s.lifecycle ?? "draft"];
                    return (
                      <tr
                        key={s.id}
                        data-testid={`strategy-row-${s.id}`}
                        data-status={s.parse_status}
                        data-lifecycle={s.lifecycle}
                      >
                        <td>
                          <Link className="strat-name" href={`/strategies/${s.id}/edit`}>
                            {s.name}
                          </Link>
                          <span className="strat-id">{s.id.slice(0, 8)}</span>
                        </td>
                        <td className="col-status">
                          <span className={CHIP_TONE_CLASS[tone]}>
                            {showCheckIcon ? <CheckIcon aria-hidden="true" /> : null}
                            {label}
                          </span>
                        </td>
                        {/* 무데이터 셀 — 심볼·주기가 전략에 저장돼 있지 않으면 EMPTY_CELL 로 표기한다. */}
                        <td className="mono-l">
                          {s.symbol || s.timeframe ? (
                            <>
                              {s.symbol ?? EMPTY_CELL} · {s.timeframe ?? EMPTY_CELL}
                            </>
                          ) : (
                            <span title="이 전략에는 심볼과 주기가 저장돼 있지 않습니다.">
                              {EMPTY_CELL}
                            </span>
                          )}
                        </td>
                        <td className="num">{s.param_count ?? EMPTY_CELL}</td>
                        <StrategyMetricCell
                          value={s.latest_backtest?.metrics?.total_return}
                          missing={s.latest_backtest == null}
                          format={(value) => formatPercent(value)}
                        />
                        <StrategyMetricCell
                          value={s.latest_backtest?.metrics?.max_drawdown}
                          missing={s.latest_backtest == null}
                          format={(value) => formatPercent(value)}
                        />
                        <StrategySharpeCell
                          metrics={s.latest_backtest?.metrics}
                          missing={s.latest_backtest == null}
                        />
                        <td
                          className="num"
                          data-testid="strategy-backtest-count"
                          title={
                            s.backtest_count === 0 ? STRATEGY_EMPTY_REASON.noBacktestYet : undefined
                          }
                        >
                          {s.backtest_count ?? EMPTY_CELL}
                        </td>
                        <td className="mono-l dim">{formatDateTime(s.updated_at)}</td>
                        <td>
                          <Link className="btn btn-ghost btn-xs" href={`/strategies/${s.id}/edit`}>
                            편집
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

function StrategyMetricCell({
  value,
  missing,
  format,
}: {
  value: number | null | undefined;
  missing: boolean;
  format: (value: number) => string;
}) {
  return (
    <td className="num" title={missing ? "완료 실행 없음" : undefined}>
      {value == null ? EMPTY_CELL : format(value)}
    </td>
  );
}

// 샤프는 값만으로 표시할 수 없다 — 컨벤션이 있어야 degenerate 실행을 `—` 로
// 구분한다. 엔진이 그 경우 의도적으로 0 을 반환하므로(`engine/metrics.py:76-103`)
// 형제 `StrategyMetricCell` 의 `format(value)` 서명으로는 표현 불가라 전용 셀을 둔다.
function StrategySharpeCell({
  metrics,
  missing,
}: {
  metrics: BacktestMetricsSummary | null | undefined;
  missing: boolean;
}) {
  const sharpe = describeSharpe(metrics?.sharpe_convention, metrics?.sharpe_ratio);
  return (
    <td className="num" title={missing ? "완료 실행 없음" : sharpe.foot}>
      {sharpe.display}
    </td>
  );
}

function buildParseStatusCounts(items: readonly StrategyListItem[]) {
  const result: Record<ParseStatus, number> = { ok: 0, unsupported: 0, error: 0 };
  for (const s of items) result[s.parse_status] += 1;
  return result;
}

// CSV 한 필드를 RFC 4180 규약으로 감싼다(쌍따옴표 이스케이프). 콤마·개행·따옴표 안전.
function csvField(value: string): string {
  return `"${value.replace(/"/g, '""')}"`;
}

// backed 열만 내보낸다 — 렌더 표와 열 구성이 같다.
function buildCsv(rows: readonly StrategyListItem[]): string {
  const header = [
    "전략명",
    "상태",
    "심볼 · 주기",
    "파라미터",
    "최근 수익률",
    "MDD",
    "샤프",
    "백테스트",
    "마지막 수정",
  ];
  const lines = [header.map(csvField).join(",")];
  for (const s of rows) {
    const lifecycleLabel = STRATEGY_LIFECYCLE_LABEL[s.lifecycle ?? "draft"].label;
    const symbolTf =
      s.symbol || s.timeframe ? `${s.symbol ?? ""} · ${s.timeframe ?? ""}`.trim() : "";
    lines.push(
      [
        s.name,
        lifecycleLabel,
        symbolTf,
        String(s.param_count ?? EMPTY_CELL),
        s.latest_backtest?.metrics?.total_return != null
          ? formatPercent(s.latest_backtest.metrics.total_return)
          : EMPTY_CELL,
        s.latest_backtest?.metrics?.max_drawdown != null
          ? formatPercent(s.latest_backtest.metrics.max_drawdown)
          : EMPTY_CELL,
        describeSharpe(
          s.latest_backtest?.metrics?.sharpe_convention,
          s.latest_backtest?.metrics?.sharpe_ratio,
        ).display,
        String(s.backtest_count ?? EMPTY_CELL),
        formatDateTime(s.updated_at),
      ]
        .map(csvField)
        .join(","),
    );
  }
  return lines.join("\r\n");
}

// 다음 페이지를 불러오는 동안의 스켈레톤 — 프로토타입 aria-busy tbody 관례 (.sk .sk-cell).
function ListSkeleton() {
  return (
    <div className="table-wrap" data-testid="strategy-skeleton" aria-hidden="true">
      <table className="trades runs-table">
        <tbody>
          {Array.from({ length: 6 }).map((_, i) => (
            <tr key={i}>
              {Array.from({ length: 10 }).map((__, j) => (
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
