# Step 1: [BL-671] close 엔드포인트의 409 계약을 OpenAPI 에 도달시킨다

## 읽어야 할 파일

- `phases/n9-common.md`
- `docs/backlog.md` 의 `### BL-671` 절 — **잔여 1건이 정확히 이것이다**(FE 축은 2026-08-10 에 닫혔다)
- `apps/api/src/trading/router.py` — `close_live_session_position` (심볼로 찾아라)
- `apps/api/src/trading/services/close_service.py` — 409 를 **실제로 내는 자리**.
  `resting_conditional_entries` 로 grep 하면 나온다. 여기가 body 형상의 정본이다
- `apps/api/src/trading/schemas.py` — `RestingEntryOrder` 등 기존 스키마

## 배경 (결함)

`close_position` 은 두 가지 409 를 낸다:

- `detail="no_open_position"` — 포지션도 미체결 진입도 없다
- `detail={"code": "resting_conditional_entries", "count": N, "detail": "...", ...}` —
  포지션은 없지만 미체결 진입이 남아 있다

**둘 다 OpenAPI 에 없다.** 실측: 이 경로의 `responses` 는 `202` 와 `422` 뿐이다.
⇒ 스키마를 읽는 쪽(FE 타입 생성·API 문서·클라이언트)은 **409 가 존재한다는 것조차 모른다.**

## 작업

1. `@router.post(...)` 의 `responses=` 에 `409` 를 선언한다. **description 과 스키마를 함께** 준다 —
   `409` 키만 넣고 형상을 비워 두면 「있다」만 알리고 「무엇이 오는가」는 여전히 감춘다.
2. 두 형상이 다르므로 하나로 뭉개지 마라. `detail` 이 **문자열**인 경우와 **객체**인 경우를 둘 다
   표현해라(`oneOf` / `anyOf` 또는 그에 준하는 방식).
3. 객체 쪽 형상은 `close_service.py` 가 **실제로 내는 키**를 정본으로 삼아라 — 문서를 보고 베끼지 마라.
4. 응답 스키마를 Pydantic 모델로 새로 만든다면 `apps/api/src/trading/schemas.py` 에 둔다.
   ★기존 `RestingEntryOrder` 를 **재사용**해라 — 그 타입을 거쳐 내는 것이 두 경로(409 raw dict ·
   200 response_model)의 필드가 영구히 갈라지지 않게 하는 유일한 장치라고 코드 주석이 명시한다.

## 벗어나면 안 되는 계약

- **런타임 동작을 바꾸지 마라.** 이 step 은 **선언**만 추가한다. `close_service.py` 가 내는 상태 코드·
  body 를 바꾸면 FE 가 이미 파싱 중인 계약이 깨진다(`RestingEntriesConflictSchema` 가 그것을 읽는다).
- **`HTTPException(detail=...)` 경로는 `JSONResponse` 가 직접 직렬화한다** — `Decimal` 이 그대로면
  터진다. 기존 코드가 `mode="json"` 으로 그것을 피하고 있으니 그 관용구를 유지해라.

## 테스트

`apps/api/tests/trading/` 에 **테스트 이름에 `close_409` 를 포함**해 2개 이상 만든다
(AC 가 `-k 'close_409'` 로 센다):

1. 생성된 OpenAPI 스키마에서 그 경로의 `post.responses` 에 `409` 가 있고, 그 안의 형상이
   `code`/`count` 를 표현한다
2. **런타임 응답과 선언이 일치한다** — 실제로 409 를 내는 경로를 태워, 나온 body 의 키가 선언한
   형상에 담긴다. *이 두 번째가 없으면 선언은 그냥 주석이다.*

## Acceptance Criteria

- `cd apps/api && uv run --env-file .env.local python -c "from src.main import create_app; s=create_app().openapi(); r=s['paths']['/api/v1/live-sessions/{session_id}/positions/close']['post']['responses']; import sys; sys.exit(0 if '409' in r else 1)"`
- `cd apps/api && uv run --env-file .env.local pytest tests/trading -q -k 'close_409 or openapi'`
- `-k 'close_409'` 로 수집되는 테스트 ≥2
- `cd apps/api && uv run --env-file .env.local pytest tests/trading -q`
- `cd apps/api && uv run ruff check src/trading/router.py`

## 자기 점검

1. 위 AC 를 직접 실행해 green 을 확인한다. `status` 를 `completed` 로 바꾸지 마라.
2. **step 0 이 세운 가드가 여전히 통과하는지 확인해라** —
   `cd apps/api && uv run --env-file .env.local pytest tests/trading/test_strenum_column_contract.py -q`.
3. 사람 개입이 필요하면 `status:"blocked"` 와 `blocked_reason` 을 쓰고 즉시 중단한다.

## 금지사항

- **`close_service.py` 의 409 body 를 바꾸지 마라. 이유:** FE 의 `RestingEntriesConflictSchema` 가
  이미 그 형상을 파싱한다. 이 step 은 **이미 있는 계약을 선언**하는 것이지 계약을 바꾸는 것이 아니다.
- **`409` 키만 넣고 스키마를 비우지 마라. 이유:** 그러면 이 항목이 닫히지 않는다 — 「무엇이 오는가」가
  여전히 감춰진다.
- **다른 엔드포인트의 `responses=` 를 손대지 마라. 이유:** 범위 밖이고 diff 를 키운다.
- 커밋하지 마라(커밋은 러너 소관).
