# Step 1: 모양 A — try 본문의 metric 이 **업무 결과를 뒤집는** 자리 2곳

## 읽어야 할 파일

- **`phases/n7-common.md`**
- `apps/api/src/tasks/live_signal.py:4146-4230` — **대상 ①.** ★`:4212` 에 **정답 관용구**가 있다
- `apps/api/src/tasks/trading.py:2027-2300` — **대상 ②**
- `apps/api/src/common/metrics_multiproc.py:26` — `record_metric_safely` 시그니처
- Step 0 이 심은 「해로운 자리」 판정

## 이 step 이 고치는 것

| # | 자리 | 해악 |
| --- | --- | --- |
| ① | `live_signal.py:4201` `qb_live_conditional_sweep_filled_total.inc()` | metric 실패 → `except` 로 떨어져 `rollback` + **`sweep_cancel_failed`** ⇒ 실제로 **체결된** 주문이 「취소 실패」로 기록된다 |
| ② | `trading.py:2216` `qb_exchange_exit_link_unverified_total.inc()` | metric 실패 → 청산 스윕 루프 전체가 `except` 로 빠진다 |

★**줄 번호는 움직인다.** 원장은 ①을 `:4180` 이라 적었지만 실제는 `:4201` 이었다. **먼저 재라.**

## 작업

1. 두 자리를 `record_metric_safely(...)` 로 감싼다.
   ★**관용구는 같은 파일 `live_signal.py:4212` 에 이미 있다** — `record_metric_safely(qb_x.dec)`.
   호출이 아니라 **호출 가능한 것과 인자**를 넘기는 형태다. 시그니처를 확인하고 따라라.
   ★`.labels(...)` 가 붙은 자리는 라벨 실체화 자체가 던질 수 있다 — **`labels` 까지 가드 안**으로.
2. **`_FROZEN_CENSUS` 에서 해당 키 2개를 지운다.**
   ★★**`: 0` 으로 남기지 마라 — 키 자체를 지워라.** 파일 `:104` 주석이 그 이유를 적어 뒀다:
   `actual == _FROZEN_CENSUS` 는 dict 비교라 `: 0` 은 **영구 red** 다.
3. **래칫 숫자를 내린다** — `len(_FROZEN_CENSUS) == 40` → **38**,
   `sum(_FROZEN_CENSUS.values()) == 83` → **81**.
4. **두 자리를 `_PROTECTED_SITES` 에 등재한다.** `test_every_protected_site_is_actually_guarded`
   (`:712`)와 `test_protected_site_list_is_not_vacuous`(`:741`)가 그것을 집행한다.
   ⇒ **한 번 감싼 자리가 나중에 풀리면 red 가 난다.** 이게 이 lane 의 영속 산출이다.

## Acceptance Criteria

1. `cd apps/api && uv run --env-file .env.local pytest tests/common/test_metric_guard_census.py -q`
2. `cd apps/api && test "$(grep -c 'len(_FROZEN_CENSUS) == 38' tests/common/test_metric_guard_census.py)" -ge 1`
3. `cd apps/api && test "$(grep -c 'sum(_FROZEN_CENSUS.values()) == 81' tests/common/test_metric_guard_census.py)" -ge 1`
4. `cd apps/api && uv run --env-file .env.local pytest tests/tasks tests/common -q`

★**AC 2·3 이 래칫의 증인이다.** 공허성 단언을 **지워서** 통과하는 우회로를 막는다 —
숫자가 정확히 38/81 이어야 한다.

## `summary` 에 반드시 담을 것

- 실제로 고친 좌표 2개 (재측정값. 위 표와 다르면 그 차이를 맨 앞에)
- `.labels(...)` 를 가드 안에 넣었는지, 넣었다면 어떻게
- `_PROTECTED_SITES` 항목의 정확한 형태 (다음 step 이 같은 형식으로 2건 더 넣는다)
- AC 4 에서 **함께 red 가 난 테스트**가 있었으면 목록과 처리

## 금지사항

- **`_FROZEN_CENSUS` 항목을 `: 0` 으로 남기지 마라** — 영구 red 가 된다(파일 `:104` 주석).
- **래칫 단언(`len(...) == N` · `sum(...) == N`)을 지워서 통과하지 마라** (AC 2·3 이 잡는다).
  ★그 단언이 이 파일의 **유일한 공허성 방어**다.
- **모양 B 2곳(`realtime_publisher.py` · `webhook.py`)은 이 step 에서 건드리지 마라.**
  이유: 해악의 기전이 다르고 Step 2 의 몫이다. 섞으면 무엇이 무엇을 고쳤는지 안 갈린다.
- **`apps/api/AGENTS.md` 에 규칙을 등재하지 마라** — `summary` 에 문안만.
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
