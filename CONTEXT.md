<!-- QuantBridge 도메인 헌법 — 모든 코드·명명·설계가 우선 따르는 용어/관계 SSOT (methodology Stage 0) -->

# QuantBridge — Context

TradingView Pine Script 전략을 가져와 **백테스트 → 스트레스 테스트 → 최적화 → 데모/라이브 트레이딩** 한 파이프라인으로 잇는 퀀트 플랫폼. 본 문서는 도메인 용어의 canonical 정의와 경계를 고정하는 헌법이며, 충돌하는 명명/코드는 즉시 정렬한다.

> **SSOT 위임:** 컬럼 정의 = [`docs/reference/domain/erd.md`](docs/reference/domain/erd.md) · 엔티티 책임 = [`docs/reference/domain/entities.md`](docs/reference/domain/entities.md) · 상태 전이 = [`docs/reference/domain/state-machines.md`](docs/reference/domain/state-machines.md) · 결정 근거 = `docs/decisions/`(ADR). 본 문서는 **용어/관계** 만 보유.

## Language

### Strategy Context

**Strategy**:
사용자가 등록한 Pine Script 원본(`pine_source`) + 파싱 결과를 보유하는 전략 엔티티.
_Avoid_: Algorithm, Script(원본 코드 문자열은 `pine_source` 로 한정)

**pine_v2**:
Pine Script 를 트랜스파일 없이 AST 를 bar-by-bar 해석·실행하는 자체 인터프리터이자 백테스트·라이브 **신호**의 단일 진실(SSOT).
★**신호이지 체결이 아니다.** 백테스트에는 거래소가 없으므로 시뮬이 곧 거래소이고 체결도 `pine_v2` 가 정한다. 라이브에는 진짜 매칭엔진이 있으므로 **조건부 진입 체결의 권한은 주문 원장에 있다** — 원장이 증언하지 않은 체결을 엔진이 만들지 않고, 증언하면 엔진의 봉·트리거 판정과 무관하게 체결한다([ADR-025](docs/decisions/025-conditional-fill-ownership.md) / [BL-595]). 그 결과 **라이브 재생은 「전략 + OHLCV」만으로 재현되지 않는다** — 원장이 입력에 들어간다. 백테스트 경로는 인자 기본값으로 byte-identical 이며 테스트가 그 경계를 집행한다.
_Avoid_: transpiler, "vectorbt 엔진", Pine v1(철거됨, Sprint 59)

**Track**:
pine_v2 가 스크립트 선언을 분류해 실행 경로를 정하는 라우팅 분류 — **S**(strategy 선언 → native `run_historical`) / **A**(indicator|library + alert → `run_virtual_strategy` 가상 래퍼) / **M**(indicator|library, alert 없음 → 지표 pass-through `run_historical`). `library` 선언도 indicator 와 동일하게 alert 유무로 A/M 분기(`ast_classifier._classify_track`).

**Coverage Analyzer**:
백테스트 제출 시점에 미지원 함수 포함 여부로 실행 가능성(`is_runnable`)을 all-or-nothing 판정하는 사전 검사(ADR-003).
_Avoid_: parser(별개 — 파서는 문법만, 지원범위 판정은 안 함)

**parse_status**:
create/update 시 파서가 즉시 set 하는 터미널 값으로 `ok` 또는 `error` 만 사용(`unsupported` 는 enum 예약·미사용).

**Degraded Pine**:
`heikinashi` / `request.security` / `timeframe.period` 처럼 supported 지만 TradingView 와 결과가 달라질 수 있는 호출 — backtest submit 시 `coverage.has_degraded` 이면 `allow_degraded_pine=true` 명시 동의 없이는 차단(Trust Layer, `backtest/service.py` 의 `has_degraded` 분기).

### Verification Context

**Backtest**:
한 Strategy 를 과거 OHLCV 에 대해 pine_v2 로 실행한 시뮬레이션 결과(불변 입력 + 상태 + `metrics` JSONB).

**BacktestTrade**:
Backtest 시뮬레이션 내부의 개별 가상 체결 기록.

**Stress Test**:
완료된 Backtest 위에서 Monte Carlo / Walk-Forward / Cost-Assumption / Param-Stability 로 강건성을 평가하는 분석.

**Optimizer**:
한 Strategy 의 파라미터 공간을 Grid / Bayesian(scikit-optimize) / Genetic(자체 GA) 으로 탐색하는 실행(엔티티 = `OptimizationRun`, ADR-013). ★**ADR-013 은 `docs/decisions/` 에 파일이 없다**(결번) — 실체는 삭제된 dev-log 이고 git 에 살아 있다: `git show 94da86b1^:docs/dev-log/2026-05-12-sprint54-bayesian-genetic-grammar-adr.md` ([BL-504] · 소급 ADR 작성은 [BL-658]).
_Avoid_: Optuna(채택 안 함)

**vectorbt**:
★**제거됨(2026-08-06)** — 묘비로 남긴다. ADR-011 이 실행 엔진에서 _지표 계산 전용_ 으로 강등했고,
그 뒤 **의존성 자체가 제거**됐다. 강등 시점의 정의(「`ta.*` 지표 계산 가속」)조차 실제와 달랐다 —
`apps/api/src` 는 vectorbt 를 **한 줄도 import 하지 않았고**(2026-08-06 실측: 언급 16곳 전부
주석/독스트링), `ta.*` 는 `pine_v2/stdlib.py` 가 pandas/numpy 로 **직접** 계산한다.
유일한 소비처는 라이브러리 설치 확인용 smoke 테스트 1개였다.
_Avoid_: backtest engine, 전략 실행기, "지표 계산 가속"(이 표현도 드리프트였다)

### Execution Context

**Trading**:
검증된 Strategy 를 거래소에서 데모/라이브로 실행하는 도메인(구 `exchange` 도메인 통합 — ADR-018).

**LiveSignalSession**:
한 Strategy 를 실시간 신호로 자동매매하는 활성 세션(`is_active` bool, user 당 active ≤ 5). **현재 Bybit + demo 계정만 허용** — live 는 `AccountModeNotAllowed`(BL-003 mainnet runbook 전, `trading/services/live_session_service.py`).
_Avoid_: **TradingSession**(미구현 phantom — 실제 lifecycle 은 LiveSignalSession + Order + LiveSignalEvent). ★단 `strategy/trading_sessions.py` 의 `TradingSession(StrEnum)` 은 **별개 개념**(asia/london/ny 세션 시간대 게이트, Sprint 7d)으로 현역 — phantom 은 엔티티/테이블 이름으로서의 사용을 말한다.

**LiveSignalEvent**:
신호 평가와 주문 발주 사이의 transactional outbox 레코드(`pending → dispatched / failed`).

**Order**:
거래소에 발주되는 단일 주문(`pending → submitted → filled / rejected / cancelled`, 조건부 UPDATE race-winner).

**Kill Switch**:
손실/마진/포지션 한도 위반 시 주문을 차단하는 리스크 게이트(엔티티 = `KillSwitchEvent`, active = `resolved_at IS NULL`). 트리거별 scope 상이 — `cumulative_loss` 는 strategy 단위, `daily_loss`/`api_error` 는 exchange_account 단위.

**ExchangeAccount**:
사용자별 거래소 API Key 를 AES-256(Fernet) 암호화 보관하는 계정(평문 미저장, 응답은 마스킹).

**ExchangeName**:
지원 거래소 enum (`bybit` / `binance` / `okx`). 단 모든 `(ExchangeName, ExchangeMode, has_leverage)` 조합에 provider 가 있는 건 아님 — 실제 라우팅 SSOT 는 `trading/registry.py` PROVIDER_REGISTRY(현재 bybit demo±leverage / okx demo / bybit live).

**ExchangeMode**:
거래소 실행 모드로 `demo` 또는 `live` 두 값만 존재(testnet 모드 제거됨). demo 의미는 거래소마다 다름 — Bybit demo = 실 매칭엔진, OKX demo = CCXT sandbox.
_Avoid_: testnet(모드 이름으로는 미사용)

**Trailing Stop Intent**:
`Order.trailing_stop` 에 영속된 트레일링 _의도_ 로, entry `create_order` 에 절대 주입하지 않고 체결 후 `place_trailing_stop` task 가 `set_trading_stop` 으로 포지션에 부착한다.

**Bracket / OCO**:
entry 에 부착된 TP/SL 묶음으로, 현재 자율 exit 는 거래소 네이티브 OCO 가 형제 취소를 처리(app-side sibling-cancel 은 standalone-trigger 발주 시점 이연).

### Data Context

**OHLCV**:
거래소별 캔들 시계열(`ts.ohlcv` TimescaleDB hypertable). market_data 는 공개 REST 없는 내부 전용 subdomain.

**FundingRate**:
Perpetual Futures 펀딩비 시계열(`funding_rates`).

### Cross-cutting

**Signal**:
Strategy 가 산출하는 entry / exit / alert 신호(라이브에서는 LiveSignalEvent 로 outbox 화).

**Trust Layer**:
pine_v2 결과의 3-Layer parity 를 CI 에서 검증하는 회귀 안전망(ADR-020).

**Demo-first**:
라이브 손익보호(TP/SL·트레일링)를 데모 경로로 먼저 빌드하고 실자금 라이브는 마지막에 cutover 하는 원칙.

## Relationships

- 한 **User** 가 모든 엔티티의 소유권 단위 — 다른 도메인은 `user_id` 로 종속.
- 한 **Strategy** 는 0..N **Backtest** 를 생성(삭제 RESTRICT, 참조 중이면 409).
- 한 **Backtest** 는 0..N **Stress Test** 의 입력(삭제 CASCADE).
- 한 **Optimizer** 실행은 한 **Strategy** 의 파라미터 공간을 탐색.
- **Optimizer**·**Stress Test** 는 backtest 의 `run_backtest`(= pine_v2 `v2_adapter.run_backtest_v2`) 엔진을 **재실행**한다 — Optimizer = param combo 마다, Stress Test = WFO/Param-Stability/Cost-Assumption cell 마다(단 Monte Carlo 는 완료 **Backtest** trades 재표집이라 엔진 미재실행). v2_adapter 변경은 이 3 소비자에 동시 영향(BL-388/389/391).
- 한 **LiveSignalSession** 은 한 **Strategy** + 한 **ExchangeAccount** 를 참조한다. ★**Backtest 참조는 없다** — `trading.live_signal_sessions` 에 그런 FK 가 없고 trading 모듈 전체에 backtest 참조가 없다(2026-07-28 실측으로 "선택적 reference Backtest" 표기 정정). 라이브↔백테스트 대조는 FK 가 아니라 **같은 `strategy_id`** 로 잇는다.
- 한 **LiveSignalEvent** 는 0..1 **Order** 로 dispatch.
- **Kill Switch** 는 모든 **Order** 발주 전 게이트.
- **OHLCV** 는 **Backtest** 와 **Trading** 양쪽에 공급(Backtest=배치 Provider, Trading=실시간 WebSocket 별도 경로).
- **Provider 라우팅 SSOT**: `(ExchangeName, ExchangeMode, has_leverage)` 튜플이 `trading/registry.py` 에서 ExchangeProvider 구현으로 dispatch(예: bybit·demo·leverage=True → BybitFuturesProvider).

## Example dialogue

> **Dev:** "라이브 세션을 시작하면 **TradingSession** 행이 하나 생기나요?"
> **Domain expert:** "아니요. **TradingSession** 테이블은 없습니다(phantom). 실제로는 **LiveSignalSession**(활성 세션) + 신호마다 **LiveSignalEvent**(outbox) + 거래소 **Order** 3개로 구성됩니다."
>
> **Dev:** "그럼 백테스트는 vectorbt 가 돌리는 거죠?"
> **Domain expert:** "아니요. 실행 엔진은 **pine_v2** 인터프리터이고, vectorbt 는 **아예 없습니다**(2026-08-06 의존성 제거). 한동안 '지표 계산 보조'로 적혀 있었지만 그것도 실제와 달랐어요 — `apps/api/src` 는 vectorbt 를 한 줄도 import 하지 않았고 `ta.*` 는 `pine_v2/stdlib.py` 가 직접 계산합니다(ADR-003/011)."
>
> **Dev:** "트레일링 스톱은 진입 주문에 같이 넣나요?"
> **Domain expert:** "절대 안 됩니다. `Order.trailing_stop` 은 _의도_ 만 영속하고, 체결 후 `set_trading_stop` 으로 포지션에 부착합니다. entry 에 넣으면 ccxt 가 trading-stop 으로 라우팅해 진입이 깨집니다."

## Flagged ambiguities

- **"TradingSession"** 이 라이브 lifecycle 을 가리키는 데 쓰임 → 해소: 그런 테이블 없음. **LiveSignalSession** + **Order** + **LiveSignalEvent** 사용. _잔여 드리프트_: `docs/reference/domain/domain-overview.md` §4.1 FK 표 + `entities.md` ENT-007/008 이 phantom `trading_sessions`/`live_trades` 를 실재처럼 표기 → Phase 2 정정 완료(본 브랜치).
- **"engine" / "backtest engine"** 이 vectorbt 를 지칭 → 해소: 실행 엔진 SSOT 는 **pine_v2**. ★2026-08-06 에 한 겹 더 벗겼다 — 「vectorbt 는 지표계산 전용」이라는 강등 서술**조차** 드리프트였고(코드 import 0건), 의존성 자체를 제거했다. _잔여 드리프트_: `system-architecture.md` L82/L143 → Phase 2 정정 완료.
- **"exchange"** 가 별도 도메인으로 쓰임 → 해소: **Trading** 으로 통합(ADR-018), `apps/api/src/exchange/` 부재. _잔여 드리프트_: `entities.md` ENT-009 가 `domain: exchange` / `apps/api/src/exchange/models.py` 표기 → Phase 2 정정 완료(본 브랜치).
- **"testnet"** vs **"demo"** → 해소: testnet 모드 제거됨. **ExchangeMode** = `demo | live` 뿐이고 demo 의미는 거래소별 상이(Bybit demo = 실 매칭엔진 / OKX demo = CCXT sandbox).
- **"unsupported"**(parse_status) → 해소: 파서는 `ok`/`error` 만 set. 미지원 함수 판정은 백테스트 제출 시 **Coverage Analyzer**(ADR-003 all-or-nothing).
- **"transpile"** → 해소: pine_v2 는 AST 를 해석(interpret)하며 Python 으로 트랜스파일하지 않음(`exec`/`eval` 금지, ADR-003).

---

## 변경 이력

- **2026-06-30** — 초안 작성(verification loop Stage 0). `docs/reference/{domain-overview,entities,state-machines}.md` + ADR-003/011/013/018/020 + 코드(`trading/models.py`, `pine_v2/compat.py`) 교차 ground. Flagged ambiguities 6건 중 3건은 Phase 2 문서 정정으로 연계.
- **2026-06-30** — codex consult gate 7건 보정(직접 코드 검증 후 반영) — Track A/M 에 `library` 포함 / Degraded Pine·allow_degraded_pine 신설 / LiveSignalSession Bybit-demo 한정 명시 / ExchangeName 신설 + registry SSOT / demo 의미 거래소별 상이 / Kill Switch 트리거별 scope / Provider 라우팅 튜플 relationship.
- **2026-08-06** — **vectorbt 항목을 묘비로 전환**(ci-diet 후속 dead-code-sweep). 의존성 4종
  (`vectorbt` · `pandas-ta` · `aioboto3` · `orjson`)을 제거했고 lock 에서 **47 패키지**가 빠졌다
  (numba · matplotlib · plotly · boto3 계열 포함). **numpy/pandas/scipy/scikit-learn 버전은 불변**이라
  pine_v2 수치에 영향이 없다. ★교훈: 「지표 계산 전용으로 강등」이라는 **헌법의 서술 자체가 드리프트**
  였다 — 강등 후 실제로는 import 0 건이었는데 아무도 다시 재지 않았다. **강등도 측정 대상이다.**
- **2026-08-05** — **pine_v2 정의 정밀화**([ADR-025] / [BL-595]). 「백테스트·라이브 신호의 단일 진실」은 **신호**에 대한 진술이고, 라이브의 **조건부 진입 체결** 권한은 주문 원장으로 옮겼다. 좁힌 것이 아니라 원래 그 문장이 뜻하던 경계를 코드와 맞춘 것이다 — 그동안 코드가 라이브에서도 체결을 정하고 있었고, 그것이 `position_divergence` 사망 5건의 뿌리였다. 대가는 **라이브 재현성**(원장이 재생 입력에 들어간다).
