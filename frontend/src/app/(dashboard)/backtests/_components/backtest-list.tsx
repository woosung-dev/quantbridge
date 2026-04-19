"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { useBacktests } from "@/features/backtest/hooks";
import type { BacktestSummary } from "@/features/backtest/schemas";
import { formatDateTime } from "@/features/backtest/utils";

import { BacktestStatusBadge } from "./status-badge";

const LIST_QUERY = { limit: 20, offset: 0 };

export function BacktestList() {
  const { data, isLoading, isError, error, refetch } = useBacktests(LIST_QUERY);

  return (
    <div className="mx-auto max-w-[1080px] px-6 py-8">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold">백테스트</h1>
          <p className="text-sm text-muted-foreground">최근 실행한 백테스트 {LIST_QUERY.limit}건</p>
        </div>
        <Link href="/backtests/new">
          <Button>새 백테스트</Button>
        </Link>
      </header>

      {isLoading ? (
        <p className="py-12 text-center text-sm text-muted-foreground">불러오는 중…</p>
      ) : isError ? (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <p className="text-sm text-destructive">
            목록을 불러오지 못했습니다{error ? `: ${error.message}` : ""}
          </p>
          <Button variant="outline" onClick={() => refetch()}>
            다시 시도
          </Button>
        </div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState />
      ) : (
        <BacktestSummaryTable items={data.items} />
      )}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-4 rounded-xl border border-dashed p-12 text-center">
      <p className="text-sm text-muted-foreground">
        아직 실행한 백테스트가 없습니다
      </p>
      <Link href="/backtests/new">
        <Button>첫 백테스트 실행</Button>
      </Link>
    </div>
  );
}

function BacktestSummaryTable({ items }: { items: readonly BacktestSummary[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border bg-card">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th scope="col" className="px-4 py-3 text-left">심볼</th>
            <th scope="col" className="px-4 py-3 text-left">TF</th>
            <th scope="col" className="px-4 py-3 text-left">기간</th>
            <th scope="col" className="px-4 py-3 text-left">상태</th>
            <th scope="col" className="px-4 py-3 text-left">실행일</th>
            <th scope="col" className="sr-only">상세</th>
          </tr>
        </thead>
        <tbody>
          {items.map((b) => (
            <tr key={b.id} className="border-t hover:bg-muted/30">
              <td className="px-4 py-3 font-medium">
                <Link
                  href={`/backtests/${b.id}`}
                  className="hover:text-primary"
                >
                  {b.symbol}
                </Link>
              </td>
              <td className="px-4 py-3 font-mono text-xs text-muted-foreground">
                {b.timeframe}
              </td>
              <td className="px-4 py-3 text-xs text-muted-foreground">
                {formatDateTime(b.period_start)} → {formatDateTime(b.period_end)}
              </td>
              <td className="px-4 py-3">
                <BacktestStatusBadge status={b.status} />
              </td>
              <td className="px-4 py-3 text-xs text-muted-foreground">
                {formatDateTime(b.created_at)}
              </td>
              <td className="px-4 py-3 text-right">
                <Link
                  href={`/backtests/${b.id}`}
                  className="text-primary hover:underline"
                >
                  상세 →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
