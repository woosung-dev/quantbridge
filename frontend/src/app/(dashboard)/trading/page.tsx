import type { Metadata } from "next";
import {
  ExchangeAccountsPanel,
  KillSwitchPanel,
  OrdersPanel,
} from "@/features/trading";
import { KillSwitchBanner } from "./_components/kill-switch-banner";

export const metadata: Metadata = {
  title: "Trading | QuantBridge",
};

export default function TradingPage() {
  return (
    <main className="p-6 space-y-4 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold">Trading</h1>
      {/* C-1: Kill Switch 활성 배너 — KillSwitchBanner는 Client Component */}
      <KillSwitchBanner />
      <KillSwitchPanel />
      <OrdersPanel />
      <ExchangeAccountsPanel />
    </main>
  );
}
