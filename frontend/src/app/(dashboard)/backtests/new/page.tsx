import type { Metadata } from "next";

import { BacktestForm } from "../_components/backtest-form";

export const metadata: Metadata = {
  title: "새 백테스트 | QuantBridge",
};

export default function NewBacktestPage() {
  return (
    <div className="mx-auto max-w-[720px] px-6 py-8">
      <header className="mb-6">
        <h1 className="font-display text-2xl font-bold">새 백테스트</h1>
        <p className="text-sm text-muted-foreground">
          전략과 시장 조건을 선택해 백테스트를 실행합니다.
        </p>
      </header>

      <section className="rounded-xl border bg-card p-6">
        <BacktestForm />
      </section>
    </div>
  );
}
