"use client";

// 백테스트 목록 — C 디자인 언어 이식 (S5). 프로토타입 screen-03 의 시맨틱 CSS 를 소비하되,
// 열은 실데이터(BacktestSummary)가 받치는 것만 그린다. 목업의 수익률/MDD/샤프/거래수/전략명은
// list 스키마에 없어 렌더하지 않는다 (캐논 §4.9 "데이터 모델에 없는 값 = 가짜 데이터").
// 상태 라벨·톤은 S4 용어 SSOT(BACKTEST_STATUS_LABEL) → CHIP_TONE_CLASS 로 파생한다.

import Link from "next/link";
import { useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AlertTriangleIcon, CheckIcon, InboxIcon, PlusIcon, RefreshCwIcon } from "lucide-react";

import {
  BACKTEST_LIST_HEADER,
  BACKTEST_STATUS_FILTER_LABEL,
  BACKTEST_STATUS_LABEL,
  NEW_BACKTEST_LABEL,
} from "@/features/backtest/labels";
import { useBacktests } from "@/features/backtest/hooks";
import type { BacktestStatus, BacktestSummary } from "@/features/backtest/schemas";
import { formatDateTime } from "@/features/backtest/utils";
import { CHIP_TONE_CLASS, EMPTY_CELL } from "@/lib/labels";

const PAGE_SIZE = 20;
// 목록 조회 엔드포인트 — 에러 상태에 실제 경로를 노출한다 (프로토타입 state-code 관례).
const LIST_ENDPOINT = "GET /api/v1/backtests";

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
  const activeStatus: "all" | BacktestStatus = STATUS_FILTERS.some((f) => f.id === statusParam)
    ? (statusParam as "all" | BacktestStatus)
    : "all";

  // BE 가 status 필터를 list endpoint 에서 지원하지 않으므로 client-side filter (현재 페이지 한정).
  // hook query 는 페이지네이션만 → queryKey identity 유지 (H-2 정합).
  const query = useMemo(() => ({ limit: PAGE_SIZE, offset: 0 }), []);
  const { data, isLoading, isError, error, refetch } = useBacktests(query);

  // useMemo dep 안정성을 위해 items reference 자체를 memoize (H-1 정합 — RQ data 를 직접 dep 금지).
  const items = useMemo<readonly BacktestSummary[]>(() => data?.items ?? [], [data?.items]);
  // Sprint 41-B2 (codex review P2): client-side status 필터는 현재 페이지(limit 20)에만 적용 가능.
  // total > items.length 면 후속 페이지의 매칭이 누락 → chip(전체 제외) 비활성 + 안내 문구 표시.
  const total = data?.total ?? 0;
  const hasMorePages = total > items.length;
  const filtered = activeStatus === "all" ? items : items.filter((b) => b.status === activeStatus);
  const counts = useMemo(() => buildStatusCounts(items), [items]);

  const pushStatus = (id: "all" | BacktestStatus) => {
    const params = new URLSearchParams(searchParams.toString());
    if (id === "all") params.delete("status");
    else params.set("status", id);
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname);
  };

  // 헤더 라벨은 스칼라로 푼다. BACKTEST_LIST_HEADER.status 는 enum 값이 아닌 헤더 문자열이지만,
  // no-raw-enum-labels 가드가 `.status`/`.state` 로 끝나는 JSX 멤버 체인을 전부 잡으므로 우회한다.
  const {
    runId: hRunId,
    symbolTimeframe: hSymbolTf,
    period: hPeriod,
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
            최근에 실행한 순서로 정렬했습니다. 심볼과 주기는 전략의 기본값이 아니라 그 실행에 실제로 쓴
            값입니다.
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
              <div className="tabs" role="group" aria-label="상태 필터">
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
              </div>
            </div>
          </div>

          <p className="runs-summary">
            <span className="mono">{total}</span>건 · 완료{" "}
            <span className="mono">{counts.completed}</span> · 실행 중{" "}
            <span className="mono">{counts.running + counts.queued}</span> · 실패{" "}
            <span className="mono">{counts.failed}</span>
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
              <div className="state-box failed" role="alert" data-testid="backtest-error">
                <span className="state-icon failed" aria-hidden="true">
                  <AlertTriangleIcon />
                </span>
                <p className="state-title">목록을 불러오지 못했습니다.</p>
                <p className="state-body">
                  {error ? error.message : "네트워크 또는 서버 상태 일시적 오류일 수 있습니다."}
                </p>
                <p className="state-code">{LIST_ENDPOINT}</p>
                <button className="btn btn-ghost" type="button" onClick={() => refetch()}>
                  <RefreshCwIcon aria-hidden="true" />
                  다시 시도
                </button>
              </div>
            </div>
          ) : filtered.length === 0 ? (
            <div className="card-body">
              <div className="state-box" role="status" data-testid="backtest-empty">
                <span className="state-icon" aria-hidden="true">
                  <InboxIcon />
                </span>
                <p className="state-title">
                  {items.length === 0
                    ? "첫 백테스트를 시작하세요"
                    : "해당 상태의 백테스트가 없습니다"}
                </p>
                <p className="state-body">
                  {items.length === 0
                    ? "전략을 선택하고 기간을 설정하면 결과를 받을 수 있습니다."
                    : "다른 상태를 선택하거나 새 백테스트를 실행하세요."}
                </p>
                {items.length === 0 ? (
                  <Link className="btn btn-primary btn-xs" href="/backtests/new">
                    첫 백테스트 실행
                  </Link>
                ) : (
                  <button className="btn btn-ghost btn-xs" type="button" onClick={() => pushStatus("all")}>
                    전체 보기
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="table-wrap">
              <table
                className="trades runs-table"
                aria-label={`백테스트 실행 목록 ${filtered.length}건`}
              >
                <thead>
                  <tr>
                    <th scope="col">{hRunId}</th>
                    <th scope="col">{hSymbolTf}</th>
                    <th scope="col">{hPeriod}</th>
                    <th scope="col" className="col-status">
                      {hStatus}
                    </th>
                    <th scope="col">{hStartedAt}</th>
                    <th scope="col">종료 시각</th>
                    <th scope="col">{hAction}</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((b) => {
                    // 라벨·톤은 S4 용어 SSOT 에서만 온다 (원시 enum 렌더 금지 — no-raw-enum-labels 가드).
                    const { label, tone, showCheckIcon } = BACKTEST_STATUS_LABEL[b.status];
                    return (
                      <tr key={b.id} data-testid={`backtest-row-${b.id}`} data-status={b.status}>
                        <td className="mono-l run-id">
                          <Link href={`/backtests/${b.id}`}>{b.id.slice(0, 8)}</Link>
                        </td>
                        <td className="mono-l">
                          {b.symbol} · {b.timeframe}
                        </td>
                        <td className="mono-l">
                          {formatDateTime(b.period_start)}
                          <span className="run-sub">~ {formatDateTime(b.period_end)}</span>
                        </td>
                        <td className="col-status">
                          <span className={CHIP_TONE_CLASS[tone]}>
                            {showCheckIcon ? <CheckIcon aria-hidden="true" /> : null}
                            {label}
                          </span>
                        </td>
                        <td className="mono-l dim">{formatDateTime(b.created_at)}</td>
                        {/* 무데이터 셀 — completed_at 은 종료(완료/실패/취소) 시각이다. 아직 끝나지
                            않은 실행(대기/실행 중)은 값이 없어 EMPTY_CELL 로 표기한다 (S4 lib/labels). */}
                        <td className="mono-l dim">
                          {b.completed_at ? formatDateTime(b.completed_at) : EMPTY_CELL}
                        </td>
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
          )}
        </div>
      </section>
    </main>
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
          {Array.from({ length: 6 }).map((_, i) => (
            <tr key={i}>
              {Array.from({ length: 7 }).map((__, j) => (
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
