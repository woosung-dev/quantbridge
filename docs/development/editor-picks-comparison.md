# 에디터 픽 Pine·Terra·Gemini 재현 비교

PRD §5와 ADR-046의 결과·가정 공개 및 격리 실행 계약을 따른다. 진입점은
`docs/status.md` 하나다. 실행 코드 = `tools/research/editor_picks/`.

## 대상과 고정 조건

- TradingView 에디터 픽의 실행 가능한 고유 원문 200개를 목표로 한다. 공개 원문·URL·작성자·
  UI 목록 관측·버전·라이선스·SHA를 보존한다. 같은 원문 SHA는 별도 지표로 세지 않는다.
- Pine 원문을 보존한 결정론 전략, `gpt-5.6-terra/high` 구독 Codex CLI,
  Antigravity `gemini-3.8-flash-high/high` 구독 CLI의 Python 재현을 비교한다.
  API 키·모델 fallback은 사용하지 않는다. CLI 요청 모델과 실제 응답 모델의 미보고를 구분한다.
- BTCUSDT 무기한·1h/4h/1d·동일 UTC 종료일의 최근 6/12/24개월·실제 1분 청산 시계다.
  원문 기본 입력을 보존한다. 초기 이력은 같은 봉으로 맞추며 준비봉보다 짧은 시세는 거부한다.
- 초기 10,000 USDT·1배·자본 100%·단일 포지션·다음 봉 시가다. 기존 연구의 taker 0.055%,
  maker 0.02%, slippage 0.014%와 관측 펀딩을 사용한다. 현재 거래소 공시 수수료 주장이 아니다.
- 완료 2봉 극값까지 실제 진입가 거리×1.1을 최초 R로 고정하고 1R SL·1.5R 50% TP·2R부터
  본절/2R trailing을 공통 실행기가 소유한다. 원 지표의 자체 청산을 재현한 성과와 구분한다.

연구의 `raw_signal_v1`은 기존 Pine 어댑터가 생성한 진입문의 포지션 guard만 제거한다. 같은 방향
원문 신호도 Pine·Python 모두 제출하고 공통 원장이 중복 진입을 처리한다. 원문과 원래 포지션
조건은 보존하며 변환 코드·metadata SHA를 함께 갱신한다. 동봉 양방향 신호는 Pine 실행 실패로
분모에 남기며 방향 우선순위를 임의로 만들지 않는다. 해당 셀은 비교·등록 검증을 통과할 수 없다.

원문에 연결할 신호 호출이 없으면 검토한 전역 조건식을 `reviewed_expression_v1`로 연결한다.
원문 body는 바꾸지 않고 끝에 고유한 진단 `alertcondition` 두 개만 추가한다. 원본과 추가본 SHA를
따로 보존하고, TradingView에서도 같은 추가본을 실제 컴파일·관측한다. native 검증은 원문과
조건식에서 추가본·위치·메타데이터를 다시 생성해 대조한 뒤 기존 원시 증거 파서를 사용한다.
이 결과는 원저자의 매매 신호 검증과 구분한 연구 진입 규칙 검증이다. 모델에는 원본과 명시 조건식을
함께 제공하며 실제 성과를 보고 조건·입력을 고르지 않는다.
v4 이하의 추가 진단에서만 검토식의 `ta.*`·`math.*` 이름을 해당 버전의 전역 builtin으로
연결한다. 원문 body·모델 요청의 검토식은 보존하고 실제 컴파일한 조건식을 별도 기록한다.
같은 전역 함수 이름의 사용자 함수가 있으면 자동 연결하지 않는다.

정적 coverage는 이미 실행기에 연결된 v4 전역 삼각함수 별칭 `sin`·`cos`·`tan`·`asin`·`acos`·
`atan`을 namespaced 함수와 동일하게 판정한다. 버전 지시문은 주석과 문자열을 구분해 읽으며,
일반 주석의 apostrophe 때문에 실제 `//@version`이 사라지거나 문자열 안의 예제가 버전으로
승격되지 않아야 한다. v4 미만의 캐스트 제한과 다른 미지원 의존성의 전체 실행 차단은 유지한다.

어댑터는 [TradingView v4 study 선언](https://www.tradingview.com/pine-script-docs/v4/annotations/study-annotation/)의
`study(title, shorttitle, overlay, format, precision)` 중 표시용 위치 인자만 같은 이름의 전략
인자로 연결한다. `overlay`는 bool 상수, `format`은 원래 `inherit`·`price`·`volume` 상수,
`precision`은 0~16 정수 상수만 허용한다. 중복·동적 인자·이름 인자 뒤의 위치 인자·추가 옵션은
거절한다. v4 밖의 `study` 위치 규칙을 추측하지 않으며 원문 계산·신호·기본 입력은 바꾸지 않는다.

원저자가 방향을 정하지 않은 MA 리본의 연구 규칙은 `research_prespecified_ribbon_order_v1`이다.
원문 기본 길이의 모든 표시 MA를 빠름→느림으로 정렬하고, 모든 인접 쌍이 상승 정렬인 상태의 첫
진입은 long, 전부 하락 정렬인 상태의 첫 진입은 short다. 동률·준비 이력 부재는 진입하지 않는다.
첫 plot만 대표로 고르거나 일부 선을 제외하지 않는다. 원저자 신호라는 표현을 사용하지 않으며
원문 지표 계산과 연구 진입 규칙의 출처를 따로 기록한다. 방향을 설명하지 않는 stress 색상은 제외한다.

기본·수수료2배·슬리피지2배·펀딩2배의 전체 분모는 **21,600셀**이다. 펀딩 부호는 유지한다.
6개 파일럿은 3경로×3주기×최근6개월×기본비용 = **54셀**이며 전체 평가가 아니다.
미지원·미확보·생성 실패·timeout·불일치를 성공 수에서만 빼고 계획 분모에는 남긴다.

## 실행 순서

명령은 루트에서 실행한다. 기존 `.env.local`은 통째 소싱하며 DB·Celery·주문은 사용하지 않는다.

```bash
set -a
. apps/api/.env.local
set +a
apps/api/.venv/bin/python -m tools.research.editor_picks --run-dir runs/editor-picks-20261024 ingest
apps/api/.venv/bin/python -m tools.research.editor_picks --run-dir runs/editor-picks-20261024 screen
```

1. Playwright MCP의 `browser_run_code_unsafe`로 `capture.js`의 UI 수집 함수를 실행한다.
   반환한 listings/captures를 runs 안에 JSON으로 보존한다. Source code 클릭이 발생시킨 응답만
   사용한다. 기존 사용자 차트·지표는 삭제하지 않는다. 보호 소스·로그인/한도 오류는 기록한다.
2. `ingest`는 관측된 에디터 픽 목록과 원문 응답을 확인한다. `screen`은 별도 프로세스 제한 시간으로
   정적 coverage와 방향 검토를 검사한다. 실행 검증과 다르다. `reviews/<id>.json`에는 원문 SHA,
   `reviewed_by`, `basis`, `family`, `warmup_bars`, `inputs`, 줄·열·방향 `signal_bindings`를 명시한다.
3. 검토 원문 6개로 `seal --pilot` 후 아래 원문별 병렬 생성 CLI를 사용한다. 기존 `generate`는
   모델별 worker 안에서 원문을 순차 처리한다. 병렬 CLI는 완료 생성물을 먼저 재사용하고,
   독립 원문을 최대 6개씩 같은 배치에서 처리한다(기본 3개). 순서대로 집계한 timeout·중단·차단이
   두 번 연속이면 진행 중 배치를 마친 후 다음 배치를 시작하지 않는다. Gemini JSON Schema CLI 옵션은 사용하지 않고 stream-json의 단일 SUCCESS turn과
   JSON payload를 함께 확인한다. 도구 사용·다중 turn·비정상 종료·부분 출력은 실패다.
4. `freeze --end YYYY-MM-DD`로 24개월 부모봉과 1분봉을 수집하고 `validate-data`로 확인한다.
   API 페이지를 재사용하되 원문·시세 명세가 달라지면 새 실험으로 분리한다.
   `plan --pilot` → Linux gVisor의 `execute --plan <pilot-plan.json>` → `report --plan ...` 순서다.
5. 정적 검토 200개를 확보한 뒤 `seal`·`generate`·`plan`으로 전체 계획을 만든다.
   대상 인디케이터 목록을 전부 수집·판정해도 200개 미달이면 scope 감사 근거를 남긴 후
   `seal --allow-partial`로 실확보 수와 목표 200개를 함께 중간 동결할 수 있다. 미확보 슬롯도 전체 분모에 남긴다.
   Pine 실제 실행에서 탈락하면 cohort와 결과를 보존한 새 epoch에서 후속 원문을 추가한다.
   부분 회차의 종결은 세션 목표 200개의 완료가 아니다. 지원 확장·소싱·원본 대조를 계속하며
   200개 고유 원본의 실제 기술 검증을 별도 집계한다.
   `execute --shard N --shards M`은 고정 셀을 분배하며 실제 runner 동시성을 보장하지 않는다.

사용자가 승인한 Gemini 장기 재시도도 실패하면 이후 생성은 Terra만 진행한다. Gemini 실패와
원래 3경로 계획의 분모는 유지하며 모델을 임의 대체하지 않는다.

```bash
apps/api/.venv/bin/python tools/scripts/editor-picks-generate-parallel.py \
  --run-dir runs/editor-picks-20261024 --arm terra --pilot --workers 3 --limit 6 --timeout 900
```

전체 코호트는 `--pilot`을 빼고 실제 확보 수에 맞는 `--limit`을 지정한다. 실행 설정·코호트와
원문 SHA·dispatcher SHA·순서별 재사용/실패는 `generation-dispatch/<요청 identity>/`에 남긴다.

생성 최초 시도와 공개 구문/프로토콜 오류에 대한 최대 2회 수정은 별도 디렉터리다. 중단된 생성은
자동 재호출하지 않는다. 완료 캐시의 요청·파일 해시를 확인하며 실패 결과도 보존한다.
생성 시간과 원문·데이터·이미지·실행기 해시를 결박한다. gVisor가 없으면 blocked이며 호스트의
`exec/eval`이나 공유 Celery로 우회하지 않는다. 원시 곡선·신호는 lossless gzip으로 보존한다.

대규모 회차는 일회용 ARM에서 전체 결과 archive의 모든 파일을 스트림으로 읽어 원래
envelope의 SHA·크기·경로를 검증한다. 전체 원시는 인증 암호화한 뒤 1GiB 이하 release
asset으로 분할 보존한다. 각 asset의 공식 ID·크기·digest·소유 URL이 일치해야 작은 인증
번들을 마지막에 공개한다. 기존 asset은 덮어쓰지 않는다.
로컬에는 요청·신호·영수증·native proof·실제 종료 증거와 인증 번들을 보존하고,
정확한 `results/<작업 SHA>/result.json.gz`만 원격 원시로 참조할 수 있다. 검증 때마다
번들을 AES로 재인증하고 원래 SHA·분할 asset 근거·보존 파일을 다시 확인한 문맥에서만
그 누락을 허용한다. 다른 필수 파일은 누락을 허용하지 않으며 가짜 파일 경로도 만들지
않는다. 보고서의 `raw_result_storage`는 로컬 전체 원시와 인증된 원격 원시를 구분한다.
이 방식은 전체 곡선을 로컬에서 재계산했다는 의미가 아니다. 새 계획에 보관·수거 구현도
동결하며 이전 회차의 원시 파일·실행 provenance는 바꾸지 않는다.
입력 archive에는 원문 소싱 범위 감사와 모델 생성 정책도 보존한다. 이전 Gemini 실패를
후속 회차의 시도로 세지 않으며, 해당 이전 epoch의 실제 파일·SHA를 출처로 구분한다.
수집 감사의 정적 판정 수는 관측 당시 전체 목록의 값이며 현재 코호트·실제 실행 수와
구분한다. 현재 선택된 스크립트를 과거 시세에 적용한 회고 비교이므로 당시 공개·선택
가능했음을 증명한 성과나 독립 holdout 성과로 표시하지 않는다.
새 전체 회차의 실행 step은 270분, job 전체는 330분으로 제한해 뒤의 인증 보관에 시간을
남긴다. 초기 설정·압축·전송 시간 때문에 보관 완료를 보장하는 수치는 아니다. 제한에 닿으면
실제 완료한 receipt와 로그를 보존하고, 미소비 셀·종료 근거 누락을 미완으로 남긴다.

## 판정과 저장

`verify --id ID --plan <full-plan.json>`은 원본 UI compile/study/OHLCV 캡처를 기존
`native_capture` 파서로 확인한다. 검토 바인딩의 함수·줄·방향·조건 의미를 변환 근거와 대조하고
고유하게 확인한 원문 열 좌표만 파서 입력에 보강한다. 모호하거나 기존 좌표와 다르면 거부한다.
파서 구현 SHA도 계획에 동결한다. 확보한 세 주기 native 구간에서 같은 준비봉(현재 1,000봉)을 먼저 계산하고 이후 모든
봉의 양방향 사건을 대조한다. 준비봉 이후 검증·prefix 구간이 없으면 거부한다. 동일 재실행과
미래 봉을 제거한 prefix는 준비봉을 포함한 전체 행동 이력에서 실제 격리 세션으로 대조한다. 이 구간 밖의 TV 일치를 주장하지 않는다.
TradingView Basic 원본 대조는 워밍업과 미확정 봉을 포함해 수신한 고유 시각의 합집합이
5,000봉 이내여야 한다. 정상 UI에서 필요한 범위만 단계적으로 확인하고, 한도 팝업을 만나면
추가 요청을 멈춘다. 캡처의 `collection_policy`와 `quota_popup_observed=false`를 확인하며
동시 지표 한도는 계정 UI에서 실측한 Basic **2개**를 적용한다. 기존 사용자 지표는 ID·활성
상태를 보존하고 검증 중에만 숨겼다가 복구한다. 한도 안내가 `dialog` role 없이 표시되는
경우도 있으므로 실제 보이는 한도 문구를 함께 검사한다. 세 번째 추가가 차단된 시험은
한도 발생 원시로 남기며 관측 성공으로 합산하지 않는다.
진단 출력을 덧붙인 버전이 서비스의 스크립트 출력 한도를 넘으면 원문·출력을 삭제해 맞추지
않는다. 원문 자체와 진단 버전의 제한을 구분하고 실제 오류·소스 SHA를 검증 불가 근거로 남긴다.
계획에도 같은 한도를 동결한다. 기존 확대·드래그 반복으로 얻은 초과 기록은 보존하되 새
계약의 통과 근거로 재사용하거나 후미만 잘라 사용하지 않는다. 로컬 실행은 TV 계산의 첫
봉부터 같은 OHLCV로 시작하며, 준비봉이나 양방향 사건이 부족하면 검증 불가로 남긴다.
UI의 사용자 지정 기간으로 추가 이력을 받으면 기존 행과 합집합을 이루며, 모든 추가 완료를
직전 완료 이후의 같은 차트·주기 범위 요청과 `study_loading`/`study_completed` token 쌍에
결박한다. 완료되지 않은 추가 계산이나 확정 봉의 값 충돌은 거부한다. 지표의 초기 가격이
공통 구간 밖에서 누락되면 워밍업으로 대신하지 않는다. 원시는 보존하고 평가 종료 뒤의
봉만 동결 데이터의 종료 시각에서 제외한다.
초기 plot이 NA라 지표 출력이 뒤에서 시작해도 실제 가격이 앞에 있으면 그 가격부터 계산한다.
가격 입력의 첫 봉을 공통 plot 구간으로 잘라 초기 상태를 바꾸지 않는다. native 사건 대조는
동일한 1,000봉 준비 이후의 완전한 관측 구간에서 수행한다. 이전 고정 코어의 common-only
입력이 앞 가격을 제외하는 경우에는 후속 통과로 승격하지 않고 수정한 새 회차로 넘긴다.
계정이 제공하는 기간 시작점 추가 봉도 이번 연구에서는 5,000봉 한도 안에서만 수용한다
([TradingView 공식 한도](https://www.tradingview.com/support/solutions/43000480679-historical-intraday-data-bars-and-limits-explained/)).
독립 Bybit 시세의 6·12·24개월 경제 측정은 유지하고, TV 원본 대조 구간 밖의 일치를 주장하지 않는다.
차트 주기는 실제 UTC 봉 격자를 검증한 JSONL 문맥으로 전달하고 worker의 일치 ACK를 요구한다.
v4의 `stoch/cum/linreg/vwma/roc/cci/hma` 별칭은 기존 `ta.*` 계산으로 연결하며 공식 인자명을
검사한다. `cum(x)`와 v5 `source`의 이름 차이를 보존하고 중복·미등재 인자는 거부한다
([공식 마이그레이션](https://www.tradingview.com/pine-script-docs/migration-guides/to-pine-version-5/)).
`input.string` 타입 상수와 선언의 `format.volume` 표시 상수도 구분한다. 아직 구현하지 않은
`tostring(..., format.volume)`은 형식을 무시해 시장 판단을 바꾸지 않도록 실행 오류로 남긴다.
시간·달력과 v5/v6 색상 연산은 보존한 통제 관측으로 회귀 확인하되, 각 원본의 신호 일치 판정은
별도다. native의 candle OHLC·색상 7열도 실제 metadata 순서·대상·제목과 함께 결박한다.
v4에서 wick·border 색을 생략한 경우는 실측 5열과 compiler의 기본 스타일이 모두 맞아야 한다.
정적 `color.new(hex6, transp)` fill은 색상 열이 없을 수 있다. 원문 plot 변수의 위치와 compiler의
끝점·제목·색·투명도까지 맞는 경우만 수용하며 동적·gradient 열 요구는 유지한다. `bgcolor`의
별도 `bg_colorer`도 비신호 열로 고정한다. 신규 형식은 실제 원시로 대조하며 기존 epoch는 갱신하지 않는다.
정적 색은 전체 AST의 중첩 쓰기까지 단일 쓰기가 확인된 전역 hex·named·정수 RGB 생성으로
제한한다. 이 색의 fill과 legacy 투명도는 실제 compiler 스타일·끝점에 결박한다. hline fill은
독립 band ordinal·제목·가격·스타일을 확인하며 plot ordinal과 섞지 않는다. `plotarrow`는 비신호
arrows/up/down 3열·target·제목·높이 스타일을 확인한다. 일반 plot과 같이 showLast/display 표시식은
평가하지 않으며, 실제 행·열·시간격자와 선택한 신호 열은 계속 검증한다.
정적 fill의 투명도는 전역 단일 쓰기의 0~100 숫자 리터럴 별칭도 허용하지만 입력·식·재대입·
이름 충돌은 거부한다. 관측한 v6 gradient의 두 series 값과 조건부 topColor는 세 비신호 열로
대조한다. 6개 위치 인자·Name 조건·`color.new(Name, 숫자 리터럴)`·na 가지에 한정하고,
끝점·기본 제목·gradient 스타일·palette 부재를 실제 compiler와 맞춘다. 조건·값을 호스트에서
계산하지 않으며 기존 두 열 형식과 진입 바인딩은 유지한다([공식 gradient 형식](https://www.tradingview.com/blog/en/pine-script-vertical-gradients-33586/)).
v4/5의 바인딩된 alertcondition에서 실측한 정확한 양수 `1e100`은 초기 결측으로 기록한다.
원시 관측값과 시각·열·방향을 보존하고 이벤트를 만들지 않으며, 요청 비교창에 결측이 있으면
`window_events`가 거부한다. 따라서 준비봉 이후의 결측은 native 통과가 될 수 없다. `None`과
v6·다른 수치는 이 근거로 허용하지 않는다. bool `na`는 false와 같은 값이 아니고 조건이 true일
때만 alert가 발생한다([공식 bool 규칙](https://www.tradingview.com/pine-script-docs/migration-guides/to-pine-version-6/#boolean-values-cannot-be-na),
[v4 alerts](https://www.tradingview.com/pine-script-docs/v4/essential/alerts/)). wire의 `1e100` 표기는 공개 명세가 아닌 보존 원시의 실측 근거다.
전체 36개 경제 셀의 Pine↔Python 신호·곡선·거래 원장 일치도 별도 요구한다. Python은 독립 정답
오라클이 아니다. 기존 연간 strict 검증기의 최대 100개·독립 oracle 계약은 바꾸지 않는다.

늦게 도착한 관측은 `editor-picks-native-followup.py`가 원래 고정 코어·입력·계획·이미지로
별도 검증한다. 첫 수집 통과 3TF 묶음과 앞선 실패 참조를 gVisor 실행 전에 동결하며 결과로
구간을 다시 선택하지 않는다. worker에는 키·자격증명을 주지 않고 경제 셀을 재실행하지 않는다.
원래 20개 경제 봉투와 후속 봉투를 인증한 뒤 별도 파생 root에만 선택본을 배치하여 기존
`reconcile/export`의 36셀·이미지·원문·native 게이트를 재사용한다. 원본 영수증과 판정은
보존하고 후속 관측을 합친 결과임을 명시한다. 외부 실패 원시는 식별명·SHA 참조만 담으며
실행 입력에 본문을 추가하지 않는다. Mac 파생 복사는 APFS CoW로 압축 영수증의 재팽창을 막는다.

실제 compile metadata로 확인한 generic `input(close)`·`type=input.source`는 고정 OHLCV source
이름만 검증한다. 빈 `study(resolution="")`의 compiler 자동 주기 slot은 정확한 metadata와 빈
wire 값을 함께 요구하며 추가 입력·주기 override는 거부한다. 일반 colorer는 바로 앞
line/shapes를 가리키며 arrow 색상 열은 같은 arrow를 향한 연속 그룹으로 검사한다.
제목 없는 plot은 관측한 기본 제목 `Plot`만 허용한다.
v4의 제목 없는 `plotchar`는 실제 컴파일·wire로 관측한 `Chars`만 허용하며,
다른 제목이나 대소문자 표현으로 느슨하게 대조하지 않는다.
`indicator(timeframe="")`의 자동 Timeframe도 원문·compiler metadata·빈 wire가 함께 맞아야 한다.
숫자 input의 관측한 정수 10·100 나눗셈과 상수 뺄셈 wrapper는 바깥 계산 없이 raw slot을 보존한다.
알 수 없는 wrapper를 누락시키거나 bool·숫자 문자열을 숫자로 바꾸지 않는다. source `volume`·
부호 숫자·`size.*` 기본값과 버전별 named/new 색은 원문·compiler·typed wire를 함께 대조한다.
generic input의 readonly hex 색 상수는 source 입력과 구분한다. 검증된 color 타입의 literal
hex6만 RGB byte가 같은 대소문자 표현을 허용하고 원문·compiler·resolved·wire 문자열은 보존한다.
일반 text·source·enum·제목은 대소문자를 구분하며 다른 RGBA·hex8 동치는 추가하지 않는다.
generic `input`의 읽기 전용 전역 `color.*` 이름 상수 별칭은 기존 hex 별칭과 같은 단일쓰기·
쉐도잉 거절 검사를 거쳐 원문 버전의 rendering SSOT로 기본값을 읽는다. 실제 compiler의 color
슬롯과 wire를 함께 대조하며 재대입·동적 색·연쇄 별칭·`input.source` 또는 text 슬롯으로의 혼용은
거절한다. 원문 입력값을 바꾸거나 관측 없는 색 생성식으로 지원을 넓히지 않는다.
v4 `fill`의 직접 named color에서 `transp`가 생략된 관측 형식은 기본 90을 사용한다.
정적 fill은 색 열을 요구하지 않으며 원래 plot 끝점·filledAreas 순서·기본 색·display 15·
transparency 90·visible true를 대조한다. 뒤의 동적 fill 색 열은 기존 순서·대상 검사를 유지한다.

원문 `barcolor`·`bgcolor`는 실제 열·제목·순서를 결박한다. 명시 keyword 제목은 literal 문자열만
정확 일치시키고, 생략하면 각각의 기본 제목을 사용한다. 진입 binding 범위는 확장하지 않는다.

실제 TV 통제 반례가 Pine builtin 의미 오류를 드러내면 기존 Pine 출력을 정답으로 고정하지 않는다.
정적 원본 재검사는 비어 있는 전용 private 디렉터리에 현재 파서가 직접 생성한 AST 캐시만
재사용할 수 있다. source bytes·파서 버전·스키마 키와 디렉터리 권한을 보존하며 외부 캐시를
복사하지 않는다. 원격 격리 worker의 캐시 설정과 원본·시장·행동 결과는 바꾸지 않는다.
원래 결과·실패·모델 생성물을 보존한 새 epoch에서 계산 소스·이미지·계획 SHA를 다시 동결한다.
RSS_WMA의 전체 이력 재계산처럼 공개 실행 계약의 자원 오류를 수정할 때도 매매 조건·기본 입력은
바꾸지 않고 별도 생성 시도와 선택 근거를 남긴다. 완료 부모 시도는 새 epoch의 이력으로 옮겨
첫 완료 생성물 선택기가 수정 시도를 가리는 일을 막는다. 수익률·승률로 조건을 조정하지 않는다.

`export --plan ...`는 통과한 경로만 기존 `SaveCodeStrategyRequest`로 내보낸다. 각 원문에 Pine·
Terra Python·Gemini Python 최대 3개를 저장하며 기본 화면은 BTC·1h다. 적자 전략도 기술 검증을
통과하면 연구로 저장한다. 출처·원문/변환 SHA·모델·검증 범위는 기존 provenance에 담는다.
저장 설정은 1배·자본 100%·다음 봉 시가를 명시한다. [가정] 계정 활성화가 없는 연구 저장의
margin_mode는 isolated다. 공통 R 정책·비용·펀딩 한계·요청 모델과 실제 모델 미보고도 provenance에
보존한다. 실제 앱 저장은 인증된 소유자 API로 요청 후 버전 해시를 다시 읽어 확인한다. 자동 주문은 없다.
운영 API/DDL 차이·인증이 막히면 저장 요청 묶음까지 완성하고 해당 단계의 blocked 근거를 남긴다.

200개 생성 원문의 새 실험 코호트는 기존 `static_eligible` 전용 seal과 구별한다. 공개 원문·검토·
완료 생성 요청의 해시를 대조한 모델은 독립 실행할 수 있다. Pine 정적 거절은 원문과 정적 검사
파일의 SHA를 동결한 `preflight_failure` 선택으로 남기며, 각 셀은 `failed`·
`failure_stage=static_preflight`·`runtime_attempted=false`다. 이를 실제 Pine 실행 수로 세지 않는다.
후처리에서도 이 선택의 원문·정적 근거 SHA와 Pine 경로를 다시 확인한다. 원래 거절 이유를
보존하고 native 검증 실패·경제 일치 0으로 유지하며, 미확보 모델의 사유와 섞지 않는다.
시장 입력 준비 실패와 transport 생성 호출 이후의 실행 실패도 분리한다. `runtime_attempted`는
격리 transport를 요청했음을 뜻하며 성공 실행은 별도다. 보고서는 경로별 실제 요청 원문 수·완료
원문 수·정적 거절 셀 수를 제공한다. Pine 비교가 없는 모델 결과의 기술·native·앱 저장 게이트는 유지한다.
200원문 회차는 160개 고정 shard에 분배하고 금융 계산은 최대 19개 runner에서 실행한다.
공유 실행 예산 20개 중 1개를 이미지 빌드·CI·후속 검증에 남겨 계산 중에도 검증을 진행한다.
작업별 계산 수를 줄여 중간 보관을 앞당기고 release 메타데이터 조회의 API 예산도 고려한다.
원문·셀·데이터·모델·계산은 바꾸지 않는다. [GitHub matrix 한도](https://docs.github.com/en/actions/reference/limits)는 256개다. 이전 20개 shard
회차의 배정·영수증은 바꾸지 않는다. 파일럿의 셀별 소요시간을 자원 계획 근거로만 사용하며,
사전검사·실행 timeout을 성공으로 바꾸거나 수익에 따라 대상을 바꾸지 않는다.
각 셀은 요청 기간 이전의 실제 준비봉부터 종료까지 빠짐없는 가격 격자를 요구한다. 최대
24개월 시작점에 확보한 기본 준비봉 수보다 요구량이 크더라도, 6·12개월 셀의 실제 과거 이력이
충분하면 원래 요구량을 그대로 사용한다. 이력이 부족한 기간·주기는 입력 준비 실패로 남긴다.

보고서는 검색 가능한 HTML과 전체 CSV/JSON이다. 신호 일치와 승률, 비용 포함 수익과 열린 손익을
구분한다. 부분 익절은 같은 episode로 센다. 평균 R은 비용 후 완료 episode 손익을 최초 R×최초 수량으로
나눈 값이며, 완료 episode 승률은 미종료 포지션을 제외한다. 분봉 노출은 부분 청산 분봉을
포함하고 시가 전량 청산 분봉은 제외한 보유 구간의 합집합이다. 저장 직전 native 세 주기 캡처 SHA와
동일 실행 이미지의 경제 36셀을 다시 검사한다. PF/Sharpe 등의 정의상 NULL을 0으로 보정하지 않는다.
엔진의 `sharpe_convention=unavailable*`와 원시 Sharpe 0은 후처리 보고서에서 NULL과 기준 열로
표시하며, 실제 측정된 Sharpe 0은 유지한다. 원시 receipt의 값은 바꾸지 않는다.
중첩 과거 구간·에디터 선정 편향·유사 계열을 독립 표본이나 미사용 holdout으로 부르지 않는다.
관측 펀딩 grid는 과거 일정의 독립 완전성 증거가 아니며 `funding_data_incomplete=None`을 통과로
바꾸지 않는다. 기존 경제 기준 통과 0을 모든 전략의 적자로 해석하지 않는다.

## 일회용 ARM 실행과 암호문 수거

`.github/workflows/editor-picks-research.yml`은 소유자 PR의 **정확한 head SHA**와 입력 암호문
URL/SHA 변수가 일치할 때만 20개 ARM shard를 실행한다. `EDITOR_PICKS_PLAN_FILE`은
`pilot-plan.json`(기본) 또는 `full-plan.json`만 허용해 단계별 실행을 구분한다. 로컬·운영 Docker daemon은 수정하지 않는다.
일회용 GitHub Linux ARM의 `/home/runner/work/`에서만 고정 runsc 보조 파일·이미지 archive의 SHA를
먼저 확인해 설치하고 이미지 ID·아키텍처를 다시 검사한다. 런타임 증거에 계산 코드 대조 증거도 보존한다.

입력과 결과는 별도 키 파일 또는 `EDITOR_PICKS_RESEARCH_KEY`로 AES-GCM 청크 인증한다. 이 키는
연구 입력 디렉터리 밖에 두며 실제 셀 worker에는 전달하지 않는다. 공개 release에는 `.enc`만 올린다.
실제 subprocess 종료 코드, shard별 셀 소비 요약, runtime 증거, 원시 결과를 함께 암호화한다.
전체 실행은 기존 8개 shard의 고정 run/head/input SHA에 인증된 완료 셀을 20개 shard에 재배정한다.
입력 계획과 금융 계산 Python은 바꾸지 않는다. 이력 암호문은 한 번에 하나만 내려받아 검증하고
현재 shard의 완료 셀만 보존한 뒤 해당 임시 암호문을 삭제한다. 누락 asset·인증 오류는 실행 실패다.
이 재사용은 원래 v3 입력 암호문 SHA에만 적용하며 계산 소스·이미지가 바뀐 교정 epoch는 재사용하지 않는다.
재개 처리는 worker 이전의 별도 secret 환경에서 수행하며 전략 코드를 호스트에서 실행하지 않는다.

`execute --workers 1|2`의 기본값은 기존 직렬 실행 1이다. 선택형 2는
배정된 셀을 중복 없는 두 lane의 독립 spawn 프로세스에서 처리한다. 자식은 같은 이미지 ID를
확인하고 기존 셀 실행·request 잠금·실패 영수증을 그대로 사용한다. 부모는 모든 자식을 회수한
뒤 전체 소비 수를 한 번 기록하며 native 검증·terminal·인증 보관은 기존 단일 부모가 맡는다.
컨테이너별 1 CPU·1GiB·900초와 gVisor 정책은 유지한다. 호스트 시세 검증·분봉 배열·직렬화
메모리는 프로세스마다 복제되므로 ARM A/B의 VM 전체 메모리·OOM·시간·출력 동등성 확인 전에는 전체
배치에 채택하지 않는다. 실행 중인 동결 회차와 그 배정·계획·결과에는 소급하지 않는다.
전체 배치의 선택은 `plan --workers 2`로 `execution_workers=2`를 동결해야 원격 worker까지
전달된다. 기본 1은 기존 계획·terminal 형식을 유지한다. 계획이 2이면 최종 수거는 terminal의
선언과 allocation의 `workers=2`·`spawn`·배정 셀 수에 맞는 실제 프로세스 수(최대 2)를 요구한다.
같은 계획의 직렬·병렬 A/B는 직접 `execute --workers`로 비교할 수 있으나 전체 완료 판정과 구분한다.
별도 보조 회차는 같은 200원문의 정적 적격 70−52 차이인 사전 고정 18개만 직렬 1로 검증한다.
1,944 계획 셀을 32 shard·최대 3 runner로 나누며 기존 200원문 실행·입력 변수·동시성 19는 그대로 둔다.
보조 회차는 독립 변수와 입력을 쓰고 계정 공유 예산 안에서 대기하며, 전체 200원문의 완료를 뜻하지 않는다.

`editor-picks-process-ab.py`는 기존 코호트 순서의 첫 두 Pine·Terra 적격 원문의
1h·24개월·기본 비용 네 셀을 직렬 1회와 2프로세스 1회로 비교한다. 선택·순서·core SHA·
control HEAD는 실행 전에 결박한다. 준비를 포함한 계산 예산은 30분, job 전체는 35분이다.
여덟 실행 완료와 신호·원장·지표·원시 결과 해시 일치, 속도비 1.2 이상, VM 가용 메모리
2GiB 이상과 OOM 0을 모두 관측해야 후속 채택을 검토한다. 측정 누락·잔여 writer는 거절하며
단일 순서의 캐시 편향을 명시한다. 자동 채택하지 않고 원시 근거는 암호문으로만 보존한다.

full worker는 경제 셀 실행 후 코호트 순서의 `index % shards`로 배정된 원문을 같은 무자격
환경에서 native 검증 CLI로 실행한다. 전략 실행은 기존 gVisor를 사용한다. 경제·native의 실제
종료 코드를 terminal에 따로 남기고 하나라도 실패 종료하면 worker도 실패한다.
worker의 `verification/<ID>.json`은 수거할 때 불변 `native-checks/<ID>.json`으로 매핑하며
봉투 파일 해시와 plan SHA를 함께 검사한다. 파생 `verification/` 결과는 원시 봉투에 넣지 않는다.
`finish`·`collect`는 head/run ID/attempt/입력 암호문 SHA/plan SHA/shard를 암호 인증에 결합하므로
이전 실행 결과를 다른 실행의 결과로 수거할 수 없다.

수거 시 원래 입력을 보존한 run-dir을 사용한다. 아래 `HEAD`, `RUN_ID`, `ATTEMPT`, `INPUT_SHA`는
실제 실행값으로 정하고 `SHARD`는 0..19를 각각 실행한다. 키 파일은 32바이트 원시 키다.

```bash
apps/api/.venv/bin/python -m tools.research.editor_picks.remote collect \
  --run-dir runs/editor-picks-20261024 --plan pilot-plan.json \
  --cipher "$RESULT_CIPHER" --archive "$UNIQUE_RESULT_ARCHIVE" --key-file "$KEY_FILE" \
  --head "$HEAD" --run-id "$RUN_ID" --attempt "$ATTEMPT" --input-sha "$INPUT_SHA" \
  --shard "$SHARD" --shards 20
apps/api/.venv/bin/python tools/scripts/editor-picks-postprocess.py remote finalize \
  --run-dir runs/editor-picks-20261024 --plan pilot-plan.json \
  --head "$HEAD" --run-id "$RUN_ID" --attempt "$ATTEMPT" --input-sha "$INPUT_SHA" --shards 20
```

`collect`는 전체 인증·파일 목록·해시·기존 파일 충돌을 검사한 뒤 병합한다. 동일 파일 재수신은
허용하되 기존 결과를 덮지 않는다. `finalize`는 모든 shard의 실제 종료 코드 0·고정 plan·배정 셀
소비 수와 전체 receipt 분모를 함께 요구한다. 누락/실패 종료는 `remote/<실행 identity>/finalization.json`에 남기고
종료 코드 1을 반환한다. 원격 증거와 finalization은 plan SHA·head·run ID·attempt의 identity를
경로에 포함하므로 같은 연구 디렉터리의 파일럿·전체 실행을 덮지 않는다.
셀 자체의 미지원·전략 실패도 보고서의 실패 분모로 보존하므로 실행 완주와
성과 통과는 별개다. full finalization은 모든 shard 증거 확인 후 원시 native proof와 수거한 전체
경제 결과를 reconcile하고 보고서를 만든다. 파생 `verification/`은 불변 `native-checks/`와
분리한다. 등록 export는 별도 단계이며 파일럿 finalization으로 전체 검증을 대체하지 않는다.

교정 실행에서 첫 셀 이전 `docker info` 시간 초과로 실패한 shard는 같은 입력·head·plan의
해당 GitHub job만 재시도한다. 성공한 다른 shard를 재실행하거나 첫 실패 증거를 덮지 않는다.
성과 열람 전에 `retry-selection.json`에 shard별 실제 attempt와 실패 원인 파일 SHA를 고정한다.
별도 `tools/scripts/editor-picks-finalize-retry.py`가 각 attempt의 원래 namespace·인증 수거 근거·
envelope 파일 해시·실제 종료·정확한 셀 소유 집합·native 배정을 다시 검증한다. attempt를 바꿔
원본 봉투를 복사하지 않으며 선택 manifest identity의 `remote/mixed-<identity>/`에만 종결한다.
앱 저장 묶음도 같은 검증 함수를 재호출해 혼합 출처를 결박하며, 전체 검증 전에는 저장하지 않는다.

Pine 계산 지원 확장용 `.github/workflows/editor-picks-runtime-refresh.yml`은 소유자의 정확한 PR head와
GitHub 변수 `EDITOR_PICKS_RUNTIME_REFRESH_HEAD`가 일치할 때만 별도 ARM 준비 작업을 실행한다.
기존 `EDITOR_PICKS_INPUT_URL/SHA256`의 인증된 부모 이미지를 적재하고 바뀐 Pine 계산 파일만 COPY한 자식의
단일 layer·실행 설정·25개 Pine 파일·worker·계산 class·Python loader/SDK를 검증한다.
로컬 Docker·운영 배포·생성 전략 실행 없이 새 runtime 전용 `.enc`만 보존한다. 새 epoch 입력을
만들기 전 부모/자식 이미지 ID·소스 SHA를 확인하고 갱신 변수를 해제한다.

복합 대입·UDF 마지막 대입 반환·NA 종료 경계·배열 통계·삼각 함수·좌표/문자열 객체 상태와
여섯 TA 함수 지원은 원문 전체 실행 전에 독립 회귀와 실제 TradingView 통제 관측으로 확인한다.
지원 함수 수·정적 적격 수·생성 완료 수를 실제 원본 실행·native 기술 통과 수로 합산하지 않는다.
외부 라이브러리 import는 별칭 메서드처럼 보이더라도 의존성을 확보·검증하기 전 정적 미지원이다.

새 receipt는 분봉 drawdown·buy-and-hold 곡선을 지표 요약에 중복하지 않는다. 전체 곡선은
같은 원시 `result.json.gz`에 유지하고 나머지 지표·신호·거래 원장·경제 판정은 그대로 보존한다.
완료한 이전 회차의 로컬 결과 캐시는 동일 SHA의 원격 암호문과 복구 manifest를 검증한 뒤 비울 수
있으며 원본 소스·시세·native 관측·최종 보고서와 원격 원장은 지우지 않는다.

대용량 `finalize`·`report`·`export`는 `tools/scripts/editor-picks-postprocess.py`를 진입점으로
사용한다. 원시 receipt에는 분봉 drawdown·buy-and-hold 곡선이 있으므로 전체를 메모리에 누적하면
24개월 셀 수에 따라 로컬 RAM을 초과한다. 후처리 reader는 이 두 곡선만 반환 메모리에서 제외하고
원래 파일·파일 SHA 검사·경제 판정·신호·원장 비교를 유지한다. 수치 재계산과 전략 실행은 없다.
`sharpe_convention` 기준 열과 미측정 NULL 표시는 보고 단계의 표현 계약이다. 금융 계산 Python과
동결 계획을 보존하며, 별도 후처리 구현 SHA와 원시 근거를 실행 산출물에 기록한다.
같은 계획 SHA를 셀마다 다시 계산하는 비용은 `receipts` 한 호출 안에서만 재사용한다.
다른 객체의 해시·모든 원시 파일 검사는 유지하고, 종료 시 원래 함수를 복원한 뒤 계획을 다시
해시해 변경을 거부한다. 전역 함수의 임시 교체를 쓰므로 단일 스레드의 순차 후처리 전용이다.

```bash
apps/api/.venv/bin/python tools/scripts/editor-picks-postprocess.py \
  --run-dir runs/editor-picks-20261024 report --plan runs/editor-picks-20261024/full-plan.json
apps/api/.venv/bin/python tools/scripts/editor-picks-postprocess.py \
  --run-dir runs/editor-picks-20261024 export --plan runs/editor-picks-20261024/full-plan.json
```

`plan --months 6`은 기본 6·12·24개월 계획과 별개의 6개월 전용 계약이다. 새 full 계획에
`periods: [6]`을 동결하고, 모든 원본×3 arm×3 주기×1 기간×4 비용을 빠짐없이 배정한다.
200원본이면 7,200셀, 원본·arm별 경제 일치 요구는 12셀이다. 명시 기간의 전체 행렬·순서·코호트
원본 집합을 실행 전에 검사하며 사후 필터·누락·중복을 거부한다. native·준비봉·리스크·체결·이미지
게이트는 그대로다. `periods`가 없는 기존 계획의 36셀 요구와 기본 CLI 동작은 유지한다.
