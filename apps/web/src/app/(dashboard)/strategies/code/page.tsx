import type { Metadata } from "next";

import { CodeWorkspace } from "@/features/strategy/components/code-workspace";

export const metadata: Metadata = { title: "코드 전략" };

export default function CodeStrategiesPage() {
  return <CodeWorkspace />;
}
