"use client";

// 백테스트 목록 — 프로토타입 09 visual layout 정합 (Sprint 41-B2).
// 헤더 + KPI 스트립(현 페이지 status 분포) + 필터 chip + 테이블. EmptyState 는 Worker E.

import Link from "next/link";
import { useMemo, type ReactNode } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  CheckCircle2 as CheckIcon,
  Clock as ClockIcon,
  ListIcon,
  PlusIcon,
  XCircle as FailIcon,
} from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { useBacktests } from "@/features/backtest/hooks";
import type { BacktestStatus, BacktestSummary } from "@/features/backtest/schemas";
import { formatDateTime } from "@/features/backtest/utils";

import { RunningProgressBar } from "./running-progress-bar";
import { BacktestStatusBadge } from "./status-badge";

const PAGE_SIZE = 20;
const STATUS_FILTERS: ReadonlyArray<{ id: "all" | BacktestStatus; label: string }> = [
  { id: "all", label: "전체" },
  { id: "completed", label: "완료" },
  { id: "running", label: "실행중" },
  { id: "queued", label: "대기" },
  { id: "failed", label: "실패" },
  { id: "cancelled", label: "취소" },
];

export function BacktestList() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const statusParam = searchParams.get("status") ?? "all";
  const activeStatus: "all" | BacktestStatus = STATUS_FILTERS.some((f) => f.id === statusParam)
    ? (statusParam as "all" | BacktestStatus)
    : "all";

  // BE 가 status 필터를 list endpoint 에서 지원하지 않을 수 있으므로 client-side filter.
  // hook query 는 페이지네이션만 변경 → queryKey identity 유지.
  const query = useMemo(() => ({ limit: PAGE_SIZE, offset: 0 }), []);
  const { data, isLoading, isError, error, refetch } = useBacktests(query);

  // useMemo dep 안정성을 위해 items reference 자체를 memoize.
  // data?.items 는 매 렌더 fresh array fallback 가능 → React Query 결과 그대로 dep 에 넣지 않음.
  const items = useMemo<readonly BacktestSummary[]>(
    () => data?.items ?? [],
    [data?.items],
  );
  // Sprint 41-B2 (codex review P2): client-side status 필터는 현재 페이지(limit 20)에만 적용 가능.
  // total > items.length 면 후속 페이지의 매칭이 누락 → "해당 상태 없음" 오표시. Beta 에 BE
  // status param 추가까지 chip(전체 제외)을 비활성 + 안내 문구 표시. 이미 활성 상태였다면
  // 현재 페이지에 한정 적용됨을 명시.
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
    <div className="mx-auto max-w-[1200px] px-6 py-8">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">백테스트</h1>
          <p className="text-sm text-text-secondary">
            전략의 과거 성과를 측정하고 비교하세요
          </p>
        </div>
        <Button render={<Link href="/backtests/new" />} nativeButton={false}>
          <PlusIcon className="size-4" />새 백테스트
        </Button>
      </header>

      {/* KPI 스트립 — 프로토타입 09 패턴. 현재 페이지 status 분포 (BE 집계 endpoint 추가 X). */}
      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <KpiCard
          icon={<ListIcon className="size-4" />}
          label="총 건수"
          value={data?.total ?? 0}
          tone="primary"
          sub="전체 백테스트"
        />
        <KpiCard
          icon={<CheckIcon className="size-4" />}
          label="완료"
          value={counts.completed}
          tone="success"
          sub={
            counts.completed > 0 && items.length > 0
              ? `${Math.round((counts.completed / items.length) * 100)}% 완료율`
              : undefined
          }
        />
        <KpiCard
          icon={<ClockIcon className="size-4" />}
          label="실행 중"
          value={counts.running + counts.queued}
          tone="primary"
          pulse={counts.running + counts.queued > 0}
          sub={counts.queued > 0 ? `대기 ${counts.queued}건 포함` : undefined}
        />
        <KpiCard
          icon={<FailIcon className="size-4" />}
          label="실패"
          value={counts.failed}
          tone="destructive"
          sub={counts.failed > 0 ? "재실행 권장" : undefined}
        />
      </div>

      {/* 필터 chip — Strategy list 와 동일 패턴 (Sprint FE-A).
          Sprint 41-B2 (codex review P2): hasMorePages 시 '전체' 제외 chip 비활성 + 안내. */}
      <div className="mb-2 flex flex-wrap gap-2">
        {STATUS_FILTERS.map((f) => {
          const active = f.id === activeStatus;
          const isDisabled = hasMorePages && f.id !== "all";
          const title = isDisabled
            ? "현재 페이지(20건) 만 필터되므로 비활성화 — Beta 에 서버 필터 추가 예정"
            : undefined;
          return (
            <button
              key={f.id}
              type="button"
              onClick={() => {
                if (isDisabled) return;
                pushStatus(f.id);
              }}
              aria-pressed={active}
              aria-disabled={isDisabled || undefined}
              disabled={isDisabled}
              title={title}
              data-testid={`backtest-filter-${f.id}`}
              className={
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors duration-150 ease-out " +
                (isDisabled
                  ? "cursor-not-allowed border-[color:var(--border)] text-[color:var(--text-muted)] opacity-50"
                  : active
                    ? "border-[color:var(--primary)] bg-[color:var(--primary-light)] text-[color:var(--primary)]"
                    : "border-[color:var(--border)] text-[color:var(--text-secondary)] hover:bg-[color:var(--bg-alt)]")
              }
            >
              {f.label}
            </button>
          );
        })}
      </div>
      {hasMorePages && (
        <p
          data-testid="backtest-filter-notice"
          className="mb-6 text-xs text-[color:var(--text-muted)]"
        >
          현재 페이지(20건)만 필터됩니다 — Beta 에 서버 필터가 추가될 예정입니다.
        </p>
      )}
      {!hasMorePages && <div className="mb-6" />}

      {isLoading ? (
        <ListSkeleton />
      ) : isError ? (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <p className="text-sm text-destructive">
            목록을 불러오지 못했습니다{error ? `: ${error.message}` : ""}
          </p>
          <Button variant="outline" onClick={() => refetch()}>
            다시 시도
          </Button>
        </div>
      ) : filtered.length === 0 ? (
        items.length === 0 ? (
          <EmptyState
            headline="첫 백테스트를 시작하세요"
            description="전략을 선택하고 기간을 설정하면 결과를 받을 수 있습니다."
            cta={{ label: "첫 백테스트 실행", href: "/backtests/new" }}
          />
        ) : (
          <EmptyState
            headline="해당 상태의 백테스트가 없습니다"
            description="다른 필터를 선택하거나 새 백테스트를 실행하세요."
            cta={{ label: "전체 보기", onClick: () => pushStatus("all") }}
          />
        )
      ) : (
        <BacktestSummaryTable items={filtered} />
      )}
    </div>
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

function KpiCard({
  icon,
  label,
  value,
  tone,
  sub,
  pulse = false,
}: {
  icon: ReactNode;
  label: string;
  value: number;
  tone: "primary" | "success" | "destructive";
  /** prototype 09 .kpi-sub — 한 줄 보조 정보 (delta / 가정 / 강조 라벨). */
  sub?: string;
  /** 실시간 상태 보강 — value > 0 시 icon ring pulse (WebSocket 재연결 시 시각 단서). */
  pulse?: boolean;
}) {
  const accent =
    tone === "success"
      ? "text-[color:var(--success)] bg-[color:var(--success-light)]"
      : tone === "destructive"
        ? "text-[color:var(--destructive)] bg-[color:var(--destructive-light)]"
        : "text-[color:var(--primary)] bg-[color:var(--primary-light)]";
  const valueTone =
    tone === "success"
      ? "text-[color:var(--success)]"
      : tone === "destructive"
        ? "text-[color:var(--destructive)]"
        : "text-[color:var(--text-primary)]";
  return (
    <div
      className="rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-card p-5 shadow-[var(--card-shadow)] transition hover:shadow-[var(--card-shadow-hover)]"
      data-testid={`kpi-card-${label.replace(/\s+/g, "-")}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[0.75rem] font-semibold uppercase tracking-wide text-[color:var(--text-muted)]">
          {label}
        </span>
        <span
          className={"grid size-8 place-items-center rounded-md " + accent}
          style={pulse ? { animation: "qb-pulse-dot 2s infinite" } : undefined}
          aria-hidden="true"
        >
          {icon}
        </span>
      </div>
      <p className={`mt-3 font-mono text-2xl font-bold tabular-nums ${valueTone}`}>{value}</p>
      {sub ? (
        <p className="mt-1 text-[0.75rem] text-[color:var(--text-muted)]">{sub}</p>
      ) : null}
    </div>
  );
}

function ListSkeleton() {
  return (
    <div className="overflow-x-auto rounded-xl border bg-card">
      <div className="flex flex-col gap-2 p-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-12 animate-pulse rounded-md bg-[color:var(--bg-alt)]"
          />
        ))}
      </div>
    </div>
  );
}

function BacktestSummaryTable({ items }: { items: readonly BacktestSummary[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border bg-card shadow-[var(--card-shadow)]">
      <table className="w-full text-sm">
        <thead className="bg-[color:var(--bg-soft)] text-xs uppercase tracking-wide text-[color:var(--text-muted)]">
          <tr>
            <th scope="col" className="px-4 py-3 text-left">심볼</th>
            <th scope="col" className="px-4 py-3 text-left">TF</th>
            <th scope="col" className="px-4 py-3 text-left">기간 / 진행률</th>
            <th scope="col" className="px-4 py-3 text-left">상태</th>
            <th scope="col" className="px-4 py-3 text-left">실행일</th>
            <th scope="col" className="sr-only">상세</th>
          </tr>
        </thead>
        <tbody>
          {items.map((b) => {
            const isInFlight = b.status === "running" || b.status === "queued" || b.status === "cancelling";
            return (
              <tr
                key={b.id}
                className="cursor-pointer border-t border-[color:var(--border-light)] border-l-2 border-l-transparent transition-colors duration-150 ease-out hover:border-l-[color:var(--primary)] hover:bg-[color:var(--bg-soft)]"
                data-testid={`backtest-row-${b.id}`}
                data-status={b.status}
              >
                <td className="px-4 py-3 font-medium">
                  <Link href={`/backtests/${b.id}`} className="hover:text-primary">
                    {b.symbol}
                  </Link>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{b.timeframe}</td>
                <td className="px-4 py-3 text-xs text-muted-foreground">
                  {isInFlight ? (
                    <RunningProgressBar status={b.status} />
                  ) : (
                    <span className="font-mono">
                      {formatDateTime(b.period_start)} → {formatDateTime(b.period_end)}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <BacktestStatusBadge status={b.status} />
                </td>
                <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                  {formatDateTime(b.created_at)}
                </td>
                <td className="px-4 py-3 text-right">
                  <Link href={`/backtests/${b.id}`} className="text-primary hover:underline">
                    상세 →
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
