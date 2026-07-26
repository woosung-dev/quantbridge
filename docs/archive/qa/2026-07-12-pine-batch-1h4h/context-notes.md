# Pine 코퍼스 배치 백테스트 — 컨텍스트 노트

> 결정과 근거를 append-only 로 기록. 다음 세션이 재추론 없이 이어받는 용도.

## 2026-07-12 Phase 0

### 베이스라인

- `pytest tests/strategy/pine_v2 -q` = **778 passed, 16 skipped, 207.63s** (skip = mutation oracle nightly 전용).
- 브랜치 `stage/pine-batch-qa` @ main f087b5a.

### coverage before 매트릭스 (실측, analyze_coverage)

| 파일                      | runnable | degraded                           | unsupported                                                              |
| ------------------------- | -------- | ---------------------------------- | ------------------------------------------------------------------------ |
| DrFX_strategy_quantbridge | ✅       | —                                  | —                                                                        |
| LuxAlgo_indicator_medium  | ✅       | —                                  | —                                                                        |
| PbR_strategy_easy         | ✅       | —                                  | —                                                                        |
| RsiD_strategy_hard        | ✅       | —                                  | —                                                                        |
| UtBot_indicator_easy      | ✅       | heikinashi, timeframe.period       | —                                                                        |
| UtBot_strategy_medium     | ✅       | heikinashi, timeframe.period       | —                                                                        |
| bs_indicator_medium       | ❌       | —                                  | array 8종 (clear/get/new_bool/new_float/new_line/push/set/size)          |
| DrFXGOD_indicator_hard    | ❌       | request.security, timeframe.period | array 9종 + request.security_lower_tf, ta.alma, ta.dmi, ticker.new, time |

### 사전 확정 사실 (플랜 탐색 단계)

- 8종 중 6종은 `tests/fixtures/pine_corpus_v2/` 와 바이트 동일 (DrFXGOD = i3_drfx). 진짜 신규 = bs + DrFX_strategy.
- 인터프리터가 for/while 을 **조용히 skip** (interpreter.py:361-363) — coverage regex 는 호출 기반이라 루프 자체를 못 봄. Trust Layer 구멍. runnable 코퍼스에 루프 사용 0건 → G1 추가는 골든 회귀 리스크 0.
- Track A(indicator+alertcondition) 는 run_backtest_v2 로 직접 가상 트레이드 생성 (i1==s2 433 트레이드 parity). strategy.entry(stop=) 구현됨 (s1_pbr 465).
- `BacktestConfig.freq` 기본 "1D" — 하니스에서 반드시 "1h"/"4h" 명시 (avg_holding_hours 왜곡 방지). Sharpe 는 bar-count 스케일 → TF 간 직접 비교 불가 각주 의무. CAGR 은 timestamp 기반 → 비교 가능.
- bare v4 `security` 가 `_DEGRADED_FUNCTIONS` 에 누락 (request.security 만 등재) — G3 1줄 trust fix 대상.
- run_backtest_v2 에는 degraded 게이트 없음 (게이트는 backtest/service.py:167 submit 레벨) → CLI 하니스는 UtBot 실행 가능, 웹 UI 는 422 카드.

### 결정 기록

- **데이터 = 둘 다** (사용자 선택): 2024 고정 세트(재현성·오라클·개선 루프) + 최근 1년 CCXT fetch(국면 비교). 4h(2024) 는 1h 픽스처 리샘플 — Bybit 4h 봉은 1h 봉의 정확한 집계(UTC 정렬)이므로 왜곡 없음.
- 4h CSV 위치 = `backend/data/fixtures/ohlcv/BTCUSDT_4h.csv` — FixtureProvider `{root}/{SYMBOL}_{TIMEFRAME}.csv` 규칙을 따라 웹 UI 백테스트에도 그대로 서빙되게 함.
- 산출물 위치 = `docs/archive/qa/2026-07-12-pine-batch-1h4h/` (기존 `docs/archive/qa/2026-06-30-pine-tiered-backtest/` 관례).

## 2026-07-12 Phase 1 실측 후 계획 수정 (중대)

- **기존 `BTCUSDT_1h.csv` 픽스처 = 합성 데이터 확정** (git log: "synthetic OHLCV fixture for Sprint 4"). 8,760봉 중 low 위반 3,385 + high 위반 3,276 (~77% OHLC 불변식 위반), 실 Bybit 대비 최대 $37k 괴리. 의미 있는 성과 측정 불가 + stop fill(high/low 의존) 왜곡.
- 참조 테스트 전수 확인 결과 **모두 자체 tmp CSV 생성** — 커밋 픽스처 값 의존 0건 → 실데이터 교체 안전.
- **계획 변경**: 리샘플 스크립트+fetch 스크립트 2종 → 통합 `scripts/fetch_qa_ohlcv.py` 1종. 실 Bybit perp {2024, 2025-07~2026-07} × {1h, 4h} 4세트 fetch. 검증 4중: 봉수 정확(8784/2196/8760/2190) + 갭 0 + OHLC 위반 0 + 1h→4h 리샘플 크로스체크 + **frozen parquet(2024 1~6월) 완전 일치** (trust-layer 와 동일 소스 증명).

## 2026-07-12 Phase 2 결과 (before)

- 24 runnable 셀 전부 `status=ok` (0.7~9.9s/셀). bs/DrFXGOD skipped_unsupported.
- **UtBot indicator(Track A) == UtBot strategy(Track S) 메트릭 완전 동일** (916/916, 228/228 트레이드) — Track A parity 재확인.
- **LuxAlgo 0 트레이드 원인 규명**: upos/dnos 플립은 존재(4h 308/112 bars). alert 2종은 수집되지만 기본 `strict` 휴리스틱에서 `\btrendline\b` → INFORMATION 분류 (설계된 보수 기본값). `PINE_ALERT_HEURISTIC_MODE=loose` 가 기존 opt-in (\bupward\b → LONG_ENTRY). trust-layer 베이스라인도 strict 0 트레이드로 동결 — 엔진 버그 아님, 리포트에 양 모드 병기.
- **사이징 왜곡**: qty 미선언 스크립트(PbR/UtBot)는 TV parity 기본 qty=1.0 BTC → init_cash 10k 대비 4~10배 레버리지 효과 → -2000%대 수익률/MDD(-19xx%), mdd_exceeds_capital. DrFX(percent_of_equity 100)만 정상 스케일. 청산(liquidation) 모델 부재는 알려진 가정 — 리포트 각주.

## 2026-07-12 Phase 3 결과 (엔진 개선 G1~G5)

| 갭  | 내용                                                                            | 처리                                                                                                          |
| --- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| G1  | for/while/break/continue silent skip (Trust Layer 구멍)                         | ✅ 구현 — TV 시멘틱(inclusive·방향 자동·`by` 양수 크기), iteration cap 100k, ForIn 포함. test_loops.py 19건   |
| G2  | array.\* 전체 미지원 → bs/DrFXGOD 차단                                          | ✅ 최소 15종 구현 (\_names.ARRAY_FUNCTIONS SSOT). 잔여(avg/sort 등) namespace catch 유지. test_arrays.py 18건 |
| G3  | v4 bare `security` 가 \_DEGRADED_FUNCTIONS 누락                                 | ✅ 1줄 fix + 테스트                                                                                           |
| G4  | rendering NOP 시그니처 협소 — `table.new(pos, cols, rows)` positional TypeError | ✅ table_new/table_cell \*args/\*\*extras 흡수                                                                |
| G5  | coverage 는 `label.style_*` prefix 허용, runtime 은 dict 열거만 → drift         | ✅ _eval_attribute prefix fallback (label.style_/line.style\_)                                                |

- 스위트: before 778 → **after 815 passed, 0 failed** (골든/parity 포함 = 기존 결과 바이트 동일 증명).
- bs: **7/8 runnable 달성** — 2024 4h 129 트레이드 (1h 599). DrFXGOD 는 잔여 5종(ta.alma/ta.dmi/ticker.new/security_lower_tf/time()) BL 등재로 정직 종결.
- 구스펙 테스트 3건 갱신 (sprint31 array 차단 테스트 → G2 승격 반영, parity union 13그룹).
- 선재 발견: coverage.py `_PINE_V6_COLLECTION_NAMESPACES` 는 실사용 없는 문서용 중복 상수 (실 동작 = `_KNOWN_NAMESPACES`) — 미삭제, 기록만.

## 2026-07-12 오라클 검증 (§7.3 비순환)

- **오라클 ① UtBot 4h**: Wilder ATR(10)+트레일링 스탑 체인 순수 pandas 독립 재구현 → 첫 시그널 bar 14 short, entry=close[14]=43736.2 — **엔진과 3항목(바/방향/가격) 완전 일치 PASS**.
- **오라클 ② bs 4h**: ta.ema SMA 시드 독립 재구현. 엔진 시멘틱(nan 비교→False) 수계산 = bar 12 long → **엔진과 완전 일치**. 단, **TV-parity 갭 발견**: Pine 은 bool 시리즈에 na 전파(na 조건=false) → TV 첫 시그널은 bar 15 short. 엔진은 emaSlow(13) 첫 정의 bar(12) 에서 False→True 전환으로 **스퓨리어스 시그널 1건** 발생. → BL 등재 (indicator warmup 경계 na→False 실체화).
