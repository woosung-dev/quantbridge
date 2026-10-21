import type { Metadata } from "next";

import { CodeWorkspace } from "@/features/strategy/components/code-workspace";

export const metadata: Metadata = { title: "코드 전략" };

export default async function CodeStrategiesPage({
  searchParams,
}: {
  searchParams: Promise<{ strategy?: string | string[] }>;
}) {
  const { strategy } = await searchParams;
  return <CodeWorkspace initialStrategyId={typeof strategy === "string" ? strategy : undefined} />;
}
