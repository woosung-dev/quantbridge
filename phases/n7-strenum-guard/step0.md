# Step 0: 가드 대상 필드를 **models.py 에서 파생**시킨다 (하드코딩 금지)

## 읽어야 할 파일

- **`phases/n7-common.md`** — 이 회차 공통 금지사항·AC 규율. **먼저 읽어라**
- `apps/api/src/trading/models.py` — 이번 lane 의 **파생 원천**
- `apps/api/tests/tasks/test_no_module_level_loop_bound_state.py` — **AST 가드 관용구 정본.**
  베끼지 말고 열어서 모양을 따라라 (실패 메시지에 규칙을 적는 방식 · 공허성 단언)
- `apps/api/tests/common/test_metric_guard_census.py` — 같은 계열의 성숙한 census 구현.
  ★단 **이 파일은 다른 lane 이 동시에 고치고 있다. 읽기만 해라.**

## 이 lane 이 만드는 파일

- `apps/api/tests/trading/test_no_strenum_value_access.py` (**신규 · 이 lane 의 유일한 산출**)

## 배경 — [BL-453] 이 무엇인가

`trading/models.py` 의 일부 필드는 **StrEnum 으로 주석돼 있지만 컬럼은 평문 `String(N)`** 이다.
PG enum 을 안 만든 이유는 `LiveSignalInterval` 이 밟은 자동 enum cast(`UndefinedObjectError`)
함정을 피하려는 것이었다(models.py:542 주석). 대가는 이것이다 — **새 세션이 재조회한 행은
plain `str` 로 온다.** 그 값에 `.value` / `.name` 을 쓰면 `AttributeError` 로 죽는다.

★**이건 가정이 아니다.** `models.py:854` 가 적어 뒀다 —
「dogfood 에서 실제로 `_alert_new_exchange_exits` 가 이 경로로 매 사이클 죽었다」.

## 착수 전 실측 (2026-08-24 · CONTROL)

★**파생 규칙 = StrEnum 주석 + `Field(sa_column=Column(..., String(N), ...))`.** 이 규칙으로
`models.py` 를 훑으면 **정확히 6건**이 나오고, 그 6건은 사람이 손으로 단 `★BL-453` 가드 주석
6곳과 **1:1로 일치**한다(주석은 각 선언 바로 윗줄).

| 클래스.필드 | enum | 컬럼 | 선언 | 가드 주석 |
| --- | --- | --- | --- | --- |
| `LiveSignalSession.interval` | `LiveSignalInterval` | `String(8)` | `models.py:543` | `:542` |
| `LiveSignalEvent.status` | `LiveSignalEventStatus` | `String(16)` | `:706` | `:705` |
| `AlertRule.rule_type` | `AlertRuleType` | `String(32)` | `:763` | `:762` |
| `AlertRule.channel` | `AlertChannel` | `String(16)` | `:769` | `:768` |
| `ExchangeExit.classification` | `ExitClassification` | `String(24)` | `:855` | `:853` |
| `ExchangeExit.attribution_confidence` | `ExitAttribution` | `String(16)` | `:878` | `:877` |

★★**안전한 것을 잡으면 안 된다.** `models.py` 의 StrEnum 필드 **7건**은 `sa_column` 이
**아예 없다**(`exchange`·`mode`·`side`·`type`·`state`·`trigger_type`·`exchange`). SQLModel 이
컬럼을 자동 생성하면 **native PG enum** 이 되고 SQLAlchemy 가 로드 시 **재캐스팅**한다 ⇒
그 필드들의 `.value` 는 **정상이다.** 잡으면 위양성이다.

★★★**`deactivated_reason` 은 대상이 아니다** — `models.py:576` 이 `str | None` 으로 주석돼
있다(enum 주석이 아니다). 파생 규칙이 자동으로 제외한다. **손으로 넣지 마라.**

## 작업

1. **먼저 위 표를 네가 다시 재라.** `models.py` 를 열어 6건이 맞는지 확인해라.
   ★**다르면 네 값이 맞다** — `summary` 맨 앞에 그 사실과 측정 방법을 적어라.
2. 테스트 파일을 신설하고, 이 step 에서는 **파생부만** 만든다:
   - `models.py` 를 `ast` 로 파싱해 「StrEnum 주석 + `Column(..., String(N), ...)`」 필드
     집합을 **파생**하는 헬퍼
   - 테스트 ⑴ — 파생 결과가 **6건 이상**이고 위 6개 필드명을 **전부 포함**한다
   - 테스트 ⑵ — **공허성 방어**: 파생 집합이 비면 실패한다. 그리고 `sa_column` 없는
     StrEnum 필드(위 7건)가 파생 집합에 **들어오지 않는다**
3. ★**필드 이름을 테스트에 하드코딩한 상수로만 두지 마라.** 하드코딩하면 `models.py` 가
   바뀔 때 가드가 조용히 낡는다. **파생이 정본이고, 표는 그 파생을 검증하는 대조군**이다.

## Acceptance Criteria

1. `test -f apps/api/tests/trading/test_no_strenum_value_access.py`
2. `cd apps/api && uv run --env-file .env.local pytest tests/trading/test_no_strenum_value_access.py -q`
3. `cd apps/api && test "$(uv run --env-file .env.local pytest tests/trading/test_no_strenum_value_access.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 2`
4. `git diff --quiet -- apps/api/src`

★AC 4 는 **이 lane 이 소스를 한 줄도 안 고친다**는 계약이다. 이 lane 은 테스트만 만든다.

## `summary` 에 반드시 담을 것

- 재측정한 파생 결과 (건수 + 필드 목록). 위 표와 **다르면 그 차이를 맨 앞에**
- 파생 규칙을 어떻게 구현했는지 (어떤 AST 노드를 봤는지)
- 위양성 후보로 의심되지만 이 step 에서 판정하지 않은 것

## 금지사항

- **`apps/api/src` 를 한 줄도 고치지 마라.** 이유: 이 lane 은 **가드 lane** 이다. 소스를
  고치면 재-pin 대상이 되고, 무엇이 가드의 효과인지 알 수 없게 된다.
  ★소스에서 결함을 발견하면 **고치지 말고 `summary` 에 적어라.**
- **`apps/api/tests/common/test_metric_guard_census.py` 를 고치지 마라.** 이유: **다른 lane 이
  같은 회차에 그 파일을 고치고 있다.** 병합이 충돌한다. 읽기 전용이다.
- **필드 목록을 하드코딩만 하고 파생을 생략하지 마라.** 이유: 그러면 `models.py` 에 새 String
  컬럼이 생겨도 가드가 못 잡는다 — 이 항목의 Trigger 자체가 「새 코드가 추가될 때」다.
- `phases/n7-common.md` 의 공통 금지사항 전부.
- 커밋하지 마라(커밋은 러너 소관).
