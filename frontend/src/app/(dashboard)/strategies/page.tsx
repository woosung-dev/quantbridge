import type { Metadata } from "next";
import { StrategyList } from "./_components/strategy-list";

export const metadata: Metadata = {
  title: "전략 | QuantBridge",
};

export default function StrategiesPage() {
  return <StrategyList />;
}
