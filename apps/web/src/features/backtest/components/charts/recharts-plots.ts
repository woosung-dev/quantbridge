// recharts plot 서브트리 5종의 단일 dynamic-import 진입점.
// 각 차트가 개별 plot 파일을 dynamic import 하면 Turbopack 이 지점마다 recharts 사본을
// 담은 청크 그룹을 만들어 355KB × N 중복이 생긴다 — 모든 plot 을 이 모듈 하나로 묶어
// dynamic import 대상을 통일하면 recharts 는 지연 청크 1벌만 생성된다.
// (범용 barrel 아님 — recharts 청크 병합 전용 seam. 여기에 non-recharts export 추가 금지.)

export { MonteCarloFanPlot } from "@/features/backtest/components/charts/monte-carlo-fan-plot";
export { WalkForwardBarPlot } from "@/features/backtest/components/charts/walk-forward-bar-plot";
export { TradeOutcomeDonutPlot } from "@/features/backtest/components/report/trade-outcome-donut-plot";
export { ProfitWaterfallPlot } from "@/features/backtest/components/report/profit-waterfall-plot";
export { PnlDistributionPlot } from "@/features/backtest/components/report/pnl-distribution-plot";
