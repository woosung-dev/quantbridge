## T1 — 검증 매트릭스 (analyze_coverage)

| 스크립트                       | Track | Runnable | Degraded                               | Unsupported                                                  |
| ------------------------------ | ----- | -------- | -------------------------------------- | ------------------------------------------------------------ |
| DrFXGOD_indicator_hard.pine    | A     | ❌       | request.security, timeframe.period     | request.security_lower_tf, ta.alma, ta.dmi, ticker.new, time |
| DrFX_strategy_quantbridge.pine | S     | ✅       | —                                      | —                                                            |
| LuxAlgo_indicator_medium.pine  | A     | ✅       | —                                      | —                                                            |
| PbR_strategy_easy.pine         | S     | ✅       | —                                      | —                                                            |
| RsiD_strategy_hard.pine        | S     | ✅       | —                                      | —                                                            |
| UtBot_indicator_easy.pine      | A     | ✅       | heikinashi, security, timeframe.period | —                                                            |
| UtBot_strategy_medium.pine     | S     | ✅       | heikinashi, security, timeframe.period | —                                                            |
| bs_indicator_medium.pine       | A     | ✅       | —                                      | —                                                            |

## T2 — 2024 / 1h 성과

| 스크립트                       | 상태                | 실행(s) | Trades | Return   | CAGR    | Sharpe | Sortino | MDD      | WinRate | PF   | AvgHold(h) | MaxConsecLoss | Fees     | Slip     |
| ------------------------------ | ------------------- | ------- | ------ | -------- | ------- | ------ | ------- | -------- | ------- | ---- | ---------- | ------------- | -------- | -------- |
| DrFXGOD_indicator_hard.pine    | skipped_unsupported | —       | —      | —        | —       | —      | —       | —        | —       | —    | —          | —             | —        | —        |
| DrFX_strategy_quantbridge.pine | ok                  | 4.9     | 142    | -46.54%  | -46.48% | -0.56  | -0.46   | -59.91%  | 32.39%  | 0.77 | 61.51      | 9             | 2313.69  | 1156.85  |
| LuxAlgo_indicator_medium.pine  | ok                  | 3.2     | 0      | 0.00%    | 0.00%   | 0.00   | —       | 0.00%    | 0.00%   | —    | —          | —             | 0.00     | 0.00     |
| PbR_strategy_easy.pine         | ok                  | 3.3     | 949    | -366.01% | —       | -1.18  | -0.15   | -351.49% | 41.41%  | 0.69 | 9.23       | 11            | 33242.02 | 16621.01 |
| RsiD_strategy_hard.pine        | ok                  | 10.1    | 133    | -411.96% | —       | 0.50   | 2.65    | -219.16% | 43.61%  | 0.81 | 37.64      | 8             | 35480.94 | 17740.47 |
| UtBot_indicator_easy.pine      | ok                  | 4.6     | 916    | -318.93% | —       | 0.97   | 0.51    | -318.30% | 27.84%  | 0.59 | 9.54       | 14            | 19913.03 | 9956.51  |
| UtBot_strategy_medium.pine     | ok                  | 6.0     | 916    | -318.97% | —       | 0.65   | 0.51    | -318.35% | 27.84%  | 0.59 | 9.54       | 14            | 19915.78 | 9957.89  |
| bs_indicator_medium.pine       | ok                  | 16.4    | 599    | -168.58% | —       | 0.36   | -0.25   | -168.49% | 21.70%  | 0.56 | 14.59      | 19            | 8580.40  | 4290.20  |

## T3 — 2024 / 4h 성과

| 스크립트                       | 상태                | 실행(s) | Trades | Return  | CAGR    | Sharpe | Sortino | MDD      | WinRate | PF   | AvgHold(h) | MaxConsecLoss | Fees    | Slip    |
| ------------------------------ | ------------------- | ------- | ------ | ------- | ------- | ------ | ------- | -------- | ------- | ---- | ---------- | ------------- | ------- | ------- |
| DrFXGOD_indicator_hard.pine    | skipped_unsupported | —       | —      | —       | —       | —      | —       | —        | —       | —    | —          | —             | —       | —       |
| DrFX_strategy_quantbridge.pine | ok                  | 1.4     | 35     | -17.75% | -17.73% | -0.09  | -0.08   | -55.66%  | 40.00%  | 0.82 | 236.69     | 6             | 717.78  | 358.89  |
| LuxAlgo_indicator_medium.pine  | ok                  | 1.0     | 0      | 0.00%   | 0.00%   | 0.00   | —       | 0.00%    | 0.00%   | —    | —          | —             | 0.00    | 0.00    |
| PbR_strategy_easy.pine         | ok                  | 0.8     | 251    | 113.39% | 113.13% | 1.43   | 1.04    | -32.01%  | 58.57%  | 1.24 | 34.73      | 4             | 9336.14 | 4668.07 |
| RsiD_strategy_hard.pine        | ok                  | 3.7     | 23     | 244.34% | 243.66% | -0.09  | 1.03    | -105.44% | 56.52%  | 1.76 | 122.96     | 2             | 6516.55 | 3258.27 |
| UtBot_indicator_easy.pine      | ok                  | 1.4     | 228    | -71.52% | -71.47% | -0.79  | -0.52   | -80.47%  | 31.58%  | 0.75 | 38.26      | 13            | 4185.65 | 2092.83 |
| UtBot_strategy_medium.pine     | ok                  | 1.4     | 228    | -68.76% | -68.70% | -0.72  | -0.48   | -80.09%  | 31.58%  | 0.76 | 38.26      | 13            | 4268.72 | 2134.36 |
| bs_indicator_medium.pine       | ok                  | 12.3    | 129    | 35.15%  | 35.09%  | 0.80   | 0.54    | -36.87%  | 28.68%  | 1.19 | 67.63      | 9             | 2937.69 | 1468.85 |

## T4 — recent / 1h 성과

| 스크립트                       | 상태                | 실행(s) | Trades | Return    | CAGR    | Sharpe | Sortino | MDD      | WinRate | PF   | AvgHold(h) | MaxConsecLoss | Fees     | Slip     |
| ------------------------------ | ------------------- | ------- | ------ | --------- | ------- | ------ | ------- | -------- | ------- | ---- | ---------- | ------------- | -------- | -------- |
| DrFXGOD_indicator_hard.pine    | skipped_unsupported | —       | —      | —         | —       | —      | —       | —        | —       | —    | —          | —             | —        | —        |
| DrFX_strategy_quantbridge.pine | ok                  | 5.0     | 131    | -24.49%   | -24.51% | -0.26  | -0.10   | -51.23%  | 34.35%  | 0.85 | 65.63      | 17            | 2502.60  | 1251.30  |
| LuxAlgo_indicator_medium.pine  | ok                  | 3.3     | 0      | 0.00%     | 0.00%   | 0.00   | —       | 0.00%    | 0.00%   | —    | —          | —             | 0.00     | 0.00     |
| PbR_strategy_easy.pine         | ok                  | 3.3     | 962    | -298.97%  | —       | -0.98  | 7.70    | -294.62% | 38.57%  | 0.61 | 9.08       | 19            | 24872.20 | 12436.10 |
| RsiD_strategy_hard.pine        | ok                  | 9.7     | 110    | -1277.03% | —       | -0.98  | 1.21    | -632.60% | 48.18%  | 0.54 | 43.11      | 8             | 39733.62 | 19866.81 |
| UtBot_indicator_easy.pine      | ok                  | 4.7     | 961    | -286.14%  | —       | -0.46  | 0.68    | -286.96% | 29.45%  | 0.57 | 9.10       | 13            | 20431.31 | 10215.65 |
| UtBot_strategy_medium.pine     | ok                  | 5.7     | 961    | -286.40%  | —       | 1.22   | 0.69    | -287.25% | 29.45%  | 0.57 | 9.10       | 13            | 20463.41 | 10231.71 |
| bs_indicator_medium.pine       | ok                  | 16.5    | 575    | -183.13%  | —       | 0.73   | 4.22    | -175.48% | 23.48%  | 0.66 | 15.13      | 21            | 14357.03 | 7178.51  |

## T5 — recent / 4h 성과

| 스크립트                       | 상태                | 실행(s) | Trades | Return   | CAGR    | Sharpe | Sortino | MDD      | WinRate | PF   | AvgHold(h) | MaxConsecLoss | Fees     | Slip    |
| ------------------------------ | ------------------- | ------- | ------ | -------- | ------- | ------ | ------- | -------- | ------- | ---- | ---------- | ------------- | -------- | ------- |
| DrFXGOD_indicator_hard.pine    | skipped_unsupported | —       | —      | —        | —       | —      | —       | —        | —       | —    | —          | —             | —        | —       |
| DrFX_strategy_quantbridge.pine | ok                  | 1.5     | 31     | 25.85%   | 25.89%  | 0.77   | 0.35    | -31.96%  | 41.94%  | 1.22 | 266.06     | 4             | 680.02   | 340.01  |
| LuxAlgo_indicator_medium.pine  | ok                  | 1.0     | 0      | 0.00%    | 0.00%   | 0.00   | —       | 0.00%    | 0.00%   | —    | —          | —             | 0.00     | 0.00    |
| PbR_strategy_easy.pine         | ok                  | 0.8     | 254    | -58.52%  | -58.56% | -0.77  | -0.17   | -78.61%  | 46.85%  | 0.78 | 34.22      | 14            | 4977.20  | 2488.60 |
| RsiD_strategy_hard.pine        | ok                  | 3.7     | 29     | -769.10% | —       | 1.36   | 1.69    | -477.47% | 44.83%  | 0.53 | 117.10     | 5             | 10349.09 | 5174.54 |
| UtBot_indicator_easy.pine      | ok                  | 1.2     | 224    | -72.08%  | -72.12% | -1.32  | -0.45   | -77.77%  | 36.61%  | 0.77 | 38.82      | 9             | 5328.33  | 2664.16 |
| UtBot_strategy_medium.pine     | ok                  | 1.7     | 224    | -72.49%  | -72.53% | -1.33  | -0.45   | -77.91%  | 36.61%  | 0.76 | 38.82      | 9             | 5288.54  | 2644.27 |
| bs_indicator_medium.pine       | ok                  | 12.5    | 145    | -50.47%  | -50.51% | -0.92  | -0.25   | -64.19%  | 26.21%  | 0.71 | 59.64      | 18            | 2624.81  | 1312.41 |

> **각주**: Sharpe/Sortino 는 bar-count 스케일(연율화 아님) — TF 간 직접 비교 금지.
> CAGR(annual_return_pct) 은 timestamp 기반 — TF/기간 간 비교 가능.
> config: init_cash=10000, fees=0.1%, slippage=0.05%, fill_timing=bar_close.
> degraded 스크립트는 CLI 하니스에서 실행되지만 웹 UI 는 명시 동의 없이 422 차단.
