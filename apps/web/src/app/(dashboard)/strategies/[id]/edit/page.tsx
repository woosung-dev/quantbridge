// Sprint 7c T5: /strategies/[id]/edit Server Component.
// UUID 포맷을 검증하여 잘못된 URL은 즉시 404 — 백엔드 라운드트립 전 early return.

import type { Metadata } from "next";

import { notFound } from "next/navigation";

import { EditorView } from "@/features/strategy/components/edit/editor-view";

// h1 은 전략 이름이라 동적이다 — <title> 은 형제 라우트("새 전략")와 같은 결의 정적 라벨을 쓴다.
export const metadata: Metadata = {
  title: "전략 편집",
};

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
