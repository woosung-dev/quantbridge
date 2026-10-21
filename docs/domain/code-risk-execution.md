# 생성 코드의 데모 주문·리스크 실행 계약

[ADR-046](../adr/046-generated-strategy-language-evaluation.md)의 `code_v1`에만 적용한다.
기존 Pine 세션은 `execution_snapshot IS NULL`, 기존 주문은 `risk_context IS NULL`로 구별한다.
아래 구현은 실제 주문 없이 가짜 공급자와 슬롯 테스트 DB로 검증한다. 운영 활성화는 별도다.

## 활성화와 불변 입력

`POST /live-sessions`는 `source_policy="code_v1"`와 `strategy_version_id`로 명시 진입한다.
서버는 소유자를 확인한 불변 버전과 검증한 `StrategySettings`로 스냅샷을 생성한다.
선택적인 요청 `execution_snapshot`은 동일성 검사에만 쓰며 저장값을 덮어쓰지 않는다.

스냅샷 필수값은 `schema_version=1`, `source_policy=code_v1`,
`policy_version=swing_two_bar_v1`, `version_id`, `language`, `source_hash`,
`execution_hash`, `params`, `warmup_bars`, `execution_mode=bybit_demo`, `market_type=linear`다.
`execution_settings`에는 서버가 동결한 레버리지·마진·포지션 비율을 저장한다.
실제 `source_code` SHA256과 버전/스냅샷의 해시·언어·정책·파라미터·워밍업을 대조한다.
저장 버전의 `read_code_version` 공통 검증기로 생성 이력을 포함한 전체 실행 해시도 확인한다.
`sizing_policy=session_initial_equity_percent_v1`을 동결하며, 1h·next_bar_open·1X만 활성화한다.
쓰기 권한이 확인된 Bybit demo 계정만 허용한다. 실행기 미주입·미완성 버전은 거부한다.

라이브 코드의 30초 제한은 transport 생성부터의 deadline이다. 이전 체크포인트 검증과
cleanup을 포함한 전체 호스트 wall time 보장은 아니며, [별도 운영 gate](../development/sol-operational-gate.md)는
전체 재생·cleanup 확인까지 30초 이하인지 더 엄격하게 측정한다. 연구 900초 실행 통과를 이 gate의 통과로 대체하지 않는다.

## 체결과 고정 R

`LiveRiskState`는 세션당 한 행이며 `revision` CAS로 갱신한다.
주문 귀속은 `Order.risk_context={session_id,generation,role}`에 저장한다.
진입 전 직전 완료 2봉의 extreme까지 거리 × 1.1로 임시 SL을 주문과 함께 저장한다.
누적 체결량·가치는 단조 갱신하고 중복 이벤트를 무시한다. terminal 진입 VWAP만 초기 R을
확정한다. 이후 동일 방향은 R을 바꾸지 않는다. 실제 절반 수량이 최소/단위 규칙을
만족하지 못하면 새 진입을 막고 축소한다.

부분 진입에도 SL을 적용한다. 최종 체결 후 SL을 실제 VWAP 기준으로 조정하고,
1.5R의 reduce-only 절반 TP 주문과 2R 거리/2R 활성가의 native trailing을 전달한다.
실제 가격 관측이 2R에 도달하면 손익분기 이상으로 SL을 이동한다.
독립 포지션 조회가 SL·trailing ACK를 확인한 뒤 `protection_applied`를 갱신한다.
그 전까지 desired/applied 차이는 대기 상태다. 실패는 새 진입 중단과 reduce-only 청산 의도를
영속화한다. 거래소가 만든 native SL/trailing 청산은 실제 flat 확인으로 원장에 수렴시킨다.
0이 아닌 잔량 차이는 SL 체결로 합성하지 않는다. 주문별 누적 체결 증거를 기다리며
보호 교체·새 청산 명령도 보류한다. 실제 flat 뒤 늦게 도착한 TP는 진입 총량 안에서
기록을 보충하고 포지션을 다시 차감하지 않는다.

거래소 눈금의 실제 가격은 이론 R과 별개다. SL은 long 내림/short 올림으로 최대 1tick
추가 손실 거리를 허용한다. 절반 TP는 long 올림/short 내림으로 1.5R보다 이르게 당기지 않는다.
`Order.risk_context.venue_order`에 이론/실제 제출 가격과 tick을, `protection_applied.venue`에
실제 SL·trailing 거리·활성가·조회 SL/거리·손익분기 가격을 저장한다. 고정 R 자체는 바꾸지 않는다.

중간 tick VWAP에서는 long 손익분기 가격을 ceil(E), short는 floor(E)로 정한다.
native 거리를 ceil(2R)로 잡고 활성가는 long에서 `BE+거리` 이상, short에서 `BE−거리` 이하로
맞춘다. 따라서 활성 시 초기 native stop이 E의 손실 쪽에 놓이지 않는다. 이론 2R보다
최대 2tick 미만의 활성화 지연이 생길 수 있다. backend가 이미 2R을 관찰한 경우 SL도
이 손익분기 눈금 이상/이하로 이동한다. 이 보장은 거래소가 ACK한 파라미터의 수치 조건이다.
Bybit position 조회는 SL·거리만 검증하며 activePrice 읽기 검증은 제공하지 않아
`active_price_readback_available=false`를 함께 기록한다. 실제 데모 체결 검증 완료를 뜻하지 않는다.

수량은 세션 시작 equity 기준선의 동결 비율을 가격으로 나눈 뒤 `2×qty_step`에 내린다.
각 절반이 최소 수량 이상이어야 한다. live는 시작 equity 고정, 연구 백테스트는 현재 cash의
비율로 복리 계산하므로 여러 거래 뒤 명목 규모가 같다는 주장은 하지 않는다.
시장가의 실제 terminal VWAP가 진입 가격 권위이며, 다음 봉 시가 체결 보장은 없다.

공식 계약: [주문 가격 tick](https://bybit-exchange.github.io/docs/v5/order/create-order),
[종목 규칙](https://bybit-exchange.github.io/docs/v5/market/instrument),
[native 보호](https://bybit-exchange.github.io/docs/v5/position/trading-stop).

## 명령 전달과 재시작

원장 CAS와 `CodeRiskCommand` outbox enqueue는 같은 트랜잭션이다.
상태는 `pending/running/applied/failed/superseded`이며, 세션별 PostgreSQL advisory lock으로
짧게 claim한 뒤 commit하고 외부 IO를 수행한다. lease는 60초, 명령 IO 예산은 45초다.
lease token이 같은 실행기만 ACK할 수 있다. 만료 뒤 재시도는 같은 UUID로 먼저 조회한다.
외부 시스템을 포함한 exactly-once는 주장하지 않는다. 응답 유실은 UUID 조회·중복 제거로
수렴시키고 조회만으로 미발주를 증명할 수 없으면 취소 확인을 대기한다.

새 진입 UUID는 세션+봉의 `intent_key`, TP UUID는 세션+세대에 고정한다.
청산 재시도는 실제 잔량과 종결된 시도를 반영한 별도 UUID를 쓴다.
실행기는 세대·현재 desired token과 다른 명령을 무효화한다.
WS 체결 직후·연결 복구·5초 주기 복구가 전용 주문/포지션을 조회해 전달을 이어간다.
종료된 세션이나 소스 검증 실패도 기존 포지션의 축소·취소를 차단하지 않는다.

## 종료와 반전

close/반대 방향 의도는 먼저 영속화하고 미완료 진입을 취소하며 실제 잔량을 축소한다.
취소 요청 ACK만으로 완료 처리하지 않고 주문 terminal 상태와 실제 flat을 재조회한다.
자체 TP 주문과 거래소 보호 자식이 모두 사라진 뒤에만 반전을 준비한다.
이전 반대 의도를 지연 발동하지 않는다. 다음 평가의 **새로운 같은 방향 의도**가 있어야
그 평가의 수량·직전 2봉으로 새 세대를 만든다. 이 지연 정책 때문에 과거 신호의 2봉은
다음 진입의 SL 계산에 재사용하지 않는다.

V5 원본 `cumExecValue`와 CCXT `info.cumExecValue`를 같은 정확한 누적 체결대금으로
정규화한다. 반올림된 `avgPrice × cumExecQty`로 합성하지 않는다. 양수 진입 수량에
정확한 체결대금 증거가 없으면 REST/WS 모두 정합 보류하며 원장을 확정하지 않는다.
보호 적용 직전 같은 방향의 포지션이 미종결 진입 원장보다 크고 예상 진입 수량 이내이면
늦은 누적 체결 증거를 기다린다. 예상 초과·반대 방향·종결 후 초과는 기존 실패 경로다.
새 코드 주문은 `PartiallyFilledCanceled` 원본 취소 상태를 보존한다. 절반 TP 잔량이
취소되고 포지션이 남았으면 보호 상실로 새 진입을 차단하고 축소 명령을 영속화한다.

`LiveSignalState`는 UI 캐시다. 리스크 권위나 재시작 원장으로 사용하지 않는다.


## 사용자 조회 요약

`GET /live-sessions/{id}/state`는 코드 세션에서 `LiveSignalState`를 읽지 않는다.
`code_execution`은 최신 `LiveCodeBar`의 상태·봉·의도와 `LiveRiskState`의 세대·잔량·
terminal VWAP·고정 R·보호 ACK 대기·진입 차단·반전 대기를 반환한다.
`evaluated`는 워밍업이 아닌 체크포인트가 존재한다는 뜻이며, `prepared`도 포함한다.
의도 전달(`delivered`)은 주문 체결 완료를 뜻하지 않는다. 체크포인트가 없어도 실현손익과
출처 소계는 세션 범위의 실제 체결 주문에서 계산하며, 기존 시뮬레이션 캐시로 대체하지 않는다.
코드 세션의 주문 범위는 정확한 `risk_context.session_id`와 전략·계정·심볼로 정한다.
종료 후 복구 청산도 원래 세션의 손익·미정산 주문 개수에 포함하며, 같은 시간창의 수동 주문이나
다른 코드 세션 주문은 제외한다. legacy는 기존 `filled_at` 반열림 시간창 계약을 유지한다.
legacy 세션의 `code_execution`은 null이다. 코크핏의 전략 이름은 코드 전략 목록도 포함한다.

코드 WS의 부분 체결 취소·거부는 `Order`에도 수량·평균가·거래소 ID를 같은 commit으로 보존한다.
중복 terminal 수신은 상태 CAS로 부수효과를 반복하지 않는다. 기존 실패 주문의 추정 손익은
제외하고, 코드 귀속과 양수 체결분이 있는 취소·거부만 실제 체결 조회에 추가한다.
`OrderResponse.has_recorded_fill`은 같은 체결 증거를 서버에서 계산한 표시용 bool이며,
`risk_context` 원문은 노출하지 않는다. 기존 filled와 코드 양수 부분 체결 종결은 true다.
미체결·legacy 실패 주문은 false이며, 이 값만으로 손익 확정을 뜻하지 않는다.
그 주문은 기존 closed-PnL refresh·원장 sweep·백필/정정 CAS·세션 손익·kill-switch 합계에
포함한다. 순수 진입 주문은 기존 reduce-only 게이트에 따라 closed-PnL refresh를 예약하지 않는다.



## native 청산 미정산과 손익 표시

로컬 축소 주문의 누적 체결로 설명되지 않는 잔량이 거래소에서 flat으로 관측되면
`LiveRiskState.unsettled_exit_quantity`에 그 잔량을 남긴다. 잔량은 실제 flat으로 갱신하되
`native_exit_unsettled` 사유로 새 진입을 차단한다. 이는 native SL 체결 원인·가격·손익을
확정한 것이 아니다. 아래 attached SL 명시 귀속을 통과하지 못한 WS는 orphan으로 폐기하고, `ExchangeExit`의 native
SL/trailing 분류·추정 전략 귀속을 정확한 세션/세대 체결이나 확정 손익으로 승격하지 않는다.

같은 계정 ID와 알려진 `exchange_uid` 형제는 종료·archive된 세션의 미정산도 조회한다.
미정산 계정은 legacy를 포함한 새 세션 등록과 코드 신규 진입 준비·전달을 거부한다.
코드 venue도 거래소 주문 조회·시장 규칙 조회 뒤 `submitted` 전이 전에 재조회한다.
새 진입만 보류하여 아직 거래소에 없는 주문은 pending을 유지한다. 이미 거래소에 존재하는
같은 UUID 주문은 재생성하지 않고 체결 정합을 계속한다.
수동·웹훅·legacy 신호의 `OrderService`도 비축소 신규 주문을 거부한다. 이미 생성된 큐
주문은 실제 provider `create_order` 직전에 같은 정본 쿼리를 재조회하여
`native_exit_unsettled`로 종결한다. 축소 주문·취소·보호 변경·기존 outbox 보호 복구는
이 가드로 막지 않는다. 조회 직후 거래소 호출과 DB marker 변경을 원자화하지는 못한다.
세션 FK는 RESTRICT로 보존하여 세션 삭제로 marker를 제거하지 못한다.
0005 downgrade도 양수 marker가 있으면 필드·FK를 바꾸기 전에 거부한다. 기존 Order FK도
전략·계정 삭제를 제한한다. UID가 불명인 새 계정 행이 같은 실제 계정인지 판별할 수 없는
한계는 남는다. NULL·빈 문자열·공백만 있는 UID는 모두 unknown으로 취급하며
그 값만으로 다른 계정 행을 묶지 않는다. 권위 리스크 행의 임의 DB 삭제는 제품 API가 제공하지 않는다.

뒤늦은 **기존 로컬 Order의 session·generation·reduce-only·terminal 누적 체결**만
`exit_fills`에 아직 기록되지 않은 증가분으로 marker를 한 번 상쇄할 수 있다. 다른 이유의
진입 차단은 해제하지 않는다. 검증된 attached SL 관측 행도 같은 정본을 사용한다.
미귀속 native 주문·inferred 원장 행에는 자동 해제가 없다.
marker 발생 뒤 새로 관측한 정확한 로컬 주문의 증가분은 주문별
`exit_fills.unsettled_pending`으로 저장하고 terminal 수신 때만 한 번 상쇄한다.
재시작·같은 누적값의 terminal 재관측에도 이 대기분을 복구한다. marker 이전에 이미
알던 TP/close 누적값은 credit하지 않는다. 일반 resolve API는 제공하지 않는다.

코드 상태 응답의 `pnl_scope=known_order_subtotal`은 **알려진 주문 손익 소계**다.
미정산 수량이 있거나 실제 축소 주문의 `realized_pnl`이 아직 없으면 `pnl_complete=false`다.
`unpriced_exit_orders`는 후자의 개수이며 `code_execution.unsettled_exit_quantity`는
전자의 수량이다. 화면은 false일 때 **손익 미정산·전체 실현손익 아님**을 표시한다.
수량 marker가 양수이면 같은 계정 새 진입 차단도 알린다. 세션 목록 배지도 미정산 소계를 중립색으로 표시한다.
대시보드는 활성 세션 중 하나라도 미정산이면 알려진 소계와 해당 세션 수를 표시하고,
수익·손실 강조색과 자산 곡선을 보류한다. 숫자 0이나 confirmed 소계 0은 전체 손익 확정 0이 아니다.
기존 fake native 여정은 보호 파라미터 ACK와 명시적 close 주문을 검증했으며,
실제 native SL/trailing 자식 주문의 체결 회계·자동 귀속을 검증한 결과가 아니다.


## 명시 부모가 있는 attached SL 관측

Bybit의 `parentOrderLinkId`는 futures의 원래 attached TP/SL 부모 client ID다.
원래 attached 보호를 trading-stop으로 변경한 경우에도 유지되지만, attached 보호가
없던 포지션에 나중에 추가한 경우는 유효한 연결 증거가 아니다.
이 계약을 native trailing 전체로 확대하지 않는다. 시간·가격·positionIdx만으로 귀속하지 않는다.
공식 근거는 [private order WS](https://bybit-exchange.github.io/docs/v5/websocket/private/order),
[실시간 주문](https://bybit-exchange.github.io/docs/v5/order/open-order),
[주문 이력](https://bybit-exchange.github.io/docs/v5/order/order-list),
[trading-stop](https://bybit-exchange.github.io/docs/v5/position/trading-stop)이다.

현재 귀속 범위는 Bybit demo linear·one-way(`positionIdx=0`)의
`StopLoss`/`CreateByStopLoss`·reduce-only 주문뿐이다. 같은 계정의 부모 UUID가
현재 세대 entry이고 임시 SL이 부착되어 있어야 한다. 부모의 session·generation·전략·
심볼·소유자와 자식의 반대 side를 대조한다. 자식 외부 ID는 부모 외부 ID와 달라야 한다.
외부 ID 조회는 계정 범위를 포함하며, 부모 UUID가 자식 orderLinkId로 전달되어도 부모를 갱신하지 않는다.

`Order`에 별도 관측 행을 만들며 `risk_context.native_origin=bybit_attached_sl`,
불변 `native_binding`, `parent_order_id`, 정확한 `native_fill` 누적 수량·대금을 보존한다.
부분 체결도 `filled_quantity`와 정확한 대금/수량 평균가를 보존한다. 반올림 avgPrice로
대금을 합성하지 않는다. 계정+외부 ID의 transaction advisory lock과 결정적 UUID로
WS/REST 중복을 직렬화하고, 현재 리스크 행을 잠근 뒤 관측 행·리스크 CAS·terminal·
미정산 credit를 한 트랜잭션으로 확정한다. 충돌이나 commit 실패는 함께 rollback한다.

미발동 New/Untriggered·누적 체결 0은 미종결 부분 진입을 취소하거나 청산하지 않는다.
양수 SL 체결이 부모 terminal 증거보다 먼저 오면 exit counter를 소비하지 않고 기존
close-request 경로로 미체결 진입 취소·잔량 축소를 요청한다. 부모 최종 누적 증거 뒤 같은
자식을 재처리한다. 이 보수적 대기는 새 영구 failure를 만들거나 진짜 실패 사유를 해제하지 않는다.
복구는 부모 진입을 먼저 조회한 후 자식 이력을 처리한다.

관측 행은 처음부터 submitted 이상이며 새 주문으로 발주하지 않는다. 일반 주문의 실행·
취소 worker와 일반 취소 API는 이 행을 거부한다. 전용 복구·취소는 자식의 실제 외부 ID로
조회하며, 취소 전 신선한 부모/자식 증거를 다시 검증한다. 취소 ACK는 terminal 확인이 아니다.

기존 부모/자식 누적 증거를 먼저 정합하고 현재 포지션을 조회한다. 수량·방향이 원장과
다르거나 양수 미정산 marker가 있을 때만 새 자식 이력을 검색한다. 정상 잔량이 정확히
일치하는 보호·명시 close/cancel은 이력 조회를 기다리지 않는다. 포지션 조회 실패는 기존
정합 보류를 유지한다. WS 누락 복구는 Demo 보존 범위인 최근 7일에서 realtime/history 각각 50행·최대 2페이지를
조회한다. parent는 응답 필드이며 조회 필터로 전송하지 않는다. category·symbol·cursor를
검증하고, 반복/누락 cursor·페이지 예산 소진·잘못된 응답은 새 관측만 보류한다.
네트워크·페이지 오류에도 기존 주문/포지션 정합과 보호·축소·취소 명령은 계속 처리한다.
실패한 조회의 부분 행은 정상 관측으로 반환하지 않으며 marker·PnL을 추정하지 않는다. 빈 응답은
청산 부재나 취소 완료 증거가 아니다. [Demo 범위](https://bybit-exchange.github.io/docs/v5/demo).

수량 귀속과 손익 확정은 별개다. native 관측 행은 기존 closed-PnL aggregate 자동
확정·sweep·백필·정정에서 제외한다. 검증된 terminal WS의 주문별 정확한 `closedPnl`만
독립 CAS로 기록하며 중복 금액을 합산하지 않는다. REST terminal이 먼저 확정되어 Order
상태 CAS가 0이어도 늦은 WS 금액은 보충한다. 이미 귀속된 과거 세대의 자식도 저장된
account·external ID·부모 UUID·session·generation·SL identity·누적 증거가 동일하면
손익만 보충한다. 현재 리스크·포지션·marker·명령은 변경하지 않는다. 새로 발견된
미귀속 과거 세대 주문은 자동 귀속하지 않는다.

REST로 수량을 복구해 marker가 0이어도 WS의 정확한 closedPnl가 없으면 손익은 NULL이며
`pnl_complete=false`다. 부분 native 체결도 미정산 주문 개수에 포함한다. 손익 미정산만으로
새로운 계정 전체 진입 차단을 만들지는 않는다. 수량 미귀속 차단은 기존 계약을 유지한다.
실제 Demo native SL 자식 관측은 아직 검증하지 않았으며, 이번 근거는 가짜 Bybit 응답과
슬롯 SQL의 양성·음성·두 트랜잭션 경합 검증이다. native trailing 자동 귀속 보장은 없다.


## 일반 주문과 최종 발주의 소유권 경계

일반 수동·웹훅·legacy 신규 non-reduce-only 주문도 실제 저장 직전에 같은
`acquire_code_symbol_admission(..., is_code=false)` 정본을 사용한다. KillSwitch가
commit할 수 있으므로 그 뒤에 검사하고 INSERT commit까지 같은 transaction 락을 유지한다.
같은 물리 계정·정규화 심볼의 활성/미정리 코드 소유자가 있으면 409
`code_position_reserved`로 거부한다. idempotent 재조회는 기존 주문을 반환한다.
legacy끼리의 기존 정책과 reduce-only 저장·발주는 유지한다.

일반 worker는 provider 선택 후 실제 create_order 직전에 같은 정본을 재확인하고
실패하면 주문을 거절한다. 성공하면 이미 영속된 submitted 행이 코드 등록을 막으므로
commit으로 락을 풀고 외부 호출한다. 코드 venue의 신규 진입도 정확한 session UUID·entry
귀속으로 `acquire_entry_admission`을 submitted 전 재검사하며, 차단 시 pending을 유지한다.
기존 거래소 UUID 주문은 새 발주 없이 정합하고 보호·축소·취소는 이 가드를 적용하지 않는다.

코드 venue의 신규/축소 주문은 `OrderSubmit.position_idx=0`을 전달한다. Bybit futures
provider는 명시된 값만 `positionIdx`에 넣고 legacy의 기본 None은 전송하지 않는다.
[공식 주문 계약](https://bybit-exchange.github.io/docs/v5/order/create-order)은 0을 one-way,
1/2를 hedge-mode 양 방향으로 구별한다. 이는 one-way 요청을 명시한 것이며 단일 hedge leg나
flat 계정의 포지션 모드를 `fetch_position`으로 독립 확인했다는 뜻은 아니다.


## 코드 청산의 REST 손익 제한 지원

code_v1의 로컬 reduce-only `partial_tp`/`close` 등은 legacy 행 합산을 확정 근거로
사용하지 않는다. [Bybit closed-PnL 계약](https://bybit-exchange.github.io/docs/v5/position/close-pnl)은
orderId·closedSize·fillCount·updatedTime을 제공하지만 행별 체결 ID나 수정 revision·
최종성을 보장하지 않는다. 서로 다른 raw가 독립 분할인지 수정 snapshot인지 추론하지 않는다.
동일 raw 전체의 canonical JSON만 중복 제거한다. updatedTime만 다른 행도 서로 다른 관측이다.
legacy는 raw=None의 기존 합산과 서로 다른 행 합산을 유지하며, 전체 cursor 철거/교체는 별도다.

코드 전용 조회는 원본 V5 linear·symbol·account credentials 범위에서 기존 최근 7일·
100행/최대 5페이지 예산을 재사용한다. 명시적 빈 nextPageCursor까지 읽고 cursor 누락·
반복·예산 소진·잘못된 응답이면 새 확정을 보류한다. matching order의 서로 다른 raw가
정확히 한 개이며 Trade·반대 청산 side·양수 유한 closedSize·유한 closedPnl이어야 한다.
0/음수 손익은 유효하다. 수량은 실제 terminal Order.filled_quantity와 Decimal로 정확히
일치해야 한다. 이는 **수량 일치 단일 거래소 관측의 제한 지원**이며 거래소 최종성 보장이 아니다.
서로 다른 두 행 이상은 수량 합계가 우연히 맞아도 불명이다. 합산·최신 행 선택으로 해결하지 않는다.

refresh·backfill·correction·sweep는 같은 evidence envelope를 중앙 Repository에 전달한다.
계정·외부 주문 ID·심볼·side·reduce-only·청산 역할·종결 실제 수량과 근거가 일치하지 않거나
근거를 생략하면 코드 손익 CAS는 0행이다. 코드 진입/비축소 반전은 확정 대상이 아니다.
기존 native_origin의 terminal exact WS 전용 손익은 이 경로와 분리한다.

같은 코드 주문에 실제로 다른 raw나 부적합한 matching row가 관측되면
`risk_context.pnl_evidence_conflict`에 원본 hash와 불명 사유를 영속화한다. 성공한 단일
관측의 hash도 보존해 이후 조회와 대조한다. 기존 ledger의 다른 원본도 무시하지 않는다.
조회 완료 전의 matching 관측 hash도 별도로 보존하되 수량 일치 proof로 승격하지 않는다.
완전히 matching한 단일 근거는 금액 no-op 재조회에도 최초 metadata로 기록한다.
이전 금액·synced_at은 알려진 소계로 보존하지만 unpriced_exit_orders에 포함하여
`pnl_complete=false`로 표시한다. 수량/보호에 따른 진입 권위나 계정 차단 범위를 늘리지 않는다.
나중의 단일 snapshot으로 영속 충돌을 자동 해제하지 않으며 일반 해소 API는 제공하지 않는다.
통신 실패·단순 조회 미완료·미발견·7일 보존 소멸만으로 이전 관측을 삭제하거나 충돌로
승격하지 않는다. 이전값이 없으면 NULL/미정산을 유지하고 재시도한다.

스윕은 이번에 관측한 matching 코드 원본을 원장 적재와 같은 짧은 트랜잭션에서 대조한다.
금액이 같아 기존 legacy 정정 후보에서 빠져도 충돌은 표시하며, 후보 상한을 이미 일치하는
모든 코드 주문으로 채우지 않는다. strict 원격 조회는 mutation 트랜잭션 전에 수집하고
주문별 ProviderError를 격리해 다음 주문 실패가 앞서 확인한 충돌을 버리지 않게 한다.
