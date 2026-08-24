# Step 1: 스코프 + allowlist 로 **위양성 없는** 정적 가드를 세운다

## 읽어야 할 파일

- **`phases/n7-common.md`**
- `apps/api/src/trading/entry_completeness.py` — **위양성의 정본 사례.** `:1391` 과 `:1450-1470`
- `apps/api/src/backtest/models.py:87-90` · `:186-190` — **왜 그 파일들이 안전한지**의 근거
- Step 0 이 만든 `apps/api/tests/trading/test_no_strenum_value_access.py`

## 착수 전 실측 (2026-08-24 · CONTROL) — ★이 lane 의 핵심

Step 0 이 파생한 6개 **필드명**으로 `apps/api/src` 전체에서 `<무엇>.<필드>.value|.name` 을
그냥 찾으면 **12건**이 나온다. 그리고 **12건 전부 위양성이다. 진짜 위반은 0건이다.**

| 위양성 | 건수 | 왜 안전한가 |
| --- | --- | --- |
| `backtest/service.py` `.status.value` | 4 | `BacktestStatus` 는 `Column(SAEnum(BacktestStatus, ...))` (`backtest/models.py:89`) = **진짜 PG enum** ⇒ SQLAlchemy 가 로드 시 재캐스팅한다 |
| `optimizer/service.py` `.status.value` | 3 | `optimizer/models.py:83` `SAEnum(OptimizationStatus, ...)` |
| `stress_test/service.py` `.status.value` | 2 | `stress_test/models.py:78` `SAEnum(StressTestStatus, ...)` |
| `trading/entry_completeness.py` `.channel.value` | 3 | `tally.channel` 은 `LedgerChannel` (`:1391`) — **DB 행이 아니라 메모리 dataclass** 다. `AlertRule.channel` 과 **이름만 같다** |

⇒ **이름만 보는 가드는 판별력 0 에 오탐 12건이다.** 그대로 만들면 못 쓴다.

## 이 step 의 설계 결정 (CONTROL 이 정했다 — 임의로 바꾸지 마라)

**⑴ 스코프로 자른다.** 위험은 「`trading/models.py` 의 행을 새 세션이 재조회한 뒤 `.value`」다.
그 코드가 사는 곳은 **`apps/api/src/trading/` 과 `apps/api/src/tasks/`** 다.
`backtest`·`optimizer`·`stress_test` 는 **다른 모델**을 쓰므로 스코프 밖이다 ⇒ 위양성 9건이
**규칙으로** 사라진다(예외 목록이 아니라 스코프로 사라지는 것이 중요하다).

**⑵ 남는 3건은 allowlist 로, 사유 문자열과 함께.** `entry_completeness.py` 의 3건은 스코프
안이지만 메모리 타입이다. allowlist 항목은 **`(파일, 속성, 사유)` 3튜플**로 두고, 사유가
빈 문자열이면 테스트가 **실패**하게 해라(사유 없는 면제 금지).

**⑶ 지금 위반이 0건이라는 사실을 그대로 단언하지 마라.** 「0건이니 통과」는 대상에 안 닿아도
참이다. 반드시 **양성 대조**를 함께 둬라 —
「스캔이 실제로 훑은 파일 수가 N개 이상」 · 「allowlist 3건이 **실제로 매치된다**」.
allowlist 가 아무것도 안 잡으면 그것도 실패여야 한다(죽은 면제 = 낡은 가드의 신호).

## 작업

1. 스캐너를 구현한다 — 스코프(`src/trading`, `src/tasks`) 안에서 파생 필드명에 대한
   `.value` / `.name` 속성 접근을 AST 로 찾는다.
2. allowlist 를 붙이고 **사유 필수** 규약을 테스트로 집행한다.
3. 테스트를 채운다 (최소 5케이스):
   - 위반 0건 (본 단언)
   - **양성 대조**: 훑은 파일 수 하한
   - **양성 대조**: allowlist 3건이 전부 실제로 매치된다
   - allowlist 사유가 비면 실패한다
   - 스코프 밖(`backtest` 등)은 훑지 않는다
4. 실패 메시지에 **규칙 전문과 못 잡는 것**을 적어라 —
   `test_metric_guard_census.py` 의 `_CENSUS_RULE_FAILURE_MESSAGE` 가 정본 관용구다.
   ★**못 잡는 것을 반드시 적어라**: 별칭(`c = row.channel; c.value`) · `getattr` 동적 접근 ·
   스코프 밖 파일. 가드가 전능한 척하면 다음 사람이 그것을 믿는다.

## Acceptance Criteria

1. `test -f apps/api/tests/trading/test_no_strenum_value_access.py`
2. `cd apps/api && uv run --env-file .env.local pytest tests/trading/test_no_strenum_value_access.py -q`
3. `cd apps/api && test "$(uv run --env-file .env.local pytest tests/trading/test_no_strenum_value_access.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 5`
4. `cd apps/api && uv run --env-file .env.local pytest tests/trading -q`
5. `git diff --quiet -- apps/api/src`

## `summary` 에 반드시 담을 것

- 스코프 안에서 실제로 나온 히트 수와 **각각의 판정**(위반 / allowlist / 스코프밖)
- 위 실측표(12건 전부 위양성)와 **다르면 그 차이**
- 가드가 **못 잡는 것** 목록

## 금지사항

- **`apps/api/src` 를 한 줄도 고치지 마라** (AC 5 가 집행한다).
- **`entry_completeness.py` 의 `.value` 를 「고쳐서」 위양성을 없애지 마라.** 이유: 그 코드는
  **옳다.** 옳은 코드를 가드에 맞춰 바꾸는 것은 가드가 틀렸다는 뜻이다. allowlist 를 써라.
- **스코프를 `apps/api/src` 전체로 넓히지 마라.** 이유: 위양성 9건이 되살아나고, 그것을
  allowlist 로 덮으면 **면제 목록이 규칙보다 커진다.**
- **`test_metric_guard_census.py` 를 고치지 마라** (다른 lane 소유).
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
