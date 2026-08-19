# Step 1: repo-ownership-getters — 소유권 검사를 Repository 질의로 내린다

이 phase 의 목표는 **[BL-762]** — `apps/api/src/trading/router.py` 가 Repository 를 직접
조립하는 11곳을 0으로 만드는 것이다. 라우터가 지금 하는 일 중 **가장 위험한 부분은
소유권 검사**다(주문/세션을 조회한 뒤 `acc.user_id != current_user.id` 를 라우터가 손으로 비교).
그 검사를 **Repository 질의 자체**로 내리면 다음 호출자가 검사를 빼먹을 수 없다.

이 step 은 getter 2종과 그 단위 테스트만 만든다. **라우터는 아직 건드리지 않는다.**

## 읽어야 할 파일

- `apps/api/src/trading/repositories/order_repository.py` — 특히 `list_by_user`(:529, ExchangeAccount join 패턴) · `get_by_id`(:312)
- `apps/api/src/trading/repositories/live_signal_session_repository.py` — `get_by_id`(:50) · `list_active_by_user`(:66)
- `apps/api/src/trading/repositories/kill_switch_event_repository.py` 의 `get_owned`(:111) — **이미 있는 같은 계열 getter**. 이름·시그니처·독스트링 톤을 여기에 맞춰라
- `apps/api/tests/trading/test_repository_kill_switch_ownership.py` — 같은 계열 단위 테스트의 관용구
- `apps/api/AGENTS.md` §3 (Repository = AsyncSession 유일 보유자)

## 작업

### 1) `OrderRepository.get_by_id_for_user`

```python
async def get_by_id_for_user(self, order_id: UUID, user_id: UUID) -> Order | None:
```

- `Order` → `ExchangeAccount` **join** 으로 `ExchangeAccount.user_id == user_id` 를 걸어
  한 질의에서 소유권까지 판정한다. join 방식은 같은 파일 `list_by_user`(:529) 를 그대로 미러해라.
- 남의 주문이면 `None` (존재를 알리지 않는다 — 라우터가 404 로 답한다).

### 2) `LiveSignalSessionRepository.get_by_id_for_user`

```python
async def get_by_id_for_user(self, session_id: UUID, user_id: UUID) -> LiveSignalSession | None:
```

- `LiveSignalSession` 은 `user_id` 컬럼을 직접 갖는다 — join 없이 `where(id==, user_id==)` 다.
- 남의 세션이면 `None`.

두 메소드 모두 한국어 독스트링 1~3줄로 「왜 소유권을 질의에 넣는가」를 적어라
(라우터에 두면 재사용자가 검사를 조용히 빼먹는다).

### 3) 단위 테스트

신규 파일 `apps/api/tests/trading/test_repository_ownership_getters.py` 에 **6종**을 만든다.
이름은 반드시 `_for_user_` 를 포함한다:

- `test_order_get_by_id_for_user_returns_owned_order`
- `test_order_get_by_id_for_user_rejects_other_users_order`
- `test_order_get_by_id_for_user_returns_none_for_missing_id`
- `test_live_session_get_by_id_for_user_returns_owned_session`
- `test_live_session_get_by_id_for_user_rejects_other_users_session`
- `test_live_session_get_by_id_for_user_returns_none_for_missing_id`

`db_session` 픽스처로 직접 repository 를 만들어 검증한다(HTTP 경유 금지 — 이건 단위 축이다).

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/trading/test_repository_ownership_getters.py -q
cd apps/api && n=$(uv run --env-file .env.local pytest tests/trading/test_repository_ownership_getters.py --collect-only -q 2>/dev/null | grep -c '::test_'); echo "collected=$n"; test "$n" -ge 6
cd apps/api && uv run --env-file .env.local pytest tests/trading -q
cd apps/api && uv run ruff check .
```

## 금지사항

- **기존 메소드(`get_by_id` 등)의 시그니처·동작을 바꾸지 마라.** 이유: 두 repository 의
  `get_by_id` 는 celery task·서비스 등 수십 곳이 쓴다. 이 phase 는 **추가만** 한다.
- **repository 생성자를 바꾸지 마라.** 이유: `OrderRepository(session)` 조립 지점이 코드+테스트에
  수십 곳이다. 인자를 늘리면 그 전부가 깨진다.
- `apps/api/src/trading/router.py` 를 수정하지 마라 — 라우터 교체는 step 2~4 가 한다.
- 커밋하지 마라(커밋은 러너 소관).
