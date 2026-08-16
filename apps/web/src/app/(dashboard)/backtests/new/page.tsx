// 새 백테스트 실행 페이지 (server) — C 이식(screen-05). 전체 폼 셸은 BacktestForm 이 렌더한다.

import type { Metadata } from "next";

import { BacktestForm } from "@/features/backtest/components/forms/backtest-form";

export const metadata: Metadata = {
  title: "새 백테스트",
};

export default function NewBacktestPage() {
  return <BacktestForm />;
}
