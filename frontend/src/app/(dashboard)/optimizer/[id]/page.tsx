// Optimizer run 상세 페이지 (server) — params 해석 후 client 상세 컴포넌트 렌더.

import { OptimizerRunDetail } from "../_components/optimizer-run-detail";

export default async function OptimizerRunPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <main className="container mx-auto px-4 py-6">
      <OptimizerRunDetail runId={id} />
    </main>
  );
}
