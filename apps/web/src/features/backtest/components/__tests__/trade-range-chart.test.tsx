// 거래 확장 시점의 OHLCV 조회와 구간 차트 상태를 검증한다.

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ChartMarker, ChartPoint } from "@/components/charts/trading-chart";
import type { TradeItem, TradeOhlcvResponse } from "@/features/backtest/schemas";

const mocks = vi.hoisted(() => ({
  useTradeOhlcv: vi.fn(),
  tradingChart: vi.fn(),
}));

vi.mock("@/features/backtest/hooks", () => ({
  useTradeOhlcv: mocks.useTradeOhlcv,
}));

vi.mock("@/components/charts/trading-chart", () => ({
  TradingChart: mocks.tradingChart,
}));

import { TradeDetailTable } from "@/features/backtest/components/trades/trade-detail-table";
import { TradeRangeChart } from "@/features/backtest/components/trades/trade-range-chart";

interface ChartProps {
  data: readonly ChartPoint[];
  markers?: readonly ChartMarker[];
  ariaLabel: string;
}

const BACKTEST_ID = "11111111-1111-4111-8111-111111111111";

const trade: TradeItem = {
  trade_index: 12,
  direction: "long",
  status: "closed",
  entry_time: "2026-01-01T01:00:00Z",
  exit_time: "2026-01-01T03:00:00Z",
  entry_price: 100,
  exit_price: 103,
  size: 1,
  pnl: 3,
  return_pct: 0.03,
  fees: 0.1,
  bars_in_trade: 2,
};

const response: TradeOhlcvResponse = {
  backtest_id: BACKTEST_ID,
  trade_index: 12,
  symbol: "BTC/USDT",
  timeframe: "1h",
  entry_time: trade.entry_time,
  exit_time: trade.exit_time,
  pad_bars: 4,
  stride: 1,
  truncated: false,
  bars: [
    {
      time: "2026-01-01T00:00:00Z",
      open: 99,
      high: 101,
      low: 98,
      close: 100,
      volume: 10,
    },
    {
      time: "2026-01-01T01:00:00Z",
      open: 100,
      high: 104,
      low: 99,
      close: 103,
      volume: 12,
    },
  ],
};

function queryResult(overrides: Record<string, unknown> = {}) {
  return {
    data: undefined,
    error: null,
    isError: false,
    isLoading: false,
    ...overrides,
  };
}

beforeEach(() => {
  mocks.useTradeOhlcv.mockReset();
  mocks.tradingChart.mockReset();
  mocks.tradingChart.mockImplementation((props: ChartProps) => (
    <div data-testid="mock-trading-chart" aria-label={props.ariaLabel} />
  ));
  mocks.useTradeOhlcv.mockReturnValue(queryResult({ data: response }));
});

describe("TradeRangeChart", () => {
  it("확장 전에는 조회 훅을 호출하지 않고 확장 뒤에만 마운트한다", () => {
    render(
      <TradeDetailTable
        backtestId={BACKTEST_ID}
        trades={[trade]}
        isLoading={false}
        isError={false}
        endpoint="GET /api/v1/backtests/test/trades"
        filenamePrefix="test"
      />,
    );

    expect(mocks.useTradeOhlcv).not.toHaveBeenCalled();

    fireEvent.click(screen.getByLabelText("거래 #12 상세 보기"));

    expect(mocks.useTradeOhlcv).toHaveBeenCalledWith(BACKTEST_ID, 12, {
      enabled: true,
    });
  });

  it("종가 데이터와 거래 마커를 TradingChart에 전달한다", () => {
    render(
      <TradeRangeChart
        backtestId={BACKTEST_ID}
        tradeIndex={trade.trade_index}
        trade={trade}
      />,
    );

    const props = mocks.tradingChart.mock.calls[0]?.[0] as ChartProps;
    expect(props.data).toEqual([
      { time: "2026-01-01T00:00:00Z", value: 100 },
      { time: "2026-01-01T01:00:00Z", value: 103 },
    ]);
    expect(props.markers).toHaveLength(2);
    expect(screen.getByLabelText(/12번 거래 구간의 1h 봉 가격 차트/)).toBeInTheDocument();
  });

  it("stride가 1보다 크면 표본 간격 안내를 표시한다", () => {
    mocks.useTradeOhlcv.mockReturnValue(
      queryResult({ data: { ...response, stride: 3, truncated: true } }),
    );

    render(
      <TradeRangeChart
        backtestId={BACKTEST_ID}
        tradeIndex={trade.trade_index}
        trade={trade}
      />,
    );

    expect(screen.getByText(/3봉 간격으로 표본을 표시했습니다/)).toBeInTheDocument();
  });

  it("청산 거래는 보유 봉 수를, 미청산 거래는 보유 중 라벨을 표시한다", () => {
    const { rerender } = render(
      <TradeRangeChart backtestId={BACKTEST_ID} tradeIndex={trade.trade_index} trade={trade} />,
    );
    expect(screen.getByText(/보유 2봉/)).toBeInTheDocument();

    const openTrade: TradeItem = {
      ...trade,
      status: "open",
      exit_time: null,
      exit_price: null,
      bars_in_trade: null,
    };
    mocks.useTradeOhlcv.mockReturnValue(queryResult({ data: { ...response, exit_time: null } }));
    rerender(
      <TradeRangeChart backtestId={BACKTEST_ID} tradeIndex={openTrade.trade_index} trade={openTrade} />,
    );
    expect(screen.getByText(/미청산\(보유 중\)/)).toBeInTheDocument();
    expect(screen.queryByText(/알 수 없음/)).not.toBeInTheDocument();
  });

  it("오류와 빈 봉 상태를 StateBox로 렌더링한다", () => {
    mocks.useTradeOhlcv.mockReturnValue(
      queryResult({ isError: true, error: new Error("network") }),
    );
    const { rerender } = render(
      <TradeRangeChart
        backtestId={BACKTEST_ID}
        tradeIndex={trade.trade_index}
        trade={trade}
      />,
    );
    expect(screen.getByTestId("trade-range-chart-error")).toHaveAttribute("role", "alert");

    mocks.useTradeOhlcv.mockReturnValue(queryResult({ data: { ...response, bars: [] } }));
    rerender(
      <TradeRangeChart
        backtestId={BACKTEST_ID}
        tradeIndex={trade.trade_index}
        trade={trade}
      />,
    );
    expect(screen.getByTestId("trade-range-chart-empty")).toHaveAttribute("role", "status");
  });
});
