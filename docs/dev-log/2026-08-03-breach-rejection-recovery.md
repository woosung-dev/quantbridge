# breach-rejection-recovery — 가드는 옳았고, 없었던 것은 거절 뒤의 복구다 (2026-08-03)

> 브랜치 `stage/breach-rejection-recovery` (`main` @ `18d1fdaa`) · 마이그레이션 **0** · FE 변경 **0**
> [BL-590] **Resolved** · bl-audit active **151 → 151**(신설과 해소가 상쇄)
> 최종 게이트: BE **3938 / 46 skipped** · ruff 0 · mypy 0 (**215**) · FE 무접촉
> 유도 주입으로 프로덕션 발화 확인: `recovery_placed` **1.0**(신규 series), 복구 주문 **체결**

**한 줄.** 계획기의 돌파 가드는 **발주 시각에 옳았다.** 거래소는 그 2.1초 뒤 자기 시각으로
판정해 거절했고, **그 거절 뒤에 아무 일도 일어나지 않는 것**이 소크를 105분에 끊었다.

---

## §0. baseline 재측정 (`global.md` §7.1)

| 축                | 대조값 (status.md)   | 실측                   | 판정                       |
| ----------------- | -------------------- | ---------------------- | -------------------------- |
| BE pytest         | 3914 / 46 skipped    | **3914 / 46** (402.7s) | ✅ 일치                    |
| ruff check · mypy | clean · 214 clean    | **clean · 214 clean**  | ✅                         |
| bl-audit active   | 151                  | **151**                | ✅                         |
| 마이그레이션 head | `20260801_0001`      | **`20260801_0001`**    | ✅                         |
| 활성 세션         | 「소크가 돌고 있다」 | **0 / 26**             | ❌ **status.md 가 낡았다** |

★**진입점 블록의 전제가 무효였다.** `docs/status.md` 최상단은 세션 `a201a47b` 가 돌고 있다고
적고 있었으나 그 세션은 `2026-08-03T15:54:34Z` 에 죽어 있었다(T0+**104.9분**).
⇒ `backend/src` 편집이 금지가 아니라 **허용**되는 창이었다.

## §1. 착수 전제 반박 2건

### (1) 「기준가가 스테일이라 가드가 뚫렸다」 — **틀렸다**

PR #493(`274dc645`)이 이미 기준가를 「마지막 종료 bar 종가」에서 **거래소 라이브 perp last** 로
교체했다(`live_signal.py:1234-1258`). 60초 스테일은 그때 없어졌다.

**주문의 형태가 곧 증거다.** `.soak/snap-20260803T154620Z.txt` → `snap-20260803T161053Z.txt` 차분:

```
conditional_placed          216 → 217   (+1)   ← 사망을 유발한 그 주문
market_converted             11 →  11   불변
breach_with_resting          11 →  11   불변
trigger_already_breached      6 →   6   불변
breach_capped / reference_unavailable / convert_suppressed / breach_reverted   전부 불변
direction_transient          21 →  22   (+1)   15:53:34
direction / divergence_blocked 2 →   3   (+1)   15:54:34 사망
```

연역이 닫힌다 — ① `reference_unavailable` 불변 ⇒ 라이브 조회 **성공**, `allow_market_conversion=True`
② `conditional_placed +1` 이고 주문이 `cond:` 키에 trigger 필드를 달고 나갔다 ⇒ `as_market=False`
⇒ **`breached` 가 False** ③ short leg 에서 False ⟺ **기준가 > 63723.6**.
2.1초 뒤 거래소는 **63698.8** 로 쟀다(`110093 "expect Falling"`).

⇒ **가드와 거래소가 서로 다른 시각에 판정한다. 그 창은 사전 가드로 못 닫는다.**

### (2) 「이 클래스는 `110093` 이다」 — **절반이다**

거울 코드 **`110092`**(`"expect Rising"`, long/RISE)가 있고 둘 다 `reason="trigger_breached"` 로
접힌다(`metrics.py:259-262`). PR #493 이후 원장 4건 중 **2건이 110092** 다.
110093 만 고쳤으면 절반만 닫았다. (표적 변이 **X2** 가 이 실수를 정확히 잡는다.)

## §2. 뿌리 — 거절 뒤 복구 경로의 부재

`trading.py` 의 `except ProviderError` 는 `trigger_breached` 를 **계상만** 하고 주문을
`rejected` 로 종결한다. 그 뒤가 없다(`grep resubmit|retry_order|recover` → 0건).
`janitor_conditional_entries` 도 `submitted` 만 훑으므로 대상이 아니다(실측: 사망 43초 전에
돌았고 `{repaired:0, rejected:0, terminal:0}`).

그런데 엔진 포지션은 `run_live` **시뮬**이라 주문을 아예 모른다([BL-589] 확정).
**거래소가 「현재가가 트리거를 지났다」고 거절했다는 사실 자체가 그 bar 가 트리거를 찍었다는
증명**이므로 시뮬은 반드시 체결한다 ⇒ 엔진만 전진 ⇒ `direction` 발산 2회 ⇒ fail-closed.

★**[BL-589] 와 합치지 마라.** 저건 계획기가 진입을 **드롭한** 경우(`breach_with_resting`),
이건 **발주했는데 거절된** 경우다. `breach_with_resting` 은 11 불변이라 직전 수리 갈래는 안 밟혔다.

### 사망 연쇄 (세션 `a201a47b`)

| 시각 (UTC)  | 사건                                                                         |
| ----------- | ---------------------------------------------------------------------------- |
| 15:52:00    | bar `15:51` 마감 (perp C=**63760.6**)                                        |
| ~15:52:45   | 계획기가 short stop `63723.6` 계획. 기준가 **> 63723.6** (§1)                |
| 15:52:46.67 | 주문 `48c9cdc9` 생성 (`cond:` · `trigger_direction=2`)                       |
| 15:52:48.78 | Bybit current **63698.8** → `110093` **거절**                                |
| 15:52:49.05 | `trigger_breached` 계상. **여기서 끝**                                       |
| 15:53:34    | 엔진이 bar `15:52`(L=**63698.8**) 처리 → 시뮬 숏. 거래소는 롱 +0.029 → 1회차 |
| 15:54:34    | 2회 연속 → `position_divergence`                                             |

## §3. 재생 오라클 — 구현과 독립 (거절 4건 전수)

원장 + Bybit 공개 1분봉(인증 불필요). 계획기·복구 코드를 **한 줄도 부르지 않는다**.
판정 규칙은 `PendingOrder.try_fill` 계약을 손으로 재구현했다(short: `low <= stop`).

| 주문     | ret    | 방향  | 트리거  | 다음 봉 L/H       | 시뮬 체결 | 거래소 순 | 발산 판정     |
| -------- | ------ | ----- | ------- | ----------------- | --------- | --------- | ------------- |
| a87a931d | 110092 | long  | 64025.9 | 64019.1 / 64047.7 | 64025.9   | 0         | `engine_only` |
| b46f23d3 | 110093 | short | 64448.4 | 64423.1 / 64451.9 | 64448.4   | +0.029    | **direction** |
| ca5dfee4 | 110092 | long  | 62734.3 | 62712.4 / 62736.6 | 62734.3   | 0         | `engine_only` |
| 48c9cdc9 | 110093 | short | 63723.6 | 63698.8 / 63771.8 | 63723.6   | +0.029    | **direction** |

- **「거절 = 시뮬은 체결한다」 = 4/4.** 아키텍처와 무관하게 성립한다.
- **치명(`direction`) = 2/4** — 거래소가 **반대 포지션을 들고 있을 때만** 치명이다.
  flat 이면 `engine_only` 라 관측 전용이고 죽지 않는다.

★**괄호를 단일 숫자로 줄이지 마라.** 4건 중 **오늘의 반전 아키텍처를 공유하는 것은 1건뿐**이다 —
`close:` 별도 청산 leg 는 07-31 까지만 쓰였고(일자별 13/9/25/3/**0**/0/0), 07-29 두 건은
sell 0.029(합산 반전이 아니라 진입만)였다. 게다가 그 시기는 `deactivated_reason` 미영속이라
사인을 못 읽는다. ⇒ **「4/4 가 세션을 죽였다」고 쓰면 거짓이다.**

**규모:** PR #493 이후 **4건 / 19.09 세션시간 = 0.21건/h**. 조건부 주문당 **4/178 = 2.25%**.
사망 세션은 105분에 조건부 15건이었으므로 **105분 기대값 ≈ 0.34건**.

## §4. 수리

거절을 **「돌파 확정 증거」**로 읽고 PR #493 이 이미 정의한 시장가 전환을 그 자리에서 집행한다.
**새 정책이 아니다** — 이미 있는 전환의 **발화 시점**만 옮겼다.
★**fail-closed 킬 경로(2회 연속 `direction`)는 무수정.** 복구가 실패하면 오늘과 똑같이 죽는다.

- `trading.py` — `except ProviderError` 의 `await session.commit()` **뒤**, `if rows == 1:` **안**
  에서 `_enqueue_breach_recovery(order, reason)`. 판별(reason/kind)은 **helper 안**에서 한다
  (`_enqueue_conditional_reversal_measure` 와 같은 형태).
- `conditional_entry_recovery.py` **(신규)** — `live_signal.recover_breached_entry`.
  판정 순서는 계획 시점 전환(`live_signal.py:1421-1531`)과 **같다**:
  `not_applicable` → interval → 억제창 → **만료** → 기준가 → 돌파 재확인 → 캡 → 발주.
- `metrics.py` — guard outcome **4종 추가**(`recovery_placed`/`_reverted`/`_suppressed`/`_expired`).
  `reference_unavailable`·`breach_capped` 는 **기존 라벨 재사용**(로그로 단계를 가른다).
- `celery_app.py` — `include` 등재.

★**`recovery_placed` 는 「거래소가 받았다」가 아니다.** `OrderService.execute` 는 원장에 commit 하고
`trading.execute_order` 를 예약할 뿐이며, 같은 key 의 **캐시 응답에 합류**했을 수도 있다.

## §5. 사전등록 변이 — **8/8 판별** (네 회차 연속 「판별력 0」을 끊었다)

집행은 평가자가 직접(`git checkout` 금지 · 백업 복사 + sha256 복원 대조 · 치환 문자열 1회 확인).

| ID  | 변이                                          | 판정  |
| --- | --------------------------------------------- | ----- |
| X1  | 복구 예약 자체를 끈다(= 수리 이전 상태)       | RED ✓ |
| X2  | **거울 코드 110092 를 뺀다**                  | RED ✓ |
| X3  | 돌파 부등식에서 등호를 뺀다(트리거 == 현재가) | RED ✓ |
| X4  | 이중 진입 억제 창을 무력화한다                | RED ✓ |
| X5  | CAS 패자도 예약하게 만든다                    | RED ✓ |
| X6  | 되짚을 수 없는 `bar_epoch` 를 통과시킨다      | RED ✓ |
| X7  | 만료 가드를 끈다                              | RED ✓ |
| X8  | 만료를 항상 참으로(대칭 짝)                   | RED ✓ |

## §6. Generator/Evaluator — codex 가 잡은 것, 내가 잡은 것

**G1(코드 전) 9건** — 전건 코드 대조, 액면 수용 0.

- ★**동결 테스트의 시한폭탄**: 억제 창이 `bar_time - 2*interval` 인데 기존 전환 행을
  벽시계로 심어, **2시간 뒤 올바른 구현이 red** 가 되는 상태였다(실측 확인).
- `StrategySettings` 는 `leverage`/`margin_mode`/`position_size_pct` **필수** — fixture 의 `{}` 로는
  주문이 아예 안 나간다.
- 예약은 **CAS 승자만, commit 뒤에**(`transition_to_rejected` 는 CAS).
- `parse_live_entry_key` 는 `bar_epoch=None` 을 **의도적으로 허용**한다 — 파싱 성공을 key 생성
  가능으로 읽으면 안 된다.

**G2 구현에서 내가 잡은 BLOCKING 1건** — codex 가 `_enqueue_breach_recovery` 호출을
**`credential_decrypt_failed` 핸들러**에 넣었다. `response_reason` 이 그 스코프에 없어
**복호화 실패 시 `UnboundLocalError`** 였고, 정작 돌파 거절에서는 예약이 안 됐다.
★**전체 BE 스위트 3914건으로는 안 잡힌다** — 그 경로를 실행하는 테스트가 레포에 없다.
동결 테스트가 잡았다.

**G6 이 잡은 것 중 확인된 것**

- ★**내가 쓴 celery 등록 테스트가 항상 green 이었다** — 테스트 모듈이 복구 모듈을 이미
  import 해 registry 를 채우므로 `include` 를 통째로 지워도 통과한다(**실제로 지우고 확인**).
  ⇒ `celery_app.conf.include` 를 보도록 교체하고 판별력을 재확인했다.
- **지연된 복구가 과거 bar 의 방향·수량으로 시장가를 낸다** ⇒ 만료 가드(1 interval) 신설.
  `still_breached` 재확인은 **가격이 되돌아온 경우만** 막고, 같은 방향으로 더 간 경우는 못 막는다.
- 평가자의 spy 위치 변경은 **옳다**고 판정받았다(helper 를 mock 으로 덮으면 helper **안의**
  판별이 통째로 미검증이 된다 — 실제로 음성 대조 3건이 red 였다).

**G6 이 낸 Standards BLOCKING 은 기각한다** — 「활성 소크가 `backend/src` 편집을 금지한다」의
근거가 `status.md` 인데 **그 문서가 낡았다**(§0). 세션은 0건이었다.

## §7. 프로덕션 유도 주입 — 분기 도달·종결

★**증명한 것과 못 한 것을 합치지 마라.**

| 층                        | 증명 수단                   | 결과                                          |
| ------------------------- | --------------------------- | --------------------------------------------- |
| 분기 **도달·종결**        | 프로덕션 유도 주입          | ✅ `recovery_placed` 1.0 · 복구 주문 **체결** |
| 판정 로직(경계·억제·만료) | 오프라인 결정론 테스트 24건 | ✅ 변이 8/8                                   |
| 계측 실패 봉쇄            | 오프라인 고장 주입          | ✅ `.labels()` 예외에도 판정·발주 불변        |
| 이중 진입 **동시성**      | —                           | ❌ **미검증**(§8)                             |

절차: flat 확인 → 버리는 세션 등재 → 현재가 **+200** 에 sell FALL stop 발주(발화 불가) →
`110093` → 복구. 실측 로그:

```
17:59:00.329  provider_create_order_failed  retCode 110093
17:59:00.352  live_signal.recover_breached_entry received   ← 거절 23ms 뒤
17:59:08.850  conditional_entry_recovery_placed  key=...:condmkt:...
              → {'outcome': 'recovery_placed'}
```

복구 주문 `51397763` **filled 0.001 @ 63859.1**. 이후 세션 비활성화 + 재 flat 확인.

★**거래소를 flat 으로 맞추는 일이 원장을 거치지 않는다** — 죽은 세션 `a201a47b` 가 롱 0.029 를
남겼고(세션 비활성화는 **아무것도 flat 하지 않는다**), 그 청산과 유도 정리 청산 2건은
`trading.orders` 에 행이 **없다**. 과거 원장을 셀 때 이 구멍을 빼먹지 마라(3회째 재발).

## §8. 남긴 것 (의도적 미수리 — 「없다」가 아니라 「안 했다」)

- **거절 commit 과 `apply_async` 사이 크래시 시 복구 유실.** 실패 모드가 **오늘의 동작과 같다**
  (복구 없음 → 안전하게 죽는다). 게다가 만료 가드 때문에 뒤늦은 sweeper 재시도는 무효다.
- **서로 다른 `trade_id` 두 복구의 동시 실행.** 억제 질의가 read-then-write 라 이론상 경쟁이
  있다. 같은 세션에서 두 조건부 진입이 같은 순간 돌파 거절될 확률이 낮아(0.21건/h) 보류.
- `recovery_placed` 가 **캐시 응답에도 계상**된다(주석으로 명시, 동작 미변경).

## §9. 교훈 후보

1. ★★★**「가드가 왜 안 걸렸나」 전에 「가드가 언제 판정했나」를 물어라.** 이번 가드는 틀린 게
   아니라 **다른 시각에 옳았다**. 판정 시각이 둘이면 그 사이는 사전 가드로 못 닫는다 —
   닫는 자리는 **결과를 받은 뒤**다.
2. ★★★**격리 실행이 거짓말을 했다.** 두 파일만 돌리면 24 passed 인데 전체 스위트에서는 **8 failed**
   였다. 원인은 오염이 아니라 **내 fixture 가 시각을 모듈 import 시점에 고정**한 것 —
   6분짜리 스위트에서는 실행 시점에 이미 낡아 만료 가드에 걸렸다.
   ⇒ **시간 의존 fixture 는 실행 시점에 만들어라. 그리고 전체 스위트가 유일한 판정자다.**
3. ★★★**두 안전한 것이 합쳐져 결함이 됐다.** codex 는 `created_at = bar+106초` 를
   「assertion 에 안 쓰이니 flake 아님」으로 판정했고 그때는 맞았다. 그 뒤 내가 **만료 가드**를
   넣으면서 그 값이 **load-bearing** 이 됐다. **판정은 그 시점의 코드에만 유효하다.**
4. ★★**내가 쓴 테스트가 항상 green 이었다**(celery 등록). 사전등록 변이만 검증 대상이 아니라
   **음성 대조·존재 확인 테스트도 판별력을 증명해야 한다.**
5. ★★**변이 실행 중 워커가 그 코드를 적재한다** — `backend/src` bind-mount + watchfiles.
   이번엔 활성 세션 0 이라 무해했지만, **소크 중 변이 테스트는 프로덕션에 고장을 주입하는 것**이다.
6. ★**백로그가 지목한 코드가 지목한 결함을 안 갖고 있을 수 있다** — 지시문이 지목한 `110093` 은
   클래스의 절반이었다.
