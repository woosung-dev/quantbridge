# dogfood-restore — 잔여 작업 체크리스트 (다음 세션용)

> 2026-07-26 작성. 브랜치 `stage/dogfood-restore` · PR [#482](https://github.com/woosung-dev/quantbridge/pull/482).
> **이 스프린트는 여기서 닫는다.** 아래 A·B 는 다음 세션 몫이고, 사용자 확정 사항이다.
> 배경 전문 = [`dev-log/2026-07-26-dogfood-restore.md`](../dev-log/2026-07-26-dogfood-restore.md).

---

## 0. 지금 상태 (다음 세션이 이어받는 지점)

### 끝난 것

- `make seed` — 빈 DB → 전 화면 사용 가능. 전략 3 / 백테스트 6 / 거래 3,194 / OHLCV 9,337 / optimizer 1. **재실행 멱등.**
- 결함 수정 5건 — 샤프 raw 렌더 5곳(BL-465 계열 D1) · 전체 원장 청산 사유 열(D2) · 에러 문구(D3) · 음수 자본 위험조정수익 가드(**BL-465**) · optimizer-heavy OHLCV env(**BL-467**) · WS auth `expires` 창(**BL-473**).
- 게이트 — BE **3005** / FE **1130** / canon **32** / **e2e:authed 65-0** / build ok / 마이그레이션 **0**.

### 안 끝난 것 — 이게 A·B 의 이유

**#481 출처 라벨(거래소 확정/추정)과 #477 SessionScope 는 아직 화면에서 못 봤다.**

필요 조건 — linear perp **진입 체결** → **청산** → `realized_pnl` 생성 → 스윕이 `realized_pnl_synced_at` 채움. 이래야 확정/추정이 **섞여서** 칩 두 개가 서로 다른 값을 읽는다. 한쪽만 있으면 검증력이 0 이다.

★**시드로 만들면 안 된다.** 그게 이 스프린트가 없애려던 것이다.

---

## A. BL-474 — 테스트 주문 다이얼로그가 라이브와 다른 시장으로 나간다

> **먼저 할 것.** 이걸 고치면 perp 진입→청산을 **결정적으로** 만들 수 있어서 B 없이도 출처 라벨 검증이 열린다.

### 실측된 사실

라우팅은 `(exchange, mode, has_leverage)` 튜플이다(`backend/src/trading/registry.py:35-39`) — `False` → `BybitDemoProvider`(**Spot**), `True` → `BybitFuturesProvider`(**Linear Perp**).

```
라이브 신호 주문      leverage=1  margin_mode=isolated  has_leverage=true   → linear perp
테스트 주문 다이얼로그  leverage=NULL  margin_mode=NULL  has_leverage=false  → spot
```

우리 주문 `2267433208968908032` 는 Bybit **spot** 히스토리에만 있다(숫자형 ID = spot, linear 는 UUID). 청산 원장(`/v5/position/closed-pnl`)·포지션 코크핏·`exchange_exits` 는 **전부 linear 만** 본다 → 다이얼로그로 낸 체결은 `realized_pnl_synced_at` 을 **영원히 못 받는다.**

### 체크리스트

- [ ] `frontend/src/features/trading/components/test-order-dialog.tsx` 가 보내는 페이로드에 전략 Live Settings(`leverage`/`margin_mode`)가 실리는지 확인. 안 실린다면 어디서 끊기는지 — 다이얼로그인지 `webhook.py` 파싱인지 **코드로 특정**할 것.
- [ ] 실으려면 다이얼로그가 선택한 전략의 settings 를 조회해야 한다. `GET /strategies/{id}` 응답에 `settings` 가 있는지 확인(있다면 추가 페치 0).
- [ ] **최소안 대안** — 페이로드를 안 바꾸고 다이얼로그에 **"이 주문은 spot 으로 나갑니다"** 를 표시만 해도 조용한 오검증은 막힌다. 어느 쪽이든 사용자 확인 후.
- [ ] 회귀 테스트 — dispatch snapshot 의 `has_leverage` 를 단정. **수정 전 코드에 RED 인지 반드시 확인**(이번 스프린트에서 소스 스캔 가드가 5곳 중 2곳만 잡은 전례).
- [ ] 부수 — 시더로 만든 전략은 평문 webhook secret 이 브라우저에 없어 다이얼로그가 "캐시 없음" 으로 막힌다. **Secret 회전 1회 선행 필요**(`/strategies/{id}/edit` → §05 Webhook 카드 → "Secret 회전" → 확정). 안내문이 "Strategy 페이지에서 Rotate" 라고만 해서 카드까지 스크롤해야 한다는 걸 알기 어렵다.

### A 가 열리면 바로 할 것 (출처 라벨 검증)

- [ ] perp 진입 체결 → **청산**까지. `realized_pnl` 이 생기는지 psql 확인.
- [ ] 스윕(`trading.sweep_closed_pnl`, beat 5분) 전/후를 **둘 다** 관측 — 전에는 `realized_pnl_synced_at IS NULL`(추정), 후에는 값 있음(확정). **섞인 상태를 만들려면 청산 2건을 시차를 두고** 내는 게 확실하다.
- [ ] 세션 상세 칩 — `거래소 확정 <금액>` / `추정 <금액>` 두 개가 **서로 다른 값**인지. 같으면 검증력 0.
- [ ] 대시보드 §01 KPI foot — `splitComplete` 는 **모든** 활성 세션이 두 키를 보고해야 렌더된다(`hooks.ts:288-289`). 활성 세션이 1개뿐이면 조건이 느슨하니 주의.
- [ ] ★**세션 에쿼티 차트는 `live_signal_events` 행이 없으면 아예 마운트되지 않는다**(`live-session-detail.tsx:63-68`). orders 만 있으면 빈 화면이고, 그걸 "차트 버그" 로 오진하기 쉽다.
- [ ] 독립 오라클 — raw HMAC `GET /v5/position/closed-pnl` 값과 우리 `realized_pnl` 대조. 레시피는 dev-log 의 §S4 참조.
- [ ] `docs/money-path-finish/operating-contract.md` §4 대조 — "알 수 없는 것" 으로 적힌 걸 화면이 아는 척하면 그게 버그다.

---

## B. pine_v2 시뮬 상태 ↔ 거래소 실제 포지션 발산

> A 보다 깊고, 진짜 문제일 수 있다. **단정하지 말고 측정부터.**

### 관측된 현상

라이브 세션이 **청산(reduce-only) 신호**를 냈는데 거래소에 linear 포지션이 없었다.

```
order 857864e6  side=sell  qty=1.0  leverage=2  margin_mode=isolated
err: retCode 110017 "current position is zero, cannot fix reduce-only order qty"
```

pine_v2 는 포지션이 있다고 보는데 거래소엔 없다. 앞선 주문들이 spot 으로 갔거나(A) 읽기 전용 키로 거부돼서다.

### 체크리스트

- [ ] **먼저 재현 조건을 특정**하라 — 발주 실패 후 pine_v2 상태가 롤백되는가? 아니면 신호 생성과 발주 결과가 분리돼 있어 실패해도 상태가 전진하는가? `src/tasks/live_signal.py` + `LiveSignalState` 를 읽고 **코드로** 답할 것.
- [ ] 이게 **설계된 동작인지** 확인 — outbox 패턴상 신호와 발주는 분리돼 있고, 실패한 발주를 상태에 되먹이지 않는 게 의도일 수 있다. 그렇다면 결함이 아니라 **재동기화 수단 부재**가 결함이다.
- [ ] 기존 재동기화 경로가 있는지 — `reconciler` / `ws_reconcile` / `PositionService` 의 verdict 6종이 이 발산을 이미 표면화하는지 확인. 표면화한다면 화면에서 보이는지.
- [ ] ★**수량 1.0 도 같이 볼 것.** `compute_qty` 가 사이징 미선언 전략에 `1.0` 을 돌려준다(`strategy_state.py:317`) → 1 BTC ≈ $64,000 명목. 전략 settings 의 `position_size_pct: 0.01` 이 **라이브 발주 수량에 반영되지 않는 것으로 보인다**. 반영 경로가 있는지, 없다면 그게 별개 결함인지 판정.
- [ ] 판정 결과를 BL 로 등재. 이미 있는 [BL-466](../REFACTORING-BACKLOG.md#bl-466)(L=1 무제한 음수 자본)과 뿌리가 같은지 확인.

---

## 1. 환경 — 다음 세션이 알아야 할 것

| 항목          | 값                                                                                                                                                  |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| 스택          | db **5433** · redis **6380** · BE **8100** · FE **3100**                                                                                            |
| compose       | 항상 `-f docker-compose.yml -f docker-compose.isolated.yml` + **`--no-deps`**                                                                       |
| 거래소 계정   | `19a8166a` **bybit demo** — `readOnly:0`, **거래 가능**, 2026-10-26 만료<br>`0277c150` **bybit demo- aaa** — `readOnly:1`, **읽기 전용**(주문 불가) |
| 라이브 세션   | `0e15c3c0` PbR / BTC/USDT / 1m / `19a8166a` 계정 · **활성**                                                                                         |
| 전략 settings | PbR = leverage **2** · isolated · position_size_pct 0.01                                                                                            |
| 시드          | `make seed` (멱등) · `make seed ONLY=daily` 로 부분 실행                                                                                            |

### 정리하면 좋을 것

- [ ] 읽기 전용 계정 `0277c150` 삭제 여부 — 사용자 판단. 두면 ws-stream 이 계속 붙긴 하나 주문은 못 낸다.
- [ ] spot 에 남은 0.001 BTC(다이얼로그 실험 잔재) — 데모라 무해하지만 인지할 것.

---

## 2. 함정 (이번 세션에서 실제로 당한 것)

- ★★**우리 에러 메시지를 거래소의 진단으로 믿지 마라.** `ws_stream_auth_failed … Check API key validity, IP whitelist, system clock` 은 **우리가 쓴 문구**다. 그걸 믿고 "키 만료" 로 진단해 사용자에게 불필요한 재등록을 시켰다. 실제 원인은 우리 `expires` 창이었다. **외부 오라클(raw HMAC)을 먼저 쳐라.**
- ★**레버리지 1 은 위험만 줄이는 게 아니라 시장 유형을 바꾼다**(`has_leverage=False` → spot). "최소 노출" 이라고 1 을 넣었다가 spot 으로 나갔다.
- ★**가드를 만들면 판별력을 증명하라.** 첫 소스 스캔 규칙이 5곳 중 2곳만 잡았다. 통과만 보고 넘어갔으면 40% 가드를 100% 로 착각했다.
- ★**테스트 픽스처를 "정리" 하면 성질이 죽는다.** 실측 13표본을 6으로 줄이자 큰 음수 하나가 평균을 지배해 결함이 재현되지 않았다.
- ★**`| tail` 파이프는 exit code 를 가린다** — `pnpm e2e:authed | tail` 의 exit 0 은 tail 의 것이다.
- **BE pytest 는 3-env 통째 export 필수** — `set -a; source .env.local; set +a`.
- **`pnpm test --run`** 은 `Unknown option` 으로 죽으면서 exit 0. `pnpm test` 가 정답.
- **db/redis 컨테이너가 삭제된 스크래치패드 override 로 생성돼 있다** — plain `docker compose up` 이 포트를 5432/6379 로 되돌린다.
- **`ruff format`/`prettier` 는 이 레포의 통과 가능 게이트가 아니다**(`format:check` 는 main 에서 선재 356 red).
