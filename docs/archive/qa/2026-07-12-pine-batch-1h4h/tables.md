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

| 스크립트                       | 상태                | 실행(s) | Trades | Return    | CAGR    | Sharpe | Sortino | MDD       | WinRate | PF   | AvgHold(h) | MaxConsecLoss | Fees      | Slip     |
| ------------------------------ | ------------------- | ------- | ------ | --------- | ------- | ------ | ------- | --------- | ------- | ---- | ---------- | ------------- | --------- | -------- |
| DrFXGOD_indicator_hard.pine    | skipped_unsupported | —       | —      | —         | —       | —      | —       | —         | —       | —    | —          | —             | —         | —        |
| DrFX_strategy_quantbridge.pine | ok                  | 4.7     | 142    | -46.54%   | -46.48% | -0.56  | -0.46   | -59.91%   | 32.39%  | 0.77 | 61.51      | 9             | 2313.69   | 1156.85  |
| LuxAlgo_indicator_medium.pine  | ok                  | 3.0     | 0      | 0.00%     | 0.00%   | 0.00   | —       | 0.00%     | 0.00%   | —    | —          | —             | 0.00      | 0.00     |
| PbR_strategy_easy.pine         | ok                  | 3.3     | 949    | -1337.70% | —       | 1.16   | 1.96    | -1058.64% | 41.41%  | 0.70 | 9.23       | 11            | 125522.77 | 62761.39 |
| RsiD_strategy_hard.pine        | ok                  | 9.8     | 133    | -411.96%  | —       | 0.50   | 2.65    | -219.16%  | 43.61%  | 0.81 | 37.64      | 8             | 35480.94  | 17740.47 |
| UtBot_indicator_easy.pine      | ok                  | 4.4     | 916    | -2029.34% | —       | -0.41  | -0.28   | -1961.07% | 27.84%  | 0.57 | 9.54       | 14            | 122494.47 | 61247.23 |
| UtBot_strategy_medium.pine     | ok                  | 5.6     | 916    | -2029.34% | —       | -0.41  | -0.28   | -1961.07% | 27.84%  | 0.57 | 9.54       | 14            | 122494.47 | 61247.23 |
| bs_indicator_medium.pine       | ok                  | 15.8    | 599    | -1486.44% | —       | 1.25   | 0.11    | -1462.83% | 21.70%  | 0.57 | 14.59      | 19            | 79311.73  | 39655.86 |

## T3 — 2024 / 4h 성과

| 스크립트                       | 상태                | 실행(s) | Trades | Return   | CAGR    | Sharpe | Sortino | MDD      | WinRate | PF   | AvgHold(h) | MaxConsecLoss | Fees     | Slip     |
| ------------------------------ | ------------------- | ------- | ------ | -------- | ------- | ------ | ------- | -------- | ------- | ---- | ---------- | ------------- | -------- | -------- |
| DrFXGOD_indicator_hard.pine    | skipped_unsupported | —       | —      | —        | —       | —      | —       | —        | —       | —    | —          | —             | —        | —        |
| DrFX_strategy_quantbridge.pine | ok                  | 1.5     | 35     | -17.75%  | -17.73% | -0.09  | -0.08   | -55.66%  | 40.00%  | 0.82 | 236.69     | 6             | 717.78   | 358.89   |
| LuxAlgo_indicator_medium.pine  | ok                  | 0.9     | 0      | 0.00%    | 0.00%   | 0.00   | —       | 0.00%    | 0.00%   | —    | —          | —             | 0.00     | 0.00     |
| PbR_strategy_easy.pine         | ok                  | 0.7     | 251    | 343.78%  | 342.73% | 2.19   | 1.46    | -90.50%  | 58.57%  | 1.19 | 34.73      | 4             | 33579.23 | 16789.61 |
| RsiD_strategy_hard.pine        | ok                  | 3.7     | 23     | 244.34%  | 243.66% | -0.09  | 1.03    | -105.44% | 56.52%  | 1.76 | 122.96     | 2             | 6516.55  | 3258.27  |
| UtBot_indicator_easy.pine      | ok                  | 1.1     | 228    | -451.14% | —       | 0.31   | 0.20    | -352.07% | 31.58%  | 0.78 | 38.26      | 13            | 30036.81 | 15018.41 |
| UtBot_strategy_medium.pine     | ok                  | 1.4     | 228    | -451.14% | —       | 0.31   | 0.20    | -352.07% | 31.58%  | 0.78 | 38.26      | 13            | 30036.81 | 15018.41 |
| bs_indicator_medium.pine       | ok                  | 11.7    | 129    | 238.91%  | 238.25% | -0.79  | 1.16    | -139.56% | 28.68%  | 1.22 | 67.63      | 9             | 16844.86 | 8422.43  |

## T4 — recent / 1h 성과

| 스크립트                       | 상태                | 실행(s) | Trades | Return    | CAGR    | Sharpe | Sortino | MDD       | WinRate | PF   | AvgHold(h) | MaxConsecLoss | Fees      | Slip     |
| ------------------------------ | ------------------- | ------- | ------ | --------- | ------- | ------ | ------- | --------- | ------- | ---- | ---------- | ------------- | --------- | -------- |
| DrFXGOD_indicator_hard.pine    | skipped_unsupported | —       | —      | —         | —       | —      | —       | —         | —       | —    | —          | —             | —         | —        |
| DrFX_strategy_quantbridge.pine | ok                  | 4.7     | 131    | -24.49%   | -24.51% | -0.26  | -0.10   | -51.23%   | 34.35%  | 0.85 | 65.63      | 17            | 2502.60   | 1251.30  |
| LuxAlgo_indicator_medium.pine  | ok                  | 2.9     | 0      | 0.00%     | 0.00%   | 0.00   | —       | 0.00%     | 0.00%   | —    | —          | —             | 0.00      | 0.00     |
| PbR_strategy_easy.pine         | ok                  | 3.2     | 962    | -2090.04% | —       | 0.38   | 0.05    | -1546.81% | 38.57%  | 0.61 | 9.08       | 19            | 174832.50 | 87416.25 |
| RsiD_strategy_hard.pine        | ok                  | 9.8     | 110    | -1277.03% | —       | -0.98  | 1.21    | -632.60%  | 48.18%  | 0.54 | 43.11      | 8             | 39733.62  | 19866.81 |
| UtBot_indicator_easy.pine      | ok                  | 4.7     | 961    | -2429.27% | —       | -0.12  | -0.09   | -2353.19% | 29.45%  | 0.56 | 9.10       | 13            | 175473.16 | 87736.58 |
| UtBot_strategy_medium.pine     | ok                  | 5.5     | 961    | -2429.27% | —       | -0.12  | -0.09   | -2353.19% | 29.45%  | 0.56 | 9.10       | 13            | 175473.16 | 87736.58 |
| bs_indicator_medium.pine       | ok                  | 16.0    | 575    | -1214.54% | —       | 1.61   | -0.14   | -615.90%  | 23.48%  | 0.67 | 15.13      | 21            | 104776.38 | 52388.19 |

## T5 — recent / 4h 성과

| 스크립트                       | 상태                | 실행(s) | Trades | Return   | CAGR   | Sharpe | Sortino | MDD      | WinRate | PF   | AvgHold(h) | MaxConsecLoss | Fees     | Slip     |
| ------------------------------ | ------------------- | ------- | ------ | -------- | ------ | ------ | ------- | -------- | ------- | ---- | ---------- | ------------- | -------- | -------- |
| DrFXGOD_indicator_hard.pine    | skipped_unsupported | —       | —      | —        | —      | —      | —       | —        | —       | —    | —          | —             | —        | —        |
| DrFX_strategy_quantbridge.pine | ok                  | 1.4     | 31     | 25.85%   | 25.89% | 0.77   | 0.35    | -31.96%  | 41.94%  | 1.22 | 266.06     | 4             | 680.02   | 340.01   |
| LuxAlgo_indicator_medium.pine  | ok                  | 1.0     | 0      | 0.00%    | 0.00%  | 0.00   | —       | 0.00%    | 0.00%   | —    | —          | —             | 0.00     | 0.00     |
| PbR_strategy_easy.pine         | ok                  | 0.7     | 254    | -537.93% | —      | 0.54   | -0.19   | -412.41% | 46.85%  | 0.78 | 34.22      | 14            | 46442.43 | 23221.21 |
| RsiD_strategy_hard.pine        | ok                  | 3.7     | 29     | -769.10% | —      | 1.36   | 1.69    | -477.47% | 44.83%  | 0.53 | 117.10     | 5             | 10349.09 | 5174.54  |
| UtBot_indicator_easy.pine      | ok                  | 1.1     | 224    | -355.73% | —      | -0.63  | 0.18    | -198.68% | 36.61%  | 0.84 | 38.82      | 9             | 40374.00 | 20187.00 |
| UtBot_strategy_medium.pine     | ok                  | 1.4     | 224    | -355.73% | —      | -0.63  | 0.18    | -198.68% | 36.61%  | 0.84 | 38.82      | 9             | 40374.00 | 20187.00 |
| bs_indicator_medium.pine       | ok                  | 13.8    | 145    | -367.92% | —      | -0.94  | -0.30   | -272.88% | 26.21%  | 0.78 | 59.64      | 18            | 26554.55 | 13277.28 |

> **각주**: Sharpe/Sortino 는 bar-count 스케일(연율화 아님) — TF 간 직접 비교 금지.
> CAGR(annual_return_pct) 은 timestamp 기반 — TF/기간 간 비교 가능.
> config: init_cash=10000, fees=0.1%, slippage=0.05%, fill_timing=bar_close.
> degraded 스크립트는 CLI 하니스에서 실행되지만 웹 UI 는 명시 동의 없이 422 차단.
