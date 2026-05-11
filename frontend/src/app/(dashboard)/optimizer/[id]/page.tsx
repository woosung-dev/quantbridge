// Sprint 54 — Optimizer run 상세 페이지.
"use client";

import { use } from "react";

import { OptimizerRunDetail } from "../_components/optimizer-run-detail";

export default function OptimizerRunPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return (
    <main className="container mx-auto px-4 py-6">
      <OptimizerRunDetail runId={id} />
    </main>
  );
}
