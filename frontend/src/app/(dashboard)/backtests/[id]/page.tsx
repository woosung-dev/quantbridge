import type { Metadata } from "next";

import { BacktestDetailView } from "@/app/(dashboard)/backtests/_components/backtest-detail-view";

export const metadata: Metadata = {
  title: "백테스트 상세 | QuantBridge",
};

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function BacktestDetailPage({ params }: PageProps) {
  const { id } = await params;
  // BacktestDetailView 가 <main className="page"> 로 C 디자인 언어 최대폭·패딩을 소유한다.
  return <BacktestDetailView id={id} />;
}
