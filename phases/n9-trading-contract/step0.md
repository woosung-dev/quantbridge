# Step 0: [BL-453] StrEnum-on-String 컬럼 선언 계약 가드

## 읽어야 할 파일

- `phases/n9-common.md` — 전 lane 공통 규약·금지
- `docs/backlog.md` 의 `### BL-453` 절 — 권장안 (a)(b)(c) 중 **이 step 은 (b) 정적 가드**다
- `apps/api/src/trading/models.py` — 대상. `grep -n 'BL-453' apps/api/src/trading/models.py` 가 계약 6곳을 짚는다
- `apps/api/tests/common/test_repository_boundary_guard.py` — **같은 형태의 선행 가드.**
  AST 수집기 + 동결 census + 양성 대조 구조를 여기서 베껴라

## 배경 (결함)

이 레포에는 `sa_column=Column(..., String(N))` 위에 **StrEnum 타입 주석**을 얹은 컬럼이 있다.
같은 세션이면 파이썬 객체가 enum 이지만 **새 세션이 재조회하면 plain `str`** 로 온다(재캐스팅 없음).
그때 `.value` / `.name` 을 만지면 `AttributeError` 로 죽는다 — dogfood 에서
`_alert_new_exchange_exits` 가 실제로 매 사이클 이 경로로 죽었다.

지금 그 계약은 **주석 6줄로만** 존재하고 **기계가 재지 않는다.**

## ★CONTROL 이 이미 실측해 기각한 접근 — 다시 하지 마라

「6개 필드명에 대한 `.value`/`.name` 접근을 금지한다」는 **사용처 가드는 성립하지 않는다.**
`apps/api/src` 전량 AST 실측 결과 12건이 걸렸고 **12건 전부 위양성**이었다:

- `bt.status.value` · `run.status.value` (backtest·optimizer·stress_test) — 그 `status` 는
  **진짜 Enum 컬럼**이라 `.value` 가 정당하다
- `tally.channel.value` (`entry_completeness.py`) — `tally` 는 `ChannelTally` 라는 **로컬 dataclass** 다

⇒ 필드 **이름만으로는** 소유 클래스를 못 가른다. 이 step 은 **선언 지점**을 잰다.

## 작업

`apps/api/tests/trading/test_strenum_column_contract.py` 를 **새로** 만든다.
**`apps/api/src` 를 한 글자도 고치지 마라** — 이 step 은 가드만 세운다.

### 모듈 레벨 함수 2개를 반드시 이 이름으로 노출해라

러너 AC 가 이 둘을 **직접 import 해서** 판정한다.

```python
def strenum_string_columns() -> list[tuple[str, str]]:
    """`sa_column=Column(..., String(...))` 위에 StrEnum 주석이 얹힌 필드 전부.
    (클래스명, 필드명)."""

def uncontracted_columns() -> list[tuple[str, str]]:
    """그중 **BL-453 계약 주석을 달지 않은** 것. 이것이 위반 census 다."""
```

### 판정 규칙 (벗어나면 안 되는 계약)

- **구조는 `ast` 로 재라.** 대상 파일은 `apps/api/src/trading/models.py` 하나로 **좁혀라**.
- StrEnum 판별은 **`models.py` 안에서 import·정의된 이름**을 실제로 해석해 `issubclass(x, StrEnum)`
  으로 재라. 이름이 `...Status`/`...Type` 로 끝나는지 같은 **작명 규칙에 기대지 마라** — 그것은
  문자열 검색과 같은 종류의 우회 가능한 판정이다.
- `Column(...)` 의 두 번째 위치 인자(또는 `type_=`)가 `String(...)` 인 것만 대상이다.
  `sa.Enum(...)` 컬럼은 **대상이 아니다**(그쪽은 `.value` 가 정당하다).
- 계약 주석 판별 = 그 필드 **바로 위 주석 블록**에 `BL-453` 이 있다. 파일 어디든 있으면 통과시키는
  느슨한 판정을 쓰지 마라 — 그러면 파일 상단 주석 하나로 전건이 통과한다.

### 테스트는 최소 3개

1. **양성 대조** — `strenum_string_columns()` 가 **6건 이상**을 찾는다.
   *이것이 없으면 수집기가 죽어도 「위반 0」으로 초록이다.*
2. **동결 census** — `uncontracted_columns()` 가 **0건**이다.
3. **수집기 자체 단위 검사** — 인라인 소스 문자열을 `ast.parse` 해서, ⑴ `sa.Enum` 컬럼은 안 세고
   ⑵ StrEnum + `String()` 조합은 세며 ⑶ 계약 주석이 없으면 위반으로 낸다는 것을 보여라.

## Acceptance Criteria

- `test -f apps/api/tests/trading/test_strenum_column_contract.py`
- `cd apps/api && uv run --env-file .env.local pytest tests/trading/test_strenum_column_contract.py -q`
- 수집된 테스트 ≥3
- `cd apps/api && uv run python -c "from tests.trading.test_strenum_column_contract import strenum_string_columns, uncontracted_columns; import sys; sys.exit(0 if len(strenum_string_columns())>=6 and len(uncontracted_columns())==0 else 1)"`
- `git diff --quiet -- apps/api/src`

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. `strenum_string_columns()` 가 낸 목록을 `grep -n 'BL-453' apps/api/src/trading/models.py` 의
   6곳과 **대조**해라. 수가 다르면 수집기가 틀렸거나 계약이 빠진 필드를 찾은 것이다 —
   후자라면 그것이 **진짜 발견**이니 `summary` 에 적어라.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`apps/api/src` 를 수정하지 마라. 이유:** AC `git diff --quiet -- apps/api/src` 가 그것을 잰다.
  계약 주석이 빠진 필드를 찾았다면 **주석을 달지 말고** `summary` 에 적어라 — 가드를 세우는 step 이
  대상을 함께 고치면 가드가 red 를 낸 적 없이 초록이 되어 판별력을 증명할 수 없다.
- **위에 기각된 「필드명 기반 사용처 가드」를 만들지 마라. 이유:** CONTROL 이 실측했고 위양성 12/12 다.
- **`strenum_string_columns` · `uncontracted_columns` 의 이름을 바꾸지 마라. 이유:** 러너 AC 가 import 한다.
- 커밋하지 마라(커밋은 러너 소관).
