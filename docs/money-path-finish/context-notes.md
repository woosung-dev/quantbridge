# money-path-finish 결정 노트

> 이 스프린트에서 내린 결정과 그 근거. 되돌리려는 사람이 먼저 읽어야 하는 문서.

---

## §1 실측이 착수 전에 전제 2건을 정정했다

**[정정 1] BL-457 의 "새 쿼리가 필요 없다" 는 틀렸다.** 백로그는 스윕이 이미 만드는 `attribution_facts` 로 `known_order_ids` 를 공짜로 만들 수 있다고 적었다. 코드를 보면 그 목록은 `list_filled_for_attribution` 이 **`limit=500` + `state==filled` + `filled_at IS NOT NULL`** 로 좁힌 것이고, 실재 확인이 필요한 행은 **정의상 `state==filled` 매칭에 실패한 주문**이다. 즉 그 목록에는 필요한 행이 구조적으로 없다. 재사용하면 진짜 우리 청산이 `external_manual` 로 뒤집혀 운영자가 헛발화 알림을 받는다.

→ 계정 스코프 + **state 무필터** 전용 메서드 `list_existing_ids` 를 신설했다. **백로그의 그 권장 접근도 제자리에서 정정했다** — 안 하면 다음 독자가 같은 버그를 재도입한다.

**[정정 2] `pnpm format:check` 는 이 레포의 통과 가능 게이트가 아니다.** 킥오프 §5 가 게이트 목록에 넣었지만 main 에서 이미 **356 파일 red** 다. 원인은 `package.json:14-26` — lint-staged 가 FE `{ts,tsx,js,jsx}` 에 **eslint 만** 돌린다(prettier 없음). 내가 만질 `hooks.ts` 조차 baseline 에서 dirty 였다. 356 파일 일괄 포맷은 거대 diff 라 스코프 밖이므로, 기준을 "주변 스타일 일치 + baseline 대비 불변" 으로 바꿨다.

---

## §2 ★백로그에 없던 결함을 찾았다 — BL-464

`attribute_exit`(`exit_attribution.py:99`)이 `order.symbol == symbol` 로 비교한다. 호출부가 넘기는 `snapshot.symbol` 은 Bybit 원문 **`BTCUSDT`**(`providers.py:368`)이고 `OrderFact.symbol` 은 우리 canonical **`BTC/USDT`**(`_order_facts`)다. → **어떤 표본에서도 매칭이 성립하지 않는다. `inferred` 귀속 축이 구조적으로 죽어 있었다.**

직전 스프린트(exit-money-path) §0.5 가 `attributed_strategy_id NOT NULL 0` 을 관측했지만 **"0행 위에서 0"** 으로 해석했다. 그 해석과 이건 구분되는 진단이다 — **데이터가 있어도** 매칭이 안 된다. 생산부·축약부·비교부 3지점을 코드로 확인했고, 픽스처가 왜 이걸 가렸는지도 찾았다.

**★픽스처가 거짓말을 하고 있었다.** `test_closed_pnl_sweep.py::_snapshot` 의 기본 심볼이 `"BTC/USDT"` 였다 — 우리 canonical 표기다. 실제 Bybit closed-pnl 은 `BTCUSDT` 를 준다(DB 4행 전부 그렇다). 원장 쪽 피연산자를 우리 표기로 위장한 픽스처가 이 결함을 한 스프린트 내내 안 보이게 만들었다. 그래서 **C-red 의 첫 동작이 픽스처 정정**이었다.

**교훈** — 외부 시스템 픽스처의 기본값은 "우리가 다루기 편한 형태" 가 아니라 **그 시스템이 실제로 주는 형태**여야 한다. 편한 형태로 두면 경계 버그가 테스트를 통과한다.

### 왜 `normalize_symbol` 이 아니라 `to_bybit_raw_symbol` 인가

`normalize_symbol` 은 **raise** 한다. 낯선 Bybit 심볼 하나가 계정 루프 안에서 던지면 바깥 `except Exception` 에 삼켜져 `failed_provider` 로 오집계되고 **그 계정의 원장 적재 전체를 잃는다.** `to_bybit_raw_symbol` 은 절대 raise 하지 않고 원문에 idempotent 하다. 레포 선례도 같다(`websocket/position_fanout.py:72`).

---

## §3 사용자 결정 5건

| #   | 결정                               | 근거                                                                                                                                                     |
| --- | ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | 스코프 = BL-457 + 454 + 458 (+464) | BL-446 은 리스크 게이트 시맨틱 변경이라 회귀 표면이 넓고, 실측 여유가 임계 10% 대비 54,117배                                                             |
| D2  | 라벨 + 소계 · 사람이 읽는 2표면    | 게이트 수식 무변경(가산적) · 필터링은 fail-open 이라 기각                                                                                                |
| D3  | 과거 원장 4행 불변                 | 그 3행 UUID 는 계정 재등록 전 우리 주문이었을 개연성이 높은데 Order 이력이 사라져 증명 불가 → 재분류는 원장에 새 거짓을 쓰는 셈. 알림은 신규 행에만 발화 |
| D4  | 공용 도메인 프리미티브 타입        | 레포에 동일 선례 존재(`strict_decimal_input.py`) + Parse-don't-validate + 422 공짜 + 이후 어떤 ingress 도 타입만 받으면 자동 안전                        |
| D5  | 거부 + 전용 관측                   | TV 실문자열 미확인 → 추측 코드 대신 fail-closed. 웹훅 경로 실사용 0 · orders 0행이라 오늘 공짜                                                           |

### D4·D5 를 1차 출처로 조사한 것

사용자가 "업계 권장 · TV 는 어떻게 · 10년차 아키텍트라면" 을 물어 실제로 조사했다.

- **CCXT 자체 계약** — "항상 unified symbol 을 쓰고 거래소 market id 는 `markets_by_id` 로 되돌린다" → **경계 정규화 + 내부 단일 canonical**.
- **TV 문서** — `{{ticker}}` 는 거래소 원문, `{{exchange}}` 는 별도 변수, 지연 심볼은 `_DL`/`_DLY` 접미가 붙는다 → **TV 식별자는 장식을 단다**.
- **TV→브로커 브리지 업계** — 1순위 실패 모드가 정확히 이 포맷 불일치이고, 권고 해법은 **수신 ingress 에서 맞추는 것**.
- **Parse, don't validate** — 경계에서 한 번 파싱해 불가능한 상태를 타입으로 배제하고 이후 재검증하지 않는다.

★**확인 못 한 것** — TV 가 Bybit USDT 퍼프에서 `BTCUSDT` 를 주는지 `BTCUSDT.P` 를 주는지. 확인한 두 출처 모두 예시 payload 에 `BTCUSDT` 만 쓰고 `.P` 여부를 명시하지 않았다. **그래서 D5 가 "추측 코드 금지 + 관측"** 이다. 모르는 것을 코드로 단정하는 대신 로그가 답하게 했다.

### canonical `BTC/USDT` 는 선택이 아니라 강제였다

`_to_bybit_linear_symbol`(`providers.py:678-695`)이 `:USDT` 를 합성하는데 `:692` 가 `if "/" not in symbol: return symbol` 이다. 즉 **원문 `BTCUSDT` 는 linear 어댑터를 우회**해 조용히 잘못된 market 으로 라우팅된다. 지금 위험한 포맷은 canonical 이 아니라 원문 쪽이었다. 이 발견이 "정규화가 provider 를 깰까" 라는 make-or-break 리스크를 해소했다.

---

## §4 codex G0 — BLOCKING 0 · P1 4 · P2 1, 전건 코드 대조 후 판정

**[P2 수용 — codex 가 맞았다]** "Site 3 의 기존 context 5개" 전제가 틀렸다. 실제 **6키**(`scope` 포함)이고, 내가 인용한 real-DB 테스트는 6키 보존을 검증하지 않고 **두 값만** 단정한다. 내 플랜이 양쪽 다 틀렸다. → context 11키 전수 단정을 신규로 넣었다.

**[P1-1 수용]** 메서드 개명이 깨는 테스트 목록. 실제로 8곳(prod 1 + test 7)이었고 전수 갱신했다.

**[P1-2 수용]** pending 응답 정확-dict 단정이 깨진다. 실제로 깨졌고, **약화시키지 않고** 신규 4키를 명시적으로 적었다 — 응답 형태 동결이 제 역할을 한 것이다.

**[P1-3 수용]** `utils.ts` 가 `equity_curve` 의 `source` 를 버리므로 차트 색만 추가해도 전달되지 않는다. 확인했고 carry-forward 에 출처를 동반시켰다.

**[P1-4 절반 기각]** codex 가 내 _신규_ nullable 필드와 _기존_ non-null 필드를 섞었다. `totalRealizedPnl: number`·`latestValue: number` 는 기존 것이고 내가 바꾸지 않는다. 다만 경고의 실질(널을 `number` 자리에 넣거나 `0` 폴백으로 "모름" 을 "0" 으로 위장하지 말 것)은 유효하고, 설계가 이미 `number | null` + `== null` 렌더로 그걸 피하고 있었다.

---

## §5 설계 결정 — 되돌리기 전에 읽을 것

### 분기 8 (`unknown`) 을 만든 이유

UUID 모양 link id 인데 실재 확인이 안 된 행을 단순 fall-through 시키면 `createByUser` 와 만나 `external_manual` 이 된다. 그건 "사람이 거래소 UI 에서 Close 를 눌렀다" 는 단정이고 **사람은 UUID4 를 타이핑하지 않는다.** 운영자가 알림에서 읽는 문자열이라 유령 수동거래를 찾아 헤매게 만든다.

### 3번째 classification 값을 만들지 않은 이유

비용은 논거가 아니다 — `classification` 은 `String(24)` 이라 값 추가도 마이그레이션 0 이다(직접 확인). 진짜 이유는 ① `ours` 술어가 영구히 두 값으로 쪼개져 모든 미래 소비처가 둘 다 기억해야 한다(BL-453·BL-457 을 만든 결함 형태 그대로) ② `ix_exchange_exits_classification` 의 쿼리 소비자가 레포 전체에 0 이고 BL-438 ② 는 "현재 데이터로 정직하게 구현 불가" 로 기록돼 있어 그 값은 **읽히지 않은 채 존재**한다 ③ "우리 DB 가 행을 잃었다" 는 청산의 속성이 아니라 **우리 운영 사실**이라 Prometheus 카운터가 올바른 집이다.

**탈출구 명시** — `qb_exchange_exit_link_unverified_total` 이 프로덕션에서 오르면 그때 enum 값을 추가한다. n=0 에서 오늘 정하는 건 추측이다.

### `EquityPoint` 를 건드리지 않고 형제 타입을 만든 이유

`EquityPoint` 는 pine 쓰기 경로가 `LiveSignalState.equity_curve` JSONB 로 **영속**하는 구조다. 필수 키를 추가하면 스코프 밖 쓰기 경로가 타입 불일치가 된다. 출처는 읽기 시점의 가산적 파생이므로 `SessionEquityPoint` 로 분리했다.

### `source` 가 문자열 유니온이고 `bool` 이 아닌 이유

FE 에 이미 출하된 판별자(`orders-blotter.tsx` `realizedPnlSource`)가 정확히 이 유니온을 돌려준다. 그래서 FE 가 `ORDER_REALIZED_PNL_SOURCE_LABEL[p.source]` 로 **번역 계층 0** 이다. `bool` 이면 같은 사실의 두 번째 인코딩이 생겨 드리프트한다. 또 `bool` 은 세 번째 상태(손익 미도착)로 자랄 수 없다.

### Site 3 은 반환 타입을 바꾸고 Site 4 는 리포를 안 바꾼 이유

Site 4 는 라우터가 이미 ORM 행을 들고 있어 출처가 공짜로 파생된다 → **추가 왕복 0 · 시그니처 파손 0 · 가드레일 걸린 쿼리 형태 byte-identical.**

Site 3 은 `Decimal` 하나를 돌려주는 메서드를 남겨두면 "출처를 안 보고 합산" 이 계속 가능하고 그게 BL-458 이 지적한 결함 그 자체다. 타입을 바꿔 표현 불가하게 만들었다 — `SessionScope`/`from_live_session` 이 이 파일에서 이미 쓴 수와 같다. 포기한 것은 grep 연속성(구 이름이 dev-log·계약 문서에 있다 → 같은 PR 에서 갱신).

### ★병합 커브에는 포인트별 출처를 실을 수 없다

`mergeCumulativeCurves`(`aggregate.ts:33-45`)를 읽고 확인했다 — 시각 합집합을 훑으며 각 세션의 **마지막 누적값을 carry-forward** 해 더한다. 즉 병합 지점의 값은 N개 기여의 합이고 통상 N−1 개가 과거 거래에서 실려온 stale 값이다. 그걸 "t 시점 델타의 출처" 로 칠하면 **적극적으로 틀린다** — 그 돈 대부분은 다른 데서 왔다.

→ **포인트별 출처는 단일 세션 고도 전용, 포트폴리오 곡선은 집계 수준 라벨.** 와이어가 두 형태(포인트 `source` + 평면 소계)를 다 싣는 이유가 정확히 이 비대칭이다. 소계는 가산적으로 올바르게 병합된다.

### 집계 소계가 `number | null` 인 이유

채워진 세션 **전부**가 소계를 보고했을 때만 합산한다. 하나라도 빠지면 `null` — **부분 분할은 없는 것보다 나쁘다.** "확정 −100" 이 실제로는 세션 하나만의 확정일 수 있고, 그건 없는 신뢰를 주장하는 것이다. 렌더는 느슨한 `== null` 로 걸러 기존 픽스처(신규 키 `undefined`)가 자동으로 미렌더된다.

---

## §6 감수하는 부채

- **혼재 vintage 컬럼** — D3 대로 과거 4행 미재분류. 컷오버 = 이 PR 머지 시점. 오늘 노출은 문서뿐(컬럼 독자 0).
- **`inferred` 부활은 휴리스틱 승인이 아니다** — 함수 스스로 "검정력이 없다" 고 적고 있고, `attributed_strategy_id` 독자가 0 이라서만 안전하다. `qb_exchange_exit_attribution_total{confidence}` 는 BL-438 ② 승격 **전에** 실제 비율을 재기 위해 존재한다.
- **Site 4 는 `unrecorded_count` 를 안 센다** — `/state` 폴링마다 집계 쿼리가 하나 더 붙는 비용 대신 추가 왕복 0 을 택했고, 그 숫자는 Site 3 알림이 이미 전달한다. 패리티 폴백은 계약 문서 §4 에 적었다.
- **화면 dogfood 미실행** — `orders`/`sessions` 0행이라 seed 없이는 실화면 종단 확인이 불가하다. 실주문이 필요하면 사용자 요청이 선행돼야 한다. 대신 실DB 종단 테스트(Site 3·4)와 독립 오라클(2의 거듭제곱 유일 부분합)로 대체했다.

---

## §7 함정 기록

- **`send_rule_alert` 는 첫 인자를 위치 인자로 받는다.** `**kwargs` 만 받는 mock 을 쓰면 `TypeError` 가 나는데, 그게 `_alert_new_exchange_exits` 의 `try/except Exception` 에 삼켜져 **`alerted == 0` 으로만 보인다**(라벨은 정상). 기존 테스트처럼 `AsyncMock` 을 쓸 것.
- **`select(Order.id)` 는 mypy 에서 `call-overload`** — 레포 관례는 `# type: ignore[call-overload]`(`exchange_exit_repository.py:50` 선례).
- **`market_data` 재수출은 `__all__` 이 필요하다** — mypy `implicit_reexport=False` 라 평범한 import 로는 `attr-defined` 가 난다.
- **`Numeric(18,8)` 응답은 `-4.00000000`** — 테스트에서 문자열 동등 대신 `Decimal()` 로 비교할 것(같은 파일 선례 있음).
- **`.default()` 를 zod 에 쓰면 추론 출력 타입이 필수가 된다** → 기존 픽스처 전부 깨짐. `.optional()` + 폴백 헬퍼.
- 필수 필드를 FE 타입에 추가하면 기존 테스트 픽스처가 깨진다. 이번엔 **생산자 계약을 강하게 두는 쪽**을 택해 픽스처 2줄을 갱신했다.
