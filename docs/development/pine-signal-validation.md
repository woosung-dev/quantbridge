# Pine 신호 교차 검증

PRD §5의 결과·가정 공개와 ADR-040/042의 결정론 판정 경계를 따르는 **로컬 검증 도구**다.
운영 전략 등록이나 주문을 수행하지 않는다. 외부 LLM 없이 원본 Pine 실행과 검토한 Python 계산을 대조한다.

## 두 실행 경로

1. **원본 Pine → `pine_v2`**: `run_historical(..., capture_signals=True, timeframe="1h")`가
   실제 실행한 `plotshape`·`plotchar`·`plotarrow`·`alertcondition`·`alert`의 조건값과 소스 위치를 수집한다.
   일반 history의 최근 500개 제한과 독립적이다. 방향은 원본을 검토한 manifest가 명시한다.
   실행된 degraded 호출도 기록한다. 빈 실행 목록만으로 임의 소스의 동등성을 보증하지 않으며, 현재 분기 미실행
   예외는 검토한 UT Bot 원본의 정확한 hash와 `h=false`에 한정한다. 운영 coverage 동의 규칙은 유지한다.
   수집 옵션은 계산·주문을 바꾸지 않는다. 화면에 그리지 않는 `plot` 등의 인자와 문자열 포맷 인자도 두 모드에서
   같은 순서로 한 번씩 평가하고, 관측 기록만 수집 여부에 따라 달라진다.
2. **검토한 Python 계산 → 사건 → 선물 원장**: `scripts/pine_validation/oracles.py`의 정적 계산을 사용한다.
   Pine 인터프리터·stdlib를 재사용하거나 임의 Python을 `exec/eval`하지 않는다. EMA/SMA/RSI/Supertrend/UTBot
   계산기 이름만 같다는 이유로 특정 공개 지표와 동일하다고 판정하지 않는다. 원본 hash·입력·신호 줄을 함께 고정한다.
   `supertrend_cloud`는 두 밴드의 네 교차 표식을 중복 보존하고, `supertrend_v1`은 추세 전환 alert만 읽는다.
   `multi_sma_cross`는 20/200·50/200 교차 alert를 사용하며 7봉 동안 유지되는 화면 표식과 구분한다.
   `pucci_trend`는 원문 분모 1000·가격 필터·마지막 방향 상태를 그대로 계산한다.
   `emax2_cross`는 검토한 v4 EMAx2 원문의 일반/강한 신호 네 호출과 filter·NA 비교·`not`을 계산한다.
   slow EMA 준비 전 양방향 신호도 원문 결과이며 일반 `ema_cross`에 같은 초기 신호를 넣지 않는다.

독립 EMA는 실제 TradingView v4/v5에서 초기 제어 수열을 실행해 확인한 비NA `length`개 SMA seed를 사용한다.
같은 평가창의 OHLCV만 같아도 이전 계산 이력이 다르면 EMA와 경계 신호가 달라질 수 있다. 비교에는 초기 이력도
맞추고, 짧은 이력의 불일치와 이력을 연장한 재검증을 별도로 보존한다. 엔진과 Python이 같다는 사실만으로
관측하지 못한 TradingView 이력까지 같다고 추정하지 않는다.

기존 **Python View는 읽기 전용**이며 이 실행 경로와 별개다. 범용 Pine→Python 변환기는 아니다.
기존 indicator→strategy 슬라이싱도 원본 조건식·범위를 보존할 수 없으면 성공을 반환하지 않는다.

`strategy_adapter.adapt_strategy`는 검토한 manifest 위치의 신호를 실제 전략 진입으로 연결한다.
원본 계산 body를 보존하고 선언과 선택 호출의 첫 인자만 AST의 정확한 범위로 편집한다. 조건은 호출 위치에서
한 번 평가한 임시 변수로 원래 plot/alert와 진입문이 함께 읽는다. 원본 hash·변환 hash·변환 Pine·줄 대응표를
보고서에 남긴다. 단독 최상위 호출이나 안전한 인자 평가를 증명하지 못하면 변환을 거부한다.
방향은 manifest가 명시하며, 같은 방향 복수 표식은 추가 진입을 만들지 않는다.
원본 실행·OHLCV·방향 바인딩의 선행 조건을 통과한 셀에서는 Python oracle 생성 여부와 별도로
앱 백테스트를 시도한다. `app_status=ok` 또는
`executed=true`는 앱 엔진 실행 사실이고, 독립 사건 원장과의 `exact_match`가 아니다. Python
사건이 없으면 `missing_signal_ledger`로 남기며 앱 거래가 있었다는 이유로 신호 동등성을 주장하지 않는다.

## 비교 계약

| 항목 | 기준 |
| --- | --- |
| 시장 | `BYBIT:BTCUSDT.P` — BTC/USDT 무기한 선물 |
| 기간 | 실행일의 최근 확정 UTC 일봉 경계까지 calendar 1년, 별도 warmup |
| 타임프레임 | 1h·4h·1d, 누락·중복 없는 동일 OHLCV |
| 후보 | Boost ≥100 공개 소스, 중복 id/URL·원본 SHA 중복 구분, 최대 100개 |
| 사건 | 조건 평가 봉·방향·확정 시각·표시 offset 시각을 각각 비교 |
| 선물 | 롱/숏 반전, 단일 포지션, 같은 방향 추가 진입 없음, 명시 청산 지원 |
| 신호·원장 대조 체결 가정 | 다음 봉 시가, 1배, 고정 1수량, 수수료·슬리피지·펀딩 0 |

마지막 봉 신호는 미체결로 남긴다. 종료 시 강제 청산하지 않는다. 이 단순 원장은 실제 거래소 체결·
청산·증거금 엔진을 대체하지 않는다. TV 지표의 신호를 같은 선물 규칙으로 해석하는 비교이며,
TradingView Strategy Tester의 손익을 수집하지 않았다면 그 손익까지 검증했다고 말하지 않는다.

앱의 indicator+alert 경로도 `next_bar_open`을 실제 시장가 인텐트 큐로 전달한다. 앱 체결 통합 검사는
`run_backtest_v2`의 종료·열린 거래를 별도 Python 원장과 비교하며, 신호 비교만으로 앱 체결까지 통과했다고
말하지 않는다. 초기 계산 이력은 양쪽이 같아야 한다. warmup 중의 포지션을 유지한 앱 실행과 평가창 시작에
빈 포지션으로 시작한 단순 원장 실행을 섞어 비교하지 않는다.

빈 사건, 한 방향만 발생한 사건, 자료 누락, 원본 hash 불일치, 미지원 계산은 통과하지 않는다.
`exact_match`는 개별 비교의 일치다. runner의 기본 최소 지표 수는 10이고 manifest의
`minimum_indicators`는 10~100 정수다. **50개 연구에서는 이를 50으로 고정하고 `--limit 50`으로
50개 고유 공개 원본 × 1h·4h·1d = 150개 셀을 분모로 유지한다.** runner의 `expected_pairs`는
`max(minimum_indicators, 선택한 지표 수) × 3`이며 `evaluated_pairs`, `exact_pairs`와 구분한다.
신호 없는 원본, 미지원·런타임 오류, 참조 부재, 불일치도 평가 분모에 남긴다. 소스 SHA가 같은 게시물은
다른 ID여도 독립 지표 수에 보태지 않는다. 전체 `passed`는 최근 확정 UTC 일봉 경계의 calendar 1년,
최소 고유 원본 수, 중복 없음, 모든 셀의 strict `exact_match`가 함께 필요하다.
짧은 기간의 일치 결과도 기록하지만 전체 성공으로 승격하지 않는다.
기본 입력에서 한 방향만 나와 입력을 바꿔 검증한다면 기본 결과를 보존하고 변경한 입력을 TV·Pine·Python
세 경로에 동일하게 명시한다. 변경한 입력의 결과로 기본 입력 검증을 대체하지 않는다.

## 비용 포함 성과는 별도 판정

`evaluation.py`는 manifest의 `evaluation` 계획으로 비용 포함 앱 엔진 결과를 측정한다. 계획에는
UTC 일봉 경계의 train·validation·holdout, 초기자본, 자본 대비 포지션 비율, 수수료·슬리피지 비율과
`cost_basis` 근거를 성과 실행 전에 고정한다. `registered_at` 문자열만으로 사전등록을 증명하지 않는다.
이미 지난 holdout을 평가한 결과는 `retrospective_not_untouched`이며, 이전 시점으로 선언했더라도
독립 확인이 없으면 `declared_preregistered_unverified`다. 회고 구간을 미래 미사용 holdout이라고 부르지 않는다.

각 타임프레임의 train·validation·holdout·full 네 구간을 수수료·슬리피지 기본값과 2배 스트레스에서
각각 실행한다. 구간 이전 OHLCV는 지표 초기 계산에만 쓰고 미래 봉은 실행기에 주지 않는다. 구간마다
포지션을 다시 시작하며 종료 시 강제 청산하지 않는다. 순손익에는 열린 포지션의 평가손익이 포함될 수
있어 닫힌 거래 손익과 분리해 읽는다. 펀딩은 관측 정산만 반영하고 2배 비용 스트레스에서 펀딩을 2배로
늘리지 않는다. 펀딩 파일은 출처·심볼·관측시각·SHA와 중복 없는 유한 비율을 확인하지만 과거 전체
정산 일정의 완전성을 증명하지 못한다. 자료 없음은 비용 0의 실측 증거가 아니며, 관측 정산이 있어도
`funding_status=observed_settlements_only`를 유지한다. 엔진의 `funding_data_incomplete`가 `None`
또는 `false`여도 과거 정산 일정 전체를 확인했다는 뜻으로 해석하지 않는다.

`performance.status=completed`는 고정 가정으로 엔진 실행을 끝냈다는 뜻이다. 원본 native 신호,
Pine↔Python 사건, 앱 원장 일치나 추천 적격을 뜻하지 않는다. 성과 임계값과 후보 선택 기준은 결과를
보고 바꾸지 않고 회차 계획에 보존한다. 성과 수치·순위는 해당 실행의 입력·코드 hash와 가정을 함께
제시하고, 투자 권유나 미래 수익 보장으로 표현하지 않는다.

## 선택형 청산 정책의 비교

추세 지표 확대는 **원문 수집 → 정적 선별 → 실제 실행 → 신호·원장 대조 → 비용 포함 성과**를
각각 집계한다. 목표가 실행 가능한 50개라면 수집한 50개를 분모 충족으로 대신하지 않는다.
원문 SHA 중복을 제외하고 같은 EMA·SSL 등의 계열 변형은 별도로 표시한다.
파싱 시간 제한은 `parser_timeout`으로 보존하며 원문 문법 오류나 미지원 함수라고 단정하지 않는다.

V1은 원래 방향 신호를 같은 선물 규칙으로 실행한다. V2는 **동일 신호에 별도 청산 정책을 적용한 실험**이다.
V2의 SL·부분 익절·트레일링으로 달라진 청산을 원본 TradingView 지표와의 신호 불일치로 집계하지 않는다.
두 봉의 주기·확정 범위, SL 여유 방향, 익절 R 배수·수량, 트레일링 활성화와 간격, 같은 방향 신호의
재설정 여부를 성과 측정 전에 확정한다. 정해지지 않은 값을 기본값으로 숨기지 않는다.

R은 실제 진입 체결가와 최초 SL 사이 거리로 계산해야 한다. 다음 봉 시가 체결을 종가 체결로 대신하거나,
진입 봉의 미래 고저가로 SL을 계산하면 안 된다. 첫 진입 봉부터 보호되는지, 갭·동봉 SL/TP 충돌·반전 시
이전 주문 취소·잔량·수량 보존을 수기 기대값으로 먼저 검증한다. 진입가 SL은 수수료·펀딩을 뺀 순손익
본전을 뜻하지 않는다. 봉내 순서를 하위봉으로 재현하지 않았다면 OHLC 근사로 명시한다.

V1/V2는 같은 OHLCV·초기 이력·진입 크기·비용·평가 구간을 사용한다. 부분 TP가 생기면 기존 시장가 전용
실험의 `maker_fee=0`을 그대로 복사하지 않는다. 최초 진입 포지션 수와 부분 종료 leg 수, 닫힌 손익과
열린 잔량 평가손익을 각각 공개한다. 공통 청산 프리미티브의 지원 범위와 라이브 차단은
[지원 계약](../domain/supported-indicators.md#23-strategy)을 따른다. 정책 래퍼와 첫 진입 봉 보호를
구현·검증하기 전에는 공통 엔진 검사 통과를 V2 성과 측정 완료로 보고하지 않는다.

## 수집과 실행

TradingView는 로그인된 Playwright MCP의 실제 UI로 조작한다. 원본은 공개 게시물의 **Source code**를 눌러
발생한 응답에서 읽고 작성자·URL·관측 Boost·관측 시각·원본 SHA-256을 보존한다. 보호된 소스는 제외한다.
사용자 차트에서 기존 지표를 삭제하지 않는다. 검증용 지표는 한 번에 하나만 활성화하고 교체한다.
기존 지표를 잠시 숨겨야 한다면 표시 상태를 먼저 기록하고 복구한다. 검증이 끝난 임시 지표는 제거한 뒤
다음 지표를 추가한다. 새 레이아웃은 만들지 않는다. 알림·주문은 수집에 필요하지 않다.

Basic의 일반 차트 이력과 내보내기 제한 때문에 최근 1년 1h가 없을 수 있다. 이용 가능한
`request.security_lower_tf`와 Pine Logs로 수집한 값은 **별도 probe 증거**다. 원본의 native 실행과
겹치는 구간에서 동등성을 입증하기 전에는 원본 검증 성공으로 취급하지 않는다. v4는 `log.info`를 지원하지
않으므로 v5/v6 포팅도 원본 변경 내역과 검토 근거를 따로 남긴다. 한도·오류·누락을 숨기거나 우회하지 않는다.

`scripts/pine_validation/tv_logs.py`는 UI에서 읽은 `QB1|epoch_ms,open,high,low,close,volume,buy,sell,stop,atr;`
로그를 CSV와 사건 JSON으로 변환한다. 바깥 로그의 차트 시간대 대신 payload의 UTC epoch를 사용한다.
중복·충돌·시간 격자 누락·잘린 로그를 거부한다. 초기 warmup의 진단값 NA와 OHLCV 결측은 구분한다.
원본 native 검증을 완료하지 않은 probe는 `native_original_verified=false`로 보존한다.

`scripts/pine_validation/tv_native.py`는 UI가 요청한 원본 study의 응답을 파싱한다. 원본/실제 컴파일 소스의
바이트 hash와 줄바꿈만 정규화한 동일성, 입력값, 심볼, 타임프레임, plot/alert 일치, 확정 봉 격자를 확인한다.
OHLCV가 없는 응답은 데이터까지 검증한 것으로 표시하지 않는다. 원본의 초기 계산 이력과 probe의 warmup이
다르면 같은 평가 기간에도 경계 신호가 달라질 수 있다. 동일 이력으로 재계산한 실험은 별도 결과로 보존하고,
원래 비교의 불일치를 지우지 않는다.

`scripts/pine_validation/native_capture.py`는 여러 공개 원본을 위한 별도 파서다. 원본 파일 SHA-256,
실제 editor·compile request 소스의 LF 정규화 동일성, 기본 입력과 override(`inputs`) 및 실제 전개값
(`resolved_inputs`), 성공 컴파일 `metaInfo`, `create_study` 입력·IL·study cohort를 교차 확인한다.
원문의 최상위 정적 `plot`·`plotshape`·`plotchar`·`alertcondition` 호출의 AST 줄·0-based 열·순서·
제목·문구를 metadata `plots`/`styles`의 plot id·유형과 연결한다. 로컬/동적 호출, 모호한 기본값·
표시 타입, 누락/변조된 metadata는 거부한다. 검토하지 않은 표시를 임의 매수·매도로 바꾸지 않는다.
현재 명시적으로 확인한 정적 입력은 scalar와 일곱 OHLCV source 이름이며, 동적 색상 기본값 등은
별도 원문·컴파일 대조 없이 자동 지원하지 않는다.

UI wire의 `du` study 열과 같은 차트 cohort의 `du`/`timescale_update` OHLCV를 UTC 봉 시각으로
맞춘다. 같은 차트의 `timescale_update`가 빈 `s=[]`로 이력을 명시적으로 초기화하면 그 이전 가격행만
이전 차트 구간으로 제외한다. 초기화 뒤에는 확정봉의 중복 충돌·격자 누락·비유한 값·가격 범위 오류를
거부하며 진행 중 봉은 사건에서 제외한다. alertcondition 1만 발화하고 0은 불발이다. plotshape/plotchar는 숫자 0, NA 및
TradingView의 큰 NA sentinel을 불발로 취급한다. `window_events(start,end)`는 [시작, 종료)의
study와 OHLCV 완결 격자가 모두 있어야 반환한다. 공통 관측구간 결과의
`reference_kind=native_original_partial_window`는 **그 구간의 원본 사건 추출**이지 최근 calendar
1년 또는 150셀 strict 통과가 아니다. runner의 `tv_events[timeframe]`가 이 raw 캡처 파일을 가리키면
원본·입력·컴파일 metadata·study cohort를 재검증하고 `window_events`의 비교창 완결성과 manifest
OHLCV의 전 봉 동일성을 확인한 뒤에만 `tv_verification=raw_capture_checked`로 사건을 사용한다.
raw 검증 실패 시 같은 파일의 `events`·`provenance`로 돌아가지 않는다. 독립 Python/Pine·앱 원장
대조는 별도 판정으로 유지한다.

모든 수집물·원본·실행 결과는 gitignore된 `runs/<회차>/` 아래에 둔다. manifest의 경로는 manifest
기준 상대 경로다. CSV 열은 `time,open,high,low,close,volume`, time은 시간대가 명시된 ISO 문자열이다.

```json
{
  "version": 1,
  "symbol": "BYBIT:BTCUSDT.P",
  "window": {"start": "2025-10-20T00:00:00Z", "end": "2026-10-20T00:00:00Z"},
  "ohlcv": {"1h": "data/1h.csv", "4h": "data/4h.csv", "1d": "data/1d.csv"},
  "indicators": [{
    "id": "n8ss8BID", "title": "UT Bot Alerts",
    "url": "https://www.tradingview.com/script/n8ss8BID-UT-Bot-Alerts/", "author": "QuantNomad",
    "boosts": 60605, "observed_at": "2026-10-20T13:59:00Z",
    "source_file": "sources/ut-bot-alerts.pine",
    "source_sha256": "d17fdc1d34a20107dbb853316886ac8c27803b159f379e66c685810d7e10410c",
    "signal_bindings": [
      {"function": "alertcondition", "line": 41, "direction": "long"},
      {"function": "alertcondition", "line": 42, "direction": "short"}
    ],
    "oracle": "utbot", "params": {"key_value": 1, "atr_period": 10},
    "inputs": {"a": 1, "c": 10, "h": false},
    "tv_events": {"1h": "tv/1h.json", "4h": "tv/4h.json", "1d": "tv/1d.json"}
  }]
}
```

기존 TV 사건 JSON은 `events` 배열과 `provenance` 객체를 갖는다. provenance에는 원본 `source_sha256`,
`symbol`, `timeframe`, `inputs`, `window`를 manifest와 동일하게 명시한다. `kind=native_original` 또는
원본 대조를 마친 `kind=reviewed_port, native_original_verified=true`만 최종 판정에 사용한다.
`native_original`에도 `native_original_verified=false`를 명시했다면 미검증으로 남긴다.
이 형식의 검증 강도는 `tv_verification=operator_provenance_attestation`이다. 과거 strict 일치도
원본 wire의 compile·study·OHLCV를 직접 검사했다는 뜻은 아니다.
출처 없는 배열이나 미검증 probe는 차이를 계산해 보여주더라도 통과시키지 않는다. 동일 원본 hash는 중복 사례로
표시하고 최소 10개의 독립 표본 수에 보태지 않는다. 게시물 URL의 query·slug 차이도 별도 지표로 세지 않는다.

줄은 1-based, 선택적인 `column`은 0-based다. 같은 줄의 여러 호출은 column으로 구분한다.
`when`은 `truthy`(기본), `positive`, `negative`를 지원한다. 부호가 없는 cross를 임의로 롱/숏에 연결하지 않는다.
시각의 `source_line`은 출처 메타데이터이므로 사건·체결 동일성에 포함하지 않는다.

```bash
cd apps/api
uv run python scripts/validate_pine_signals.py \
  --manifest ../../runs/pine-validation/manifest.json \
  --output ../../runs/pine-validation/result --limit 100
```

`report.json`은 원본·CSV·TV 자료 hash, 원시 사건, 세 쌍의 신호 차이, 선물 원장을 보존한다.
변환 전략을 `run_backtest_v2`로 실행한 앱 거래도 전체 warmup 이력의 독립 Python 원장과 대조한다.
종료·열린 거래의 방향·진입/청산 시각·가격·수량·Decimal 손익을 비교한다. 마지막 봉의 미체결 신호는 별도로
보존하지만 앱 내부 대기 큐의 동일성은 비교하지 않으며 `pending_queue_compared=false`로 명시한다.
`summary.md`는 Pine↔Python·선물 원장·앱 백테스트·전체 판정을 나눠 보여준다. 앱 변환 실패나 체결 불일치도
전체 통과를 막는다. 종료 코드는 0=전체 통과, 1=미완료/불일치, 2=manifest 오류다.
워크트리에서는 Celery 대신 이 직접 실행 도구를 사용한다. DB·서버 등록·배포는 이 명령의 범위가 아니다.
50개 평가를 재현할 때는 manifest에 `minimum_indicators: 50`을 넣고 `--limit 50`을 지정한다.
예: `uv run python scripts/validate_pine_signals.py --manifest ../../runs/corpus50/manifest.json --output ../../runs/corpus50/result --limit 50`.
`report.json`의 `expected_pairs`·`evaluated_pairs`·`exact_pairs`, 지표별 실패 이유, 원본·OHLCV·
TV 참조 hash를 함께 보존한다. Python/oracle 선행 점검과 앱 엔진 실행 사실, 엄격 일치 및 별도 비용
성과를 서로 다른 열로 읽는다. 현 수집물이 부분 native 구간뿐이면 연간 판정은 incomplete로 남긴다.

## LLM 차단

`LLM_PROVIDER_ORDER` 기본값은 빈 문자열이다. 키가 남아 있어도 provider 목록이 비어 있으면
해설·생성·변환·모델 카탈로그·명시 override에서 외부 SDK를 생성하지 않는다. 필요한 경우에만 사용자가
provider 목록을 명시적으로 설정한다. 이 검증 도구는 LLM 기능을 호출하지 않는다.
