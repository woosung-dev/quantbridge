import type { Metadata } from "next";

import { BacktestDetailView } from "../_components/backtest-detail-view";

export const metadata: Metadata = {
  title: "백테스트 상세 | QuantBridge",
};

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function BacktestDetailPage({ params }: PageProps) {
  const { id } = await params;
  return (
    <div className="mx-auto max-w-[1080px] px-6 py-8">
      <BacktestDetailView id={id} />
    </div>
  );
}
