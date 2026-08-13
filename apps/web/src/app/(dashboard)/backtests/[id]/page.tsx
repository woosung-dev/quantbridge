// 백테스트 상세 페이지 (/backtests/[id], Server Component) — params 에서 id 를 추출해
// BacktestDetailView 에 전달만 하는 얇은 라우트 엔트리 (레이아웃은 하위 컴포넌트가 소유).
import type { Metadata } from "next";

import { BacktestDetailView } from "@/app/(dashboard)/backtests/_components/backtest-detail-view";

export const metadata: Metadata = {
  title: "백테스트 상세",
};

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function BacktestDetailPage({ params }: PageProps) {
  const { id } = await params;
  // BacktestDetailView 가 <main className="page"> 로 C 디자인 언어 최대폭·패딩을 소유한다.
  return <BacktestDetailView id={id} />;
}
