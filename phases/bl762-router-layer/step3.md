# Step 3: kill-switch-axis — kill-switch 2 endpoint 에서 Repository 직접 조립을 걷어낸다

이 phase 의 목표는 **[BL-762]** — `apps/api/src/trading/router.py` 가 `Repository()` 를 직접
만드는 자리를 0으로 만드는 것이다(`AGENTS.md` §3: Router 는 DB 접근 금지 · Depends 조립은
`dependencies.py` 가 유일). 이 step 은 kill-switch 축 **2곳**(`router.py` 의
`list_kill_switch_events` · `resolve_kill_switch` — `KillSwitchEventRepository(session)` 2회)을
없앤다. 이전 step 들이 orders 축을 끝냈으므로 남은 수가 **6 → 4** 가 된다.

## 읽어야 할 파일

- `apps/api/src/trading/router.py` — `list_kill_switch_events` · `resolve_kill_switch`
- `apps/api/src/trading/kill_switch.py` — `KillSwitchService`(:204, 생성자 :213, `ensure_not_gated` :225)
- `apps/api/src/trading/dependencies.py` — `get_kill_switch_service`(**이미 있다** — 새로 만들지 마라)
- `apps/api/src/trading/repositories/kill_switch_event_repository.py` — `list_recent_by_user`(:83) · `get_owned`(:111) · `resolve`(:62) · `get_by_id`(:29) · `commit`
- `apps/api/tests/trading/test_router_kill_switch.py` — `publish_realtime` 를 monkeypatch 하는 방식
- `apps/api/tests/trading/test_router_layer_contract.py` — 이전 step 이 못박은 교차 사용자 404

## 작업

### 1) `KillSwitchService` 에 메소드 2종 **추가** (생성자는 손대지 마라)

```python
@dataclass(frozen=True)
class ResolveOutcome:
    kind: Literal["not_owned", "already_resolved", "resolved"]
    event: KillSwitchEvent | None = None


class KillSwitchService:
    async def list_events_for_user(
        self, user_id: UUID, *, limit: int, offset: int
    ) -> Sequence[KillSwitchEvent]: ...

    async def resolve_for_user(
        self, event_id: UUID, *, user_id: UUID, note: str | None
    ) -> ResolveOutcome: ...
```

`resolve_for_user` 의 순서는 **지금 라우터가 하는 것과 같아야 한다**:

1. `self._events_repo.get_owned(event_id, user_id=user_id)` — `None` 이면 `ResolveOutcome("not_owned")`
2. `rowcount = await self._events_repo.resolve(event_id, note=note)` → `await self._events_repo.commit()`
3. `rowcount == 0` 이면 `ResolveOutcome("already_resolved")`
4. `rowcount == 1` 이면 `self._events_repo.get_by_id(event_id)` 로 재조회해
   `ResolveOutcome("resolved", event=fetched)`. 재조회가 `None` 이면 `event=None` 으로 두고
   라우터가 지금처럼 500 을 낸다.

`ResolveOutcome` 은 `kill_switch.py` 안에 둔다(신규 파일 금지).

### 2) 라우터 2 endpoint 교체

- 두 endpoint 의 `session: AsyncSession = Depends(get_async_session)` 을 없애고
  `service: KillSwitchService = Depends(get_kill_switch_service)` 로 바꾼다.
- ★**`publish_realtime(...)` 호출은 라우터에 그대로 남겨라.** 이유:
  `apps/api/tests/trading/test_router_kill_switch.py:79` 가 문자열 경로
  `"src.trading.router.publish_realtime"` 를 monkeypatch 한다 — 서비스로 옮기면 그 테스트가
  `AttributeError` 로 죽는다. 발행 조건(취소가 실제로 일어난 경우에만)과 payload
  (`{"event_id": str(event_id), "trigger_type": <trigger_type>.value}`) 도 지금과 같아야 한다.
- 응답도 지금과 **바이트 단위로 같아야 한다**:
  - 미소유 → `HTTPException(404, "event not found")`
  - 이미 resolved → `HTTPException(404, "event not found or already resolved")`
  - 목록 응답의 키 4종(`items`/`total`/`limit`/`offset`)과 `total = len(events)` 계산도 그대로.

## Acceptance Criteria

```bash
n=$(grep -c 'Repository(' apps/api/src/trading/router.py); echo "remaining=$n"; test "$n" = "4"
cd apps/api && uv run --env-file .env.local pytest tests/trading -q
cd apps/api && uv run --env-file .env.local pytest tests/common/test_metric_guard_census.py -q
cd apps/api && uv run ruff check .
```

## 금지사항

- **`KillSwitchService.__init__` 시그니처를 바꾸지 마라.** 이유: `OrderService` 조립과
  `tests/trading/test_kill_switch_service.py` 등 여러 곳이 지금 인자로 만든다. 메소드 추가만 한다.
- **`ensure_not_gated` 를 건드리지 마라.** 이유: 그 경로는 발주 게이트(돈이 나가는 자리)이고
  이 phase 의 범위가 아니다.
- **`publish_realtime` 를 서비스로 옮기지 마라**(위 이유).
- **404 문구 2종을 하나로 합치지 마라.** 이유: 지금 두 분기가 다른 문장을 쓴다 — 합치면
  응답 계약이 바뀐다.
- orders·live-session endpoint 는 이 step 에서 건드리지 마라.
- 커밋하지 마라(커밋은 러너 소관).
