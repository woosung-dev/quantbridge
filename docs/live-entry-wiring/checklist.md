# live-entry-wiring — 라이브 자동매매가 실제로 진입을 낼 수 있게 (다음 세션용)

> 2026-07-26 작성. 선행 = PR [#484](https://github.com/woosung-dev/quantbridge/pull/484) (`feat/bl-474-webhook-ingress-parity`).
> 배경 전문 = [`dev-log/2026-07-26-bl474-webhook-ingress-parity.md`](../dev-log/2026-07-26-bl474-webhook-ingress-parity.md) 부록.
> **조사는 끝났다.** 이 문서는 발굴이 아니라 **결정 + 구현** 을 위한 것이다.

---

## 0. 한 줄 요약

**라이브 자동매매는 진입 주문을 낸 적이 없다.** 청산만 나가서 매번 `110017` 로 거부된다. 원인은 규명됐고 범위도 좁다.

---

## 1. 지금 상태

### 끝난 것 (#484)

- **BL-474** webhook ingress 패리티 — 실주문 dogfood 로 linear perp 라우팅 확인(주문 ID 가 숫자형→UUID 로 바뀜)
- **BL-475** risk% 모드 문구 정정 + `risk_percent` 배선
- **BL-480** 발산 표면화 — 화면이 `local_only` 를 숨기지 않는다
- 출처 라벨(#481)·SessionScope(#477) **실화면 검증 완료** — 독립 raw-HMAC 오라클 3중 일치

### 열려 있는 것

| BL         | 우선순위 | 내용                                                |
| ---------- | -------- | --------------------------------------------------- |
| **BL-478** | **P1**   | stop-entry 진입이 거래소에 발주되지 않는다          |
| **BL-479** | **P1**   | 라이브 사이징 미배선 — `compute_qty()` 항상 `1.0`   |
| BL-476     | P2       | webhook 핸들러 동기 CCXT 왕복 3회 (**+4.8초 실측**) |
| BL-477     | P3       | API 키 2개가 같은 서브계정 → 청산 원장 2행          |

---

## 2. BL-478 — 먼저 **결정**이 필요하다

### 규명된 사실 (재조사 불필요)

```
strategy.entry(..., stop=)  →  PendingOrder 파킹 + return None    strategy_state.py:598-608
                            →  체결 시 event_action="fill"        strategy_state.py:752-758
run_live                    →  fill 은 dispatch 제외              event_loop.py:287-288
독스트링 전제                →  "broker 가 자체 fill 알림 처리"      event_loop.py:253-255
실측                        →  live_signal.py 에 trigger_price 참조 0건
```

**broker 에 그 stop 주문을 올린 적이 없다.** 그래서 진입 이벤트가 0건이고, 반전 시 발행되는 `close` 만 나간다.

**영향 범위 = `stop=` 진입 전략 한정.** 시장가 진입은 `strategy_state.py:634-642` 가 `event_action="entry"` 를 정상 발행하므로 무관하다. 다만 시드 `s1_pbr` 은 진입 2개가 전부 `stop=` 이라 100% 이 경로다.

### 선택지 — ★사용자 결정 필요

| 안                             | 내용                                                                                                                                                                | 장점                                                             | 대가                                                                                                                                                                |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **(a)** conditional order 등재 | `PendingOrder` 를 거래소 조건부 주문으로. `OrderRequest.trigger_price`/`trigger_direction` 이 **이미 있고** `_merge_exit_params`(`providers.py:438-465`)가 처리한다 | TV 시맨틱 그대로. 체결가 괴리 0                                  | 가장 큼. 조건부 주문 수명주기(취소·갱신·재발행)를 새로 다뤄야 하고, pine 이 매 tick `PendingOrder` 를 재발행하는 것과 거래소 주문의 idempotency 를 맞춰야 한다      |
| **(b)** 시장가 근사            | `fill` 도 dispatch 대상에 포함                                                                                                                                      | 작다                                                             | **체결가가 달라진다.** stop 가격이 아니라 다음 시장가에 들어가므로 TV parity 훼손. 백테스트 숫자와 라이브가 어긋나기 시작한다 — 지난 3스프린트가 쌓은 신뢰를 깎는다 |
| **(c)** 세션 시작 차단         | stop-entry 전략의 라이브 세션 시작을 거부하고 이유를 화면에 표시                                                                                                    | **가장 정직하고 가장 작다.** 지금은 조용히 안 되면서 되는 척한다 | 기능이 늘지 않는다. s1_pbr 로는 라이브를 못 돌린다                                                                                                                  |

**★권고 = (c) 먼저, 그다음 (a).** (c)는 거짓말을 즉시 멈추고 (a)의 설계 시간을 벌어준다. (b)는 권하지 않는다 — 백테스트↔라이브 일치가 이 프로젝트의 핵심 자산인데 그걸 조용히 깬다.

### (c) 를 고른 경우 체크리스트

- [ ] 차단 지점 — `LiveSignalSessionService` 세션 시작(`live_session_service.py:80` 근처, 이미 settings 존재를 검사하는 자리)
- [ ] 판정 방법 — pine 소스에서 `strategy.entry(..., stop=)` 사용 여부. `ast_extractor.py` 가 이미 `strategy(...)` kwarg 를 파싱하므로 **entry 호출의 `stop` kwarg 검출**을 같은 자리에 붙일 수 있는지 먼저 확인
- [ ] ★**판별력 증명** — `stop=` 있는 전략은 차단되고 **없는 전략은 통과**하는 것을 양쪽 다 단정. 한쪽만 보면 전부 차단하는 가드를 정상으로 착각한다
- [ ] 화면 문구 — "이 전략은 조건부 진입(stop)을 쓰는데 라이브 발주가 아직 지원되지 않습니다" 수준으로 **왜 안 되는지**까지
- [ ] 기존 활성 세션(`0e15c3c0`)은 어떻게 할지 — 자동 종료 vs 경고만. 실행 중인 것을 끊는 건 별도 결정

---

## 3. BL-479 — 사이징. **BL-478 과 같이 가야 한다**

진입이 열리는 순간 수량이 곧바로 문제가 된다(1 BTC ≈ $64,000 명목).

### 규명된 사실

`run_live`(`event_loop.py:270-272`)가 `run_historical` 을 **사이징 인자 없이** 호출한다 → `configure_sizing` 미호출 → `compute_qty()` 가 fallback `1.0`(`strategy_state.py:311-317`).

`position_size_pct` 는 라이브에서 **아무 데서도 읽히지 않는다.** 사이징 계산의 유일한 자리는 `compat.parse_and_run_v2`(`compat.py:99-111`)이고 프로덕션 호출자는 `v2_adapter.py:96`(백테스트) 하나뿐이다. `live_session_service.py:80` 은 필드 **존재**만 요구하고 값은 안 본다.

★**Pine 선언도 무시된다** — `strategy(default_qty_type=..., default_qty_value=...)` 를 선언한 스크립트조차 라이브에선 `1.0` 이다. 추출 경로 전체가 `if initial_capital is not None` 게이트 뒤에 있기 때문. 즉 사이징 우선순위 사슬(Pine > form > Live)이 라이브에선 통째로 죽어 있다.

### 체크리스트

- [ ] `run_live` 에 `initial_capital` + 사이징 파라미터를 전달 (또는 `parse_and_run_v2` 경유로 우선순위 사슬을 복원)
- [ ] ★**equity 기준선을 어디서 가져올지 결정** — 이게 유일한 미해결 설계점이다. `position_size_pct` 는 evaluate 단계에서 이미 손에 있다(`live_signal.py:396`). 없는 건 자본 값
  - 후보 1: 매 tick 거래소 잔고 조회 — 정확하지만 **BL-476 과 같은 지연 문제**를 evaluate 경로에 추가한다
  - 후보 2: 세션 시작 시 1회 스냅샷 후 캐시 — 싸지만 입출금·손익에 따라 표류
  - 후보 3: kill-switch 가 이미 쓰는 balance provider 재사용(`live_signal.py:880-885`) — 배선이 가장 짧다. 그 경로의 갱신 주기를 먼저 확인할 것
- [ ] 회귀 — `position_size_pct: 0.01` + 잔고 X → 기대 수량이 나오는지. **수정 전 `1.0` 이 나오는 것을 RED 로 확인**
- [ ] Pine `default_qty_type` 선언이 라이브에서도 우선하는지 (백테스트와 같은 우선순위)

---

## 4. BL-476 — 결정만 하면 되는 것

`leverage` 가 채워지면서 notional 가드가 webhook 경로에서 처음 도달 가능해진 대가.

```
fetch_mark_price 1663ms · fetch_min_notional 1549ms · fetch_balance_usdt 1600ms  →  4812ms
```

★**게이트는 provider 를 stub 으로 갈아끼우므로 영원히 0ms 다.** 이 회귀는 프로덕션에서만 보인다.

- [ ] 결정 — 가드를 Celery 경계 뒤로 옮길지. `tasks/trading.py:_execute_with_session` 이 발주 직전에 평가하고 실패 시 `rejected` 로 전이하면 되고, 그 경로엔 이미 `except ProviderError` graceful 전이가 있다
- [ ] 다만 **거부 시점이 응답 뒤로 밀리는 계약 변경**이다 — 201 을 준 뒤 rejected 가 되는 걸 받아들일지가 결정 포인트
- [ ] TradingView 재시도 정책과 함께 볼 것 — 멱등키가 client-generated 라 재시도마다 새 값이면 중복 주문이 될 수 있다

---

## 5. BL-477 — 사용자 판단이면 끝

읽기 전용 계정 `0277c150` 을 삭제하면 **자연 소멸**한다. 두려면 (b) 등록 시 동일 서브계정 중복 감지 또는 (c) 귀속을 `(exchange, exchange_order_id)` 기준으로 재조회.

- [ ] `0277c150` 삭제 여부 결정

---

## 6. 환경 (이전 세션에서 이어짐)

| 항목        | 값                                                                                                        |
| ----------- | --------------------------------------------------------------------------------------------------------- |
| 스택        | db **5433** · redis **6380** · BE **8100** · FE **3100**                                                  |
| compose     | 항상 `-f docker-compose.yml -f docker-compose.isolated.yml` + **`--no-deps`**                             |
| 거래소 계정 | `19a8166a` **bybit demo** — 거래 가능 · `0277c150` **읽기 전용**(주문 불가)                               |
| 라이브 세션 | `0e15c3c0` PbR / BTC/USDT / 1m / `19a8166a` · **활성** — 지금도 110017 을 쌓고 있다                       |
| 시드        | `make seed` (멱등)                                                                                        |
| BE 기동     | `make be-isolated` (호스트 uvicorn --reload). 워커는 `./backend/src` bind-mount + watchfiles 라 자동 반영 |

---

## 7. 이번 세션에서 실제로 통한 기법 (재사용)

- ★**외부 증거를 거래소에서 받아라** — spot/linear 판별은 우리 로그가 아니라 **주문 ID 형식**이 답했다(숫자형 vs UUID).
- ★**"추정" 값은 주입해서 검증한다** — 확정값과 우연히 같아질 수 없는 값(`-9.99`)을 넣으면 교체 여부가 한눈에 보인다.
- ★**확정까지 14초** — `_enqueue_closed_pnl_refresh` countdown=5 가 beat 스윕(300s)보다 먼저 돈다. 혼재 상태를 보려면 서둘러야 한다.
- **독립 오라클** = ccxt·`providers.py` 미경유 raw HMAC. `asyncpg` 로 암호화 키 읽고 `MultiFernet` 복호화 → `X-BAPI-SIGN` 손서명.
- **브라우저** = Chrome 확장 미연결 → Playwright MCP + `frontend/e2e/.auth/storageState.json`. 신선 JWT = `await window.Clerk.session.getToken()`.
- ★★**첫 실행에 다 통과하면 의심하라** — FE 18/18 통과였는데 `git stash push -- <프로덕션 파일>` 로 되돌리니 신규 7건이 전부 RED 였다. 통과만 보고 넘어갔으면 판별력 0인 가드를 100%로 착각했다.
- ★**가드는 "무엇을 안 잡는지" 도 단정하라** — BL-480 에서 `match`/평가-전 `unknown` 이 조용히 남는 것을 함께 고정했다. 안 그러면 세션 시작마다 경고가 떠서 진짜 발산이 노이즈에 묻힌다.

---

## 8. 함정

- **`bool("false") is True`** — TV alert 은 문자열 불리언을 보낸다. 명시 화이트리스트로 방어할 것.
- **leverage 가 채워지면 안 돌던 가드가 켜진다** — 테스트는 서비스가 아니라 **provider 를 오버라이드**해야 TRD-4 소유권 게이트가 실 repo 로 유지된다.
- **RUF003** — 주석의 `×`(MULTIPLICATION SIGN)·`−`(MINUS SIGN)이 ruff 를 깬다. 네 번째 재발 대기 중.
- **디자인 캐논 em-dash 래칫** — 새 노출 산문의 `—` 는 `design-canon-source.test.ts` 가 잡는다. 허용치를 올리지 말고 문구에서 뺄 것.
- **BE pytest 는 3-env 통째 export 필수** — `set -a; source .env.local; set +a`.
- **`| tail` 파이프는 exit code 를 가린다** · **`pnpm test --run` 은 exit 0 으로 조용히 죽는다**(`pnpm test` 가 정답).
- **`ruff format`/`prettier`/`format:check` 는 이 레포의 통과 가능 게이트가 아니다.**
- **`| tail -2` 로 감싼 백그라운드 pytest 는 끝날 때까지 출력 파일이 비어 있다** — 진행 중인지 죽은 건지 구분하려면 `pgrep -f pytest` 로 확인할 것.

---

## 9. 다음 세션 첫 step

1. `docs/status.md` 에서 이 스프린트 상태 확인
2. **BL-478 선택지 (a)/(b)/(c) 를 사용자에게 물어보고 시작** — 이게 blocking 결정이다
3. (c) 라면 BL-479 와 묶어서 한 스프린트, (a) 라면 BL-478 단독으로 한 스프린트
