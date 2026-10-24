# code_v1 저장·백테스트 계약

제품 결정은 [ADR-046](../adr/046-generated-strategy-language-evaluation.md)을 따른다. 승자 언어·생성 방법은 평가 후 별도로 정한다. 이 API는 수익성이나 지원 가능성을 저장만으로 보증하지 않는다.

`POST /strategies/code`, `PUT /strategies/code/{id}`는 `name`, 선택적 `description/symbol/timeframe/settings`, 필수 `code`를 받는다. `settings`는 기존 `StrategySettings` 검증을 공유하며 응답에도 포함한다. 갱신에서 생략하면 유지하고 명시적 NULL이면 해제한다. 기존 Pine settings 경로는 code 행을 저장 전에 422로 거부한다. `code`는 `schema_version:1`, **명시적** `execution_policy:"code_v1"`, `language:"pine"|"python"|"typescript"`, `source_code`, `warmup_bars`(1~10000), JSON `params`, JSON `provenance`다. `GET /strategies/code`와 `GET /strategies/code/{id}`는 소유자의 현재 불변 `version`을 반환한다. 다른 사용자와 없는 ID는 같은 404다.

기존 `StrategyVersion`에 코드를 저장하고 변경마다 새 행을 만든다. `source_hash`는 원문 SHA-256, `execution_hash`는 schema/policy/language/source/warmup/params/provenance의 canonical JSON SHA-256이다. 실행 시 둘을 다시 검증한다. `Strategy`의 현재 버전 포인터 변경은 이미 제출한 백테스트의 버전을 바꾸지 않는다. 코드 전략은 Pine 필드를 NULL로 두고, 기존 Pine 목록에서는 제외한다. 기존 get/brief/update/narrative 및 Pine 전용 실행은 코드 행에 422를 반환한다. 읽기 전용 Python View는 기존 Pine 경로에 유지한다. 기존 settings·삭제의 소유권 규칙은 동일하다.

수동 저장의 `provenance`는 사용자 제출 설명이다. 해시는 저장 이후 변경 여부를 검증하며,
모델이 실제로 생성했다는 증명이나 의미 검증 통과 인증을 제공하지 않는다.

`POST /backtests`는 기존 202 비동기 dispatch를 유지하며 코드 전략에 `execution_policy:"code_v1"`가 필수다. 현재 신호 주기는 **1h/4h/1d**만 지원하며 1m/5m/15m은 dispatch 전에 422다. 평가 입력 버전·해시를 고정하고 완료 봉→다음 봉 시가, 레버리지 1, 공통 `swing_two_bar_v1` 정책을 사용한다. Pine 자체 수량·가격 청산은 허용하지 않으며 무효화 `strategy.close` 의도는 허용한다. 워밍업 포함 부모 봉이 정확히 연속되어야 하고 평가 구간의 1분 실행 봉을 별도로 읽는다. 거래 시각은 1분 실행 인덱스로 저장한다. 분봉 내부 경로는 OHLC 근사이며 실제 틱 체결 보장이 아니다. 실제 펀딩·수수료·슬리피지를 공통 원장에 반영한다.

선택적 `strategy_version_id`는 해당 소유 전략에 속한 불변 버전을 지정한다. 생략 또는 NULL이면
접수 시점의 현재 버전을 사용한다. 없는 버전이나 다른 전략의 버전을 명시하면 422이며 현재
버전으로 대체하지 않는다. 전략 자체가 다른 소유자에게 속하면 기존과 같은 404다. 기존 Pine
경로에 NULL이 아닌 버전 ID를 보내면 422이며, 생략한 기존 요청의 동작은 유지한다.

코드 백테스트의 평가 구간은 `period_start` 포함·`period_end` 제외다. 결과의
`data_coverage`도 워밍업을 제외한 같은 구간의 부모 봉을 센다. 기존 Pine 경로의
양 끝 포함 커버리지 계산은 유지한다.

제품 실행 입력은 `CodeBacktestExecution`이 준비·실행 두 단계로 소유한다.
`prepare(backtest, version, provider=...)`는 QUEUED 단계에서 warmup을 포함한 부모 봉을
조회하고 정확한 연속 구간을 확인한 뒤 객체를 반환한다. `signal_ohlcv`는 이 부모 봉을
그대로 제공한다. caller가 RUNNING 전환·commit·취소 확인과 config·funding 준비를 마친 뒤
`run(config, funding_rates=...)`을 호출하면 버전·저장 execution hash를 다시 확인하고
평가 구간의 1분 봉을 조회해 격리 실행한다. 준비 시 검증한 snapshot을 캐시해 후기 검증을
생략하지 않는다. 객체는 기존 provider와 로드된 모델의 읽기 전용 참조를 사용하며 DB 조회·
상태 전이·commit·결과 저장은 caller가 소유한다. 입력·실행 오류는 기존 단계의 오류 처리로
전달하고, 격리 자원의 수명은 기존 `CodeExecutionSession`이 맡는다.

코드 백테스트는 row를 먼저 commit한 뒤 작업을 publish하고, task ID를 두 번째 commit으로 저장한다. 즉시 시작한 worker도 row를 읽을 수 있다. publish 실패는 이미 저장된 QUEUED row를 조건부 FAILED로 기록·commit하고 `TaskDispatchError`를 반환한다. 이미 RUNNING 등으로 전이한 row를 실패로 덮어쓰지 않는다. legacy Pine dispatch 순서는 이 변경 범위에 포함하지 않는다.

전략은 격리 실행기로만 전달한다. 이미지·gVisor·프로토콜·해시·데이터 오류는 FAILED이며 호스트 실행이나 Pine fallback이 없다. 스트레스·최적화는 코드 백테스트를 아직 지원하지 않아 422로 거부한다. 실행 확장은 기존 Pine 인터프리터·연구 compiler를 변경하지 않는 제품 helper에 둔다.

마이그레이션 `20261022_0003`은 컬럼을 추가하고 Pine 컬럼을 nullable로 바꾼다. 기존 행은 그대로 Pine이다. 코드 행이 존재하면 손실 없는 downgrade가 불가능하므로 이를 거부한다. 서버 DDL과 실제 거래소 주문은 별도 승인이 필요하며, 마이그레이션 검증은 폐기 가능한 슬롯 테스트 DB에서 한다.

`/strategies/code` 화면은 수동으로 검토한 원문·언어·파라미터·준비 봉·거래 설정을 저장한다.
자연어에서 실행 Python을 만드는 [Gemini preview](gemini-python-generation.md)는 명시적
적용 뒤 이 저장 경로를 사용하며, 생성만으로 저장·백테스트·Demo를 호출하지 않는다.
사용자가 바꾼 원문을 저장하기 전에는 백테스트를 실행하지 않는다. 언어 변경만으로 코드를
번역하지 않으며 기존 Pine의 읽기 전용 Python View와도 다른 흐름이다. 계정 identity가
바뀌면 편집·선택 상태를 초기화한다. 백테스트는 화면에서 선택·검토한 `version.id`를
`strategy_version_id`로 명시해 기존 202 경로로 제출한다. 그 사이 목록의 현재 버전이
갱신돼도 검토한 버전은 바뀌지 않는다. 결과 화면에서 진행 상태를 본다.
지원 신호 주기는 백테스트 1h/4h/1d, 데모 1h다.
코드 결과 응답은 `config.execution_policy=code_v1`과 저장된 수량 방식을 보존한다. 결과와
거래 내역의 전략 링크는 코드 조회 API를 쓰며 Pine 편집기 대신 코드 작업 공간을 연다.
재실행은 정책·수량·비용·다음 시가 설정을 전달하고, 수량 근거가 없는 코드 결과는 거부한다.
재실행이 선택하는 소스는 현재 저장 버전이다. 과거 실행 버전의 재현 버튼을 제공한다는
의미가 아니며, 이미 제출된 개별 백테스트의 버전 핀은 계속 불변이다.
`?strategy={id}` 링크는 해당 소유자의 저장 전략을 편집기에 선택한다. 수동으로 원문·언어·
파라미터·준비 봉을 바꾸면 생성 출처를 그대로 주장하지 않고 부모 버전 ID와 수동 편집 출처를
기록한다. 저장한 마진 모드는 유지한다.

화면의 데모 시작은 주문 권한이 확인된(`read_only=false`) Bybit Demo 계정과 저장한 1h 버전만
선택한다. dirty 상태에서는 시작할 수 없다. `source_policy=code_v1`과 불변 버전 ID를 보내며
클라이언트 실행 스냅샷은 보내지 않는다. 서버가 소유권·설정·계정 배타성·자본 기준선을 확인하고
스냅샷을 만든다. 버튼이 자동 주문 시작임을 표시하고 성공 시 트레이딩 화면으로 이동한다.

작업 공간 hook은 검토한 저장 버전에서 백테스트·Demo 가능 여부와 거부 이유를 함께 계산한다.
화면은 이 판정과 전송 중 상태만 사용하며 action도 같은 판정을 확인한 뒤 검토 버전의 ID로
요청한다. 기간 검증은 백테스트 제출 시 수행한다. 목록 캐시 갱신은 검토 대상을 교체하지 않는다.

같은 물리 계정·정규화 심볼에서는 한쪽이 `code_v1`이면 활성 세션을 공유하지 않는다.
등록의 양방향 검사와 코드 신규 진입 준비는 같은 PostgreSQL transaction advisory lock을
쓴다. 알려진 UID는 공백을 제거해 같은 거래소·모드의 형제 계정을 합치고, UID를 모르면
자기 계정 행만 확인한다. 기존 행의 심볼 비교는 `BTC/USDT`, `BTCUSDT`와 두 표기의
`:USDT` 접미형을 같은 축으로 본다. legacy 세션끼리의 기존 정책은 유지한다. 비활성 코드
세션도 잔여 포지션, 미종결 진입, 취소 미확정 또는 미귀속 청산 수량이 남으면 소유권을 보유한다.
같은 축의 미종결 non-reduce-only 주문도 새 코드 진입을 막는다. 이미 준비된 자기 세대의
진입 주문만 정확한 원장·귀속 대조로 최종 재검사에서 제외한다. 보호·축소·취소·기존
outbox 복구는 이 신규 진입 admission 검사로 차단하지 않는다.

등록은 검사부터 INSERT commit까지, 코드 준비는 KillSwitch 검사 뒤 재확인부터
`prepare_entry` commit까지 같은 트랜잭션이다. 최종 발주 검사 뒤 submitted commit으로
락이 풀려도 미종결 리스크·주문이 영속 소유권을 유지한다. 이 경계는 단일 DB 안의
세션·주문을 조정한다. 별도 호스트 DB, 외부 수동 주문의 거래소 경합이나 UID가 확인되지
않은 두 계정 행의 동일성까지 원자적으로 보장하지 않는다. Bybit의 one-way 모드는 한
심볼의 Buy/Sell 한쪽 포지션만 허용하므로 공유 세션의 수량을 독립 포지션처럼 해석하지
않는다([공식 position mode](https://bybit-exchange.github.io/docs/v5/position/position-mode)).

코드 세션의 손익은 알려진 주문 소계로 표시한다. 귀속 미확인 거래소 청산이나 정산 대기 주문이
있으면 전체 손익이 미정산임을 밝히며, 미귀속 청산 수량과 같은 계정의 새 진입 차단 상태를
보여준다. 주문 목록·상세·CSV는 서버가 실제 체결 증거를 확인한 코드 부분 체결 취소·거부의
손익도 표시한다. 기존 실패 주문에 남은 추정값은 계속 제외한다.
정산된 청산 주문 수는 손익이 기록된 주문 건수다. 분할 익절과 잔량 청산은 별도 주문으로 센다.
Code Order의 REST·WebSocket 체결 증거는 `CodeOrderObservationService.apply`가 같은
session의 Order·리스크 원장에 반영하고 한 번 commit한다. 전송 adapter는 관측을 정규화하며,
알림·후속 작업은 commit 성공 뒤 상태 전이 winner만 실행한다. REST 수량 복구 뒤 늦은
WS가 native SL의 정확한 손익을 보충하는 흐름은 유지한다. historical native 증거는 수량을
다시 차감하지 않는다. REST의 부분 TP 보호 상실·0체결 청산 복구와 WS의 외부 ID가 없는
terminal 증거는 기존 경로별 의미를 보존한다. 누적대금이 없는 REST 진입은 VWAP 실패로
승격하지 않고 증거 대기로 처리한다.
목록 배지와 대시보드 합산에도 미정산 상태를 전달한다. 대시보드는 해당 소계를 중립색으로
표시하고 전체 자산 곡선을 보류한다. 실제 인증·개발 서버의 MCP Playwright 검증은
모든 거래 API를 대체한 범위이며, 실제 거래소나 worker 실행의 증거가 아니다.

non-native 코드 청산의 REST 손익 관측은 `CodePnlEvidenceService.apply`가 반영한다.
단건 refresh와 계정 sweep은 원격 조회를 끝낸 뒤 관측·최초 반영/재검사 모드를 전달하며,
이 module이 충돌 사실과 증거 기반 손익 CAS를 같은 Repository의 단일 commit으로 확정한다.
증거가 없는 관측도 충돌 사실을 보존하고 다른 주문의 유효한 관측을 버리지 않는다.
단건의 증거 지연은 기존 지수 백오프·횟수 상한으로 재시도하며, 소진 시 코드 증거 지연
원인으로 알리고 종료한다. sweep의 legacy 확정·계측은 코드 원격 조회보다 먼저 끝난다.
native SL의 terminal WS 손익과 legacy의 페이지 합산·조회 완전성 계약은 별도다.

라이브 코드는 `tasks/code_live_signal.py`에서 핀 버전·소유자·Bybit demo·동결 설정을 확인하고 전용 `CodeEvaluationService`로 보낸다. 기존 Pine replay·주문 이벤트 큐를 통과하지 않는다. 현재 제품 경계는 **1h·1X·next_bar_open**이며 실제 demo 시장가의 지연·슬리피지가 역사적 다음 시가와 같다고 보증하지 않는다. 수량 추정 가격과 손절 기준 2봉은 같은 완료 봉 집합을 사용한다. 실제 시장가 VWAP은 그 완료 종가 추정값과 다를 수 있다. 수량은 세션 등록 당시 고정 `equity_baseline_usdt` × 동결 `position_size_pct` / 가격을 Decimal로 계산해 `2×qty_step`에 내린다. 두 절반이 각각 최소 수량 이상이어야 하며 50% 익절을 생략하지 않는다. 백테스트의 current cash 복리 사이징과 다른 정책이므로 두 자본 경로가 동일하다는 주장을 하지 않는다.

`trading.live_code_bars`(migration `20261022_0004`)는 세션+봉 시각 및 세션+순번이 유일하다. 실행 해시, OHLCV, 평가 때 관찰한 실제 포지션, 워밍업 여부, 수량 등 전달 인자, 입력 해시, intent, 상태를 저장한다. 최초 워밍업은 명시적으로 flat이다. 새 진입 전에 거래소 포지션과 확정 체결 원장이 정확히 맞아야 한다. 첫 관찰을 놓쳤거나 봉 공백이 있으면 현재 포지션으로 과거를 추측하지 않는다. 재시작은 저장된 입력 전체를 같은 격리 실행기에 재생한다. 임의 Python 객체 상태를 JSON으로 추측·복원하지 않는다. 저장된 intent와 달라지면 차단한다. 전체 재생 상한은 50000봉이며 이를 넘으면 새 진입을 거부한다.

입력·의도는 외부 주문 전달 전에 `prepared`로 커밋한다. coordinator에는 checkpoint UUID를 `intent_key`로 전달하고 전달 완료 후 `delivered` 및 세션 워터마크를 커밋한다. ACK 유실 시 현재 수량·현재 포지션을 과거 입력에 덮어쓰지 않고 같은 키·저장된 전달 인자로 재시도한다. 다음 봉까지 이미 종료된 오래된 진입 의도는 새 주문으로 재시도하지 않는다. 라이브 봉 재생은 transport 생성부터 30초 deadline을 적용한다. 생성 전의 체크포인트 검증과 종료 cleanup까지 포함한 호스트 전체 wall time을 30초로 보장하는 뜻은 아니다. 실제 주문·부분 체결·보호 SL 확인·반전의 권위는 기존 영속 리스크 원장과 실행기다. 소스 오류·이미지 불가를 검사하기 전에도 열린 포지션의 보호·취소 복구를 먼저 시도한다.

연구·백테스트의 900초 격리 한도와 라이브 transport의 30초 한도는 다르다. 백테스트 실행
통과만으로 라이브 실행 가능성을 보증하지 않는다. [운영 측정 gate](sol-operational-gate.md)는
체크포인트 검증·컨테이너 생성·init·봉 재생·cleanup 확인을 모두 포함한 전체 30초를 별도로
판정한다. 전체 실행 시간으로 parser 단계만의 시간을 추정하지 않으며, 원문과 누적 입력 규모별
실측 전에는 시간 한도 통과를 주장하지 않는다.
