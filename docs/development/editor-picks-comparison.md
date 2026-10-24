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
3. 검토 원문 6개로 `seal --pilot` 후 `generate --pilot`을 실행한다. 각 구독 CLI는 동시에 1건만
   호출한다. Gemini JSON Schema CLI 옵션은 사용하지 않고 stream-json의 단일 SUCCESS turn과
   JSON payload를 함께 확인한다. 도구 사용·다중 turn·비정상 종료·부분 출력은 실패다.
4. `freeze --end YYYY-MM-DD`로 24개월 부모봉과 1분봉을 수집하고 `validate-data`로 확인한다.
   API 페이지를 재사용하되 원문·시세 명세가 달라지면 새 실험으로 분리한다.
   `plan --pilot` → Linux gVisor의 `execute --plan <pilot-plan.json>` → `report --plan ...` 순서다.
5. 정적 검토 200개를 확보한 뒤 `seal`·`generate`·`plan`으로 전체 계획을 만든다.
   Pine 실제 실행에서 탈락하면 cohort와 결과를 보존한 새 epoch에서 후속 원문을 추가한다.
   `execute --shard N --shards M`은 고정 셀을 분배하며 실제 runner 동시성을 보장하지 않는다.

생성 최초 시도와 공개 구문/프로토콜 오류에 대한 최대 2회 수정은 별도 디렉터리다. 중단된 생성은
자동 재호출하지 않는다. 완료 캐시의 요청·파일 해시를 확인하며 실패 결과도 보존한다.
생성 시간과 원문·데이터·이미지·실행기 해시를 결박한다. gVisor가 없으면 blocked이며 호스트의
`exec/eval`이나 공유 Celery로 우회하지 않는다. 원시 곡선·신호는 lossless gzip으로 보존한다.

## 판정과 저장

`verify --id ID --plan <full-plan.json>`은 원본 UI compile/study/OHLCV 캡처를 기존
`native_capture` 파서로 확인한다. 확보한 세 주기 native 구간의 양방향 사건, 동일 재실행,
미래 봉을 제거한 prefix를 실제 격리 세션으로 대조한다. 이 구간 밖의 TV 일치를 주장하지 않는다.
전체 36개 경제 셀의 Pine↔Python 신호·곡선·거래 원장 일치도 별도 요구한다. Python은 독립 정답
오라클이 아니다. 기존 연간 strict 검증기의 최대 100개·독립 oracle 계약은 바꾸지 않는다.

`export --plan ...`는 통과한 경로만 기존 `SaveCodeStrategyRequest`로 내보낸다. 각 원문에 Pine·
Terra Python·Gemini Python 최대 3개를 저장하며 기본 화면은 BTC·1h다. 적자 전략도 기술 검증을
통과하면 연구로 저장한다. 출처·원문/변환 SHA·모델·검증 범위는 기존 provenance에 담는다.
실제 앱 저장은 인증된 소유자 API로 요청 후 버전 해시를 다시 읽어 확인한다. 자동 주문은 없다.
운영 API/DDL 차이·인증이 막히면 저장 요청 묶음까지 완성하고 해당 단계의 blocked 근거를 남긴다.

보고서는 검색 가능한 HTML과 전체 CSV/JSON이다. 신호 일치와 승률, 비용 포함 수익과 열린 손익을
구분한다. 부분 익절은 같은 episode로 센다. PF/Sharpe 등의 정의상 NULL을 0으로 보정하지 않는다.
중첩 과거 구간·에디터 선정 편향·유사 계열을 독립 표본이나 미사용 holdout으로 부르지 않는다.
관측 펀딩 grid는 과거 일정의 독립 완전성 증거가 아니며 `funding_data_incomplete=None`을 통과로
바꾸지 않는다. 기존 경제 기준 통과 0을 모든 전략의 적자로 해석하지 않는다.
