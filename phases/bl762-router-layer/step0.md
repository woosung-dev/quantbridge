# Step 0: contract-lock — 리팩터가 깨뜨릴 수 있는 계약을 테스트로 먼저 못박는다

이 phase 전체의 목표는 **[BL-762]** — `apps/api/src/trading/router.py` 가 Repository 를 직접
조립하는 11곳을 0으로 만드는 것이다. 이 step 은 **아직 리팩터를 하지 않는다.** 리팩터가
조용히 깨뜨릴 수 있는 계약 5종을 **지금 동작 그대로** 고정하는 회귀 테스트만 추가한다.

## 읽어야 할 파일

- `apps/api/src/trading/router.py` — 특히 `cancel_order`(:323 부근) · `get_order` · `list_kill_switch_events` · `resolve_kill_switch` · `list_live_session_events`
- `apps/api/tests/trading/test_router_orders.py` — 기존 orders 라우터 테스트(관용구 참조)
- `apps/api/tests/trading/test_router_cancel_cf4.py` — submitted/pending cancel 분기 테스트(픽스처 조립 관용구)
- `apps/api/tests/trading/test_router_kill_switch.py` — kill-switch 라우터 테스트
- `apps/api/tests/trading/test_router_live_session_state_real_pnl.py` — 타 사용자 세션 404 테스트(`_seed_session` 관용구)
- `apps/api/tests/conftest.py` 의 `authed_user` · `mock_authed_user` · `client` · `db_session` 픽스처

## 작업

신규 파일 **하나만** 만든다: `apps/api/tests/trading/test_router_layer_contract.py`

모듈 독스트링은 한국어로 쓰고, 「이 파일은 [BL-762] 라우터 계층 리팩터가 깨뜨릴 수 있는 계약을
고정한다」는 취지를 1~3줄로 적는다.

테스트 5종을 **정확히 이 이름으로** 만든다 (러너 AC 가 이름으로 수집을 센다):

1. `test_cancel_submitted_ack_detail_is_frozen`
   - `submitted` 상태 주문을 `POST /api/v1/orders/{id}/cancel` 로 취소 요청하면 **202** 와
     body `{"order_id": <uuid str>, "state": "submitted", "detail": "exchange cancel requested"}` 가 나온다.
   - ★`detail` 문자열을 **리터럴로** 단언해라. 이유: 프론트가
     `apps/web/src/features/trading/schemas.ts:62` 에서 `z.literal("exchange cancel requested")`
     로 못박았는데 백엔드 테스트는 지금 202 status 만 본다. 그 문자열이 바뀌면
     **BE 전량 초록인 채 FE 만 깨진다.**
   - `cancel_order_task.delay` 는 `import src.tasks.trading as task_mod` 후
     `monkeypatch.setattr(task_mod.cancel_order_task, "delay", ...)` 로 잡아라
     (`test_router_cancel_cf4.py` 와 같은 방식). 실제 celery 를 태우지 마라.

2. `test_cancel_rejects_other_users_order`
   - 다른 User 소유의 `ExchangeAccount` 에 달린 `pending` 주문을 인증 사용자가 취소 시도 → **404**.
   - 취소가 실제로 일어나지 않았음을 DB 로 확인해라(`state` 가 여전히 `pending`).

3. `test_get_order_rejects_other_users_order`
   - 다른 User 소유 주문을 `GET /api/v1/orders/{id}` → **404**.
   - ★기존 `test_router_orders.py::test_get_order_by_id_404_if_not_owner` 는 이름과 달리
     **존재하지 않는 랜덤 uuid** 만 친다. 진짜 교차 사용자 경로는 지금 무커버리지다.

4. `test_live_session_events_reject_other_users_session`
   - 다른 User 소유 `LiveSignalSession` 의 `GET /api/v1/live-sessions/{id}/events` → **404**.

5. `test_resolve_kill_switch_rejects_other_users_event`
   - 다른 User 소유 strategy 에 달린 `KillSwitchEvent` 를
     `POST /api/v1/kill-switch/events/{id}/resolve` → **404**.
   - `resolved_at` 이 여전히 `None` 인지 DB 로 확인해라.

픽스처는 기존 관용구를 따른다 — 다른 사용자는 `User(auth_subject=..., email=...)` 를
`db_session` 에 add + flush 해서 만들고(`test_router_live_session_state_real_pnl.py:195` 참조),
인증 사용자는 `mock_authed_user` 를 쓴다.

## Acceptance Criteria

```bash
cd apps/api && uv run --env-file .env.local pytest tests/trading/test_router_layer_contract.py -q
cd apps/api && n=$(uv run --env-file .env.local pytest tests/trading/test_router_layer_contract.py --collect-only -q 2>/dev/null | grep -c '::test_'); echo "collected=$n"; test "$n" -ge 5
cd apps/api && uv run --env-file .env.local pytest tests/trading -q -k 'ack_detail_is_frozen or other_users'
cd apps/api && uv run --env-file .env.local pytest tests/trading -q
cd apps/api && uv run ruff check .
```

## 금지사항

- **`apps/api/src/` 아래 프로덕션 코드를 한 줄도 고치지 마라.** 이유: 이 step 은 「지금 동작」을
  고정하는 것이 목적이고, 코드를 함께 고치면 무엇이 기존 동작이었는지 증인이 사라진다.
  5종이 **지금 코드에서 전부 green** 이어야 한다 — red 가 나면 그것은 테스트를 잘못 쓴 것이다.
- 기존 테스트 파일을 수정하지 마라. 이유: 이 phase 의 diff 를 사람이 읽을 때 「추가된 계약」과
  「옮겨진 코드」가 섞이면 안 된다.
- 테스트 이름을 바꾸지 마라. 이유: 러너 AC 가 `-k 'ack_detail_is_frozen or other_users'` 로
  이름을 직접 센다.
- 커밋하지 마라(커밋은 러너 소관).
