"use client";

import Link from "next/link";

import type { BacktestDetail } from "@/features/backtest/schemas";
import { useCodeResultStrategy } from "@/features/strategy/use-code-result-strategy";
import { useStrategy } from "@/features/strategy/hooks";

type Props = { backtest: BacktestDetail; testId: string };

export function BacktestStrategyLink({ backtest, testId }: Props) {
  return backtest.config?.execution_policy === "code_v1" ||
    backtest.config?.execution_policy === "code_research_v1" ? (
    <CodeStrategyLink id={backtest.strategy_id} testId={testId} />
  ) : (
    <LegacyStrategyLink id={backtest.strategy_id} testId={testId} />
  );
}

function LegacyStrategyLink({ id, testId }: { id: string; testId: string }) {
  const strategy = useStrategy(id);
  return (
    <StrategyLink
      id={id}
      testId={testId}
      name={strategy.data?.name}
      href={`/strategies/${id}/edit`}
    />
  );
}

function CodeStrategyLink({ id, testId }: { id: string; testId: string }) {
  const strategy = useCodeResultStrategy(id);
  return (
    <StrategyLink
      id={id}
      testId={testId}
      name={strategy.data?.name}
      href={`/strategies/code?strategy=${id}`}
    />
  );
}

function StrategyLink({
  id,
  testId,
  name,
  href,
}: {
  id: string;
  testId: string;
  name?: string;
  href: string;
}) {
  return (
    <Link className="chip" href={href} title="전략 편집기로 이동" data-testid={testId}>
      {name ?? `전략 ${id.slice(0, 8)}`}
    </Link>
  );
}
