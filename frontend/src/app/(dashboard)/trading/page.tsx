import { Suspense } from "react";

import type { Metadata } from "next";

import { KillSwitchBanner } from "./_components/kill-switch-banner";
import { TradingTabs } from "./_components/trading-tabs";

export const metadata: Metadata = {
  title: "Trading | QuantBridge",
};

export default function TradingPage() {
  return (
    <main className="p-6 space-y-4 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold">Trading</h1>
      {/* C-1: Kill Switch 활성 배너 — Client Component */}
      <KillSwitchBanner />
      {/* Sprint 26: Tabs (Orders / Live Sessions). Suspense 는 useSearchParams 요구사항. */}
      <Suspense fallback={null}>
        <TradingTabs />
      </Suspense>
    </main>
  );
}
