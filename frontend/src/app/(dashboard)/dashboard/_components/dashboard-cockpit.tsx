// 포트폴리오 개요 코크핏 — 라이브 세션/백테스트/전략을 집계한 data-as-hero 플래그십
"use client";

import type { ReactNode } from "react";
import {
  Activity,
  ArrowRight,
  Code2,
  LineChart,
  Receipt,
  ShieldAlert,
  ShieldCheck,
  Wifi,
} from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { TradingChart } from "@/components/charts/trading-chart";
import { Skeleton } from "@/components/skeleton";
import { useBacktests } from "@/features/backtest/hooks";
import { formatDate } from "@/features/backtest/utils";
import {
  useLiveSessions,
  useLiveSessionsAggregate,
} from "@/features/live-sessions";
import { useStrategies } from "@/features/strategy/hooks";
import {
  useExchangeAccounts,
  useKillSwitchEvents,
  useOrders,
} from "@/features/trading";
import { cn } from "@/lib/utils";

import { LiveSessionTable } from "../../trading/_components/live-session-table";
import { PnlTape } from "@/components/tape/pnl-tape";
import { TickRuler } from "@/components/tick-ruler";

function formatUsd(n: number): string {
  const sign = n > 0 ? "+" : n < 0 ? "−" : "";
  return `${sign}$${Math.abs(n).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

const MICRO_LABEL =
  "font-mono text-[0.68rem] font-medium uppercase tracking-[0.14em] text-muted-foreground";

export function DashboardCockpit() {
  const sessionsQ = useLiveSessions();
  const sessionItems = sessionsQ.data?.items;
  const activeSessions = useMemo(
    () => (sessionItems ?? []).filter((s) => s.is_active),
    [sessionItems],
  );

  const agg = useLiveSessionsAggregate(activeSessions);
  const accountsQ = useExchangeAccounts();
  const ksQ = useKillSwitchEvents();
  const ordersQ = useOrders(50);
  const strategiesQ = useStrategies({ limit: 1, offset: 0, is_archived: false });
  const recentBacktestsQ = useBacktests({ limit: 5, offset: 0 });
  const strategyListQ = useStrategies({ limit: 100, offset: 0, is_archived: false });

  const accounts = accountsQ.data?.length ?? 0;
  const unresolvedKs = (ksQ.data?.items ?? []).filter(
    (e) => e.resolved_at == null,
  ).length;
  const pendingOrders = (ordersQ.data?.items ?? []).filter(
    (o) => o.state === "pending" || o.state === "submitted",
  ).length;
  const strategyCount = strategiesQ.data?.total ?? 0;

  const pnlTone =
    agg.totalRealizedPnl > 0
      ? "text-bullish"
      : agg.totalRealizedPnl < 0
        ? "text-bearish"
        : "text-foreground";

  const deltas = useMemo(() => {
    const c = agg.mergedEquityCurve;
    const out: number[] = [];
    for (let i = 1; i < c.length; i++) out.push(c[i]!.value - c[i - 1]!.value);
    return out;
  }, [agg.mergedEquityCurve]);

  const equityChartData = useMemo(
    () => agg.mergedEquityCurve.map((p) => ({ time: p.time, value: p.value })),
    [agg.mergedEquityCurve],
  );
  const hasEquitySeries = equityChartData.length >= 2;

  const strategyNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of strategyListQ.data?.items ?? []) map.set(s.id, s.name);
    return map;
  }, [strategyListQ.data?.items]);

  const recentBacktests = recentBacktestsQ.data?.items ?? [];

  return (
    <div className="mx-auto max-w-[1200px] space-y-6 px-4 py-6 sm:px-6 sm:py-8">
      <header className="flex flex-col gap-1">
        <h1 className="font-display text-2xl font-bold tracking-tight">
          포트폴리오 개요
        </h1>
        <p className="text-sm text-muted-foreground">
          라이브 세션·백테스트·전략을 한눈에. 손익은 활성 세션의 실현 손익 합산
          기준입니다.
        </p>
      </header>

      {unresolvedKs > 0 ? (
        <div
          role="alert"
          className="flex items-center gap-2.5 rounded-lg border border-destructive/40 bg-destructive-subtle p-3 text-sm text-destructive"
        >
          <ShieldAlert className="h-4 w-4 shrink-0" aria-hidden="true" />
          Kill Switch 가 활성 상태입니다 — 주문이 차단됩니다.{" "}
          <Link href="/trading" className="font-semibold underline">
            트레이딩에서 확인
          </Link>
        </div>
      ) : null}

      {/* HERO — data-as-hero 실현 손익 + P&L Tape 시그니처 + ops 리스트 (하이라인 분할) */}
      <section className="qb-card-fade-in overflow-hidden rounded-xl border border-border shadow-card">
        <div className="grid gap-px bg-border md:grid-cols-[1.55fr_1fr]">
          {/* 실현 손익 hero */}
          <div className="bg-card p-5 sm:p-6">
            <div className="flex items-center justify-between">
              <span className={MICRO_LABEL}>실현 손익 · 합산</span>
              <Activity
                className={cn(
                  "size-4",
                  activeSessions.length > 0
                    ? "text-primary"
                    : "text-muted-foreground",
                )}
                aria-hidden="true"
              />
            </div>
            <p
              className={cn(
                "mt-3 font-mono text-[2.5rem] font-bold leading-none tracking-tight tabular-nums sm:text-[3rem]",
                pnlTone,
              )}
            >
              {formatUsd(agg.totalRealizedPnl)}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 font-mono text-xs text-muted-foreground">
              <HeroStat label="활성 세션" value={activeSessions.length} live={activeSessions.length > 0} />
              <HeroStat label="종료 거래" value={agg.totalClosedTrades} />
              <HeroStat label="전략" value={strategyCount} />
            </div>
            <PnlTape deltas={deltas} className="mt-5 h-8" />
          </div>

          {/* ops 상태 리스트 */}
          <div className="flex flex-col justify-center gap-px bg-border">
            <OpsRow
              icon={unresolvedKs > 0 ? <ShieldAlert className="size-4" /> : <ShieldCheck className="size-4" />}
              label="Kill Switch"
              value={unresolvedKs > 0 ? "활성" : "정상"}
              tone={unresolvedKs > 0 ? "destructive" : "success"}
            />
            <OpsRow
              icon={<Wifi className="size-4" />}
              label="연결 거래소"
              value={accounts > 0 ? `${accounts}개` : "미등록"}
              tone={accounts > 0 ? "primary" : "muted"}
            />
            <OpsRow
              icon={<Receipt className="size-4" />}
              label="미체결 주문"
              value={`${pendingOrders}건`}
              tone={pendingOrders > 0 ? "primary" : "muted"}
            />
            <OpsRow
              icon={<Code2 className="size-4" />}
              label="등록 전략"
              value={`${strategyCount}개`}
              tone="muted"
            />
          </div>
        </div>
      </section>

      {/* 합산 실현-PnL 곡선 */}
      <section
        className="qb-card-fade-in rounded-xl border border-border bg-card p-5 shadow-card"
        style={{ animationDelay: "80ms" }}
      >
        <div className="mb-3 flex items-center gap-2">
          <LineChart className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <span className={MICRO_LABEL}>합산 실현 손익 추이</span>
        </div>
        {hasEquitySeries ? (
          <TradingChart
            data={equityChartData}
            height={260}
            options={{ color: "#c2780f", lineWidth: 2 }}
            ariaLabel="활성 세션 합산 실현 손익 누적 곡선 (USDT)"
          />
        ) : agg.isLoading ? (
          <Skeleton shimmer className="h-[260px] w-full rounded-lg" />
        ) : (
          <div className="flex flex-col items-center justify-center gap-3 py-12">
            <PnlTape deltas={[]} className="h-10 w-40 opacity-50" />
            <p className="text-center text-sm text-muted-foreground">
              라이브 세션이 거래를 시작하면 합산 손익 곡선이 그려집니다.
            </p>
          </div>
        )}
      </section>

      {/* 활성 세션 + 최근 백테스트 */}
      <div
        className="qb-card-fade-in grid grid-cols-1 gap-6 lg:grid-cols-2"
        style={{ animationDelay: "160ms" }}
      >
        <WidgetSection title="활성 세션" href="/trading">
          {activeSessions.length > 0 ? (
            <LiveSessionTable
              sessions={activeSessions}
              resolveStrategyName={(id) => strategyNameById.get(id) ?? "전략"}
            />
          ) : (
            <EmptyRow>
              활성 라이브 세션이 없습니다.{" "}
              <Link href="/trading" className="font-semibold text-primary hover:underline">
                트레이딩에서 시작
              </Link>
            </EmptyRow>
          )}
        </WidgetSection>

        <WidgetSection title="최근 백테스트" href="/backtests">
          {recentBacktests.length > 0 ? (
            <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-card">
              {recentBacktests.map((b) => (
                <li key={b.id}>
                  <Link
                    href={`/backtests/${b.id}`}
                    className="flex items-center justify-between gap-3 px-4 py-3 text-sm transition-colors hover:bg-muted"
                  >
                    <span className="min-w-0 truncate font-medium text-foreground">
                      {b.symbol}{" "}
                      <span className="font-mono text-xs text-muted-foreground">
                        {b.timeframe}
                      </span>
                    </span>
                    <span className="inline-flex items-center gap-2 shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                      {formatDate(b.completed_at ?? b.created_at)}
                      <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyRow>
              아직 백테스트가 없습니다.{" "}
              <Link href="/backtests/new" className="font-semibold text-primary hover:underline">
                새 백테스트
              </Link>
            </EmptyRow>
          )}
        </WidgetSection>
      </div>
    </div>
  );
}

function HeroStat({
  label,
  value,
  live,
}: {
  label: string;
  value: number;
  live?: boolean;
}) {
  return (
    <span className="inline-flex items-center gap-1.5">
      {live ? (
        <span
          className="inline-block size-1.5 rounded-full bg-success shadow-[0_0_6px_var(--success)]"
          aria-hidden="true"
        />
      ) : null}
      {label}{" "}
      <b className="font-semibold tabular-nums text-foreground">{value}</b>
    </span>
  );
}

const OPS_TONE: Record<string, string> = {
  primary: "text-primary",
  success: "text-success",
  destructive: "text-destructive",
  muted: "text-muted-foreground",
};

function OpsRow({
  icon,
  label,
  value,
  tone,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  tone: "primary" | "success" | "destructive" | "muted";
}) {
  return (
    <div className="flex flex-1 items-center justify-between gap-3 bg-card px-5 py-3">
      <span className="inline-flex items-center gap-2">
        <span className={OPS_TONE[tone]} aria-hidden="true">
          {icon}
        </span>
        <span className={MICRO_LABEL}>{label}</span>
      </span>
      <span
        className={cn(
          "font-mono text-sm font-semibold tabular-nums",
          tone === "muted" ? "text-foreground" : OPS_TONE[tone],
        )}
      >
        {value}
      </span>
    </div>
  );
}

function WidgetSection({
  title,
  href,
  children,
}: {
  title: string;
  href: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <span className="shrink-0">
          <span className={MICRO_LABEL}>{title}</span>
        </span>
        {/* Precision Instrument 시그니처 — 섹션 경계 계측 눈금 */}
        <TickRuler className="hidden min-w-0 flex-1 opacity-60 sm:block" />
        <Link
          href={href}
          className="inline-flex shrink-0 items-center gap-1 text-xs font-semibold text-primary hover:underline"
        >
          전체 보기
          <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </div>
      {children}
    </section>
  );
}

function EmptyRow({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-border bg-card p-8 text-center text-sm text-muted-foreground">
      {children}
    </div>
  );
}
