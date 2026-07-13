"use client";

// TV "성과" 복합 차트 히어로 — equity+B&H+Compare / drawdown (기존 2-pane 승계)
// + per-trade PnL 히스토그램 pane + 접기 토글. 섹션 탭 밖 상시 노출.

import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { EquityPoint, TradeItem } from "@/features/backtest/schemas";

import { EquityChartWithCompare } from "@/app/(dashboard)/backtests/_components/charts/equity-chart-with-compare";
import { TradePnlPane } from "@/app/(dashboard)/backtests/_components/report/trade-pnl-pane";

interface PerformanceChartProps {
  currentId: string;
  equityCurve: readonly EquityPoint[];
  trades?: readonly TradeItem[];
  initialCapital: number;
  timeframe: string;
  mddExceedsCapital?: boolean | null;
  buyAndHoldCurve?: readonly EquityPoint[] | null;
}

const TRADE_PNL_PANE_HEIGHT = 120;

export function PerformanceChart({
  currentId,
  equityCurve,
  trades,
  initialCapital,
  timeframe,
  mddExceedsCapital,
  buyAndHoldCurve,
}: PerformanceChartProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [showTradePnl, setShowTradePnl] = useState(true);

  const hasTrades = (trades?.length ?? 0) > 0;

  return (
    <section
      className="rounded-lg border bg-card shadow-[var(--card-shadow)]"
      aria-label="성과 차트"
      data-testid="performance-chart"
    >
      <div className="flex items-center justify-between border-b border-[color:var(--border)] px-4 py-2">
        <h2 className="text-sm font-semibold">성과</h2>
        <div className="flex items-center gap-3">
          {hasTrades && !collapsed ? (
            <label className="inline-flex items-center gap-2 text-xs text-[color:var(--text-secondary)] select-none">
              <input
                type="checkbox"
                checked={showTradePnl}
                onChange={(e) => setShowTradePnl(e.target.checked)}
                className="h-4 w-4 cursor-pointer accent-[color:var(--primary)]"
                aria-label="거래별 PnL 바 표시"
              />
              거래 PnL
            </label>
          ) : null}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setCollapsed((prev) => !prev)}
            aria-expanded={!collapsed}
            aria-label={collapsed ? "성과 차트 펼치기" : "성과 차트 접기"}
          >
            {collapsed ? (
              <ChevronDown className="h-4 w-4" aria-hidden="true" />
            ) : (
              <ChevronUp className="h-4 w-4" aria-hidden="true" />
            )}
          </Button>
        </div>
      </div>

      {!collapsed ? (
        <div className="space-y-3 p-4">
          <EquityChartWithCompare
            currentId={currentId}
            equityCurve={equityCurve}
            trades={trades}
            initialCapital={initialCapital}
            timeframe={timeframe}
            mddExceedsCapital={mddExceedsCapital}
            buyAndHoldCurve={buyAndHoldCurve}
          />
          {hasTrades && showTradePnl ? (
            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">
                거래별 순손익 (USDT)
              </p>
              <TradePnlPane trades={trades ?? []} height={TRADE_PNL_PANE_HEIGHT} />
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
