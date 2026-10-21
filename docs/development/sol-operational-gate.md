# 선택 원문의 제품 cold replay 운영 gate

`tools/research/sol_operational_gate.py`는 완료된 full 품질 선정의 첫 semantic pass 원문을
기존 `replay_code_intents`로 재생한다. 현재 UI·활성화·주문 경로를 변경하지 않는다.
모델 생성·DB·Celery·거래소 호출은 없고, `--execute`를 명시할 때만 native transport를 실행한다.
기본 실행은 입력과 선정 증거를 검증하고 NOT_RUN 계획을 저장한다. 산출물은 현재 checkout의
`runs/`에만 둔다. 품질·경제 점수를 생성하거나 더 높은 수익의 원문을 다시 고르지 않는다.

필수 CLI 인자는 `--artifacts`, `--selection`, `--case-id`, `--code-snapshot`,
`--execution-hash`, `--environment`, `--snapshot`, `--symbol`, `--start`, `--output`이다.
`--environment`는 선정 보고서와 SHA가 같은 full manifest다. `--code-snapshot`은
`CodeSnapshot` JSON 전체이며 language/source/params/warmup/provenance 및 execution hash를
동결한다. 현재 full 평가와 동일한 `params={}`, `warmup_bars=200`만 허용하며 다른 입력은
원문 SHA가 같아도 실행 전에 거부한다. 기존 경제 runner의 30개 분모·첫 pass·source SHA 선정 검증을 재사용한다.

프로필은 다음 두 가지이며 새 컨테이너에서 직렬 실행한다.

- `first_activation_flat`: 동결 시세의 `--start` 1h 완료 봉 하나와 원문의 warmup 개수만큼
  과거 봉을 읽는다. 최초 warmup+1 전체 position은 flat이며, 아직 관찰하지 않은 intent를
  hold로 인증하지 않는다. 데이터 snapshot SHA·ID와 실제 입력 record digest를 기록한다.
- `observed_checkpoint`: `--checkpoint`와 `--checkpoint-sha256`이 있는 경우만 실제 보존 입력을
  재생한다. 없으면 UNKNOWN이며 신규 활성화 통과로 복구를 인증하지 않는다. 관찰한 봉별
  position·intent·input hash를 유지하며 현재 position을 과거에 넣지 않는다.

checkpoint export의 정확한 상위 필드는 `schema_version=1`,
`origin=persisted_live_code_bars`, `source_hash`, `execution_hash`, `snapshot_id`, `records`다.
각 record의 필드는 `sequence`, `execution_hash`, `input_hash`, `bar`, `position`,
`is_warmup`, `delivery_args`, `intent`, `status`다. 계정·사용자·세션 ID는 넣지 않는다.
bar에는 index/timestamp/open/high/low/close/volume, position에는 direction/size/average_price만
넣는다. 시간은 UTC 1h 연속이며 최초 warmup만 flat이다. 원문·버전·시세·파일 SHA와 모든
입력 hash를 대조한다. 이 검사는 operator가 제공한 영속 export의 byte binding이며 실제
거래소 관찰을 독립 인증하지 않는다. export 근거는 별도로 검토해야 한다.

제품 replay의 transport timeout은 30초이며 연구 실행의 900초로 늘리지 않는다. 타이머는
제품 replay 호출 직전부터 시작해 입력 hash 검증, factory/컨테이너 생성, init, 모든 봉,
close 및 자체 컨테이너 제거 확인까지 포함한다. 시세 로드·선정 증거 검증은 입력 준비이며
별도다. construct에는 Pine의 load 전달도 포함된다. init에는 parser·TS 컴파일·사용자 init이
함께 들어갈 수 있으며 내부 단계를 분리 계측했다고 주장하지 않는다. 완료한 봉 수와
bar 누적/max/p95, 단계 시간, 전체 시간, 이미지 ID와 컨테이너 이름을 기록한다.
`last_observed_phase`는 cleanup을 시도했으면 close다. `failure_phase`는 별도로 init/bar
응답 검증 등 실패 문맥을 보존하며, cleanup 실패는 close, 전체 시간 초과 판정은 total_gate다.

전체 30초 이하·모든 봉 응답·저장 intent 정합·동결 이미지 일치·cleanup 확인이 모두 있어야
PASS다. transport가 성공해도 총 시간이 넘으면 FAIL이다. 중단은 INTERRUPTED로 보존한다.
생성 중 실패해 이미지·이름을 관측하지 못하면 추측하지 않는다. cleanup probe 비용도 전체
시간에 포함하는 보수적 gate이며 이를 제품 함수 전체의 강제 취소 deadline 구현이라고
주장하지 않는다. 실제 관찰 checkpoint가 없으면 전체 준비 판정은 UNKNOWN으로 남는다.

cold는 호스트 경로를 mount하지 않은 새 컨테이너·새 프로세스다. 로컬에 보존한 이미지와
호스트 OS page cache까지 차갑다는 뜻은 아니다. 단일 실행의 통과는 선언한 원문과 N봉에만
해당하며, 최대 50000봉 또는 무제한 세션 기간의 성능으로 일반화하지 않는다. 회귀 테스트는
fake clock/transport만 쓰며 native 성능 증거가 아니다. 실제 gate는 full 선정 후 별도 수행한다.
