# Pine Execution Strategy v4 — Session Design Deep-Dive

> **Generated:** 2026-04-17 (50+ 턴 세션 아카이브)
> **Session ID:** QuantBridge Sprint 7b 완료 직후 세션
> **ADR 출력:** [`dev-log/011-pine-execution-strategy-v4.md`](../../dev-log/011-pine-execution-strategy-v4.md)
> **Architecture 출력:** [`04_architecture/pine-execution-architecture.md`](../../04_architecture/pine-execution-architecture.md)

본 문서는 QuantBridge의 Pine Script 실행 전략 v4(Alert Hook Parser + 3-Track) 수렴 과정의 **학술적 아카이브**다. 50+ 대화 턴에서 나온 모든 핵심 근거·통찰·반박·실측을 시간순으로 보존하여, 향후 이 결정이 뒤집히거나 amendment될 때 참조 가능하도록 한다.

---

## Executive Summary

### 한 줄 결론

> **Pine Script를 Execution-First 원칙으로 그대로 실행하되, `alert()` 호출을 매매 신호 선언으로 파싱하여 가상 strategy() 래퍼를 자동 생성하는 3-Track(S/A/M) 아키텍처를 채택한다.**

### 핵심 통찰 3가지

1. **`alert()`은 개발자의 자발적 매매 신호 선언** — 추측하지 말고 파싱하라
2. **매매 로직은 전체 Pine의 13% 이하** (DrFX 650줄 중 2줄) — Execution-First 원칙
3. **실측 없는 설계 5라운드 < 실측 1번** — Phase -1 실측 우선

### Session 진화 요약 (v0 → v5)

```
v0: AST 인터프리터 재검토 질의
  ↓
v1: 3-way evaluator (Opus + Sonnet + me) 16개 아키텍처 조사
  ↓
v2: Gemini Deep Research (11개 방안) + 5개 LLM 비교
  ↓
v3: 반박 16건 중 9건 수용 (KPI 현실화, vectorbt 충돌 등)
  ↓
v4: Alert Hook Parser + 3-Track 수렴 ← 세션 최대 통찰
  ↓
v5: DrFX 실측 (LLM 변환 + BTC/USDT 1년 백테스트)
```

---

## 1. 세션 진화 타임라인 상세

### v0 — 문제 제기 (세션 시작 시점)

**트리거:** Sprint 7b QA(PR #16) 완료 후 사용자가 LuxAlgo Trendlines-with-Breaks Pine 스크립트를 QuantBridge `/strategies/new`에 입력 → 파싱 실패.

**에러 원문:**
```
파싱 실패  /  Pine v5
에러 (1)
L6: 예상치 못한 토큰 LBRACKET('[')
```

**L6 원인:** `locationDashboard = input.string("Bottom Right", "Location", ["Top Right", "Middle Right", ...])` — 배열 리터럴 `[...]` 구문이 QB 파서에 미지원.

**사용자 질문:** "AST 인터프리터가 정답에 가장 가까울까? 대안들이 있을까?"

### v1 — 3-way Evaluator 조사 (병렬 다각 조사)

**방법론:** 3개 agent 병렬 dispatch + 내 직접 WebSearch

| Agent | 역할 | 산출 |
|-------|------|------|
| **Opus subagent** (fresh context) | Pine 생태계 실태 조사 | 13개 실존 프로젝트 + 학술 현황 |
| **Sonnet subagent #1** (fresh) | DSL 실행 아키텍처 이론 | 16개 아키텍처 + 크로스 언어 사례 |
| **Sonnet subagent #2** (fresh) | LLM 번역 최신 연구 | IBM/Oxidizer/EquiBench 벤치마크 |
| 현재 세션 (me) | 종합 + 추천 | 3-Tier 로드맵 |

**결과:** 16개 아키텍처 (A1~A16 symbolic + B13~B14 LLM + C17 우회)

### v2 — 5개 LLM 응답 비교 (의견 다양성 확보)

사용자가 **다른 5개 LLM 응답**을 가져와 제공:

| 응답 # | 핵심 주장 | 1순위 추천 |
|-------|----------|------------|
| #1 | AST 트랜스파일러 + Python/JS 런타임 | PyneCore |
| #2 | 3대장 심층 분석 | PineTS + PyneCore 하이브리드 |
| #3 | 간단 평가표 (10개 방식) | AST + Transpiler + Backtesting + LLM |
| #4 | 14가지 방안 매우 상세 | PyneCore + PyneSys API 시작 |
| #5 (나중에 중복) | **"매매 로직 13%" 통찰 최초 등장** | **Semantic Extraction DSL** |

**공통 수렴점:** PyneCore 생태계 참조 + LLM 단독 금지 + 하이브리드 정답

### v2.5 — Gemini Deep Research 11개 방안

사용자가 Gemini Deep Research 보고서(11,000+ 단어) 제공. 11개 방안 포괄 조사:

1. PyneCore + PyneSys SaaS
2. PineTS 직접 통합 (AGPL 경고 최초 명시)
3. Opus-Aether pine-transpiler
4. 자체 커스텀 파서 + Bytecode VM
5. LLM + Agentic Reflection Loop
6. QuantConnect LEAN 어댑터
7. WebAssembly 파이프라인
8. 원격 MCP API 백테스트 서버 (신규 발견)
9. Zorro Project (신규 발견)
10. TradingView Webhooks 하이브리드
11. OpenPineScript 엔진

**Gemini 추천:** PineTS 1순위 (AGPL 경고 스스로 하면서도 추천). QB는 SaaS라 AGPL 자동 발동 → **실행 불가** 판정.

### v3 — 반박 1차 (8건)

사용자가 내 종합안에 대한 반박 제시. 주요 지점:

1. 순위 불변이 방어적? (Semantic Extraction 1순위?)
2. PyneSys $45 구독 거부는 잘못된 절약?
3. pynescript 포크 중간 경로 누락
4. 14~15자리 정확도 목표 엔지니어링 자만
5. Sprint 용어 조직 맥락 부적합
6. LLM 47% 프레이밍 오용
7. Semantic Extraction 4점 평가 재산정
8. PyneCore strategy.exit 지원 검증 안 함

**수용 (6건):** 3, 4, 6, 7, 8, 그리고 #1 부분 수용
**거부 (2건):** 2, 5 (조직 맥락 오류 기반)

### v3.5 — 반박 2차 (8건, 더 날카로움)

새로운 반박자가 더 깊이 파고듦:

1. 결정론 우상화 (TV도 결정론 아님)
2. Tier-B 드로잉 87% 무시 전제 순진 (SMC line.get_y1 재참조)
3. **vectorbt vs Pine imperative 근본 충돌** ⭐
4. Day 1 TV 골든 하네스 — 어떻게?
5. Sprint 일정 3~5배 낙관적
6. Pine 해석이 진짜 차별점? (유저 5명 인터뷰 필요)
7. 다계층 라우터 Sprint 8b 필수
8. AGPL 단일화 리스크

**수용 (6건):** 1, 3, 4, 5, 7, 8
**부분 수용 (1건):** 2 (드로잉 좌표 getter 필요)
**부분 수용 (1건):** 6 (H1 Stealth에선 유지, H2 전 필수)

**가장 뼈아픈 지적:** #3 vectorbt vs Pine imperative 충돌. 내가 회피했던 구조적 문제. trailing stop/분할 익절/피라미딩이 현재 `SignalResult(entries, exits, sl, tp)` 구조로 표현 불가. → bar-by-bar 이벤트 루프 백테스터 분리 결정.

### v4 — Alert Hook Parser 수렴 ⭐ (세션 최대 통찰)

사용자가 또 다른 의견(v4) 제공. 이게 **세션 전체의 자연스러운 수렴점**이 됨.

**핵심 아이디어:**

> "TradingView `alert()`은 **개발자가 자발적으로 선언한 매매 신호 라벨**이다. Semantic Extraction의 추측 게임을 피할 수 있다."

```pine
if longCondition
    alert("LONG entry at " + str.tostring(close), ...)  // ← 추측 불필요
```

**3-Track 분류:**

| Track | 기준 | 비율 | 자동화 |
|:---:|------|:---:|:---:|
| S | `strategy()` 선언 | 20~30% | 100% |
| **A** | **`indicator()` + `alert()`** | **40~50%** | **80~90%** |
| M | `indicator()` 단독 | 20~30% | 40~50% (수동) |

**합산:** 75% 준-자동 + 25% 수동 → 상품 수준.

**이 순간 순위가 재구조화됨:**

이전 내 5순위:
1. AST 코어 확장 + PyneCore 이식
2. 의미 추출 DSL (Semantic Extraction)
3. vectorbt 매핑
4. LLM 정규화기
5. 다계층 라우터

v4 후 재배치:
- **Tier-0** (enabling infra): AST 코어 + 렌더링 객체 런타임
- **Tier-1** (차별화 핵심) ⭐: **Alert Hook Parser + 3-Track**
- **Tier-2** (Trust): PyneCore 골든 오라클
- **Tier-3**: strategy() 네이티브 (trail_points 포함)
- **Tier-4**: Variable Explorer (Track M)
- **Tier-5**: LLM 하이브리드 + MTF

### v5 — 실측 시작 (이 세션 후반)

#### v5.1 DrFX 스크립트 분석

사용자가 실제 사용하려는 DrFX Diamond Algo Pine 스크립트 제공.

**분해 실측:**

| 부분 | 줄 수 | 백테스트 영향 |
|------|:----:|:--:|
| 입력/설정 | ~50 | ❌ |
| Supertrend 함수 | ~20 | ✅ |
| **bull/bear 매매 로직** | **2** | ✅ **핵심** |
| Supply/Demand 박스 | ~200 | ⚠️ 재참조 리스크 |
| Trend Cloud / Comulus / Cirrus | ~80 | ❌ |
| Smart Trail Fibonacci | ~60 | ❌ |
| Trend Lines | ~50 | ❌ |
| **SL/TP 레벨 계산** | ~60 | ✅ |
| MTF 대시보드 | ~100 | ❌ |
| 세션 감지 | ~50 | ❌ |
| ADX / Volatility / Volume | ~40 | ❌ |
| **Alert 호출** | ~10 | ✅ |

**결론: 매매 의사결정 코드 ~30라인 (4.6%)** — v4 "매매 로직 13%" 통찰 **극단적으로 확인**.

**Alert 매핑:**
- 2개 `alertcondition(bull/bear, message="BUY")` — 오타 존재 (bear인데 "BUY")
- 2개 `alert("Buy Alert"/"Sell Alert")` — 매매 신호 ⭐
- 2개 `alert("break down/upper trendline")` — **정보성, 매매 신호 아님**
- 1개 기타

→ **Track A 분류 + 메시지 분류기 + 사용자 1질문 UX 필요성 완벽 입증**.

#### v5.2 LLM 변환 Python 코드 품질 평가

사용자가 LLM(Claude Opus 추정)에게 DrFX Pine → Python 변환 요청한 결과(800줄) 제공.

**코드 품질:** 매우 높음. dataclass / 타입 힌트 / "생략 항목" 주석 / argparse / Sharpe·MDD·Profit Factor 리포팅 전부 완비.

**발견 버그 3개:**

| 버그 | 심각도 | 사유 |
|------|:---:|------|
| **SL 기준점** | 🔴 Critical | Pine: `low/high - atrBand`, Python: `entry_price - atrBand`. 손절 더 빨리 맞음 |
| **부동소수점 `==` 비교** | 🟠 Medium | `st[i-1] == upper[i-1]` — IEEE 754 엣지 케이스에서 깨질 수 있음 |
| **Look-ahead bias** | 🟡 Minor | 현재 봉 close에 진입 (next bar open 대비 유리) |

**핵심 해석:** 이 변환본은 "LLM이 결정론보다 좋다"를 보여주는 게 아니라 **"Rule+Verifier 하이브리드(Oxidizer 패턴)의 첫 통과 결과로 훌륭하다"**를 보여줌. 검증 없이는 SL 버그를 못 잡음.

LLM 원샷 프레이밍 재평가:
- 이전: "IBM 47% → LLM 금지" 
- 이후: "prompt 잘 된 고급 모델 + 검증 루프 → Oxidizer 73% 패턴으로 가치 있음 (Tier-5)"

#### v5.3 BTC/USDT 1년 실측 백테스트

사용자 요청: "1시간 봉, 4시간 봉, 1년, TP 2, SL 그대로, 신호 바뀌면 청산 후 반대 진입"

**환경:**
- Backend venv (pandas 2.3.3 / numpy 2.2.6 / ccxt 4.5.49 / matplotlib 3.10.8)
- 데이터 소스: Binance 현물 CCXT (BTC-USD yfinance는 패키지 없음 / BTC/USDT 선물 대신 현물)
- 2025-04-17 ~ 2026-04-17 1년

**실측 결과:**

| 지표 | **1H 봉** | **4H 봉** |
|------|:--------:|:--------:|
| 데이터 봉 수 | 8,760 | 2,190 |
| 총 수익률 | **-41.26%** 🔴 | **-10.14%** 🟠 |
| 최종 자본 | $5,874 | $8,986 |
| MDD | -44.06% | -13.84% |
| 샤프 | -4.48 | -0.89 |
| 프로핏 팩터 | 0.36 | 0.71 |
| 총 거래 | 145 | 37 |
| 승률 | 24.83% | 32.43% |
| 청산 사유 | SL 109 / TP2 36 | SL 25 / TP2 12 |
| **REVERSE** | **0** | **0** |

**핵심 발견:**

1. **REVERSE 사용률 0%** — SL/TP가 항상 반대 신호 전에 발동. **Alert Hook Parser 설계 시 SL/TP 우선, REVERSE 후순위 권장**
2. **TP 2:1 × 승률 25~32% 수학적 적자** — 분기점 33.3% 미달
3. **1H vs 4H 차이 31%p** — 노이즈 + 수수료 누적 (145 × 0.15% × 2 = 43% 수수료 소실)
4. **v4 원칙 자동 적용** — LLM이 스크립트 생성 시 "[생략 항목 — 백테스팅 무관]" 주석으로 시각화 87% 자동 무시

**파일 저장:**
- `/tmp/drfx_test/drfx_backtest.py` — 실행 스크립트 (CCXT 버전)
- `/tmp/drfx_test/output/drfx_1h.png`, `drfx_4h.png` — 차트
- `/tmp/drfx_test/output/drfx_1h_trades.csv`, `drfx_4h_trades.csv` — 거래 내역
- `/tmp/drfx_test/output/summary.txt` — 비교 요약

---

## 2. 16개 아키텍처 비교 매트릭스

| # | 접근 | 의미론 | 초기비용 | 기능추가 | 적합성(QB) | 대표 레퍼런스 |
|:---:|------|:---:|:---:|:---:|------|---------------|
| A1 | Tree-walking AST (현재 ADR-004) | ★★★★★ | 완료 | 높음 | **Tier-0 기반** | Crafting Interpreters Lox, Terraform HCL, jq |
| A2 | Python src emit + exec | ★★★★☆ | 중 | 낮음 | ❌ ADR-003 위반 | Cython, xlcalculator, transpyle |
| A3 | Python AST + compile() | ★★★★☆ | 높음 | 중 | ❌ A2와 유사 | ast 모듈, MacroPy |
| A4 | 바이트코드 VM | ★★★★★ | 매우높음 | 낮음 | ❌ 과대투자 | CPython VM, Lua VM, RustPython |
| A5 | LLVM/llvmlite JIT | ★★★☆☆ | 극히높음 | 중 | ❌ vectorbt가 Numba로 커버 | Numba, llvmlite |
| A6 | AssemblyScript WASM | ★★☆☆☆ | 매우높음 | 높음 | ❌ 브라우저 요구 없음 | AssemblyScript |
| A7 | WASM 직접 | ★★☆☆☆ | 극히높음 | 높음 | ❌ | Emscripten, Binaryen |
| A8 | MLIR dialect | ★★★☆☆ | 극히높음 | 낮음 | ❌ 연구 수준 | MLIR, DSP-MLIR, Mojo |
| A9 | 벡터화 해석 | ★★★☆☆ | 중 | 중 | ⚠️ 지표 한정 (Tier-0 세부) | ClickHouse, DuckDB, numexpr |
| A10 | 단계적 부분 평가 | ★★★★☆ | 매우높음 | 낮음 | ❌ 연구 수준 | Futamura 투영, Truffle/GraalVM |
| A11 | PyPy/RestrictedPython | ★★★☆☆ | 중 | 높음 | ❌ 실익 없음 | RestrictedPython, PyPy sandbox |
| A12 | vectorbt 프리미티브 매핑 | ★★★★☆ | 낮음 | 낮음 | ⚠️ 지표 계산 전용 (Tier-0 내부) | vectorbt, pandas-ta |
| A15 | DAG 실행 | ★★★☆☆ | 높음 | 중 | ❌ 사이클 문제 | Dask, Spark DAG |
| A16 | 쿼리 플랜 | ★★★☆☆ | 높음 | 중 | ❌ 상태 불일치 | DuckDB, ClickHouse |
| B13 | LLM 원샷 번역 | ★★☆☆☆ | 극히낮음 | 낮음 | ❌ 비결정성 | IBM Lost in Translation, Pineify |
| B14 | LLM + 결정적 검증 하이브리드 | ★★★☆☆ | 중 | 낮음 | ⭐ **Tier-5 채택** | Amazon Oxidizer PLDI'25 73% |
| C17 | TV webhook 우회 | ★★★★★ | 낮음 | 낮음 | ❌ 백테스트 부적합 | PineConnector, 3Commas |

**v4에서 추가된 신규 (16개에 없던 것):**
- **X1. Alert Hook Parser** — 3-Track 분류 + alert() AST 파싱 (⭐ 채택)
- **X2. 이벤트 루프 백테스터** — bar-by-bar 상태 머신 (Tier-0 필수)

---

## 3. 생태계 13개 프로젝트 상세

| # | 프로젝트 | URL | 접근 | 버전 | 활성도 | 라이선스 | 비고 |
|:--:|---------|-----|------|:----:|:------:|:-------:|------|
| 1 | **PyneCore** | github.com/PyneSys/pynecore | Python을 Pine처럼 동작 (AST 변환) | v6.4.2 | 121★ (2026-04) | Apache 2.0 | **QB Tier-0 참조 대상** |
| 2 | PyneSys (PyneComp) | pynesys.io | 결정론적 Pine → Python codegen | v6 only | 상용 $8-45/mo | 상용 | "We don't use LLM" 명시. 벤더 락인 리스크 |
| 3 | PineTS | github.com/QuantForgeOrg/PineTS | Pine → JS (LuxAlgo 후원) | v5/v6 | 319★ (최다) | **AGPL-3.0** | **SaaS 조항 → 참조 원천 차단** |
| 4 | **pynescript** | github.com/elbakramer/pynescript | ANTLR4 AST 파서 | v0.3.0 | 88★ | LGPL | **파서 포크 대상** |
| 5 | OpenPineScript | github.com/be-thomas/OpenPineScript | Pine → JS | **v2만** | 29★ | GPL-3.0 | v5/v6 미지원 — 실용성 없음 |
| 6 | pine-transpiler | github.com/Opus-Aether-AI/pine-transpiler | 교과서형 컴파일러 → JS | v5/v6 | 14★ | AGPL-3.0 | strategy.* 미지원 |
| 7 | pyine | github.com/TomCallan/pyine | Pine → Python 헬퍼 | - | 134★ | MIT | **2026-02 archived** — 60% 벽 사례 |
| 8 | Trading Strategy | github.com/tradingstrategy-ai/... | 수동 재작성 예제 | - | 운영 중 | - | 인덱싱 함정 문서화 |
| 9 | PineConnector | pineconnector.com | TV + Webhook 중계 | - | 상용 | 상용 | 백테스트 아님, 집행만 |
| 10 | 3Commas Signal Bot | 3commas.io/signal-bot | TV + Webhook | - | 상용 | 상용 | 동일 |
| 11 | QuantConnect LEAN | github.com/QuantConnect/Lean | 독립 퀀트 엔진 | - | 300+ 헤지펀드 | Apache 2.0 | **정책적 Pine 거부** |
| 12 | Pineify / PineGenius / Pine Script Wizard | pineify.app, etc. | LLM 번역 | - | 상용 | 다양 | 비결정적, 복잡도↑ 실패 |
| 13 | PinePyConvert | github.com/LotfiAghel/PinePyConvert | 정적+동적 분석 혼합 | - | 실험적 | - | 문서 부족 |

**학술 문헌:** arXiv/ACM/IEEE 2023-2026 검색 결과 Pine Script 전용 형식화 논문 **0건**.

---

## 4. Pine 의미론 함정 6가지

TV 공식 문서 기반 재현 난제:

| 영역 | TV 동작 | 매핑 난이도 | QB 전략 |
|------|---------|:---:|----|
| **`var`/`varip` + rollback** | realtime bar마다 committed state 복원 | 🔴 상 | PyneCore 이식 (Tier-0) |
| **Bar Magnifier** | 프리미엄+에서 1m/tick 체결 정밀화 | 🔴 상 | H2+ 프리미엄 기능 분리 |
| `calc_on_every_tick` | 백테스트=바 클로즈, 실거래=틱 | 🟠 중 | 명시 설정으로 노출 |
| `process_orders_on_close` | 신호 바에서 즉시 체결 | 🟢 하 | 기본값 유지 |
| `backtest_fill_limits_assumption` | 리밋 체결 엄격성 틱 | 🟠 중 | 명시 설정 |
| **`[0]` vs `.iloc[-1]`** | Pine 역방향 인덱스 | 🔴 상 | 모든 series 접근 추상화 |
| **`na` 3-value logic** | `na==na → na`, NaN==NaN → False | 🟠 중 | Wrapper 래핑 |
| 5000 바 lookback | 버퍼 초과 시 재시작 | 🟢 하 | QB 제한 없음 |
| Pine v6 타입 수식어 | `const`/`input`/`simple`/`series` 4단계 | 🟠 중 | AST에 타입 태그 |
| Pine v6 Matrix/Map/UDT | 최대 100k 요소, Enum 키 | 🟠 중 | Tier-0 파서 확장 |

---

## 5. LLM 번역 벤치마크 (v3 반박으로 재평가)

| 벤치마크 / 사례 | 수치 | 출처 |
|---|---|---|
| HumanEval (함수 단위) | Gemini 2.5 Flash **96.3%** (iterative) | arxiv 2604.10508 |
| **IBM Lost in Translation** (5언어 1,700 샘플) | 상용 LLM **2.1~47.3%** 정확 번역 | ICSE 2024 |
| **Amazon Oxidizer** Go→Rust (프로젝트 단위) | **73% 평균** I/O 동등성, **Rule+LLM 하이브리드** | PLDI'25 / arxiv 2412.08035 |
| **EquiBench** CUDA 수치연산 | o4-mini **60.8%** (일반 82.3%, 수치 급락) | arxiv 2502.12466 |
| **COBOL-Coder** (14B 파인튜닝) | 73.95% 컴파일 성공 | arxiv 2604.03986 |
| **DrFX 실측** (이 세션에서 확인) | **80~90%** 구조 정확, 버그 3개 (검증 후 수정 필요) | 본 세션 v5 |

**교훈:**
- 이전 프레이밍 "LLM 47% → 원천 금지"는 **naive one-shot** 기준으로 오해 유발
- prompt 잘 된 고급 모델 + 검증 루프 = **Oxidizer 73%** 패턴이 현실
- DrFX 80~90%는 검증 파이프라인 **첫 통과 결과로 유효**. 단 3개 버그 (SL 기준점·부동소수점·look-ahead)는 사람이 검증해야 잡힘
- 결정: **LLM을 주경로가 아닌 Tier-5 보조로 배치** (원래 금지 → 재평가 후 Rule+LLM 하이브리드 채택)

---

## 6. 반박 수용/거부 로그 (총 16건)

### 1차 반박 (8건)

| # | 반박 | 입장 | 사유 |
|:--:|------|:---:|------|
| 1 | "순위 불변" 방어적, Semantic Extraction 1순위? | 🟠 부분 수용 | Tier-0/Tier-1 재구조화 |
| 2 | PyneSys $45 구독 거부는 잘못된 절약 | 🔴 거부 | 조직 맥락 오류 + vectorbt 호환 불가 |
| 3 | pynescript 포크가 중간 경로 | ✅ **수용** | 1~2주 작업. ANTLR 대안 |
| 4 | 14-15자리 정확도는 자만 | ✅ **수용** | 상대 오차 단계별 KPI로 재정의 |
| 5 | Sprint 용어 조직 부적합 | 🔴 거부 | 사실 오류 기반. solo indie |
| V1 | LLM 47% 프레이밍 오용 | ✅ 수용 | Oxidizer 73% 맥락 추가 |
| V2 | Extraction 4점 평가 UX 고려? | 🟠 부분 수용 | UX 포함 시 상향, 비용 고려 |
| **V3** | **PyneCore strategy.exit 검증 누락** | 🔴 **강력 수용** | Phase -1 Day 1 긴급 |

### 2차 반박 (8건, 더 날카로움)

| # | 반박 | 입장 | 사유 |
|:--:|------|:---:|------|
| 1 | "결정론 우상화" — TV도 결정론 아님 | ✅ 수용 | KPI 재정의 완료 |
| 2 | Tier-B 드로잉 87% 무시 전제 순진 (SMC line.get_y1) | ✅ 수용 | **범위 A 확정** (좌표 getter 유지) |
| **3** | **vectorbt vs Pine imperative 근본 충돌** | ✅ **수용 (가장 큼)** | **bar-by-bar 이벤트 루프로 분리** |
| 4 | Day 1 TV 골든 — 어떻게? | ✅ 수용 | PyneCore 오라클로 변경 |
| 5 | Sprint 일정 3~5배 낙관적 | ✅ 수용 | 8a를 8a-pre + 8a로 쪼갬 |
| 6 | Pine 해석이 진짜 차별점? | 🟠 부분 수용 | H1은 유지, H2 진입 전 유저 5명 인터뷰 |
| 7 | 다계층 라우터 Sprint 8b 필수 | ✅ 수용 | 5순위 → Tier-1 3-Track 흡수 |
| 8 | AGPL 단일화 리스크 | 🟠 부분 수용 | PineTS clean-room 설계 참조만 |

**수용률:** 16건 중 12건 수용 (75%). 특히 **#3 vectorbt vs Pine imperative 충돌**이 가장 구조적 변화를 일으킴.

---

## 7. v4 Alert Hook Parser 수렴 — 상세

### 7.1 왜 이 접근이 우아한가

**기존 Semantic Extraction의 약점:**
```
AST를 봐도 "이 변수가 entry 신호다"라는 걸 **추측**해야 한다.
```

**v4의 해결:**
```pine
if longCondition
    alert("LONG entry at " + str.tostring(close), ...)
    # ↑ 개발자가 자발적으로 "이게 entry다"라고 라벨 붙임
    # → 추측 불필요
```

**장점:**
- 결정론 (LLM 환각 없음)
- 투명성 (사용자에게 "이렇게 해석됐습니다" 보여줄 수 있음)
- 학습 데이터 자동 수집 (사용자 확인 UX → 메시지 분류 라이브러리 학습)

### 7.2 3-Track 분류 체계

| Track | 판별 기준 | 처리 방식 | 비율 |
|:---:|----------|----------|:---:|
| S | `strategy()` 선언 있음 | Tier-3 네이티브 실행 | 20~30% |
| **A** | `indicator()` + `alert()`/`alertcondition()` | **Tier-1 Alert Hook Parser** | 40~50% |
| M | `indicator()` + alert 없음 | Tier-4 Variable Explorer (수동) | 20~30% |

DrFX 실측: Track A 해당 (indicator + alert 7개)

### 7.3 구현 파이프라인

```
1. AST 전체 탐색 → alert()/alertcondition() FnCall 노드 수집
   ↓
2. 각 호출의 감싸는 if 문 condition 변수 역추적
   ↓
3. 메시지 내용 분류기 (JSON → 키워드 → fallback)
   - "LONG"/"BUY"/"매수" → long_entry
   - "SHORT"/"SELL"/"매도" → short_entry
   - "break"/"trendline" → information (제외)
   ↓
4. SL/TP 수식 AST 스캔 (atrStop, tp1, tp2 같은 변수명 휴리스틱)
   ↓
5. 가상 strategy() 래퍼 자동 생성
   ↓
6. 사용자 1질문 UX (파싱 결과 탭)
   ↓
7. 확정 후 백테스트 실행
```

### 7.4 DrFX 실증 (v5 실측 연결)

```
수집된 alert 7개 분류:
├── "Buy Alert" (bull 조건) → LONG entry ⭐⭐⭐⭐⭐
├── "Sell Alert" (bear 조건) → SHORT entry ⭐⭐⭐⭐⭐
├── alertcondition bull "BUY" → LONG entry (중복) ⭐⭐⭐⭐
├── alertcondition bear "BUY" → ⚠️ 오타, 1질문 UX 필요 ⭐⭐
├── "break down trendline" → ⚠️ 정보성, 1질문 UX ⭐⭐
├── "break upper trendline" → ⚠️ 정보성, 1질문 UX ⭐⭐
└── (생략)
```

→ 자동 분류 4/7, 사용자 확인 필요 3/7 → **분류기 정확도 ~57% 실증, UX 필요성 정당화**.

---

## 8. 12주 로드맵 (세션 최종 합의)

| Phase | Sprint | 기간 | 작업 |
|-------|:------:|:---:|------|
| **-1** | 8a-pre | 2주 | PyneCore 실측 + Alert 패턴 프로파일링 + Phase -1 리포트 |
| **1** | 8a | 3주 | Tier-0 공통 코어 (pynescript 포크 + PyneCore 이식 + 이벤트 루프) |
| **2** | 8b | 3주 | Tier-1 Alert Hook Parser + Tier-3 strategy() 네이티브 |
| **3** | 8c | 2주 | Tier-2 검증 CI + Tier-4 Variable Explorer |
| **4** | 8d | 2주 | Tier-5 LLM 하이브리드 + 베타 오픈 준비 |

**Horizon 구조:**
- **H1 Stealth (0-3m):** Sprint 8a-pre ~ 8d — 솔로 dogfood
- **H2 Build-in-Public (3-6m):** 외부 베타 10~30명
- **H3 Scale (6m+):** 수익화 + 공개 API

---

## 9. 결정 축 3가지 (사용자 결정 대기)

### 결정 1: Sprint 7d vs Sprint 8a-pre 우선순위 (긴급)

| 선택 | 내용 | 추천 |
|------|------|:---:|
| A | Pine 엔진 강화 먼저 (Sprint 8a-pre 즉시 착수) | ⭐ **Claude 추천** |
| B | OKX / Trading Sessions 먼저 (Sprint 7d 유지) | |

**A 추천 이유:**
- DrFX 실측으로 Phase -1 이미 1/3 완료 (모멘텀)
- Pine 엔진이 있어야 Trading Sessions도 의미 (실행할 전략이 Pine)
- Sprint 7d는 8a 완료 후 H1 내 편성 가능

### 결정 2: 렌더링 객체 범위 A vs B

- **범위 A (권장):** 좌표 저장 + getter만. 렌더링 NOP
- **범위 B:** 범위 A + Canvas/SVG 차트 렌더

**범위 A 추천 이유:** H1 Stealth엔 차트 렌더 불필요. QB 프론트엔드가 별도 라이브러리로 차트 담당.

### 결정 3: PyneSys SaaS 유료 구독

**확정:** **구독 안 함**

- PyneCore(Apache 2.0)만 참조 이식
- Vendor lock-in + QB 엔진 아키텍처와 호환 불가

---

## 10. 세션 자기 비판

### 잘한 것

1. 3-way evaluator 병렬 조사로 커버리지 확보
2. Gemini Deep Research 포함 다양한 입력 적극 활용
3. 반박 수용 지점 명확 ("설계 폭주" 진단 인정)
4. Phase -1 실측(DrFX BTC/USDT 백테스트)으로 v4 가설 검증 시작

### 아쉬운 것

1. **초기 "결정성 100%" 프레이밍 과장** — LLM 하이브리드 가능성 과소평가
2. **vectorbt vs Pine imperative 충돌을 v3 반박 전까진 회피** — 설계 폭주
3. **Sprint 일정 초기 추정 3-5배 버블** — "Sprint 8a 1~2주" 비현실적
4. **"순위 불변"을 방어적으로 2번 반복** — v4 Alert Hook Parser는 결국 기존 2순위 완전 대체
5. **DrFX 실측 전 설계만 4라운드 진행** — 실측 먼저였어야

### 세션에서 가장 값진 산출물

1. **v4 Alert Hook Parser + 3-Track** — Semantic Extraction을 넘어선 결정론 접근
2. **DrFX BTC/USDT 1H/4H 실측** — REVERSE 0%, TP 2:1 × 승률 32% 적자 구조 확인
3. **LLM 변환 코드 품질 실증** — IBM 47% 프레이밍 과장 확인 (실제 80~90%)
4. **Tier-0~5 최종 순위 + 12주 로드맵** — 실행 가능 형태

---

## 11. 핵심 교훈 (다음 세션을 위한 메시지)

**세션에서 가장 오래 기억해야 할 3줄:**

1. **`alert()`은 개발자의 자발적 매매 신호 선언 — 추측하지 말고 파싱하라.**
2. **매매 로직은 전체의 13% 이하 — Execution-First + Semantic Extraction은 같이 간다.**
3. **실측 없는 설계 5라운드 < 실측 1번.**

---

## 12. Sources (40+ URL)

### Pine 생태계
- [PyneCore (GitHub)](https://github.com/PyneSys/pynecore) / [PyneCore docs](https://pynecore.org/)
- [PyneSys 상용](https://pynesys.io/)
- [PineTS (QuantForge/LuxAlgo)](https://github.com/QuantForgeOrg/PineTS)
- [pynescript](https://github.com/elbakramer/pynescript) / [PyPI](https://pypi.org/project/pynescript/)
- [OpenPineScript](https://github.com/be-thomas/OpenPineScript)
- [pine-transpiler (Opus-Aether)](https://github.com/Opus-Aether-AI/pine-transpiler)
- [pyine (archived)](https://github.com/TomCallan/pyine)
- [Trading Strategy DeFi](https://github.com/tradingstrategy-ai/tradingview-defi-strategy) / [Bollinger 예제](https://tradingstrategy.ai/docs/programming/strategy-examples/bollinger-band-strategy.html)
- [PineConnector](https://www.pineconnector.com/)
- [3Commas Signal Bot](https://3commas.io/signal-bot)
- [QuantConnect LEAN](https://github.com/QuantConnect/Lean) / [Pine 거부 포럼](https://www.quantconnect.com/forum/discussion/5776/do-you-guys-accept-pinescript/)
- [Pineify 2026 가이드](https://pineify.app/resources/blog/converting-pine-script-to-python-a-comprehensive-guide)
- [PineGenius](https://github.com/veo555/PineGenius)
- [Pine Script Wizard](https://www.pinescriptwizard.com/)
- [awesome-pinescript](https://github.com/pAulseperformance/awesome-pinescript)
- [PinePyConvert](https://github.com/LotfiAghel/PinePyConvert)
- [FaustoS88/Pydantic-AI-Pinescript-Expert](https://github.com/FaustoS88/Pydantic-AI-Pinescript-Expert)
- [codenamedevan/pinescriptv6](https://github.com/codenamedevan/pinescriptv6)
- [Zorro Project](https://zorro-project.com/manual/en/conversion.htm)

### TradingView 공식
- [Pine Execution Model](https://www.tradingview.com/pine-script-docs/language/execution-model/)
- [Bar Magnifier](https://www.tradingview.com/support/solutions/43000669285-what-is-bar-magnifier-backtesting-mode/)
- [Strategy Properties](https://www.tradingview.com/support/solutions/43000628599-strategy-properties/)
- [TradingCode 체결 계산 분석](https://www.tradingcode.net/tradingview/calculate-order-fills/)
- [calc_on_every_tick 차이](https://www.tradingcode.net/tradingview/calc-tick-backtest-difference/)
- [Pine v2 ANTLR grammar 공식 공개](https://www.tradingview.com/pine-script-docs/v3/appendix/pine-script-v2-lexer-grammar/)
- [Pine v6 Reference](https://www.tradingview.com/pine-script-reference/v6/)

### 컴파일러/DSL 이론
- [Crafting Interpreters (Lox)](https://craftinginterpreters.com/)
- [CPython VM Internals](https://blog.codingconfessions.com/p/cpython-vm-internals)
- [Lua VM](http://lua-users.org/wiki/LuaImplementations)
- [Terraform HCL](https://octopus.com/blog/introduction-to-hcl-and-hcl-tooling)
- [Python ast 모듈](https://docs.python.org/3/library/ast.html)
- [Numba](https://numba.pydata.org/) / [llvmlite](https://github.com/numba/llvmlite)
- [AssemblyScript](https://www.assemblyscript.org/)
- [MLIR](https://mlir.llvm.org/) / [DSP-MLIR](https://arxiv.org/html/2408.11205v1)
- [ClickHouse Vectorized](https://chistadata.com/clickhouse-vectorized-query-processing/)
- [DuckDB](https://duckdb.org/why_duckdb) / [Dask Delayed](https://docs.dask.org/en/latest/delayed.html)
- [Futamura Projections](https://en.wikipedia.org/wiki/Partial_evaluation)
- [Truffle/GraalVM](https://www.graalvm.org/latest/graalvm-as-a-platform/language-implementation-framework/)
- [RestrictedPython](https://github.com/zopefoundation/RestrictedPython)
- [vectorbt](https://vectorbt.pro/features/indicators/) / [pandas-ta](https://github.com/twopirllc/pandas-ta)
- [numexpr](https://github.com/pydata/numexpr)

### LLM 번역 연구
- [IBM Lost in Translation (ICSE 2024)](https://research.ibm.com/publications/lost-in-translation-a-study-of-bugs-introduced-by-large-language-models-while-translating-code)
- [Amazon Oxidizer PLDI'25 / arxiv 2412.08035](https://arxiv.org/abs/2412.08035)
- [Amazon Q Transform](https://aws.amazon.com/q/developer/transform/)
- [EquiBench EMNLP 2025 / arxiv 2502.12466](https://arxiv.org/abs/2502.12466)
- [COBOL-Coder / arxiv 2604.03986](https://arxiv.org/html/2604.03986)
- [IBM Code Translation](https://research.ibm.com/projects/code-translation)

### 기타
- arXiv/ACM/IEEE Pine Script 형식화 논문 — **0건 확인** (2023-2026)
- [Lang-PINN (무관 참고)](https://arxiv.org/html/2510.05158v1)

---

## 13. Amendment Log

| 날짜 | 내용 |
|------|------|
| 2026-04-17 | 세션 완료 직후 최초 아카이브 |
| (예정) Phase -1 완료 후 | 실측 결과 기반 ADR-011 amendment 반영 |

---

## 14. 관련 ADR 체인

```
ADR-003 (2026-04-13) — Pine 런타임 안전성 (exec() 금지, 인터프리터 패턴 강제)
   ↓
ADR-004 (2026-04-15) — AST 인터프리터 방식 선택 (Python 트랜스파일·DSL 매핑 기각)
   ↓
ADR-011 (2026-04-17) — Alert Hook Parser + 3-Track Architecture ← 본 세션 결정
```

**주의:** ADR-011이 ADR-003/004를 **뒤집는 게 아니라 상위 아키텍처로 얹어진** 것. 기반 원칙(exec 금지, AST 인터프리터)은 유지.
