# 백엔드 3-Layer 상세 — Router / Service / Repository

> 규칙 요지는 `apps/api/AGENTS.md` §3 이 갖는다(자동 로드). 이 문서는 **코드 예제와 예외 표**다.
> 2026-08-23 분리 — 자동 로드되는 파일에서 147줄을 덜어냈다.

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

