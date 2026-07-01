// 포트폴리오 개요 코크핏 — 라이브 세션/백테스트/전략을 클라이언트 집계한 플래그십 대시보드
"use client";

import {
  Activity,
  ArrowRight,
  Code2,
  LineChart,
  ListChecks,
  ShieldAlert,
  TrendingUp,
  Wifi,
} from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { TradingChart } from "@/components/charts/trading-chart";
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

import { LiveSessionTable } from "../../trading/_components/live-session-table";
import { CockpitKpiCard } from "./cockpit-kpi-card";
import { PnlTape } from "./pnl-tape";

function formatUsd(n: number): string {
  const sign = n > 0 ? "+" : n < 0 ? "-" : "";
  return `${sign}$${Math.abs(n).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

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
      ? "bullish"
      : agg.totalRealizedPnl < 0
        ? "bearish"
        : "neutral";

  // 병합 누적 곡선 → 구간 델타(Tape).
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

  // 전략 id → name (세션 테이블 표시용).
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

      {/* KPI 스트립 — P&L Tape 시그니처 */}
      <section
        aria-label="포트폴리오 KPI"
        className="grid grid-cols-2 gap-3 lg:grid-cols-3"
      >
        <CockpitKpiCard
          label="실현 손익 (합산)"
          value={formatUsd(agg.totalRealizedPnl)}
          tone={pnlTone}
          icon={<TrendingUp className="size-4" />}
          sublabel={`활성 세션 ${activeSessions.length}개 기준`}
          footer={<PnlTape deltas={deltas} />}
          className="col-span-2 lg:col-span-1"
        />
        <CockpitKpiCard
          label="활성 세션"
          value={activeSessions.length}
          tone="primary"
          icon={<Activity className="size-4" />}
          sublabel={activeSessions.length > 0 ? "자동 실행 중" : "대기 중"}
          live={activeSessions.length > 0}
        />
        <CockpitKpiCard
          label="종료 거래"
          value={agg.totalClosedTrades}
          tone="neutral"
          icon={<ListChecks className="size-4" />}
          sublabel="누적 청산 거래"
        />
        <CockpitKpiCard
          label="전략"
          value={strategyCount}
          tone="neutral"
          icon={<Code2 className="size-4" />}
          sublabel="등록된 전략"
        />
        <CockpitKpiCard
          label="연결 거래소"
          value={accounts}
          tone="primary"
          icon={<Wifi className="size-4" />}
          sublabel={accounts > 0 ? "API 연결 정상" : "API Key 미등록"}
        />
        <CockpitKpiCard
          label="미체결 주문"
          value={pendingOrders}
          tone={pendingOrders > 0 ? "primary" : "neutral"}
          icon={<ListChecks className="size-4" />}
          sublabel="대기·전송 중"
        />
      </section>

      {/* 합산 실현-PnL 곡선 */}
      <section className="rounded-xl border border-border bg-card p-4 shadow-card">
        <div className="mb-3 flex items-center gap-2">
          <LineChart className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          <h2 className="text-sm font-medium">합산 실현 손익 추이</h2>
        </div>
        {hasEquitySeries ? (
          <TradingChart
            data={equityChartData}
            height={260}
            options={{ color: "#c2780f", lineWidth: 2 }}
            ariaLabel="활성 세션 합산 실현 손익 누적 곡선 (USDT)"
          />
        ) : (
          <p className="py-10 text-center text-sm text-muted-foreground">
            {agg.isLoading
              ? "불러오는 중…"
              : "아직 표시할 실현 손익 추이가 없습니다. 라이브 세션이 거래를 시작하면 곡선이 그려집니다."}
          </p>
        )}
      </section>

      {/* 활성 세션 + 최근 백테스트 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium">활성 세션</h2>
            <Link
              href="/trading"
              className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
            >
              전체 보기
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          </div>
          {activeSessions.length > 0 ? (
            <LiveSessionTable
              sessions={activeSessions}
              resolveStrategyName={(id) => strategyNameById.get(id) ?? "전략"}
            />
          ) : (
            <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
              활성 라이브 세션이 없습니다.{" "}
              <Link href="/trading" className="font-semibold text-primary hover:underline">
                트레이딩에서 시작
              </Link>
            </div>
          )}
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium">최근 백테스트</h2>
            <Link
              href="/backtests"
              className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
            >
              전체 보기
              <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          </div>
          {recentBacktests.length > 0 ? (
            <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-card">
              {recentBacktests.map((b) => (
                <li key={b.id}>
                  <Link
                    href={`/backtests/${b.id}`}
                    className="flex items-center justify-between gap-3 px-4 py-3 text-sm transition-colors hover:bg-muted"
                  >
                    <span className="min-w-0 truncate font-medium text-foreground">
                      {b.symbol} · {b.timeframe}
                    </span>
                    <span className="shrink-0 font-mono text-xs tabular-nums text-muted-foreground">
                      {formatDate(b.completed_at ?? b.created_at)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
              아직 백테스트가 없습니다.{" "}
              <Link href="/backtests/new" className="font-semibold text-primary hover:underline">
                새 백테스트
              </Link>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
