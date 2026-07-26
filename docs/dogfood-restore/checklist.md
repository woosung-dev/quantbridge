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

### 체크리스트 — ✅ 완료 (2026-07-26, `feat/bl-474-webhook-ingress-parity`)

- [x] 페이로드에 Live Settings 가 실리는지 **코드로 특정** — ★**끊긴 곳은 다이얼로그가 아니라 webhook ingress 였다.** `router.py:138-147` 이 `OrderRequest` 를 7개 필드로만 조립하고 `parse_tv_payload`(`webhook.py:118-125`)가 6개 키만 읽어 **한 자리에서 3건이 동시에 버려졌다** — leverage/margin_mode(해결 자체 없음) + `reduce_only` + TP/SL(**프론트는 보내고 있었다**, `test-order-webhook.ts:62-70`).
- [x] ★**leverage 만 고쳤으면 A 는 안 열렸다** — 청산 확정 경로가 `reduce_only` 를 요구한다(`tasks/trading.py:1342` 조기 반환 + 스윕 `list_unsynced_reduce_only`). 그 플래그 없이는 다이얼로그 청산이 영원히 `realized_pnl_synced_at` 을 못 받는다.
- [x] `settings` 조회 — `StrategyListItem` 에 이미 실려 있어 **추가 페치 0**. 다만 해결은 FE 가 아니라 서버가 한다(`WebhookService.resolve_trading_params`). payload 로 받으면 secret 보유자가 운영자 리스크 설정을 우회한다.
- [x] settings 미설정 = **422 fail-closed**(사용자 확정). spot 진입은 닫을 수단이 없다 — 모든 청산이 linear reduce-only 라 `110017` 로 거부된다(§B 가 관측한 그 에러).
- [x] 회귀 테스트 — `dispatch_snapshot["has_leverage"] is True` 포함 **22건 전부 수정 전 RED 확인**(parse 17 · router 4 · e2e 1). FE 신규 7건은 `git stash` 로 프로덕션 변경만 되돌려 RED 재현.
- [x] 최소안(표시만) 대신 **전체 패리티** 채택 — 표시만으로는 오검증만 막고 A 가 안 열린다. 라우팅 배지는 그 위에 함께 넣었다.
- [x] 부수 — secret 캐시 안내문에 **"전략 편집 → §05 Webhook 카드 → Secret 회전"** 명시.
- [x] **신규 발견 [BL-475]** — risk% 사이징 모드는 한 번도 작동한 적 없었다(`quantity` 누락으로 401, 게다가 백엔드는 상한만 검사하고 수량을 계산하지 않음). UI 문구를 실제 동작에 맞춰 정정 + `risk_percent` 배선.

**게이트:** BE **3029**(+24) · FE **1136**(+6) · ruff·mypy·tsc·lint 0 · 마이그레이션 **0**.

### A 가 열리면 바로 할 것 (출처 라벨 검증) — ✅ 완료

- [x] perp 진입 체결 → 청산. ★**결정적 증거는 주문 ID 형식이었다** — 수정 전 `2267433208968908032`(숫자형=spot) → 수정 후 `0a245783-f809-…`(UUID=linear). 우리 코드가 아니라 **거래소가** 시장 유형이 바뀌었다고 말해준다.
- [x] 스윕 전/후 둘 다 관측. ★**확정까지 5분이 아니라 14초였다** — `_enqueue_closed_pnl_refresh` countdown=5 가 주문별로 먼저 돈다. beat 스윕을 기다릴 필요가 없었고, 오히려 혼재 상태를 잡으려면 **서둘러야** 했다.
- [x] 세션 상세 칩 — 청산에 추정 `-9.99` 를 주입해(확정값과 우연히 같아질 수 없게) **`거래소 확정 -0.05935440` / `추정 -9.99000000`** 동시 표시 포착. 8초 뒤 확정 `-0.12772399` = 두 청산의 정확한 합. `confirmed + estimated == total` 화면에서 성립.
- [x] 대시보드 §01 KPI foot — _"이 중 거래소 확정 -0.13 · 추정 0.00 입니다."_ 렌더. 지적대로 활성 세션 1개라 조건이 느슨한 건 사실이므로, 판별력은 위 칩 대조가 담당.
- [x] 세션 에쿼티 차트 — **마운트됨**(events 5행 존재). 단 마운트 게이트의 실제 위치는 `live-session-detail.tsx:128-136`(`events.items.length === 0` 분기)이고 `:63-68` 은 `useMemo` 단락이다.
- [x] 독립 오라클 — ccxt·`providers.py` 미경유 raw HMAC 으로 `/v5/position/closed-pnl` 직격. `orders.realized_pnl` · `exchange_exits.closed_pnl` · 거래소 원문 **3중 일치**.
- [x] 신규 발견 **[BL-476]** 지연 +4.8초(실측) · **[BL-477]** 청산 원장 유령 `unknown`(선재, 금액은 안전).

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
- ★~~**레버리지 1 은 위험만 줄이는 게 아니라 시장 유형을 바꾼다**(`has_leverage=False` → spot)~~ — **틀렸다. 2026-07-26 BL-474 작업 중 코드로 반증.** `order_service.py:194` = `req.leverage is not None and req.leverage > 0`, `tasks/trading.py:135` = `return lev > 0` → **레버리지 1 이면 `has_leverage=True` → linear perp**. 위 §A 표(`leverage=1 … → linear perp`)가 처음부터 맞았고 이 함정 문구가 같은 문서 안에서 그것과 모순이었다. 진짜 원인은 값이 1이어서가 아니라 **다이얼로그가 레버리지를 아예 안 보내서**다. ★교훈은 그대로 살아 있다 — 다만 내용이 다르다: **같은 문서 안 두 진술이 어긋나면 코드가 심판이다.** 관측(`spot 으로 나갔다`)에서 원인(`레버리지 1 탓`)을 성급히 일반화한 사례.
- ★**가드를 만들면 판별력을 증명하라.** 첫 소스 스캔 규칙이 5곳 중 2곳만 잡았다. 통과만 보고 넘어갔으면 40% 가드를 100% 로 착각했다.
- ★**테스트 픽스처를 "정리" 하면 성질이 죽는다.** 실측 13표본을 6으로 줄이자 큰 음수 하나가 평균을 지배해 결함이 재현되지 않았다.
- ★**`| tail` 파이프는 exit code 를 가린다** — `pnpm e2e:authed | tail` 의 exit 0 은 tail 의 것이다.
- **BE pytest 는 3-env 통째 export 필수** — `set -a; source .env.local; set +a`.
- **`pnpm test --run`** 은 `Unknown option` 으로 죽으면서 exit 0. `pnpm test` 가 정답.
- **db/redis 컨테이너가 삭제된 스크래치패드 override 로 생성돼 있다** — plain `docker compose up` 이 포트를 5432/6379 로 되돌린다.
- **`ruff format`/`prettier` 는 이 레포의 통과 가능 게이트가 아니다**(`format:check` 는 main 에서 선재 356 red).
