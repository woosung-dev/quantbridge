import type { Metadata } from "next";

import { SharedBacktestPage } from "@/features/backtest/components/share/shared-backtest-page";

export const dynamic = "force-dynamic"; // 토큰 lookup → revoke 즉시 반영

interface PageProps {
  params: Promise<{ token: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { token } = await params;
  return {
    title: "백테스트 결과 공유",
    description: "QuantBridge 에서 만든 백테스트 결과 — 데모 트레이딩 무료 시작",
    openGraph: {
      title: "백테스트 결과 · QuantBridge",
      description: "QuantBridge 백테스트 결과를 확인하세요",
      images: [`/share/backtests/${token}/opengraph-image`],
    },
  };
}

export default async function SharedBacktestRoute({ params }: PageProps) {
  const { token } = await params;
  return await SharedBacktestPage({ token });
}
