# 실세계 Pine 전략 8종 — 티어드(소/중/대) 백테스트 QA 리포트

> 일자: 2026-06-30 · base `main @37517cf` (BL-376 머지 후) · 코퍼스 `tmp_code/pine_code/` 8종
> 엔진 SSOT: `backend/src/strategy/pine_v2/` (`pine_v2` 인터프리터) · fixture: `BTCUSDT_1h.csv` (8760 bar, 2024)
> 강도: BL-376 동급 — generator-evaluator panel(Workflow 12 agent) + codex 2회(G1 plan eval / G2 challenge) + 각 finding verify-before-accept.

---

## 1. Executive summary

8 전략을 실 엔진(`run_historical` / `run_backtest_v2`)으로 8760 bar 백테스트하고, 난이도 티어별 검증 배터리를 적용했다. **분류·robustness·게이트·메트릭 무결성은 전부 PASS**. 단, 大-tier TV-parity hand-oracle 에서 **핵심 harm-class 버그 1건(`ta.atr`)을 확정**했다(5중 교차검증). 부수적으로 latent harm-class 1건 + Trust-Layer/관측성 갭 3건 + 경미 갭 3건.

| 등급                                 | 건수 | 핵심                                                                                       |
| ------------------------------------ | ---- | ------------------------------------------------------------------------------------------ |
| **harm-class (수치 오류, 트리거됨)** | 1    | **B1 `ta.atr` = rolling SMA, TV Wilder RMA 아님** → ATR 쓰는 전 전략 silent divergence     |
| harm-class (수치 오류, latent)       | 1    | B2 user-function 지역변수 `x[1]` history = na (코퍼스 8종 미트리거)                        |
| Trust-Layer / 관측성                 | 3    | F2 Track A INFORMATION alert 무경고 drop / B3 Track A parity 공허 / F5 parse_failed 오분류 |
| 설계 / 투명성                        | 1    | F1 `qty=1.0` fallback 자본초과 백테스트(`mdd_exceeds_capital`는 정직 flag)                 |
| 경미                                 | 3    | B6 valuewhen na-source / F3 v6→v5 collapse / F4 v4 bare math builtin                       |

**권고:** B1 은 영향이 크고(ATR은 가장 흔한 지표) 수정이 사소(기존 Wilder `ta_rma` 재사용)하므로 **BL-376 식 풀 G1-G4 파이프라인으로 즉시 수정 권고**. 나머지는 BL 등재.

---

## 2. Ground truth — 8 전략 × 티어 결과 매트릭스

| #   | 전략                      | ver/kind    | 티어 | 분류(coverage)                                                  | 실행(8760 bar)         | 메트릭                                                      | 판정            |
| --- | ------------------------- | ----------- | ---- | --------------------------------------------------------------- | ---------------------- | ----------------------------------------------------------- | --------------- |
| 1   | PbR_strategy_easy         | v6→v5/strat | 소   | runnable, 0 unsup                                               | escape 0, 1052 closed  | status=ok, equity NaN 0, **mdd=-16.95 (exceeds_capital=T)** | PASS\* (F1)     |
| 2   | UtBot_indicator_easy      | v4/ind      | 소   | runnable, degraded(heikinashi·timeframe.period)                 | escape 0, virtual 1645 | status=ok                                                   | PASS            |
| 3   | LuxAlgo_indicator_medium  | v5/ind      | 중   | runnable, 0 unsup                                               | escape 0, **0 trades** | status=ok                                                   | PASS\* (F2)     |
| 4   | UtBot_strategy_medium     | v4/strat    | 중   | runnable, degraded                                              | escape 0, 1645 closed  | status=ok, mdd=-41.47 (exceeds_capital=T)                   | PASS\* (F1)     |
| 5   | bs_indicator_medium       | v6→v5/ind   | 중   | **Unsupported 8 (array.\*)**                                    | (preflight reject)     | —                                                           | PASS            |
| 6   | DrFX_strategy_quantbridge | v5/strat    | 대   | runnable, 0 unsup                                               | escape 0, 246 closed   | status=ok                                                   | PASS\* (**B1**) |
| 7   | RsiD_strategy_hard        | v4/strat    | 대   | runnable, 0 unsup                                               | escape 0, 119 closed   | status=ok, +320% ret                                        | PASS\* (B1)     |
| 8   | DrFXGOD_indicator_hard    | v5/ind      | 대   | **Unsupported 14**, degraded(request.security·timeframe.period) | (preflight reject)     | —                                                           | PASS            |

`*` = 실행 완주·게이트는 PASS 이나 §4 finding 보유.

### 2.1 PASS 항목 (검증 완료)

- **분류 정확성 8/8 exact**: bs=8 unsupported(전부 `array.*`, category `syntax`), DrFXGOD=14(9 array + `ta.alma`+`ta.dmi`+`request.security_lower_tf`+`ticker.new`+bare `time`). **false-negative 0 / false-positive 0**(`fixnan`/`ta.wma`/`ta.obv`/`table.cell_set_bgcolor` 미flag, `request.security`/`timeframe.period`=degraded). workaround 14/14 존재.
- **robustness**: 실 전략 입력/시리즈에 na(`1/(close-close)`) + 비-raising inf(`1e308*10`) 주입 → 6 runnable 전부 **raw escape 0**(na→ta.sma length→nan, math.floor(inf)→nan). BL-374/376 가 실 전략 surface 에서 유지됨.
- **메트릭 무결성**: 6 runnable 전부 equity_curve NaN 0 + Decimal 메트릭 유한(sharpe/sortino/profit_factor 비-finite 0) + status 정직(parse_failed 오분류 0).
- **degraded consent gate(ADR-020)**: `service.submit` 실경로 검증(mock repo, DB불필요) — `allow_degraded_pine=False` → `StrategyDegraded(422)` `degraded_calls=['heikinashi','timeframe.period']` / `True` → 통과 / non-degraded → 통과.
- **성능**: 8760 bar × 6 전략 전부 <7s, hang/blowup 0.
- **지표 정확성(大-tier hand-oracle, anti-circular)**: DrFX 패널 oracle 6 중 5 MATCH(`_atr`상수=2, supertrend `_lower`=92/`_st`=108, `sma_filter`=108, `bull` crossover edge-trigger) + RsiD `rsi(9)` 혼합시퀀스 oracle MATCH(Wilder). 즉 sma/ema/rma/rsi/stdev/variance/highest/lowest/change/pivot/crossover/supertrend-band 로직 **TV 정합 확인**.

---

## 3. 검증 방법론 (강도 = BL-376 동급)

- **Phase A**: ground truth 재측정(coverage/version/kind/실행/메트릭) — `scratchpad/pine_qa/run_qa.py`.
- **Phase B**: Workflow generator panel — 전략당 3 후보 + judge(12 agent, ~1.17M tok)로 anti-circular hand-oracle 생성(LESSON-039: 엔진으로 기대값 유도 금지, 수학 정의에서 손유도).
- **Phase C**: codex 2회 — **G1 plan eval**(티어/oracle/누락 점검, 723k tok) + **G2 challenge**(finding 반증 시도 + missed divergence, 2.38M tok). 각 finding **verify-before-accept**(실측 반증 먼저).
- **교차검증**: B1(ATR)은 (1)codex G1 코드지적 (2)직접 hand-oracle 9/9 bar (3)패널 discriminator 설계 (4)패널 oracle 실행 15.0 vs 14.818 (5)codex G2 CONFIRMED — **5중 독립 확인**.

---

## 4. Findings

### B1 — `ta.atr` 가 Wilder RMA 아닌 rolling SMA 사용 [P1, harm-class, **트리거됨**]

**파일:** `backend/src/strategy/pine_v2/stdlib.py:133-154` (`ta_atr`).
**증상:** 엔진 `ta.atr(len)` = TR 의 단순이동평균(`deque(maxlen=len)` → `sum(buf)/len`). TradingView `ta.atr(len)` = `ta.rma(ta.tr, len)` = **Wilder smoothing**(alpha=1/len). 비-상수 TR 에서 발산.
**증거(anti-circular hand-oracle):** 비-상수 TR, len=3 → 엔진=SMA 9/9 bar, Wilder-RMA 0/9. bar 3: 엔진 `3.50000`(=SMA) vs TV `3.05556`(=RMA) **14% 발산**, 누적 증가. 패널 discriminator(len=11): 엔진 `15.0` vs TV `14.818`. 상수 TR 슬라이스는 SMA=RMA 라 은폐(= 기존 테스트가 못 잡은 이유).
**대조:** 같은 파일 `ta_rma`(stdlib.py:104, Wilder)는 정확하고 `ta_rsi`(stdlib.py:193)가 이를 사용 → **atr 만 Wilder 미사용 = 고립 버그**(systematic 아님). RSI 혼합시퀀스 oracle 은 Wilder MATCH 로 통과.
**영향:** ATR 사용 전 전략 — DrFX(`ta.atr(11)`→supertrend 밴드→진입), UtBot(`atr(c)`→트레일링), LuxAlgo(`ta.atr(length)`→slope), RsiD(`atr`→트레일링 SL). 백테스트 결과가 TV 와 silent divergence.
**수정:** `ta_atr` 가 rolling mean 대신 `return ta_rma(self.state ..., tr, length)` 호출(기존 Wilder primitive 재사용). seed bar 는 현재와 동일(SMA seed), 이후 TV 정합. node_id collision 위험 낮음(ta.atr/ta.rma 별도 AST node). **blast radius:** golden snapshot `tests/backtest/engine/golden/ema_cross_atr_sltp_v5/expected.json` 재생성 + 비-상수 TR 테스트 추가(기존 `test_ta_atr_uses_prev_close`는 smoothing 미구분). **→ [BL-378], 풀 G1-G4 수정 권고.**

### B2 — user-function 지역변수 `x[1]` history 가 na 반환 [P1, harm-class, **latent**]

**파일:** `backend/src/strategy/pine_v2/interpreter.py:653` (`_eval_subscript` — `_var_series` 만 조회, user-fn 지역변수 미append).
**증거:** `f(s) => prev = s[1]` 의 `y_fn` = `[nan,nan,nan,nan,nan]` vs top-level `close[1]` `y_top` = `[nan,10,20,30,40]`. fn 내부 subscript history = 항상 na.
**영향:** 코퍼스 8종은 **미트리거**(my DrFX 는 인라인 top-level var, RsiD `_inRange` 는 subscript 미사용). 그러나 `f(x)=>...x[1]...` (지표 함수 내 history 참조) 패턴은 매우 흔함 — 해당 전략은 silent divergence. **→ [BL-379].**

### F2 — Track A INFORMATION/UNKNOWN alert 무경고 drop [P1, Trust-Layer]

**파일:** `virtual_strategy.py:128-130`(`action is None: continue`, 경고 없음) vs docstring `virtual_strategy.py:12`("INFORMATION / UNKNOWN → 무시 + **warning**"). docstring 계약 위반.
**증거:** LuxAlgo `alertcondition(upos>upos[1], 'Upward Breakout', 'Price broke the down-trendline upward')` → 메시지가 strict 기본 INFORMATION 키워드 `\btrendline\b` 매칭(`alert_hook.py:99-110`) → INFORMATION → 무경고 무시 → **0 trades, status=ok**. loose 모드(`PINE_ALERT_HEURISTIC_MODE=loose`, opt-in)면 `\bupward\b`로 directional 분류. 지표 수치(slope/upper/lower/upos/dnos)는 정확.
**codex G2 심화:** 경고를 추가해도 `run_backtest_v2`가 `state.warnings`만 parse warnings 로 내보내 `VirtualRunResult.warnings`가 유실(`v2_adapter.py:181`). 최소 수정 = (a) wrapper 가 ignored actionable alert 시 warning 기록 + (b) `VirtualRunResult.warnings`를 backtest parse warnings 로 전파. **→ [BL-380].** (strict 기본 자체는 의도된 정책 — loose 기본 전환 아님.)

### B3 — Track A `VirtualRunResult` var_series/warnings 미반환 → trust-parity 공허 [P2, meta]

**파일:** `virtual_strategy.py:61,238`(VirtualRunResult 에 var_series 필드 없음). 그러나 `docs/04_architecture/trust-layer-architecture.md:129`는 i2_luxalgo 0-trade 를 `var_series_digest + warnings_digest`로 검증한다 주장 → 실제로는 빈 dict/빈 warnings digest. Track A 의 documented trust-parity 검증이 부분 공허. **→ [BL-381].**

### F1 — `qty=1.0` fallback 자본초과 백테스트 [P2, 투명성]

**증거:** PbR/UtBot 은 `default_qty_type` 미지정 → qty=1.0(1 BTC/trade ≈ $42k notional vs $10k capital) → mdd=-16.95/-41.47, fees $156k/$246k. 엔진은 `mdd_exceeds_capital=True` 정직 flag(`types.py`) + FE KPI 가 자본초과 손실 표시(`metrics-cards.tsx:193`). **그러나** sizing*source 가 FE 결과 schema 부재(`schemas.ts:254`), AssumptionsCard 가 "1 BTC 고정수량 fallback" 미표면화(`assumptions-card.tsx:88`). codex G2 판정 = harm-class 아닌 **투명성 P2**. 수정 = config 응답에 `sizing_source`/`default_qty*\*` 포함 + fallback 시 경고 표시. **→ [BL-382].**

### F5 — `v2_adapter` catch-all 이 런타임 버그를 parse_failed 로 오분류 [P2, 관측성]

**파일:** `v2_adapter.py:126-133`(generic `except Exception` → `status="parse_failed"`). parse 성공 후 실행 중 예외(TypeError 등)도 "parse failed"로 표시 → 원인 분류 오도. BL-376 이 na/inf escape 는 닫았으나 catch-all 잔존. **→ [BL-383].**

### B6 — `ta.valuewhen` 가 na-source occurrence 를 skip [P2, edge]

**파일:** `stdlib.py:305-307`(`cond_bool and source not na` 일 때만 기록). cond=true 인데 source=na 인 occurrence 를 TV 는 기록(na 반환), QB 는 skip → 이전 non-na 반환. 증거: src=[10,na] → `valuewhen(cond,src,0)` QB=10, TV=na. RsiD `valuewhen(plFound, osc[lbR], 1)` 후보(osc warmup 시 na). 좁은 edge. **→ [BL-384].**

### F3 / F4 — 경미 [P3]

- **F3 v6→v5 collapse**: `PineVersion` enum 이 v4/v5 뿐 → `//@version=6`(PbR, bs) 가 v5 로 보고(`strategy/service.py:_detect_version`). 메타데이터 부정확. **→ [BL-385].**
- **F4 v4 bare math builtin 미별칭**: `floor`/`ceil`/`round`/`sqrt` 가 `SUPPORTED_FUNCTIONS` 부재(abs/max/min 만 별칭). v4 스크립트의 `floor()` → unsupported flag(preflight 차단, silent 아님 = 안전하나 over-strict). **→ [BL-386].**

### (참고) heikinashi / request.security NOP 발산

UtBot `security(heikinashi(...), timeframe.period, close)` → TV=HA close, QB=일반 close(`interpreter.py:868,881`). 이는 **degraded 메커니즘이 의도대로 작동**하는 사례 — consent gate(F2 검증 항목)가 `allow_degraded_pine` 동의를 강제하므로 신규 버그 아님. 다만 발산 폭이 큼을 명시.

---

## 5. 검증 증거 표준 충족

- 8 전략 × 티어 체크 결과표(§2) + 실 엔진 출력(errors/status/trades/metrics) 첨부(`scratchpad/pine_qa/qa_result.json`).
- hand-oracle 손계산 명시(B1: TR/SMA/Wilder-RMA 정의식 / RSI 혼합시퀀스 Wilder).
- codex G1 + G2 + 패널 12-agent + 각 finding verify-before-accept 기록(B1 5중, B2/B6 직접 재현, F1 codex 강등 수용).
- anti-circular 준수(LESSON-039): 기대값은 전부 TV 수학 정의에서 손유도, 엔진 자기검증 금지.

## 6. 산출물 / 다음 단계

- **(필수) 본 리포트** = deliverable 1.
- **(조건부) B1 수정** = deliverable 2 — harm-class + 영향 큼 + 수정 사소 → **풀 G1-G4 권고**(사용자 승인 시): `ta_atr` → `ta_rma` 재사용 + 비-상수 TR 골든 + golden snapshot 재생성 + mutation + full pytest + Playwright(백테스트 수치 변동) .
- **BL 등재 9건**: BL-378(ATR/수정대상) · BL-379(fn-local subscript) · BL-380(Track A alert warning) · BL-381(Track A parity) · BL-382(sizing 투명성) · BL-383(parse_failed 오분류) · BL-384(valuewhen na) · BL-385(v6 enum) · BL-386(v4 bare math).
