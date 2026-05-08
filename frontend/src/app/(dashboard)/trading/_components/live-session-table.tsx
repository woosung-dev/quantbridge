"use client";

// 라이브 세션 테이블 (bot list) — Sprint 43-W12 prototype 03 visual 적용 (light 통일).
// prototype 03 `.bot-table` (dark `rgba(255,255,255,0.025)` hover) → light `var(--muted)` hover.
// sort: 시작 시간 desc (default) / 상태 active-first toggle.

import { useMemo, useState } from "react";
import { ArrowUpDown, Pause, Play } from "lucide-react";

import type { LiveSession } from "@/features/live-sessions/schemas";

type SortMode = "recent" | "active";

interface LiveSessionTableProps {
  sessions: readonly LiveSession[];
  // 부모가 strategy/account display name 매핑 책임.
  resolveStrategyName?: (id: string) => string;
  resolveExchangeLabel?: (id: string) => string;
}

export function LiveSessionTable({
  sessions,
  resolveStrategyName,
  resolveExchangeLabel,
}: LiveSessionTableProps) {
  const [sortMode, setSortMode] = useState<SortMode>("recent");

  const sorted = useMemo(() => {
    const copy = [...sessions];
    if (sortMode === "recent") {
      copy.sort((a, b) => b.created_at.localeCompare(a.created_at));
    } else {
      copy.sort((a, b) => {
        if (a.is_active === b.is_active) {
          return b.created_at.localeCompare(a.created_at);
        }
        return a.is_active ? -1 : 1;
      });
    }
    return copy;
  }, [sessions, sortMode]);

  if (sessions.length === 0) {
    return (
      <p className="rounded-[var(--radius-md)] border border-dashed border-[color:var(--border)] bg-[color:var(--card)] px-4 py-6 text-center text-sm text-[color:var(--text-muted)]">
        활성 세션이 없습니다.
      </p>
    );
  }

  return (
    <div
      className="overflow-hidden rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-[color:var(--card)] shadow-[var(--card-shadow)]"
      data-testid="live-session-table"
    >
      <div className="flex items-center justify-between gap-2 border-b border-[color:var(--border)] px-4 py-3">
        <h3 className="text-sm font-semibold text-[color:var(--foreground)]">
          라이브 세션 ({sessions.length})
        </h3>
        <button
          type="button"
          onClick={() =>
            setSortMode((m) => (m === "recent" ? "active" : "recent"))
          }
          className="inline-flex items-center gap-1 rounded-[var(--radius-sm)] px-2 py-1 text-xs font-medium text-[color:var(--text-muted)] transition-colors hover:bg-[color:var(--muted)] hover:text-[color:var(--foreground)]"
          data-testid="live-session-sort-toggle"
        >
          <ArrowUpDown className="size-3" aria-hidden="true" />
          {sortMode === "recent" ? "최신 시작순" : "활성 우선"}
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[color:var(--border)] bg-[color:var(--muted)]/40 text-left">
              <th
                scope="col"
                className="w-8 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--text-muted)]"
              >
                <span className="sr-only">상태</span>
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--text-muted)]"
              >
                심볼
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--text-muted)]"
              >
                전략
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--text-muted)]"
              >
                인터벌
              </th>
              <th
                scope="col"
                className="px-2 py-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--text-muted)]"
              >
                상태
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((s) => (
              <tr
                key={s.id}
                className="border-b border-[color:var(--border)] transition-colors hover:bg-[color:var(--muted)]/40 last:border-b-0"
              >
                <td className="px-4 py-2.5">
                  <span
                    className={
                      "inline-block size-2 rounded-full " +
                      (s.is_active
                        ? "bg-[color:var(--success)] shadow-[0_0_6px_var(--success)]"
                        : "bg-[color:var(--text-muted)]/50")
                    }
                    aria-label={s.is_active ? "활성" : "비활성"}
                  />
                </td>
                <td className="px-2 py-2.5 font-mono text-xs font-semibold text-[color:var(--foreground)]">
                  {s.symbol}
                </td>
                <td className="px-2 py-2.5 text-xs text-[color:var(--foreground)]">
                  {resolveStrategyName?.(s.strategy_id) ?? s.strategy_id.slice(0, 8)}
                  {resolveExchangeLabel ? (
                    <span className="ml-1 text-[color:var(--text-muted)]">
                      · {resolveExchangeLabel(s.exchange_account_id)}
                    </span>
                  ) : null}
                </td>
                <td className="px-2 py-2.5 font-mono text-xs uppercase text-[color:var(--text-muted)]">
                  {s.interval}
                </td>
                <td className="px-2 py-2.5">
                  <span
                    className={
                      "inline-flex items-center gap-1 rounded-[var(--radius-sm)] px-2 py-0.5 font-mono text-[0.68rem] font-bold uppercase tracking-wider " +
                      (s.is_active
                        ? "bg-[color:var(--success-light)] text-[color:var(--success)]"
                        : "bg-[color:var(--muted)] text-[color:var(--text-muted)]")
                    }
                  >
                    {s.is_active ? (
                      <Play className="size-2.5" aria-hidden="true" />
                    ) : (
                      <Pause className="size-2.5" aria-hidden="true" />
                    )}
                    {s.is_active ? "ACTIVE" : "PAUSED"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
