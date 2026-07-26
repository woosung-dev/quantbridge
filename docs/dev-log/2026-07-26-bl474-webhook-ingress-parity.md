# 2026-07-26 — BL-474 webhook ingress 패리티 (dogfood-restore 체크리스트 A)

> 브랜치 `feat/bl-474-webhook-ingress-parity` · main `a716ef3` 베이스.
> 출발점 = [`docs/dogfood-restore/checklist.md`](../dogfood-restore/checklist.md) §A.

---

## 왜 했나

#477(SessionScope)·#481(출처 라벨)이 아직 **화면에서 확인되지 않았다.** 확인하려면 linear perp 진입 → 청산 → `realized_pnl` 생성 → 스윕이 `realized_pnl_synced_at` 을 채우는 일이 실제로 일어나야 하고, 그래야 "거래소 확정 / 추정" 두 칩이 서로 다른 값을 읽는다. 시드로 만들면 안 된다 — 그게 직전 스프린트가 없애려던 것이다.

그 경로를 테스트 주문 도구가 막고 있었다. 그 도구로 낸 주문은 Bybit **spot** 으로 나가는데 청산 원장·포지션 코크핏·`exchange_exits` 는 **전부 linear 전용**이다.

---

## ★진단이 한 겹 더 깊었다 — 다이얼로그가 아니라 webhook ingress

BL-474 의 "권장 접근" 은 _"다이얼로그가 전략 Live Settings 를 실어 보내게 한다"_ 였다. **잘못된 층이었다.**

`router.py:138-147` 이 `OrderRequest` 를 7개 필드로만 조립하고 `parse_tv_payload`(`webhook.py:118-125`)가 6개 키만 읽어, **한 자리에서 세 가지가 동시에 버려지고 있었다.**

| 필드                        | 실제 상태                                                            |
| --------------------------- | -------------------------------------------------------------------- |
| `leverage` / `margin_mode`  | 해결 자체를 안 함 → `has_leverage=false` → `BybitDemoProvider`(spot) |
| `reduce_only`               | 프론트가 **보내는데**(`test-order-webhook.ts:68-70`) 파서가 안 읽음  |
| `take_profit` / `stop_loss` | 프론트가 **보내는데**(`:62-67`) 파서가 안 읽음                       |

`OrderRequest`(`schemas.py:51-83`)·`order_service.py:359-368`·`tasks/trading.py:377,380-381`·`providers.py:441-442` 는 전부 이미 이 필드들을 처리한다. 끊긴 고리는 webhook 파싱+라우터 배선 **단 한 군데**였다.

기원도 명시적으로 남아 있었다 — `test_e2e_webhook_to_futures_order.py:5-6` 독스트링이 _"Webhook TV payload parser 확장은 Sprint 7b로 분리되므로…"_ 라고 적어두고 그 뒤 한 번도 하지 않았다.

## ★leverage 만 고쳤으면 A 는 여전히 안 열렸다

청산 확정 경로 전체가 `reduce_only` 를 요구한다.

```
tasks/trading.py:1342   if not order.reduce_only: return {"skipped": "not_reduce_only"}
tasks/trading.py:1355   if account.exchange != bybit or order.leverage is None: skipped_unsupported
order_repository.py:294 list_unsynced_reduce_only → WHERE reduce_only IS TRUE
```

즉 leverage 만 채웠다면 주문은 linear 로 나가지만 그 청산은 **영원히 `realized_pnl_synced_at` 을 못 받아** 손익이 "추정" 으로 굳는다. 검증하려던 그 라벨이 한쪽으로만 고정되니 판별력 0이다.

## ★★체크리스트 자신의 함정 문구가 틀렸다

`checklist.md:108` — _"레버리지 1 은 위험만 줄이는 게 아니라 시장 유형을 바꾼다(`has_leverage=False` → spot)"_.

**틀렸다.** 그리고 **같은 문서 §A 표(`:36`)가 정반대**를 말하고 있었다(`leverage=1 … has_leverage=true → linear perp`).

```
order_service.py:194   "has_leverage": req.leverage is not None and req.leverage > 0
tasks/trading.py:135   return lev > 0
```

1 > 0 이므로 **레버리지 1이면 linear perp** 다. 진짜 원인은 값이 1이어서가 아니라 **다이얼로그가 레버리지를 아예 안 보내서**다. 관측(`spot 으로 나갔다`)에서 원인(`레버리지 1 탓`)을 성급히 일반화한 사례. 문서에 취소선 + 정정으로 남겼다 — 잘못된 교훈은 지우는 것보다 왜 틀렸는지 남기는 게 낫다.

**교훈 형태는 살아 있되 내용이 다르다: 같은 문서 안 두 진술이 어긋나면 코드가 심판이다.**

---

## 설계 결정

### leverage 해결 위치 = `WebhookService`

`OrderService.execute` 안이 아니다. 4개 호출자의 공유 길목이고 그중 둘(`live_signal.py:852-866`, `close_service.py:47-58`)이 **이미** settings 를 해결하며, `close_service.py:86-90` 은 의도적으로 **실 포지션의 leverage 를 settings 보다 우선**한다. 여기서 자동 채우면 경쟁하는 두 번째 해결 지점이 생기고 `flatten=True` 청산 의미가 조용히 바뀐다.

`StrategySessionsPort` 확장도 아니다 — 어댑터(`dependencies.py:141-163`)가 메서드마다 `select(Strategy)` 전체 행을 친다. 세 번째 메서드 = 주문당 세 번째 SELECT.

`WebhookService` 는 이미 webhook 신뢰 경계다. `get_webhook_service` 에 같은 세션의 `StrategyRepository` 하나만 더 넣으면 되고 **라우트 시그니처가 안 바뀐다** — 공개 ingress 계약 리스크 0.

owner-scope 를 안 쓴 이유 — webhook 은 user context 가 없고 **HMAC 자체가 소유 증명**이다. 계정↔전략 소유자 일치는 `OrderService` 의 TRD-4 게이트(`order_service.py:160-176`)가 독립적으로 재검사한다.

**payload 로 leverage 를 받지 않는다.** settings 가 SSOT 여야 세 ingress 가 같은 시장으로 나가고, body override 를 허용하면 secret 보유자가 운영자의 리스크 설정을 우회한다.

### settings 미설정 = 422 fail-closed

결정적 근거는 일관성이 아니라 **spot 진입은 닫을 수단이 없다**는 것이다. 모든 청산 경로가 linear reduce-only 로 나가고 거래소는 `110017 "current position is zero, cannot fix reduce-only order qty"` 로 거부한다 — 체크리스트 §B 가 관측한 바로 그 에러다. 흘려보내면 경로가 보존되는 게 아니라 **관리 불가능한 포지션이 만들어진다.**

거부는 반드시 보이게 했다 — `qb_order_rejected_total{reason=settings_unset|settings_invalid}` + `logger.warning`. 조용한 422 는 "왜 안 나가지" 로만 관측된다.

### FE 는 경고만, 차단은 안 함

정책을 두 곳에 두면 반드시 어긋나고, 공개 ingress 라 서버가 권위여야 한다. 다이얼로그는 라우팅 배지(`Linear Perp · 2x · isolated`)와 settings 없을 때의 422 경고만 보여준다.

---

## 부수 발견 — risk% 사이징 모드는 한 번도 작동한 적 없다 (BL-475)

UI 문구는 _"수량은 서버가 잔고·리스크 기준으로 계산합니다 (서버 권위 사이징)"_ 였다. 그런 코드는 없다.

- `_validate_position_size`(`order_service.py:92-134`)는 `max_qty` 를 구해 **초과만 거부**한다. 수량을 만들어내지 않는다.
- 그 모드는 payload 에서 `quantity` 를 빼고 보냈고 `parse_tv_payload:122` 는 `payload["quantity"]` 를 필수로 읽는다 → **전송하면 401**.

실제 동작에 맞춰 재정의했다 — 수량 필수 + risk% 는 **상한**, 손절가 필수(없으면 `risk_sizing_skip_no_stop` 으로 가드가 조용히 skip 되어 "통과처럼 보이는 미검증" 이 된다). `risk_percent` 를 파서·라우터에 배선해 상한 검증이 실제로 돌게 했다. 진짜 서버 사이징은 BL-475.

---

## 함정

- **`bool("false") is True`** — TV alert 은 JSON 불리언 대신 문자열을 보낼 수 있다. 순진한 캐스팅이면 진입 주문이 청산으로 둔갑해 reduce-only 로 나가고 110017 로 거부된다. 명시 화이트리스트(`_coerce_bool`)로 막고 `"false"`/`"0"`/`""`/`None` 을 각각 테스트했다. 같은 흉터가 이미 있다 — `tasks/trading.py:197-198` 이 문자열 `has_leverage` 를 통째로 거부하는 이유가 정확히 이것.
- **settings 해결은 HMAC 검증 뒤에** — 앞에 두면 미인증 호출자가 401/422 응답 차이만으로 어느 `strategy_id` 에 settings 가 있는지 캘 수 있다. 순서를 테스트로 고정했다.
- **leverage 가 채워지는 순간 한 번도 안 돌던 가드가 켜진다** — `order_service.py:218-266` 의 min-notional / notional / balance 검사가 webhook 경로에서 구조적으로 도달 불가였다. 테스트는 **서비스가 아니라 provider 를 오버라이드**해야 한다(TRD-4 소유권 게이트를 실 repo 로 유지하기 위해).
- **RUF003** — 주석의 `×`(MULTIPLICATION SIGN)·`−`(MINUS SIGN)이 ruff 를 깬다. 세 번째 재발.
- **디자인 캐논 em-dash 래칫** — 새 노출 산문의 `—` 는 `src/__tests__/design-canon-source.test.ts` 가 잡는다. 허용치를 올리는 게 아니라 문구에서 빼는 게 맞다(래칫은 줄이려고 있다).

---

## 판별력 증명

체크리스트가 요구한 대로 **수정 전 RED 를 전부 확인**했다.

| 대상                                   | RED                                                     |
| -------------------------------------- | ------------------------------------------------------- |
| `test_parse_tv_payload.py`             | 17 (필드 부재 → `AttributeError`)                       |
| `test_router_webhook.py`               | 4 (`leverage None`·`reduce_only False`·422 대신 201 ×2) |
| `test_e2e_webhook_to_futures_order.py` | 1 (spot 라우팅)                                         |
| FE `test-order-dialog.test.tsx`        | 7 — `git stash` 로 **프로덕션 3파일만** 되돌려 재현     |

FE 는 첫 실행에 18/18 통과했다. 통과만 보고 넘어갔으면 판별력 0인 가드를 100%로 착각한다 — 직전 스프린트에서 소스 스캔 규칙이 5곳 중 2곳만 잡고도 통과한 전례가 있다. 프로덕션 변경만 stash 하니 신규 7건이 전부 RED 였다.

---

## 게이트

BE **3029**(+24) · FE **1136**(+6) · ruff · mypy · tsc · eslint 0 · **마이그레이션 0**(모델 파일 무변경) · `--run-integration` 2건 포함.

---

## 실화면 dogfood (Bybit 데모 실주문 4건)

### BL-474 자체 — 결정적 증거는 주문 ID 형식이었다

```
수정 전 (spot)    exchange_order_id = 2267433208968908032   leverage=NULL  has_leverage=false
수정 후 (linear)  exchange_order_id = 0a245783-f809-...     leverage=2     has_leverage=true
```

Bybit 은 spot 에 숫자형, linear 에 UUID 를 준다. 같은 다이얼로그·같은 심볼·같은 수량인데 **주문 ID 형식이 바뀌었다** — 우리 코드가 아니라 거래소가 시장 유형이 달라졌다고 말해주는 것이라, 이보다 나은 외부 증거가 없다.

### 출처 라벨 — 혼재 상태를 실제로 포착

청산 주문에 추정값 `-9.99` 를 주입해 확정값과 **절대 우연히 같아질 수 없게** 만들었다.

| 시각                                | 화면                                                      |
| ----------------------------------- | --------------------------------------------------------- |
| 04:25:00 청산 #1 직후               | 거래소 확정 `-0.05935440` / 추정 `0`                      |
| 04:30:00 청산 #2 직후 (확정 8초 전) | **거래소 확정 `-0.05935440` / 추정 `-9.99000000`** ← 혼재 |
| 04:30:08 이후                       | 거래소 확정 `-0.12772399` / 추정 `0`                      |

내가 주입한 `-9.99` 가 거래소 확정값으로 **교체**됐고, 최종 `-0.12772399` 는 두 청산의 정확한 합(`-0.05935440 + -0.06836959`)이다. `confirmed + estimated == total` 항등식이 화면에서 성립.

혼재 순간 화면 = [`screenshots/2026-07-26-bl474-provenance-mixed.png`](screenshots/2026-07-26-bl474-provenance-mixed.png).

대시보드 §01 KPI foot 도 렌더 — _"이 중 거래소 확정 -0.13 · 추정 0.00 입니다."_(`splitComplete`).

★확정까지 **14초**밖에 안 걸린다(`_enqueue_closed_pnl_refresh` countdown=5). 5분 beat 스윕을 기다릴 필요가 없었고, 오히려 혼재 상태를 잡으려면 서둘러야 했다.

### 독립 오라클 (엔진 미개입)

ccxt·`providers.py` 를 전혀 쓰지 않고 raw HMAC 으로 `/v5/position/closed-pnl` 을 직접 쳤다.

```
retCode: 0 OK
  orderId=69c71bd8-...  closedPnl=-0.06836959   ← 우리 DB -0.06836959
  orderId=b0a1c42a-...  closedPnl=-0.0593544    ← 우리 DB -0.05935440
```

우리 `orders.realized_pnl` · `exchange_exits.closed_pnl` · 거래소 원문 **3중 일치**.

### 그 밖

- 라우팅 배지 `Linear Perp · 2x · isolated` / settings 없는 전략 422 경고 배너 / 미리보기 레버리지 기본값 `2` — 전부 실화면 확인. 콘솔 error 0.
- 도그푸드 중 라이브 신호가 04:28:10 에 reduce-only 1.0 을 쐈으나 무포지션이라 110017 거부 — 내 주문과 간섭 없음.

---

## 남은 것

- **[BL-476] 실측된 지연 — +4.8초.** 예상만 하고 넘기지 않고 쟀다.
  ```
  fetch_mark_price 1663ms · fetch_min_notional 1549ms · fetch_balance_usdt 1600ms  →  TOTAL 4812ms
  ```
  가드가 실제로 도는 것도 같이 확인됐다(min notional 5.0 vs 명목 $64.5). 게이트는 provider 를 stub 으로 갈아끼우므로 **영원히 0ms** 다 — 이 회귀는 프로덕션에서만 보인다. 가드를 Celery 경계 뒤로 옮기는 건 거부 시점이 응답 뒤로 밀리는 계약 변경이라 별도 결정이 필요하다.
- **[BL-477] 청산 원장 유령 `unknown`.** API 키 2개가 같은 Bybit 서브계정을 가리켜 같은 청산이 2행 적재된다. 07-24 행도 같은 패턴이라 선재 문제. **금액은 안전하다** — `aggregate_closed_pnl` 이 계정 스코프이고 세션 손익은 원장이 아니라 `orders.realized_pnl` 을 센다(실측으로 확인).
- **체크리스트 B** — pine_v2 시뮬 상태 ↔ 거래소 포지션 발산. 이번 dogfood 가 재료를 더 줬다: 라이브 신호는 계속 `qty=1.0` reduce-only 를 쏘고(전략 `position_size_pct: 0.01` 미반영) 포지션이 없어 110017 로 죽는다. 반면 다이얼로그 경로는 0.001 로 정상 왕복했다 — **사이징 경로만 다르다**는 게 좁혀졌다.
