// Sprint 43 W11 — /backtests/[id]/trades 거래 내역 상세 page (App Shell + UUID 검증).
// 인증 보호는 (dashboard) route group + proxy.ts clerkMiddleware가 자동 처리.
// 잘못된 UUID 시 즉시 notFound() — BE 라운드트립 전 early return.

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import {
  TradeDetailShell,
  TradeDetailSkeleton,
} from "@/features/backtest/components/trades/trade-detail-shell";

export const metadata: Metadata = {
  title: "거래 내역",
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
  // shell 이 <main className="page"> 로 레이아웃을 소유한다. Suspense fallback 과
  // shell isLoading 이 동일 스켈레톤을 공유한다(중복 로딩 마크업 통합, S6).
  return (
    <Suspense fallback={<TradeDetailSkeleton />}>
      <TradeDetailShell id={id} />
    </Suspense>
  );
}
