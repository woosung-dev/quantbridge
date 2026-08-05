# 2026-08-05 — 판별식을 확정하고, 라이브 재생의 눈을 실제로 재본다 (live-replay-visibility)

> 브랜치 `stage/live-replay-visibility` (main `4fd3fcdf` 에서) ·
> 코드는 `backend/scripts/` 오라클 + `backend/tests/` · **소크 무중단**(재고정 안 함).

## 무엇이 달라졌나

**판별식이 프록시에서 직접 측정으로 바뀌었다.** 「재무장 도장」(파이프라인이 조정을 끝냈나)
에서 **「직접 회복 검사」**(같은 스트림의 다음 평가에도 어긋나 있었나)로 교체했다.
바꾸기 **전에** 관측 전량에 적용한 표를 냈고, 게이트 판정은 **`FAIL` 유지 · 전 이력 실격
9 → 10** 이다 — 교체가 통과를 사지 않는다.

**그리고 이 회차의 착수 전제 두 개가 실측으로 반증됐다.** 아래 §0.

---

## 0. 착수 전제 반증 2건 — 재던 곳에 없었다

### 0.1 ★★★「Trust Layer 23테스트가 `run_live` 를 0회 부른다 ⇒ 라이브 재생이 갈라져도 CI 는 초록이다」

앞 절반은 참이고(Trust Layer 는 `run_backtest_v2` 를 몬다) **뒷 절반이 거짓**이다.

| 실측                                        | 값                                                                     |
| ------------------------------------------- | ---------------------------------------------------------------------- |
| Trust Layer 테스트 수                       | **52** (P-1 12 + P-2/P-3/envelope 32 + 변이 오라클 8). 「23」은 낡았다 |
| `tests/strategy/pine_v2/test_run_live_*.py` | **7 파일 · 89 테스트**                                                 |
| `run_live(...)` **직접 호출**               | **~90회 · 11개 파일**                                                  |
| 백테스트↔라이브 parity 오라클               | `test_run_live.py:239` 에 **이미 있다**                                |

[BL-595] 가 바꿀 두 지점도 **이미 못 박혀 있다**:

- `test_run_live_pending_orders.py:292` — 엔진이 조건부 stop 을 **혼자 시뮬해 포지션을 연다**
  (= `cc19abd2` 형, 엔진이 앞섬)
- `test_run_live_position_epoch.py:241` — 재생이 포지션을 들고 있으면 **거래소 원장 seed 를
  버린다**(`strategy_state.py:358` `if not legs or self.open_trades`) (= `39731d57` 형의 차단자)

⇒ 「`run_live` 를 태우는 테스트를 새로 만들어라」를 그대로 했으면 **이 레포가 4회 연속 밟은
판별력 0 하네스**가 됐다. 사용자 판정으로 **변이 배터리**로 대체했다(§3).

### 0.2 「현행 코드의 실질 MTBF 는 1~2.3시간」

**n=2 의 산물이다.** 실측(`trading.live_signal_sessions`):

| 세션       | 수명           | 종료 사유             |
| ---------- | -------------- | --------------------- |
| `39731d57` | 38분           | `position_divergence` |
| `cc19abd2` | 138분          | `position_divergence` |
| `a16aa640` | **5시간 13분** | **생존 중**(사망 0)   |

세 번째가 이미 그 밴드를 넘겼고 **우측 절단**이라 MTBF 를 재추정할 표본이 못 된다.
「1~2.3h」를 사실로 인용하지 않는다.

---

## 1. 판별식 교체 — 봉경계식 → 재무장 도장식 → **직접 회복 검사**

### 1.1 왜 재무장식을 버리나 — codex P1 「TTL 없음」이 미수리로 남아 있었다

재무장 도장 `H` 뒤에 체결 `F` 가 오면 그 발산이 **이후 영영 낫지 않아도** `F >= H` 인 한
계속 `replay_lag` 이다. **그 식은 회복을 확인하지 않는다.** 직전 회차가 그것을 문서에
「남는 위험」으로 적고 다음 후보로 **직접 회복 검사**를 지목한 채 끝났다.

### 1.2 규칙 (`PREDICATE_VERSION = 2026-08-05-recovery-ratchet`)

관측 `T`(세션 `S` · 심볼 `Y` · 봉 간격 `I`), 코퍼스 지평 `C`, 근접 지평 `Hn = 1.5 · I`:

| 조건                                          | 라벨          | 뜻                                        |
| --------------------------------------------- | ------------- | ----------------------------------------- |
| 같은 `(S,Y)` 의 **다음 관측**이 `T + Hn` 이내 | **`phantom`** | 바로 다음 평가에도 어긋나 있었다          |
| 다음 관측이 있고 `T + Hn` 밖                  | `replay_lag`  | 그 사이 나았다 — 뒤의 것은 새 에피소드    |
| 다음 관측 없음 + `T + Hn` 안에 **자동 사망**  | **`phantom`** | 낫지 않았다 — 죽어서 관측이 끊겼다        |
| 다음 관측 없음 + `T + Hn` 안에 `user_stopped` | (판정 불가)   | 우리가 껐다 — 회복 여부를 알 수 없다      |
| 다음 관측 없음 + `C > T + Hn`                 | `replay_lag`  | 충분히 지켜봤고 다시 안 왔다              |
| 그 외 (**로그 창이 거기서 끝난다**)           | (판정 불가)   | → `rearm_label` → `horizon_label` 로 강하 |

**원장을 아예 안 본다** — `Order.filled_at`(terminal 시각)·`filled_quantity`·반전 수량 판정이
전부 빠진다. 직전 회차가 codex 에게 지적받은 `is_filled` 계열 결함이 이 식의 **입력이 아니다.**

### 1.3 ★바꾸기 **전에** 관측 전량에 적용했다 (n=19, 교체 시점 코퍼스)

| 창                                       | n      | 회복식                 | 재무장식               | 봉경계식               | 사망  |
| ---------------------------------------- | ------ | ---------------------- | ---------------------- | ---------------------- | ----- |
| A `08-02T13:19 ~ 08-04T06:38` (아카이브) | 11     | phantom 4 · lag 7      | phantom 4 · lag 7      | phantom 4 · lag 7      | 2     |
| B `08-04T15:51 ~ 08-05T01:21` (워커로그) | 8      | **phantom 4 · lag 4**  | phantom 3 · lag 5      | phantom 7 · lag 1      | 2     |
| **합계**                                 | **19** | **phantom 8 · lag 11** | **phantom 7 · lag 12** | **phantom 11 · lag 8** | **4** |

바뀌는 것은 **1건뿐**이다 — `39731d57@16:24:01`, `replay_lag` → **`phantom`**.

### 1.4 왜 이 교체가 「통과를 사는」 교체가 아닌가 — 넷으로 확인한다

| #   | 검사                                                                         | 결과                                                                                                           |
| --- | ---------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| ①   | **방향** — phantom 이 늘어야 한다(게이트의 위험 축은 fail-open)              | 7 → **8** ✓                                                                                                    |
| ②   | **집합 포함** — 회복식 phantom ⊇ 재무장식 phantom (아무것도 사면하지 않았다) | **진부분집합** ✓ — ★단 이건 n=19 의 **관측**이지 성질이 아니었다. codex 반례 뒤 **래칫**으로 성질이 됐다(§6.1) |
| ③   | **out-of-sample** — 규칙은 창 B 에서 유도했다. 창 A 는?                      | **11/11 봉경계식과 일치** ✓                                                                                    |
| ④   | **게이트 실판정**                                                            | **`FAIL` 유지** · 전 이력 실격 **9 → 10** ✓                                                                    |

★①은 「7→8」이라는 총계만으로는 부족하다 — 하나를 빼고 둘을 넣어도 8이 된다. 그래서 ②를
**집합 연산으로** 못박았다.

### 1.5 ★추가된 그 1건은 직전 회차가 **스스로 정정한** 관측이다

직전 회차는 「`replay_lag` 12/12 생존」이라고 썼다가 codex 지적으로
「**11건은 회복했고 1건은 사망 직전 tick 이었다**」로 정정했다. 그 1건이 `16:24:01` 이다.
회복식은 그것을 **처음부터** `phantom` 으로 판정하므로 **정정할 문장이 생기지 않는다** —
채택 라벨 기준으로 `replay_lag 11/11 생존`이 그냥 참이다.

### 1.6 ★★대가 — 사망 상관이 더 이상 독립 검사가 아니다 (숨기지 않는다)

회복식의 `phantom` 은 「다음 tick 도 어긋났다」이고 프로덕션 킬은 「연속 2회 **판정된** tick」
이다. **거의 같은 신호**라 `deaths == deaths_labelled_phantom` 이 동어반복에 가까워진다.

⇒ `death_correlation_holds` 를 **`rearm_label`(없으면 `horizon_label`) 기준**으로 계산하도록
바꿨다. 재무장식은 **원장**에서, 사망은 **tick 연속성**에서 오므로 그 둘만이 서로 독립이다.
채택 라벨 기준 값은 `adopted_*` 로 **따로** 보고한다(지우지 않는다 — 둘이 갈리면 그게 정보다).

### 1.7 ★남는 위험 둘 — 둘 다 테스트로 눈금을 달았다

**(a) `Hn = 1.5 · I` 는 문턱이다.** tick 이 한 번 건너뛰면(`probe_failed`) 다음 발산이
`2·I` 뒤에 와서 `replay_lag` 으로 기운다(fail-open). 그래서 분리를 **매 실행 출력에 찍는다**:

| 눈금                                         | 골든(n=19)   | 라이브(현 워커 로그) |
| -------------------------------------------- | ------------ | -------------------- |
| `max_phantom_gap`                            | **60.12초**  | **60.02초**          |
| `min_replay_lag_gap`                         | **180.20초** | **179.94초**         |
| `ambiguous_gap_band`(tick 한 번 건너뜀 구간) | **0건**      | **0건**              |

★**「애매대 0건」이 뜻을 가지려면 채워질 수 있어야 한다** —
`test_a_skipped_tick_gap_lands_in_the_ambiguous_band` 가 120초 간격을 넣어 **1건으로
세어지는 것을 증명**한다. 그게 없으면 0은 「그런 일이 없다」가 아니라 「못 센다」다.

★**첫 초안의 애매대 상한은 `3·I` 였고 돌리자마자 1건을 잡았다** — `179.94초 = 2.999·I`.
그건 건너뛴 tick 이 아니라 **정상적인 3봉 간격**이고, 내가 상한을 근거 없이 잡아서 난
거짓 경고였다. 「한 번 건너뜀」이라는 원래 우려를 그대로 쓰면 상한은 `2.5·I` 다.
★경고를 없애려고 옮긴 게 아니라는 근거 — `max_phantom_gap`/`min_replay_lag_gap` 은
가공하지 않은 원본이고 이 계수와 **무관하게** 계속 찍힌다.

**(b) 로그 절단.** 창의 마지막 관측은 후속자가 아직 없어 **판정 불가**이고 종전 식으로
내려간다(fail-open). 게이트가 아카이브 verdict 를 **합집합**으로 모으므로 뒤 실행이 같은
`at` 을 `phantom` 으로 다시 매기면 `window_start` 가 **소급 정정**된다. 그건 지금까지
산문이었고 **코드로 못박았다** —
`test_a_later_archive_relabelling_the_same_observation_disqualifies_it` +
음성 대조 `test_the_union_never_retracts_a_phantom_once_archived`(방향은 한쪽뿐이다).

★★**정정 — 초안은 「노출 ≤ 30분」이라고 썼는데 그건 컨테이너 수명 안에서만 참이다**
(codex 적발, §6-②). `soak-gate.sh:177` 은 매 실행이 **현재 컨테이너의** `docker logs` 만
분류하고 옛 아카이브를 `--events-json` 으로 되먹이지 않는다. **워커가 재생성되면 그 tail
관측은 새 입력에 없고** 아카이브의 `replay_lag` 이 영구히 남는다. 정확한 노출 =
**컨테이너 수명당 최대 1건**. 그리고 위 두 테스트가 동결하는 것은 **게이트의 합집합
의미론**이지 「파이프라인이 실제로 재판정한다」가 아니다 — 그건 구현돼 있지 않다.

### 1.8 알려진 fail-open 1건 — 수리 안 함, 등재만

`soak_gate_predicate.py:191` 은 `label == "phantom"` 만 실격으로 보고 **모르는 라벨을
조용히 무해 취급**한다(`unattributed` 포함). 이번 회차는 새 라벨을 도입하지 **않았으므로**
(판정 불가는 종전 식으로 강하) 도달하지 않는다. 신규 [BL-596] 로 등재한다.

### 1.9 아카이브 판 이동

`PREDICATE_VERSION` 을 올렸으므로 `.soak/phantom-*.json` **18벌**을
`.soak/superseded-2026-08-05-rearm/` 으로 옮겼다.
★**이동 전에 커버리지 손실을 확인했다** — 18벌 전부 `log_from` 이 컨테이너 기동
(`2026-08-04T15:51:23`)이고 게이트는 매 실행이 로그를 통째로 재분류하므로, 새 아카이브가
같은 구간을 다시 덮는다. 실측 손실 **0**.

---

## 2. 게이트 판정 (커밋 후 재측정 전, 이동 직후)

| 항목         | 이동 전(재무장식)      | 이동 후(회복식)                    |
| ------------ | ---------------------- | ---------------------------------- |
| 판정         | **FAIL 실격** (exit 1) | **FAIL 실격** (exit 1)             |
| C3 (창 안)   | 3건                    | 3건                                |
| 누적 / 연속  | 0h / 0h                | 0h / 0h                            |
| 전 이력 실격 | 9건                    | **10건** (`16:24:01 phantom` 추가) |

---

## 3. ★사전등록 변이 배터리 — 기존 89테스트가 **무엇을 실제로 보는지** 잰다

§0.1 로 「새 테스트를 짓는다」가 폐기됐으므로, **기존 망의 판별력을 주입으로 잰다.**
아래 표는 **실행 전에 커밋한다.** 예측이 빗나가는 것 자체가 산출물이다.

★주입은 `backend/src` 를 **일시적으로** 고치고 매번 원복한다(커밋하지 않는다).
소크는 `.soak/src` 스냅샷을 mount 하므로 영향 0 이다(`soak-stack.sh status` 실측).
원복은 **역패치**로 한다 — `git checkout` 은 미커밋 변경을 날린다(이 레포의 기록된 함정).

| #   | 변이 (달리 명시 없으면 `event_loop.py`)                                        | 예측 red                                                              |
| --- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------- |
| M1  | `run_historical(..., strict=False)` → `strict=True`                            | 런타임 오류 surface 경로                                              |
| M2  | `if ... e.broker_filled: continue` 제거 (BL-560)                               | `test_pending_fill_flip_close_is_not_dispatched`                      |
| M3  | `position_epoch_bar == 0 → None` 붕괴 제거                                     | `test_run_live_position_epoch.py` off-by-one                          |
| M4  | 마지막 봉 필터 제거 — 모든 봉 이벤트 방출                                      | `test_run_live.py` signal 목록 단언                                   |
| M5  | `_pending_fills_blocked_by_session` 무력화                                     | `test_desired_set_is_empty_when_carried_into_disallowed_session`      |
| M6  | `_quantize_amount` 생략                                                        | `test_pending_orders_are_quantized_to_api_precision`                  |
| M7  | `strategy_state.py` seed 가드의 `or self.open_trades` 제거                     | `test_ledger_seed_is_idempotent_when_replay_already_holds_a_position` |
| M8  | `target_position` 을 float 공간에서 합산                                       | `test_target_position_sums_same_side_in_decimal_space`                |
| M9  | `_to_decimal` 의 `<= 0` / NaN 가드 제거                                        | `test_run_live_drops_invalid_pending_order_legs`                      |
| M10 | ★**BL-595 형 A** — 조건부 stop 을 봉 내 `high/low` 가 아니라 `close` 로만 체결 | **살아남을 것으로 예측**(치명 구멍)                                   |
| M11 | ★**BL-595 형 B** — `open_trades` 가 있어도 원장 seed 로 덮어쓴다               | M7 의 거울 — 같은 테스트가 잡을 것                                    |
| M12 | `run_live` 가 `strategy_state.warnings` 에 append                              | `test_run_live_consistent_with_run_historical_final_state`            |

**판정 절차 (거짓 green 방지):**

1. 부분 스위트(`tests/strategy/pine_v2/` + `tests/tasks/`)로 먼저 돌린다.
2. ★**부분에서 살아남은 변이는 전체 스위트로 재판정**한다 — 죽이는 테스트가 부분 밖에
   있으면 「구멍」이 거짓이 된다.
3. **죽은 변이 = 이미 눈이 있다 → 테스트를 쓰지 않는다. 보고만 한다.**
4. **살아남은 변이 = 진짜 구멍 → 그때만** 테스트를 쓰고 **같은 변이를 다시 주입해 red 를
   증명**한다. 판별력이 없으면 **커밋하지 않고 지운다.**

### 3.1 결과 — **12/12 판정. 신규 테스트는 0건이다.**

| #   | 판정                       | 죽인 테스트(첫 실패 / 실패 수)                                        | 예측        |
| --- | -------------------------- | --------------------------------------------------------------------- | ----------- |
| M1  | **KILLED**                 | `test_run_live_propagates_runtime_errors` (1건)                       | 적중        |
| M2  | **KILLED**                 | `test_pending_fill_flip_close_is_not_dispatched` (2건)                | 적중        |
| M3  | ~~SURVIVED~~ **등가 변이** | — (행위가 안 바뀐다. 아래 §3.2)                                       | **무효**    |
| M3b | **KILLED**                 | `test_position_opened_on_epoch_bar_survives` (1건)                    | 적중(파일)  |
| M4  | **KILLED**                 | `test_no_signals_when_entry_in_earlier_bar`                           | 적중(파일)  |
| M5  | **KILLED**                 | `test_desired_set_is_empty_when_carried_into_disallowed_session`      | 적중        |
| M6  | **KILLED**                 | `test_pending_orders_are_quantized_to_api_precision` 포함 **4건**     | 적중        |
| M7  | **KILLED**                 | `test_ledger_seed_is_idempotent_when_replay_already_holds_a_position` | 적중        |
| M8  | ~~SURVIVED~~ **등가 변이** | — (행위가 안 바뀐다. 아래 §3.2)                                       | **무효**    |
| M8b | **KILLED**                 | `test_target_position_sums_same_side_in_decimal_space` (1건)          | 적중        |
| M9  | **KILLED**                 | `test_run_live_drops_invalid_pending_order_legs`                      | 적중        |
| M10 | **KILLED**                 | **12건** — 아래 §3.3                                                  | ★**빗나감** |
| M11 | **KILLED**                 | `test_ledger_seed_is_idempotent_when_replay_already_holds_a_position` | 적중        |
| M12 | **KILLED**                 | `test_run_live_consistent_with_run_historical_final_state`            | 적중        |

⇒ **행위를 실제로 바꾸는 변이 12건이 전건 죽었다. 기존 망에 구멍이 없다** — 적어도 내가
찔러 본 12곳에는. **그래서 새 테스트를 쓰지 않았다.** 여기서 하나라도 짓는 것이 곧 이 레포가
4회 연속 밟은 판별력 0 하네스다.

★**1단계는 `-x` 라 첫 실패만 보인다** — 「죽었다」는 알 수 있어도 「내가 지목한 테스트가
잡았다」는 알 수 없다. 그래서 M1·M2·M6·M10·M3b·M8b 는 **`-x` 없이** 다시 돌려 실패 전량을
모았다. 예측한 테스트가 실제로 그 목록에 있다.

### 3.2 ★내 변이 2건이 **판별력 0** 이었다 — 「살아남았다」가 아니라 「행위가 안 바뀌었다」

이 레포가 4회 연속 밟은 함정과 같은 것이고, **이번엔 결과를 오독하기 직전에 잡았다.**

| 변이 | 왜 등가인가                                                                                                                                            |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| M3   | `position_epoch_bar == 0 → None` 붕괴를 없애면 `discard_state_before_epoch()` 가 **bar 0 에서** 돈다. 그 시점엔 열린 거래도 손익도 없어 **no-op** 이다 |
| M8   | `Decimal(str(x))` → `Decimal(repr(float(x)))`. **Python 3 에서 float 의 `str` 과 `repr` 은 같다** — 바이트가 같다                                      |

★**「SURVIVED」를 구멍으로 적었다면 있지도 않은 구멍을 두 개 보고했을 것이다.** 등가 변이는
구멍의 증거가 **아니다** — 아무것도 안 바꿨으니 잡힐 것도 없다. 행위가 실제로 바뀌는
M3b(off-by-one `>=` → `>`) · M8b(진짜 float 공간 합산)로 교체하니 **둘 다 예측한 테스트가
잡았다.**

★부수 관측 — M3 이 등가라는 것은 `if position_epoch_bar == 0: position_epoch_bar = None`
가드가 **행위상 사문**이라는 뜻이다(방어·문서 목적으로는 유효). 지우지 않고 적어만 둔다.

### 3.3 ★★★가장 큰 산출물 — M10 예측이 빗나갔고, 그 이유가 「구멍 2」의 진짜 반증이다

M10 = **[BL-595] 형 A** 의 최소 모형이다(조건부 stop 을 봉 내 `high/low` 로 체결하지 않고
봉이 트리거를 **열자마자** 넘은 경우만 체결). 「기존 망은 라이브를 안 보니 살아남을 것」으로
예측했다. **12건이 죽였다:**

| 파일                              | 테스트                                                                                                                         |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `test_run_live_pending_orders.py` | `test_internal_pending_stop_fill_opens_trade_without_live_signal` · `test_internal_pending_stop_fill_never_leaks_fill_signal`  |
| `test_run_live_broker_flip.py`    | `test_broker_flip_close_side_would_have_matched_the_filled_leg` · `test_broker_flip_still_records_the_close_in_the_ledger`     |
| `test_run_live_fill_timing.py`    | `test_stop_entry_is_unaffected_by_fill_timing`                                                                                 |
| `test_pivot_and_stop_order.py`    | `test_stop_long_fills_when_high_breaks_above` · `test_stop_short_fills_when_low_breaks_below` · `test_stop_plus_mintick_usage` |
| `test_leverage_engine.py`         | `test_margin_gate_skips_stop_fill_and_removes_pending_order`                                                                   |
| `test_sltp_integration.py`        | `test_real_s1_pbr_sltp_pine_executes_and_sltp_fires` · `test_same_bar_dual_stop_trigger_is_deterministic`                      |
| **`test_trust_layer_parity.py`**  | ★**`test_p3_execution_metrics_match_golden[s1_pbr]`**                                                                          |

★★★**Trust Layer 골든이 잡았다 — `run_live` 를 한 번도 안 부르면서.** 이유는 단순하다:
조건부 체결 로직은 `strategy_state.check_pending_fills` 에 있고 그건 **백테스트와 라이브가
공유하는 머니-패스**다. ⇒ **「어느 진입점을 호출하는가」와 「어느 코드를 덮는가」는 다른
질문이고, 「구멍 2」는 그 둘을 뒤섞었다.**

★**그리고 이건 [BL-595] 에 설계 제약을 하나 준다.** 공유 코드를 고치면 **백테스트 골든이
red 가 된다** — BL-595 가 「백테스트 경로 byte-identical 을 못박아야 한다」고 적어 둔 바로 그
위험이 **이미 집행되고 있다**. ⇒ 대칭 수리는 `check_pending_fills` 를 바꾸는 것이 아니라
**라이브 전용 경로에서만** 갈라져야 한다. 위 12건이 그 수리가 **의식적으로 뒤집어야 할
목록**이다.

---

## 4. 게이트 (커밋 후 실측)

_(final-gates 실행 후 채운다.)_

## 5. 소크 상태 (회차 끝)

**세션 `a16aa640` 생존 중 — 약 6시간 52분** (T0 `2026-08-05T00:34:22Z`).
고정 커밋 **`f5f06886`** 불변(`origin/main` 의 조상 YES) · **재고정 안 함** · 활성 세션 1.

| 항목              | 값                                                                   |
| ----------------- | -------------------------------------------------------------------- |
| 게이트 판정       | **`FAIL 실격`** (exit 1)                                             |
| C3 (열린 창 안)   | 3건 — `18:50`·`18:51` phantom + `18:51` auto_death (전부 `cc19abd2`) |
| C1 누적 / C2 최장 | **0h / 168h** · **0h / 24h**                                         |
| C4 표본 공백 / C5 | ✓ 0건 / ✓ 전건(db_ok·stack_pinned·phantom_archive·darkness_computed) |
| 전 이력 실격      | **10건** (교체로 `16:24:01 phantom 39731d57` 추가)                   |
| 관측 코퍼스       | 창 A 11 + 워커 로그 21 = **32건**(회차 중 20 → 21 로 자랐다)         |

**왜 `FAIL` 인가 — 이건 결함이 아니라 설계대로다.** 열려 있는 귀속 구간이 마지막 실격보다
**앞서** 시작해 애초에 계상되지 않는다(`soak_gate_predicate.py:405`). 새 창은
`scripts/soak-stack.sh up` 이 여는데, 그건 「인지했고 **고쳤다**」는 명시적 행위이므로
**[BL-595] 수리 커밋 뒤에** 한다. 이 회차는 `backend/src` 를 0줄 고쳤으므로 열지 않았다.

★**회차 중 소크는 한 번도 안 끊겼다.** 변이 주입이 `backend/src` 를 12번 고쳤지만 워커는
`.soak/src` 스냅샷을 mount 하므로 영향이 0 이다(설계대로 작동했다는 첫 실증).
★단 **주입 도중 셸 타임아웃으로 프로세스가 죽어 변이 1건이 트리에 남은 적이 있다**
(`finally` 가 SIGKILL 을 못 받는다). 매번 `git status` 로 확인했고 즉시 원복했다 —
2단계 러너는 `assert` 로 원복을 검증한다.

---

## 6. ★★★codex 적대 리뷰 — P1 2건 + P2 3건, **전건 처분**

세 회차 연속 P1 이 나왔다. 그리고 이번 둘은 **정확히 이 회차가 막으려던 것**이다 —
「교체가 게이트를 관대하게 만드는 경로」.

| #   | 지적                                                                   | 판정        | 처분                                       |
| --- | ---------------------------------------------------------------------- | ----------- | ------------------------------------------ |
| ①   | **P1** 새 식은 단조롭게 엄격하지 않다 — `probe_failed` 반례            | ✅ **실재** | **코드 수리(래칫) + 전용 테스트 2건**      |
| ②   | **P1** 「소급 정정」이 컨테이너 경계에서 거짓                          | ✅ **실재** | **문서 정정**(노출 경계를 정확히 다시 씀)  |
| ③   | **P2** `corpus_end` 가 Docker 가 아니라 앱 줄 정규식에서 온다          | ✅ **실재** | **코드 수리** — `--corpus-end` 신설 + 전달 |
| ④   | **P2** 테스트가 독립 검증이 아니다 · `ambiguous_gap_band` 는 게이트 밖 | ✅ **실재** | 문서 정정 + ①의 테스트가 부분적으로 닫는다 |
| ⑤   | **P2** 「변이 12/12 ⇒ 신규 테스트 0」의 근거 범위가 틀렸다             | ✅ **실재** | 문서 정정(§6.3)                            |

### 6.1 ①이 가장 크다 — 내 「진부분집합」은 **관측이지 성질이 아니었다**

`probe_failed` 가 나면 그 tick 은 **`direction` 줄을 안 남기고** strike 만 보존한다
(`live_signal.py:725`). 그러면 다음 관측이 `T + 2·I` 에 오고 회복식은 그걸 `replay_lag` 으로
접는다 — **재무장식이 `phantom` 이라 해도 채택이 덮어쓴다.** 실격 하나가 사라지고
`window_start` 가 앞당겨진다 ⇒ **누적이 늘고 P0 가 쉬워진다.**

내가 낸 증거 셋(`7→8` · 진부분집합 · 창 A 11/11)은 **전부 n=19 위의 관측**이라 이 반례를
배제하지 못한다. ★**「집합 연산으로 못박았다」고 썼지만 못박은 것은 그 19행뿐이었다.**

**수리 = 래칫.** 「판별식 교체는 앞 식이 실격시킨 것을 **사면할 수 없다**」:

```python
if rearm_label == "phantom":
    label = "phantom"
```

★**관측 19건에서는 아무것도 안 바뀐다**(이미 진부분집합이므로) — 그래서 골든이 지킬 수
없고 **전용 테스트**가 지킨다. codex 의 반례를 그대로 테스트로 얼렸고
(`test_the_recovery_label_cannot_pardon_a_rearm_phantom`), **음성 대조**도 같이 넣었다
(래칫은 바닥이지 상한이 아니다 — 없던 유령을 만들지 않는다). 없으면 `label = "phantom"` 를
무조건 박아도 통과한다.

### 6.2 ③ — 지평이 Docker 가 아니라 앱 줄에서 왔다

`soak-gate.sh` 는 `docker logs --timestamps` 로 `LOG_LAST` 를 **이미 갖고 있으면서**
분류기에는 타임스탬프 **없이** 파이프했다. 그래서 회복식의 지평이 celery prefix 정규식이
찾은 마지막 시각이 되고, 그 포맷은 timezone 을 버리고 UTC 로 강제한다. 무타임스탬프 후행
줄·포맷 변경·비-UTC 워커가 tail 판정을 조용히 바꾼다.
⇒ `--corpus-end` 를 만들어 게이트가 **Docker 의 값을 명시 전달**한다. 그 경로가 사라진다.

### 6.3 ⑤ — 「변이 12/12 ⇒ 신규 테스트 0」의 범위를 잘못 적었다

그 배터리는 **브리프의 deliverable 2**(「`run_live` 에 눈이 없다」)에 답한 것이다. 그 질문에
대해서는 결론이 옳다 — 라이브 재생 경로에 눈이 있다.

★**그러나 이 회차가 실제로 바꾼 것은 `run_live` 가 아니라 판별식과 게이트**다. 그 위험면
(로그 파싱 · `probe_failed` · 중복/동시 관측 · 코퍼스 끝 · timezone · 컨테이너 재시작 ·
아카이브 재판정 · 라벨 전달)은 **12개 변이 중 어느 것도 찌르지 않았다.** 실제로 codex 가
바로 그 면에서 P1 둘을 냈다. ⇒ **두 문장을 붙여 쓰면 안 된다.** 판별식 변경을 지키는 것은
골든 + 경계 테스트 + 래칫 테스트 + 게이트 재실행이고, 그건 변이 배터리와 **다른 장치**다.

### 6.4 ④ — 테스트의 독립성에 대해 정직하게

- 골든은 **변경 탐지기**이지 오라클이 아니다. 이벤트를 같은 표에서 만든다.
  독립 검사는 **사망 상관(재무장식 기준)** 하나뿐이고, 그것도 §1.6 의 이유로 약해졌다.
- `ambiguous_gap_band` 는 **게이트 입력이 아니다** — 분류기 stdout/`--json` 의 **보고용
  눈금**이다(`soak-gate.sh` 아카이브는 `{at, label, session_id}` 만 싣는다).
  「0건」은 「이 문턱이 아직 아무것도 자르지 않았다」는 관측이지 방어가 아니다.
- ①의 두 테스트는 **골든에서 유도되지 않은** 입력을 쓰므로 그만큼은 독립이다.

---
