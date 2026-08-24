# Step 0: raw metric census 가드 신설

## 읽어야 할 파일

- `phases/n9-common.md` — 전 lane 공통 규약·금지
- `apps/api/AGENTS.md` — §4 표의 「관측 metric」 행이 **이 회차가 집행할 규칙 본문**이다
- `apps/api/src/common/metrics_multiproc.py` — `record_metric_safely` 정의
- `apps/api/src/tasks/live_signal.py` — 측정 대상
- `apps/api/tests/common/test_repository_boundary_guard.py` — **같은 형태의 선행 가드.**
  AST 수집기 + 동결 census + 양성 대조 구조를 여기서 베껴라

## 작업

`apps/api/tests/common/test_metric_safety_guard.py` 를 **새로** 만든다. 이 step 은
**가드만 세운다 — `apps/api/src` 를 한 글자도 고치지 마라.**

집행할 규칙(`apps/api/AGENTS.md` §4):

> 업무 **결과를 보고하는** `try` 본문·`except` 본문에서 metric mutation 을 raw 로 두지 마라 —
> `record_metric_safely` 로 감싼다. 이유: metric 실패 예외가 그 handler 로 흘러 **체결을 취소 실패로
> 오기록**하거나 계정 스윕을 중단시킨다.

### 모듈 레벨 함수 2개를 반드시 이 이름으로 노출해라

러너의 AC 가 이 둘을 **직접 import 해서** 판정한다. 이름·시그니처를 바꾸면 AC 가 깨진다.

```python
def all_metric_sites() -> list[tuple[str, int]]:
    """스캔 대상에서 찾은 **모든** qb_* metric mutation 호출. (상대경로, lineno)."""

def raw_metric_sites() -> list[tuple[str, int]]:
    """그중 `try`/`except`/`finally` 본문 안에 있으면서 `record_metric_safely` 로
    감싸이지 **않은** 것. 이것이 위반 census 다."""
```

### 판정 규칙 (벗어나면 안 되는 계약)

- **구조는 `ast` 로 재라. 문자열 검색 금지.** 이유: `record_metric_safely(\n  qb_x.dec\n)` 처럼
  줄이 나뉘면 grep 이 「감싸이지 않았다」고 **거짓 보고**한다 — 이 회차의 재료 실측이 실제로 그렇게
  한 번 틀렸다.
- metric 객체 판별 = 호출 체인의 **뿌리 이름이 `qb_` 로 시작**. `qb_x.inc()` 와
  `qb_x.labels(...).inc()` 를 **둘 다** 잡아야 한다.
- mutation 메서드 = `inc` · `dec` · `observe` · `set`.
- 문맥 = `ast.Try` 의 `body` · `handlers[].body` · `finalbody` **안쪽**(중첩 `if`/`for` 안도 포함).
  `orelse` 는 제외한다 — 예외가 지나가지 않는 자리다.
- 감싸임 판별 = 그 호출이 `record_metric_safely(...)` 의 **인자**로 전달된 형태.
- 스캔 대상은 `apps/api/src/tasks/live_signal.py` 하나로 **좁혀라**. 이유: 다른 파일로 넓히면
  lane 2 의 디렉터리와 겹쳐 병합이 깨진다.

### 테스트는 최소 3개

1. **양성 대조** — `all_metric_sites()` 가 30건 이상을 찾는다. *이것이 없으면 수집기가 죽어도 초록이다.*
2. **동결 census** — `raw_metric_sites()` 가 **정확히 15건**이다. 이 step 에서는 15가 맞다.
3. **수집기 자체 단위 검사** — 인라인 소스 문자열을 `ast.parse` 해서, ⑴ `try` 밖의 raw 호출은
   안 세고 ⑵ `record_metric_safely` 로 감싼 것은 안 세며 ⑶ `labels(...).inc()` 형태는 센다는 것을
   보여라. 실트리에 의존하지 않는 검사가 하나는 있어야 수집기의 판별력을 증명한다.

## Acceptance Criteria

- `test -f apps/api/tests/common/test_metric_safety_guard.py`
- `cd apps/api && uv run --env-file .env.local pytest tests/common/test_metric_safety_guard.py -q`
- 수집된 테스트 ≥3
- `cd apps/api && uv run python -c "from tests.common.test_metric_safety_guard import all_metric_sites, raw_metric_sites; import sys; sys.exit(0 if len(all_metric_sites())>=30 and len(raw_metric_sites())==15 else 1)"`
- `git diff --quiet -- apps/api/src`

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. ★최종 판정은 러너가 재실행해 내린다 —
   `status` 를 `completed` 로 바꾸지 마라.
2. 프로젝트 규약을 벗어나지 않았는지 확인한다: 디렉터리 구조 · 허용된 스택 · 규칙 파일의 필수 항목.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 **즉시 중단**한다.

## 금지사항

- **`apps/api/src` 를 수정하지 마라. 이유:** 이 step 의 AC `git diff --quiet -- apps/api/src` 가
  그것을 잰다. 수리는 step 1 이다. 가드를 세우는 회차가 대상을 함께 고치면 **가드가 red 를 낸 적이
  없는 채로** 초록이 되어 판별력을 증명할 수 없다.
- **census 를 15가 아닌 값으로 맞추려고 판정 규칙을 느슨하게 하지 마라. 이유:** 15는 CONTROL 이
  AST 로 실측한 값이다. 수가 다르면 **네 수집기가 틀린 것**이다 — 규칙을 바꾸지 말고 수집기를 고쳐라.
  정말로 15가 틀렸다고 판단하면 `blocked` 로 세우고 근거를 적어라.
- **`all_metric_sites` · `raw_metric_sites` 의 이름을 바꾸지 마라. 이유:** 러너 AC 가 import 한다.
- 커밋하지 마라(커밋은 러너 소관).
