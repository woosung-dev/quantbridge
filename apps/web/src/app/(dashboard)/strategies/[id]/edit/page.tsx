// Sprint 7c T5: /strategies/[id]/edit Server Component.
// UUID 포맷을 검증하여 잘못된 URL은 즉시 404 — 백엔드 라운드트립 전 early return.

import { notFound } from "next/navigation";

import { EditorView } from "./_components/editor-view";

export default async function StrategyEditPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  // UUID 포맷 검증 — 잘못된 URL은 즉시 404.
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) {
    notFound();
  }
  return <EditorView id={id} />;
}
