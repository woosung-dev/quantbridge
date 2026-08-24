# Step 0: boundary-census — Repository 경계 위반을 AST 로 센다

## 읽어야 할 파일

- **`phases/n8-common.md`** — 이 회차 공통 금지사항·AC 규율. **먼저 읽어라**
- `apps/api/AGENTS.md` §3 — 3-Layer 표준 + **★ 예외 디렉터리 표**(이 step 의 스코프를 정한다)
- `apps/api/tests/common/test_metric_guard_census.py` — **AST census + 동결 래칫의 레포 관용구**
- `apps/api/src/trading/repositories/` — 11개 repository. 쿼리가 살아야 할 자리
- `apps/api/src/trading/dependencies.py` · `kill_switch.py` · `websocket/state_handler.py` · `websocket/reconciliation.py`

## 배경 — 왜 이 축인가

루트 `AGENTS.md` §3 NEVER: 「Repository layer 밖에서 DB 접근. **이유:** service 가 세션을
쥐면 DB 없이 단위 테스트가 불가능해진다」. 이 규칙에 **기계 집행이 없다.**

★**CONTROL 사전 실측 — 이것이 위양성이 아닌 근거:** 8개 도메인의 `dependencies.py` 중
**7개가 `select(` 0건**이고 `trading/dependencies.py` 만 4건이다. 관용구가 아니라 이상치다.

## 작업

`apps/api/tests/common/test_repository_boundary_guard.py` 를 **새로** 만든다.
이 step 은 **census 만** 만든다. 코드를 옮기지 않는다(옮기는 것은 step 2·3).

### 스코프 — 이 결정은 확정이다. 바꾸지 마라

**검사 대상** = `apps/api/src/**/*.py` 중 아래를 **제외**한 것:

- 파일명·경로에 `repositor` 가 들어가는 것 (경계 안쪽이므로 당연히 허용)
- `apps/api/AGENTS.md` §3 예외 표의 디렉터리: `market_data/` · `realtime/` · `health/` ·
  `tasks/` · `scripts/` · `common/` · `core/`

★**`tasks/` 를 제외하는 이유**를 오해하지 마라 — 예외 표는 「7파일 표준의 예외」지
「DB 규칙의 면제」가 아니다. 다만 Celery entrypoint 의 세션 사용은 별도 설계 축이라
**이 회차의 범위 밖**이다. 그래서 스코프에서 뺀다. 이 판단을 step 안에서 뒤집지 마라.

### 반드시 `ast` 로 판정해라 — `grep` 금지

`select` 라는 이름은 numpy 등에도 있다(`optimizer/engine/genetic.py` 실측). 그래서:

1. 모듈의 `Import`/`ImportFrom` 를 훑어 **`sqlmodel` 또는 `sqlalchemy` 에서 온 `select`**
   (또는 그 별칭)를 바인딩한 이름을 구한다.
2. `Call` 노드의 `func` 가 그 이름일 때만 위반으로 센다.

이렇게 하면 `from numpy import select` 같은 동명이인이 걸러진다.

### 이 step 이 남겨야 할 테스트 (2개 이상)

1. **양성 대조** — 스캔한 `.py` 파일이 **60개 이상**이고, 위반을 **6건 이상** 찾았다.
   (0건 통과를 구조적으로 막는다.)
2. **제어군** — `apps/api/src/*/dependencies.py` 8개 중 위반이 있는 것은
   **`trading/dependencies.py` 하나뿐**이다. (나머지 7개가 0건이라는 것이 이 축이
   관용구가 아님을 증명한다.)

★**CONTROL 실측은 4파일 8건**(`trading/dependencies.py` 4 · `kill_switch.py` 2 ·
`websocket/state_handler.py` 1 · `websocket/reconciliation.py` 1)이다. **믿지 말고 다시 재라.**
실측이 다르면 `summary` 에 차이를 적어라.

## Acceptance Criteria

```bash
test -f apps/api/tests/common/test_repository_boundary_guard.py
cd apps/api && uv run --env-file .env.local pytest tests/common/test_repository_boundary_guard.py -q
cd apps/api && test "$(uv run --env-file .env.local pytest tests/common/test_repository_boundary_guard.py --collect-only -q 2>/dev/null | grep -c '::')" -ge 2
git diff --quiet -- apps/api/src
```

## 자기 점검

1. AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. 파일 수·위반 수 하한 단언이 있는지 확인한다 — 없으면 이 가드는 무증거다.
3. blocked 사유가 생기면 즉시 중단한다.

## 금지사항

- **`apps/api/src` 를 수정하지 마라.** 이유: 이 step 은 census 만 만든다. AC 가 집행한다.
- **`grep` 으로 `select(` 를 세지 마라.** 이유: 동명이인이 위양성을 만든다(실측 `optimizer/engine/genetic.py` 2건).
- **스코프를 넓히지 마라.** 이유: `tasks/` 를 넣으면 lane 이 별도 설계 축을 떠안는다.
- `phases/n8-common.md` 의 공통 금지사항 전부.
