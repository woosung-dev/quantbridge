# code_v1 저장·백테스트 계약

제품 결정은 [ADR-046](../adr/046-generated-strategy-language-evaluation.md)을 따른다. 승자 언어·생성 방법은 평가 후 별도로 정한다. 이 API는 수익성이나 지원 가능성을 저장만으로 보증하지 않는다.

`POST /strategies/code`, `PUT /strategies/code/{id}`는 `name`, 선택적 `description/symbol/timeframe/settings`, 필수 `code`를 받는다. `settings`는 기존 `StrategySettings` 검증을 공유하며 응답에도 포함한다. 갱신에서 생략하면 유지하고 명시적 NULL이면 해제한다. 기존 Pine settings 경로는 code 행을 저장 전에 422로 거부한다. `code`는 `schema_version:1`, **명시적** `execution_policy:"code_v1"`, `language:"pine"|"python"|"typescript"`, `source_code`, `warmup_bars`(1~10000), JSON `params`, JSON `provenance`다. `GET /strategies/code`와 `GET /strategies/code/{id}`는 소유자의 현재 불변 `version`을 반환한다. 다른 사용자와 없는 ID는 같은 404다.

기존 `StrategyVersion`에 코드를 저장하고 변경마다 새 행을 만든다. `source_hash`는 원문 SHA-256, `execution_hash`는 schema/policy/language/source/warmup/params/provenance의 canonical JSON SHA-256이다. 실행 시 둘을 다시 검증한다. `Strategy`의 현재 버전 포인터 변경은 이미 제출한 백테스트의 버전을 바꾸지 않는다. 코드 전략은 Pine 필드를 NULL로 두고, 기존 Pine 목록에서는 제외한다. 기존 get/brief/update/narrative 및 Pine 전용 실행은 코드 행에 422를 반환한다. 읽기 전용 Python View는 기존 Pine 경로에 유지한다. 기존 settings·삭제의 소유권 규칙은 동일하다.

`POST /backtests`는 기존 202 비동기 dispatch를 유지하며 코드 전략에 `execution_policy:"code_v1"`가 필수다. 평가 입력 버전·해시를 고정하고 완료 봉→다음 봉 시가, 레버리지 1, 공통 `swing_two_bar_v1` 정책을 사용한다. Pine 자체 수량·가격 청산은 허용하지 않으며 무효화 `strategy.close` 의도는 허용한다. 워밍업 포함 부모 봉이 정확히 연속되어야 하고 평가 구간의 1분 실행 봉을 별도로 읽는다. 거래 시각은 1분 실행 인덱스로 저장한다. 분봉 내부 경로는 OHLC 근사이며 실제 틱 체결 보장이 아니다. 실제 펀딩·수수료·슬리피지를 공통 원장에 반영한다.

전략은 격리 실행기로만 전달한다. 이미지·gVisor·프로토콜·해시·데이터 오류는 FAILED이며 호스트 실행이나 Pine fallback이 없다. 스트레스·최적화는 코드 백테스트를 아직 지원하지 않아 422로 거부한다. 실행 확장은 기존 Pine 인터프리터·연구 compiler를 변경하지 않는 제품 helper에 둔다.

마이그레이션 `20261022_0003`은 컬럼을 추가하고 Pine 컬럼을 nullable로 바꾼다. 기존 행은 그대로 Pine이다. 코드 행이 존재하면 손실 없는 downgrade가 불가능하므로 이를 거부한다. 이 작업에서는 DB DDL이나 거래소 주문을 실행하지 않는다.
