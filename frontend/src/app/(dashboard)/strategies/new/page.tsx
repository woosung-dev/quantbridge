// 전략 생성 페이지 (server) — C 이식(screen-07) 단일 페이지 폼은 NewStrategyWizard 로 위임.

import type { Metadata } from "next";

import { NewStrategyWizard } from "./_components/new-strategy-wizard";

export const metadata: Metadata = {
  title: "새 전략 | QuantBridge",
};

export default function NewStrategyPage() {
  return <NewStrategyWizard />;
}
