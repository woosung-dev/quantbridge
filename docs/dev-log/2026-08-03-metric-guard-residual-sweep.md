# metric-guard-residual-sweep — 발주 outbox 12곳을 판정했다 (2026-08-03)

> 브랜치 `stage/metric-guard-residual-sweep` (`main` @ `72335f16`) · 마이그레이션 **0** · FE 변경 **0**
> census 가드 밖 mutation **104 → 96** · 판정 12곳 = **수리함 8 + 판정 보류 4**

**한 줄.** 같은 함수 · 같은 metric · 전부 「`commit()` 뒤」인데 **한 자리만 fail-open `try`
안**이었고, 그 한 자리에서 계측 실패는 오기록이 아니라 **거절을 집행으로 뒤집었다** — 거래소가
flat 이라 청산을 거부한 이벤트에 **실주문이 나갔다.**

---

## §0. baseline 재측정 (`global.md` §7.1)

| 축                           | 대조값 (status.md) | 실측                   | 판정                         |
| ---------------------------- | ------------------ | ---------------------- | ---------------------------- |
| BE pytest (수집 집합 = 전체) | 3885 / 46 skipped  | **3885 / 46** (403.0s) | ✅                           |
| BE pytest (대상 4파일 단독)  | —                  | **54 passed** (15.0s)  | ✅ 신규 기준선               |
| FE vitest                    | 1242 (205 파일)    | **1242** (205 파일)    | ✅ FE diff 0                 |
| ruff · mypy                  | clean · 214 clean  | **clean · 214 clean**  | ✅                           |
| 마이그레이션 head            | `20260801_0001`    | **동일**               | ✅                           |
| census                       | 104                | **104**                | ✅                           |
| `live_signal.py` 함수별      | 21 / 12 / 11       | **21 / 12 / 11**       | ✅ 그대로 재현               |
| `/metrics`                   | 11449 파일 · 708MB | **12459 파일 · 771MB** | ✅ BL-581 Trigger 20000 미달 |
| 활성 라이브 세션             | —                  | **0**                  | ✅ 편집 안전                 |

★**「두 번 재라」를 수집 집합으로 집행했다.** `-p no:randomly` 는 이 레포에 randomizer 가
없어 no-op 이므로 쓰지 않았다(BL-583 교훈).

## §1. Step 1 — 사이트별 「프로덕션 도달 경로」를 수리보다 먼저 적었다

status.md 첫 step #7 의 의무다. 12곳 중 **8곳만 한 줄로 적을 수 있었다.**

| #   | 줄※    | outcome                 | 도달 경로                                                                           | 판정      |
| --- | ------ | ----------------------- | ----------------------------------------------------------------------------------- | --------- |
| D1  | `3078` | `session_inactive`      | 비활성화 뒤 남은 event 를 `dispatch_pending` Beat(5분)이 재발행                     | 도달 가능 |
| D2  | `3089` | `strategy_missing`      | FK `strategies.id ON DELETE RESTRICT`(`models.py:502`)가 막고, owner 이전 경로 없음 | **보류**  |
| D3  | `3098` | `invalid_settings`      | `update_settings(settings: StrategySettings)` 라 round-trip 이 항상 유효            | **보류**  |
| D4  | `3105` | `settings_unset`        | 등록 게이트(`live_session_service.py:84`)가 유일 방벽, 통과 뒤 비는 경로 없음       | **보류**  |
| D5  | `3133` | `close_position_flat`   | close 이벤트 + 거래소 포지션 0건 (BL-560 소크가 청산 시도의 46.2% 에서 실측)        | 도달 가능 |
| D6  | `3180` | `rejected` (trailing)   | trailing 만 선언하고 고정 SL 이 없는 Pine 전략의 entry                              | 도달 가능 |
| D7  | `3218` | `rejected` (req 검증)   | NUMERIC(18,8) round-trip 으로 qty·exit 레벨이 0 (`Field(gt=0)`)                     | 도달 가능 |
| D8  | `3235` | `kill_switched`         | 누적/일일 손실 한도 위반                                                            | 도달 가능 |
| D9  | `3247` | `rejected` (도메인 4종) | min-notional 미달 / notional 초과 / leverage cap / 거래시간 밖                      | 도달 가능 |
| D10 | `3253` | `idempotency_conflict`  | ★**도달 불가** — 아래 §1.1                                                          | **보류**  |
| D11 | `3261` | `dispatched`            | 정상 발주                                                                           | 도달 가능 |
| D12 | `2820` | `max_retries_exhausted` | 일시 장애 3회 반복 후 소진                                                          | 도달 가능 |

※ **수리 전 줄번호**다(판정 시점 기준). 수리로 줄이 밀렸으므로 현재 트리의 보류 4곳은
`:3095`(D2) · `:3104`(D3) · `:3111`(D4) · `:3278`(D10) 이다 — census 정본의 키 위 주석이 SSOT.

**코퍼스 실측**(앱 DB `quantbridge`@5433) — D2/D3/D4 판정의 뒷받침:
세션 24(활성 0) · 전략의 settings 가 NULL 인 세션 **0** · owner 불일치 **0** · orphan **0** ·
`mode=live` 계정 **0**. 전략 3건 중 1건은 `settings` 가 JSONB `null`(Python `None` 으로 디코드
→ D4 분기를 만든다)이지만 **그 전략 위 세션은 0건**이라 등록 게이트가 여전히 유일 방벽이다.

★**보류 4곳에는 하네스를 만들지 않았다.** 만들면 프로덕션이 못 만드는 상태를 손조립해
「실측 유해」로 적게 된다 — 직전 회차 codex G6 가 잡은 그 함정([BL-582] 의 거울상).

### 1.1 D10 은 **사문(死文)** 이다

`except IdempotencyConflict`(현재 `:3274`)가 잡는 예외의 **유일한 raise 지점**은
`order_service.py:369` 이고 그것은 `if body_hash is not None` 안이다. 그런데
`_async_dispatch_event`(현재 `:3246`)는 **`body_hash=None`** 을 넘긴다. 즉 이 호출자에게 그 `except`
블록과 그 안의 계측은 **도달 불가**다. HTTP 라우터 경로에서는 발생하므로 예외 자체는 살아 있다.

## §2. Step 2 — 사전등록 (코드 쓰기 **전**)

**공통 기전 예측.** 8곳 전부 `mark_failed`/`mark_dispatched` + `commit()` 뒤다. 계측이 던지면
터미널 dict 가 사라지고 `OSError` 가 탈출한다. 호출자
`dispatch_live_signal_event_task:2793` 은 **예외 타입으로** 재시도를 가르므로(결정론적 거절
5종만 무재시도), `OSError` 는 `except Exception` → `self.retry()` 대상이 된다.
⇒ 라벨 **H6**(정상 종결이 재시도로 오분류). D8·D9 는 도메인 예외가 통째로 사라져 **H5** 가 겹친다.

주입은 **라벨 단위**로 `.inc` 가 아니라 **`.labels` 를 폭파**(`OSError("mmap allocation
failed")`)했고, 사이트마다 `assert calls == [{...}]`(stub 정확히 1회) + **비-계측 postcondition**
을 걸었다. `outcome="rejected"` 는 D6·D7·D9 가 공유하므로 라벨로는 안 갈린다 — **반환값**으로
구별했다(`trailing_unsupported` / `invalid_order_request` / raise).

## §3. 판정 결과 — **수리함 8**, 「가드 없이 유지」 **0곳**

주입 8건 **전건 red → 수리 후 전건 green**. 「전건 red」를 신호가 아니라 확인 대상으로 다뤄
실패 지점을 봤고, D5 를 뺀 7건이 모두 주입 stub 의 `raise`(`test:58`)였다 — 드라이버 오류가
아니다(status.md 첫 step #8).

### 3.1 ★★★D5 — 내 사전등록이 반증됐다. 신규 라벨 **H8**

D5 만 실패 지점이 달랐다. 결과 단언에서 red 였고, 반환값이 `{"dispatched": "<order_id>"}` 였다.

원인: **이 계측만 fail-open `try` 블록 안**(현재 `:3131`~`:3155`)이다.

```
mark_failed("close_position_flat") + commit()   ← 이벤트는 이미 failed 로 내구화
qb_live_signal_dispatch_total.labels(...).inc() ← 여기서 OSError
return {"failed": "close_position_flat"}        ← ★실행되지 않는다
except Exception:                                ← 계측 예외를 "포지션 조회 실패" 로 오인해 삼킨다
    logger.warning("live_signal_close_position_check_failed_open")
...                                              ← 그대로 흘러가 발주까지 간다
```

⇒ 귀결은 오기록이 아니라 **원장 분기**다. `failed` 로 커밋된 이벤트에 **실주문이 나간다.**
「거래소가 flat 이면 reduce-only 거부 주문을 만들지 않는다」는 이 분기의 존재 이유가 계측 한
줄에 뒤집힌다. 신규 라벨 **H8 — 거절이 집행으로 뒤집힌다.**

★**교훈.** 「전부 `commit()` 뒤라 같은 형태」가 내 산문이었고, 그것이 8곳 중 1곳에서 틀렸다.
같은 함수 · 같은 metric · 같은 「commit 뒤」인데 **감싸는 블록이 달라서** 귀결의 종류가
바뀌었다. ⇒ **「commit 뒤인가」가 아니라 「어느 `try` 안인가」를 봐라.**

### 3.2 판정표

| #   | 예측  | 실측                                                            | 판정       |
| --- | ----- | --------------------------------------------------------------- | ---------- |
| D1  | H6    | 예측대로                                                        | **수리함** |
| D5  | H6    | ★★★**반증 → H8** — fail-open `except` 가 삼키고 **그대로 발주** | **수리함** |
| D6  | H6    | 예측대로 (무방비 진입 차단이 재시도 대상이 된다)                | **수리함** |
| D7  | H6    | 예측대로                                                        | **수리함** |
| D8  | H6+H5 | 예측대로 — `KillSwitchActive` 대신 `OSError` 탈출               | **수리함** |
| D9  | H6+H5 | 예측대로 — `MinNotionalNotMet` 대신 `OSError` 탈출              | **수리함** |
| D11 | H6    | 예측대로 — 발주 성공이 실패로 보고                              | **수리함** |
| D12 | H6+H2 | 예측대로 — 포기 반환 소실, `OSError` 가 태스크 밖으로           | **수리함** |

## §4. 표적 변이 — 4건 중 **2건이 내 예측을 반증했다**

CONTROL 이 직접 집행(`git checkout` 금지, 문자열 치환 + sha256 복원 대조. 전량 정확히 복원).

| 변이 | 예측            | 실측                                                                       | 판별력 |
| ---- | --------------- | -------------------------------------------------------------------------- | ------ |
| M1   | 해당 주입 red   | 예측대로 — D11 red                                                         | ✅     |
| M2   | 주입 8건 green  | 예측대로 — **8 green**. 잡는 것은 가드 폭 테스트 **1건**                   | ✅(0)  |
| M3   | 주입 8건 green  | ★**반증 — 8 red**. 내가 쓴 형태는 `.labels()` 를 raw 로 한 번 더 부른다    | ❌     |
| M4   | A-C2 오라클 red | ★★**반증 — 판별력 0**. `tests/tasks`+`tests/trading` **1578건 전부 green** | ❌     |

★★**M2 가 직전 회차 M5(「반쪽 수리는 사이트 주입을 전부 통과한다」)의 재현이다.** 사이트
주입은 `.labels()` 가 안 던지는 것만 본다 — **증분 소실은 못 본다.** 유일한 방벽이
`tests/common/test_metrics_multiproc.py::test_count_safely_swallows_child_inc_failure` **1건**
이라는 것이 실측으로 확인됐다. **그 테스트를 지우지 마라.**

### 4.1 ★★M4 가 코드가 아니라 **스위트의 구멍**을 드러냈다

A-C2 오라클이 결정론적 거절 **5종 중 1종**(`TradingSessionClosed`)만 구동하고 있었다. 무재시도
튜플에서 `KillSwitchActive` 를 지워도 1578건이 전부 green 이다. 귀결이 가장 나쁜 종류가
그것이다 — **리스크 게이트의 거절**이 3회 재시도된 뒤 `max_retries_exhausted` 로 기록돼
사유가 지워진다([BL-584] 형태).

★**이건 부수적 발견이 아니라 수리의 전제다.** D8·D9 수리의 값은 「도메인 타입이 살아남는
것」인데, 그 타입을 **분류해 주는 튜플이 고정돼 있지 않으면** 수리가 지키는 것이 없다.
⇒ 오라클을 5종 전체로 넓혔고, 재집행 결과 M4 가 **red 로 잡힌다.**

## §5. [BL-584] 도달성 확인 — **현재 코퍼스 도달 불가** (수리 없음)

status.md 첫 step #4 가 「수리 전에 도달 가능한지부터」라고 지시한 항목이다. 대상이 같은
함수라 함께 봤다.

- `BalanceUnverified` 의 raise 2곳(`order_service.py:295`·`:309`)은 모두
  `dispatch_snapshot["mode"] == ExchangeMode.live` 게이트 안이다.
- `dispatch_snapshot["mode"]` 는 발주 시점 계정 **fresh read**(`order_service.py:199`).
- 라이브 세션 등록은 `account.exchange == bybit and account.mode == demo` 를 강제하고 아니면
  `AccountModeNotAllowed`(`live_session_service.py:109`).
- `ExchangeAccountRepository` 에 **mode 갱신 메서드가 없고**(`save`/`get`/`list`/`delete` 뿐),
  라우터도 POST(등록)·GET·DELETE 뿐이다 ⇒ **생성 후 mode 불변**.
- 코퍼스 실측: `mode=live` 계정 **0건**.

⇒ 라이브 신호 dispatch 경로에서 `BalanceUnverified` 는 **현재 도달 불가**. 수리하지 않고
Trigger 를 「`mode=live` 계정이 생성될 때(Wave 3 cutover)」로 보강해 유지한다.

## §6. 남긴 것

- 수리 8곳 = `_count_safely` 교체. 자리마다 「왜 여기가 위험한가」를 주석으로 남겼다.
- 주입 8건 + 오라클 확장 1건 = `tests/tasks/test_live_signal_metric_failure.py`.
- census `_FROZEN_CENSUS` 104 → **96**(dispatch_total 키 12 → 4) · 누적 산식 줄 연장 ·
  `_PROTECTED_SITES` 2건 등재 + **보류 4곳의 이유를 키 위 주석으로** 남겼다.
- ★`_PROTECTED_SITES` 의 `(파일, 함수, metric)` 삼중항은 이 함수에서 **과선택**한다(metric 이
  하나뿐). 자리별 집행은 census 천장이 한다 — 잔여 4곳이 raw 로 남아 있으므로 수리한 자리가
  raw 로 되돌아가면 개수가 4를 넘어 red 가 된다.

## §7. 회고

1. ★★★**「commit 뒤」는 형태가 아니다.** 8곳을 한 문장으로 요약한 내 구조 분석이 1곳에서
   귀결의 **종류**를 놓쳤다. 감싸는 `try` 가 fail-open 이면 가드 부재는 오기록이 아니라
   **거절의 무효화**다. 다음 스윕은 사이트마다 **바깥 `except` 가 무엇을 하는지**부터 적어라.
2. ★★**변이가 코드가 아니라 스위트를 반증할 수 있다.** M4 는 「내 변이의 판별력이 0」이었지만
   그 원인이 mutation 설계가 아니라 **오라클의 커버리지 구멍**이었다. 판별력 0 을 보면
   「변이를 바꾼다」와 「테스트를 넓힌다」 둘 다 후보다.
3. ★★**도달 불가는 두 방향으로 틀린다.** [BL-582] 는 「불가」로 적힌 것이 가능이었고, 여기
   D10 은 그 반대로 **`except` 자체가 사문**이었다. 둘 다 「그 입력을 누가 만드는가」를
   따라가야만 갈린다.
4. ★**보류를 수리로 밀지 않았다.** 4곳은 유해성을 재지 않았으므로 「수리함」에 넣지 않았다.
   대신 **왜 못 쟀는지**를 census 주석에 남겨 다음 사람이 같은 분석을 반복하지 않게 했다.
