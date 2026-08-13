// Optimizer 진입 페이지 (server) — 클라이언트 로직은 OptimizerPageView 로 위임.
import type { Metadata } from "next";

import { OptimizerPageView } from "./_components/optimizer-page-view";

// 페이지명 = "옵티마이저"(OPTIMIZER_DOMAIN_LABEL.page, terminology B8). 브랜드 접미는 root template.
export const metadata: Metadata = {
  title: "옵티마이저",
};

export default function OptimizerPage() {
  return <OptimizerPageView />;
}
