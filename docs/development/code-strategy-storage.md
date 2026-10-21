# code_v1 저장·백테스트 계약

제품 결정은 [ADR-046](../adr/046-generated-strategy-language-evaluation.md)을 따른다. 승자 언어·생성 방법은 평가 후 별도로 정한다. 이 API는 수익성이나 지원 가능성을 저장만으로 보증하지 않는다.

`POST /strategies/code`, `PUT /strategies/code/{id}`는 `name`, 선택적 `description/symbol/timeframe/settings`, 필수 `code`를 받는다. `settings`는 기존 `StrategySettings` 검증을 공유하며 응답에도 포함한다. 갱신에서 생략하면 유지하고 명시적 NULL이면 해제한다. 기존 Pine settings 경로는 code 행을 저장 전에 422로 거부한다. `code`는 `schema_version:1`, **명시적** `execution_policy:"code_v1"`, `language:"pine"|"python"|"typescript"`, `source_code`, `warmup_bars`(1~10000), JSON `params`, JSON `provenance`다. `GET /strategies/code`와 `GET /strategies/code/{id}`는 소유자의 현재 불변 `version`을 반환한다. 다른 사용자와 없는 ID는 같은 404다.

기존 `StrategyVersion`에 코드를 저장하고 변경마다 새 행을 만든다. `source_hash`는 원문 SHA-256, `execution_hash`는 schema/policy/language/source/warmup/params/provenance의 canonical JSON SHA-256이다. 실행 시 둘을 다시 검증한다. `Strategy`의 현재 버전 포인터 변경은 이미 제출한 백테스트의 버전을 바꾸지 않는다. 코드 전략은 Pine 필드를 NULL로 두고, 기존 Pine 목록에서는 제외한다. 기존 get/brief/update/narrative 및 Pine 전용 실행은 코드 행에 422를 반환한다. 읽기 전용 Python View는 기존 Pine 경로에 유지한다. 기존 settings·삭제의 소유권 규칙은 동일하다.

`POST /backtests`는 기존 202 비동기 dispatch를 유지하며 코드 전략에 `execution_policy:"code_v1"`가 필수다. 현재 신호 주기는 **1h/4h/1d**만 지원하며 1m/5m/15m은 dispatch 전에 422다. 평가 입력 버전·해시를 고정하고 완료 봉→다음 봉 시가, 레버리지 1, 공통 `swing_two_bar_v1` 정책을 사용한다. Pine 자체 수량·가격 청산은 허용하지 않으며 무효화 `strategy.close` 의도는 허용한다. 워밍업 포함 부모 봉이 정확히 연속되어야 하고 평가 구간의 1분 실행 봉을 별도로 읽는다. 거래 시각은 1분 실행 인덱스로 저장한다. 분봉 내부 경로는 OHLC 근사이며 실제 틱 체결 보장이 아니다. 실제 펀딩·수수료·슬리피지를 공통 원장에 반영한다.

전략은 격리 실행기로만 전달한다. 이미지·gVisor·프로토콜·해시·데이터 오류는 FAILED이며 호스트 실행이나 Pine fallback이 없다. 스트레스·최적화는 코드 백테스트를 아직 지원하지 않아 422로 거부한다. 실행 확장은 기존 Pine 인터프리터·연구 compiler를 변경하지 않는 제품 helper에 둔다.

마이그레이션 `20261022_0003`은 컬럼을 추가하고 Pine 컬럼을 nullable로 바꾼다. 기존 행은 그대로 Pine이다. 코드 행이 존재하면 손실 없는 downgrade가 불가능하므로 이를 거부한다. 이 작업에서는 DB DDL이나 거래소 주문을 실행하지 않는다.

라이브 코드는 `tasks/code_live_signal.py`에서 핀 버전·소유자·Bybit demo·동결 설정을 확인하고 전용 `CodeEvaluationService`로 보낸다. 기존 Pine replay·주문 이벤트 큐를 통과하지 않는다. 현재 제품 경계는 **1h·1X·next_bar_open**이며 실제 demo 시장가의 지연·슬리피지가 역사적 다음 시가와 같다고 보증하지 않는다. 수량 추정 가격과 손절 기준 2봉은 같은 완료 봉 집합을 사용한다. 실제 시장가 VWAP은 그 완료 종가 추정값과 다를 수 있다. 수량은 세션 등록 당시 고정 `equity_baseline_usdt` × 동결 `position_size_pct` / 가격을 Decimal로 계산해 `2×qty_step`에 내린다. 두 절반이 각각 최소 수량 이상이어야 하며 50% 익절을 생략하지 않는다. 백테스트의 current cash 복리 사이징과 다른 정책이므로 두 자본 경로가 동일하다는 주장을 하지 않는다.

`trading.live_code_bars`(migration `20261022_0004`)는 세션+봉 시각 및 세션+순번이 유일하다. 실행 해시, OHLCV, 평가 때 관찰한 실제 포지션, 워밍업 여부, 수량 등 전달 인자, 입력 해시, intent, 상태를 저장한다. 최초 워밍업은 명시적으로 flat이다. 새 진입 전에 거래소 포지션과 확정 체결 원장이 정확히 맞아야 한다. 첫 관찰을 놓쳤거나 봉 공백이 있으면 현재 포지션으로 과거를 추측하지 않는다. 재시작은 저장된 입력 전체를 같은 격리 실행기에 재생한다. 임의 Python 객체 상태를 JSON으로 추측·복원하지 않는다. 저장된 intent와 달라지면 차단한다. 전체 재생 상한은 50000봉이며 이를 넘으면 새 진입을 거부한다.

입력·의도는 외부 주문 전달 전에 `prepared`로 커밋한다. coordinator에는 checkpoint UUID를 `intent_key`로 전달하고 전달 완료 후 `delivered` 및 세션 워터마크를 커밋한다. ACK 유실 시 현재 수량·현재 포지션을 과거 입력에 덮어쓰지 않고 같은 키·저장된 전달 인자로 재시도한다. 다음 봉까지 이미 종료된 오래된 진입 의도는 새 주문으로 재시도하지 않는다. 라이브 봉 재생의 격리 wall time은 30초이며 초과하면 실패한다. 실제 주문·부분 체결·보호 SL 확인·반전의 권위는 기존 영속 리스크 원장과 실행기다. 소스 오류·이미지 불가를 검사하기 전에도 열린 포지션의 보호·취소 복구를 먼저 시도한다.
