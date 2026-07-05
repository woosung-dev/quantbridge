// Optimizer 진입 페이지 (server) — 클라이언트 로직은 OptimizerPageView 로 위임.

import { OptimizerPageView } from "./_components/optimizer-page-view";

export default function OptimizerPage() {
  return <OptimizerPageView />;
}
