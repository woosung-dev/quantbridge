"use client";

// TV "성과" 복합 차트 히어로 — equity+B&H+Compare / drawdown (기존 2-pane 승계)
// + per-trade PnL 히스토그램 pane + 접기 토글. 섹션 탭 밖 상시 노출.

import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

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
    <section className="card" aria-label="성과 차트" data-testid="performance-chart">
      <div className="card-head">
        <div>
          <h3 className="card-title">자산 곡선</h3>
          <p className="card-sub">전략 자산 곡선 · 매수 후 보유 벤치마크 · 낙폭 띠 (같은 x축)</p>
        </div>
        <div className="chart-head-actions">
          {hasTrades && !collapsed ? (
            <label className="chart-toggle">
              <input
                type="checkbox"
                checked={showTradePnl}
                onChange={(e) => setShowTradePnl(e.target.checked)}
                aria-label="거래별 PnL 바 표시"
              />
              거래 PnL
            </label>
          ) : null}
          <button
            type="button"
            className="btn btn-ghost btn-xs"
            onClick={() => setCollapsed((prev) => !prev)}
            aria-expanded={!collapsed}
            aria-label={collapsed ? "성과 차트 펼치기" : "성과 차트 접기"}
          >
            {collapsed ? (
              <ChevronDown aria-hidden="true" />
            ) : (
              <ChevronUp aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      {!collapsed ? (
        <div className="card-body chart-wrap">
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
              <p className="card-sub" style={{ marginBottom: 4 }}>
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
