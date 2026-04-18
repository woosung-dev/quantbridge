# N-way 매트릭스 — I3 DrFX × 1H/4H 타임프레임

> 기간: 2025-04-18 ~ 2026-04-17 1년 (BTCUSDT 현물, Binance CCXT, 고정 CSV)
> 1H: 8,760 bars / 4H: 2,190 bars
> E1 PyneCore 오라클은 PyneSys 상용 API 의존으로 제거. LLM 4개 + Opus baseline 상호 비교.

## 1H 타임프레임

| 엔진 | 모델 | 공급사 | TIER | total_return_pct | max_drawdown_pct | sharpe_ratio | profit_factor | total_trades | winning_trades | losing_trades | win_rate | exit reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e4-opus | Claude Opus 4.7 | Anthropic | 플래그십 | -40.80% | -44.06% | -4.41 | 0.37 | 145 | 37 | 108 | 25.52% | SL:108, TP2:37 |
| e5-sonnet | Claude Sonnet 4.6 | Anthropic | 중형 | -52.21% | -52.21% | -25.17 | 0.50 | 100 | 41 | 59 | 41.00% | SL:59, TP:41 |
| e6-gpt5 | GPT-5 | OpenAI | 플래그십 | 0.00% | 0.00% | 0.00 | — | 0 | 0 | 0 | 0.00% | — |
| e7a-gemini-pro | Gemini 3.1-pro-preview | Google | 플래그십 (skip — 429 quota) | — | — | — | — | — | — | — | — | skip |
| e7b-gemini-flash | Gemini 3.1-flash-lite | Google | 소형 | -0.10% | 0.00% | 0.00 | — | 0 | 0 | 0 | 0 | TrendReversal:0 |

**수익률 범위:** -52.21% ~ 0.00% (폭 52.21%p) / 거래 0건 엔진 2/4

## 4H 타임프레임

| 엔진 | 모델 | 공급사 | TIER | total_return_pct | max_drawdown_pct | sharpe_ratio | profit_factor | total_trades | winning_trades | losing_trades | win_rate | exit reasons |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| e4-opus | Claude Opus 4.7 | Anthropic | 플래그십 | -10.13% | -13.84% | -0.89 | 0.71 | 37 | 12 | 25 | 32.43% | SL:25, TP2:12 |
| e5-sonnet | Claude Sonnet 4.6 | Anthropic | 중형 | -20.51% | -33.88% | -15.89 | 0.62 | 18 | 9 | 9 | 50.00% | TP:9, SL:9 |
| e6-gpt5 | GPT-5 | OpenAI | 플래그십 | 0.00% | 0.00% | 0.00 | — | 0 | 0 | 0 | 0.00% | — |
| e7a-gemini-pro | Gemini 3.1-pro-preview | Google | 플래그십 (skip — 429 quota) | — | — | — | — | — | — | — | — | skip |
| e7b-gemini-flash | Gemini 3.1-flash-lite | Google | 소형 | -0.10% | 0.00% | 0.00 | — | 0 | 0 | 0 | 0 | TrendReversal:0 |

**수익률 범위:** -20.51% ~ 0.00% (폭 20.51%p) / 거래 0건 엔진 2/4

## Phase -1 가정 판정 (MVP scope: TP/SL/LONG/SHORT)

| 가정 | 판정 | 근거 |
|------|:--:|------|
| A2: 상대오차 <0.1% KPI 현실적 | ❌ **반증** | 1H+4H 통합 수익률 범위 52.2%p — LLM 단독 quasi-oracle 불가 |
| A3: LLM 변환 버그 재현성 | ✅ **실증** | 모델별 상이한 구조적 버그. 1H+4H 합산 4개 runs에서 진입 로직 자체 실패 |
| ~~A1: trail_points 지원~~ | N/A | scope 축소 (H2+ 이연) |

## 타임프레임 간 비교 관찰 (1H vs 4H)

- **E4 Opus:** 1H -40.80% vs 4H -10.13% (delta +30.66%p) — 노이즈 + 수수료 누적이 1H 손실 악화의 주요 원인 (145 → 37 trades)
- **E5 Sonnet:** 1H -52.21% vs 4H -20.51% — Opus와 달리 4H에서도 손실 유지 → 구조적 변환 차이 지속
- **E6/E7b:** 1H·4H 모두 0 trades — 진입 로직 자체 미구현. 타임프레임 무관 구조 실패