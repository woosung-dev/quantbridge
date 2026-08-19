# Step 2: orders-axis — orders 3 endpoint 에서 Repository 직접 조립을 걷어낸다

이 phase 의 목표는 **[BL-762]** — `apps/api/src/trading/router.py` 가 `Repository()` 를 직접
만드는 11곳을 0으로 만드는 것이다(`AGENTS.md` §3: 「Router 는 DB 접근 금지」·「AsyncSession 은
Repository 만 보유」·「Depends() 조립의 유일한 위치는 dependencies.py」).

이 step 은 그중 **orders 축 5곳**(`router.py:296, 314, 315, 336, 337`)을 없앤다 — 11 → **6**.

## 읽어야 할 파일

- `apps/api/src/trading/router.py` — `list_orders` · `get_order` · `cancel_order` 세 endpoint
- `apps/api/src/trading/services/order_service.py` — `OrderService`(생성자 :53 · `execute` :69)
- `apps/api/src/trading/dependencies.py` — `get_order_service`
- `apps/api/src/trading/repositories/order_repository.py` — 이전 step 이 추가한
  `get_by_id_for_user` · 기존 `list_by_user` · `transition_pending_to_cancelled`(:1020) · `commit`
- `apps/api/tests/trading/test_router_layer_contract.py` — 이전 step 이 못박은 계약(202 body 문자열·교차 사용자 404)
- `apps/api/tests/trading/test_router_cancel_cf4.py` · `test_router_cancel_metric_failure.py` · `test_router_orders.py`

## 작업

### 1) `OrderService` 에 메소드 3종 **추가** (생성자는 절대 손대지 마라)

```python
@dataclass(frozen=True)
class CancelOutcome:
    kind: Literal["not_found", "exchange_requested", "cancelled", "conflict"]
    order: Order | None = None


class OrderService:
    async def list_for_user(
        self, user_id: UUID, *, limit: int, offset: int,
        states: Sequence[OrderState] | None = None,
    ) -> tuple[Sequence[Order], int]: ...

    async def get_for_user(self, order_id: UUID, user_id: UUID) -> Order | None: ...

    async def cancel_for_user(self, order_id: UUID, user_id: UUID) -> CancelOutcome: ...
```

`cancel_for_user` 의 순서는 **지금 라우터가 하는 것과 같아야 한다**:

1. `repo.get_by_id_for_user(order_id, user_id)` — `None` 이면 `CancelOutcome("not_found")`
2. `order.state == OrderState.submitted` 이면 `from src.tasks.trading import cancel_order_task`
   (함수 안 로컬 import — 지금 라우터가 그렇게 한다) 후 `cancel_order_task.delay(str(order_id))`
   → `CancelOutcome("exchange_requested")`. ★DB 를 건드리지 마라(거래소에 live 인 주문의
   DB-only cancel 은 orphan position 을 만든다 — CF4).
3. 그 외에는 `repo.transition_pending_to_cancelled(order_id, cancelled_at=datetime.now(UTC))`
   → `await repo.commit()` → rowcount 가 0 이면 `CancelOutcome("conflict")`
4. rowcount 1 이면 `repo.get_by_id(order_id)` 로 재조회해 `CancelOutcome("cancelled", order=fetched)`.
   재조회가 `None` 이면 `CancelOutcome("cancelled", order=None)` 로 두고 라우터가 500 을 유지한다.

`CancelOutcome` 은 `order_service.py` 안에 둔다(신규 파일을 만들지 마라).

### 2) 라우터 3 endpoint 교체

- `list_orders` · `get_order` · `cancel_order` 의
  `session: AsyncSession = Depends(get_async_session)` 파라미터를 없애고
  `service: OrderService = Depends(get_order_service)` 로 바꾼다.
- 응답은 **바이트 단위로 지금과 같아야 한다**:
  - 404 는 계속 `raise HTTPException(status_code=404, detail="order not found")`
  - 202 는 계속 `JSONResponse(status_code=202, content={"order_id": ..., "state": OrderState.submitted.value, "detail": "exchange cancel requested"})`
  - 409 는 계속 `raise HTTPException(status_code=409, detail="cannot cancel in current state")`
  - 500 은 계속 `detail="order fetch failed after cancel"`
- ★**`record_metric_safely(qb_active_orders.dec)` 는 `cancel_order` 함수 안에 그대로 남겨라.**
  자리도 지금과 같아야 한다 — **커밋 뒤 · 409 분기 뒤**(취소가 확정된 경우에만 감소).
  이유 ⑴ `apps/api/tests/common/test_metric_guard_census.py:559` 가
  `("apps/api/src/trading/router.py", "cancel_order", "qb_active_orders")` 를 동결했고
  `test_protected_site_list_is_not_vacuous` 가 함수 이동을 red 로 잡는다.
  이유 ⑵ `tests/trading/test_router_cancel_metric_failure.py:71` 이
  `router_module.qb_active_orders` 를 monkeypatch 한다.

## Acceptance Criteria

```bash
n=$(grep -c 'Repository(' apps/api/src/trading/router.py); echo "remaining=$n"; test "$n" = "6"
cd apps/api && uv run --env-file .env.local pytest tests/trading -q
cd apps/api && uv run --env-file .env.local pytest tests/common/test_metric_guard_census.py -q
cd apps/api && uv run ruff check .
```

## 금지사항

- **`OrderService.__init__` 시그니처를 바꾸지 마라.** 이유: `OrderService(` 조립 지점이
  코드+테스트 21파일이다. 인자를 늘리면 그 전부가 깨진다. 메소드 추가는 아무것도 안 깨뜨린다.
- **`record_metric_safely(qb_active_orders.dec)` 를 서비스로 옮기지 마라.** 이유는 위 ⑴⑵.
- **404 를 도메인 예외(`OrderNotFound`)로 바꾸지 마라.** 이유: `AppException` 핸들러는 body 를
  `{"detail": {"code": ..., "detail": ...}}` 로 직렬화한다 — 지금 `{"detail": "order not found"}`
  와 **형상이 달라진다**. 이 phase 는 응답 계약을 바꾸지 않는다.
- kill-switch·live-session endpoint 는 이 step 에서 건드리지 마라(step 3·4 소관).
- 커밋하지 마라(커밋은 러너 소관).
