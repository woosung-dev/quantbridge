"use client";

// 백테스트 목록 — C 디자인 언어 이식 (S5). 프로토타입 screen-03 의 시맨틱 CSS 를 쓰되,
// 열은 실데이터(BacktestSummary)가 받치는 것만 그린다. 목업의 수익률/MDD/샤프/거래수/전략명은
// list 스키마에 없으므로 렌더하지 않는다 (캐논 §4.9 "데이터 모델에 없는 값 = 가짜 데이터").

import Link from "next/link";
import { useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { PlusIcon, RefreshCwIcon } from "lucide-react";

import { useBacktests } from "@/features/backtest/hooks";
import type { BacktestStatus, BacktestSummary } from "@/features/backtest/schemas";
import { formatDateTime } from "@/features/backtest/utils";

const PAGE_SIZE = 20;

const STATUS_FILTERS: ReadonlyArray<{ id: "all" | BacktestStatus; label: string }> = [
  { id: "all", label: "전체" },
  { id: "completed", label: "완료" },
  { id: "running", label: "실행 중" },
  { id: "queued", label: "대기" },
  { id: "failed", label: "실패" },
  { id: "cancelled", label: "취소" },
];

/** 상태 → C 칩 클래스 + 라벨. 완료=bull, 실패=warn, 나머지는 기본 칩. */
const STATUS_CHIP: Record<BacktestStatus, { cls: string; label: string }> = {
  completed: { cls: "chip done", label: "완료" },
  running: { cls: "chip", label: "실행 중" },
  cancelling: { cls: "chip", label: "취소 중" },
  queued: { cls: "chip", label: "대기" },
  failed: { cls: "chip failed", label: "실패" },
  cancelled: { cls: "chip", label: "취소됨" },
};

export function BacktestList() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const statusParam = searchParams.get("status") ?? "all";
  const activeStatus: "all" | BacktestStatus = STATUS_FILTERS.some((f) => f.id === statusParam)
    ? (statusParam as "all" | BacktestStatus)
    : "all";

  // BE 가 status 필터를 list endpoint 에서 지원하지 않으므로 client-side filter (현재 페이지 한정).
  // hook query 는 페이지네이션만 → queryKey identity 유지.
  const query = useMemo(() => ({ limit: PAGE_SIZE, offset: 0 }), []);
  const { data, isLoading, isError, error, refetch } = useBacktests(query);

  const items = useMemo<readonly BacktestSummary[]>(() => data?.items ?? [], [data?.items]);
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

  return (
    <main className="page">
      {/* ===== 목록 헤더 ===== */}
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
              새 백테스트
            </Link>
          </div>
        </div>
      </section>

      {/* ===== 목록 ===== */}
      <section className="section" aria-label="실행 목록">
        <header className="section-head">
          <p className="eyebrow">
            <span className="num">01</span> 목록
          </p>
          <h2 className="section-title">실행 {total}건</h2>
          <p className="section-desc">
            최근에 실행한 순서로 정렬했습니다. 심볼과 주기는 그 실행에 실제로 쓴 값입니다.
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
                          ? "현재 페이지(20건)만 필터되므로 비활성화 — Beta 에 서버 필터 추가 예정"
                          : undefined
                      }
                      data-testid={`backtest-filter-${f.id}`}
                      onClick={() => {
                        if (isDisabled) return;
                        pushStatus(f.id);
                      }}
                    >
                      {f.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <p className="runs-summary">
            <span className="mono">{total}</span>건 · 완료 <span className="mono">{counts.completed}</span> ·
            실행 중 <span className="mono">{counts.running + counts.queued}</span> · 실패{" "}
            <span className="mono">{counts.failed}</span>
          </p>
          {hasMorePages ? (
            <p className="runs-summary filter-chips-note" data-testid="backtest-filter-notice">
              현재 페이지(20건)만 필터됩니다 — Beta 에 서버 필터가 추가될 예정입니다.
            </p>
          ) : null}

          {isLoading ? (
            <ListSkeleton />
          ) : isError ? (
            <div className="state-box" data-testid="backtest-error">
              <p className="state-title">목록을 불러오지 못했습니다</p>
              <p className="state-body">{error ? error.message : "잠시 뒤 다시 시도하세요."}</p>
              <button className="btn btn-xs" type="button" onClick={() => refetch()}>
                다시 시도
              </button>
            </div>
          ) : filtered.length === 0 ? (
            <div className="state-box" data-testid="backtest-empty">
              <p className="state-title">
                {items.length === 0 ? "첫 백테스트를 시작하세요" : "해당 상태의 백테스트가 없습니다"}
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
                <button className="btn btn-xs" type="button" onClick={() => pushStatus("all")}>
                  전체 보기
                </button>
              )}
            </div>
          ) : (
            <div className="table-wrap">
              <table
                className="trades runs-table"
                aria-label={`백테스트 실행 목록 ${filtered.length}건`}
              >
                <thead>
                  <tr>
                    <th scope="col">실행 ID</th>
                    <th scope="col">심볼 · 주기</th>
                    <th scope="col">기간</th>
                    <th scope="col" className="col-status">
                      상태
                    </th>
                    <th scope="col">실행 시각</th>
                    <th scope="col">액션</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((b) => {
                    const chip = STATUS_CHIP[b.status];
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
                          <span className={chip.cls}>{chip.label}</span>
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

function ListSkeleton() {
  return (
    <div className="table-wrap" aria-hidden="true">
      <table className="trades runs-table">
        <tbody>
          {Array.from({ length: 6 }).map((_, i) => (
            <tr key={i}>
              {Array.from({ length: 6 }).map((__, j) => (
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
