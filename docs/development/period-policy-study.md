# 기간별 Pine·Python / A·B 정책 비교 연구

PRD §5의 결과·가정 공개와 ADR-046의 격리 실행 경계를 따른다. 연구 산출물은
`runs/indicator-strategy-period-study-20261026/`에 두고, 공유 앱 DB·Celery·거래소 주문을 사용하지 않는다.

## 선정과 출처

`tools/research/select_tradingview.py`는 제공된 목록의 지표·전략 각각에서 로켓/댓글 상위
500개를 선정한다. 동점은 수집 페이지·카드 순서로 정하고 publication ID로 합친다.
이번 고정 입력의 합집합은 지표 708개·전략 692개다. 원시 파일별 SHA와 선정 순위·교집합을
목록에 보존한다. 이는 TradingView 전체 순위가 아니다. 전략은 표시 전체 5,760개 중
수집된 3,360개가 대상이다. 서로 다른 게시물의 같은 원문 SHA는 별도 표시하며 독립 원문으로 부풀리지 않는다.

원문은 실제 공개 `Source code` 클릭의 응답만 저장한다. 원문 bytes SHA·응답 URL·버전·
수집 시각·시도별 실패를 보존하고, 실패는 최초 시도와 재시도 한 번 뒤 종결한다.
과거 원문은 publication·SHA가 일치할 때만 재사용한다. 과거 리뷰의 binding이 원문의
실제 호출 위치인지 다시 확인한다. 원문 뒤에 새 alert를 추가한 과거 진단본이나 상태를
교차 이벤트로 바꾼 계산을 원본 신호로 승격하지 않는다.

## 신호와 불변 실행 정책

기존 `code_v1`은 기존 동작·해시를 유지한다. `code_research_v1`만
`provenance.research_execution`의 엄격한 `ResearchExecution` 계약을 요구한다.

| 필드 | 허용 값·의미 |
| --- | --- |
| `contract_version` | 정수 `1` |
| `exit_policy` | `signal_only_v1`(A) / `swing_two_bar_v1`(B) |
| `reentry_policy` | `close_then_reenter_v1` |
| `signal_mode` | `shared_events` / `position_feedback` |
| `signal_mapping_hash` | 원문·입력·검토한 방향 매핑에 결박된 SHA-256 |

`shared_events`는 포지션에 무관한 원본만 사용한다. Pine와 Sol 생성 Python은 각각 실제
실행해 신호열을 만들고, 같은 코드 경로의 A/B만 동일 신호열을 공유한다. `signal_tape`는
준비 봉을 포함한 전체 입력과 원문·입력·매핑 해시를 검사한 뒤 재생한다.
`position_feedback`은 A/B 각각의 확정 포지션을 코드에 전달해 별도로 실행한다.
이 결과에는 진입 신호 차이까지 포함되므로 청산 효과만의 비교와 분리한다.
현재 포지션 피드백은 `strategy.position_size`·`position_avg_price`만 지원한다.
계정 equity·손익·개별 open/closed trade 상태가 필요한 원문은 가짜 계정으로 대체하지 않고
`not_comparable / unsupported_broker_feedback`으로 구분한다.

새로운 같은 방향·반대 방향 이벤트는 잔량 전부 청산 → 이전 계획 폐기 → 청산 비용을
반영한 자본으로 신규 수량·episode·계획 생성 순서다. 같은 이벤트 ID의 재수신만 중복이다.
연속 봉의 다른 같은 방향 이벤트는 각각 재진입한다. 단순 상태 지속을 이벤트로 만들지 않는다.
반익절 fill은 독립 승리 episode가 아니며, 완료 episode가 없으면 완료 승률은 미산출이다.

A는 원문의 진입·명시적 close만 따른다. B도 명시적 close를 적용하며 별도 보호를 추가한다.
원본 strategy의 가격 주문·자체 SL/TP를 생략했다면 차이를 명시한다. 기존 Strategy Tester의
전체 주문 규칙·성과 재현으로 표현하지 않는다. 봉당 하나의 action 프로토콜로 표현할 수 없는
복수 행동·동적 방향·모호한 순서는 임의 선택하지 않는다.

## 청산·데이터·기간

시장은 Bybit BTCUSDT linear perpetual, 신호 주기는 1h·4h·1d다. 완료 신호는 다음 부모
봉 시가에 체결한다. B의 최초 SL은 직전 완료 2봉의 저가 L/고가 H와 실제 진입가 E로
롱 `L−0.10×(E−L)`, 숏 `H+0.10×(H−E)`다. 유효하지 않은 스윙은 진입 거절이다.
최초 R을 고정하고 최초 수량 절반을 1.5R에 익절한다. 이때 SL은 유지하며 2R부터 본절·
고정 거리 2R 추적을 활성화한다. 잔량 SL은 유리한 방향으로만 이동한다.

실행 순서는 기존 포지션 펀딩 → 대기 시장가 → 보호 청산 → 종가 평가다. 1분봉 두 OHLC
경로 중 기존 보호 상태기의 불리한 종가 평가 시나리오를 사용하며 실제 틱 순서나 모든
가능 경로의 최악값으로 주장하지 않는다. 원장에는 이벤트·episode·계획 세대, 진입/청산
사유, 수량·가격·수수료·슬리피지·펀딩, SL 변화·실현/미실현 손익을 보존한다.

| 기간 | UTC 시작 포함 | UTC 종료 미포함 |
| --- | --- | --- |
| P1 | 2024-01-01 | 2024-07-01 |
| P2 | 2024-07-01 | 2025-01-01 |
| P3 | 2025-01-01 | 2025-07-01 |
| P4 | 2025-07-01 | 2026-01-01 |
| P5 | 2026-04-24 | 2026-10-24 |

기간마다 10,000 USDT·1배·100% 배분·단일 포지션으로 독립 초기화한다. 준비 봉은 계산에만
사용하고 마지막 미체결 신호는 체결하지 않는다. 종료 시 가상 청산 없이 미청산 평가손익을 포함한다.
공백 기간을 성과에 넣거나 기간별 자산 곡선을 하나로 연결하지 않는다.

비용은 taker 0.020%·maker 0.010%·slippage 0.01%와 해당 시점 관측 펀딩 한 종류다.
시장가/트리거는 taker+slippage, 부분 TP는 기존 maker 비용 함수를 사용한다.
이 숫자는 연구 가정이며 거래소의 실제 계정 요율로 주장하지 않는다. 과거 연구의 비용·모델·
재진입 조건과 다르므로 기존 금융 성과는 재사용하지 않는다.

원문별 준비 이력과 부모봉·1분봉·펀딩의 실제 원시 응답·시간 격자·중복·집계·경계를 검사한다.
누락은 보간·복사·0으로 채우지 않는다. 관측 정산의 수집 완결과 과거 정산 일정의 독립 검증은
별도 상태다. 전체 정산 일정의 근거가 없으면 완전성을 UNKNOWN으로 보존한다.

## 실행·통과·등록

분모는 1,400원본 × Pine/Python × A/B × 3시간봉 × 5기간 = 최대 84,000셀이다.
원문 확보·생성·native 대조·금융 실행·등록은 별도 분모다. 실패·미실행·재시도 필요·완료를
분리하고, 미지원 또는 참조 부재를 성공이나 0수익으로 바꾸지 않는다.
동일 namespace의 다른 입력은 덮어쓰지 않는다. 요청·원문·데이터·이미지·실행 코드·정책·
재진입 버전·신호 매핑 해시가 일치할 때만 셀 결과를 재사용한다.

Sol은 Codex 구독 `gpt-6.1-sol/high`만 요청한다. 180초·기존 출력 예산과 최대 두 시도를
보존하고 모델을 대체하지 않는다. provider-reported 모델이 없으면 UNKNOWN이다.
소스는 검토 뒤 기존 Linux gVisor 실행기에서만 실행한다. 로컬 자원 상한은 12CPU·16GiB이며,
브라우저 소유자는 하나다. GitHub는 확인한 무료 범위에서만 사용한다. job/PID·진행 로그·
재개 지점·원시 실패를 저장하고 실제 종료를 확인한다. 초기 VM·태그 상태는 종료 후 복원한다.

등록 단위는 원본 × 코드 경로 × 정책 × 시간봉이다. 해당 단위의 5기간 실행·원장 재현과
확보 가능한 native 기술 검증을 모두 요구한다. 실제 원문/컴파일 metadata·입력·초기 이력·
OHLCV·검토 binding이 일치한 원시 캡처, 비어 있지 않은 확정 사건, 반복/prefix 대조를
검사한다. 포지션 의존 원본은 실제 상태를 맞춘 대조와 정책별 피드백 검증도 구분한다.
부분창 관측은 전체 과거 기간의 TradingView 성과 검증이 아니다. 수익성 필터는 적용하지 않는다.

### Native 부분창 대조 CLI

`tools/research/period_native.py`는 검토한 `shared_events` 원본의 실제 TradingView 캡처를
Pine·Python 각각의 gVisor 실행과 대조한다. 첫 지원 범위는 전역의 명시적인 방향 plot/alert
신호다. 미지원 Pine이 Python의 직접 대조까지 막지는 않는다. 포지션 의존 원본은 native가
관측한 실제 정책별 포지션 상태를 아직 재생하지 못하므로 strict native 통과로 승격하지 않는다.

브라우저에서 무수정 원문을 실제 에디터에 넣고 컴파일·차트 추가한 뒤
`native/<publication_id>/<timeframe>.json`에 아래 관측을 보존한다. 에디터에 다른 스크립트가
남아 있거나 컴파일 요청과 원문이 다르면 의도한 소스로 바꿔 기록하지 않는다.

| 원시 필드 | 실제 관측과 검증 |
| --- | --- |
| `id`, `symbol`, `timeframe`, `observed_at` | 게시물·`BYBIT:BTCUSDT.P`·시간봉·UTC 관측 시각 |
| `source_sha256` | 해당 캡처 소스 bytes의 SHA-256 |
| `compiled_source`, `compile_request_source` | 실제 에디터 본문과 실제 컴파일 HTTP 요청 본문. 원문과 LF 정규화 후 일치 |
| `inputs`, `resolved_inputs` | 검토된 override와 기본값을 포함한 전체 실제 입력 |
| `compile_responses` | 해당 컴파일의 성공 응답 하나. 실제 `ilTemplate`·`metaInfo` 보존 |
| `wire` | 실제 WebSocket 송수신 `{direction, data}`. `~m~길이~m~` 프레이밍 보존. 손실 없이 해독한 `{direction, m, p}`도 허용 |

같은 chart session의 `create_study`로 study·chart·IL·입력을 결박한다.
`study_completed`, study의 `du.st`, chart의 `du.s` 또는 `timescale_update.s`가 필요하다.
행의 `v[0]`는 Unix 초이며 OHLCV 행은 `[시각, O, H, L, C, V]`다. 다른 study나 차트의
값을 합치지 않으며 미확정 봉·충돌하는 확정 중복·공통 확정봉 누락은 거절한다.
색 입력은 실제 v6 캡처에서 확인한 `color.green/yellow/red/aqua`의 컴파일 hex와
unsigned ABGR wire 값을 대조한다. 관측하지 않은 버전·기본색은 추측하지 않고 거절한다.

요청의 첫 행 인덱스 `i=0`은 숨은 계산 이력이 없다는 증거가 아니다. 무수정 원본 캡처와
별개로, **원문 본문을 정확한 접두사로 보존**하고 다음 한 줄만 끝에 추가한 진단본을 같은
심볼·입력·시간봉에서 컴파일·차트 추가한다.

```pine
plot(bar_index, "__QB_BAR_INDEX__", display=display.none)
```

진단본은 `native/<publication_id>/<timeframe>-initialization.json`에 실제 별도 캡처로
저장한다. 이 파일의 `source_sha256`·에디터·요청은 진단본 자체에 대응해야 한다. 진단본을
무수정 원본이라고 부르지 않는다. 두 캡처의 첫 확정봉과 전체 원본 관측창의 OHLCV·원래
방향 신호가 정확히 같고, study/가격 전체 행이 공통창과 일치하며 진단 열이 첫 봉부터
`0, 1, 2, …`일 때만 초기 이력을 확인한다. 다른 진단 로직·추가 신호는 허용하지 않는다.

```bash
cd apps/api
set -a; . ./.env.local; set +a
uv run --no-sync python ../../tools/research/period_native.py \
  --run ../../runs/indicator-strategy-period-study-20261026 \
  --id so4mWdrN --timeframe 1d
```

실행 전 기존 격리 VM의 Docker endpoint와 gVisor 이미지를 사용한다. CLI는 호스트에서
전략을 실행하지 않는다. 전체 이력·동일 입력 반복·짧은 접두 이력을 각 코드 경로에서 실제
실행하고, 검토된 준비 봉 이후 양방향 사건의 시각·방향이 native와 정확히 같아야 한다.
이미지 ID와 원시 증거 SHA도 실행 전후 확인한다.

결과는 `native-verification/<publication_id>-<timeframe>.json`과 삭제하지 않는
`native-attempts/`에 기록한다. `paths.pine`·`paths.python`을 독립 판정하고, 전체
`status=passed`는 적어도 한 경로가 통과했다는 뜻이다. 등록은 해당 코드 경로의
`paths.<code_path>.status=passed`·`evidence_verified=true`와 5기간 원장 재현을 모두
요구한다. 원시 캡처나 초기 이력 증거가 없으면 `unverified`, 실행하지 못한 경로는
`not_run`, 실제 실행 오류는 `failed`, 신호·반복·접두창 불일치는 `mismatch`로 보존한다.
파서·컴파일 응답·소스·실행기·증거 해시와 관측창을 남기며, 이 판정은 **관측한 부분창의
기술 대조**다. P1~P5 전체 native 신호·성과 또는 Strategy Tester 체결 재현을 보증하지 않는다.

새 정책을 지원하는 서버에서만 정의를 저장하고 원문·계약·해시·불변 version UUID·기간
근거를 전량 GET해 대조한다. 기존 정의는 보존한다. 서버가 지원하지 않으면 등록 payload와
검증 PR을 준비해 `validated_registration_pending_deployment`로 남긴다.
등록은 배포·Demo 활성화·주문을 허용하지 않으며 연구 정의의 Demo 활성화는 차단한다.
