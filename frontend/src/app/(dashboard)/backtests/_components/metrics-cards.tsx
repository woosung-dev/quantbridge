import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BacktestMetricsOut } from "@/features/backtest/schemas";
import { formatPercent } from "@/features/backtest/utils";

export function MetricsCards({ metrics }: { metrics: BacktestMetricsOut }) {
  const items = [
    {
      label: "총 수익률",
      value: formatPercent(metrics.total_return),
      tone: metrics.total_return >= 0 ? "positive" : "negative",
    },
    {
      label: "Sharpe Ratio",
      value: Number.isFinite(metrics.sharpe_ratio)
        ? metrics.sharpe_ratio.toFixed(2)
        : "—",
      tone: "neutral",
    },
    {
      label: "Max Drawdown",
      value: formatPercent(metrics.max_drawdown),
      tone: "negative",
    },
    {
      label: "승률 · 거래",
      value: `${formatPercent(metrics.win_rate)} · ${metrics.num_trades}`,
      tone: "neutral",
    },
  ] as const;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {items.map((it) => (
        <Card key={it.label} size="sm">
          <CardHeader>
            <CardTitle className="text-xs font-normal text-muted-foreground">
              {it.label}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className="text-2xl font-semibold tabular-nums"
              data-tone={it.tone}
            >
              {it.value}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
