# 안전장치 판정표 — live-observability soak

> **이 세션의 산출물.** "metric 이 오른다" 가 성공 기준이 아니다. 안 오르는 것도 결과다.
> 판정은 셋 중 하나 — **관측됨** / **관측 안 됨**(경로가 주행되지 않음) / **구조적 관측 불가**(계측이 없거나 상태를 만들 수 없음).
> soak: 세션 `461a999d`, PbR Pivot Reversal(조건부 stop 진입), BTC/USDT, 1m, Bybit demo `19a8166a`.
> T0 = 2026-07-28 02:48:16Z. metric 누적 기준시각 = worker 재기동 03:19:23Z.

---

## A. 관측됨 — soak 중 실제로 발화했다

| 안전장치                                                | 위치                                   | 관측 신호                                                                                 | 실측값                                          | 근거                                                       |
| ------------------------------------------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------- |
| **close 이벤트 flat 확인** (reduce-only 거부 주문 방지) | `live_signal.py:1737-1748`             | `qb_live_signal_dispatch_total{action="close",outcome="close_position_flat"}`             | **1.0**                                         | 청산 시점에 거래소 포지션이 이미 0 이라 발주를 막았다      |
| **조건부 진입 시장가 in-flight 연기**                   | `live_signal.py:245`                   | `..._reconcile_errors_total{stage="deferred_market_inflight"}`                            | **2.0**                                         | 같은 tick 에 시장가 이벤트가 있어 조건부 등재를 미뤘다     |
| **조건부 진입 교체 사이클**                             | `conditional_entry_planner.py:285-289` | `placed_total{long}=2 {short}=2` · `cancelled_total{replaced}=2 {desired_removed}=1`      | 원장과 **정확히 일치**(조건부 4행 = buy2/sell2) | 정상 동작 관측                                             |
| **부분체결 감지**                                       | `state_handler.py:156`                 | `qb_partial_fill_total{source="ws"}`                                                      | **1.0**                                         | 03:38:14 체결 수량이 `0.03014903` 로 요청과 달랐다         |
| **청산 귀속 원장**                                      | `tasks/trading.py:1774-1787`           | `qb_exchange_exit_rows_total{ours}=1 {unknown}=1` · `attribution_total{exact}=1 {none}=1` | 발화                                            | 우리 청산 1건을 정확 귀속, 1건은 귀속 불가로 정직하게 표시 |
| **분산락(Redlock)**                                     | `common/redlock.py:133`                | `qb_redlock_acquire_total{outcome="success"}`                                             | **38.0**                                        | 평가·주문 경로의 락이 매번 획득됨(경합 0)                  |
| **Redis lock pool 헬스체크**                            | `redis_client.py:101`                  | `qb_redis_lock_pool_healthy`                                                              | **1.0**                                         | API lifespan 에서 set                                      |
| **라이브 평가 루프 자체**                               | `live_signal.py:786`                   | `qb_live_signal_evaluated_total{interval="1m",outcome="success"}`                         | **30.0 / 30분**                                 | beat 60초 주기와 **정확히 1:1**                            |
| **janitor 주기 발화**                                   | `conditional_entry_janitor.py`         | (Prometheus 미노출 — Celery 결과 로그)                                                    | 5분마다 `{repaired:0, rejected:0, terminal:0}`  | **장치는 도는데 트리거 조건이 성립 안 함**                 |

## A′. ★관측됐고, **관측되자마자 틀렸다는 것이 드러났다** — `qb_active_orders`

BL-506 의 표적이던 winner-only dec 규율. 배선하자 값이 보였고, **보이자마자 절대값이 틀렸다.**

|                                           | 값                             |
| ----------------------------------------- | ------------------------------ |
| `qb_active_orders` (배선, :8101)          | **0.0**                        |
| DB 실제 in-flight (`pending`+`submitted`) | **1** (03:47:14 submitted buy) |

**산술이 전부 설명된다 (원장으로 검증):**

| 항목                             | 수     | 근거                                                                                              |
| -------------------------------- | ------ | ------------------------------------------------------------------------------------------------- |
| 재기동 이후 생성                 | +7     | `created_at >= 03:19:23`                                                                          |
| 그중 종료                        | −6     | 같은 창 terminal 전이                                                                             |
| **재기동 이전 생성 → 이후 종료** | **−1** | **정확히 1건** — 03:13:52 생성 → 03:34:10 취소. `inc` 는 배선 전 프로세스(유실), `dec` 만 배선 후 |
| **합**                           | **0**  | metric 값과 일치. 실제는 1                                                                        |

★**판정: 관측됨. 그리고 관측 결과는 "이 gauge 의 절대값은 신뢰할 수 없다" 다.**
`sum` 파일은 콜드 스타트마다 비므로, **프로세스 군을 재기동할 때마다 그 순간 in-flight 였던 주문 수만큼 영구 편향**이 남는다.

★**이건 BL-506 이 만든 결함이 아니다.** 배선 전에는 API 프로세스의 `inc` 만 수집돼 **단조 증가**였으니 더 나빴다. BL-506 이 한 일은 **그 편향을 보이게 만든 것**이고, 이것이 이 세션의 가장 값진 관측이다 — 코드 읽기로 세운 가설(C1)을 실측이 확증했다.

→ **처분: C1(BL 등재).** inc/dec 계약을 버리고 한 프로세스가 DB 의 `pending + submitted` 를 주기적으로 `.set()` 하는 스냅샷으로 교체.

## B. 관측 안 됨 — 장치는 살아 있으나 이번 soak 에서 그 상태가 오지 않았다

| 안전장치                                       | 관측 신호                                    | 왜 안 왔는가                                                                  |
| ---------------------------------------------- | -------------------------------------------- | ----------------------------------------------------------------------------- | ----------------------- | ---------------------------------------------------- |
| **kill switch**                                | `qb_kill_switch_triggered_total`             | 손실이 임계에 못 미쳤다. DB `kill_switch_events` = **0**(26시간 누적에서도 0) |
| **조건부 진입 sweeper**                        | `qb_live_conditional_sweep_filled_total` = 0 | 세션 비활성화가 선행돼야 하는데 soak 중 비활성화 없음                         |
| **janitor 실제 수선**                          | `{stage="janitor_race"                       | "janitor_probe"}` 부재                                                        | 30분 고착 행이 0건      |
| **취소 경합/고착** (BL-499 본체)               | `{stage="cancel"                             | "cancel_raced"                                                                | "cancel_stalled"}` 부재 | **아래 §D 참조 — 이번 세션의 BL-499 종결 판정 근거** |
| **발산 감지 세션 자동비활성**                  | `qb_live_signal_divergence_total` 부재       | 인터프리터 발산 0건                                                           |
| **진입 스킵(pyramiding/증거금)**               | `qb_live_signal_entry_skipped_total` 부재    | 자본 190k 대비 주문 0.03 BTC 라 증거금 여유. pyramiding 도 미도달             |
| **WS orphan 버퍼**                             | `qb_ws_orphan_buffer_size` = 0               | WS 이벤트가 로컬 INSERT 를 앞지른 경우 없음                                   |
| **WS auth 서킷**                               | `qb_ws_auth_circuit_total` 부재              | 인증 실패 0건                                                                 |
| **레버리지 cap / min-notional / max-notional** | `qb_order_rejected_total{reason=...}` 부재   | 사전 게이트에 걸릴 주문이 없었다                                              |

★**중요한 관측 계약 사실** — 위 "부재" 항목들은 `/metrics` 에 **0 으로도 나오지 않는다. 시리즈 자체가 없다.**
라벨 있는 Counter 는 자식이 처음 생길 때 비로소 노출되기 때문이다. 즉 대시보드에서 **"아직 한 번도 안 일어남" 과 "그런 metric 이 없음" 이 구분되지 않는다.**

## C. 구조적 관측 불가 — 계측 자체가 없거나, 그 상태를 이 구성에서 만들 수 없다

| 안전장치                            | 왜 불가인가                                                                                                           | 근거                              |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| **reduce-only 강제** (시장가 close) | **계측 없음.** 오직 `orders.reduce_only` 컬럼에만 남는다                                                              | `live_signal.py:182-188`          |
| **entry 에 trailing 미주입**        | **계측 없음**                                                                                                         | `tasks/trading.py:392-393`        |
| **거래소가 우리 주문을 거절함**     | **전용 계측 없음.** `qb_order_rejected_total` 은 pre-flight 게이트 전용이고 `tasks/trading.py` 는 import 조차 안 한다 | C5                                |
| **planner divergence 5종**          | **계측 없음** — `logger.warning` 뿐                                                                                   | C9                                |
| **완전체결**                        | **카운터 부재** — 부분체결만 센다                                                                                     | C10                               |
| **janitor 실적(성공)**              | **Prometheus 미노출** — dict return 만                                                                                | C12                               |
| **stand-down (hedge mode)**         | 계정이 one-way 라 **이 구성에서 상태를 만들 수 없다**                                                                 | 안전장치 인벤토리 #15             |
| **stand-down (계정·심볼 공유)**     | 계측은 있다(`{stage="positions"}`). **§E 에서 유도 시도**                                                             | —                                 |
| **데모 안정기간 게이트**            | demo soak 은 이 경로를 안 탄다                                                                                        | `live_session_service.py:177-186` |
| **자본 소진 차단**                  | 데모 잔고 190k 를 3~4h 에 소진해야 한다                                                                               | `live_signal.py:1022`             |

---

## D. BL-499 종결 판정 (초안 — soak 종료 후 확정)

**BL-499 의 trigger 는 "취소 실패 metric(`stage="cancel"`)이 관측되거나 실자금 cutover 전" 이다.**

- **BL-506 이전**: 그 metric 은 worker 전용이라 **어떤 스크레이프 경로에도 노출되지 않았다.** trigger 는 **구조적으로 충족 불가**였다.
- **BL-506 이후**: 노출된다. 이번 soak 에서 `qb_live_conditional_reconcile_errors_total` 은 `{stage="deferred_market_inflight"}` **만** 2.0 으로 관측됐고, `cancel`/`cancel_raced`/`cancel_stalled` 는 **시리즈가 나타나지 않았다**.
- **판정**: **"관측 안 됨" 이지 "일어나지 않음이 증명됨" 이 아니다.** 그러나 **trigger 의 관측 가능성 자체는 이번에 확보됐다** — 이것이 BL-499 본문의 "trigger 가 성립하지 않는다" 를 해소한다.
- BL-499 는 **열린 채로 두되 본문을 정정**한다: trigger 는 이제 발화 가능하다.

---

## E. ★유도 실험 — 다중 세션 stand-down. **관측됨(발화 + 해제 둘 다)**

`EMA Crossover Demo` 세션을 PbR 과 **같은 계정(`19a8166a`)·같은 심볼**에 올려 `shares_account_symbol` stand-down 을 유도했다. 화면(코크핏 §07)으로 생성·중단했다.

| 시각 (UTC)          | 사건                                                                |
| ------------------- | ------------------------------------------------------------------- |
| 04:17:06            | EMA 세션 `40b80659` 생성 → **두 세션이 같은 계정·심볼에 동시 활성** |
| 04:17:07            | divergence #1                                                       |
| 04:18:08            | divergence #2                                                       |
| 04:19:15            | divergence #3                                                       |
| 04:19:45            | EMA 세션 중단(화면 다이얼로그 "중단")                               |
| 04:20:00 · 04:21:03 | PbR 평가 — **divergence 없음 → stand-down 해제**                    |

**발화 증거 3층:**

| 층     | 증거                                                                                                                            |
| ------ | ------------------------------------------------------------------------------------------------------------------------------- |
| metric | `qb_live_conditional_reconcile_errors_total{stage="positions"}` **0(부재) → 3**                                                 |
| metric | `qb_live_conditional_cancelled_total{reason="shared_account_symbol"}` **0(부재) → 2** — 이미 올려둔 조건부 진입을 실제로 걷었다 |
| 로그   | `ERROR live_conditional_reconcile_divergence` **3건**                                                                           |
| 행동   | **stand-down 창(2분 39초) 동안 신규 조건부 주문 0건** — 등재가 실제로 멈췄다                                                    |

★**이 관측은 BL-506 배선 없이는 불가능했다.** 두 카운터 모두 worker 전용이다.

### ★그리고 이 실험이 새 결함을 드러냈다 — stand-down **사유**는 관측 불가하다

- `{stage="positions"}` 라벨은 **사유를 담지 않는다** — `hedge_mode` 와 `shared_account_symbol` 이 같은 시리즈다.
- 로그는 `live_conditional_reconcile_divergence` **한 줄로만 렌더**된다. 사유는 `extra={"reason": ...}` 에 있는데 **포맷터가 `extra` 를 출력하지 않는다**(실측: 3건 전부 사유 없이 출력).
- `cancelled_total{reason=...}` 만이 사유를 담는데, 그건 **취소할 대상이 있을 때만** 오른다.
- → **취소 대상이 없는 stand-down 은 사유를 알 방법이 전혀 없다.** hedge(계정 설정 문제)와 다중 세션(운영 실수)은 조치가 완전히 다른데 구분이 안 된다.

### 회복 확인 — **관측됨**

EMA 중단(04:19:45) 이후 PbR 이 **04:21:13 · 04:22:12 에 조건부 등재를 재개**했다(`placed_total{short}` 16 → 18). `{stage="positions"}` 는 **3.0 에서 멈춰** 더 오르지 않았다. **stand-down 은 발화도 해제도 정상이다.**

★**그런데 재개된 두 건이 둘 다 `rejected` 이고 트리거가 `63307.80` 으로 동일하다.** BL-511(retCode 110093)이 **간헐이 아니라 매 tick 같은 값으로 재시도하는 루프**임이 드러났다 — 원인이 stale 기준가(`_last_close_or_none`)이므로 bar 가 바뀔 때까지 같은 판단을 반복한다. **심각도가 올라간다.**

### ★내가 오독할 뻔한 것 (기록)

04:18:37 스냅샷(2.0)과 04:21:05 스냅샷(3.0)만 비교해 "**해제 후에도 stand-down 이 계속된다**" 고 읽었다. 로그 실제 시각을 보니 3번째는 **04:19:15 로 창 안**이었다. **성긴 샘플링으로 인과를 뒤집을 뻔했다** — 카운터 델타는 사건 시각을 말해주지 않는다.
