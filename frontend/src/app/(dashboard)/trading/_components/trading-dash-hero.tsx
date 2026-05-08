"use client";

// 트레이딩 대시보드 KPI 스트립 — 프로토타입 03 visual layout (Sprint 43-W12 polish).
// useLiveSessions / useExchangeAccounts / useKillSwitchEvents 기존 hook 재사용 (dep / queryKey 그대로).
// prototype 03 dark visual → light 통일 변환 (Sprint 42-polish-3 결정 / LESSON-054).

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
        sublabel={
          activeSessions > 0
            ? `${activeSessions}개 자동 실행 중`
            : "대기 중"
        }
        tone="primary"
        live={activeSessions > 0}
      />
      <DashKpi
        icon={<WifiIcon className="size-4" />}
        label="연결된 거래소"
        value={accounts}
        sublabel={accounts > 0 ? "API 연결 정상" : "API Key 미등록"}
        tone="primary"
      />
      <DashKpi
        icon={<ShieldIcon className="size-4" />}
        label="Kill Switch"
        value={unresolvedKs}
        valueLabel={unresolvedKs > 0 ? "활성" : "정상"}
        sublabel={
          unresolvedKs > 0
            ? "주문 차단 — 즉시 확인 필요"
            : "이상 없음"
        }
        tone={ksTone}
        pulse={unresolvedKs > 0}
      />
      <DashKpi
        icon={<ZapIcon className="size-4" />}
        label="총 세션"
        value={items.length}
        sublabel={`전체 ${items.length}개`}
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
  sublabel,
  tone,
  live,
  pulse,
}: {
  icon: ReactNode;
  label: string;
  value: number;
  valueLabel?: string;
  sublabel?: string;
  tone: "primary" | "success" | "destructive" | "neutral";
  live?: boolean;
  pulse?: boolean;
}) {
  // prototype 03 의 dark accent → light 토큰 매핑.
  // - rgba(99,102,241,0.16) (dash primary glow) → var(--primary-light) #EFF6FF
  // - rgba(52,211,153,0.12) (dash green glow) → var(--success-light) #D1FAE5
  // - rgba(248,113,113,0.12) (dash red glow) → var(--destructive-light) #FEE2E2
  const accent =
    tone === "destructive"
      ? "text-[color:var(--destructive)] bg-[color:var(--destructive-light)]"
      : tone === "success"
        ? "text-[color:var(--success)] bg-[color:var(--success-light)]"
        : tone === "primary"
          ? "text-[color:var(--primary)] bg-[color:var(--primary-light)]"
          : "text-[color:var(--text-muted)] bg-[color:var(--muted)]";

  return (
    <div
      className="group relative overflow-hidden rounded-[var(--radius-lg)] border border-[color:var(--border)] bg-[color:var(--card)] p-4 shadow-[var(--card-shadow)] transition-shadow hover:shadow-[var(--card-shadow-hover)]"
      aria-live={pulse ? "polite" : undefined}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[0.7rem] font-semibold uppercase tracking-wide text-[color:var(--text-muted)]">
          {label}
        </span>
        <span
          className={
            "grid size-9 place-items-center rounded-md " +
            accent +
            (pulse ? " animate-pulse" : "")
          }
          aria-hidden="true"
        >
          {icon}
        </span>
      </div>
      <p className="mt-3 font-mono text-[1.75rem] font-bold leading-none tabular-nums tracking-tight text-[color:var(--foreground)]">
        {value}
        {valueLabel ? (
          <span
            className={
              "ml-2 align-middle text-xs font-semibold tracking-wide " +
              (tone === "destructive"
                ? "text-[color:var(--destructive)]"
                : tone === "success"
                  ? "text-[color:var(--success)]"
                  : "text-[color:var(--text-muted)]")
            }
          >
            {valueLabel}
          </span>
        ) : null}
      </p>
      {sublabel ? (
        <p className="mt-2 flex items-center gap-1.5 font-mono text-[0.72rem] text-[color:var(--text-muted)]">
          {live ? (
            <span
              className="inline-block size-1.5 rounded-full bg-[color:var(--success)] shadow-[0_0_6px_var(--success)]"
              aria-hidden="true"
            />
          ) : null}
          {sublabel}
        </p>
      ) : null}
    </div>
  );
}
