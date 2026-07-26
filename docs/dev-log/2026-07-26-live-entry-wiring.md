# 2026-07-26 — live-entry-wiring (BL-478 (c) + BL-479)

> 브랜치 `feat/live-entry-wiring` · main `fcc36bf` 베이스.
> 출발점 = [`docs/live-entry-wiring/checklist.md`](../archive/sprints/live-entry-wiring/checklist.md).
> Sprint type **B** (BL fix, risk-critical).

---

## 왜 했나

**라이브 자동매매는 진입 주문을 낸 적이 없다.**

`strategy.entry(..., stop=)` 는 `strategy_state.py:598-609` 에서 `PendingOrder` 만 파킹하고 `return None` 한다 — 이벤트를 발행하지 않는다. `run_live` 는 그 체결 이벤트(`fill`)를 dispatch 대상에서 제외하는데(`event_loop.py:288-292`), 독스트링이 그 근거로 _"broker 가 자체 fill 알림 처리"_ 를 든다. **그 전제가 성립하지 않는다. broker 에 그 stop 주문을 올린 적이 없다** (`live_signal.py` 에 `trigger_price` 참조 0건).

그래서 진입 이벤트가 0건이고, 반전 시 생기는 `close` 만 나가 매번 `110017 "current position is zero"` 로 거부된다. 화면에는 "돌고 있음" 이라 적혀 있다.

진입이 열리는 순간 곧바로 두 번째 문제가 온다. `run_live` 가 `run_historical` 을 사이징 인자 없이 부르므로 `compute_qty()` 가 항상 `1.0` — **1 BTC ≈ $64,000 명목**이다.

이 스프린트는 **기능을 늘리지 않는다. 거짓말을 멈춘다.**

---

## ★★사용자 요청 실측이 채택 후보를 반증했다

킥오프 지시는 "equity 기준선은 후보 3(kill-switch balance provider 재사용)으로 가되, **그 경로의 갱신 주기를 먼저 실측하고 아니면 말해달라**" 였다. 재보니 갱신 주기라는 개념 자체가 없었다.

```
account_service.py:126-157   캐시 코드 0줄. TTL·Redis·beat 갱신 태스크 전부 부재.
                             매 호출 = DB 2회 + AES 복호화 + ephemeral ccxt -> REST -> close
                             실측 1600ms (BL-476). 독스트링의 "~200ms" 는 8배 낙관
kill_switch.py:106-107       total_pnl >= 0 이면 조기 반환 -> "이미 부르니 공짜" 가 아니다
live_signal.py:873-885       exchange_svc 는 Celery 경계 뒤 dispatch 소속
                             -> "재사용" 은 코드 재사용이지 호출 절감이 아니다
```

### 지연보다 큰 문제는 시맨틱이었다

`run_live` 는 **warmup replay**(300바)라 매 tick 히스토리 전체를 재실행한다. `configure_sizing(initial_capital=X)` 는 `running_equity = X` 로 시작해 청산 손익을 **다시** 누적한다(`strategy_state.py:295,668`). 거래소 실잔고는 **이미 그 손익이 반영된 값**이다.

즉 매 tick 실잔고를 주입하면 최근 300바 거래의 실현손익이 **이중 계상**된다. 그리고 300바를 벗어나면 빠지므로 이중 계상량이 시간에 따라 변한다 — **같은 바가 tick 마다 다른 수량**을 갖는다.

→ 세션 시작 1회 고정 스냅샷만이 백테스트(`v2_adapter.py:100` `cfg.init_cash`)와 같은 시맨틱이고, evaluate 경로에 REST 를 0회 추가한다. 사용자 승인 후 그렇게 갔다.

★**그런데 절반만 닫혔다.** 실잔고 주입에서 오던 이중 계상은 없앴지만 `running_equity` 가 **창 안 청산 손익**을 누적하는 것은 그대로다. 최종 codex 리뷰가 잡았다 — 아래 §최종 리뷰.

---

## ★탐색이 뒤집은 전제 4건

| 계획이 적은 것                               | 실측                                                                                                                                                                                                                                                                                             |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `s4_hma` 는 명시 `qty=` 라 사이징 **대조군** | ✗ **세 번째 양성.** `capital = strategy.equity` 인데 `running_equity is None` 이면 `interpreter.py:1322-1326` 이 NaN 을 준다. BL-376 chokepoint(`strategy_state.py:592`)가 non-finite qty 주문을 **skip** 한다 → 라이브에서 hma 계열은 진입 신호가 **0건**이었다. 진짜 대조군은 리터럴 `qty=0.5` |
| 우선순위 사슬을 `compat.py` 에 두고 공유     | ✗ **순환 import.** `compat.py:23` 이 `event_loop` 를 module-level import 한다 → 신규 `sizing.py` 필수                                                                                                                                                                                            |
| 기준선 = `fetch_balance_usdt`                | ✗ 그건 `providers.py:1489` 가 `data["free"]` 만 읽는다. 포지션이 있으면 증거금이 묶여 왜곡 → **`total`**                                                                                                                                                                                         |
| preflight 차단 시 divergence 카운터 inc      | ✗ `metrics.py:354` 가 그 카운터에 **"0 초과 = 즉시 운영 page"** 계약을 걸어놨다. stop-entry 세션 시작은 예상 가능한 사용자 상황이지 사고가 아니다                                                                                                                                                |

---

## 무엇을 했나

### BL-478 (c) — 못 하는 일을 못 한다고 말한다

`ast_extractor.uses_stop_entry()` 신설. 새 파싱은 0 — `_STRATEGY_EXEC_CALLS` 가 이미 `strategy.entry` 를 kwarg 이름까지 보존해 수집하고 있었다.

- 리터럴 `stop=na` 는 **제외**한다. `interpreter.py:1507-1510` 이 `_is_na` 로 런타임에 시장가 처리하므로, 정적 판정이 런타임과 어긋나면 안 된다.
- 변수 표현식(`stop=hprice + syminfo.mintick`)은 정적으로 na 여부를 알 수 없어 **보수적으로 차단**한다. 과잉 차단을 알고 골랐다는 것을 테스트로 문서화했다.
- `ScriptContent.to_dict()` 는 손대지 않았다 — `ast_content_report.json` strict equality 베이스라인이 있다.

두 자리에서 소비한다.

1. `register()` 가 422 `live_stop_entry_unsupported` 로 거부
2. evaluate preflight 가 이미 도는 세션을 자동 종료 (BL-362 가 배선해둔 deactivate → commit → winner-only → realtime push 를 그대로 재사용)

### BL-479 — 자본 기준선을 한 번 찍는다

`register()` 가 `AccountBalanceService.get_balance().total` 로 1회 스냅샷 → `live_signal_sessions.equity_baseline_usdt`(`Numeric(18,8)`, **nullable**) → evaluate 가 `run_live(initial_capital=..., live_position_size_pct=...)` 로 전달.

- **nullable 은 의무였다.** 활성 세션이 돌고 있었고 그 시점 잔고를 알 수 없어 backfill 이 불가능하다. 임의값을 채우면 **거짓 자본으로 실주문**이 나간다. NULL = 진실의 부재이고, preflight 가 fail-closed 로 처리한다.
- **quota advisory lock 앞**에 뒀다. CCXT 왕복 1.6초를 락 안에서 잡으면 사용자별 등록이 직렬화된다. 대신 락 없는 quota 사전 검사를 앞에 둬 어차피 거부될 요청이 거래소를 치지 않게 했다.
- fail-closed 4종 — `supported=False` / `total is None` / `total <= 0` / `ProviderError`. 마지막 것은 502 를 422 로 흡수한 것인데, 안 하면 우리가 쓴 "API 키 상태를 확인하세요" 안내가 **가장 흔한 실패(네트워크/CCXT)에서 도달 불가**해진다.

`pine_v2/sizing.py` 신설 — 우선순위 사슬(Pine > form > Live) SSOT. 백테스트와 라이브가 공유한다. `_extract_default_qty` 는 alias 없이 삭제했다(alias 를 남기면 SSOT 가 2개가 된다).

---

## ★계약을 반만 고칠 뻔했다

독립 검증(opus 서브에이전트)이 잡았다.

신규 preflight 2종은 `qb_live_signal_divergence_total` 을 올리지 않게 만들었는데, **알림 제목은 여전히 `"Live signal divergence — 세션 자동 비활성화"`** 였다. 카운터가 page 를 안 해도 **사람은 제목을 보고 호출된다.**

그리고 사유 override 판정이 `reason == "pine_v2 coverage↔interpreter 발산"` **문자열 동등 비교**였다 — 그 리터럴이 5곳에 복제돼 있어서 하나만 어긋나면 override 가 조용히 멈추고 **그럴듯하지만 틀린 사유**가 나간다. 검출 불가능한 종류다.

→ 제목도 카테고리에 따라 갈랐고, sentinel 을 모듈 상수 1개 + `reason is None` 판정으로 바꿨다. 같은 검증이 `SizingBaselineUnavailable` 독스트링의 BL 번호 오기(BL-478 → BL-479)도 잡았다. 그대로 뒀으면 다음 세션이 "BL-478 (a) 가 구현되면 이 게이트를 걷어낸다" 로 읽고 **사이징 게이트를 잘못 제거**했을 것이다.

---

## ★★판별력 증명 — 전체 stash 대신 표적 변이 6종

계획은 `git stash` 로 프로덕션 파일을 통째 되돌려 RED 를 보는 것이었다. 실제로 해보니 **생성자 변경과 신규 심볼 때문에 RED 가 import/TypeError 로 나온다.** 그건 "심볼이 없다" 만 증명하고 **"가드가 잡아야 할 것을 안 잡는다"** 는 증명하지 못한다.

그래서 변이를 넣었다 뺐다. 행동적 RED 만 나온다.

| 변이                                        | 결과                               |
| ------------------------------------------- | ---------------------------------- |
| M1 `uses_stop_entry -> False` (게이트 사망) | 양성 **5 FAIL** / 음성 **17 PASS** |
| M2 `uses_stop_entry -> True` (전부 차단)    | **25 FAIL**                        |
| M3 `compute_qty` 의 `/100` 제거             | **4 FAIL**                         |
| M4 `total -> free`                          | **2 FAIL**                         |
| M5 신규 2종도 page 대상으로                 | **1 FAIL**                         |
| M6 `initial_capital` 미전달 (배선 절단)     | **6 FAIL**                         |

변이 잔존 0, 복원 5/5 바이트 동일.

**M1 이 핵심이다** — 양성이 무너지는 동시에 음성 17건이 GREEN 을 유지한다. 한쪽만 봤으면 "전부 차단하는 가드" 를 100% 판별력으로 착각했을 것이다.

손계산 오라클은 2의 거듭제곱만 골라 부동소수 오차를 0 으로 만들었다 — `8192 x 50 / 100 / 65536 = 0.0625`. 오답들(`1.0` 미배선 / `0.03125` free / `6.25` /100 누락 / `0.000625` 분수 오해)이 정답과 하나도 충돌하지 않는다. 그리고 **태스크 계층**에 뒀다 — `compute_qty` 단위 테스트는 이미 GREEN 이라 배선을 하나도 증명하지 못한다.

---

## ★★★ 실화면 dogfood — 실주문 체결까지 3중 대조

### 자동 종료

마이그레이션 후 첫 tick(30초 내)에 `0e15c3c0` 이 꺼졌다.

```
live_signal_preflight_blocked
{'session_id': '0e15c3c0-…', 'deactivated': 'stop_entry_unsupported'}
is_active: t -> f
```

★ 이 세션은 **stop-entry 와 NULL baseline 두 조건 모두** 해당인데 근본 원인을 보고했다 — 설계한 우선순위(`coverage → degraded → stop_entry → equity_baseline`)가 실제로 작동한다. 화면 "활성 세션" 이 1 → 0.

### 차단 문구와 음성 대조군

PbR 로 세션 시작 → `live-session-form-error` 에 BE 문구 원문이 그대로. `"API 422"` 미포함.

EMA 로 바꾸니 **201**. 그전 단계에서 settings 가 없을 때는 기존 `StrategySettingsRequired` 문구가 정상 렌더됐다 — **`FormErrorInline` 교체를 기각한 판단이 옳았음을 실화면이 확인**해준 셈이다(그 컴포넌트는 `detail.detail` 을 안 읽어 기존 422 4종을 조용히 `"API 422 …"` 로 퇴행시킨다).

### 진입 주문 — 기다렸더니 났다

시드로 만들지 않고 EMA 크로스를 기다렸다.

```
손계산   190549.99467459 x 1% / 64512.50 = 0.02953691
DB       live_signal_events.qty           = 0.02953691   (entry, dispatched)
         orders.quantity                  = 0.02953691   (filled)
거래소    qty 0.029 · cumExecQty 0.029 · avgPrice 64484.2 · Filled · retCode 0
         orderId d474e540-… (UUID = linear perp)
```

DB → 거래소 `0.02953691 → 0.029` 차이는 **`amount_to_precision` 절삭**(BTCUSDT linear 수량 스텝 0.001)으로 정확히 설명된다.

**실집행 명목 $1,870.** 미배선이었다면 `1.0` = **$64,484**, **34.5 배**다.

### ★프로덕션 원장의 before / after

같은 계정, 같은 심볼, 같은 날. 수정 전후가 `trading.orders` 에 그대로 남았다.

```
10:02  sell 1.00000000  reduce_only=t  rejected   <- BL-478 증상. 진입이 없으니 청산만 나가 110017
10:17  buy  1.00000000  reduce_only=t  rejected
10:36  buy  1.00000000  reduce_only=t  rejected
11:51  buy  0.02953691  reduce_only=f  filled     <- 수정 후. 진짜 진입 + 자본 기준 수량
```

`1.0`(미배선 fallback) 이 전부 `reduce_only=t` 이고 전부 `rejected` 라는 것이 BL-478 과 BL-479 가
**한 증상의 두 얼굴**이었다는 증거다. 진입이 안 나가니 청산만 남고, 그 청산 수량조차 `1.0` 이었다.

### 독립 오라클

ccxt·`providers.py` 를 거치지 않은 raw HMAC 으로 잔고와 주문을 각각 직격했다. `USDT walletBalance 190549.99467459` = DB `equity_baseline_usdt` **바이트 동일**.

---

## ★정직하게 남기는 것

- **플랜의 대안 하나가 틀렸다.** "신호가 안 뜨면 `last_strategy_state_report.running_equity` 로 배선을 증명한다" 고 적었는데 `to_report()` 에 그 키가 없다(7개 키뿐). 결국 진짜 신호를 기다려서 증명했다.
- **지금 `total == free`** 다 (`totalPositionIM: 0`). dogfood 만으로는 둘을 구별할 수 없다. 그걸 증명한 건 **M4 변이뿐**이다.
- **배포 순서는 마이그레이션이 먼저다.** 워커가 신규 코드인데 DB 에 컬럼이 없던 몇 분 동안 전 세션 평가가 `UndefinedColumnError` 로 실패했다(실측). fail-closed 지만 시끄럽다.
- **`test_migrations.py` 의 `DuplicateColumn` 은 코드 결함이 아니었다.** conftest 의 `metadata.create_all` 이 신규 컬럼을 이미 만든 상태에서 `alembic_version` 만 stale 인 환경 문제였다. 클린 DB 에서 `downgrade base → upgrade head → downgrade -1 → upgrade head` 왕복은 전부 통과한다.
- **quota 초과 경로의 CCXT 왕복은 사전 검사로 없앴지만**, 락 안의 재검사와 경합하는 짧은 창에서는 여전히 한 번 탈 수 있다. 권위 판정은 락 안에 남겨뒀다.

---

## ★최종 리뷰 (codex) — P1 2건, 둘 다 실재

액면 수용하지 않고 각각 재현했다.

### [P1] 고정 스냅샷인데 수량이 창에 따라 변한다 — **확인, BL-486 등재**

`configure_sizing` 이 `running_equity = initial_capital` 로 시작하고 `strategy_state.py:668` 이 청산 손익을 누적하는데, `run_live` 는 warmup replay 라 그 누적 범위가 **300 바 롤링 창**이다. 재현:

```
같은 마지막 바(종가 65536) · initial_capital=8192 · pct=50
  창 안에 청산 1건  ->  qty 0.09375
  그 청산이 창 밖    ->  qty 0.0625     (50% 차이)
```

내가 "이중 계상을 없앴다" 고 쓴 것은 **실잔고 주입 대비**로만 참이었다. 세션 나이가 창보다 짧으면 창 누적 = 세션 누적이라 정확하지만(1m 기준 첫 5시간), 넘어가면 오래된 거래가 밀려나며 같은 신호의 수량이 바뀐다.

고치려면 **라이브 equity 시맨틱을 먼저 정해야 한다** — (a) 세션 시작 고정(복리 없음) / (b) 세션 누적(실현+시뮬 혼합) / (c) 실잔고 추종(이중 계상 부활). 이번 스코프 밖이라 **BL-486 P1** 으로 등재하고, `test_run_live_qty_drifts_with_warmup_window_KNOWN_LIMITATION` 으로 못 박아 조용히 드리프트하지 못하게 했다. 그 테스트는 바람직한 동작을 고정하는 것이 아니라 **한계를 고정**하는 것이다.

### [P1] 15초 캐시가 영구 기준선이 된다 — **확인, 수정함**

`AccountBalanceService.get_balance` 는 15초 Redis 캐시를 먼저 읽는다. 다른 값이면 무해하지만 **이 값은 한 번 찍으면 세션 내내 사이징 분모로 남는다** — 입금 직후 세션을 시작하면 입금 전 잔고로 세션 전체를 사이징한다.

`force_refresh=True` 를 추가해 register 만 캐시를 건너뛴다(갱신값은 캐시에 다시 쓴다). 회귀는 기존 "캐시 히트 시 provider 미호출" 테스트와 **쌍으로** 뒀다 — 한쪽만 있으면 "항상 캐시를 건너뛰는" 구현을 정상으로 착각한다.

---

## 게이트

|                          | 기준선 | 결과           |
| ------------------------ | ------ | -------------- |
| BE pytest                | 3029   | **3074** (+45) |
| FE vitest                | 1144   | **1151** (+7)  |
| design canon e2e         | 32     | **32**         |
| e2e:authed               | 65-0   | **65-0**       |
| ruff / mypy / tsc / lint | 0      | **0**          |
| 마이그레이션             | —      | **1**          |

---

## 신규 BL

- **[BL-481]** P2 `sessions_allowed` 라이브 미배선 — 거래 시간대를 제한해도 라이브는 24h 진입
- **[BL-482]** P3 `pyramiding` cap 라이브 미배선
- **[BL-483]** **P1** `leverage` 라이브 마진게이트 미배선. ★그냥 넘기면 안 된다 — 증거금 부족 skip 이 `warnings` 로만 남아 **완전 무음**이라 표면화 경로를 같이 만들어야 한다
- **[BL-484]** P2 자동 중단 **사유**가 화면에 안 남는다(알림 채널 전용)
- **[BL-485]** P3 `FormErrorInline` 이 `detail.detail` 폴백을 안 해 공통 컴포넌트를 못 쓴다
- **[BL-486]** **P1** 라이브 사이징 equity 가 300바 롤링 창에 따라 변한다 (위 §최종 리뷰)
- **[BL-487]** P3 `test_get_pool_safe_across_event_loops` 선재 flake — pool 객체를 안 붙잡고 `id()` 만 비교해 주소 재사용 시 random RED

---

## 문서 종결 (sprint-template §9)

- **강등 2** — `docs/dogfood-restore/` · `docs/live-entry-wiring/` → `docs/archive/sprints/`. 전자는 스스로 "닫는다" 고 선언했는데 두 스프린트가 지나도록 남아 있던 부채였다.
- **승격 1** — `docs/reference/gates-and-traps.md`. 게이트 커맨드와 함정이 **7개 스프린트 문서에 복붙**되고 있었고, `reference/` 에는 정본이 없었다.
- **`docs/` 최상위 12 → 10.** `README.md` 에 `<테마>/` 의 지위를 명문화했다 — §9 가 전제하는 대상이 지도에 없어서 유령 디렉토리가 생겼던 것이다.

---

## 남은 것

BL-478 **(a) 조건부 주문 등재**는 그대로 열려 있다. (c) 는 거짓말을 멈춘 것이지 기능을 만든 것이 아니다. `s1_pbr` 로는 여전히 라이브를 못 돌린다 — 그리고 그게 지금 정직한 상태다.
