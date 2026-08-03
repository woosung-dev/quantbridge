# 2026-08-02 — metric-guard-residual

> 가드가 못 막는 자리를 좁히고, **못 막는다는 것을 증명한다.**
> 진입점: `docs/status.md` 「다음 스프린트」. 브랜치 `stage/metric-guard-residual`.
> 판정식 정본 = `docs/reference/operations/workflows/generator-evaluator-pipeline.md` §G1.1.

---

## 0. baseline 재측정 (§7.1) — `eca5323f`, 2026-08-02

★status.md 의 baseline 은 대조 대상이다. 실제로 다시 쟀다.

| 축                | status.md 대조값         | 지금 HEAD 실측            | 판정                             |
| ----------------- | ------------------------ | ------------------------- | -------------------------------- |
| BE pytest         | 3835 passed / 46 skipped | 3835 passed / 46 skipped  | 일치                             |
| ruff              | clean                    | `All checks passed!`      | 일치                             |
| mypy              | 214 clean                | 214 source files clean    | 일치                             |
| FE vitest         | 1242 (205 파일)          | 1242 (205 파일)           | 일치                             |
| 마이그레이션 head | `20260801_0001`          | `20260801_0001 (head)`    | 일치                             |
| 가드 밖 mutation  | 141                      | 141 (census 테스트 green) | 일치                             |
| `/metrics`        | 10277 파일 · 635MB       | **10524 파일 · 650MB**    | 증가 (BL-581 Trigger 20000 미달) |

⇒ **7축 중 6축 일치, 1축은 예고된 단조 증가.** 착수 전제가 흔들린 곳은 없다.

★`PROMETHEUS_MULTIPROC_DIR` 실측 위치는 `backend/.metrics` (`Makefile:165`)이고 docker
`metrics_data` 볼륨은 **비어 있다**(0 파일). BL-581 의 「10277」은 로컬 dev 디렉터리 쪽이다.

---

## 1. ★사전등록 (G1) — 코드 쓰기 **전에** 동결한다

직전 회차가 codex G1 2회로 MAJOR 8건을 코드 이전에 잡았다. 같은 순서를 지킨다.
**이 절은 구현 전에 쓰였고, 이후 절들이 여기에 답한다. 사후 수정 금지.**

### 1.1 판정식 — 사이트별 3라벨 (「소멸/축소/유지」 계열 아님)

한 metric mutation site 에 대해 고장 주입 결과를 **정확히 하나**로 분류한다.

| 라벨               | 조건 (AND 로 읽는다)                                                                                     |
| ------------------ | -------------------------------------------------------------------------------------------------------- |
| **수리함**         | 고장 주입이 아래 「해로운 귀결」 4종 중 **1개 이상**을 실제로 일으켰다 그리고 기존 관용구로 감쌀 수 있다 |
| **가드 없이 유지** | 고장 주입이 해로운 귀결을 **0개** 일으켰다 그리고 그 사실이 커밋된 테스트로 단언된다                     |
| **판정 보류**      | 결정론적으로 구동할 수 없다 (이유를 그 자리에 적는다)                                                    |
| **영구 제외**      | 감싸는 것 자체가 결함을 만든다 (아래 §1.2 의 `metrics_multiproc.py:35`)                                  |

**해로운 귀결 4종** — 「머니-패스인가」를 대신하는 집행 가능한 정의. **구문이 아니라 주입 실행의 관측**이다.

| H1  | 성공한 외부 작용(발주·취소·체결)이 **실패로 보고**된다 (HTTP 5xx · task 예외 · 잘못된 error 라벨) |
| --- | ------------------------------------------------------------------------------------------------- |
| H2  | 내구 쓰기(`commit`) **뒤**의 후속 훅이 유실된다 (trailing·PnL·reversal enqueue · 알림)            |
| H3  | 내구 쓰기 **앞**이라 계측 예외가 DB 전이를 **rollback** 시킨다                                    |
| H4  | 안전 장치(stand-down · fail-closed drop · 세션 비활성화 고지)가 **통째로 건너뛰어진다**           |

★★**「정상 반환」을 완결 축으로 쓰지 마라 (codex G1 BLOCKING#2 — 채택).**
`_reconcile_conditional_entries` 는 **정상도 `None`, 내부 예외도 `None`** 이다(`:1772` 바깥 `except`
가 로그만 남기고 삼킨다). 그래서 「정상 반환값이 나왔다」는 그 함수에서 **아무것도 뜻하지 않는다** —
`:1234` 의 계측 실패가 reconcile 을 통째로 건너뛰어도 「정상 반환」으로 보인다.

⇒ **축 1을 「사이트별 사전등록 postcondition」으로 교체**한다. 각 사이트마다 「계측이 성공했다면
반드시 일어났을 비-계측 작업」을 **이 절에 미리 적고**, 주입 후 그것이 일어났는지를 단언한다.

⇒ **모든 고장 주입 테스트는 「주입한 stub 이 정확히 1회 호출됐다」를 함께 단언한다.**
이것이 없으면 「프로덕션 라인을 실행하지 않는 단언」(이 레포가 3번 밟았다)과 구별되지 않는다.

★**빠짐없음 대조(§G1.1 규율 2b)** — 조사 대상 전건이 4라벨 중 하나로 떨어져야 한다.
★**발화 가능 대조(§G1.1 규율 2a)** — H1~H4 각각을 **실제로 일으키는 사이트가 최소 1개** 있어야 한다.
0개인 H 는 이 회차에서 공허하다 — 공허하다고 **적는다**.

### 1.2 조사 대상 — 명시 4곳 + 「가드 옆 raw」 스윕 11곳

★**핸드오프의 파일 목록은 조사 범위가 아니라 조사 대상이다**(직전 회차 교훈 1).

**(A) status.md 가 명시한 4곳** — `tasks/trading.py:908` · `:931` · `:1093` · `trading/router.py:376`.

**(B) 규칙 S1 스윕** — 같은 statement list 안에서 가드 밖 mutation 을 품은 문 **뒤**에
가드 호출을 품은 문이 오는 쌍. census 의 AST 헬퍼를 재사용했다.

- **S1-loose**(같은 블록 뒤쪽 어디든) = **58건** → **채택하지 않는다.** 실측 후보에 **+866줄**
  짜리가 나온다. 그 거리에는 중간 제어흐름이 잔뜩 있어 「앞이 던지면 뒤 가드가 도달 불가」가
  성립하지 않는다.
- **S1-adjacent**(바로 다음 문) = **11건** ← 조사 후보.
- ★**거리 상수로 자르지 않았다.** 「인접」은 구문에서 결정되고 임의 상수가 없다 — 직전 회차가
  **자기가 박아둔 40줄 창**에 속아 「6곳」을 만든 것을 반복하지 않기 위해서다.
- ★**중간에 한 번 과하게 좁혀 참 후보를 잃었다** — 「site 가 그 문 **자체**」로 제한하니 11 → 3
  이 됐는데, 사라진 것 중 `live_signal.py:1110` 은 `else:` 블록 한 줄이라 가드(`:1113`)의
  형제가 아닐 뿐 **던지면 그 가드가 도달 불가인 진짜 후보**였다. ⇒ 되돌렸다.
  **생성기는 넓게 두고 판정은 손 + 고장 주입이 한다.**
- ★**양성 대조** — 손으로 먼저 찾아둔 3쌍(`:1214/1215` · `:1234/1235` · `:1500/1501`)이
  스윕에서 **전건 검출**돼야 한다. 0건이면 스윕부터 의심한다. (실행 결과: 전건 검출 ✓)

**S1-adjacent 원시 출력 11건 → ★7건은 S1 이 아니었다 (codex G1 BLOCKING#1 — 채택)**

내 스크립트의 「다음 문」 판정이 `_has_guard_call(block[j])` = **그 문의 서브트리 어딘가**라
`block[j]` 가 거대한 compound statement 면 깊숙한 가드까지 「인접」으로 셌다. 코드 대조로 확인:
`:1425` 다음은 logger · `:1965` 다음은 return · `:2572` 다음은 또 raw mutation · `:2939` 다음은
logger · `metrics_multiproc.py:35` 는 fallback 끝 · `trading.py:1466` 다음은 return ·
`order_service.py:129` 다음은 raise. **7건은 S1 을 재현하지 않는다.**

| #   | 사이트                                  | metric                                       | S1 참? | 처분                             |
| --- | --------------------------------------- | -------------------------------------------- | ------ | -------------------------------- |
| 1   | `tasks/live_signal.py:1110`             | `qb_live_conditional_reconcile_errors_total` | ✅ +3  | 조사                             |
| 2   | `tasks/live_signal.py:1214`             | `qb_live_conditional_reconcile_errors_total` | ✅ +1  | 조사                             |
| 3   | `tasks/live_signal.py:1234`             | `qb_live_conditional_guard_total`            | ✅ +1  | 조사                             |
| 4   | `tasks/live_signal.py:1500`             | `qb_live_conditional_guard_total`            | ✅ +1  | 조사                             |
| 5   | `common/metrics_multiproc.py:35`        | `qb_metrics_mutation_failed_total`           | ✗      | **영구 제외** (아래)             |
| 6   | `tasks/live_signal.py:1425`             | `qb_live_conditional_guard_total`            | ✗      | 141 에 유지 (S1 근거 없음)       |
| 7   | `tasks/live_signal.py:1965`             | `qb_live_signal_skipped_total`               | ✗      | 141 에 유지                      |
| 8   | `tasks/live_signal.py:2572`             | `qb_live_signal_divergence_total`            | ✗      | **손으로 찾은 별개 후보** (아래) |
| 9   | `tasks/live_signal.py:2939`             | `qb_live_conditional_reconcile_errors_total` | ✗      | 141 에 유지                      |
| 10  | `tasks/trading.py:1466`                 | `qb_closed_pnl_backfill_total`               | ✗      | 141 에 유지                      |
| 11  | `trading/services/order_service.py:129` | `qb_order_rejected_total`                    | ✗      | 141 에 유지 (blast radius 0)     |

**(C) 스윕이 아니라 손으로 찾은 후보 — `live_signal.py:2572`/`:2575`.**
출처를 정직하게 적는다: **S1 산출이 아니다.** 세션 자동 비활성화 `commit()` 직후이고
`_fire_divergence_alert`(BL-362 무신호 차단 고지) **앞**이다 ⇒ H2 후보.

**★`metrics_multiproc.py:35` = 영구 제외 (codex G1 MAJOR#3 — 채택).**
`record_metric_safely` 의 실패 fallback 자신이다(`:26-37`). `record_metric_safely` 로 감싸면
그 counter 가 실패할 때 **같은 fallback 에 재진입해 재귀**한다. 게다가 이미 자체 중첩
`try/except` 안이고 DB write·후속 훅·HTTP 표면이 **없다**. ⇒ **절대 감싸지 않는다.**

**★S1 의 맹점 (codex G1 BLOCKING#1 후단 — 채택).** 가드가 **헬퍼 안**에 있으면 S1 이 못 본다.
예: `tasks/trading.py:1530` `_count_reversal_at_fill` 의 가드는 호출부 `:1681` 에 인접하지 않는다.
⇒ **S1 은 완전성을 주장하지 않는다.** 이 회차가 만드는 것은 「141 을 전수 판정했다」가 아니라
**「이 규칙으로 뽑힌 것은 판정했다」**이다.

★스윕 스크립트는 **후보 생성기이지 산출물이 아니다** — 커밋하지 않는다.

### 1.2b 조사 대상 확정 — 9곳

| Tier | 사이트                  | 출처         | 사전등록 postcondition (계측이 성공했다면 반드시 일어났을 비-계측 작업)                              |
| ---- | ----------------------- | ------------ | ---------------------------------------------------------------------------------------------------- |
| A1   | `live_signal.py:1110`   | S1           | 같은 tick 이 등재/취소 판단까지 진행한다 (`order_service.execute` 또는 `provider.cancel_order` 도달) |
| A2   | `live_signal.py:1214`   | S1           | stand-down 이 실행된다 — resting 조건부 진입에 `provider.cancel_order` 호출                          |
| A3   | `live_signal.py:1234`   | S1           | 시장가 전환이 **금지된 채로** 등재 판단이 이어진다                                                   |
| A4   | `live_signal.py:1500`   | S1           | breach cap 초과 leg 만 드롭되고 **다음 leg 처리가 계속**된다                                         |
| B1   | `trading/router.py:376` | status.md    | HTTP **200** + `OrderResponse` 반환 (취소는 이미 commit 됨)                                          |
| B2   | `trading.py:908`        | status.md    | `{"state": "rejected"}` 반환                                                                         |
| B3   | `trading.py:931`        | status.md    | `{"state": "cancelled"}` 반환                                                                        |
| B4   | `trading.py:1093`       | status.md    | `{"state": "cancelled"}` 반환                                                                        |
| C1   | `live_signal.py:2572`   | 손 (S1 아님) | `_fire_divergence_alert` 가 호출된다 (세션 죽음 고지)                                                |

### 1.2c BL-582 설계 — codex G1 이 두 곳을 갈아엎었다

**★반증 대상.** BL-582 는 `guard_drop/bracket_trailing_only` · `bracket_tp_size_mismatch` 를
「`PendingOrderSnapshot` 의 exit 3필드가 **항상 None**」이라서 도달 불가라고 적는다. 그런데
`test_pending_order_snapshot_carries_exit_levels_when_same_id_is_open` 이 값이 실리는 형태를
이미 고정하고(`take_profit=192`·`stop_loss=64`), BL-523 은 같은 것을 「**현재 코퍼스 미발현**」
이라고 더 약하게 적는다. 두 문장은 같지 않다.

**★교정 1 (codex MAJOR#5 — 채택): 인용한 fixture 만으로는 발화하지 않는다.**
`_SAME_ID_REISSUE_WITH_EXIT` 는 long open → long stop 재발행이라 target 이 보유분과 **같은 +8**
이고, 계획기가 `quantity == 0` 에서 `continue` 한다(`conditional_entry_planner.py:481`).
TP-size 게이트는 `to_place` 에만 있다(`live_signal.py:1563`) ⇒ **도달 못 한다.**
필요한 것은 **반대 방향 same-id 재발행** — `current=+8, target=-8, quantity=16, resulting=8`.
손계산 오라클이 2의 거듭제곱이라 16/8/24/0 이 서로 구별된다.
★exit 레벨은 엔진→snapshot→계획기에서 **사라지지 않는다**(`event_loop.py:634` ·
`conditional_entry_planner.py:559` 통과 확인).

**★교정 2 (codex MAJOR#6 — 채택): `run_live` 만 돌리는 테스트는 게이트를 실행하지 않는다.**
진짜 게이트는 reconcile 루프(`live_signal.py:1529` · `:1563`)에 있다. ⇒ **엔진 산출물을 그
루프에 실제로 흘리고**, 주입한 metric 메서드가 **실제로 호출됐음**을 함께 단언한다.

**★교정 3 (codex BLOCKING#4 — 채택): `other` 게이트를 「리터럴만」으로 쓰면 현 코드가 red 다.**
`_conditional_divergence_reason("stand_down", stand_down_reason)`(`:1218`)의 둘째 인자는
**변수**다. 값은 `:1205` 에서 두 allowlist 값의 `IfExp` 로 정해진다.
⇒ 게이트를 **bounded def-use 오라클**로 쓴다: 인자가 (a) 상수, (b) 상수들의 `IfExp`, 또는
(c) 같은 함수 안에서 (a)/(b) 로 **한 번만** 대입된 지역 변수 — 이 셋 중 하나로 **해소되어야 하고**,
해소된 가능값 집합이 그 event 의 allowlist 부분집합이어야 한다.
★**해소 실패는 통과가 아니라 red** 다(「손으로 판정하고 이 목록에 적어라」). 그래야 「해소 못 했으니
넘어감」이 조용한 구멍이 되지 않는다.

### 1.3 표적 변이 M1..M4 + 음성 대조 N1 (구현 **전에** 적는다)

| ID  | 변이                                                                  | 기대 (red 여야 하는 것)                                    |
| --- | --------------------------------------------------------------------- | ---------------------------------------------------------- |
| M1  | 이번에 새로 감싼 자리 하나를 raw 로 되돌린다                          | census 천장 테스트 red **+ `_PROTECTED_SITES` 테스트 red** |
| M2  | 고장 주입 테스트의 폭파 대상이 **안 던지게** 바꾼다                   | 그 고장 주입 테스트 red (판별력)                           |
| M3  | `_conditional_divergence_reason` 호출부 리터럴 1개를 allowlist 밖으로 | `other` AST 게이트 red                                     |
| M4  | 도달성 테스트 fixture 에서 exit 레벨을 지운다                         | 그 도달성 케이스 red                                       |
| N1  | 무관한 파일의 주석만 고친다 (음성 대조)                               | 위 전부 **green 유지** (과민 반응 배제)                    |

★**census 를 내릴 때 `_PROTECTED_SITES` 도 함께 올린다 (codex G1 MAJOR#7 — 채택).**
`_FROZEN_CENSUS` 는 `(파일, metric)` **합계**뿐이라 위치 정보가 없다 — 같은 파일·metric 에서
새 raw 가 하나 생기고 수리한 자리가 raw 로 되돌아가면 **합계가 상쇄돼 통과**한다. 그래서 새로
감싼 site 마다 `_PROTECTED_SITES` 에 `(파일, 함수, metric, 이유)` 를 추가한다.

**집행 규율**

- CONTROL 이 직접 집행한다. **문자열 치환 + sha256 복원 대조.** `git checkout` 금지
  (미커밋 변경이 소실된다).
- ★**표적 변이를 전체 pytest 와 동시에 돌리지 마라** — 테스트 DB 1벌 + `drop_all`.
  직전 회차가 밟았고 그 실행 결과를 폐기했다.
- ★**변이가 실제로 의미를 바꾸는지 먼저 확인한다** (`x = None or (...)` 류 no-op 함정).

### 1.35 codex G1 적대 검증 — findings 7건 **전건 코드 대조 후 전건 채택**

`codex exec -s read-only` 1회. **액면 수용 0건** — 7건 모두 지목된 파일·줄을 직접 열어 확인했다.

| #   | 등급     | 내용                                                       | 대조 결과 | 처분                                      |
| --- | -------- | ---------------------------------------------------------- | --------- | ----------------------------------------- |
| 1   | BLOCKING | S1 11건 중 7건이 S1 을 재현하지 않는다 + 헬퍼 안 가드 맹점 | 참        | 대상 4+1+4 로 재확정 (§1.2)               |
| 2   | BLOCKING | 「정상 반환」축이 공허 — reconcile 은 성공도 실패도 `None` | 참        | 사이트별 postcondition 으로 교체 (§1.1)   |
| 3   | MAJOR    | `metrics_multiproc.py:35` 을 감싸면 **재귀**               | 참        | 영구 제외 라벨 신설 (§1.2)                |
| 4   | BLOCKING | `other` 리터럴 게이트가 현 코드(`:1218` 변수)를 red 로     | 참        | bounded def-use 오라클 (§1.2c)            |
| 5   | MAJOR    | 인용 fixture 는 `quantity==0 → continue` 로 게이트 미도달  | 참        | 반대 방향 same-id fixture (§1.2c)         |
| 6   | MAJOR    | `run_live` 만 돌리면 게이트 라인 미실행                    | 참        | reconcile 루프로 흘림 + 호출 단언 (§1.2c) |
| 7   | MAJOR    | `_FROZEN_CENSUS` 합계는 상쇄된다 — `_PROTECTED_SITES` 누락 | 참        | 수리 site 마다 함께 갱신 (§1.3)           |

★**세 건(#2 · #4 · #5)이 설계 자체를 교체했다.** 코드를 쓴 뒤였다면 전부 재작업이었다.
★**#5 는 내 착수 전제의 절반을 깎았다** — 「레포 테스트가 BL-582 를 반증한다」는 맞지만,
**그 테스트의 fixture 로는 게이트에 도달하지 못한다.** 반증에는 새 fixture 가 필요하다.

### 1.4 이 회차가 **하지 않는** 것

- **BL-576 잔여 프로덕션 발화 검증(soak) 비포함** — 사용자 결정 2026-08-02.
  `stand_down/hedge_mode` 는 Bybit demo 계정을 flat 상태에서 Hedge 포지션 모드로 전환해야
  유도되고, `guard_drop/breach_exceeds_cap` 은 확률적이다. 두 series 는
  **「결정론 fixture 검증 · 프로덕션 미확인」으로 명시 유지**한다.
- `degraded_input/reference_price_unavailable` 유도 — 유일 경로가 제3자 공개 API 남용. **영구 제외.**
- BL-581 수리 — 측정만 (위 §0).
- 새 metric 래퍼 / 새 counter / 마이그레이션 / 새 킥오프 파일.

---

## 2. [BL-580] 고장 주입 결과 — 9곳 판정, **9곳 전부 「수리함」**

사전등록한 3라벨(+영구 제외)로 전건 분류했다. **「가드 없이 유지」가 0곳이다** — 그 자체가 결과다.
BL-580 이 산문으로 「감쌀 필요 없다」고 적어 둔 근거는 **주입해 보니 전건 틀렸다.**

| ID  | 사이트                               | 주입 귀결 (실측)                                                                 | H   | 라벨   |
| --- | ------------------------------------ | -------------------------------------------------------------------------------- | --- | ------ |
| B1  | `trading/router.py` cancel           | `OSError` 가 핸들러를 탈출 — 확정된 취소가 **HTTP 5xx**                          | H1  | 수리함 |
| B2  | `trading.py` watchdog rejected       | task 예외 — 확정된 거절 전이가 **FAILED 로 기록**                                | H1  | 수리함 |
| B3  | `trading.py` watchdog cancelled      | 위와 같음                                                                        | H1  | 수리함 |
| B4  | `trading.py` cancel_order            | task 예외 + **거래소 취소를 남기는 유일한 로그 유실**                            | H1  | 수리함 |
| A1  | `live_signal.py` exchange_missing    | 한 줄 아래 가드 **미도달**(counter 차분 0) + 그 tick 등재 판단 소실              | H4  | 수리함 |
| A2  | `live_signal.py` stand_down          | ★**stand-down 미실행** — `cancel_order` 0회. 잘못된 전제 위 주문이 거래소에 남음 | H4  | 수리함 |
| A3  | `live_signal.py` degraded_input      | 가드 미도달 + 등재 판단 소실                                                     | H4  | 수리함 |
| A4  | `live_signal.py` reprobe breach cap  | 가드 미도달                                                                      | H4  | 수리함 |
| C1  | `live_signal.py` position divergence | ★**세션은 죽었는데 고지가 안 나간다** — `_fire_divergence_alert` 0회             | H2  | 수리함 |

★**발화 가능 대조(§G1.1 규율 2a)** — H1 4곳 · H2 1곳 · H4 4곳으로 셋 다 실재한다.
**H3(commit 앞 rollback 유발)은 이번 9곳에 0건이다 — 이 회차에서 공허하다.** 직전 회차가
찾은 H3 4곳은 이미 수리됐고, 이번 스윕 대상에는 없었다.

### 2.1 ★★S1 이 놓친 2곳을 수리 중에 발견했다 — **총 12곳**

A4 를 고치고도 테스트가 red 였다. 원인은 **같은 `breach_capped` 라벨을 쓰는 자리가 하나 더**
있었기 때문이다(`plan.divergences` 루프). 그 둘(`breach_capped` · `breach_with_resting`)은
`_count_safely` **바로 뒤**에 있어서 **앞만 보는 S1 이 구조적으로 못 잡는다.**

⇒ **S1 은 「가드 앞의 raw」만 본다. 「가드 뒤의 raw」는 못 본다.** 이 비대칭을 적어 둔다.
던지면 `plan.divergences` 루프가 죽어 **남은 leg 의 드롭 계상과 로그가 통째로 사라진다.**

★**직전 회차와 같은 형태의 재발이다** — 「고쳤다」와 「그 종류를 다 고쳤다」는 다른 문장이다.
이번엔 G6 가 아니라 **내 테스트가** 잡았다(A4 가 red 로 남아 있었다).

**수리 12곳 · 새 추상 0** — 전건 기존 관용구(`record_metric_safely` · `_count_safely`).
census **141 → 129**(`(파일, metric)` 45키 → 43키).

### 2.2 ★`metrics_multiproc.py:35` = 영구 제외

`record_metric_safely` 자신의 실패 fallback 이다. 감싸면 **재귀**한다. 이미 자체 중첩
`try/except` 안이고 DB write·후속 훅·HTTP 표면이 없다. **census 129 에 남긴다.**

---

## 3. [BL-582] 도달성 재판정 — **「7종 도달 불가」 중 2종 반증**

### 3.1 반증

BL-582 의 근거 문장은 「`PendingOrderSnapshot` 의 exit 3필드가 **항상 `None`**」이었다.
**엔진을 직접 돌려 반증했다.**

| Pine 형태                                 | 엔진 산출 (`run_live` 실측)                                              |
| ----------------------------------------- | ------------------------------------------------------------------------ |
| 반대 방향 same-id 재발행 + `stop`/`limit` | `target=-8` · `take_profit=192` · `stop_loss=64`                         |
| 반대 방향 same-id 재발행 + `trail_points` | `target=-8` · `trailing_stop=100` · `stop_loss=None`                     |
| 같은 방향 재발행 (음성 대조)              | 브래킷은 실리지만 계획기가 `quantity==0` 에서 `continue` ⇒ 게이트 미도달 |

⇒ `guard_drop/bracket_trailing_only` · `guard_drop/bracket_tp_size_mismatch` 는
**도달 가능**이다. 도달 불가 **7종 → 5종**(`other` 5종만 남는다).

★**올바른 서술은 BL-523 쪽이었다** — 「현재 코퍼스 미발현」. 발현 조건 3개를 확정했다:
(a) 같은 `trade_id` 가 이미 열려 있고 (b) 그 id 에 `strategy.exit` 브래킷이 붙고
(c) 재발행이 **반대 방향**. (c) 가 이번 회차의 새 사실이다.

### 3.2 ★메운 seam — 기존 테스트는 게이트만 증명했다

`test_live_conditional_divergence_labels.py` 의 두 테스트는 게이트 라인을 **손조립**
`_pending(take_profit=...)` 으로 구동한다. 그래서 「게이트는 동작한다」는 증명하지만
「**엔진이 그 입력을 만들 수 있는가**」는 증명하지 않았다. BL-582 가 도달 불가로 적은 근거가
정확히 그 미검증 구간이다. 새 테스트는 `run_live` 산출물을 **그대로** reconcile 루프에 흘린다.

### 3.3 `other` 5종 — 구조 전제 게이트

전 호출부의 reason 가능값을 **bounded def-use** 로 해소해 allowlist 부분집합임을 단언한다.
해소 실패는 **통과가 아니라 red** 다.
★설계 중 `None` 갈래를 발견했다 — `stand_down_reason` 은 `hedge_mode | shared_account_symbol |
**None**` 이고 `None` 은 `other` 로 정규화된다. 그것을 막는 유일한 근거가 호출부의
`if stand_down_reason is not None:` 가드라서, 오라클이 **그 가드를 구조로 요구**하게 했다.

---

## 4. 표적 변이 — 7건 전건 판별 · 음성 대조 1건 green

문자열 치환 + **sha256 복원 대조**(전건 일치). `git checkout` 미사용. 전체 pytest 와 분리 실행.

| ID  | 변이                                                    | 결과              | 기대와 일치 |
| --- | ------------------------------------------------------- | ----------------- | ----------- |
| M1  | 새로 감싼 자리를 raw 로 복귀 → census                   | RED (3 failed)    | ✓           |
| M2a | `router.py` 언랩 → B1 고장 주입 테스트                  | RED               | ✓           |
| M2b | `live_signal.py` stand_down 언랩 → A2                   | RED               | ✓           |
| M3  | allowlist 밖 리터럴 주입 → `other` 게이트               | RED               | ✓           |
| M3b | `is not None` 가드 제거 → `other` 게이트                | RED (3 failed)    | ✓           |
| M4a | 도달성 fixture 에서 `limit=192` 제거                    | RED               | ✓           |
| M4b | 계획기의 exit 레벨 pass-through 절단 → 엔진↔게이트 seam | RED               | ✓           |
| N1  | 무관 파일 주석만 (음성 대조)                            | GREEN (16 passed) | ✓           |

★★**사전등록한 M2 는 틀린 변이였다 — 실행 전에 발견해 교체했다.**
원안은 「고장 주입 테스트의 폭파 대상이 안 던지게 바꾼다 → red」였는데, 그렇게 하면 코드가
정상 동작하므로 테스트는 **green** 이 된다. 판별력이 0인 변이다. 역방향(**프로덕션 언랩**)으로
바꿨고, 그것이 실제로 판별한다(M2a·M2b). **교체 사실과 이유를 여기 남긴다 — 사전등록을
조용히 고치지 않는다.**

★M3b·M4b 는 사전등록에 없던 **추가** 변이다. 각각 「구조 전제 게이트가 전제를 실제로 지키는가」와
「seam 테스트가 seam 을 실제로 덮는가」를 물었다.

---

## 5. ★★부수 발견 — 테스트 스위트가 **실행 순서에 따라 red/green 이 바뀐다**

내 새 테스트 3건이 `test_live_conditional_divergence_labels.py` **뒤에 오면** 실패했다.
증상은 `_async_cancel_order` 가 `skipped: not_found` 를 내는 것 — 방금 fixture 가 만든 DB 행을
task 가 못 찾는다.

★**내 테스트 문제가 아니다.** 대조로 확정했다 — **내가 건드리지 않은 기존
`tests/trading/test_cancel_order_task.py` 도 같은 순서에서 2건 실패**한다(단독 실행은 통과).

```
uv run pytest tests/trading/test_cancel_order_task.py                          → 2 passed
uv run pytest tests/tasks/test_live_conditional_divergence_labels.py \
              tests/trading/test_cancel_order_task.py                          → 2 failed
```

`pytest-randomly` 가 순서를 섞으므로 **이 red 는 우연히 나타났다 사라진다.** 전체 스위트가
green 인 것은 그날의 순서가 운이 좋았다는 뜻일 수 있다. ⇒ **[BL-583] 등재.**
뿌리는 이번 회차에서 규명하지 않았다(범위 밖) — 재현 명령과 대조를 등재해 둔다.

---

## 6. 게이트

| 게이트                 | 결과                                                              |
| ---------------------- | ----------------------------------------------------------------- |
| BE pytest              | **3848 passed / 46 skipped** (baseline 3835 + 신규 13)            |
| ruff                   | `All checks passed!` (전체 경로 `.`, 파이프 없음)                 |
| mypy                   | `Success: no issues found in 214 source files`                    |
| FE typecheck/test/lint | **미실행** — FE diff 0. 미실행을 미실행이라고 적는다(무음 금지)   |
| `scripts/bl-audit.sh`  | ✓ 3면 정합 · active 152 / 전체 240 (BL-583 신설로 +1) · UNKNOWN 0 |
| `make docs-audit`      | ✓ 링크·폐기 경로·줄길이 상한 clean                                |
| 마이그레이션           | 신규 0 (head `20260801_0001` 불변)                                |

**신규 테스트 13건**
`test_router_cancel_metric_failure.py` 1 · `test_trading_task_metric_failure.py` 3 ·
`test_live_signal_metric_failure.py` 5 · `test_conditional_divergence_reachability.py` 4.

★**커밋 후 다시 잰다** — pre-commit 이 `ruff format`·`prettier --write` 를 돌린다.
직전-직전 회차가 「커밋 전 측정치로 PASS」라고 썼다가 codex BLOCKING 을 받았다.

★**사전등록 시점 증명** — §1 은 소스 파일을 **한 줄도 고치기 전에** 작성했고 그 상태로
codex G1 검증을 받았다(findings 7건 → §1.35). 커밋 순서도 그것을 따른다.

---

## 7. 다음 회차로 넘기는 것

1. **[BL-583]** — 스위트 순서 의존. 재현 명령과 **배제된 가설 2개**를 백로그에 적어 뒀다.
   ★이게 먼저다. 이 레포는 BE pytest 수치를 판정 근거로 쓴다.
2. **[BL-580] 잔여 129곳 중 아직 코드 독해인 것** — `order_service.py` 10곳 ·
   `trading.py` closed_pnl 7곳. 이번 회차가 명시 4곳을 **전건 반증**했으므로 같은 의심을 받아야 한다.
3. **[BL-582]** 반증된 2종의 프로덕션 발화 — 코퍼스에 발현 전략이 없어 전략 등록이 선행돼야 한다.
4. **[BL-576] 잔여 2종** — soak 미실시(사용자 결정). 「프로덕션 미확인」 유지.
