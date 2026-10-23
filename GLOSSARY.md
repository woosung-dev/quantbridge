# QuantBridge

TradingView Pine Script 전략의 백테스트·스트레스 테스트·최적화·Bybit Demo 트레이딩을 연결하는 퀀트 플랫폼의 용어집이다.
도메인 관계는 [도메인 개요](docs/domain/domain-overview.md), 구현 계약은 관련 설계 문서, 결정 이유는 `docs/adr/`에서 확인한다.

## Language

### Strategy Context

**Strategy**:
사용자가 등록한 Pine Script 원본과 파싱 결과를 보유하는 전략 엔티티.
_Avoid_: Algorithm, Script(원본 코드 문자열은 `pine_source`)

**pine_v2**:
Pine Script를 봉마다 해석하는 인터프리터이며, Pine 백테스트와 라이브 신호의 정본이다. 라이브의 조건부 진입 체결 권한은 주문 원장에 있다.
_Avoid_: transpiler, vectorbt 엔진, Pine v1

**Track**:
Pine 선언과 alert 유무에 따른 실행 분류. S는 strategy, A는 alert가 있는 indicator·library, M은 alert가 없는 indicator·library다.

**Coverage Analyzer**:
Pine의 지원 범위를 검사해 실행 가능 여부를 전체 단위로 판정하는 사전 검사기.
_Avoid_: parser(문법을 읽는 별도 역할)

**parse_status**:
저장된 Pine 원문의 판정으로, `ok`는 파싱·지원 검사 통과, `unsupported`는 파싱 성공·지원 범위 밖, `error`는 파싱 실패를 뜻한다. 저장 허용 여부와 실행 허용 여부는 별도다.

**Degraded Pine**:
지원 범위 안이지만 TradingView와 결과가 달라질 수 있어 실행 전 명시적 동의가 필요한 Pine 호출.

**Strategy Brief**:
백테스트 제출 전에 전략의 실행 가능성·신호·입력을 설명하는 브리핑. 실행 판정은 결정론 층이 소유하며 LLM 해설은 보조 설명이다.
_Avoid_: AI 분석 결과, parse preview

**Python View**:
Pine 원본을 읽기 쉽게 표현한 실행 불가·읽기 전용 Python 뷰. 원본과의 의미 동등성을 보증하지 않는다.
_Avoid_: transpile, Python 전략, Python으로 변환

**Python Research Strategy**:
서비스에서 철거된 과거 Python 연구 전략 개념. 현재 Code Strategy 및 읽기 전용 Python View와 구분한다.

**Generated Strategy**:
자연어 설명에서 생성한 Pine 정본과 읽기용 Python 초안. 사용자가 검토·적용하기 전에는 저장된 Strategy가 아니다.
_Avoid_: LLM 변환(기존 전략 번역과 구분)

### Verification Context

**Code Strategy**:
Pine·Python·TypeScript 실행 원문과 불변 버전으로 구성된 전략. 기존 Pine Strategy, Python View, 과거 Python Research Strategy와 구분한다.

**Backtest**:
한 전략을 고정된 입력과 과거 OHLCV로 실행한 시뮬레이션 결과.

**BacktestTrade**:
Backtest 시뮬레이션 내부의 개별 가상 체결 기록.

**Stress Test**:
완료된 Backtest를 바탕으로 전략의 강건성을 평가하는 분석.

**Optimizer**:
한 전략의 파라미터 공간에서 목표 지표를 비교하는 탐색.
_Avoid_: Optuna(채택하지 않은 도구)

**vectorbt**:
제품에서 제거된 과거 의존성. 현재 실행 엔진이나 지표 계산기의 이름으로 사용하지 않는다.
_Avoid_: backtest engine, 전략 실행기, 지표 계산 가속

### Execution Context

**Trading**:
검증된 전략을 Bybit Demo 계정에서 실행하는 도메인.
_Avoid_: exchange(별도 도메인 이름)

**LiveSignalSession**:
한 Strategy와 한 ExchangeAccount에 연결된 실시간 신호 자동매매 세션.
_Avoid_: TradingSession(자동매매 세션 엔티티 이름으로 사용하지 않음)

**LiveSignalEvent**:
신호 평가와 주문 발주를 연결하는 발송 상태 기록.

**Order**:
거래소에 발주되는 단일 주문.

**Kill Switch**:
손실·마진·포지션 한도 위반 시 주문을 차단하는 리스크 게이트.

**ExchangeAccount**:
사용자의 거래소 자격증명과 계정 모드를 보유하는 계정.

**ExchangeName**:
거래소 이름. 현재 제품이 허용하는 거래소는 Bybit 하나다.

**ExchangeMode**:
거래소 계정 모드. 현재 제품은 Bybit Demo만 허용하며 과거 live 값은 이력 조회용이다.
_Avoid_: testnet(계정 모드 이름)

**Trailing Stop Intent**:
진입 체결 뒤 포지션에 부착할 트레일링 스톱의 영속된 의도.

**Bracket / OCO**:
진입에 연결된 익절·손절 주문 묶음으로, 한쪽 체결 시 다른 쪽을 취소하는 관계.

### Data Context

**OHLCV**:
거래소·상품·봉 주기별 시가·고가·저가·종가·거래량 시계열.

**FundingRate**:
무기한 선물의 펀딩비율 시계열.

### Cross-cutting

**Signal**:
Strategy가 산출하는 진입·청산·alert 신호.

**Trust Layer**:
Pine 실행 결과의 동등성을 검증하는 회귀 안전망.

**Demo-first**:
거래소 주문·손익보호를 Bybit Demo 경로에서 검증하는 제품 원칙. 실자금 전환은 제품 범위 밖이다.
