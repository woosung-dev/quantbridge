// Sprint 43 W15 — Waitlist KPI 3종 strip (총 신청 / 미승인 / 승인됨).
// W11 trade-stats-strip + W6 metrics-cards 패턴 차용. 클라이언트 즉석 집계.
"use client";

import { useMemo } from "react";

import type {
  WaitlistApplicationResponse,
  WaitlistStatus,
} from "@/features/waitlist/schemas";

interface WaitlistStatsStripProps {
  items: readonly WaitlistApplicationResponse[];
  /** 현재 필터로 가린 인원 미반영 — total 은 BE 응답값 사용. */
  total?: number;
}

interface AggregatedStats {
  totalCount: number;
  pendingCount: number;
  approvedCount: number;
}

function aggregate(
  items: readonly WaitlistApplicationResponse[],
): AggregatedStats {
  const counts: Record<WaitlistStatus, number> = {
    pending: 0,
    invited: 0,
    joined: 0,
    rejected: 0,
  };
  for (const item of items) {
    counts[item.status] += 1;
  }
  // 승인됨 = invited + joined (이미 invite 발송 또는 가입 완료)
  return {
    totalCount: items.length,
    pendingCount: counts.pending,
    approvedCount: counts.invited + counts.joined,
  };
}

export function WaitlistStatsStrip({ items, total }: WaitlistStatsStripProps) {
  const stats = useMemo(() => aggregate(items), [items]);

  return (
    <section
      aria-label="Waitlist 요약 통계"
      className="grid grid-cols-1 gap-3 sm:grid-cols-3"
      data-testid="waitlist-stats-strip"
    >
      <StatCard
        label="총 신청"
        value={(total ?? stats.totalCount).toString()}
        sub={total !== undefined ? "전체 누적" : "현재 필터 기준"}
      />
      <StatCard
        label="미승인 (대기중)"
        value={stats.pendingCount.toString()}
        sub={stats.pendingCount > 0 ? "검토 필요" : "처리 완료"}
        tone={stats.pendingCount > 0 ? "warn" : "neutral"}
      />
      <StatCard
        label="승인됨"
        value={stats.approvedCount.toString()}
        sub="invited + joined"
        tone="pos"
      />
    </section>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  tone?: "pos" | "warn" | "neutral";
}

function StatCard({ label, value, sub, tone = "neutral" }: StatCardProps) {
  const toneClass =
    tone === "pos"
      ? "text-emerald-600"
      : tone === "warn"
        ? "text-amber-600"
        : "text-[color:var(--text-primary)]";
  return (
    <div className="rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-white px-4 py-3">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-[color:var(--text-tertiary)]">
        {label}
      </div>
      <div
        className={`font-mono text-2xl font-bold leading-tight ${toneClass}`}
        data-testid={`waitlist-stat-${label}`}
      >
        {value}
      </div>
      {sub ? (
        <div className="mt-1 text-xs text-[color:var(--text-secondary)]">
          {sub}
        </div>
      ) : null}
    </div>
  );
}
