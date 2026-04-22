"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";
import type { TradeItem } from "@/features/backtest/schemas";
import {
  formatCurrency,
  formatDateTime,
  formatPercent,
} from "@/features/backtest/utils";

const TRADE_LIMIT = 200;

export function TradeTable({ trades }: { trades: readonly TradeItem[] }) {
  const visible = trades.slice(0, TRADE_LIMIT);
  const truncated = trades.length > TRADE_LIMIT;

  // 누적 PnL — FE에서 reduce로 계산 (API 변경 없음, 불변 패턴)
  const tradesWithCumulative = useMemo(
    () =>
      visible.reduce<Array<TradeItem & { cumulativePnl: number }>>((acc, t) => {
        const prevCum = acc.at(-1)?.cumulativePnl ?? 0;
        return [...acc, { ...t, cumulativePnl: prevCum + t.pnl }];
      }, []),
    [visible],
  );

  if (visible.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
        기록된 거래가 없습니다
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border bg-card">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th scope="col" className="px-3 py-2 text-left">#</th>
            <th scope="col" className="px-3 py-2 text-left">방향</th>
            <th scope="col" className="px-3 py-2 text-left">Entry</th>
            <th scope="col" className="px-3 py-2 text-left">Exit</th>
            <th scope="col" className="px-3 py-2 text-right">Size</th>
            <th scope="col" className="px-3 py-2 text-right">PnL</th>
            <th scope="col" className="px-3 py-2 text-right">Return</th>
            <th scope="col" className="px-3 py-2 text-right">누적 PnL</th>
          </tr>
        </thead>
        <tbody>
          {tradesWithCumulative.map((t) => (
            <tr
              key={t.trade_index}
              className="border-t"
              data-direction={t.direction}
            >
              <td className="px-3 py-2 tabular-nums">{t.trade_index}</td>
              <td className="px-3 py-2 uppercase">
                <span data-dir={t.direction}>{t.direction}</span>
              </td>
              <td className="px-3 py-2 text-xs text-muted-foreground tabular-nums">
                {formatDateTime(t.entry_time)}
                <div className="text-foreground">
                  {formatCurrency(t.entry_price)}
                </div>
              </td>
              <td className="px-3 py-2 text-xs text-muted-foreground tabular-nums">
                {formatDateTime(t.exit_time)}
                <div className="text-foreground">
                  {t.exit_price !== null ? formatCurrency(t.exit_price) : "—"}
                </div>
              </td>
              <td className="px-3 py-2 text-right tabular-nums">
                {formatCurrency(t.size, 4)}
              </td>
              {/* PnL 색상 바 — return_pct 비례 */}
              <td className="relative overflow-hidden px-3 py-2 text-right tabular-nums">
                <div
                  className="absolute inset-y-0 right-0 opacity-15"
                  style={{
                    width: `${Math.min(Math.abs(t.return_pct) * 100, 100)}%`,
                    backgroundColor:
                      t.pnl >= 0 ? "rgb(34,197,94)" : "rgb(239,68,68)",
                  }}
                />
                <span
                  className={cn(
                    "relative",
                    t.pnl >= 0 ? "text-green-500" : "text-red-500",
                  )}
                  data-tone={t.pnl >= 0 ? "positive" : "negative"}
                >
                  {formatCurrency(t.pnl)}
                </span>
              </td>
              <td
                className="px-3 py-2 text-right tabular-nums"
                data-tone={t.return_pct >= 0 ? "positive" : "negative"}
              >
                {formatPercent(t.return_pct)}
              </td>
              <td
                className={cn(
                  "px-3 py-2 text-right font-mono tabular-nums",
                  t.cumulativePnl >= 0 ? "text-green-500" : "text-red-500",
                )}
              >
                {t.cumulativePnl >= 0 ? "+" : ""}
                {t.cumulativePnl.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {truncated ? (
        <p className="border-t bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
          최대 {TRADE_LIMIT}건만 표시됩니다. 전체 결과는 내보내기로 확인하세요.
        </p>
      ) : null}
    </div>
  );
}

export { TRADE_LIMIT };
