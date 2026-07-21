// 주문 원장(Blotter) — 라이브/데모 주문을 상태 필터·정렬·CSV·페이지네이션으로 통합 조회
"use client";

import { AlertCircle, Download, Receipt } from "lucide-react";
import { useMemo, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/skeleton";
import { downloadCsv } from "@/features/backtest/utils";
import { useOrders } from "@/features/trading";
import { ORDER_STATE_LABEL } from "@/features/trading/labels";
import type { Order } from "@/features/trading/schemas";
import { statusLabelOf, type ChipTone } from "@/lib/labels";
import { cn } from "@/lib/utils";

const FETCH_LIMIT = 200;
const PAGE_SIZE = 25;

type StateFilter = "all" | "filled" | "open" | "closed";

const STATE_TABS: ReadonlyArray<{ value: StateFilter; label: string }> = [
  { value: "all", label: "전체" },
  { value: "filled", label: "체결" },
  { value: "open", label: "대기·전송" },
  { value: "closed", label: "취소·거부" },
];

function matchesFilter(state: Order["state"], f: StateFilter): boolean {
  if (f === "all") return true;
  if (f === "filled") return state === "filled";
  if (f === "open") return state === "pending" || state === "submitted";
  return state === "cancelled" || state === "rejected";
}

// 라벨·톤은 용어 SSOT(ORDER_STATE_LABEL)에서 온다. 아래는 ChipTone → 현행 Tailwind
// 표현 매핑일 뿐이며, 프로토타입 chip 클래스 적용은 /trading 재구축 슬라이스 소관이다.
const TONE_CLASS: Record<ChipTone, string> = {
  neutral: "bg-muted text-muted-foreground",
  done: "bg-success-subtle text-success",
  accent: "bg-primary-light text-primary",
  warn: "bg-destructive-subtle text-destructive",
};

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("ko-KR", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function ordersToCsv(orders: readonly Order[]): string {
  const header = ["시간", "심볼", "방향", "수량", "체결가", "상태"];
  const rows = orders.map((o) => [
    formatDateTime(o.created_at),
    o.symbol,
    o.side === "buy" ? "매수" : "매도",
    o.quantity,
    o.filled_price ?? "",
    statusLabelOf(ORDER_STATE_LABEL, o.state, "order.state").label,
  ]);
  return [header, ...rows]
    .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))
    .join("\n");
}

export function OrdersBlotter() {
  const ordersQ = useOrders(FETCH_LIMIT);
  const [filter, setFilter] = useState<StateFilter>("all");
  const [page, setPage] = useState(0);

  const orderItems = ordersQ.data?.items;
  const allOrders = useMemo(() => orderItems ?? [], [orderItems]);
  const filtered = useMemo(
    () => allOrders.filter((o) => matchesFilter(o.state, filter)),
    [allOrders, filter],
  );

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const pageRows = filtered.slice(
    safePage * PAGE_SIZE,
    safePage * PAGE_SIZE + PAGE_SIZE,
  );

  const counts = useMemo(() => {
    const c: Record<StateFilter, number> = { all: 0, filled: 0, open: 0, closed: 0 };
    for (const o of allOrders) {
      c.all += 1;
      for (const t of STATE_TABS) {
        if (t.value !== "all" && matchesFilter(o.state, t.value)) c[t.value] += 1;
      }
    }
    return c;
  }, [allOrders]);

  const handleFilter = (f: StateFilter) => {
    setFilter(f);
    setPage(0);
  };

  const handleExport = () => {
    const ts = formatDateTime(new Date().toISOString()).replace(/[^\d]/g, "");
    downloadCsv(`orders-${ts}.csv`, ordersToCsv(filtered));
  };

  return (
    <div className="mx-auto max-w-[1200px] space-y-5 px-4 py-6 sm:px-6 sm:py-8">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl font-bold tracking-tight">
          주문 내역
        </h1>
        <p className="text-sm text-muted-foreground">
          라이브·데모 세션이 실행한 모든 주문을 한곳에서 조회합니다.
        </p>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div
          role="tablist"
          aria-label="주문 상태 필터"
          className="inline-flex items-center gap-1 rounded-md bg-muted p-1"
        >
          {STATE_TABS.map((t) => (
            <button
              key={t.value}
              type="button"
              role="tab"
              aria-selected={filter === t.value}
              onClick={() => handleFilter(t.value)}
              className={cn(
                "min-h-9 rounded px-3 text-sm font-medium transition-colors",
                filter === t.value
                  ? "bg-card text-primary shadow-card"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {t.label}
              <span className="ml-1.5 font-mono text-xs tabular-nums opacity-70">
                {counts[t.value]}
              </span>
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={handleExport}
          disabled={filtered.length === 0}
          className="inline-flex h-9 items-center gap-1.5 rounded-md border border-input bg-background px-3 text-sm font-medium transition-colors hover:bg-muted disabled:opacity-50"
        >
          <Download className="h-4 w-4" aria-hidden="true" />
          CSV
        </button>
      </div>

      {ordersQ.isLoading ? (
        // 스켈레톤 로더 — 레이아웃 높이와 맞춘 행 shimmer (스피너 대신, design-taste Rule 5).
        <div className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-card">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton
              key={i}
              variant="list-row"
              shimmer
              className="rounded-none border-0"
            />
          ))}
        </div>
      ) : ordersQ.isError ? (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-destructive/40 bg-destructive-subtle py-16 text-sm text-destructive">
          <AlertCircle className="h-5 w-5" aria-hidden="true" />
          주문 목록을 불러오지 못했습니다.
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border bg-card">
          <EmptyState
            icon={<Receipt className="h-6 w-6 text-muted-foreground" aria-hidden="true" />}
            headline="표시할 주문이 없습니다"
            description="라이브·데모 세션이 주문을 실행하면 이곳 원장에 기록됩니다."
          />
        </div>
      ) : (
        <>
          <div className="qb-card-fade-in overflow-x-auto rounded-lg border border-border bg-card">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-left font-mono text-[0.68rem] uppercase tracking-[0.12em] text-muted-foreground">
                  <th className="px-4 py-2.5 font-medium">시간</th>
                  <th className="px-4 py-2.5 font-medium">심볼</th>
                  <th className="px-4 py-2.5 font-medium">방향</th>
                  <th className="px-4 py-2.5 text-right font-medium">수량</th>
                  <th className="px-4 py-2.5 text-right font-medium">체결가</th>
                  <th className="px-4 py-2.5 font-medium">상태</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {pageRows.map((o) => {
                  const { label, tone } = statusLabelOf(
                    ORDER_STATE_LABEL,
                    o.state,
                    "order.state",
                  );
                  return (
                    <tr key={o.id} className="transition-colors hover:bg-muted/50">
                      <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs tabular-nums text-muted-foreground">
                        {formatDateTime(o.created_at)}
                      </td>
                      <td className="px-4 py-2.5 font-medium text-foreground">
                        {o.symbol}
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className={
                            o.side === "buy" ? "text-bullish" : "text-bearish"
                          }
                        >
                          {o.side === "buy" ? "매수" : "매도"}
                        </span>
                        {o.reduce_only ? (
                          <span className="ml-1.5 rounded bg-muted px-1.5 py-0.5 text-[0.65rem] text-muted-foreground">
                            감소전용
                          </span>
                        ) : null}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums">
                        {o.quantity}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums">
                        {o.filled_price ?? "—"}
                      </td>
                      <td className="px-4 py-2.5">
                        <span
                          className={cn(
                            "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                            TONE_CLASS[tone],
                          )}
                        >
                          {label}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-mono tabular-nums">
              {filtered.length}건 중 {safePage * PAGE_SIZE + 1}–
              {Math.min((safePage + 1) * PAGE_SIZE, filtered.length)}
              {allOrders.length >= FETCH_LIMIT ? ` · 최근 ${FETCH_LIMIT}건 표시` : ""}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={safePage === 0}
                className="rounded-md border border-input bg-background px-3 py-1.5 font-medium transition-colors hover:bg-muted disabled:opacity-40"
              >
                이전
              </button>
              <span className="font-mono tabular-nums">
                {safePage + 1} / {pageCount}
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
                disabled={safePage >= pageCount - 1}
                className="rounded-md border border-input bg-background px-3 py-1.5 font-medium transition-colors hover:bg-muted disabled:opacity-40"
              >
                다음
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
