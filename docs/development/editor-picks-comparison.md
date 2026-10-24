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
3. 검토 원문 6개로 `seal --pilot` 후 `generate --pilot`을 실행한다. 같은 원문의 동일 경로는 한 번만 호출하며 독립 원문은 제한된 동시성으로 처리한다. Gemini JSON Schema CLI 옵션은 사용하지 않고 stream-json의 단일 SUCCESS turn과
   JSON payload를 함께 확인한다. 도구 사용·다중 turn·비정상 종료·부분 출력은 실패다.
4. `freeze --end YYYY-MM-DD`로 24개월 부모봉과 1분봉을 수집하고 `validate-data`로 확인한다.
   API 페이지를 재사용하되 원문·시세 명세가 달라지면 새 실험으로 분리한다.
   `plan --pilot` → Linux gVisor의 `execute --plan <pilot-plan.json>` → `report --plan ...` 순서다.
5. 정적 검토 200개를 확보한 뒤 `seal`·`generate`·`plan`으로 전체 계획을 만든다.
   대상 인디케이터 목록을 전부 수집·판정해도 200개 미달이면 scope 감사 근거를 남긴 후
   `seal --allow-partial`로 실확보 수와 목표 200개를 함께 동결한다. 미확보 슬롯도 전체 분모에 남긴다.
   Pine 실제 실행에서 탈락하면 cohort와 결과를 보존한 새 epoch에서 후속 원문을 추가한다.
   `execute --shard N --shards M`은 고정 셀을 분배하며 실제 runner 동시성을 보장하지 않는다.

사용자가 승인한 Gemini 장기 재시도도 실패하면 이후 생성은 Terra만 진행한다. Gemini 실패와
원래 3경로 계획의 분모는 유지하며 모델을 임의 대체하지 않는다.

생성 최초 시도와 공개 구문/프로토콜 오류에 대한 최대 2회 수정은 별도 디렉터리다. 중단된 생성은
자동 재호출하지 않는다. 완료 캐시의 요청·파일 해시를 확인하며 실패 결과도 보존한다.
생성 시간과 원문·데이터·이미지·실행기 해시를 결박한다. gVisor가 없으면 blocked이며 호스트의
`exec/eval`이나 공유 Celery로 우회하지 않는다. 원시 곡선·신호는 lossless gzip으로 보존한다.

## 판정과 저장

`verify --id ID --plan <full-plan.json>`은 원본 UI compile/study/OHLCV 캡처를 기존
`native_capture` 파서로 확인한다. 검토 바인딩의 함수·줄·방향·조건 의미를 변환 근거와 대조하고
고유하게 확인한 원문 열 좌표만 파서 입력에 보강한다. 모호하거나 기존 좌표와 다르면 거부한다.
파서 구현 SHA도 계획에 동결한다. 확보한 세 주기 native 구간에서 같은 준비봉(현재 1,000봉)을 먼저 계산하고 이후 모든
봉의 양방향 사건을 대조한다. 준비봉 이후 검증·prefix 구간이 없으면 거부한다. 동일 재실행과
미래 봉을 제거한 prefix는 준비봉을 포함한 전체 행동 이력에서 실제 격리 세션으로 대조한다. 이 구간 밖의 TV 일치를 주장하지 않는다.
전체 36개 경제 셀의 Pine↔Python 신호·곡선·거래 원장 일치도 별도 요구한다. Python은 독립 정답
오라클이 아니다. 기존 연간 strict 검증기의 최대 100개·독립 oracle 계약은 바꾸지 않는다.

실제 compile metadata로 확인한 generic `input(close)`·`type=input.source`는 고정 OHLC source
이름만 검증한다. 빈 `study(resolution="")`의 compiler 자동 주기 slot은 정확한 metadata와 빈
wire 값을 함께 요구하며 추가 입력·주기 override는 거부한다. 색상 열은 바로 앞 line/shapes만
가리킬 수 있고 제목 없는 plot은 관측한 기본 제목 `Plot`만 허용한다.

`export --plan ...`는 통과한 경로만 기존 `SaveCodeStrategyRequest`로 내보낸다. 각 원문에 Pine·
Terra Python·Gemini Python 최대 3개를 저장하며 기본 화면은 BTC·1h다. 적자 전략도 기술 검증을
통과하면 연구로 저장한다. 출처·원문/변환 SHA·모델·검증 범위는 기존 provenance에 담는다.
저장 설정은 1배·자본 100%·다음 봉 시가를 명시한다. [가정] 계정 활성화가 없는 연구 저장의
margin_mode는 isolated다. 공통 R 정책·비용·펀딩 한계·요청 모델과 실제 모델 미보고도 provenance에
보존한다. 실제 앱 저장은 인증된 소유자 API로 요청 후 버전 해시를 다시 읽어 확인한다. 자동 주문은 없다.
운영 API/DDL 차이·인증이 막히면 저장 요청 묶음까지 완성하고 해당 단계의 blocked 근거를 남긴다.

보고서는 검색 가능한 HTML과 전체 CSV/JSON이다. 신호 일치와 승률, 비용 포함 수익과 열린 손익을
구분한다. 부분 익절은 같은 episode로 센다. 평균 R은 비용 후 완료 episode 손익을 최초 R×최초 수량으로
나눈 값이며, 완료 episode 승률은 미종료 포지션을 제외한다. 분봉 노출은 부분 청산 분봉을
포함하고 시가 전량 청산 분봉은 제외한 보유 구간의 합집합이다. 저장 직전 native 세 주기 캡처 SHA와
동일 실행 이미지의 경제 36셀을 다시 검사한다. PF/Sharpe 등의 정의상 NULL을 0으로 보정하지 않는다.
중첩 과거 구간·에디터 선정 편향·유사 계열을 독립 표본이나 미사용 holdout으로 부르지 않는다.
관측 펀딩 grid는 과거 일정의 독립 완전성 증거가 아니며 `funding_data_incomplete=None`을 통과로
바꾸지 않는다. 기존 경제 기준 통과 0을 모든 전략의 적자로 해석하지 않는다.

## 일회용 ARM 실행과 암호문 수거

`.github/workflows/editor-picks-research.yml`은 소유자 PR의 **정확한 head SHA**와 입력 암호문
URL/SHA 변수가 일치할 때만 8개 ARM shard를 실행한다. `EDITOR_PICKS_PLAN_FILE`은
`pilot-plan.json`(기본) 또는 `full-plan.json`만 허용해 단계별 실행을 구분한다. 로컬·운영 Docker daemon은 수정하지 않는다.
일회용 GitHub Linux ARM의 `/home/runner/work/`에서만 고정 runsc 보조 파일·이미지 archive의 SHA를
먼저 확인해 설치하고 이미지 ID·아키텍처를 다시 검사한다. 런타임 증거에 계산 코드 대조 증거도 보존한다.

입력과 결과는 별도 키 파일 또는 `EDITOR_PICKS_RESEARCH_KEY`로 AES-GCM 청크 인증한다. 이 키는
연구 입력 디렉터리 밖에 두며 실제 셀 worker에는 전달하지 않는다. 공개 release에는 `.enc`만 올린다.
실제 subprocess 종료 코드, shard별 셀 소비 요약, runtime 증거, 원시 결과를 함께 암호화한다.
full worker는 경제 셀 실행 후 코호트 순서의 `index % shards`로 배정된 원문을 같은 무자격
환경에서 native 검증 CLI로 실행한다. 전략 실행은 기존 gVisor를 사용한다. 경제·native의 실제
종료 코드를 terminal에 따로 남기고 하나라도 실패 종료하면 worker도 실패한다.
worker의 `verification/<ID>.json`은 수거할 때 불변 `native-checks/<ID>.json`으로 매핑하며
봉투 파일 해시와 plan SHA를 함께 검사한다. 파생 `verification/` 결과는 원시 봉투에 넣지 않는다.
`finish`·`collect`는 head/run ID/attempt/입력 암호문 SHA/plan SHA/shard를 암호 인증에 결합하므로
이전 실행 결과를 다른 실행의 결과로 수거할 수 없다.

수거 시 원래 입력을 보존한 run-dir을 사용한다. 아래 `HEAD`, `RUN_ID`, `ATTEMPT`, `INPUT_SHA`는
실제 실행값으로 정하고 `SHARD`는 0..7을 각각 실행한다. 키 파일은 32바이트 원시 키다.

```bash
apps/api/.venv/bin/python -m tools.research.editor_picks.remote collect \
  --run-dir runs/editor-picks-20261024 --plan pilot-plan.json \
  --cipher "$RESULT_CIPHER" --archive "$UNIQUE_RESULT_ARCHIVE" --key-file "$KEY_FILE" \
  --head "$HEAD" --run-id "$RUN_ID" --attempt "$ATTEMPT" --input-sha "$INPUT_SHA" \
  --shard "$SHARD" --shards 8
apps/api/.venv/bin/python -m tools.research.editor_picks.remote finalize \
  --run-dir runs/editor-picks-20261024 --plan pilot-plan.json \
  --head "$HEAD" --run-id "$RUN_ID" --attempt "$ATTEMPT" --input-sha "$INPUT_SHA" --shards 8
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
