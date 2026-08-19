# Step 4: live-session-read-axis — 남은 Repository 직접 조립 4곳을 없앤다

이 phase 의 목표는 **[BL-762]** — `apps/api/src/trading/router.py` 의 `Repository()` 직접 조립을
0으로 만드는 것이다. 이전 step 들이 orders·kill-switch 축을 끝냈고, 이 step 이 마지막
**4곳**(`get_live_session_state` 의 `LiveSignalSessionRepository` + `OrderRepository`,
`list_live_session_events` 의 `LiveSignalSessionRepository` + `LiveSignalEventRepository`)을 없앤다 ⇒ **0**.

## 읽어야 할 파일

- `apps/api/src/trading/router.py` — `get_live_session_state` · `list_live_session_events`
- `apps/api/src/trading/dependencies.py` — 특히 `get_alert_rule_service` · `get_outcome_parity_service`
  (읽기 전용 서비스 factory 의 관용구)
- `apps/api/src/trading/services/alert_rule_service.py` — 얇은 읽기 서비스의 관용구
- `apps/api/src/trading/repositories/order_repository.py` — `list_filled_realized_for_session`(:559) · `SessionScope`(:69)
- `apps/api/src/trading/repositories/live_signal_session_repository.py` — `get_state`(:296) · 이전 step 의 `get_by_id_for_user`
- `apps/api/src/trading/repositories/live_signal_event_repository.py` — `list_by_session_with_order_state`(:139)
- `apps/api/src/trading/equity_calculator.py` — `recompute_equity_curve` · `label_curve_provenance` · `RealizedPnlSource`
- `apps/api/tests/trading/test_router_live_session_state_real_pnl.py` — 이 경로의 종단 회귀(타 사용자 404 · BL-445 커브 분리)

## 작업

### 1) 신규 파일 `apps/api/src/trading/services/live_session_query_service.py`

한국어 모듈 독스트링 1~3줄 + 다음 서비스:

```python
class LiveSessionQueryService:
    def __init__(
        self,
        session_repo: LiveSignalSessionRepository,
        order_repo: OrderRepository,
        event_repo: LiveSignalEventRepository,
    ) -> None: ...

    async def get_state_for_user(
        self, session_id: UUID, user_id: UUID
    ) -> LiveSignalStateResponse | None: ...

    async def list_events_for_user(
        self, session_id: UUID, user_id: UUID, *, limit: int
    ) -> LiveSignalEventListResponse | None: ...
```

- 세션이 없거나 남의 것이면 **`None`** 을 반환한다(라우터가 404 로 답한다).
  소유권은 이전 step 이 만든 `session_repo.get_by_id_for_user(session_id, user_id)` 로 판정한다.
- `AsyncSession` 을 import 하지 마라 — 서비스는 repository 만 갖는다(`AGENTS.md` §3).

★**`router.py` 의 equity-curve 재계산 블록(`BL-445` 주석부터 `LiveSignalStateResponse(...)`
반환까지)은 한 글자도 바꾸지 말고 통째로 옮겨라** — 주석 포함. 이유: 그 블록은
`confirmed + estimated == total` 항등식이 **대입이 아니라 산술로** 성립하도록 짜여 있고,
`rows` 한 리스트에서 커브·소계·라벨을 함께 파생시킨다. 같은 2절 필터를 복제하거나 순서를
바꾸면 라벨이 조용히 어긋난다. `state is None` 일 때의 빈 응답(`evaluated=False`, `schema_version=0`,
`total_realized_pnl=Decimal("0")`, `equity_curve=[]`, `updated_at=None`)도 그대로 유지한다.

### 2) `dependencies.py` 에 factory 1개 추가

```python
async def get_live_session_query_service(
    session: AsyncSession = Depends(get_async_session),
) -> LiveSessionQueryService:
    return LiveSessionQueryService(
        session_repo=LiveSignalSessionRepository(session),
        order_repo=OrderRepository(session),
        event_repo=LiveSignalEventRepository(session),
    )
```

### 3) 라우터 2 endpoint 교체

- `session: AsyncSession = Depends(get_async_session)` 제거 →
  `service: LiveSessionQueryService = Depends(get_live_session_query_service)`
- `None` 이면 지금과 같은 `HTTPException(status_code=404, detail="live session not found")`
- 두 endpoint 의 `response_model`·docstring 은 그대로 둔다.
- 라우터에서 쓰이지 않게 된 import(`OrderRepository`, `SessionScope`, `recompute_equity_curve`,
  `label_curve_provenance`, `RealizedPnlSource`, `AsyncSession`, `get_async_session`,
  `Decimal` 등)는 **실제로 더 이상 안 쓰는 것만** 지운다(`ruff check` 가 판정한다).

## Acceptance Criteria

```bash
n=$(grep -c 'Repository(' apps/api/src/trading/router.py); echo "remaining=$n"; test "$n" = "0"
cd apps/api && uv run --env-file .env.local pytest tests/trading/test_router_live_session_state_real_pnl.py -q
cd apps/api && uv run --env-file .env.local pytest tests/trading -q
cd apps/api && uv run ruff check .
```

## 금지사항

- **equity-curve 계산식을 「정리」하지 마라.** 이유 위 참조(BL-445/BL-458 회귀).
- **`LiveSignalSessionService`(`services/live_session_service.py`)의 생성자에 `order_repo` 를
  더하지 마라.** 이유: 그 생성자 조립 지점이 17곳(테스트 16 포함)이라 전부 깨진다. 그래서
  읽기 전용 신규 서비스를 따로 두는 것이다.
- **404 를 도메인 예외로 바꾸지 마라** — 응답 body 형상이 달라진다.
- 이미 서비스를 쓰는 endpoint(`positions` · `close` · `alert-rules`)는 건드리지 마라.
- 커밋하지 마라(커밋은 러너 소관).
