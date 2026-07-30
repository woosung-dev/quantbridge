# close-mismatch-visibility — 재던 곳에 없었고, 진짜 신호는 이미 원장에 있었다 (2026-07-30)

> **스코프.** `entry-defer-convergence` 로 착수했으나 **G0 preflight 에서 전제가 반박**되어
> 사용자 승인으로 **청산측 포지션 불일치**로 전환했다. **마이그레이션 0 · 새 엔드포인트 0.**

---

## 1. 착수 전제가 반박됐다 — C2 는 유실 채널이 아니다

`docs/status.md` 의 다음 스프린트 블록은 `deferred_market_inflight`(C2)를
_"원장에 발자국을 남기지 않는 한 채널, 합의 75%"_ 로 지목했다. **셋이 독립적으로 그것을 반박했다.**

### 1.1 C2 는 「청산 신호가 난 tick 수」다

| 확인                                    | 값                                                      |
| --------------------------------------- | ------------------------------------------------------- |
| 세션 `98d86785` 의 `live_signal_events` | **9건 전량 `action='close'`**, 서로 다른 9 bar          |
| 같은 창의 C2 counter                    | **9** → **1:1 동치**                                    |
| 그 9개 bar 의 조건부 진입 주문          | **0건** (reconcile 이 실제로 스킵된 것은 맞다)          |
| C2 증가 시점                            | `live_signal.py:706` — `desired`(`:742`) 를 **읽기 전** |

`market_orders_in_flight` 의 실인자는 `bool(new_events)`(`:2270`)이고 `new_events` 는
`entry`/`close` 만 담는다(`event_loop.py:491-494`). **조건부 진입은 그 테이블을 거치지 않는다.**
그래서 stop-entry 전략에서 C2 는 **청산 횟수의 함수**이고, 증가 지점이 `desired` 를 읽기 전이라
**미룰 진입이 0건이어도 오른다.**

★**「합의 75%」는 유실의 75% 가 아니라 "이 전략이 진입보다 청산을 자주 했다" 였다.**

### 1.2 그 9번의 defer 는 대가가 없었다 (공개 kline 외부 오라클)

`api.bybit.com` + `api-demo.bybit.com` 의 `category=linear` 1m kline 151 bar — **두 호스트 불일치 0**.

| 신호                                                   | 값    |
| ------------------------------------------------------ | ----- |
| defer 창에 armed 였던 조건부 진입의 트리거 돌파        | **0** |
| defer 창 직후 등재된 주문의 트리거가 그 창 안에서 돌파 | **0** |
| armed 주문이 하나도 없던 defer 창                      | 5 / 9 |

★**이것은 하한이다.** 그 창의 engine desired 는 영속되지 않는다 —
`last_strategy_state_report` 는 매 tick **전면 덮어쓰기**(`live_signal_session_repository.py:294`)라
소급 복원이 구조적으로 불가능하다. **"유실 0" 이라고 쓰지 않는다.**

---

## 2. ★진짜 신호 — `110017` 두 갈래가 한 라벨에 묻혀 있었다

`trading.orders`, `reduce_only`, `state='rejected'`, retCode `110017`, **2026-07-26 ~ 07-30**:

| 갈래                                       |     n | 뜻                                |
| ------------------------------------------ | ----: | --------------------------------- |
| `reduce-only order has same side ...`      | **9** | ★★**엔진과 거래소가 반대 방향**   |
| `current position is zero`                 |    30 | 유령 포지션 (무해 - 닫을 게 없다) |
| **합 = 기존 라벨 `reduce_only_violation`** |    39 |                                   |

- 위험 갈래가 **5개 세션**에 걸쳐 반복 발생했다. 일회성이 아니다.
- ★★★**무해 갈래가 3배 많아 위험 갈래를 같은 라벨 안에 묻는다.** counter 만 보면
  "유령 포지션 문제" 로 보이고 **방향 반전은 보이지 않는다.** 큰 숫자가 무해한 쪽이라
  **평균이 안전을 말한다.**
- ★**정본 두 곳이 이미 금지하고 있었다** — `gates-and-traps.md:104`
  ("코드로만 매핑하면 **포지션 반전 부작용이 '무해' 로 위장**된다") ·
  `live-close-diagnostics.md` §2 ("반드시 retMsg 까지 갈라서 세라").
  **문서가 금지한 일을 코드가 하고 있었다.** BL-512 는 `110017` 을 `position_zero` 에서
  `reduce_only_violation` 으로 고친 것까지는 옳았으나 **거기서 멈췄다.**

### 2.1 그리고 화면은 그 9건 전부를 초록으로 보여줬다

```sql
SELECT e.status, o.state, count(*) FROM trading.orders o
JOIN trading.live_signal_events e ON e.order_id = o.id
WHERE o.reduce_only AND o.state='rejected' AND o.error_message LIKE '%same side%'
GROUP BY 1,2;
-->  dispatched | rejected | 9
```

**9/9** 가 이벤트 `dispatched`(Activity Timeline 에서 `text-success` **초록**)인데 주문은
거래소에서 `rejected` 였다. **outbox dispatch 성공과 거래소 수락은 다른 사건인데
화면이 둘을 구분하지 않았다.** 사용자가 그 표를 "청산됐다" 로 읽으면 틀린다.

---

## 3. 한 일

| #   | 내용                                                                                                |
| --- | --------------------------------------------------------------------------------------------------- |
| W1  | `110017` 을 `reduce_only_same_side`(★위험) / `reduce_only_position_zero`(무해) / 잔여 버킷으로 분리 |
| W2  | C2 를 `deferred_market_inflight` 와 `..._noop` 으로 분화 - **미룰 진입이 있었는지**를 처음으로 구분 |
| W3  | 「엔진 내부 체결은 어떤 signal 도 만들지 않는다」를 결정론 회귀로 고정 (프로덕션 코드 0줄)          |
| W4  | 거절된 청산이 화면에서 초록으로 보이지 않게 한다                                                    |

### 3.1 W2 가 부수적으로 고친 것

`_count_safely` 가 `reason=` 을 하드코딩해 `stage=` 라벨 counter 에 재사용할 수 없었다.
`**labels` 로 일반화했다. ★그리고 **기존 defer 사이트는 격리 자체가 없었다** —
`.labels()` 는 멀티프로세스에서 새 라벨 조합 시 mmap 파일을 늘리므로(디스크 full·권한 오류 가능)
`.inc()` 만 감싸는 것으로는 절반만 막는다. 이번에 그 자리도 `_count_safely` 로 들어갔다.

---

## 4. 검증

### 게이트 (실측)

BE **3633 passed / 46 skipped** (baseline **3616** -> **+17**. ★status.md 가 적어둔 **3603 은 stale**
이었다 - §7.1 baseline 재측정이 그것을 잡았다) · ruff **clean** · mypy **213 clean** · 마이그레이션 **0**.

FE **205 파일 / 1231 tests passed** · `pnpm typecheck` clean · `pnpm lint` clean.
`/vercel-react-best-practices` 통과 — 이벤트 표의 행별 파생은 **memo 하지 않는 것이 맞다**
(문자열 비교 3개 x 최대 20행. `rerender-simple-expression-in-memo` 는 그 memo 를 **위반**으로 본다).
신규 fetch 0이라 워터폴도 없다.

### 표적 변이 — **10종 전건 판별, 탈출 0**

앵커는 주입 전 `text.count(old) == 1` 단언 · 복원은 문자열 치환 쌍 + **sha256 해시 대조** ·
마지막에 복원 확인 실행. `git checkout` 은 쓰지 않았다.

| 변이  | 무엇을 뒤집나                            | 결과 |
| ----- | ---------------------------------------- | ---- |
| M-W1a | 위험 갈래를 잔여 버킷으로 접는다         | 판별 |
| M-W1b | 공백 정규화 무력화                       | 판별 |
| M-W1c | 무해 갈래를 잔여 버킷으로 접는다         | 판별 |
| M-W2a | 항상 원 라벨 (noop 판별력)               | 판별 |
| M-W2b | 항상 `_noop` 라벨                        | 판별 |
| M-W2c | 신규 사이트의 counter 격리 제거          | 판별 |
| M-W2d | `_count_safely` 격리 자체를 제거         | 판별 |
| M-W3a | `fill` 을 dispatch 대상에 넣는다         | 판별 |
| M-W3b | 내부 체결 후 pending 을 pop 하지 않는다  | 판별 |
| M-W4  | `hasRejectedOrder` 를 항상 false 로 (FE) | 판별 |

★**M-W3a 는 원래 탈출할 뻔했다.** codex G1 검증이 코드 쓰기 **전에** 지적했다 —
그 변이를 **태스크 레벨**에서 단언하면 `fill` 이 새 outbox 이벤트가 되고 그 이벤트가 다시
`new_events` 를 non-empty 로 만들어 다음 tick 을 defer 시키며, dispatch 는 `apply_async` 라
`OrderService.execute` 는 여전히 안 불린다. **즉 단언이 통과한다.**
그래서 W3 을 `run_live` **반환값 직접 단언**으로 재설계했고, 그 형태에서는 우회가 불가능하다.

### 외부 오라클

- 공개 Bybit kline **2개 호스트 교차 대조** (mainnet · demo, 151 bar, 불일치 0).
- `110017` 갈래 판정은 **거래소 원문 retMsg** 를 픽스처로 동결.

---

## 5. 배운 것

- ★★★**재던 곳에 없었다 — 두 스프린트 연속이다.** 직전 회차는 "유실이 한 채널로 수렴했다" 로
  끝났고 이번 회차는 그 채널이 **유실을 세는 것이 아님**을 발견했다. **분모를 확인하지 않은
  비중(75%)은 측정이 아니다.**
- ★★★**무해한 갈래가 위험한 갈래를 같은 라벨 안에 묻는다.** 30 대 9 라서 counter 는 계속
  "유령 포지션" 을 가리켰다. **같은 에러 코드 안의 갈래가 서로 다른 위험도를 가지면
  그 코드는 라벨이 될 수 없다.** (`110017` 은 이 저장소에서 **두 번째**로 이 교훈을 준다.)
- ★★**정본이 금지한 것을 코드가 하고 있는지 정기적으로 대조해라.** 이번 결함은 새로 생긴 게
  아니라 `gates-and-traps.md` 가 **그 위험을 정확히 서술해 둔 채로** 남아 있었다.
  문서가 경고를 적는 것과 코드가 그 경고를 지키는 것은 다른 사건이다.
- ★★**내 계측기가 이번 회차에도 두 번 먼저 틀렸다.**
  1. key 를 `split_part` 로 잘라 21행을 `cond` 로 읽었는데 `LIKE ':cond:%'` 는 **0** 을 냈다 -
     key 형식이 **둘**이었다(`cond:` / `<ISO>:<seq>:close:`). **분해 결과를 쓰기 전에 원문을 한 번 출력해라.**
  2. `0.058` 주문이 09:09:46 까지 armed 였다고 적었으나 실제 terminal 은 **09:07:40**(armed 1m49s)
     이었다. **다음 주문의 `created_at` 과 혼동했다.** `orders.filled_at` 은 이름과 달리
     **취소·거절 시각도 담는 terminal_at** 이다. 두 행의 시각을 섞지 마라.
- ★**적대 검증이 스코프를 바꿨다.** 읽기 전용 서브에이전트가 "C2 = 청산 횟수" 를 쿼리 한 줄로
  반증했고, 그 시점은 **코드를 한 줄도 쓰기 전**이었다.

---

## 6. 남은 것

- **soak 미실시** — 이번 회차는 **기존 원장**만으로 판정했다. 신규 counter 3종
  (`reduce_only_same_side` · `reduce_only_position_zero` · `deferred_market_inflight_noop`)이
  **실주행에서 실제로 발화하는지**는 다음 회차 첫 step 이다. 사전등록 문턱은
  `docs/status.md` 다음 스프린트 블록에 적어 뒀다.
- **BL-553** ≥30분 공백 검증도 그 soak 에 함께 싣는다.
- **원인은 아직 안 고쳤다.** 이번 회차는 **보이게 만든 것**까지다. 방향 반전이 왜 생기는지
  (재가격 경주 · 청산 거절 후 엔진 미정렬 · 재생 아티팩트)는 신규 라벨이 시간당 몇 건인지
  나온 뒤에 겨눈다. **크기를 모르는 채 고치지 않는다.**
