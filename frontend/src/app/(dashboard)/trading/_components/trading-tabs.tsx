"use client";

// Sprint 26 — Trading 탭 wrapper (Orders / Live Sessions).
//
// URL sync: ?tab=orders | live-sessions. 미지정 → "orders" 기본.
// router.replace() 로 history pollution 방지 (Sprint 13 TabWebhook 패턴 미러).
//
// Live Sessions tab content 는 Client 측에서 strategies / exchange-accounts /
// live-sessions data fetch 후 LiveSessionForm props 전달.

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";

import {
  ExchangeAccountsPanel,
  KillSwitchPanel,
  OrdersPanel,
  useExchangeAccounts,
} from "@/features/trading";
import {
  LiveSessionDetail,
  LiveSessionForm,
  LiveSessionList,
  useLiveSessions,
  type LiveSession,
} from "@/features/live-sessions";
import { useStrategies } from "@/features/strategy/hooks";

const TAB_VALUES = ["orders", "live-sessions"] as const;
type TabValue = (typeof TAB_VALUES)[number];

function isTabValue(v: string | null): v is TabValue {
  return TAB_VALUES.includes(v as TabValue);
}

export function TradingTabs() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const activeTab: TabValue = isTabValue(tabParam) ? tabParam : "orders";

  const handleTabChange = (value: string) => {
    if (!isTabValue(value)) return;
    const params = new URLSearchParams(Array.from(searchParams.entries()));
    params.set("tab", value);
    router.replace(`?${params.toString()}`, { scroll: false });
  };

  return (
    <Tabs value={activeTab} onValueChange={handleTabChange}>
      <TabsList>
        <TabsTrigger value="orders">Orders</TabsTrigger>
        <TabsTrigger value="live-sessions" data-testid="tab-live-sessions">
          Live Sessions
        </TabsTrigger>
      </TabsList>

      <TabsContent value="orders" className="mt-4 space-y-4">
        <KillSwitchPanel />
        <OrdersPanel />
        <ExchangeAccountsPanel />
      </TabsContent>

      <TabsContent value="live-sessions" className="mt-4 space-y-4">
        <LiveSessionsTabContent />
      </TabsContent>
    </Tabs>
  );
}

// ── Live Sessions tab content ───────────────────────────────────────────

function LiveSessionsTabContent() {
  const { data: strategiesData } = useStrategies({
    limit: 100,
    offset: 0,
    is_archived: false,
  });
  const { data: accountsData } = useExchangeAccounts();
  const { data: sessionsData } = useLiveSessions();
  const [selected, setSelected] = useState<LiveSession | null>(null);

  const strategies = (strategiesData?.items ?? []).map((s) => ({
    id: s.id,
    name: s.name,
  }));
  const accounts = (accountsData ?? []).map((a) => ({
    id: a.id,
    exchange: a.exchange,
    mode: a.mode,
    label: a.label,
  }));
  const activeCount = (sessionsData?.items ?? []).filter(
    (s) => s.is_active,
  ).length;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="space-y-4">
        <LiveSessionForm
          strategies={strategies}
          exchangeAccounts={accounts}
          activeSessionsCount={activeCount}
          onSuccess={(s) => setSelected(s)}
        />
        <LiveSessionList
          onSelect={setSelected}
          selectedId={selected?.id ?? null}
        />
      </div>
      <div>
        {selected ? (
          <LiveSessionDetail session={selected} />
        ) : (
          <p className="text-sm text-muted-foreground">
            Live Session 을 선택하면 상세 정보가 표시됩니다.
          </p>
        )}
      </div>
    </div>
  );
}
