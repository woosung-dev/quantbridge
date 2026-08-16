// Optimizer run 상세 페이지 (server) — params 해석 후 client 상세 컴포넌트 렌더.
import type { Metadata } from "next";

import { OptimizerRunDetail } from "@/features/optimizer/components/optimizer-run-detail";

// 최적화 실행 개요 화면. 브랜드 접미는 root template 이 붙인다.
export const metadata: Metadata = {
  title: "최적화 실행 상세",
};

export default async function OptimizerRunPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  // OptimizerRunDetail 이 <main className="page"> 셸을 직접 렌더한다(C 이식). 여기서 감싸지 않는다.
  return <OptimizerRunDetail runId={id} />;
}
