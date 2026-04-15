# Strategy 도메인 API + Clerk 인증 실배선 — 설계 문서

- **작성일:** 2026-04-15
- **단계:** Stage 3 / Sprint 3
- **관련 ADR:** ADR-003 (Pine 런타임 안전성 + 파서 범위)
- **선행 스프린트:** Sprint 2 (vectorbt engine + SignalResult fill, merge `9fcf6a5`)
- **방법론:** brainstorming → writing-plans → TDD 구현 (Sprint 1/2와 동일)
- **시간박스:** 없음. 완료 기준 충족 시 종료.

---

## 1. 목적과 범위

### 1.1 왜 이 스프린트인가

Sprint 1 + 2로 Pine 파서와 vectorbt 백테스트 엔진이 순수 라이브러리 함수 수준에서 완성되었다 (`strategy.pine.parse_and_run`, `backtest.engine.run_backtest`). 현재는 **HTTP 표면이 전무한 상태** — 모든 도메인 스텁이 1-line 모듈이고, Clerk JWT 검증 dependency는 `HTTP 501`만 반환한다. 본 스프린트는 이 엔진들을 처음으로 REST API 뒤로 노출하고, Strategy 도메인 CRUD와 Clerk 인증을 실배선한다.

이와 함께 Sprint 2 리뷰에서 도출된 파서 follow-up 2건 (S3-01/S3-02)을 정리한다. S3-03/S3-04는 backtest/engine 관련이므로 Sprint 4(Celery + `POST /backtests`)로 이관한다.

### 1.2 완료 기준 (Go / No-Go)

모두 충족 시 스프린트 종료:

1. **8개 엔드포인트 E2E green:** `/auth/me`, `/auth/webhook`, `/strategies/parse`, `POST/GET/GET-id/PUT/DELETE /strategies`
2. **Ownership 격리:** 타 사용자 전략 접근 시 404 (정보 누출 방지) 테스트 통과
3. **파서 follow-ups 2건 커버 (S3-01/S3-02):** 골든 테스트로 재현, `warnings`/`status` 기대값 고정
4. **Alembic migration 검증:** upgrade/downgrade/upgrade round-trip 테스트 통과
5. **테스트 카운트 목표:** ~267 passing (Sprint 2 230 + Sprint 3 신규 ~37)
6. **CI green:** `ruff`/`mypy`/`pytest` 로컬과 CI 모두 pass. `backend` 잡의 `alembic upgrade head` 스텝 신규 포함
7. **의존성 & docs:** `svix` 추가된 `pyproject.toml`/`uv.lock` 커밋, `.env.example` 갱신, `docs/TODO.md`/`endpoints.md` 업데이트

### 1.3 범위 밖 (Out of Scope)

- `POST /strategies/import-url` (Sprint 4+) — TradingView ToS 검토 선행 필요
- Celery 태스크 래퍼 / `POST /backtests` (Sprint 4)
- S3-03 (backtest/engine 커버리지) / S3-04 (`_price_to_sl_ratio` clamp) — Sprint 4
- 템플릿 / fork_of / is_public / `ast_cache` / `default_params` 필드
- Cursor pagination, tags 필터 (JSONB 인덱스 설계 지연)
- Frontend UI 구현 (Sprint 5+)
- 성능 벤치마크, OpenAPI 스키마 정제, 프로덕션 배포 준비
- Clerk Dashboard Webhook 실등록 및 라이브 이벤트 수신 (Sprint 7 배포 시점)

---

## 2. 아키텍처

### 2.1 도메인 경계

Sprint 3은 `auth`와 `strategy` 두 도메인만 확장. 다른 5개 도메인(backtest/exchange/market_data/optimizer/stress_test/trading)은 스텁 상태 유지.

```
backend/src/
├── auth/                    [확장]
│   ├── router.py            [신규] /auth/me, /auth/webhook
│   ├── service.py           [신규] UserService (get-or-create, webhook handling)
│   ├── repository.py        [신규] UserRepository (AsyncSession 유일 보유)
│   ├── models.py            [신규] User SQLModel
│   ├── schemas.py           [확장] CurrentUser + UserResponse + WebhookEvent DTO
│   ├── dependencies.py      [재작성] 실검증 (501 제거)
│   └── exceptions.py        [신규] AuthError 계열
│
├── strategy/                [확장]
│   ├── router.py            [재작성] 6개 엔드포인트 등록
│   ├── service.py           [신규] StrategyService
│   ├── repository.py        [신규] StrategyRepository
│   ├── models.py            [신규] Strategy SQLModel
│   ├── schemas.py           [신규] Create/Update/Response DTOs
│   ├── dependencies.py      [신규] Depends() 조립
│   ├── exceptions.py        [신규] StrategyError 계열
│   └── pine/                [기존 불변 — Sprint 1/2 산출물]
│
├── common/
│   ├── database.py          [기존 불변]
│   ├── pagination.py        [확장] PageRequest/PageResponse Generic
│   └── exceptions.py        [기존 불변]
│
├── core/config.py           [기존 불변 — Clerk 설정 이미 존재]
└── main.py                  [수정] auth_router + strategy_router 등록
```

### 2.2 레이어 규칙 재확인 (`.ai/stacks/fastapi/backend.md`)

- **Router** 10줄 이하. Service 호출만. DB 접근 / 비즈니스 로직 금지.
- **Service** 비즈니스 로직 + 트랜잭션 경계. **`AsyncSession` import 절대 금지.**
- **Repository** `AsyncSession` 유일 보유. `await session.execute(select(...))` 패턴. `commit()`은 Service 요청으로만.
- **Dependencies** `Depends()` 조립의 유일한 위치. `service.py`/`repository.py`에 `Depends` import 금지.

### 2.3 Cross-Domain 트랜잭션 — Strategy → User 참조

`strategy` Service는 `user` 테이블을 직접 건드리지 않는다. `CurrentUser`(검증된 JWT + DB User.id)를 Router에서 주입받아 Service로 전달한다. Strategy.user_id FK는 **DB 외래키 제약**으로만 보장하며, Service는 `current_user.id`를 신뢰하고 조회·저장한다.

```python
# strategy/router.py
@router.post("", status_code=201, response_model=StrategyResponse)
async def create_strategy(
    data: CreateStrategyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyResponse:
    return await service.create(data, owner_id=current_user.id)
```

**Webhook `user.deleted` 처리만 예외 — cross-repo 트랜잭션 필요:**
`UserService.handle_clerk_event`에서 User soft delete와 Strategy cascade archive를 하나의 Session으로 처리한다. 이를 위해 `UserService`는 생성자에서 **`UserRepository`와 `StrategyRepository`를 모두** 주입받는다. `dependencies.py`(`auth/`)에서 두 repo에 **동일 session 공급** 후 `UserService(user_repo, strategy_repo)`로 조립하고, Service에서 한 번만 `commit()`. 이 cross-domain import(auth → strategy 방향 한 개)는 `.ai/stacks/fastapi/backend.md` §"크로스 레포지토리 트랜잭션" 패턴에 부합한다.

### 2.4 인증 플로우

**경로 1: 인증된 API 호출 (모든 보호 엔드포인트)**

```
Request: Authorization: Bearer <Clerk JWT>
  ↓
clerk_backend_api.Clerk.authenticate_request(request, authorized_parties=[frontend_url])
  - JWT 서명 검증 (JWKS 자동 fetch)
  - 만료 검증
  - authorized_parties(CSRF 방지) 검증
  ↓
UserService.get_or_create(clerk_user_id, email, username)
  - INSERT … ON CONFLICT (clerk_user_id) DO NOTHING + SELECT 재조회
  - 동일 사용자 병렬 요청 race 방지
  ↓
User.is_active == false → HTTP 403 (auth_user_inactive)
  ↓
CurrentUser(id, clerk_user_id, email, is_active) → Router Depends 주입
```

**경로 2: Clerk Webhook (Svix 서명 검증)**

```
POST /api/v1/auth/webhook
Headers: svix-id, svix-timestamp, svix-signature
Body: raw bytes (Clerk 이벤트 payload)
  ↓
svix.webhooks.Webhook(secret).verify(payload, headers)
  - 서명 검증 실패 → 400 webhook_signature_invalid
  ↓
event["type"] switch:
  user.created, user.updated → UserRepository.upsert_from_webhook
  user.deleted              → User soft delete + Strategy cascade archive
  기타                       → 200 OK 무시 (Clerk 재시도 방지)
  ↓
200 {"received": true}
```

`user.created`와 `get_or_create_user`의 race는 `clerk_user_id` UNIQUE 제약 + ON CONFLICT DO NOTHING로 idempotent.

### 2.5 Parse 플로우

**공통:** 두 엔드포인트 모두 `strategy.pine.parse_and_run(source, ohlcv)`를 호출.

**차이:**

| 엔드포인트 | DB 저장 | OHLCV | 반환 |
|------------|---------|-------|------|
| `POST /strategies/parse` | 없음 | 빈 DataFrame | `ParsePreviewResponse` |
| `POST /strategies` | 있음 (store-any) | 빈 DataFrame | `StrategyResponse` (`parse_status`/`parse_errors` 포함) |
| `PUT /strategies/:id` | 있음 (pine_source 변경 시만 재파싱) | 빈 DataFrame | `StrategyResponse` 갱신본 |

**빈 OHLCV 근거:** 파싱 자체는 OHLCV 없이도 수행된다. `ta.atr(14)` 등 OHLCV 의존 함수는 파싱 시점에 에러가 아닌 **런타임 시점에 실패** — 빈 OHLCV로 `parse_and_run`을 호출하면 `warnings`에 기록되지만 `status="ok"`는 유지된다. 실제 지표 계산은 `POST /backtests`(Sprint 4)에서 수행.

### 2.6 Config 및 환경변수

`core/config.py`에 Clerk 관련 설정 이미 존재 (`clerk_secret_key`, `clerk_publishable_key`, `clerk_webhook_secret`). 추가 환경변수 없음.

`.env.example`에 `CLERK_WEBHOOK_SECRET=whsec_your_secret_here` 플레이스홀더 확인 후 없으면 추가.

---

## 3. 데이터 모델 + Alembic

### 3.1 User 테이블

```python
# src/auth/models.py
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clerk_user_id: str = Field(index=True, unique=True, max_length=64)
    email: str | None = Field(default=None, max_length=320)
    username: str | None = Field(default=None, max_length=64)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column_kwargs={"server_default": text("NOW()")},
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column_kwargs={"server_default": text("NOW()"), "onupdate": text("NOW()")},
    )
```

**인덱스:** `clerk_user_id` UNIQUE (상시 lookup), `is_active` (archive 필터).
**Nullable 근거:** Clerk는 외부 provider signup(Google 등)에서 email이 없거나 username이 없는 경우를 허용. `clerk_user_id`가 유일한 SSOT.

### 3.2 Strategy 테이블

```python
# src/strategy/models.py
class ParseStatus(str, Enum):
    ok = "ok"
    unsupported = "unsupported"
    error = "error"

class PineVersion(str, Enum):
    v4 = "v4"
    v5 = "v5"

class Strategy(SQLModel, table=True):
    __tablename__ = "strategies"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        foreign_key="users.id",
        ondelete="CASCADE",   # 무결성 안전망, 실제 흐름은 soft delete
        index=True,
    )
    name: str = Field(max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    pine_source: str                                          # TEXT, no length limit
    pine_version: PineVersion
    parse_status: ParseStatus = Field(index=True)
    parse_errors: list[dict] | None = Field(
        default=None,
        sa_column=Column(JSONB),
    )
    timeframe: str | None = Field(default=None, max_length=16)
    symbol: str | None = Field(default=None, max_length=32)
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, server_default="[]"),
    )
    is_archived: bool = Field(default=False, index=True)
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column_kwargs={"server_default": text("NOW()")},
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_column_kwargs={"server_default": text("NOW()"), "onupdate": text("NOW()")},
    )
```

**인덱스:**
- 단일: `user_id`, `parse_status`, `is_archived`
- 복합: `(user_id, is_archived, updated_at DESC)` — 기본 목록 쿼리 경로

**Soft delete vs CASCADE 정책:** `user.deleted` webhook은 User를 `is_active=false`로 표시하고 해당 User의 모든 Strategy를 `is_archived=true`로 처리한다. DB FK CASCADE는 실제로는 작동하지 않으며 **데이터 불일치 방어용 안전망**으로만 존재한다. 코멘트로 model과 migration 파일 양쪽에 명시.

### 3.3 Alembic 첫 migration

**파일명:** `20260415_xxxx_create_users_and_strategies.py` (Alembic 자동 생성 타임스탬프)

단일 파일에 User와 Strategy를 함께 생성. 인덱스와 FK 포함. 생성 후 사람이 다음을 검토:
- JSONB 컬럼 타입
- `ondelete="CASCADE"` FK
- 복합 인덱스명
- `server_default=text("NOW()")` 반영 여부

**Alembic env.py:** 기존 스캐폴드 그대로 (`src.core.config.settings.database_url` 주입). `target_metadata = SQLModel.metadata` 연결 확인.

**검증 절차 (Task 범위):**
1. `uv run alembic revision --autogenerate -m "create users and strategies"`
2. 사람 검토 — JSONB, CASCADE, 인덱스명, 컬럼 순서
3. `uv run alembic upgrade head` (로컬 docker compose DB)
4. `uv run alembic downgrade base` → `upgrade head` 왕복 검증
5. CI에도 `alembic upgrade head` 스텝 추가

### 3.4 Tests 스키마 준비 — `create_all` + migration round-trip 분리

| 용도 | 방식 |
|------|------|
| 일반 테스트 시작 | `SQLModel.metadata.create_all` (빠름) |
| Migration 검증 | `tests/test_migrations.py` 1건에서 `upgrade/downgrade/upgrade` 왕복 |
| CI | `backend` 잡에 `alembic upgrade head` 스텝 추가, 이후 pytest가 `create_all`로 시작 |

이 분리는 "모델 기반 스키마 ↔ 프로덕션 migration" 이탈을 round-trip 테스트로 검증하면서, 일반 테스트 속도는 유지한다.

---

## 4. API 계약 (8 엔드포인트)

### 4.1 공통 규약

- **Base URL:** `/api/v1`
- **인증:** `Authorization: Bearer <Clerk JWT>` — `/auth/webhook` 제외 전부 필수
- **에러 응답 포맷:** `{"detail": {"code": "<machine>", "detail": "<human>"}}`
  예: `{"detail": {"code": "strategy_not_found", "detail": "Strategy not found"}}`
- **UUID 경로 파라미터:** Pydantic V2 `UUID` 타입으로 422 자동 검증
- **정렬:** 목록은 `updated_at DESC` 고정 (클라이언트 정렬 파라미터 없음)

### 4.2 Auth 엔드포인트

#### `GET /api/v1/auth/me`

현재 사용자 정보 반환.

- **Response 200:** `UserResponse`
  ```json
  {
    "id": "uuid",
    "clerk_user_id": "user_2abc...",
    "email": "user@example.com",
    "username": "alice",
    "is_active": true,
    "created_at": "2026-04-15T..."
  }
  ```
- **Errors:** 401 (JWT 무효/누락), 403 (User `is_active=false`)

#### `POST /api/v1/auth/webhook`

Clerk Webhook 수신. Svix 서명 검증 후 이벤트 처리.

- **Headers:** `svix-id`, `svix-timestamp`, `svix-signature`
- **Body:** Clerk 이벤트 raw bytes
- **Response 200:** `{"received": true}`
- **Errors:** 400 (`webhook_signature_invalid`)
- **이벤트 처리:**

| 이벤트 | 동작 |
|--------|------|
| `user.created` | `UserRepository.upsert_from_webhook(clerk_user_id, email, username)` |
| `user.updated` | 동일 upsert 경로 (email/username 덮어씀) |
| `user.deleted` | `User.is_active = false` + 해당 User의 모든 Strategy `is_archived = true` (동일 session) |
| 기타 | 200 OK silently ignore |

### 4.3 Strategy 엔드포인트

#### `POST /api/v1/strategies/parse` — 미리보기

파싱만 수행하고 결과를 즉시 반환. DB 저장 없음.

- **Request:**
  ```json
  { "pine_source": "//@version=5\nstrategy(\"x\")\n..." }
  ```
- **Response 200:**
  ```json
  {
    "status": "ok",
    "pine_version": "v5",
    "warnings": [],
    "errors": [],
    "entry_count": 42,
    "exit_count": 38
  }
  ```
  파싱 실패 시:
  ```json
  {
    "status": "unsupported",
    "pine_version": "v5",
    "warnings": ["duplicate strategy.exit at line 23"],
    "errors": [{"code": "PineUnsupportedError", "message": "request.security is not supported", "line": 15}]
  }
  ```
- **Errors:** 400 — `pine_source` 누락/빈 문자열

`entry_count`/`exit_count`는 `ParseOutcome.signals.entries.sum()` 등으로 계산. 빈 OHLCV에서도 산출 가능.

#### `POST /api/v1/strategies` — 생성 (store-any)

- **Request:**
  ```json
  {
    "name": "EMA Cross 20/50",
    "description": "optional",
    "pine_source": "...",
    "timeframe": "1h",
    "symbol": "BTCUSDT",
    "tags": ["ema", "trend"]
  }
  ```
- **Response 201:** `StrategyListItem` (`pine_source`/`description` 제외)
- **동작:** `parse_and_run` 호출 → `parse_status`/`parse_errors`/`pine_version` 기록 → INSERT. **파싱 실패해도 201 Created.**

#### `GET /api/v1/strategies` — 목록

- **Query:**
  - `page: int = 1` (1-based)
  - `limit: int = 20` (max 100)
  - `parse_status: ok|unsupported|error | None`
  - `is_archived: bool = false` (기본=활성만)
- **Response 200:**
  ```json
  {
    "items": [<StrategyListItem>, ...],
    "total": 42,
    "page": 1,
    "limit": 20,
    "total_pages": 3
  }
  ```
- **소유권:** `WHERE user_id = current_user.id` 강제.

#### `GET /api/v1/strategies/:id` — 상세

- **Response 200:** `StrategyResponse` (`pine_source` + `description` 포함)
- **Errors:** 404 (`strategy_not_found` — 존재하지 않거나 타 사용자 소유, **정보 누출 방지로 둘 다 404**)

#### `PUT /api/v1/strategies/:id` — 수정

- **Request:** `CreateStrategyRequest`의 부분 필드 (`Partial<CreateStrategyRequest>`).
- **동작:**
  - `pine_source` 포함 시 재파싱 → `parse_status`/`parse_errors`/`pine_version` 갱신
  - `updated_at` 자동 갱신 (DB `onupdate`)
- **Response 200:** `StrategyResponse`
- **Errors:** 404, 401, 400

#### `DELETE /api/v1/strategies/:id` — 삭제 (hard)

- **Response 204 No Content**
- **동작:** hard delete. Sprint 3에 Strategy를 FK로 참조하는 테이블 없음. Sprint 4에서 Backtest가 추가되면 그때 soft delete로 승격. Soft delete는 `PUT`의 `is_archived=true`로 별도 처리.

### 4.4 에러 코드 목록

| Code | HTTP | 발생 |
|------|------|------|
| `auth_required` | 401 | Authorization header 누락/malformed |
| `auth_invalid_token` | 401 | JWT 검증 실패 (만료/서명 불일치/authorized_parties 불일치) |
| `auth_user_inactive` | 403 | `is_active=false` 사용자 |
| `webhook_signature_invalid` | 400 | Svix 서명 검증 실패 |
| `strategy_not_found` | 404 | 존재하지 않거나 타 사용자 소유 |
| `validation_error` | 422 | Pydantic V2 기본 — 구체 필드 detail |

---

## 5. 인증 구현 상세 + Parser Follow-ups

### 5.1 `get_current_user` Dependency

```python
# src/auth/dependencies.py (요지)
from clerk_backend_api import Clerk, AuthenticateRequestOptions
from fastapi import Depends, HTTPException, Request, status

_clerk = Clerk(bearer_auth=settings.clerk_secret_key.get_secret_value())

async def get_current_user(
    request: Request,
    service: UserService = Depends(get_user_service),
) -> CurrentUser:
    req_state = _clerk.authenticate_request(
        request,
        AuthenticateRequestOptions(authorized_parties=[settings.frontend_url]),
    )
    if not req_state.is_signed_in:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "auth_invalid_token", "detail": req_state.reason.name},
        )

    payload = req_state.payload
    user = await service.get_or_create(
        clerk_user_id=payload["sub"],
        email=payload.get("email"),
        username=payload.get("username"),
    )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "auth_user_inactive", "detail": "User account deactivated"},
        )
    return CurrentUser.model_validate(user)
```

**smoke check (Task 0.5):** `_clerk.authenticate_request`가 FastAPI `Request`를 수락하는지 한 번 확인. 비호환 시 fallback은 `python-jose` + Clerk JWKS URL 수동 fetch + RS256 검증 (추가 1~2 Task, R1 참조).

### 5.2 `UserService.get_or_create`

```python
class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def get_or_create(
        self,
        clerk_user_id: str,
        email: str | None,
        username: str | None,
    ) -> User:
        user = await self.repo.find_by_clerk_id(clerk_user_id)
        if user is not None:
            if user.email != email or user.username != username:
                user = await self.repo.update_profile(user.id, email=email, username=username)
                await self.repo.commit()
            return user

        user = await self.repo.insert_if_absent(clerk_user_id, email, username)
        await self.repo.commit()
        return user
```

`insert_if_absent`는 `INSERT … ON CONFLICT (clerk_user_id) DO NOTHING` + `SELECT` 재조회 패턴으로 race 방지.

### 5.3 Webhook 핸들러

```python
# src/auth/router.py
from svix.webhooks import Webhook, WebhookVerificationError

_svix = Webhook(settings.clerk_webhook_secret.get_secret_value())

@router.post("/webhook", status_code=200)
async def clerk_webhook(
    request: Request,
    service: UserService = Depends(get_user_service),
) -> dict[str, bool]:
    payload = await request.body()  # raw bytes 필수
    headers = dict(request.headers)
    try:
        event = _svix.verify(payload, headers)
    except WebhookVerificationError:
        raise HTTPException(400, detail={"code": "webhook_signature_invalid"})
    await service.handle_clerk_event(event)
    return {"received": True}
```

```python
class UserService:
    async def handle_clerk_event(self, event: dict) -> None:
        event_type = event["type"]
        data = event["data"]
        clerk_user_id = data["id"]
        match event_type:
            case "user.created" | "user.updated":
                await self.repo.upsert_from_webhook(clerk_user_id, data)
                await self.repo.commit()
            case "user.deleted":
                await self._soft_delete_and_archive(clerk_user_id)
                await self.repo.commit()
            case _:
                return

    async def _soft_delete_and_archive(self, clerk_user_id: str) -> None:
        user = await self.repo.find_by_clerk_id(clerk_user_id)
        if user is None:
            return
        await self.repo.set_inactive(user.id)
        await self.strategy_repo.archive_all_by_owner(user.id)
```

`UserService`가 `StrategyRepository`도 주입받는다 — `dependencies.py`에서 두 repo에 **동일 session 공급**.

### 5.4 Parser Follow-ups

#### S3-01: `if cond: strategy.exit(...)` gate propagation

**현상 (Sprint 2 interpreter `src/strategy/pine/interpreter.py:356-384`):** `strategy.exit` 호출이 `if`/`if-else` branch 내부에 있을 때, interpreter는 호출 자체는 실행하지만 gate 조건을 무시하고 `BracketState.sl_price`/`tp_price`에 값을 기록. 결과적으로 브래킷 시그널이 항상 활성화된다.

**수정:**
- `Interpreter.exec_if_stmt`가 branch 진입 시 현재 gate mask(Series[bool])를 `self._gate_stack`에 push, 종료 시 pop
- `strategy.exit` call 처리에서 `self._current_gate_mask()`를 lookup해 `sl_price`/`tp_price`를 gate mask AND로 합성

**테스트 (`tests/strategy/pine/test_interpreter_gate.py`):**
- `if close > sma_50: strategy.exit(stop=sma_20)` — sma_50 이상 바에서만 SL 기록, 이하에서 NaN
- Else branch의 독립 SL도 동일 검증

**리스크 완화:** 이 변경은 interpreter statement 실행 구조 일부 재작성. Task 진입 시 interpreter.py 현 구조 재검토 후, 필요 변경 범위가 과도하면 S3-01을 Sprint 4로 이관하는 결정 게이트 포함 (R2 참조).

#### S3-02: 중복 `strategy.exit` warning

**현상:** 동일 전략 내 `strategy.exit(...)` 2회 이상 호출 시 마지막 값이 조용히 덮어씀.

**수정:**
- `BracketState`에 `seen_exit_lines: list[int]` 추가
- `strategy.exit` call 처리에서 매 호출마다 line 기록
- `ParseOutcome` 생성 시 `len(seen_exit_lines) > 1`이면 `warnings`에 `"duplicate strategy.exit at lines [..]; last value wins"` 추가

**테스트 (`tests/strategy/pine/test_interpreter_exit.py`):**
- 두 번의 `strategy.exit` 호출이 있는 합성 전략 → `warnings` 1건 포함, `status="ok"` 유지
- 한 번만 있는 기존 골든은 불변 (`warnings` 빈 목록)

---

## 6. 테스트 전략

### 6.1 테스트 계층 구조

```
backend/tests/
├── conftest.py                         [신규] engine, session, app, client, authed_user
├── auth/
│   ├── test_user_service.py           [신규] UserService 단위 (mock repo)
│   ├── test_user_repository.py        [신규] Repository 통합 (실 PG)
│   ├── test_clerk_auth.py             [신규] get_current_user dependency (mock Clerk)
│   ├── test_webhook_handler.py        [신규] Webhook E2E (Svix 서명)
│   └── test_auth_me.py                [신규] /auth/me E2E
├── strategy/
│   ├── pine/                           [기존 — Sprint 1/2]
│   │   ├── test_interpreter_gate.py   [신규] S3-01
│   │   └── test_interpreter_exit.py   [신규] S3-02
│   ├── test_strategy_service.py       [신규] Service 단위 (mock repo + real parser)
│   ├── test_strategy_repository.py    [신규] Repository 통합
│   ├── test_strategies_parse.py       [신규] POST /strategies/parse E2E
│   ├── test_strategies_crud.py        [신규] POST/GET/PUT/DELETE E2E
│   └── test_strategies_ownership.py   [신규] 타 사용자 격리 E2E
├── backtest/engine/                    [기존 — Sprint 2]
└── test_migrations.py                  [신규] Alembic upgrade/downgrade round-trip
```

### 6.2 `conftest.py` Fixtures (핵심 패턴)

- `_test_engine` (session scope) — `quantbridge_test` DB 연결, `metadata.drop_all` + `create_all`
- `db_session` (function scope) — connection + savepoint 격리. 테스트 종료 시 rollback으로 DB 상태 초기화
- `app` (function scope) — FastAPI 앱 + `get_async_session` dependency override
- `client` (function scope) — `httpx.AsyncClient(transport=ASGITransport)` wrapper
- `authed_user` (function scope) — 테스트용 User 레코드 생성
- `mock_clerk_auth` (function scope) — `get_current_user`를 monkeypatch로 bypass, `authed_user` 반환

### 6.3 단위 vs 통합 분리

| 계층 | 방식 |
|------|------|
| `UserService` / `StrategyService` | Repository mock + 실 parser(Sprint 1/2 산출물) 사용 — 서비스 로직 검증 |
| `UserRepository` / `StrategyRepository` | 실 PG 사용 — SQL/JSONB/FK/CASCADE 검증 |
| Router (E2E) | httpx.AsyncClient + savepoint fixture + `mock_clerk_auth` |
| Webhook E2E | svix `Webhook.sign()`로 유효 서명 생성해 실 엔드포인트 호출 |

### 6.4 Ownership 격리

`test_strategies_ownership.py`에서 Alice/Bob 두 User 생성 후 각 사용자의 Strategy를 상대가 접근했을 때 404 `strategy_not_found`가 반환되는지 검증. 정보 누출 방지를 위해 "존재 but 권한 없음"도 404로 통일.

### 6.5 Migration Round-trip

```python
# tests/test_migrations.py
def test_alembic_roundtrip():
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
```

환경변수 `DATABASE_URL`로 test DB를 가리키며, round-trip 후 `users`/`strategies` 테이블 존재 assertion.

### 6.6 CI 연계

`.github/workflows/ci.yml` `backend` 잡에 추가:

```yaml
- run: uv run alembic upgrade head
  env:
    DATABASE_URL: postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test
# 이후 기존 ruff/mypy/pytest 스텝
```

테스트 실행 자체는 `metadata.create_all` 사용 (속도). migration 검증은 위 스텝 + `test_migrations.py`로 이중화.

### 6.7 테스트 카운트 추정

| 영역 | 신규 테스트 |
|------|-------------|
| Auth (service + repo + dep + me + webhook) | ~12 |
| Strategy (service + repo + parse + CRUD + ownership) | ~20 |
| Parser follow-ups (S3-01 + S3-02) | ~4 |
| Migration round-trip | 1 |
| **Sprint 3 신규 합계** | **~37** |
| **Sprint 2 누적 (230) + Sprint 3 (~37)** | **~267** |

---

## 7. 리스크와 완화

| # | 리스크 | 확률/영향 | 완화 |
|---|--------|-----------|------|
| R1 | `clerk-backend-api` Python SDK `authenticate_request()`가 FastAPI `Request`와 직접 호환 안 될 수 있음 | 중/중 | Task 0.5 smoke check. 비호환 시 fallback은 `python-jose` + Clerk JWKS 수동 검증 (추가 1~2 Task) |
| R2 | S3-01 gate propagation이 Sprint 1 interpreter 아키텍처 대폭 변경을 요구할 수 있음 | 중/중 | Task 진입 시 interpreter.py 구조 재검토. 복잡도가 `if_stmt` 재작성 수준이면 S3-01을 Sprint 4로 이관 결정. 플랜 체크포인트로 명시 |
| R3 | `svix` SDK가 numpy/pandas 버전과 충돌 | 저/중 | 설치 후 `uv sync` 확인. 의존성 트리가 단순해 가능성 낮음 |
| R4 | pytest-asyncio + asyncpg + savepoint fixture 복잡도 | 저/중 | SQLAlchemy 공식 패턴 그대로 사용. hang/leak 발생 시 NullPool + 단순 transaction 경계로 fallback |
| R5 | `email` 중복 허용 정책 — Clerk는 동일 email 복수 identity 허용 가능 | 저/저 | `email`은 UNIQUE 아님, `clerk_user_id`가 SSOT |
| R6 | CASCADE FK + soft delete 혼재로 의도 외 동작 | 저/저 | 모델/migration 주석에 "CASCADE는 안전망, 실흐름은 soft delete" 명시 |

---

## 8. 다음 스프린트 및 장기 확장 연결

- **Sprint 4 (예상):** Celery task 래퍼 + `POST /backtests` (202 + task_id) + `market_data` 도메인 기초 + TimescaleDB OHLCV hypertable. Sprint 2 `run_backtest()`와 Sprint 3 Strategy 모델이 여기서 결합됨
- **Sprint 4 이관된 follow-ups:** S3-03 (`backtest/engine` 91→95% coverage fault injection), S3-04 (`_price_to_sl_ratio` 음수 clamp)
- **Sprint 5+:** Frontend Strategy 편집기 (Monaco + `/strategies/parse` 실시간 호출), 프로토타입 12종을 기반으로 순차 구현
- **Sprint 6+:** `POST /strategies/import-url` (TradingView ToS 선행 검토), cursor pagination, tags JSONB 인덱스
- **Sprint 7 (배포):** Clerk Dashboard Webhook 실등록, `CLERK_WEBHOOK_SECRET` 주입, 프로덕션 Dockerfile, 배포 파이프라인

---

## 9. 참조

- Sprint 1 spec: `docs/superpowers/specs/2026-04-15-pine-parser-mvp-design.md`
- Sprint 2 spec: `docs/superpowers/specs/2026-04-15-vectorbt-signal-fill-design.md`
- ADR-003: `docs/dev-log/003-pine-runtime-safety-and-parser-scope.md`
- API 명세: `docs/03_api/endpoints.md`
- 백엔드 규칙: `.ai/stacks/fastapi/backend.md` (3-Layer Router/Service/Repository)
- 프로젝트 규칙: `CLAUDE.md` §QuantBridge 고유 규칙 (Celery 비동기, Decimal, AES-256 등)
- Clerk Python SDK: `clerk-backend-api>=1.0.0` (이미 `pyproject.toml`)
- Svix Python SDK: `svix` (이번 스프린트 추가)
- 프로토타입: `docs/prototypes/01-strategy-editor.html`, `06-strategies-list.html`, `07-strategy-create.html`

---

## 10. Sprint 3 구현 후 노트 (스펙 이탈 기록)

_(구현 완료 후 실측과 스펙의 차이가 발견되면 여기 기록. Sprint 1/2의 post-impl notes 섹션과 동일 형식.)_
