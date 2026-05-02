# Supported Indicators / Strategies — QuantBridge Trust Layer

> **목적**: TradingView Pine Script 의 어떤 strategy/indicator 가 QuantBridge 백테스트로 실행 가능한지 명시. **trust layer 철학**: 커버리지보다 정직함 — 미지원은 명시적으로 reject.
>
> **Last update**: 2026-04-23 (Sprint Y1 — pre-flight coverage analyzer 도입 시점)
> **SSOT**: `backend/src/strategy/pine_v2/coverage.py` 의 `SUPPORTED_FUNCTIONS` + `SUPPORTED_ATTRIBUTES`

---

## 1. 검증된 Strategy/Indicator (qualified corpus)

dogfood 환경에서 backtest 통과 확인된 항목. `backend/tests/fixtures/pine_corpus_v2/` 에 fixture 포함 + E2E 테스트 존재.

| Name              | Fixture              | Type                            | Note                                                  |
| ----------------- | -------------------- | ------------------------------- | ----------------------------------------------------- |
| **s1_pbr**        | `s1_pbr.pine`        | Strategy                        | PBR mean reversion. 단순. **권장 첫 dogfood**         |
| **s1_pbr_sltp**   | `s1_pbr_sltp.pine`   | Strategy                        | + SL/TP exit                                          |
| **s2_utbot**      | `s2_utbot.pine`      | Strategy                        | UT Bot Alerts                                         |
| **s2_utbot_sltp** | `s2_utbot_sltp.pine` | Strategy                        | + SL/TP                                               |
| **s3_rsid**       | `s3_rsid.pine`       | Strategy                        | RSI divergence                                        |
| **s3_rsid_sltp**  | `s3_rsid_sltp.pine`  | Strategy                        | + SL/TP                                               |
| **i1_utbot**      | `i1_utbot.pine`      | Indicator                       | UT Bot 신호 추출                                      |
| **i2_luxalgo**    | `i2_luxalgo.pine`    | Indicator (Trendlines + Breaks) | **`PINE_ALERT_HEURISTIC_MODE=loose`** 필요 (W1 X1+X3) |
| **MA crossover**  | `ma_crossover.pine`  | Strategy                        | 학습용                                                |

---

## 2. 지원 Pine v5 built-in (SSOT: `coverage.py`)

### 2.1 `ta.*` 함수

`ta.sma`, `ta.ema`, `ta.rma`, `ta.atr`, `ta.rsi`, `ta.crossover`, `ta.crossunder`, `ta.highest`, `ta.lowest`, `ta.change`, `ta.pivothigh`, `ta.pivotlow`, `ta.stdev`, `ta.variance`, `ta.sar`, `ta.barssince`, `ta.valuewhen`

### 2.2 `ta.*` built-in series (attribute access)

`ta.tr` (True Range — Sprint X1+X3 hotfix)

### 2.3 `strategy.*`

- 함수: `strategy.entry`, `strategy.close`, `strategy.close_all`, `strategy.exit`
- 변수: `strategy.long`, `strategy.short`, `strategy.position_size`, `strategy.position_avg_price`

### 2.4 `math.*`

`math.max`, `math.min`, `math.abs`, `math.sign`, `math.sqrt`, `math.exp`, `math.log`, `math.log10`, `math.pow`, `math.round`, `math.floor`, `math.ceil`, `math.sum`, `math.avg`

### 2.5 Series 변수 (built-in)

`open`, `high`, `low`, `close`, `volume`, `hl2`, `hlc3`, `ohlc4`, `time`, `bar_index`, `barstate.*`

### 2.6 Pine v4 → v5 별칭 (alias)

`rma`, `sma`, `ema`, `rsi`, `atr`, `highest`, `lowest`, `crossover`, `crossunder`, `change`, `stdev`, `variance`, `iff`, `switch`

**Sprint 21 추가** (`abs/max/min/pivothigh/pivotlow/barssince/valuewhen/timestamp`) — v4 no-namespace 형식. interpreter alias map 에서 `math.*` 또는 `ta.*` 로 재라우팅. **사용자 정의 함수 우선 dispatch** (Sprint 21 Phase A.1, codex G.0 P1 #1+#4 — `abs(x) =>` 정의 시 alias 압도 차단).

### 2.7 Explicit constant sets (Sprint 21 신규)

namespace prefix 기반 wildcards 가 아닌 **명시적 frozenset** — false-pass 차단 (codex G.0 P1 #3):

- **`_CURRENCY_CONSTANTS`** (12개): `currency.USD`, `currency.EUR`, `currency.JPY`, `currency.GBP`, `currency.AUD`, `currency.CAD`, `currency.CHF`, `currency.NZD`, `currency.HKD`, `currency.SGD`, `currency.KRW`, `currency.NONE`
- **`_STRATEGY_CONSTANTS_EXTRA`** (6개): `strategy.fixed`, `strategy.cash`, `strategy.percent_of_equity`, `strategy.commission_percent`, `strategy.commission_cash_per_contract`, `strategy.commission_cash_per_order`

**`timeframe.*`** — Sprint 21 v2 plan 에 추가 의도였으나 codex G.2 P1 #1 발견으로 회수 (interpreter `_eval_attribute` 의 `timeframe.*` runtime 평가 미구현 = silent corruption risk). Sprint 22+ 의 BL-100 에서 NOP 또는 strict toggle 후 supported.

### 2.7 Plot/Visual (NOP — backtest 영향 없음)

`plot`, `plotshape`, `plotchar`, `plotarrow`, `plotcandle`, `plotbar`, `bgcolor`, `fill`, `hline`, `vline`, `alertcondition`, `alert`, `label.new`, `line.new`, `box.new`, `table.new`, `color.*`

### 2.8 Input (NOP — default value 사용)

`input`, `input.int`, `input.float`, `input.bool`, `input.string`, `input.color`, `input.source`, `input.timeframe`, `input.symbol`, `input.session`, `input.price`, `input.time`

### 2.9 String / format (NOP — display only)

`str.tostring`, `str.tonumber`, `str.format`, `str.length`, `tostring`, `tonumber`, `request.security` (placeholder — MTF 는 H2+)

---

## 3. 알려진 미지원 (deferred)

backtest 실행 시 `pre-flight coverage analyzer` 가 즉시 reject. 별도 sprint scope.

### 3.1 Indicator-level

| Indicator                       | 미지원 항목                                                                                         | 추가 필요                              |
| ------------------------------- | --------------------------------------------------------------------------------------------------- | -------------------------------------- |
| **i3_drfx** (DrFX Diamond Algo) | `fixnan`, `ta.supertrend`, `request.security` MTF, 30+ user functions, complex `box`/`label` 렌더링 | Sprint X4+ — 5개 이상 sprint 누적 필요 |

### 3.2 함수 카테고리

- **`array.*` / `matrix.*`** — Pine v5 의 dynamic array/matrix 미지원
- **`ta.supertrend`, `ta.bbw`, `ta.cci`, `ta.mom`, `ta.mfi`, `ta.willr`, ...** — top-N indicator 별 추가 필요
- **`request.security`, `request.financial`, `request.dividends`** — MTF / fundamental data (H2+ 재설계)
- **`fixnan`, `ta.tostring`, `array.from`** — utility

### 3.3 Semantic-level

- **MTF (Multi-Timeframe)**: `request.security("BTCUSD", "4H", close)` — 현재 NOP placeholder
- **사용자 정의 function 의 stdlib state isolation**: 호출 사이트마다 state 공유 위험 (Sprint 8c partial)
- **dynamic timeframe / symbol switching**: input.timeframe / input.symbol 의 default 만 사용

---

## 4. 사용자 워크플로우

### 4.1 새 strategy 등록 시

1. Pine Script 붙여넣기 → "파싱 결과 해설" 탭 자동 활성
2. **미지원 함수/변수가 있으면 노란 경고 박스에 명시**:
   ```
   ⚠️ 미지원 Pine 함수/변수 (3건) — 백테스트 실행 불가
   ta.supertrend  fixnan  request.security
   ```
3. 사용자가 strategy 자체는 저장 가능 (parse error 없으면)
4. 백테스트 생성 시도 시 **422 Unprocessable Entity** + 미지원 항목 메시지

### 4.2 기존 strategy 의 backtest 시

- API: `POST /api/v1/backtests`
- 미지원 발견 시: `422` + `code=strategy_not_runnable` + `detail` 에 미지원 목록

### 4.3 지원 추가 요청

새 indicator 의 stdlib 함수가 필요하면:

1. `backend/src/strategy/pine_v2/stdlib.py` — 함수 구현
2. `backend/src/strategy/pine_v2/interpreter.py` `_STDLIB_NAMES` 또는 `_eval_attribute()` 등록
3. **`backend/src/strategy/pine_v2/coverage.py`** SUPPORTED set 등록 (SSOT)
4. `backend/tests/strategy/pine_v2/test_stdlib_<func>.py` — 단위 테스트
5. fixture 추가 (선택) — `backend/tests/fixtures/pine_corpus_v2/`

> **Golden Rule (CLAUDE.md)**: Pine Script 미지원 함수 1개라도 포함 시 전체 "Unsupported" 반환. 부분 실행 금지 (잘못된 결과 방지).

---

## 5. 변경 이력

- **2026-05-02 (Sprint 21)** — v4 alias 8 추가 (`abs/max/min/pivothigh/pivotlow/barssince/valuewhen/timestamp`) + `_CURRENCY_CONSTANTS` (12) + `_STRATEGY_CONSTANTS_EXTRA` (6) explicit set + `study` declaration alias NOP. **Backend 422 shape 표준화** (`StrategyNotRunnable.unsupported_builtins: list[str]`) + **interpreter alias ordering correctness fix** (user_functions 우선 dispatch). codex G.0 round 1 RETHINK + round 2 GO_WITH_FIXES + G.2 GO_WITH_FIXES (P1 3건 — timeframe 회수 / strategy.exit / vline BL 분리).
- **2026-04-23 (Sprint Y1)** — 본 문서 신설. pre-flight coverage analyzer 도입.
- **2026-04-23 (Sprint X1+X3 follow-up)** — `ta.sar`, `ta.rma`, `ta.tr`, loose mode 추가
- **이전** — `pine-v2-migration` PR #52 + Sprint 8c (user-defined function + 3-Track dispatcher)
