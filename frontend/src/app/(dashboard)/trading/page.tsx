// 트레이딩 페이지 — 프로토타입 03 (Full Dark App Shell) visual layout 적용.
// data-theme="dash" 는 DashboardShell 이 /trading 진입 시 자동 토글.

import { Suspense } from "react";

import type { Metadata } from "next";

import { TableSkeleton } from "@/components/skeleton";

import { KillSwitchBanner } from "./_components/kill-switch-banner";
import { TradingDashHero } from "./_components/trading-dash-hero";
import { TradingTabs } from "./_components/trading-tabs";

export const metadata: Metadata = {
  title: "Trading | QuantBridge",
};

export default function TradingPage() {
  return (
    <main className="mx-auto max-w-[1200px] space-y-6 px-6 py-8">
      {/* C-1: Kill Switch 활성 배너 (Sprint 12 Phase A 그대로) */}
      <KillSwitchBanner />

      {/* Sprint 41-B2: 프로토타입 03 KPI 스트립 — 활성 세션 / 거래소 / KS / 총 세션 */}
      <TradingDashHero />

      {/* Sprint 26: Tabs (Orders / Live Sessions). Suspense 는 useSearchParams 요구사항. */}
      <Suspense fallback={<TableSkeleton rows={6} columns={5} />}>
        <TradingTabs />
      </Suspense>
    </main>
  );
}
