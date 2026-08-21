// 거래 확장 행의 OHLCV 구간 가격 차트를 렌더링한다.
"use client";

import { useMemo } from "react";

import { AlertTriangleIcon, InboxIcon, LoaderCircleIcon } from "lucide-react";

import { TradingChart } from "@/components/charts/trading-chart";
import { StateBox } from "@/components/state-box";
import { useTradeOhlcv } from "@/features/backtest/hooks";
import type { TradeItem } from "@/features/backtest/schemas";
import { formatCurrency, formatDateTime } from "@/features/backtest/utils";
import { resolveChartTokens } from "@/lib/chart-tokens";

import { deriveTradeMarkers } from "@/features/backtest/components/charts/marker-layer";

interface TradeRangeChartProps {
  backtestId: string;
  tradeIndex: number;
  trade: TradeItem;
}

export function TradeRangeChart({ backtestId, tradeIndex, trade }: TradeRangeChartProps) {
  const ohlcv = useTradeOhlcv(backtestId, tradeIndex, { enabled: true });

  // TradingChart 는 data/markers/options 참조 안정성을 요구한다(그 doc-comment). 인라인 생성 시
  // 부모(TradeDetailTable) 재렌더마다 syncSeries+getComputedStyle 이 재실행되므로 memoize 한다.
  const bars = ohlcv.data?.bars;
  const chartData = useMemo(
    () => (bars ?? []).map((bar) => ({ time: bar.time, value: bar.close })),
    [bars],
  );
  const chartMarkers = useMemo(() => deriveTradeMarkers([trade]), [trade]);
  const chartOptions = useMemo(() => ({ color: resolveChartTokens().equity }), []);

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
  const ariaLabel =
    data.exit_time && trade.exit_price !== null
      ? `${trade.trade_index}번 거래 구간의 ${data.timeframe} 봉 가격 차트. ${entryTime}에 ${entryPrice}에 진입해 ${formatDateTime(data.exit_time)}에 ${formatCurrency(trade.exit_price)}에 청산했습니다.`
      : `${trade.trade_index}번 거래 구간의 ${data.timeframe} 봉 가격 차트. ${entryTime}에 ${entryPrice}에 진입한 뒤 아직 청산하지 않았습니다.`;
  // 청산된 거래는 보유 봉 수, 미청산(open) 거래는 bars_in_trade 가 null 이므로 "보유 중" 으로 표기.
  const holdLabel =
    trade.bars_in_trade != null ? `보유 ${trade.bars_in_trade}봉` : "미청산(보유 중)";
  const samplingNote = data.stride > 1 ? ` ${data.stride}봉 간격으로 표본을 표시했습니다.` : "";

  return (
    <section className="card" data-testid="trade-range-chart">
      <div className="card-head">
        <div>
          <h3 className="card-title">구간 가격</h3>
          <p className="card-sub">
            {holdLabel} + 앞뒤 {data.pad_bars}봉 · {data.timeframe} 봉 {data.bars.length}개
            {samplingNote}
          </p>
        </div>
      </div>
      <div className="card-body chart-wrap">
        <TradingChart
          data={chartData}
          markers={chartMarkers}
          options={chartOptions}
          height={200}
          ariaLabel={ariaLabel}
        />
        <p className="card-sub">종가만 선으로 표시합니다.</p>
      </div>
    </section>
  );
}
