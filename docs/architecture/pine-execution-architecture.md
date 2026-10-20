# Pine 실행 아키텍처

> **역할:** 현재 `pine_v2` 실행 계약의 진입점. 실제 구현은 [`apps/api/src/strategy/pine_v2/`](../../apps/api/src/strategy/pine_v2/), 결정 이유는 [`ADR-011`](../adr/011-pine-execution-strategy-v4.md)·[`ADR-014`](../adr/014-sprint-8b-8c-pine-v2-expansion.md), 2026-04 설계 과정은 `archive`(`docs/archive/architecture/2026-04-17-pine-execution-v4-design.md`)에 보존한다.

## 핵심 원칙

- Pine을 Python으로 변환해 `exec()`·`eval()`로 실행하지 않는다. `pine_v2`가 AST를 bar-by-bar로 해석한다.
- 실행 엔진의 정본은 `pine_v2`다. ★2026-08-06 에 vectorbt 의존성은 **제거됐다** — 「지표 계산 보조」라는 서술도 드리프트였고(코드 import 0건), 지표는 `pine_v2/stdlib.py` 가 pandas/numpy 로 직접 계산한다.
- 지원하지 않는 호출이 하나라도 있으면 부분 결과를 만들지 않고 Unsupported로 끝낸다.
- TradingView와 달라질 수 있는 degraded 호출은 백테스트 제출 시 명시 동의 없이는 실행하지 않는다.

## 실행 경로

```mermaid
flowchart LR
    S[Pine source] --> P[parser_adapter]
    P --> C[AST classifier]
    C -->|S: strategy| H[run_historical]
    C -->|A: indicator/library + alert| V[run_virtual_strategy]
    C -->|M: indicator/library, alert 없음| H
    H --> R[Backtest result]
    V --> R
    R --> X[Backtest · Stress Test · Optimizer]
```

| Track | 분류                                     | 실행 계약                                     |
| ----- | ---------------------------------------- | --------------------------------------------- |
| **S** | `strategy()` 선언                        | 네이티브 `run_historical` 경로                |
| **A** | `indicator()` 또는 `library` + alert     | `VirtualStrategyWrapper`가 전략 이벤트로 투영 |
| **M** | `indicator()` 또는 `library`, alert 없음 | 지표 pass-through로 `run_historical` 실행     |

분류 규칙의 정본은 `ast_classifier._classify_track`, 외부 진입점은 `compat.parse_and_run_v2`다.
Track A의 `next_bar_open`은 실제 alert 호출값을 시장가 인텐트로 등록하고 다음 봉 시작에 체결한다.
명시 청산을 진입보다 먼저 처리하며, 같은 방향 추가 진입은 생략하고 동봉 양방향 진입은 거부한다.
마지막 봉 인텐트는 미체결로 남는다. 기본 `bar_close`의 기존 edge-trigger 동작은 유지한다.
앱의 `BacktestConfig.freq`도 Pine 봉 context로 전달한다.
다음 봉 시장가 반전의 자본 비례 수량은 기존 포지션의 실현 후 gross 자본으로 계산한다. 증거금 사전 검사에서
거부되면 기존 포지션을 보존한다. 봉 시가에 체결한 시장가 진입은 같은 봉의 고저가로 청산 여부를 검사하며,
체결 전 고저가의 순서를 알 수 없는 종가·stop/limit 진입은 기존 진입 봉 청산 제외를 유지한다.

Pine v5 이하의 `and`/`or`는 모든 항을 평가하며 v6부터 단축 평가한다
([공식 버전 이전 계약](https://www.tradingview.com/pine-script-docs/migration-guides/to-pine-version-6/#lazy-evaluation-of-conditions)).
이 구분은 논리식 안의 `ta.*` 호출 이력에도 적용한다. 종료 거래의 손익은 Decimal 진입가·청산가·수량으로
계산한다. float 공간에서 뺀 손익을 Decimal로 포장하지 않는다.

비교 결과의 NA는 v5 이하에서 보존하고 v6에서는 false로 반환한다
([bool 버전 경계](https://www.tradingview.com/pine-script-docs/migration-guides/to-pine-version-6/#boolean-values-cannot-be-na)).
`crossover`·`crossunder`·`cross`도 현재 피연산자가 NA이면 같은 버전 계약을 따르지만,
현재 값은 유효하고 이전 값만 없으면 교차를 확인할 수 없으므로 false다.
v5 이하의 `and`·`or`는 NA를 false로 소비하여 bool을 반환하며, `not NA`는 true다.
버전은 compiler annotation에서 읽은 `BarContext.pine_version`을 표준 함수 호출까지 전달한다.
EMA의 초기값은 비NA 표본 length개의 SMA이며, bool 경계와 별개다.

전략 파싱 프리뷰의 `errors[].line`은 파서가 제공한 구조화된 1-based 행 번호를 보존한다.
`pynescript` 구문 오류는 `details.lineno`에서 읽으며, 메시지 문자열에서 위치를 추측하지 않는다.
위치 정보가 없는 오류는 `null`을 유지한다.

`timestamp`의 UTC 달력 인자는 음수 월·월말 초과 일자를 정규화한다
([공식 달력 계산 예시](https://www.tradingview.com/pine-script-docs/faq/times-dates-and-sessions/#how-can-i-plot-a-value-starting-n-months-or-years-back)).
날짜 문자열·비UTC 시간대와 지원 달력 범위 밖 값은 추측해 계산하지 않고 명시 오류를 반환한다.

### 체결 위상과 비용 경계

`strategy_state.Trade`는 진입·청산을 `bar_open`, `bar_close`, `intrabar_unknown`으로 구분한다.
시가 시장가 체결과 봉 내부의 조건부 체결을 같은 시각으로 간주하지 않는다. 이 위상은 내부 `RawTrade`까지
보존하며 공개 거래 응답이나 DB 컬럼을 늘리지 않는다.

`backtest/engine/holding_period.py`의 순수 `HoldingPeriod`가 거래별 MFE/MAE, equity 극값 근사와 펀딩 보유 여부를 함께 판정한다.
시가 진입봉은 보유하고 시가 청산봉의 이후 wick은 제외한다. 종가 진입봉의 이전 wick도 제외한다.
MFE/MAE는 확실히 전부 보유한 봉과 실제 진입·청산 가격으로 계산한다. 조건부 체결봉의 고저가 순서를
알 수 없으면 해당 wick을 보유 성과로 만들지 않는다.

별도 equity 극값 근사는 주문 전 시가, 확실히 전부 보유한 봉의 공통 high/low 가격점,
실제 종가 equity를 후보로 사용한다. 종가 진입 이전 wick은 제외하고 종가 청산 이전 wick은 포함한다.
봉 내부 체결로 노출이 변한 봉은 전체 포지션의 wick 조합을 제외하고 확인된 가격점만 사용하며 경고한다.
실제 종가 equity를 재사용하므로 이 근사로 종가 곡선·헤드라인 MDD를 다시 계산하지 않는다.
같은 봉의 high/low 선후는 알 수 없으므로 상승·하락 통계는 양방향 범위 근사다. 펀딩 봉 총액도 후보에
선차감하는 기존 근사를 유지한다. 정산과 wick의 실제 선후나 TradingView의 봉 내부 경로를 재현한 값은 아니다.

```mermaid
flowchart LR
    T[Trade 체결 위상] --> R[RawTrade 내부 메타데이터]
    R --> H[HoldingPeriod]
    H --> E[거래별 MFE · MAE]
    H --> I[equity 극값의 전체 보유 봉]
    H --> F[관측 정산의 펀딩 보유 판정]
    F --> C[같은 비용 배열을 equity · metrics에 공유]
```

펀딩은 관측한 정산 시각만 사용한다. 종가 진입에 그 봉의 앞선 정산을 소급 부과하지 않으며,
종가 청산 직전까지의 정산은 포함한다. 마지막 확정 봉도 `[시가, 시가 + cfg.freq)` 범위의 정산을 포함한다.
OHLCV 공백을 이전 봉으로 늘려 귀속하지 않는다. 봉 내부 체결 순서가 불명확하거나 정산에 해당하는 봉이
없으면 그 정산을 미반영하고 경고한다. 비용의 명목금액은 해당 봉 종가×수량의 근사이며, 정산 시점의
거래소 mark price를 재현한 것이 아니다.

`funding_data_incomplete`의 `True`는 관측 정산을 반영하지 못한 경우, `False`는 펀딩 노출이 없는 경우다.
보유가 있지만 과거 정산 일정의 독립적인 증거가 없으면 `None`(미검증)이다. rate의 최소·최대 시각이나
관측 간격만으로 완전성을 주장하지 않는다. `total_funding`과 `include_funding`으로 미계산/구 결과와
관측 비용의 계산을 구분하고, 화면에서도 미검증을 안내한다. 고정 8시간 주기를 가정하지 않는다
([Bybit 상품 정보](https://bybit-exchange.github.io/docs/v5/market/instrument),
[정산 이력](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate)).

### 파스 캐시 2층 (BL-832)

파싱 진입점은 `parser_adapter.parse_to_ast` **하나**다(n13 이 직접 `pynescript.ast.parse` 를 부르던 3곳을 여기로 모았다). 그 위에 캐시가 2층이다.

| 층 | 범위 | 무엇을 없애나 |
| --- | --- | --- |
| **L1** `lru_cache(maxsize=8)` | 프로세스 안 | 백테스트 1회의 중복 파스 4→1 (Track A 5→1) |
| **L2** 디스크(`PINE_AST_CACHE_DIR`) | 프로세스 **밖** | 프로세스 경계마다 다시 무는 콜드 파스 |

★**왜 디스크까지 가나** — 콜드 파스 1회는 실측상 `s5_ema_trend` 2.69초 · `s3_rsid` 11.47초 · `i3_drfx`(38,954B) **53.38초**이고, celery `worker_max_tasks_per_child` 재활용 · uvicorn 워커 · 테스트 프로세스가 각각 자기 콜드를 문다. L1 만으로는 그 경계를 못 넘는다.

★★**그 초의 정체는 「느린 코드」가 아니다** — `s3_rsid` cProfile 에서 `ParserATNSimulator.closure_` 의 cumtime 이 **35.77/36.96초(96.8%)** 다. ANTLR Python 런타임의 ATN 클로저 계산이고, **파서 층을 손대는 축(SLL 2단계·기동 워밍·문법 모호성 축소)은 이 성분을 못 건드린다**([BL-829] 기각 tombstone = `docs/backlog-deferred.md` 헤더). 줄이는 방법은 **다시 파싱하지 않는 것** 하나다.

- **캐시 키** = `sha256(스키마 버전 ∥ pynescript 버전 ∥ 소스)`. 버전이 바뀌면 미스다 — 업그레이드 후 낡은 AST 가 조용히 살아남으면 안 된다.
- **실패는 캐시되지 않는다.** 캐시 읽기가 어떤 이유로든 실패하면(동시 쓰기·클래스 소멸·손상) 조용히 정상 파스로 떨어진다 — 캐시는 파스를 **못 막는다**.
- **용량 상한**(`PINE_AST_CACHE_MAX_BYTES`, 기본 512MiB) 초과 시 mtime 오래된 것부터 소각한다. 파스 엔드포인트에 소스 길이 상한이 없어([BL-831]) 캐시 표면이 임의 입력으로 채워질 수 있다.
- ★**테스트는 기본 비활성**이다(`tests/conftest.py` autouse). 켜 두면 캐시가 테스트 프로세스 사이에서도 살아남아 파스 계수를 바꾼다 — 실제로 n13 계수 테스트 3건이 그렇게 red 였다.
- 판정은 **초가 아니라 계수·digest 동일성**이다: `test_parse_ast_disk_cache.py`(10건) · `test_parse_call_census.py`(6건).

## 지원 범위와 Trust Layer

`coverage.py`의 지원 집합과 `interpreter.py`의 실제 바인딩은 함께 바뀌어야 한다. 이 둘의 정합과 실행 회귀는 [`trust-layer-architecture.md`](./trust-layer-architecture.md)가 설명하며, 사용자에게 보이는 지원/미지원 목록은 [`supported-indicators.md`](../domain/supported-indicators.md)가 맡는다.

함수 지원을 추가할 때는 다음을 한 변경으로 끝낸다.

1. `stdlib.py` 또는 interpreter에 의미론을 구현한다.
2. `coverage.py`의 지원 집합을 갱신한다.
3. 단위 테스트와 필요 시 corpus fixture를 추가한다.
4. Track·결과 의미가 바뀌면 이 문서와 Trust Layer 회귀 기준을 함께 갱신한다.

## 소비자 경계

Backtest가 `pine_v2` 실행의 단일 소비자 경계다. Optimizer와 Stress Test는 이를 재실행하거나 완료된 Backtest 산출물을 사용한다. 따라서 실행 의미론을 바꾸면 세 도메인의 회귀를 함께 검증한다.

★**실행이 아닌 소비자가 하나 더 있다 — 전략 브리핑**([ADR-040](../adr/040-strategy-brief-outside-trust-layer.md)).
`GET /api/v1/strategies/{id}/brief` 는 `pine_v2` 를 **실행하지 않고** 정적 층 넷만 읽는다 —
`ast_extractor.extract_content`(선언·input·주문호출+줄번호) · `coverage.analyze_coverage`(판정·미지원) ·
`ast_classifier.classify_script`(Track) · `signal_extractor.SignalExtractor`(신호 변수).
⇒ **실행 의미론을 바꿔도 브리핑은 안 깨지지만, 이 네 모듈의 반환 형태를 바꾸면 브리핑이 깨진다.**
★`StrategyCall` 에 `line` 이 붙어 있고 그 값이 화면의 「소스 어디서 나오나」다 —
`tests/fixtures/pine_corpus_v2/ast_content_report.json` 이 그 계약을 strict equality 로 잠근다.

현재 용어·관계의 짧은 정본은 [`CONTEXT.md`](../../CONTEXT.md), 도메인 상태는 [`domain-overview.md`](../domain/domain-overview.md)에 둔다.
