"use client";

// 트레이딩 대시보드 KPI 스트립 — 프로토타입 03 visual layout (Sprint 41-B2).
// useLiveSessions / useExchangeAccounts / useKillSwitchEvents 기존 hook 재사용 (dep / queryKey 그대로).

import type { ReactNode } from "react";
import {
  Activity as ActivityIcon,
  ShieldAlert as ShieldIcon,
  Wifi as WifiIcon,
  Zap as ZapIcon,
} from "lucide-react";

import { useExchangeAccounts, useKillSwitchEvents } from "@/features/trading";
import { useLiveSessions } from "@/features/live-sessions";
import type { LiveSession } from "@/features/live-sessions/schemas";
import type { KillSwitchEvent } from "@/features/trading/schemas";

export function TradingDashHero() {
  const { data: sessionsData } = useLiveSessions();
  const { data: accountsData } = useExchangeAccounts();
  const { data: ksData } = useKillSwitchEvents();

  const items: readonly LiveSession[] = sessionsData?.items ?? [];
  const activeSessions = items.filter((s) => s.is_active).length;
  const accounts = accountsData?.length ?? 0;
  const ksEvents: readonly KillSwitchEvent[] = ksData?.items ?? [];
  const unresolvedKs = ksEvents.filter((e) => e.resolved_at == null).length;
  const ksTone = unresolvedKs > 0 ? "destructive" : "success";

  return (
    <section
      aria-label="트레이딩 KPI"
      className="grid grid-cols-2 gap-3 md:grid-cols-4"
    >
      <DashKpi
        icon={<ActivityIcon className="size-4" />}
        label="활성 세션"
        value={activeSessions}
        tone="primary"
      />
      <DashKpi
        icon={<WifiIcon className="size-4" />}
        label="연결된 거래소"
        value={accounts}
        tone="primary"
      />
      <DashKpi
        icon={<ShieldIcon className="size-4" />}
        label="Kill Switch"
        value={unresolvedKs}
        valueLabel={unresolvedKs > 0 ? "활성" : "정상"}
        tone={ksTone}
      />
      <DashKpi
        icon={<ZapIcon className="size-4" />}
        label="총 세션"
        value={items.length}
        tone="neutral"
      />
    </section>
  );
}

function DashKpi({
  icon,
  label,
  value,
  valueLabel,
  tone,
}: {
  icon: ReactNode;
  label: string;
  value: number;
  valueLabel?: string;
  tone: "primary" | "success" | "destructive" | "neutral";
}) {
  const accent =
    tone === "destructive"
      ? "text-[color:var(--destructive)] bg-[color:var(--destructive-light,rgba(248,113,113,0.12))]"
      : tone === "success"
        ? "text-[color:var(--success,#34d399)] bg-[rgba(52,211,153,0.12)]"
        : tone === "primary"
          ? "text-[color:var(--primary)] bg-[rgba(99,102,241,0.16)]"
          : "text-[color:var(--text-muted)] bg-[color:var(--muted)]";
  return (
    <div className="rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-[color:var(--card)] p-4 shadow-[var(--card-shadow)]">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[0.7rem] font-semibold uppercase tracking-wide text-[color:var(--text-muted)]">
          {label}
        </span>
        <span
          className={"grid size-8 place-items-center rounded-md " + accent}
          aria-hidden="true"
        >
          {icon}
        </span>
      </div>
      <p className="mt-3 font-mono text-2xl font-bold tabular-nums">
        {value}
        {valueLabel ? (
          <span className="ml-2 text-xs font-medium tracking-wide text-[color:var(--text-muted)]">
            {valueLabel}
          </span>
        ) : null}
      </p>
    </div>
  );
}
