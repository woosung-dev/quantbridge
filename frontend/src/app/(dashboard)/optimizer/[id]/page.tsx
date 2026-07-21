// Optimizer run 상세 페이지 (server) — params 해석 후 client 상세 컴포넌트 렌더.

import { OptimizerRunDetail } from "../_components/optimizer-run-detail";

export default async function OptimizerRunPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  // OptimizerRunDetail 이 <main className="page"> 셸을 직접 렌더한다(C 이식). 여기서 감싸지 않는다.
  return <OptimizerRunDetail runId={id} />;
}
