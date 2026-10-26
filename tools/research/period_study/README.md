# 고정 코호트·5기간 A/B 연구

`catalogue.json`의 publication ID를 먼저 동결한다. 원문 확보·방향 매핑 검토·Sol 생성·금융 실행·
TradingView native 대조·운영 등록은 서로 다른 분모다. 1,400원본은 84,000 금융 셀이며 실패와
미실행도 계획에서 제거하지 않는다. DB·Celery·주문·유료 API·모델 대체를 사용하지 않는다.

## 입력과 실행

1. `plan`: `--catalogue`의 선정 목록·SHA와 Pine/Python × A/B × 1h/4h/1d × P1~P5를 고정한다.
2. `freeze-data --seed-dir <이전 data>`: 기존 파일 SHA 검증 후 실제 Bybit 누락 구간만 보충한다.
   각 기간의 부모봉 준비 이력·정확한 1분봉·관측 펀딩을 25개 파일로 나눠 보존한다. 페이지별 캐시로 재개한다.
3. `generate --id <publication ID>`: 검토 원문을 Codex 구독 `gpt-6.1-sol/high`로 생성한다.
   최대 두 번·호출당180초·대체 모델 없음. 기본3 worker이며 동일 인증·쿼터 원인의 연속 실패는 배치 뒤 멈춘다.
4. `execute --id <publication ID>`: 고정 gVisor Pine/Python 이미지에서만 실행한다. 기본 순차,
   `--shard N --shards M`은 서로 다른 원본을 분배한다. 같은 입력의 성공은 파일 SHA 검증 후 재사용하며
   같은 입력의 금융 실행은 최대 두 번이다. `--limit`은 원본×코드×주기×기간 그룹 수다(A/B 두 셀).
5. `status`와 `export`: 예정·성공·실패·미실행·대기를 구분한다. JSON/CSV 단위를 보존하고
   null을0으로 채우지 않는다. 금융 성공은 native 통과·수익성·운영 등록을 뜻하지 않는다.

루트의 Python 실행기에 `apps/api/.env.local`을 통째 소싱한다. Docker endpoint는 연구 프로세스에만
지정하며 전역 Docker context와 앱 환경 파일은 바꾸지 않는다. `--run-dir`은 새 연구 namespace다.

```sh
set -a
. apps/api/.env.local
set +a
DOCKER_HOST="unix://$HOME/.lima/qb-python-research/sock/docker.sock" \
  apps/api/.venv/bin/python -m tools.research.period_study \
  --run-dir runs/indicator-strategy-period-study-20261026 execute --id PUBLICATION --limit 1
```

## 원문·리뷰 계약

목록 항목의 `source_sha256` 또는 별도 `source_receipts/<id>.json`의 SHA로 원문을 검증한다.
`reviews/<id>.json`은 `source_sha256`, `reviewer`, `basis`, `inputs`, `signal_bindings`,
`signal_mode`(`shared_events`/`position_feedback`), `warmup_bars`를 갖는다. Pine 실행은 검토한
`adapted_file`/`adapted_sha256`이 추가로 필요하다. 원본 indicator를 실행 가능한 strategy로 가장하지 않는다.
Sol 생성물은 원문·입력·매핑 해시가 모두 일치해야 하며 실제 응답 모델이 미보고되면 UNKNOWN이다.
생성 완료는 코드 검토 통과가 아니다. Python 금융 실행 전에는 해당 생성 시도의 `code-review.json`에
`status=reviewed_for_isolated_execution`, `reviewer`, `original_source_sha256`, `generated_sha256`가
정확히 결박돼 있어야 한다. 미검토·거절·해시 불일치는 실제 코드를 실행하지 않고 별도로 남긴다.
검토 파일이 외부 `market_context_file`·SHA를 선언하면 실제 파일도 검증하고 확인한 SHA를 실행
요청에 결박한다. 기존 결과의 사후 증거 재검증은 별도 영수증이며 새 게이트로 과거 계산을
실행했다거나 당시 모든 시각의 파일 불변성이 확인됐다고 주장하지 않는다.
원문에 없는 동봉 신호 우선순위나 추정한 시장 메타데이터를 정상 원본 재현으로 승인하지 않는다.
Pine 실행기는 심볼 메타데이터를 주입하지 않으므로 원문의 `syminfo.mintick`·ticker 계열 사용은
시장 문맥 미지원으로 보류한다. 원문 매핑 검토와 Python의 독립 실행 가능성은 별개로 보존한다.

A는 신호만, B는 고정2봉 swing SL·1.5R 절반·2R 본절/추적 정책이다. 양쪽 모두 같은 방향 신규
이벤트에서도 잔량 청산 후 신규 episode를 만든다. `shared_events`는 A에서 실제 실행한 신호열을
B가 해시 검증 후 재생한다. `position_feedback`은 각 정책의 실제 포지션으로 독립 실행한다.
실행 코드·정책·비용·원문·입력·데이터·이미지 SHA가 달라지면 새 namespace로 분리한다.

실패 시도는 `cells/<원본>/<경로>/<주기>/<기간>/<정책>/attempt-*.json`에 남기며 성공 결과의
압축 JSON은 신호·fill·episode·정책·비용 근거를 갖는다. 신규 `event_ledger_recipe_v1`은 원시
분봉 곡선을 반복 저장하지 않는다. 고정 시세 SHA·사건 처리 순서·Decimal 문맥·계산 구현과 환경·
원 곡선 canonical SHA를 저장하고, 저장 전에 equity·drawdown·buy-and-hold 전량을 exact 복원해
검증한다. `restore-result --input <결과> --output <새 파일>`로 원시 곡선을 다시 만들 수 있다.
기존 full-curve pilot·attempt는 보존하며 최신 상태에는 대형 곡선을 중복 저장하지 않는다.
여유 공간이12GiB 미만이면 신규 금융 실행만 `storage_paused`로 멈추며 남은 셀은 대기로 유지한다.
소스·검토·보고는 계속할 수 있다. P5는 2026-04-24부터
2026-10-24까지 고정이며 기간 말 가상 청산을 만들지 않는다. 현재 인기 기준의 회고 코호트이며
과거 선택 가능성이나 독립 holdout을 주장하지 않는다.
