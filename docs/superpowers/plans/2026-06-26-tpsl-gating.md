# Demo-Stability Readiness Gate (Live Path) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 라이브 Live Session 등록 경로에 "데모 안정화 N일" readiness 게이트를 추가한다 (demo 세션 생성은 무영향, FE 무수정).

**Architecture:** `LiveSignalSessionService.register()` 가 `account.mode == ExchangeMode.live` 일 때만 `user.created_at` 기준 경과일을 검사해, `_MIN_DEMO_STABLE_DAYS` 미만이면 `DemoAccountNotYetStable` (HTTP 422) 예외를 던진다. 라이브는 어차피 `AccountModeNotAllowed` stub 으로 막혀 있으므로 이 게이트는 belt-and-suspenders + Wave 3 cutover 준비다. demo 경로는 게이트를 전혀 거치지 않아 신규 데모 유저가 차단되지 않는다.

**Tech Stack:** FastAPI · SQLModel(AsyncSession) · Pydantic V2 · pytest-asyncio · unittest.mock.AsyncMock.

## Global Constraints

- demo-only / 실자금 0 — BybitLiveProvider stub 유지, 신규 mainnet 주문 0.
- 금융 숫자 Decimal (단 본 작업엔 금융 숫자 없음 — datetime delta 만).
- migration 0 · 신규 Celery task 0 · `core/config.py` 미접촉 (W2 와 disjoint).
- 임계값 = 모듈 상수 `_MIN_DEMO_STABLE_DAYS` (config.py 미접촉, ponytail: 상수→튜닝 필요 시 config 승격).
- FE 절대 미수정 — readiness 는 기존 error path(예외)로만 표면화.
- IDOR ownership / 기존 리스크가드(quota/mode) 우회 금지 — 신규 게이트는 기존 게이트 앞에 additive.
- 신규 파일 첫줄 한국어 역할주석. 사고/문서 한국어, 네이밍/커밋 영어.
- 커밋 trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- LESSON-019 commit-spy: service mutation 회귀 보존.

## 안정 기준 선택 (근거 1줄)

**`user.created_at` 채택** — demo-stability 는 사용자의 플랫폼 체류 기간(데모 운영 tenure)을 측정하는 안정·비조작 신호다. ExchangeAccount 는 삭제/재등록이 자유로워 `account.created_at` 은 시계를 리셋할 수 있는 약한 anchor 이므로 `user.created_at` 을 쓴다.

---

### Task 1: `DemoAccountNotYetStable` 예외 추가

**Files:**

- Modify: `backend/src/trading/exceptions.py`
- Test: `backend/tests/trading/test_demo_stability_gate.py` (Task 2 에서 사용)

**Interfaces:**

- Produces: `DemoAccountNotYetStable(days_elapsed: int, min_required: int)` — `AppException`, `status_code = 422`, `code = "demo_account_not_yet_stable"`, 속성 `.days_elapsed`, `.min_required`.

- [ ] **Step 1: 예외 클래스 추가** (`backend/src/trading/exceptions.py` 끝에)

```python
class DemoAccountNotYetStable(AppException):
    """Wave 0 W4 — 라이브 전환 전 데모 안정화 기간 미충족.

    user.created_at 기준 경과일이 _MIN_DEMO_STABLE_DAYS 미만일 때 라이브 경로에서 raise.
    기존 error toast 가 표면화 — FE 무수정. demo 세션 생성에는 영향 없음.
    """

    status_code = 422
    code = "demo_account_not_yet_stable"

    def __init__(self, *, days_elapsed: int, min_required: int) -> None:
        super().__init__(
            f"데모 안정화 기간 미충족: {days_elapsed}일 경과 < 필요 {min_required}일. "
            "라이브 전환은 데모 안정화 후 가능."
        )
        self.days_elapsed = days_elapsed
        self.min_required = min_required
```

- [ ] **Step 2: import 확인** — 컴파일 검증

Run: `cd backend && uv run python -c "from src.trading.exceptions import DemoAccountNotYetStable; print(DemoAccountNotYetStable(days_elapsed=1, min_required=7).status_code)"`
Expected: `422`

- [ ] **Step 3: Commit**

```bash
git add backend/src/trading/exceptions.py
git commit -m "feat(trading): add DemoAccountNotYetStable exception (422)"
```

---

### Task 2: `UserRepository.get_created_at` 추가

**Files:**

- Modify: `backend/src/auth/repository.py`
- Test: `backend/tests/auth/test_user_repo_created_at.py`

**Interfaces:**

- Produces: `UserRepository.get_created_at(user_id: UUID) -> datetime | None` — user 없으면 None.

- [ ] **Step 1: 실패 테스트 작성** (`backend/tests/auth/test_user_repo_created_at.py`)

```python
"""UserRepository.get_created_at — Wave 0 W4 readiness gate 조회 메서드."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.auth.models import User
from src.auth.repository import UserRepository


@pytest.mark.asyncio
async def test_get_created_at_returns_user_created_at(db_session) -> None:
    repo = UserRepository(db_session)
    user = User(clerk_user_id=f"clerk_{uuid4().hex}")
    db_session.add(user)
    await db_session.flush()

    got = await repo.get_created_at(user.id)

    assert got is not None
    assert got == user.created_at


@pytest.mark.asyncio
async def test_get_created_at_missing_user_returns_none(db_session) -> None:
    repo = UserRepository(db_session)
    assert await repo.get_created_at(uuid4()) is None
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/auth/test_user_repo_created_at.py -q`
Expected: FAIL (`AttributeError: 'UserRepository' object has no attribute 'get_created_at'`)

- [ ] **Step 3: 메서드 구현** (`backend/src/auth/repository.py`, `find_by_id` 아래)

```python
    async def get_created_at(self, user_id: UUID) -> datetime | None:
        """readiness gate 용 — user.created_at 만 조회 (없으면 None)."""
        result = await self.session.execute(
            select(User.created_at).where(User.id == user_id)  # type: ignore[arg-type]
        )
        return result.scalar_one_or_none()
```

상단 import 에 `from datetime import datetime` 추가.

- [ ] **Step 4: 통과 확인**

Run: `cd backend && uv run pytest tests/auth/test_user_repo_created_at.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/src/auth/repository.py backend/tests/auth/test_user_repo_created_at.py
git commit -m "feat(auth): UserRepository.get_created_at for readiness gate"
```

---

### Task 3: readiness 게이트 — `register()` 라이브 경로 분기

**Files:**

- Modify: `backend/src/trading/services/live_session_service.py`
- Modify: `backend/src/trading/dependencies.py:173-185`
- Modify: `backend/tests/trading/test_live_session_commits.py:192-216` (live 테스트가 게이트 통과 후 AccountModeNotAllowed 도달하도록 stable user_repo 주입)
- Test: `backend/tests/trading/test_demo_stability_gate.py`

**Interfaces:**

- Consumes: `DemoAccountNotYetStable` (Task 1), `UserRepository.get_created_at` (Task 2).
- Produces: `LiveSignalSessionService(..., user_repo: UserRepository | None = None)` 키워드 인자. 모듈 상수 `_MIN_DEMO_STABLE_DAYS: int = 7`.

- [ ] **Step 1: 실패 테스트 작성** (`backend/tests/trading/test_demo_stability_gate.py`)

```python
"""Wave 0 W4 — 데모 안정화 readiness 게이트 (라이브 경로 한정)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.exceptions import AccountModeNotAllowed, DemoAccountNotYetStable
from src.trading.models import ExchangeAccount, ExchangeMode, ExchangeName
from src.trading.schemas import RegisterLiveSessionRequest
from src.trading.services.live_session_service import (
    _MIN_DEMO_STABLE_DAYS,
    LiveSignalSessionService,
)

_VALID_SETTINGS = {
    "schema_version": 1,
    "leverage": 2,
    "margin_mode": "cross",
    "position_size_pct": 10.0,
}


def _strategy(user_id):
    return Strategy(
        id=uuid4(), user_id=user_id, name="t",
        pine_source="//@version=5\nstrategy('t')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
        settings=_VALID_SETTINGS,
    )


def _account(user_id, *, mode):
    return ExchangeAccount(
        id=uuid4(), user_id=user_id, exchange=ExchangeName.bybit, mode=mode,
        api_key_encrypted=b"x", api_secret_encrypted=b"y",
    )


def _req(strategy_id, account_id):
    return RegisterLiveSessionRequest(
        strategy_id=strategy_id, exchange_account_id=account_id,
        symbol="BTCUSDT", interval="5m",
    )


def _svc(*, strategy, account, created_at):
    repo = AsyncMock()
    repo.acquire_quota_lock = AsyncMock(return_value=None)
    repo.count_active_by_user = AsyncMock(return_value=0)
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)
    user_repo = AsyncMock()
    user_repo.get_created_at = AsyncMock(return_value=created_at)
    return LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo,
        user_repo=user_repo,
    ), repo, user_repo


@pytest.mark.asyncio
async def test_live_not_yet_stable_raises():
    """라이브 + 경과일 < N → DemoAccountNotYetStable (AccountModeNotAllowed 보다 먼저)."""
    user_id = uuid4()
    created = datetime.now(UTC) - timedelta(days=_MIN_DEMO_STABLE_DAYS - 1, hours=1)
    svc, repo, _ = _svc(strategy=_strategy(user_id),
                        account=_account(user_id, mode=ExchangeMode.live),
                        created_at=created)
    with pytest.raises(DemoAccountNotYetStable) as ei:
        await svc.register(user_id, _req(uuid4(), uuid4()))
    assert ei.value.min_required == _MIN_DEMO_STABLE_DAYS
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_live_boundary_exactly_n_days_passes_gate():
    """경계: 정확히 N일 경과 → 게이트 통과 → 라이브 stub(AccountModeNotAllowed) 도달."""
    user_id = uuid4()
    created = datetime.now(UTC) - timedelta(days=_MIN_DEMO_STABLE_DAYS, hours=1)
    svc, repo, _ = _svc(strategy=_strategy(user_id),
                        account=_account(user_id, mode=ExchangeMode.live),
                        created_at=created)
    with pytest.raises(AccountModeNotAllowed):
        await svc.register(user_id, _req(uuid4(), uuid4()))
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_demo_path_skips_gate_no_user_repo_call():
    """demo 경로 → readiness 미적용 → user_repo 미호출 → 정상 등록 commit."""
    user_id = uuid4()
    strategy = _strategy(user_id)
    account = _account(user_id, mode=ExchangeMode.demo)
    svc, repo, user_repo = _svc(strategy=strategy, account=account, created_at=None)
    repo.save = AsyncMock(return_value=object())
    await svc.register(user_id, _req(strategy.id, account.id))
    user_repo.get_created_at.assert_not_called()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_live_missing_created_at_fails_closed():
    """user.created_at None (조회 실패) → fail-closed → DemoAccountNotYetStable(days=0)."""
    user_id = uuid4()
    svc, repo, _ = _svc(strategy=_strategy(user_id),
                        account=_account(user_id, mode=ExchangeMode.live),
                        created_at=None)
    with pytest.raises(DemoAccountNotYetStable) as ei:
        await svc.register(user_id, _req(uuid4(), uuid4()))
    assert ei.value.days_elapsed == 0
    repo.commit.assert_not_called()
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && uv run pytest tests/trading/test_demo_stability_gate.py -q`
Expected: FAIL (`ImportError: cannot import name '_MIN_DEMO_STABLE_DAYS'` / TypeError unexpected kwarg `user_repo`)

- [ ] **Step 3: 서비스 구현** (`live_session_service.py`)

(a) import 에 추가:

```python
from datetime import UTC, datetime  # 기존
from src.auth.repository import UserRepository
from src.trading.exceptions import (
    ...,
    DemoAccountNotYetStable,
)
```

(b) 모듈 상수 (logger 아래):

```python
# Wave 0 W4 — 라이브 전환 전 요구 데모 안정화 기간(일). ponytail: 상수, 튜닝 필요 시 config 승격.
_MIN_DEMO_STABLE_DAYS = 7
```

(c) `__init__` 에 keyword 인자 추가:

```python
        strategy_repo: StrategyRepository,
        *,
        user_repo: UserRepository | None = None,
        max_active_per_user: int = 5,
    ) -> None:
        ...
        self._user_repo = user_repo
        self._max_active_per_user = max_active_per_user
```

(d) register() account fetch 직후, AccountModeNotAllowed 블록 **앞에** 삽입:

```python
        # Wave 0 W4 — 라이브 경로 한정 demo-stability readiness 게이트.
        # 라이브는 어차피 AccountModeNotAllowed(stub)로 막히지만, 게이트를 앞에 둬
        # cutover(Wave 3) 시 데모 안정화 강제가 그대로 동작하도록 prep. demo 무영향.
        if account.mode == ExchangeMode.live:
            await self._enforce_demo_stability(user_id)
```

(e) helper 메서드 (register 아래):

```python
    async def _enforce_demo_stability(self, user_id: UUID) -> None:
        """라이브 전환 readiness — user.created_at 경과일 >= _MIN_DEMO_STABLE_DAYS 강제.

        조회 실패(None)는 검증 불가 → fail-closed(days_elapsed=0)로 거부.
        """
        created_at = (
            await self._user_repo.get_created_at(user_id) if self._user_repo else None
        )
        if created_at is None:
            days_elapsed = 0
        else:
            days_elapsed = (datetime.now(UTC) - created_at).days
        if days_elapsed < _MIN_DEMO_STABLE_DAYS:
            raise DemoAccountNotYetStable(
                days_elapsed=days_elapsed, min_required=_MIN_DEMO_STABLE_DAYS
            )
```

- [ ] **Step 4: DI 배선** (`dependencies.py:173-185`)

```python
async def get_live_signal_session_service(
    session: AsyncSession = Depends(get_async_session),
) -> LiveSignalSessionService:
    ...
    return LiveSignalSessionService(
        repo=LiveSignalSessionRepository(session),
        account_repo=ExchangeAccountRepository(session),
        strategy_repo=StrategyRepository(session),
        user_repo=UserRepository(session),
    )
```

상단 import 에 `from src.auth.repository import UserRepository` 추가.

- [ ] **Step 5: 기존 live 테스트 적응** (`test_live_session_commits.py::test_register_account_mode_live_rejected`)

게이트가 AccountModeNotAllowed 보다 앞서므로, 이 테스트가 stub-block 을 검증하려면 stable user_repo 를 주입해 게이트를 통과시킨다. import 에 `from datetime import UTC, datetime, timedelta` 추가 후 해당 테스트의 svc 생성에:

```python
    user_repo = AsyncMock()
    user_repo.get_created_at = AsyncMock(
        return_value=datetime.now(UTC) - timedelta(days=3650)
    )
    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo,
        user_repo=user_repo,
    )
```

- [ ] **Step 6: 신규 + 회귀 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/trading/test_demo_stability_gate.py tests/trading/test_live_session_commits.py -q`
Expected: PASS (전부 green, 기존 9 + 신규 4)

- [ ] **Step 7: Commit**

```bash
git add backend/src/trading/services/live_session_service.py backend/src/trading/dependencies.py backend/tests/trading/test_demo_stability_gate.py backend/tests/trading/test_live_session_commits.py
git commit -m "feat(trading): demo-stability readiness gate on live register path"
```

---

### Task 4: 전체 self-verify (회귀 0)

- [ ] **Step 1: lint + type + 도메인 테스트**

Run: `cd backend && uv run ruff check . && uv run mypy src/ && uv run python -m pytest tests/trading tests/auth -q`
Expected: ruff clean · mypy clean · all pass (회귀 0)

---

## Self-Review

- **Spec coverage:** register readiness(Task3) ✅ / DemoAccountNotYetStable 422(Task1) ✅ / user_repo created_at(Task2) ✅ / 모듈 상수(Task3 b) ✅ / 신규 test PASS·FAIL·경계(Task3 step1) ✅ / 기존 게이트 회귀 + commit-spy(Task3 step5,6) ✅ / config.py 미접촉 ✅ / FE 미수정 ✅ / migration 0 ✅.
- **Placeholder scan:** 없음 — 모든 step 실제 코드 포함.
- **Type consistency:** `get_created_at(UUID)->datetime|None`, `DemoAccountNotYetStable(days_elapsed,min_required)`, `_MIN_DEMO_STABLE_DAYS:int` 전 태스크 일관.
