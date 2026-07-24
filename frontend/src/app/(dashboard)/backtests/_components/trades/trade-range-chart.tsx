// 거래 확장 행의 OHLCV 구간 가격 차트를 렌더링한다.
"use client";

import { AlertTriangleIcon, InboxIcon, LoaderCircleIcon } from "lucide-react";

import { TradingChart } from "@/components/charts/trading-chart";
import { StateBox } from "@/components/state-box";
import { useTradeOhlcv } from "@/features/backtest/hooks";
import type { TradeItem } from "@/features/backtest/schemas";
import { formatCurrency, formatDateTime } from "@/features/backtest/utils";
import { resolveChartTokens } from "@/lib/chart-tokens";

import { deriveTradeMarkers } from "@/app/(dashboard)/backtests/_components/charts/marker-layer";

interface TradeRangeChartProps {
  backtestId: string;
  tradeIndex: number;
  trade: TradeItem;
}

export function TradeRangeChart({
  backtestId,
  tradeIndex,
  trade,
}: TradeRangeChartProps) {
  const ohlcv = useTradeOhlcv(backtestId, tradeIndex, { enabled: true });

  if (ohlcv.isLoading) {
    return (
      <section className="card" data-testid="trade-range-chart">
        <div className="card-body">
          <StateBox
            testId="trade-range-chart-loading"
            icon={<LoaderCircleIcon />}
            title="거래 구간 가격을 불러오는 중입니다."
          />
        </div>
      </section>
    );
  }

  if (ohlcv.isError) {
    return (
      <section className="card" data-testid="trade-range-chart">
        <div className="card-body">
          <StateBox
            tone="failed"
            testId="trade-range-chart-error"
            icon={<AlertTriangleIcon />}
            title="거래 구간 가격을 불러오지 못했습니다."
            body={ohlcv.error.message}
            code={`GET /api/v1/backtests/${backtestId}/trades/${tradeIndex}/ohlcv`}
          />
        </div>
      </section>
    );
  }

  const data = ohlcv.data;
  if (data === undefined || data.bars.length === 0) {
    return (
      <section className="card" data-testid="trade-range-chart">
        <div className="card-body">
          <StateBox
            testId="trade-range-chart-empty"
            icon={<InboxIcon />}
            title="표시할 거래 구간 가격이 없습니다."
            body="이 거래 기간에 저장된 OHLCV 봉이 없습니다."
          />
        </div>
      </section>
    );
  }

  const entryTime = formatDateTime(data.entry_time);
  const entryPrice = formatCurrency(trade.entry_price);
  const ariaLabel = data.exit_time && trade.exit_price !== null
    ? `${trade.trade_index}번 거래 구간의 ${data.timeframe} 봉 가격 차트. ${entryTime}에 ${entryPrice}에 진입해 ${formatDateTime(data.exit_time)}에 ${formatCurrency(trade.exit_price)}에 청산했습니다.`
    : `${trade.trade_index}번 거래 구간의 ${data.timeframe} 봉 가격 차트. ${entryTime}에 ${entryPrice}에 진입한 뒤 아직 청산하지 않았습니다.`;
  const holdBars = trade.bars_in_trade ?? "알 수 없음";
  const samplingNote = data.stride > 1
    ? ` ${data.stride}봉 간격으로 표본을 표시했습니다.`
    : "";

  return (
    <section className="card" data-testid="trade-range-chart">
      <div className="card-head">
        <div>
          <h3 className="card-title">구간 가격</h3>
          <p className="card-sub">
            보유 {holdBars}봉 + 앞뒤 {data.pad_bars}봉 · {data.timeframe} 봉 {data.bars.length}개
            {samplingNote}
          </p>
        </div>
      </div>
      <div className="card-body chart-wrap">
        <TradingChart
          data={data.bars.map((bar) => ({ time: bar.time, value: bar.close }))}
          markers={deriveTradeMarkers([trade])}
          options={{ color: resolveChartTokens().equity }}
          height={200}
          ariaLabel={ariaLabel}
        />
        <p className="card-sub">종가만 선으로 표시합니다.</p>
      </div>
    </section>
  );
}
