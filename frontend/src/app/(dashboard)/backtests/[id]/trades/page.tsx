// Sprint 43 W11 — /backtests/[id]/trades 거래 내역 상세 page (App Shell + UUID 검증).
// 인증 보호는 (dashboard) route group + proxy.ts clerkMiddleware가 자동 처리.
// 잘못된 UUID 시 즉시 notFound() — BE 라운드트립 전 early return.

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { TradeDetailShell } from "../../_components/trade-detail-shell";

export const metadata: Metadata = {
  title: "거래 내역 | QuantBridge",
};

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function BacktestTradesPage({ params }: PageProps) {
  const { id } = await params;
  if (!UUID_REGEX.test(id)) {
    notFound();
  }
  return (
    <div className="mx-auto max-w-[1400px] px-6 py-8">
      <Suspense
        fallback={
          <p className="py-12 text-center text-sm text-muted-foreground">
            불러오는 중…
          </p>
        }
      >
        <TradeDetailShell id={id} />
      </Suspense>
    </div>
  );
}
