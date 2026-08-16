# Backend Rules (FastAPI + SQLModel)

---

## 1. Tech Stack

| 항목            | 기술                                                       |
| --------------- | ---------------------------------------------------------- |
| Framework       | FastAPI (100% Async)                                       |
| ORM             | SQLModel + SQLAlchemy 2.0 (`asyncpg`)                      |
| Validation      | Pydantic V2 + `pydantic-settings`                          |
| Package Manager | `uv`                                                       |
| Database        | PostgreSQL + **TimescaleDB hypertable** (OHLCV 시계열)     |
| Cache / Broker  | Redis (Celery broker + 락 / 캐시)                          |
| Async Worker    | Celery (prefork pool, `_WORKER_LOOP` 통일 — §8)            |
| Auth            | Better Auth JWT 를 JWKS 로 검증 (`pyjwt[crypto]`, ADR-034) |
| Exchange SDK    | CCXT (Bybit / OKX / Binance 등 데모·라이브)                |
| 시크릿 암호화   | API 키는 AES-256 (Fernet) 암호화 저장                      |
| 배포            | Docker compose (개발) / TBD (프로덕션 H2+)                 |

> **참고**: 본 프로젝트는 백엔드에서 LLM SDK / Object Storage / Vector DB 를 사용하지 않는다. Pine Script 변환 등 AI 보조는 frontend → backend HTTP API 만 거쳐 진행한다.

---

## 2. 핵심 제약 사항 (Strict Rules)

### Pydantic V2 필수 패턴

- `BaseSettings`는 반드시 `pydantic_settings`에서 임포트 (pydantic 내부 금지)
- `.dict()` 대신 `.model_dump()`, `.model_dump_json()`
- `@root_validator` 대신 `@model_validator(mode="after")`

### 100% 비동기 SQLModel

- `session.exec()` 절대 금지
- `await session.execute(select(...))` 후 `.scalars().all()` 또는 `.scalar_one_or_none()`
- N+1 방지: `options(selectinload(...))`

### SecretStr

- API 키, DB 패스워드 등 → `SecretStr` 타입 (★인증 시크릿은 이제 백엔드에 없다 — ADR-034)
- 사용 시 `.get_secret_value()`

### Decimal-first 금융 숫자

- 가격 / 수량 / 수익률 / 레버리지 등은 `Decimal` 사용 (float 금지).
- 합산 시 `Decimal(str(a)) + Decimal(str(b))` — float 공간 합산 후 변환 금지 (Sprint 4 D8 교훈).

### JWT 검증 — JWKS 공개 키 ([ADR-034](../../docs/decisions/034-auth-self-host-better-auth.md))

★**백엔드는 인증 시크릿을 쥐지 않는다.** 검증기는 `src/realtime/auth.py` **한 곳**이고
HTTP·WebSocket 이 그것을 공유한다. 새 검증 경로를 만들지 마라.

```python
# realtime/auth.py — 요지
signing_key = PyJWKClient(settings.jwks_url, cache_keys=True).get_signing_key_from_jwt(token)
payload = jwt.decode(token, signing_key.key, algorithms=["EdDSA"],
                     issuer=issuer, audience=issuer,
                     options={"require": ["exp", "sub", "iss", "aud"]})
```

- 알고리즘은 **EdDSA 하나로 고정**한다 — 목록을 넓히면 알고리즘 혼동 표면이 열린다.
- `iss`/`aud` 는 `settings.better_auth_url` 이다. FE 의 `BETTER_AUTH_URL` 과 어긋나면 **전건 401**.
- 사용자 행은 첫 인증 요청에서 생긴다(JIT). 웹훅이 없다 — `users.auth_subject` = JWT `sub`.
- `python-jose` 는 **EdDSA 미지원**이라 쓸 수 없다(실측). `pyjwt[crypto]` 를 쓴다.

---

## 3. Architecture (도메인 모듈러 — Router / Service / Repository)

**핵심: AsyncSession은 Repository만 보유한다.**

```
[domain]/
├── router.py        # HTTP 전용 (10줄 이하)
├── service.py       # 비즈니스 로직 (AsyncSession 보유 금지)
├── repository.py    # DB 접근 전담 (AsyncSession 유일 보유자)
├── schemas.py       # Pydantic V2 입출력
├── models.py        # SQLModel 테이블
├── dependencies.py  # Depends() 조립 (repo → service)
└── exceptions.py    # 도메인 예외
```

### 레이어 규칙

- **Router** — HTTP 수신, 스키마 검증, service 호출만. DB 접근/비즈니스 로직 금지.
- **Service** — 비즈니스 로직 + 트랜잭션 경계. AsyncSession import 절대 금지. Repository만 생성자 주입.
- **Repository** — AsyncSession 유일 보유. DB 접근만. commit()은 service 요청으로만.
- **Dependencies** — Depends() 조립의 유일한 위치. service.py/repository.py에 Depends import 금지.

### ★ 이 표준을 따르지 않는 디렉터리 (예외 — 위반이 아니다)

`src/` 하위 전부가 도메인 모듈은 아니다. 아래는 **의도된 예외**이고, 여기에 없는 디렉터리를
7파일 표준에서 벗어나게 만들려면 먼저 이 표에 줄을 추가해라.

| 디렉터리            | 무엇인가                                                  | 왜 3-Layer 가 아닌가                                                                                                                                                                                        |
| ------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `market_data/`      | OHLCV provider(CCXT·Timescale·fixture) 공급               | **공개 REST 가 없는 내부 전용 subdomain**(`CONTEXT.md` Data Context). `main.py` 에 마운트되지 않고 `backtest`·`optimizer`·`stress_test`·`tasks`·`trading` 이 라이브러리로 쓴다. router/service/schemas 없음 |
| `realtime/`         | WS 라우터 + **JWT/JWKS 검증기**(`auth.py`) + 연결 manager | 검증기는 도메인이 아니라 횡단 관심사다. 원장은 `auth/` 가 갖는다                                                                                                                                            |
| `health/`           | `/healthz`·`/livez`                                       | 상태 프로브. 소유 엔티티가 없다                                                                                                                                                                             |
| `tasks/`            | Celery task entrypoint                                    | HTTP 표면이 아니다. prefork-safe 규칙은 §9                                                                                                                                                                  |
| `scripts/`          | 운영 entrypoint helper (`run_alembic_with_lock`)          | `python -m src.scripts.*` 로 실행. 테스트·dogfood 스크립트는 여기가 아니라 `apps/api/scripts/`(앱 루트)                                                                                                     |
| `common/` · `core/` | 기술 기반 · 설정                                          | 도메인이 아니다                                                                                                                                                                                             |

`trading/` 은 예외가 아니라 **확장**이다 — `service.py`/`repository.py` 가 파일이 아니라
`services/`·`repositories/` 디렉터리로 분해돼 있고, 그 밖에 `websocket/` 서브패키지를 갖는다.

### 필수 코드 패턴

```python
# router.py
@router.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(
    data: CreateItemRequest,
    service: ItemService = Depends(get_item_service),
) -> ItemResponse:
    return await service.create_item(data)

# service.py — AsyncSession import 금지
class ItemService:
    def __init__(self, repo: ItemRepository) -> None:
        self.repo = repo

    async def create_item(self, data: CreateItemRequest) -> ItemResponse:
        item = Item.model_validate(data)
        saved = await self.repo.save(item)
        await self.repo.commit()
        return ItemResponse.model_validate(saved)

# repository.py
class ItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, item: Item) -> Item:
        self.session.add(item)
        await self.session.flush()
        return item

    async def commit(self) -> None:
        await self.session.commit()

# dependencies.py
async def get_item_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ItemRepository:
    return ItemRepository(session)

async def get_item_service(
    repo: ItemRepository = Depends(get_item_repository),
) -> ItemService:
    return ItemService(repo)
```

### 트랜잭션 commit 보장 (LESSON-019 승격, 2026-04-28)

> Sprint 6 → Sprint 13 → Sprint 15-A 에서 동일 broken bug 가 3 회 재발했다. `get_async_session()` 은 `expire_on_commit=False` + autocommit OFF 라 service 가 명시적 `commit()` 호출 안 하면 request 종료 시 ROLLBACK. `db_session` fixture 기반 통합 테스트는 conftest 트랜잭션 안에서 read-your-writes 로 통과 = false-positive.

**의무 규약:**

- 모든 service mutation 메서드 (`save/update/delete` 호출 + commit 책임 보유) 는 `tests/<domain>/test_*_commits.py` 에 **AsyncMock spy 회귀 테스트 1건 필수**
- spy 표준: `repo.commit.assert_awaited_once()` (default commit) 또는 `repo.commit.assert_not_called()` (atomic 옵션)
- 표준 reference: `apps/api/tests/trading/test_webhook_secret_commits.py` 의 `test_issue_default_calls_repo_commit` / `test_order_service_execute_calls_outer_commit` / `test_register_calls_repo_commit`

**예시 패턴:**

```python
# tests/<domain>/test_*_commits.py
@pytest.mark.asyncio
async def test_<method>_calls_repo_commit():
    """LESSON-019 spy: <method>() 가 repo.commit() 호출 강제."""
    repo = AsyncMock()
    svc = MyService(repo=repo, ...)
    await svc.my_method(...)
    repo.save.assert_awaited_once()
    repo.commit.assert_awaited_once()  # ← broken bug 재발 방어
```

**PR review 체크리스트:**

- `git diff -- '*service.py'` 에 `repo.save|repo.update|repo.delete` 가 추가/수정되면 동일 PR 에 commit-spy 테스트 추가 여부 검증
- atomic 트랜잭션 (예: `WebhookSecretService.issue(commit=False)`) 은 `assert_not_called()` 로 명시 검증

### 크로스 레포지토리 트랜잭션

여러 Repository가 하나의 트랜잭션으로 묶여야 할 때, **동일 session**을 공유한다.
개별 Repository에서 commit하지 않고, **조율하는 Service에서 한 번만 commit**한다.

```python
# dependencies.py — 동일 session을 여러 repo에 주입
async def get_order_service(
    session: AsyncSession = Depends(get_async_session),
) -> OrderService:
    return OrderService(
        order_repo=OrderRepository(session),
        payment_repo=PaymentRepository(session),  # 동일 session
    )

# service.py — 마지막에 한 번만 commit
class OrderService:
    def __init__(self, order_repo: OrderRepository, payment_repo: PaymentRepository):
        self.order_repo = order_repo
        self.payment_repo = payment_repo

    async def create_order_with_payment(self, data: CreateOrderRequest):
        order = await self.order_repo.save(Order(...))
        payment = await self.payment_repo.save(Payment(...))
        await self.order_repo.commit()  # 한 번만 — 같은 session이므로 둘 다 커밋됨
        return order
```

**원칙:** 여러 repo를 묶는 service는 `dependencies.py`에서 동일 session으로 조립.

---

## 4. QuantBridge 도메인 고유 규칙

| 영역             | 규칙                                                                                                                                                                  |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pine Script 변환 | `exec()` / `eval()` 절대 금지 — 인터프리터 패턴 (`pine_v2`) 또는 sandbox 사용 (ADR-003).                                                                              |
| Pine 미지원 함수 | 1개라도 포함 시 전체 "Unsupported" 반환 — 부분 실행 금지 (잘못된 결과 방지).                                                                                          |
| 백테스트/최적화  | 반드시 Celery 비동기. API 핸들러 직접 실행 금지. 결과는 `result_jsonb` 컬럼.                                                                                          |
| 거래소 API Key   | AES-256 (`Fernet`) 암호화 후 DB 저장. 평문 컬럼 금지.                                                                                                                 |
| OHLCV 시계열     | TimescaleDB hypertable (`ts.ohlcv`) 에 저장. 일반 PostgreSQL 테이블 사용 금지.                                                                                        |
| 실시간 가격      | WebSocket + Zustand 캐시 (frontend). 백엔드는 `ws_stream` 별도 queue + prefork worker (Sprint 24 BL-012 prefork 복귀 — `docker-compose.yml` ws-stream 서비스가 정본). |

---

## 5. 스트리밍 응답

```python
from fastapi.responses import StreamingResponse

@router.post("/stream-progress")
async def stream(
    data: StreamRequest,
    service: ProgressService = Depends(get_progress_service),
):
    async def generate():
        async for chunk in service.stream_progress(data):
            yield f"data: {chunk}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## 6. 비동기 장기 작업 패턴

수초 이상 걸리는 작업(백테스트, 최적화, 스트레스 테스트)은 HTTP 응답을 블로킹하지 않는다.

### Celery shared_task (QuantBridge 표준)

```python
# apps/api/src/tasks/backtest.py
@shared_task(name="backtest.run")
def run_backtest_task(backtest_id: str) -> dict:
    from src.tasks._worker_loop import run_in_worker_loop
    return run_in_worker_loop(_async_run_backtest(backtest_id))
```

### 상태 폴링 (클라이언트)

```python
@router.get("/backtests/{backtest_id}/status")
async def get_status(
    backtest_id: str,
    service: BacktestService = Depends(get_backtest_service),
):
    return await service.get_status(backtest_id)
```

**원칙:**

- 장기 작업은 `202 Accepted` + task id 반환
- 클라이언트는 polling 또는 WebSocket으로 상태 확인
- DB에 `status` 컬럼으로 진행 상태 관리 (`pending | running | completed | failed | cancelled`)
- 실시간 진척률은 Redis pub/sub + WebSocket 으로 전송 (필요 시)

---

## 7. DB 마이그레이션 (Alembic)

```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "add backtest_kind column"

# 마이그레이션 적용
alembic upgrade head

# 롤백
alembic downgrade -1
```

### 규칙

- `models.py` 변경 시 **반드시** Alembic 마이그레이션 생성
- 마이그레이션 파일은 커밋에 포함 (자동 생성 후 검토)
- 프로덕션 배포 전 `alembic upgrade head` 자동 실행 (Docker entrypoint)
- 데이터 삭제/컬럼 삭제는 **2단계 배포**: (1) 코드에서 사용 중단 → (2) 다음 배포에서 삭제
- **enum value 추가/제거**: downgrade 안 enum swap 패턴 의무 (LESSON-066) — 처음부터 uppercase 채택, 이후 enum value 추가 시 alembic 안 양방향 안전 검증

---

## 8. 백엔드 폴더 구조

```
apps/api/src/
├── main.py         # create_app() — 라우터 조립 · 미들웨어 · 예외 핸들러 · lifespan
│                   #   ★조립 전용 디렉터리(api/)는 없다. /api/v1 프리픽스는 여기서 붙인다
├── [domain]/       # 3-Layer 도메인 (router/service/repository/schemas/models/dependencies/exceptions)
│   #   backtest · stress_test · optimizer · strategy · trading · waitlist · auth
│   #   (exchange 는 trading 으로 통합 — ADR-018)
├── auth/           # 사용자 원장 + 탈퇴. ★JWT 검증기는 realtime/auth.py
├── strategy/
│   ├── convert/    # 지표 변환 서브도메인 (자체 router — prefix 는 /strategies 공유)
│   └── pine_v2/    # Pine Script v2 인터프리터 (SSOT — interpreter / stdlib / coverage)
├── trading/
│   ├── services/   # ★단일 파일이 아니라 디렉터리로 분해됨
│   ├── repositories/
│   └── websocket/  # Bybit private/public 스트림 + 재조정
├── market_data/    # 내부 전용 subdomain — 공개 REST 없음 (§3 예외 표)
├── realtime/       # WS 라우터 + JWT/JWKS 검증기 + 연결 manager
├── health/         # /healthz · /livez
├── tasks/          # Celery task entrypoints (prefork-safe pattern — §9)
├── scripts/        # 운영 entrypoint helper (python -m src.scripts.*)
├── common/         # 기술 기반 — database · exceptions · redis_client · redlock
│                   #   metrics · rate_limit · logging_config · alert(Slack) · telegram_alert
└── core/
    └── config.py   # 전 도메인 Settings (pydantic-settings)
```

> `src` 는 **설치되는 패키지가 아니다** — `pyproject.toml` 에 `[build-system]` 이 없고
> `[tool.uv] package = false` 다. import 가능성은 CWD 가 `apps/api`(컨테이너 `/app`)라는 사실에
> 의존하고, 그 사실은 `pyproject.toml` `pythonpath=["."]` · `alembic.ini` `prepend_sys_path=.` ·
> `Dockerfile` `WORKDIR` 셋이 함께 세운다. **디렉터리 이름 `src` 를 바꾸면 이 셋과
> `docker-entrypoint.sh`·compose 의 `uvicorn src.main:app`·`celery -A src.tasks` 가 함께 깨진다.**

---

## 9. Celery prefork-safe 패턴 (Sprint 18 BL-080, 2026-05-02)

> Sprint 17 → Sprint 18 architectural 진화. `asyncio.run()` per task 패턴이 module-level async state 와 함께 쓰이면 **2nd+ task 부터 `RuntimeError("Future ... attached to a different loop")` / `InterfaceError("another operation is in progress")` 로 silent fail**. asyncpg 의 `BaseProtocol._on_waiter_completed` callback 이 1st task asyncio.run() loop 에 stale bound. Option C (영속 worker loop) 로 root fix.

### 9.1 의무 — `_WORKER_LOOP` 통일

**모든 Celery task entry point** 는 `asyncio.run(coro)` 대신 `run_in_worker_loop(coro)` 사용.

```python
# apps/api/src/tasks/<task_module>.py
@shared_task(name="domain.task_name")
def task_entry(payload: str) -> dict:
    from src.tasks._worker_loop import run_in_worker_loop

    return run_in_worker_loop(_async_impl(payload))
```

**예외 (master process 만)**:

- `celery_app.py:_on_worker_ready` — `@worker_ready.connect` 는 master process 에서 1회 실행. `_WORKER_LOOP` 비대상 → `asyncio.run()` 그대로.

**worker_process_init / worker_process_shutdown signal**:

```python
@worker_process_init.connect
def _init(...):
    init_worker_loop()         # 영속 loop 생성
    reset_redis_lock_pool()    # fork stale FD 폐기

@worker_process_shutdown.connect
def _shutdown(...):
    shutdown_worker_loop()     # pending cancel + asyncgens drain + close
```

### 9.2 의무 — Module-level async state 검증 (Sprint 19 BL-084 AST audit gate)

`asyncio.Semaphore` / `Lock` / `Event` / `Queue` 를 module-level 에 두는 것 자체는 OK 이지만 (영속 loop 통일로 stale 안 됨), **새 module-level async object 추가 시 PR 리뷰 의무**:

1. 해당 객체가 worker child fork 후 `_WORKER_LOOP` 안에서만 acquire/await 되는가?
2. `worker_process_init` 의 reset hook 필요한가? (Redis pool 처럼 fork 시 FD 공유 회피)
3. `_WORKER_LOOP` 미초기화 환경 (uvicorn FastAPI / pytest unit) 에서 안전한가?

**자동 audit gate**: `tests/tasks/test_no_module_level_loop_bound_state.py` (Sprint 19 BL-084) 가 `src/tasks/*.py` + `src/common/alert.py` + `src/common/redis_client.py` 의 module-level `Assign + AnnAssign` 노드에서 `asyncio.<Semaphore|Lock|Event|Queue|Condition|...>(...)` 호출 검출. import alias (`from asyncio import Semaphore as S`) 도 catch.

**Allowlist 갱신 절차**:

1. `tests/tasks/test_no_module_level_loop_bound_state.py` 의 `_ALLOWLIST` 상수에 `(module, name)` 튜플 추가 (현재 `("src.common.alert", "_SEND_SEMAPHORE")` 1개).
2. 본 §9.2 에 안전 사유 1-2줄 명시 (왜 영속 `_WORKER_LOOP` 통일 가정 하에 안전한지).
3. PR 리뷰에서 (1)+(2) 동시 변경 검증.
4. 미준수 시 audit `test_allowlisted_modules_have_documented_violations` 가 stale allowlist 검출.

**현재 allowlist (1개)**:

- `src.common.alert._SEND_SEMAPHORE` — Slack send burst 상한 `asyncio.Semaphore(8)`. Sprint 18 `_WORKER_LOOP` 통일로 모든 acquire 가 동일 loop. Sprint 19 BL-081 `track_pending_alert` helper 가 cross-task semantic 명시화.

### 9.3 의무 — Per-call engine + dispose (Sprint 17 패턴 유지)

Option C 가 loop 통일하더라도 **engine 수명은 task 단위로 유지**:

```python
async def _async_impl():
    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            ...
    finally:
        await engine.dispose()
```

이유: connection pool stale connection 누수 방어 (loop binding 과 별개). `apps/api/src/tasks/backtest.py:31-91` 가 표준 reference.

### 9.4 금지 — `run_in_worker_loop` 안에서 `run_in_worker_loop` (nested)

`run_in_worker_loop` 는 이미 실행 중인 loop 안에서 호출 시 `RuntimeError` raise (silent fallback 금지). pytest-asyncio / celery_eager 환경에서 호출자가 직접 coroutine 을 await 해야 함.

### 9.5 라이브 검증 의무 (sprint 신규 task type 추가 시)

새 Celery task 추가 시:

1. 동일 child 의 N 번째 task 도 success 인지 라이브 검증 (즉시 3회 + 5분 cycle 30분 자동)
2. ws_stream 같은 long-running 은 별도 queue (`task_routes`) 로 분리 — pool 은 prefork 고정 (Sprint 12 solo → Sprint 24 BL-012 prefork 복귀, `docker-compose.yml` 이 정본)
3. Sprint 19 BL-082 1h soak gate 통과 (RSS slope < 임계, fd 누수 없음)

### 9.6 Alert task pending observability (Sprint 19 BL-081)

영속 `_WORKER_LOOP` 채택으로 fire-and-forget alert task (e.g. `KillSwitchService` 의 Slack 발송 task) 가 **Celery task 경계를 넘어 살아남을 수 있음** — 이전 `asyncio.run()` 패턴은 task 종료 시 모든 pending task 자동 cancel. cross-task semantic 변화 → 운영 모니터링 의무.

**의무 규약**:

1. fire-and-forget alert task 는 `track_pending_alert(task)` helper 사용. `_PENDING_ALERTS.add(task)` 직접 호출 금지.
2. `track_pending_alert` 가 `qb_pending_alerts` Prometheus Gauge inc + idempotent `add_done_callback` (set membership 검사로 외부 drain + done callback 중복 dec underflow 방지).
3. 표준 reference: `apps/api/src/common/alert.py:track_pending_alert` + `apps/api/src/trading/kill_switch.py:225` (migration 패턴).
4. 운영 임계값: `qb_pending_alerts > 50` 시 Slack/Grafana alert 권장 (Sprint 20+ BL-089 wire-up).

**예시 패턴**:

```python
# apps/api/src/<domain>/<service>.py
import asyncio
from src.common.alert import send_critical_alert, track_pending_alert

class MyService:
    async def trigger_alert(self, ...):
        # 직접 add 금지 — track_pending_alert helper 사용
        task = asyncio.create_task(self._send_alert(...))
        track_pending_alert(task)
        # 호출자는 task 결과 await 안 함 (fire-and-forget). gauge 가 in-flight 모니터링.
```

**금지 패턴** (Sprint 19 BL-081 migration 후):

```python
# 직접 _PENDING_ALERTS 조작 — gauge 동기화 누락
_PENDING_ALERTS.add(task)
task.add_done_callback(_PENDING_ALERTS.discard)
```

---

## 10. 검사기가 무엇을 보는지 증명해라 (LESSON-092 승격, 2026-08-08)

> 한 회차에 **세 워커가 각자 「초록」을 얻고 셋 다 그것이 거짓임을 스스로 발견**했다. 셋 다
> 원인이 같다 — **검사기가 보는 표면이 실제 실패 표면보다 좁았다.** 초록은 「통과했다」가 아니라
> 「내가 본 것 중에는 없었다」만 말한다.

**의무 규약 3종:**

1. **행위 동결은 반환값이 아니라 부작용까지 얼려라.** no-op 변이는 반환값을 안 바꾼다 —
   실측으로 `_block_on_direction_divergence` 를 no-op 으로 만들어도 `return`·`upsert_state`·
   `insert_pending_events`·`dispatch`·`reconcile` 5개가 **완전 동일**했고, 잡은 것은 부작용
   원장(deactivate · publish · alert · prometheus 델타)뿐이었다.
   표준 reference: `apps/api/tests/tasks/test_live_signal_tick_oracle.py`.
2. **새 순수 함수를 만들면 「그 함수」가 아니라 「그것을 쓰는 경로」를 재는 케이스를 최소 1개 둬라.**
   단위 테스트가 순수 함수를 직접 호출하면 **호출부에서 그 함수를 떼어내는 변이가 red 0** 을 낸다.
   순수 함수 정확성 ≠ 배선.
3. **테스트 페이크는 프로덕션의 제약 축을 그대로 흉내내라.** `row_hash` 단독으로 dedup 하는
   페이크는 실제 UNIQUE 축 `(exchange_account_id, row_hash)` 를 재현하지 못해, **재현하려던 결함
   자체를 페이크 안에서 소멸**시켰다.

**판별 절차 (셋 다 이걸로 잡혔다):** 변이를 심는다 → **그 변이가 도달했는지 따로 확인한다** →
red 가 나는지 본다. **가운데 단계를 빼면 셋 다 놓친다** — 도달 못 한 변이의 red 0 은 무증거다.

★★**「도달」은 파일 내용이 아니라 실행 여부다** ([LESSON-087] 3/3 승격, 2026-08-15). 확인은 3층이다:

1. **앵커가 1건인가** — 0건이면 못 심었고, 2건 이상이면 어디가 바뀌었는지 모른다.
2. **치환이 파일에 들어갔는가** — sha256 스냅샷으로 심고 되돌려라(`git checkout` 금지).
3. ★**그 줄을 실행하는 입력이 테스트 집합에 있는가** — 3 이 빠지면 1·2 를 다 지켜도 무증거다.
   2026-08-15 에 계획서가 ★★로 표시한 가드(`interpreter.py` 의 `and limit is None`)를 지운
   변이가 **파일 도달 확인까지 통과하고 전건 초록**이었다. 그 분기는
   `fill_timing == "next_bar_open"` 일 때만 지나는데 엔진 기본값이 `bar_close` 라 어떤
   테스트도 그 줄을 실행하지 않았다.
   ⇒ **분기 조건에 기본값이 아닌 설정**(`fill_timing`·feature flag·env)**이 걸려 있으면
   그 설정을 명시로 켜는 케이스를 최소 1건 둬라.**

★**판정 명령에 파이프를 붙이지 마라** — `uv run pytest ... | tail -3` 은 **pytest 가 아니라
tail 의 rc** 를 읽는다. 2026-08-15 에 이 함정이 「7종 전부 초록(판별력 0)」이라는 **정반대
전건**을 냈다(출력에는 `6 failed` 가 찍혀 있었다). rc 를 먼저 잡고 텍스트는 나중에 잘라라.
게이트 rc 에서도 같은 것을 밟은 적이 있다(2026-08-15 harness-readopt).

★**주석에 적는 근거 문장도 실측 대상이다** — 「기본값이 X 라서 이 분기를 지난다」 같은
문장은 코드로 확인한 뒤에 써라. 같은 회차에서 그 문장 자체가 거짓이었다.

### 10.1 가드는 「있다」가 아니라 「그 경로가 지나는가」로 재라 (2026-08-10 [BL-451])

`_assert_disposable_database` 는 2026-07-25 실사고 직후 붙었고 2년 가까이 「있다」고 여겨졌다.
실측하니 그것은 `tests/test_migrations.py` **파일 안에만** 있었고, 사본 하나는
`tests/real_broker/conftest.py` 에 있었지만 그 파일은 **그 디렉터리를 수집할 때만** 로드됐다.
`DATABASE_URL`(개발 DB) 하나만 있는 셸에서 `pytest tests/trading/` 이 rc=0 으로 1088건을
수집했고, 그 경로의 세션 픽스처는 `SQLModel.metadata.drop_all` 을 돈다.

- **가드는 그 판정이 필요한 모든 진입점보다 위에 둬라.** pytest 라면 하위 conftest 가 아니라
  루트 `tests/conftest.py::pytest_configure` 다.
- **가드가 못 보는 표면을 주석으로 적어라.** `alembic/env.py` 의 방향 가드는 `config.cmd_opts`
  가 `None` 인 프로그램 호출 경로를 감지하지 못한다 — 그 사실을 코드 옆에 남겨야 다음 사람이
  그 초록을 「전부 막혔다」로 읽지 않는다.
- **막는 가드에는 「안 막는 것」의 음성 대조를 붙여라.** 방향을 안 보는 가드는 파괴를 막는 대신
  `mise run migrate`·entrypoint·CI 를 죽인다. 그 대조는 **역방향 변이**(가드를 더 넓게 만드는 변이)
  로만 판별력이 증명된다 — 정방향 변이만 돌리면 「너무 넓은 가드」가 초록으로 통과한다.
