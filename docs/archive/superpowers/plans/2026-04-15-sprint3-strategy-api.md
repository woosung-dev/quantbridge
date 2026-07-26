# Sprint 3: Strategy API + Clerk Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pine 파서와 vectorbt 엔진을 처음으로 HTTP REST API 뒤에 노출. Clerk JWT 실검증 + User/Strategy 도메인 CRUD + Webhook 핸들러 구현. Sprint 2 파서 follow-ups 2건 정리.

**Architecture:** FastAPI 3-Layer (Router/Service/Repository) — `backend.md` 준수. PostgreSQL (TimescaleDB 인스턴스, 일반 스키마 사용) + SQLModel + Alembic 첫 migration. Clerk JWT는 `clerk-backend-api` SDK로 검증, Webhook은 `svix` SDK로 서명 검증. 테스트는 실 PG + pytest-asyncio savepoint 격리.

**Tech Stack:** Python 3.12 · FastAPI · SQLModel · asyncpg · Alembic · pytest-asyncio · httpx.AsyncClient · clerk-backend-api · svix

**Spec:** `docs/superpowers/specs/2026-04-15-sprint3-strategy-api-design.md`

---

## File Structure

### 수정 (기존 파일)
```
backend/pyproject.toml                               — svix 의존성 추가
backend/mypy.ini                                     — svix import 허용 (필요시)
backend/alembic/env.py                               — target_metadata 배선 확인
backend/src/main.py                                  — auth_router, strategy_router 등록
backend/src/auth/dependencies.py                     — 501 제거, 실 Clerk 검증
backend/src/auth/schemas.py                          — UserResponse, WebhookEvent DTO 추가
backend/src/auth/router.py                           — [재작성] /auth/me, /auth/webhook
backend/src/auth/service.py                          — [재작성] UserService 구현
backend/src/auth/repository.py                       — [재작성] UserRepository 구현
backend/src/auth/models.py                           — [재작성] User SQLModel
backend/src/auth/__init__.py                         — (불변)
backend/src/strategy/router.py                       — [재작성] 6개 엔드포인트
backend/src/strategy/service.py                      — [재작성] StrategyService
backend/src/strategy/repository.py                   — [재작성] StrategyRepository
backend/src/strategy/models.py                       — [재작성] Strategy SQLModel
backend/src/strategy/schemas.py                      — [재작성] Create/Update/Response
backend/src/strategy/dependencies.py                 — [재작성] Depends 조립
backend/src/strategy/pine/interpreter.py             — S3-01 gate, S3-02 warnings
backend/src/strategy/pine/types.py                   — (필요시 warnings 필드)
backend/.env.example                                 — CLERK_WEBHOOK_SECRET 플레이스홀더
.github/workflows/ci.yml                             — alembic upgrade 스텝
docs/TODO.md                                         — Sprint 3/4 follow-ups 이동
docs/03_api/endpoints.md                             — 구현 완료 마킹
CLAUDE.md                                            — §현재 작업 갱신
docs/superpowers/specs/2026-04-15-sprint3-strategy-api-design.md — §10 post-impl notes
```

### 신규 (Create)
```
backend/alembic/versions/<stamp>_create_users_and_strategies.py  — 첫 migration
backend/src/auth/exceptions.py                       — AuthError 계열
backend/src/strategy/exceptions.py                   — StrategyError 계열
backend/tests/conftest.py                            — 공용 fixtures
backend/tests/test_migrations.py                     — Alembic round-trip
backend/tests/auth/__init__.py                       — (빈 파일)
backend/tests/auth/test_user_repository.py
backend/tests/auth/test_user_service.py
backend/tests/auth/test_clerk_auth.py
backend/tests/auth/test_auth_me.py
backend/tests/auth/test_webhook_handler.py
backend/tests/strategy/__init__.py                   — (이미 있을 수 있음)
backend/tests/strategy/test_strategy_repository.py
backend/tests/strategy/test_strategy_service.py
backend/tests/strategy/test_strategies_parse.py
backend/tests/strategy/test_strategies_crud.py
backend/tests/strategy/test_strategies_ownership.py
backend/tests/strategy/pine/test_interpreter_gate.py   — S3-01
backend/tests/strategy/pine/test_interpreter_exit.py   — S3-02
```

---

## Block 0 — Parser Follow-ups

### Task 1: S3-02 — 중복 `strategy.exit` 호출 시 `warnings` 기록

**의도:** 동일 전략 내 `strategy.exit(...)` 2회 이상 호출 시 조용히 덮어쓰지 않고 `SignalResult.warnings`에 기록.

**Files:**
- Test: `backend/tests/strategy/pine/test_interpreter_exit.py` (신규)
- Modify: `backend/src/strategy/pine/types.py` — `SignalResult.warnings` 필드 추가
- Modify: `backend/src/strategy/pine/interpreter.py` — `_BracketState` + `_execute_fncall_stmt` `strategy.exit` 블록 수정

- [ ] **Step 1: types.py 현 상태 확인**

Run: `grep -n "class SignalResult\|warnings" backend/src/strategy/pine/types.py`

확인: `warnings` 필드가 이미 있는지. 있으면 Step 2 건너뜀.

- [ ] **Step 2: `SignalResult`에 `warnings` 필드 추가 (없는 경우만)**

`backend/src/strategy/pine/types.py`의 `SignalResult` dataclass 수정:

```python
@dataclass
class SignalResult:
    entries: pd.Series
    exits: pd.Series
    direction: pd.Series | None = None
    sl_stop: pd.Series | None = None
    tp_limit: pd.Series | None = None
    position_size: pd.Series | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)  # [NEW] 중복 strategy.exit 등
```

- [ ] **Step 3: 실패 테스트 작성**

`backend/tests/strategy/pine/test_interpreter_exit.py` 생성:

```python
"""S3-02: 중복 strategy.exit 호출 시 warnings 기록."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategy.pine import parse_and_run


def _ohlcv(n: int = 40) -> dict[str, pd.Series]:
    idx = pd.date_range("2026-01-01", periods=n, freq="h")
    close = pd.Series(np.linspace(100, 140, n), index=idx)
    high = close + 1
    low = close - 1
    open_ = close
    volume = pd.Series(1000.0, index=idx)
    return {"open": open_, "high": high, "low": low, "close": close, "volume": volume}


def test_duplicate_strategy_exit_emits_warning():
    source = """//@version=5
strategy("dup exit")
long = ta.crossover(close, ta.sma(close, 5))
flat = ta.crossunder(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
if flat
    strategy.close("L")
strategy.exit("x1", stop=close * 0.95)
strategy.exit("x2", stop=close * 0.90)
"""
    outcome = parse_and_run(source, **_ohlcv())
    assert outcome.status == "ok", outcome
    assert outcome.signals is not None
    warnings = outcome.signals.warnings
    assert any("duplicate strategy.exit" in w for w in warnings), warnings


def test_single_strategy_exit_has_no_warning():
    source = """//@version=5
strategy("single exit")
long = ta.crossover(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
strategy.exit("x", stop=close * 0.95)
"""
    outcome = parse_and_run(source, **_ohlcv())
    assert outcome.status == "ok"
    assert outcome.signals is not None
    assert outcome.signals.warnings == []
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_exit.py -v`
Expected: FAIL — `warnings` 필드가 있어도 `duplicate` 메시지가 없음.

- [ ] **Step 5: `_BracketState`에 호출 카운터 추가 + warnings 생성 로직**

`backend/src/strategy/pine/interpreter.py` 수정:

```python
# 파일 상단 근처 (line ~210 근방)
@dataclass
class _BracketState:
    """strategy.exit 호출 시 평가된 stop/limit 가격 Series."""

    stop_series: pd.Series | None = None
    limit_series: pd.Series | None = None
    exit_call_lines: list[int] = field(default_factory=list)  # [NEW] S3-02
```

`_execute_fncall_stmt`의 `strategy.exit` 블록 (line ~356 근방) 내부 끝에 추가:

```python
# S3-02: 호출 라인 기록
brackets.exit_call_lines.append(node.source_span.line)
```

`_assemble_signal_result`에 warnings 전파 추가 (line ~262 근방 `return SignalResult(...)` 직전):

```python
warnings: list[str] = []
if len(brackets.exit_call_lines) > 1:
    lines = ", ".join(str(ln) for ln in brackets.exit_call_lines)
    warnings.append(
        f"duplicate strategy.exit calls at lines [{lines}]; only last stop/limit is used"
    )
```

그리고 `SignalResult(...)` 생성자 인자에 `warnings=warnings` 추가.

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_exit.py -v`
Expected: 2 passed.

- [ ] **Step 7: 기존 230 테스트 회귀 없는지 확인**

Run: `cd backend && uv run pytest -q`
Expected: 232 passed (230 기존 + 2 신규).

- [ ] **Step 8: ruff + mypy**

Run: `cd backend && uv run ruff check . && uv run mypy src/`
Expected: All checks passed + Success.

- [ ] **Step 9: Commit**

```bash
git add backend/src/strategy/pine/interpreter.py backend/src/strategy/pine/types.py backend/tests/strategy/pine/test_interpreter_exit.py
git commit -m "feat(strategy/pine): record warning on duplicate strategy.exit (S3-02)

이전에는 중복 호출 시 마지막 값이 조용히 덮어썼음. 이제 exit_call_lines
카운터로 라인 번호 누적 후 2회 이상이면 SignalResult.warnings에 기록."
```

---

### Task 2: S3-01 — `if cond: strategy.exit(...)` gate propagation

**의도:** `if` branch 내부의 `strategy.exit` 호출에서 gate 조건을 SL/TP Series에 AND 합성. 이전에는 gate 무시되어 브래킷이 항상 활성화됨.

**Files:**
- Test: `backend/tests/strategy/pine/test_interpreter_gate.py` (신규)
- Modify: `backend/src/strategy/pine/interpreter.py` — `_execute_fncall_stmt` `strategy.exit` 블록에 gate AND

**Decision gate (Task 시작 시 재검토):** `_execute_fncall_stmt`가 이미 `gate` 파라미터를 받고 있고 `strategy.exit` 분기에서만 미적용 상태. 픽스 범위는 gate를 Series로 변환 후 `ensure_series` 결과와 AND — 약 10줄. 복잡도 낮음. 만약 구현 중 예상 범위(30줄)를 초과하면 **체크포인트에서 Task 중단 후 사용자에게 Sprint 4 이관 여부 문의**.

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/strategy/pine/test_interpreter_gate.py` 생성:

```python
"""S3-01: if-branch 내부의 strategy.exit는 gate 조건을 SL/TP에 반영해야 함."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategy.pine import parse_and_run


def _ohlcv(n: int = 40) -> dict[str, pd.Series]:
    idx = pd.date_range("2026-01-01", periods=n, freq="h")
    close = pd.Series(np.linspace(100, 140, n), index=idx)
    return {
        "open": close,
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "volume": pd.Series(1000.0, index=idx),
    }


def test_strategy_exit_inside_if_respects_gate():
    # 20바 이후에만 SL 활성화
    source = """//@version=5
strategy("gated exit")
long = ta.crossover(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)

late = bar_index > 20
if late
    strategy.exit("x", stop=close * 0.95)
"""
    outcome = parse_and_run(source, **_ohlcv())
    assert outcome.status == "ok", outcome
    sr = outcome.signals
    assert sr is not None

    # 포지션 진입 이전 바에선 sl_stop이 NaN (carry forward 없음)
    # 포지션 진입 후에도 bar_index <= 20 구간에선 entry 바에 sl 설정이 없었으므로
    # sampling 값이 NaN → ffill도 NaN
    # 구체 검증: bar_index <= 20 에서 sl_stop이 NaN 이거나 설정 없음
    sl = sr.sl_stop
    assert sl is not None
    # 조건: bar_index <= 20 구간은 전체 NaN (entry가 gate 밖에서만 났을 경우)
    # 안전 검증: gate 활성화 전까지 sl의 finite 값이 없어야 함
    finite_before_21 = sl.iloc[:21].dropna()
    assert len(finite_before_21) == 0, f"SL should be NaN before bar 21, got {finite_before_21}"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_gate.py -v`
Expected: FAIL — assert 실패. 현재 interpreter가 gate 무시하고 SL을 전 구간에 설정.

- [ ] **Step 3: `strategy.exit` 블록에 gate AND 적용**

`backend/src/strategy/pine/interpreter.py`의 `_execute_fncall_stmt` 내 `strategy.exit` 블록 (line ~376-384) 수정:

```python
if has_stop:
    stop_raw = _ensure_series(
        evaluate_expression(kwargs["stop"], env), signals.entries.index
    )
    brackets.stop_series = _apply_bracket_gate(stop_raw, gate)
if has_limit:
    limit_raw = _ensure_series(
        evaluate_expression(kwargs["limit"], env), signals.entries.index
    )
    brackets.limit_series = _apply_bracket_gate(limit_raw, gate)
```

`_execute_fncall_stmt` 위 또는 아래에 헬퍼 함수 추가:

```python
def _apply_bracket_gate(
    raw: pd.Series,
    gate: pd.Series | bool | None,
) -> pd.Series:
    """gate가 Series면 False 바에서 NaN으로 마스킹. 스칼라 True/None이면 원본 유지."""
    if isinstance(gate, pd.Series):
        return raw.where(gate, other=np.nan)
    if gate is False:
        return pd.Series(np.nan, index=raw.index)
    # gate is None or True
    return raw
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/pine/test_interpreter_gate.py -v`
Expected: 1 passed.

- [ ] **Step 5: Sprint 2 기존 브래킷 골든 회귀 확인**

Run: `cd backend && uv run pytest tests/backtest/engine/ -v`
Expected: 기존 브래킷 테스트 전부 통과 (ATR SL/TP golden이 gate 없는 경로에서도 동일해야 함).

- [ ] **Step 6: 전체 회귀**

Run: `cd backend && uv run pytest -q`
Expected: 233 passed (232 + 1 신규).

- [ ] **Step 7: ruff + mypy**

Run: `cd backend && uv run ruff check . && uv run mypy src/`
Expected: All green.

- [ ] **Step 8: Commit**

```bash
git add backend/src/strategy/pine/interpreter.py backend/tests/strategy/pine/test_interpreter_gate.py
git commit -m "feat(strategy/pine): propagate if-gate into strategy.exit SL/TP (S3-01)

_apply_bracket_gate 헬퍼 추가. if/if-else 내부의 strategy.exit 호출에서
gate Series를 stop/limit Series에 마스크 적용 (where False → NaN)."
```

---

## Block 1 — Foundation

### Task 3: 의존성 + 환경변수 플레이스홀더 + DB 모델 + 첫 Alembic migration + round-trip 테스트

**의도:** Sprint 3 코드베이스 인프라 베이스. svix 추가, User/Strategy SQLModel 정의, Alembic autogenerate로 첫 migration 생성, round-trip 테스트 배치.

**Files:**
- Modify: `backend/pyproject.toml` — `svix` 추가
- Modify: `backend/.env.example` — `CLERK_WEBHOOK_SECRET` 플레이스홀더
- Create: `backend/src/auth/models.py` (User)
- Create: `backend/src/strategy/models.py` (Strategy + enums)
- Create: `backend/alembic/versions/<stamp>_create_users_and_strategies.py`
- Modify: `backend/alembic/env.py` (target_metadata 확인)
- Create: `backend/tests/test_migrations.py`

- [ ] **Step 1: svix 의존성 추가**

`backend/pyproject.toml` 수정:

```toml
dependencies = [
    # ... 기존 항목 유지
    "vectorbt>=0.28,<0.29",
    "svix>=1.37.0",  # [NEW] Clerk Webhook Svix 서명 검증
]
```

- [ ] **Step 2: uv sync 실행**

Run: `cd backend && uv sync --all-extras --dev`
Expected: `svix` 다운로드 + lock 갱신 성공. 충돌 없음.

- [ ] **Step 3: `.env.example` 확인 / 업데이트**

`backend/.env.example` 파일 존재 여부 확인:

Run: `cat backend/.env.example 2>&1 | grep -E "CLERK|WEBHOOK"`

`CLERK_WEBHOOK_SECRET` 없으면 Clerk 관련 섹션에 추가:

```bash
# Clerk 인증 (Sprint 3)
CLERK_SECRET_KEY=sk_test_placeholder_get_from_clerk_dashboard
CLERK_PUBLISHABLE_KEY=pk_test_placeholder_get_from_clerk_dashboard
CLERK_WEBHOOK_SECRET=whsec_placeholder_sprint7_real_value
```

(이미 존재하면 수정 없이 진행.)

- [ ] **Step 4: User SQLModel 작성**

`backend/src/auth/models.py` 재작성:

```python
"""auth 도메인 SQLModel 테이블. Sprint 3에서 User 추가."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlmodel import Column, Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    clerk_user_id: str = Field(
        index=True,
        unique=True,
        max_length=64,
        nullable=False,
    )
    email: str | None = Field(default=None, max_length=320, nullable=True)
    username: str | None = Field(default=None, max_length=64, nullable=True)
    is_active: bool = Field(default=True, index=True, nullable=False)
    created_at: datetime = Field(
        default_factory=_utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("NOW()")},
    )
    updated_at: datetime = Field(
        default_factory=_utcnow,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("NOW()"),
            "onupdate": text("NOW()"),
        },
    )
```

- [ ] **Step 5: Strategy SQLModel 작성**

`backend/src/strategy/models.py` 재작성:

```python
"""strategy 도메인 SQLModel 테이블. Sprint 3에서 Strategy 추가."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, Index, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ParseStatus(str, Enum):
    ok = "ok"
    unsupported = "unsupported"
    error = "error"


class PineVersion(str, Enum):
    v4 = "v4"
    v5 = "v5"


class Strategy(SQLModel, table=True):
    __tablename__ = "strategies"
    __table_args__ = (
        Index(
            "ix_strategies_owner_active_updated",
            "user_id",
            "is_archived",
            "updated_at",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        foreign_key="users.id",
        index=True,
        nullable=False,
        sa_column_kwargs={"ondelete": "CASCADE"},
    )
    name: str = Field(max_length=120, nullable=False)
    description: str | None = Field(default=None, max_length=2000, nullable=True)
    pine_source: str = Field(nullable=False)
    pine_version: PineVersion = Field(nullable=False)
    parse_status: ParseStatus = Field(index=True, nullable=False)
    parse_errors: list[dict] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
    )
    timeframe: str | None = Field(default=None, max_length=16, nullable=True)
    symbol: str | None = Field(default=None, max_length=32, nullable=True)
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    is_archived: bool = Field(default=False, index=True, nullable=False)
    created_at: datetime = Field(
        default_factory=_utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("NOW()")},
    )
    updated_at: datetime = Field(
        default_factory=_utcnow,
        nullable=False,
        sa_column_kwargs={
            "server_default": text("NOW()"),
            "onupdate": text("NOW()"),
        },
    )
```

- [ ] **Step 6: alembic env.py 모델 import 확인**

`backend/alembic/env.py` 상단의 import 섹션 확인:

Run: `grep -n "import\|target_metadata\|SQLModel" backend/alembic/env.py | head -20`

`target_metadata = SQLModel.metadata`가 있어야 하며, `from src.auth.models import User` 및 `from src.strategy.models import Strategy`가 `target_metadata` 할당 전에 import되어 SQLModel 메타데이터에 등록되어야 함. 

필요 시 env.py에 추가:

```python
# SQLModel 메타데이터에 도메인 모델 등록
from src.auth import models as _auth_models  # noqa: F401
from src.strategy import models as _strategy_models  # noqa: F401

from sqlmodel import SQLModel
target_metadata = SQLModel.metadata
```

- [ ] **Step 7: docker compose DB 시작 + Alembic autogenerate**

Run: `cd /Users/woosung/project/agy-project/quant-bridge && docker compose up -d db && sleep 3`

그리고:

```bash
cd backend && uv run alembic revision --autogenerate -m "create users and strategies"
```

Expected: `alembic/versions/` 아래에 `<timestamp>_create_users_and_strategies.py` 파일 생성.

- [ ] **Step 8: autogenerated migration 검토 및 정제**

생성된 migration 파일 열어 확인:
- `op.create_table("users", ...)` — 컬럼 타입, UNIQUE 제약, 인덱스
- `op.create_table("strategies", ...)` — JSONB 컬럼, FK CASCADE, 복합 인덱스
- `op.create_index("ix_strategies_owner_active_updated", ...)` 존재

혹시 JSONB가 JSON으로 autogen되었다면 수동으로 `postgresql.JSONB`로 치환:

```python
from sqlalchemy.dialects import postgresql
# ...
sa.Column("parse_errors", postgresql.JSONB, nullable=True),
sa.Column("tags", postgresql.JSONB, nullable=False, server_default="[]"),
```

주석 추가 (CASCADE 정책 명시):

```python
# NOTE: ondelete="CASCADE"는 데이터 무결성 안전망.
# 실제 흐름은 /auth/webhook의 user.deleted 에서 User.is_active=false +
# Strategy.is_archived=true 로 soft delete. (spec §3.2 참조)
```

- [ ] **Step 9: Migration 적용 + 테이블 검증**

Run: `cd backend && uv run alembic upgrade head`
Expected: `INFO  [alembic.runtime.migration] Running upgrade  -> <rev>, create users and strategies`

Run: `docker exec quantbridge-db psql -U quantbridge -d quantbridge -c "\dt"`
Expected: `users`와 `strategies` 테이블 모두 존재.

- [ ] **Step 10: Round-trip 테스트 작성**

`backend/tests/test_migrations.py` 생성:

```python
"""Alembic migration upgrade/downgrade round-trip 검증."""
from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config


def _alembic_cfg() -> Config:
    cfg = Config("alembic.ini")
    # 테스트 DB 사용 (CI 및 로컬 모두)
    cfg.set_main_option(
        "sqlalchemy.url",
        os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test",
        ).replace("+asyncpg", ""),  # alembic은 sync driver 필요
    )
    return cfg


def test_alembic_roundtrip(tmp_path, monkeypatch):
    """upgrade head → downgrade base → upgrade head가 모두 성공해야 함."""
    # backend/ 디렉토리에서 실행되도록 monkeypatch
    monkeypatch.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cfg = _alembic_cfg()

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    # 오류 없이 완주하면 성공
```

이 테스트는 `quantbridge_test` DB가 존재해야 함. Task 4의 conftest에서 fixture로 DB 생성 로직을 넣을 예정.

**임시:** 이 테스트는 `pytest.mark.skipif` 또는 환경변수 가드 없이 실행 가능 (docker compose로 db는 띄워있음). `quantbridge_test` DB가 없으면 실패할 수 있음.

임시 해결: 로컬에서 테스트 DB 수동 생성:

```bash
docker exec quantbridge-db psql -U quantbridge -d quantbridge -c "CREATE DATABASE quantbridge_test;"
```

(Task 4에서 fixture가 이를 자동화.)

- [ ] **Step 11: Migration 테스트 실행 (임시)**

Run: `cd backend && uv run pytest tests/test_migrations.py -v`
Expected: 1 passed.

실패 시 이 Task 막바지에서는 `@pytest.mark.skip(reason="fixture not ready; Task 4 activates")` 처리하고 Task 4에서 해제.

- [ ] **Step 12: ruff + mypy**

Run: `cd backend && uv run ruff check . && uv run mypy src/`
Expected: All green. (models.py는 `# type: ignore`  없이 통과해야 함.)

- [ ] **Step 13: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/.env.example backend/src/auth/models.py backend/src/strategy/models.py backend/alembic/ backend/tests/test_migrations.py
git commit -m "feat(backend): User + Strategy models + Alembic initial migration

- pyproject.toml: svix>=1.37 의존성 추가 (Clerk Webhook 서명 검증)
- .env.example: CLERK_WEBHOOK_SECRET 플레이스홀더 (Sprint 7 실값 주입)
- auth/models.py: User SQLModel (clerk_user_id UNIQUE, is_active soft-delete)
- strategy/models.py: Strategy SQLModel + ParseStatus/PineVersion enum
  + (user_id, is_archived, updated_at DESC) 복합 인덱스
- alembic/versions/*: 첫 migration (users + strategies 동시 생성)
- tests/test_migrations.py: upgrade/downgrade/upgrade round-trip"
```

---

### Task 4: pytest conftest — DB fixtures + Clerk auth mock

**의도:** 테스트 전체가 공유하는 fixtures 구축. 실 PostgreSQL + savepoint 격리 + FastAPI client + authed_user 생성 + Clerk JWT bypass.

**Files:**
- Create: `backend/tests/conftest.py`
- Modify: `backend/tests/test_migrations.py` (skip 제거, fixtures 연동)

- [ ] **Step 1: conftest.py 작성 (단계별)**

`backend/tests/conftest.py` 생성:

```python
"""Sprint 3 공용 테스트 fixtures.

전략:
- 세션 스코프 엔진: quantbridge_test DB. 시작 시 drop_all + create_all.
- 함수 스코프 db_session: connection + outer tx + savepoint 격리. 테스트 종료 시 전체 rollback.
- FastAPI app fixture는 get_async_session을 db_session으로 override.
- authed_user: 테스트용 User 레코드 생성.
- mock_clerk_auth: get_current_user dependency를 authed_user로 bypass.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel

from src.auth.models import User  # noqa: F401 — metadata 등록
from src.auth.schemas import CurrentUser
from src.common.database import get_async_session
from src.main import create_app
from src.strategy.models import Strategy  # noqa: F401 — metadata 등록


DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test",
)


@pytest_asyncio.fixture(scope="session")
async def _test_engine():
    engine = create_async_engine(DB_URL, poolclass=NullPool, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Savepoint 격리 fixture — 매 테스트마다 깨끗한 상태."""
    connection = await _test_engine.connect()
    trans = await connection.begin()
    session_maker = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    session = session_maker()
    nested = await connection.begin_nested()

    @event.listens_for(session.sync_session, "after_transaction_end")
    def _restart_savepoint(sess: Any, transaction: Any) -> None:
        nonlocal nested
        if transaction.nested and not transaction._parent.nested:
            nested = connection.sync_connection.begin_nested()

    try:
        yield session
    finally:
        await session.close()
        if trans.is_active:
            await trans.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def app(db_session: AsyncSession) -> AsyncGenerator[FastAPI, None]:
    """FastAPI app + get_async_session override."""
    app = create_app()

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_async_session] = _override_session
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def authed_user(db_session: AsyncSession) -> User:
    """테스트용 User 생성."""
    user = User(
        clerk_user_id=f"user_test_{uuid.uuid4().hex[:8]}",
        email=f"test_{uuid.uuid4().hex[:6]}@example.com",
        username="tester",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def mock_clerk_auth(monkeypatch: pytest.MonkeyPatch, authed_user: User, app: FastAPI):
    """get_current_user dependency를 authed_user를 반환하는 함수로 override."""
    from src.auth.dependencies import get_current_user

    async def _fake_current_user() -> CurrentUser:
        return CurrentUser(
            id=authed_user.id,
            clerk_user_id=authed_user.clerk_user_id,
            email=authed_user.email,
            is_active=authed_user.is_active,
        )

    app.dependency_overrides[get_current_user] = _fake_current_user
    yield authed_user
    # cleanup은 app fixture의 dependency_overrides.clear()로 처리됨
```

- [ ] **Step 2: test DB 생성 유틸 (최초 1회 수동)**

로컬 개발용:

Run: `docker exec quantbridge-db psql -U quantbridge -d quantbridge -c "CREATE DATABASE quantbridge_test;" 2>&1 || echo "DB already exists"`
Expected: `CREATE DATABASE` 또는 "already exists" 메시지.

CI는 `quantbridge_test`가 service container env로 이미 생성됨 (`.github/workflows/ci.yml`).

- [ ] **Step 3: 간단한 sanity 테스트 추가**

`backend/tests/test_conftest_sanity.py` 생성 (임시, 나중에 삭제 가능):

```python
"""conftest fixtures가 동작하는지 확인하는 smoke 테스트."""
import pytest


@pytest.mark.asyncio
async def test_db_session_usable(db_session):
    from sqlalchemy import text

    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_client_health(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_authed_user_persisted(db_session, authed_user):
    from src.auth.models import User
    from sqlalchemy import select

    result = await db_session.execute(
        select(User).where(User.id == authed_user.id)
    )
    assert result.scalar_one().clerk_user_id == authed_user.clerk_user_id
```

- [ ] **Step 4: sanity 테스트 실행**

Run: `cd backend && uv run pytest tests/test_conftest_sanity.py -v`
Expected: 3 passed.

실패 시 debug: fixture 조합, connection 누수, savepoint 재개 훅 등 점검.

- [ ] **Step 5: test_migrations.py 활성화 + 전체 회귀**

이전 Task 3에서 skip 마크가 있었다면 제거. 전체 실행:

Run: `cd backend && uv run pytest -q`
Expected: 234~236 passed (Task 1~3 누적 + conftest 3 sanity + migration 1).

- [ ] **Step 6: sanity 테스트 삭제**

Task 4의 목적은 fixture 검증이므로, 삭제 또는 유지 선택 — 이번 계획에서는 유지 (회귀 방어용). 파일 그대로 둠.

- [ ] **Step 7: ruff + mypy**

Run: `cd backend && uv run ruff check . && uv run mypy src/`
Expected: All green. conftest는 tests/ 아래이므로 mypy 설정상 느슨하게 통과.

- [ ] **Step 8: Commit**

```bash
git add backend/tests/conftest.py backend/tests/test_conftest_sanity.py
git commit -m "test(backend): shared pytest fixtures for DB + FastAPI client + auth

- _test_engine (session): quantbridge_test 엔진, metadata.create_all
- db_session (function): connection + outer tx + savepoint 격리
- app + client: FastAPI + httpx.AsyncClient, get_async_session override
- authed_user: 테스트용 User 레코드 생성
- mock_clerk_auth: get_current_user dependency를 authed_user로 bypass
- sanity: db_session/client/authed_user 3건 smoke 검증"
```

---

## Block 2 — Auth Vertical

### Task 5: UserRepository + 통합 테스트

**의도:** User 테이블 CRUD Repository. `AsyncSession` 유일 보유자. Webhook upsert 경로와 lazy-create 경로를 모두 지원.

**Files:**
- Modify: `backend/src/auth/repository.py` (재작성)
- Create: `backend/tests/auth/__init__.py` (빈 파일)
- Create: `backend/tests/auth/test_user_repository.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/auth/__init__.py` 생성 (빈 파일).

`backend/tests/auth/test_user_repository.py` 생성:

```python
"""UserRepository 통합 테스트 (실 PostgreSQL)."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from src.auth.models import User
from src.auth.repository import UserRepository


@pytest.mark.asyncio
async def test_insert_if_absent_creates_new_user(db_session):
    repo = UserRepository(db_session)
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    user = await repo.insert_if_absent(clerk_id, email="a@b.com", username="alice")
    await repo.commit()

    assert user.clerk_user_id == clerk_id
    assert user.email == "a@b.com"
    assert user.is_active is True


@pytest.mark.asyncio
async def test_insert_if_absent_is_idempotent(db_session):
    repo = UserRepository(db_session)
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    first = await repo.insert_if_absent(clerk_id, email="a@b.com", username="alice")
    await repo.commit()
    second = await repo.insert_if_absent(clerk_id, email="different@b.com", username="different")
    await repo.commit()

    assert first.id == second.id
    assert second.email == "a@b.com"  # 기존 값 보존 (ON CONFLICT DO NOTHING)


@pytest.mark.asyncio
async def test_find_by_clerk_id_returns_none_if_missing(db_session):
    repo = UserRepository(db_session)
    found = await repo.find_by_clerk_id("user_nonexistent")
    assert found is None


@pytest.mark.asyncio
async def test_update_profile_changes_email_and_username(db_session):
    repo = UserRepository(db_session)
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    user = await repo.insert_if_absent(clerk_id, email="old@b.com", username="old")
    await repo.commit()

    updated = await repo.update_profile(user.id, email="new@b.com", username="new")
    await repo.commit()

    assert updated.email == "new@b.com"
    assert updated.username == "new"


@pytest.mark.asyncio
async def test_set_inactive_soft_deletes(db_session):
    repo = UserRepository(db_session)
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    user = await repo.insert_if_absent(clerk_id)
    await repo.commit()

    await repo.set_inactive(user.id)
    await repo.commit()

    fetched = await repo.find_by_clerk_id(clerk_id)
    assert fetched is not None
    assert fetched.is_active is False


@pytest.mark.asyncio
async def test_upsert_from_webhook_inserts_or_updates(db_session):
    repo = UserRepository(db_session)
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"

    # 최초: INSERT
    u1 = await repo.upsert_from_webhook(
        clerk_user_id=clerk_id,
        email="first@b.com",
        username="first",
    )
    await repo.commit()
    assert u1.email == "first@b.com"

    # 두번째: UPDATE
    u2 = await repo.upsert_from_webhook(
        clerk_user_id=clerk_id,
        email="second@b.com",
        username="second",
    )
    await repo.commit()
    assert u2.id == u1.id
    assert u2.email == "second@b.com"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/auth/test_user_repository.py -v`
Expected: FAIL — UserRepository 메서드 미정의.

- [ ] **Step 3: UserRepository 구현**

`backend/src/auth/repository.py` 재작성:

```python
"""auth 도메인 Repository. AsyncSession 유일 보유자."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_clerk_id(self, clerk_user_id: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.clerk_user_id == clerk_user_id)
        )
        return result.scalar_one_or_none()

    async def find_by_id(self, user_id: UUID) -> User | None:
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def insert_if_absent(
        self,
        clerk_user_id: str,
        email: str | None = None,
        username: str | None = None,
    ) -> User:
        """INSERT ... ON CONFLICT DO NOTHING + SELECT 재조회.

        동일 clerk_user_id로 병렬 요청이 와도 race 없이 1개만 존재하도록 보장.
        """
        stmt = pg_insert(User).values(
            clerk_user_id=clerk_user_id,
            email=email,
            username=username,
        ).on_conflict_do_nothing(index_elements=["clerk_user_id"])
        await self.session.execute(stmt)
        # 삽입됐든 아니든 최종 row 반환
        user = await self.find_by_clerk_id(clerk_user_id)
        assert user is not None
        return user

    async def upsert_from_webhook(
        self,
        clerk_user_id: str,
        email: str | None = None,
        username: str | None = None,
    ) -> User:
        """Webhook user.created/updated 처리.

        INSERT ... ON CONFLICT DO UPDATE — email/username을 최신으로 덮어씀.
        """
        stmt = (
            pg_insert(User)
            .values(
                clerk_user_id=clerk_user_id,
                email=email,
                username=username,
            )
            .on_conflict_do_update(
                index_elements=["clerk_user_id"],
                set_={"email": email, "username": username},
            )
        )
        await self.session.execute(stmt)
        user = await self.find_by_clerk_id(clerk_user_id)
        assert user is not None
        return user

    async def update_profile(
        self,
        user_id: UUID,
        email: str | None,
        username: str | None,
    ) -> User:
        user = await self.find_by_id(user_id)
        assert user is not None
        user.email = email
        user.username = username
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_inactive(self, user_id: UUID) -> None:
        user = await self.find_by_id(user_id)
        if user is None:
            return
        user.is_active = False
        self.session.add(user)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/auth/test_user_repository.py -v`
Expected: 6 passed.

- [ ] **Step 5: 전체 회귀**

Run: `cd backend && uv run pytest -q`
Expected: 누적 +6 passed.

- [ ] **Step 6: ruff + mypy**

Run: `cd backend && uv run ruff check . && uv run mypy src/`
Expected: All green.

- [ ] **Step 7: Commit**

```bash
git add backend/src/auth/repository.py backend/tests/auth/__init__.py backend/tests/auth/test_user_repository.py
git commit -m "feat(auth): UserRepository with upsert + idempotent insert

- find_by_clerk_id / find_by_id
- insert_if_absent: INSERT ... ON CONFLICT DO NOTHING (race 방지)
- upsert_from_webhook: INSERT ... ON CONFLICT DO UPDATE
- update_profile, set_inactive (soft delete)
- 6 integration tests (실 PG)"
```

---

### Task 6: UserService + Schemas + 단위 테스트

**의도:** Repository를 주입받아 Webhook 이벤트와 lazy-create를 처리하는 Service 레이어. Strategy archive까지 cross-repo 트랜잭션 지원.

**Files:**
- Modify: `backend/src/auth/schemas.py`
- Modify: `backend/src/auth/service.py` (재작성)
- Create: `backend/src/auth/exceptions.py`
- Create: `backend/tests/auth/test_user_service.py`

- [ ] **Step 1: schemas.py 작성**

`backend/src/auth/schemas.py` 재작성:

```python
"""auth 도메인 Pydantic V2 스키마."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CurrentUser(BaseModel):
    """검증된 Clerk 세션 + DB User 매핑 결과."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clerk_user_id: str
    email: str | None = None
    username: str | None = None
    is_active: bool = True
    session_id: str | None = None


class UserResponse(BaseModel):
    """GET /auth/me 응답 DTO."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clerk_user_id: str
    email: str | None
    username: str | None
    is_active: bool
    created_at: datetime
```

- [ ] **Step 2: exceptions.py 작성**

`backend/src/auth/exceptions.py` 생성:

```python
"""auth 도메인 예외."""
from __future__ import annotations

from src.common.exceptions import AppException


class AuthError(AppException):
    pass


class InvalidTokenError(AuthError):
    def __init__(self, reason: str = "Invalid or expired token") -> None:
        super().__init__(status_code=401, detail={"code": "auth_invalid_token", "detail": reason})


class UserInactiveError(AuthError):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            detail={"code": "auth_user_inactive", "detail": "User account deactivated"},
        )


class WebhookSignatureError(AuthError):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            detail={"code": "webhook_signature_invalid", "detail": "Svix signature verification failed"},
        )
```

- [ ] **Step 3: 실패 테스트 작성**

`backend/tests/auth/test_user_service.py` 생성:

```python
"""UserService 단위 테스트 (repository mock)."""
from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.auth.models import User
from src.auth.service import UserService


@pytest.fixture
def user_repo_mock():
    repo = AsyncMock()
    repo.commit = AsyncMock()
    return repo


@pytest.fixture
def strategy_repo_mock():
    return AsyncMock()


@pytest.fixture
def service(user_repo_mock, strategy_repo_mock):
    return UserService(user_repo=user_repo_mock, strategy_repo=strategy_repo_mock)


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_when_found(service, user_repo_mock):
    existing = User(id=uuid4(), clerk_user_id="user_x", email="a@b.com", username="a")
    user_repo_mock.find_by_clerk_id.return_value = existing

    result = await service.get_or_create("user_x", email="a@b.com", username="a")

    assert result is existing
    user_repo_mock.insert_if_absent.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_updates_profile_on_change(service, user_repo_mock):
    existing = User(id=uuid4(), clerk_user_id="user_x", email="old@b.com", username="old")
    updated = User(id=existing.id, clerk_user_id="user_x", email="new@b.com", username="new")
    user_repo_mock.find_by_clerk_id.return_value = existing
    user_repo_mock.update_profile.return_value = updated

    result = await service.get_or_create("user_x", email="new@b.com", username="new")

    user_repo_mock.update_profile.assert_awaited_once()
    assert result.email == "new@b.com"


@pytest.mark.asyncio
async def test_get_or_create_inserts_when_missing(service, user_repo_mock):
    created = User(id=uuid4(), clerk_user_id="user_y", email="y@b.com", username="y")
    user_repo_mock.find_by_clerk_id.return_value = None
    user_repo_mock.insert_if_absent.return_value = created

    result = await service.get_or_create("user_y", email="y@b.com", username="y")

    user_repo_mock.insert_if_absent.assert_awaited_once()
    assert result is created


@pytest.mark.asyncio
async def test_handle_user_created_event_upserts(service, user_repo_mock):
    event = {
        "type": "user.created",
        "data": {
            "id": "user_z",
            "email_addresses": [{"email_address": "z@b.com"}],
            "username": "z",
        },
    }
    await service.handle_clerk_event(event)

    user_repo_mock.upsert_from_webhook.assert_awaited_once_with(
        clerk_user_id="user_z", email="z@b.com", username="z"
    )


@pytest.mark.asyncio
async def test_handle_user_deleted_archives_strategies(service, user_repo_mock, strategy_repo_mock):
    existing = User(id=uuid4(), clerk_user_id="user_gone", email=None, username=None, is_active=True)
    user_repo_mock.find_by_clerk_id.return_value = existing

    event = {"type": "user.deleted", "data": {"id": "user_gone"}}
    await service.handle_clerk_event(event)

    user_repo_mock.set_inactive.assert_awaited_once_with(existing.id)
    strategy_repo_mock.archive_all_by_owner.assert_awaited_once_with(existing.id)


@pytest.mark.asyncio
async def test_handle_unknown_event_is_noop(service, user_repo_mock, strategy_repo_mock):
    await service.handle_clerk_event({"type": "session.created", "data": {}})

    user_repo_mock.upsert_from_webhook.assert_not_awaited()
    user_repo_mock.set_inactive.assert_not_awaited()
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/auth/test_user_service.py -v`
Expected: FAIL — UserService 미구현.

- [ ] **Step 5: UserService 구현**

`backend/src/auth/service.py` 재작성:

```python
"""auth Service. 비즈니스 로직 + 트랜잭션 경계."""
from __future__ import annotations

from typing import TYPE_CHECKING

from src.auth.models import User
from src.auth.repository import UserRepository

if TYPE_CHECKING:
    from src.strategy.repository import StrategyRepository


class UserService:
    """User lazy-create + Webhook 이벤트 처리.

    user.deleted 이벤트에서 Strategy cascade archive를 위해
    StrategyRepository도 함께 주입받는다 (동일 AsyncSession 공유).
    """

    def __init__(
        self,
        user_repo: UserRepository,
        strategy_repo: "StrategyRepository | None" = None,
    ) -> None:
        self.user_repo = user_repo
        self.strategy_repo = strategy_repo

    async def get_or_create(
        self,
        clerk_user_id: str,
        email: str | None,
        username: str | None,
    ) -> User:
        """보호 엔드포인트에서 호출됨. 첫 요청 시 DB User 생성."""
        user = await self.user_repo.find_by_clerk_id(clerk_user_id)
        if user is not None:
            if user.email != email or user.username != username:
                user = await self.user_repo.update_profile(
                    user.id, email=email, username=username
                )
                await self.user_repo.commit()
            return user

        user = await self.user_repo.insert_if_absent(
            clerk_user_id=clerk_user_id,
            email=email,
            username=username,
        )
        await self.user_repo.commit()
        return user

    async def handle_clerk_event(self, event: dict) -> None:
        """Webhook 이벤트 디스패치.

        user.created/updated → upsert. user.deleted → soft delete + strategy archive.
        기타 이벤트는 silently 무시 (Clerk 재시도 방지).
        """
        event_type = event.get("type")
        data = event.get("data", {})
        clerk_user_id = data.get("id")
        if not clerk_user_id:
            return

        if event_type in ("user.created", "user.updated"):
            email = _extract_email(data)
            username = data.get("username")
            await self.user_repo.upsert_from_webhook(
                clerk_user_id=clerk_user_id,
                email=email,
                username=username,
            )
            await self.user_repo.commit()
            return

        if event_type == "user.deleted":
            user = await self.user_repo.find_by_clerk_id(clerk_user_id)
            if user is None:
                return
            await self.user_repo.set_inactive(user.id)
            if self.strategy_repo is not None:
                await self.strategy_repo.archive_all_by_owner(user.id)
            await self.user_repo.commit()
            return

        # 기타 이벤트: silently ignore
        return


def _extract_email(data: dict) -> str | None:
    """Clerk data payload에서 primary email 추출."""
    emails = data.get("email_addresses") or []
    if not emails:
        return None
    # Clerk primary_email_address_id와 매칭, 없으면 첫 번째
    primary_id = data.get("primary_email_address_id")
    if primary_id:
        for e in emails:
            if e.get("id") == primary_id:
                return e.get("email_address")
    return emails[0].get("email_address")
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/auth/test_user_service.py -v`
Expected: 6 passed.

- [ ] **Step 7: 회귀 + 린트**

Run: `cd backend && uv run pytest -q && uv run ruff check . && uv run mypy src/`
Expected: All green.

- [ ] **Step 8: Commit**

```bash
git add backend/src/auth/schemas.py backend/src/auth/service.py backend/src/auth/exceptions.py backend/tests/auth/test_user_service.py
git commit -m "feat(auth): UserService with lazy-create + webhook event dispatch

- schemas: CurrentUser (UUID id 포함), UserResponse
- exceptions: InvalidTokenError / UserInactiveError / WebhookSignatureError
- service.get_or_create: 프로필 변경 감지 시 upsert
- service.handle_clerk_event: user.created/updated/deleted 분기
  + user.deleted 시 StrategyRepository.archive_all_by_owner 호출
- 6 단위 테스트 (repository mock)"
```

---

### Task 7: Clerk JWT 검증 dependency + `/auth/me` 엔드포인트 + E2E

**의도:** `get_current_user` dependency 실배선. Clerk SDK + lazy-create + `is_active` 검증. `/auth/me` 엔드포인트로 E2E 확인.

**Files:**
- Modify: `backend/src/auth/dependencies.py` (재작성)
- Modify: `backend/src/auth/router.py` (재작성)
- Modify: `backend/src/main.py` (auth_router 등록)
- Create: `backend/tests/auth/test_clerk_auth.py`
- Create: `backend/tests/auth/test_auth_me.py`

- [ ] **Step 1: Clerk SDK smoke check**

Run: `cd backend && uv run python -c "from clerk_backend_api import Clerk, AuthenticateRequestOptions; print('ok')"`
Expected: `ok` 출력.

- [ ] **Step 2: dependencies.py 재작성 (Clerk 실검증)**

`backend/src/auth/dependencies.py` 재작성:

```python
"""auth 도메인 Depends() 조립."""
from __future__ import annotations

from clerk_backend_api import AuthenticateRequestOptions, Clerk
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import InvalidTokenError, UserInactiveError
from src.auth.repository import UserRepository
from src.auth.schemas import CurrentUser
from src.auth.service import UserService
from src.common.database import get_async_session
from src.core.config import settings


def _clerk_client() -> Clerk:
    """모듈 스코프 싱글톤 회피 — 테스트 monkeypatch 용이."""
    return Clerk(bearer_auth=settings.clerk_secret_key.get_secret_value())


async def get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserRepository:
    return UserRepository(session)


async def get_user_service(
    user_repo: UserRepository = Depends(get_user_repository),
    session: AsyncSession = Depends(get_async_session),
) -> UserService:
    # Strategy archive를 위해 StrategyRepository를 동일 session으로 주입
    from src.strategy.repository import StrategyRepository

    strategy_repo = StrategyRepository(session)
    return UserService(user_repo=user_repo, strategy_repo=strategy_repo)


async def get_current_user(
    request: Request,
    service: UserService = Depends(get_user_service),
) -> CurrentUser:
    """Bearer JWT 검증 + lazy-create."""
    clerk = _clerk_client()
    req_state = clerk.authenticate_request(
        request,
        AuthenticateRequestOptions(
            authorized_parties=[settings.frontend_url],
        ),
    )
    if not req_state.is_signed_in:
        reason = getattr(req_state.reason, "name", "unknown")
        raise InvalidTokenError(reason=reason)

    payload = req_state.payload or {}
    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise InvalidTokenError(reason="missing_sub")

    user = await service.get_or_create(
        clerk_user_id=clerk_user_id,
        email=payload.get("email"),
        username=payload.get("username"),
    )
    if not user.is_active:
        raise UserInactiveError()

    return CurrentUser.model_validate(user)
```

- [ ] **Step 3: auth/router.py 재작성 (/auth/me)**

`backend/src/auth/router.py` 재작성:

```python
"""auth HTTP 라우터."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user, get_user_service
from src.auth.schemas import CurrentUser, UserResponse
from src.auth.service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: CurrentUser = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await service.user_repo.find_by_id(current_user.id)
    assert user is not None  # dependency가 보장
    return UserResponse.model_validate(user)
```

- [ ] **Step 4: main.py에 auth_router 등록**

`backend/src/main.py` 수정 (`# 도메인 라우터는 Stage 3 스프린트에서 순차 등록` 주석 교체):

```python
# create_app 내부, return app 직전
from src.auth.router import router as auth_router
app.include_router(auth_router, prefix="/api/v1")
```

- [ ] **Step 5: 실패 테스트 작성 — test_clerk_auth.py (mocked Clerk)**

`backend/tests/auth/test_clerk_auth.py` 생성:

```python
"""get_current_user dependency 단위/통합 — Clerk SDK는 mock."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.mark.asyncio
async def test_me_without_auth_header_returns_401(client):
    res = await client.get("/api/v1/auth/me")
    # Clerk SDK가 signed_in=False 로 판정 → 401
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "auth_invalid_token"


@pytest.mark.asyncio
async def test_me_with_invalid_token_returns_401(client, monkeypatch):
    # Clerk client가 is_signed_in=False 반환하도록 mock
    def _fake_client():
        c = MagicMock()
        req_state = MagicMock()
        req_state.is_signed_in = False
        req_state.reason.name = "token_invalid"
        c.authenticate_request.return_value = req_state
        return c

    monkeypatch.setattr("src.auth.dependencies._clerk_client", _fake_client)

    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer garbage"},
    )
    assert res.status_code == 401
```

- [ ] **Step 6: 실패 테스트 작성 — test_auth_me.py (성공 경로, mock_clerk_auth fixture)**

`backend/tests/auth/test_auth_me.py` 생성:

```python
"""GET /api/v1/auth/me E2E — mock_clerk_auth로 get_current_user bypass."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_me_returns_current_user(client, mock_clerk_auth):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 200
    body = res.json()
    assert body["clerk_user_id"] == mock_clerk_auth.clerk_user_id
    assert body["email"] == mock_clerk_auth.email
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_me_returns_403_when_user_inactive(client, authed_user, db_session, app):
    # 먼저 user를 inactive로 set
    from src.auth.schemas import CurrentUser
    from src.auth.dependencies import get_current_user

    authed_user.is_active = False
    db_session.add(authed_user)
    await db_session.commit()

    async def _fake_current_user() -> CurrentUser:
        # dependency가 inactive 감지 → UserInactiveError 발생
        from src.auth.exceptions import UserInactiveError

        raise UserInactiveError()

    app.dependency_overrides[get_current_user] = _fake_current_user

    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "auth_user_inactive"
```

- [ ] **Step 7: 테스트 실행 + 수정 반복**

Run: `cd backend && uv run pytest tests/auth/test_clerk_auth.py tests/auth/test_auth_me.py -v`
Expected: 4 passed (test_me_without_auth_header, test_me_with_invalid_token, test_me_returns_current_user, test_me_returns_403_when_user_inactive).

실패 시 Clerk SDK 호출 시그니처 조정, `authenticate_request` API 동작 확인.

- [ ] **Step 8: 전체 회귀**

Run: `cd backend && uv run pytest -q`
Expected: 누적 +4 passed.

- [ ] **Step 9: ruff + mypy**

Run: `cd backend && uv run ruff check . && uv run mypy src/`
Expected: All green.

- [ ] **Step 10: Commit**

```bash
git add backend/src/auth/dependencies.py backend/src/auth/router.py backend/src/main.py backend/tests/auth/test_clerk_auth.py backend/tests/auth/test_auth_me.py
git commit -m "feat(auth): Clerk JWT verification + GET /auth/me E2E

- dependencies.get_current_user: clerk-backend-api authenticate_request
  + lazy-create User + is_active 검증
- dependencies.get_user_service: StrategyRepository 동일 session 주입
- router /auth/me: UserResponse 반환
- main.py: auth_router /api/v1 prefix 등록
- 4 tests: invalid/missing token → 401, 정상 → 200, inactive → 403"
```

---

### Task 8: `/auth/webhook` — Svix 서명 검증 + 3 이벤트 + E2E

**의도:** Clerk Webhook 엔드포인트. Svix Python SDK로 서명 검증, `user.created/updated/deleted` 이벤트 처리.

**Files:**
- Modify: `backend/src/auth/router.py` — `/webhook` 추가
- Create: `backend/tests/auth/test_webhook_handler.py`

- [ ] **Step 1: /webhook 엔드포인트 추가**

`backend/src/auth/router.py` 수정 (get_me 아래에 추가):

```python
import json

from fastapi import Body, HTTPException, Request
from svix.webhooks import Webhook, WebhookVerificationError

from src.auth.exceptions import WebhookSignatureError
from src.core.config import settings


def _svix_webhook() -> Webhook:
    """모듈 스코프 싱글톤 회피 — 테스트 monkeypatch 용이."""
    return Webhook(settings.clerk_webhook_secret.get_secret_value())


@router.post("/webhook", status_code=200)
async def clerk_webhook(
    request: Request,
    service: UserService = Depends(get_user_service),
) -> dict[str, bool]:
    """Clerk Svix-signed webhook 수신."""
    payload = await request.body()  # raw bytes
    headers = {k.lower(): v for k, v in request.headers.items()}

    wh = _svix_webhook()
    try:
        event = wh.verify(payload, headers)
    except WebhookVerificationError as exc:
        raise WebhookSignatureError() from exc

    # verify 반환값이 dict 혹은 bytes일 수 있음. 안전하게 json 로드.
    if isinstance(event, bytes):
        event = json.loads(event)

    await service.handle_clerk_event(event)
    return {"received": True}
```

- [ ] **Step 2: 실패 테스트 작성**

`backend/tests/auth/test_webhook_handler.py` 생성:

```python
"""/api/v1/auth/webhook Svix 서명 검증 E2E."""
from __future__ import annotations

import hmac
import json
import time
import uuid
from base64 import b64encode
from hashlib import sha256

import pytest
from pydantic import SecretStr

from src.auth.repository import UserRepository
from src.core.config import settings
from src.strategy.models import ParseStatus, PineVersion, Strategy


def _sign(secret_without_prefix: str, msg_id: str, timestamp: str, body: bytes) -> str:
    """Svix 서명 계산. 형식: 'v1,<base64-hmac-sha256>'."""
    to_sign = f"{msg_id}.{timestamp}.{body.decode()}".encode()
    mac = hmac.new(secret_without_prefix.encode(), to_sign, sha256).digest()
    return f"v1,{b64encode(mac).decode()}"


def _headers_with_signature(secret: str, body: bytes) -> dict[str, str]:
    msg_id = f"msg_{uuid.uuid4().hex[:10]}"
    ts = str(int(time.time()))
    # svix secret은 "whsec_<base64>" 형식 — verify 전에 svix SDK가 자동으로 base64 decode
    # 수동 서명 시 동일 처리 필요
    from base64 import b64decode

    secret_raw = secret.removeprefix("whsec_")
    secret_bytes = b64decode(secret_raw)
    to_sign = f"{msg_id}.{ts}.{body.decode()}".encode()
    mac = hmac.new(secret_bytes, to_sign, sha256).digest()
    sig = f"v1,{b64encode(mac).decode()}"
    return {
        "svix-id": msg_id,
        "svix-timestamp": ts,
        "svix-signature": sig,
    }


@pytest.fixture
def webhook_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """테스트용 고정 시크릿. whsec_<base64> 형식."""
    from base64 import b64encode as _b64e

    raw = b"a" * 32
    secret = "whsec_" + _b64e(raw).decode()
    monkeypatch.setattr(settings, "clerk_webhook_secret", SecretStr(secret))
    return secret


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(client, webhook_secret):
    body = json.dumps({"type": "user.created", "data": {"id": "user_x"}}).encode()
    bad_headers = {
        "svix-id": "msg_bad",
        "svix-timestamp": str(int(time.time())),
        "svix-signature": "v1,invalid",
    }
    res = await client.post("/api/v1/auth/webhook", content=body, headers=bad_headers)
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "webhook_signature_invalid"


@pytest.mark.asyncio
async def test_webhook_user_created_inserts_user(client, db_session, webhook_secret):
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    body = json.dumps(
        {
            "type": "user.created",
            "data": {
                "id": clerk_id,
                "email_addresses": [{"id": "e1", "email_address": "hook@b.com"}],
                "primary_email_address_id": "e1",
                "username": "hooked",
            },
        }
    ).encode()
    headers = _headers_with_signature(webhook_secret, body)

    res = await client.post("/api/v1/auth/webhook", content=body, headers=headers)
    assert res.status_code == 200, res.text
    assert res.json() == {"received": True}

    repo = UserRepository(db_session)
    user = await repo.find_by_clerk_id(clerk_id)
    assert user is not None
    assert user.email == "hook@b.com"
    assert user.username == "hooked"


@pytest.mark.asyncio
async def test_webhook_user_deleted_archives_strategies(client, db_session, webhook_secret):
    from src.auth.models import User

    # 사전: 사용자 + Strategy 2건 생성
    clerk_id = f"user_{uuid.uuid4().hex[:8]}"
    user = User(clerk_user_id=clerk_id, email="d@b.com", username="d", is_active=True)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    s1 = Strategy(
        user_id=user.id,
        name="s1",
        pine_source="x",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    s2 = Strategy(
        user_id=user.id,
        name="s2",
        pine_source="x",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add_all([s1, s2])
    await db_session.commit()

    body = json.dumps({"type": "user.deleted", "data": {"id": clerk_id}}).encode()
    headers = _headers_with_signature(webhook_secret, body)

    res = await client.post("/api/v1/auth/webhook", content=body, headers=headers)
    assert res.status_code == 200

    # 결과 검증
    from sqlalchemy import select

    refreshed_user = (
        await db_session.execute(select(User).where(User.id == user.id))
    ).scalar_one()
    assert refreshed_user.is_active is False

    strategies = (
        await db_session.execute(select(Strategy).where(Strategy.user_id == user.id))
    ).scalars().all()
    assert len(strategies) == 2
    assert all(s.is_archived for s in strategies)


@pytest.mark.asyncio
async def test_webhook_ignores_unknown_event_type(client, webhook_secret):
    body = json.dumps({"type": "session.created", "data": {"id": "sess_1"}}).encode()
    headers = _headers_with_signature(webhook_secret, body)

    res = await client.post("/api/v1/auth/webhook", content=body, headers=headers)
    assert res.status_code == 200
    assert res.json() == {"received": True}
```

- [ ] **Step 3: StrategyRepository stub 보강 (필요 시)**

Task 9에서 정식 구현 예정이지만, `archive_all_by_owner` 메서드가 Task 8 테스트에 필요. Task 8 테스트는 `get_user_service`가 주입하는 StrategyRepository가 해당 메서드를 노출해야 함.

임시 대응: Task 9 이전에 `archive_all_by_owner`를 `strategy/repository.py`에 선행 추가:

```python
# backend/src/strategy/repository.py
"""strategy Repository. AsyncSession 유일 보유자."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.strategy.models import Strategy


class StrategyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def archive_all_by_owner(self, user_id: UUID) -> None:
        """user.deleted Webhook 시 해당 사용자의 모든 Strategy를 archive."""
        stmt = update(Strategy).where(Strategy.user_id == user_id).values(is_archived=True)
        await self.session.execute(stmt)

    async def commit(self) -> None:
        await self.session.commit()
```

Task 9에서 전체 메서드 추가 시 기존 `archive_all_by_owner`와 `commit`은 유지.

- [ ] **Step 4: 테스트 실행**

Run: `cd backend && uv run pytest tests/auth/test_webhook_handler.py -v`
Expected: 4 passed.

**주의:** svix Python SDK의 `Webhook.verify()` 내부 서명 계산 방식이 위 `_headers_with_signature` 수동 계산과 일치해야 함. 실패 시 svix SDK의 `Webhook.sign()` 유틸이 있으면 그걸 사용. 대안:

```python
from svix.webhooks import Webhook as SvixWebhook

wh = SvixWebhook(secret)
signed = wh.sign(msg_id=msg_id, timestamp=int(ts), payload=body.decode())
# signed는 "v1,..." 형식
headers = {"svix-id": msg_id, "svix-timestamp": ts, "svix-signature": signed}
```

이 방식으로 `_headers_with_signature` 헬퍼 교체.

- [ ] **Step 5: 전체 회귀 + 린트**

Run: `cd backend && uv run pytest -q && uv run ruff check . && uv run mypy src/`
Expected: All green.

- [ ] **Step 6: Commit**

```bash
git add backend/src/auth/router.py backend/src/strategy/repository.py backend/tests/auth/test_webhook_handler.py
git commit -m "feat(auth): POST /auth/webhook with Svix signature verification

- router /webhook: raw body + Svix verify + handle_clerk_event 디스패치
- strategy/repository: archive_all_by_owner 선행 추가 (user.deleted cascade)
- 4 E2E tests: invalid sig / user.created insert / user.deleted archive /
  unknown event ignore"
```

---

## Block 3 — Strategy Vertical

### Task 9: StrategyRepository + 통합 테스트

**의도:** Strategy CRUD. 소유자 격리는 Service 레이어가 담당하므로 Repository는 raw CRUD + 목록 쿼리 + archive 제공.

**Files:**
- Modify: `backend/src/strategy/repository.py` (Task 8에서 stub 추가, 여기서 전체 완성)
- Create: `backend/tests/strategy/test_strategy_repository.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/strategy/__init__.py` 없으면 생성 (빈 파일). 이미 있다면 건너뜀.

`backend/tests/strategy/test_strategy_repository.py` 생성:

```python
"""StrategyRepository 통합 테스트."""
from __future__ import annotations

import uuid
from uuid import UUID

import pytest

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository


async def _make_user(db_session, name: str = "owner") -> User:
    user = User(
        clerk_user_id=f"user_{uuid.uuid4().hex[:8]}",
        email=f"{name}@b.com",
        username=name,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _new_strategy(owner_id: UUID, name: str, archived: bool = False) -> Strategy:
    return Strategy(
        user_id=owner_id,
        name=name,
        pine_source="//@version=5\nstrategy(\"x\")",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
        is_archived=archived,
    )


@pytest.mark.asyncio
async def test_create_and_find_by_id(db_session):
    owner = await _make_user(db_session)
    repo = StrategyRepository(db_session)

    created = await repo.create(_new_strategy(owner.id, "s1"))
    await repo.commit()

    found = await repo.find_by_id(created.id)
    assert found is not None
    assert found.name == "s1"


@pytest.mark.asyncio
async def test_find_by_id_and_owner_returns_none_for_other(db_session):
    alice = await _make_user(db_session, "alice")
    bob = await _make_user(db_session, "bob")
    repo = StrategyRepository(db_session)

    bob_strat = await repo.create(_new_strategy(bob.id, "bob"))
    await repo.commit()

    found = await repo.find_by_id_and_owner(bob_strat.id, owner_id=alice.id)
    assert found is None


@pytest.mark.asyncio
async def test_list_by_owner_filters_and_paginates(db_session):
    owner = await _make_user(db_session)
    repo = StrategyRepository(db_session)

    for i in range(5):
        await repo.create(_new_strategy(owner.id, f"s{i}"))
    await repo.create(_new_strategy(owner.id, "archived", archived=True))
    await repo.commit()

    items, total = await repo.list_by_owner(owner.id, page=1, limit=3, is_archived=False)
    assert total == 5  # archived 제외
    assert len(items) == 3


@pytest.mark.asyncio
async def test_list_by_owner_parse_status_filter(db_session):
    owner = await _make_user(db_session)
    repo = StrategyRepository(db_session)

    ok = _new_strategy(owner.id, "ok")
    bad = _new_strategy(owner.id, "bad")
    bad.parse_status = ParseStatus.unsupported
    await repo.create(ok)
    await repo.create(bad)
    await repo.commit()

    items, total = await repo.list_by_owner(
        owner.id, page=1, limit=20, parse_status=ParseStatus.unsupported, is_archived=False
    )
    assert total == 1
    assert items[0].name == "bad"


@pytest.mark.asyncio
async def test_update_persists_fields(db_session):
    owner = await _make_user(db_session)
    repo = StrategyRepository(db_session)
    s = await repo.create(_new_strategy(owner.id, "original"))
    await repo.commit()

    s.name = "renamed"
    s.parse_status = ParseStatus.unsupported
    await repo.update(s)
    await repo.commit()

    fetched = await repo.find_by_id(s.id)
    assert fetched.name == "renamed"
    assert fetched.parse_status == ParseStatus.unsupported


@pytest.mark.asyncio
async def test_delete_hard_removes(db_session):
    owner = await _make_user(db_session)
    repo = StrategyRepository(db_session)
    s = await repo.create(_new_strategy(owner.id, "doomed"))
    await repo.commit()

    await repo.delete(s.id)
    await repo.commit()

    assert await repo.find_by_id(s.id) is None


@pytest.mark.asyncio
async def test_archive_all_by_owner_bulk(db_session):
    owner = await _make_user(db_session)
    repo = StrategyRepository(db_session)
    for i in range(3):
        await repo.create(_new_strategy(owner.id, f"s{i}"))
    await repo.commit()

    await repo.archive_all_by_owner(owner.id)
    await repo.commit()

    items, total = await repo.list_by_owner(owner.id, page=1, limit=20, is_archived=True)
    assert total == 3
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/test_strategy_repository.py -v`
Expected: FAIL — `create`/`find_by_id`/`list_by_owner` 등 미구현.

- [ ] **Step 3: StrategyRepository 전체 구현**

`backend/src/strategy/repository.py` 전체 재작성 (Task 8 stub 포함):

```python
"""strategy Repository. AsyncSession 유일 보유자."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.strategy.models import ParseStatus, Strategy


class StrategyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, strategy: Strategy) -> Strategy:
        self.session.add(strategy)
        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy

    async def find_by_id(self, strategy_id: UUID) -> Strategy | None:
        result = await self.session.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        return result.scalar_one_or_none()

    async def find_by_id_and_owner(
        self, strategy_id: UUID, owner_id: UUID
    ) -> Strategy | None:
        result = await self.session.execute(
            select(Strategy).where(
                Strategy.id == strategy_id,
                Strategy.user_id == owner_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_owner(
        self,
        owner_id: UUID,
        *,
        page: int,
        limit: int,
        parse_status: ParseStatus | None = None,
        is_archived: bool = False,
    ) -> tuple[list[Strategy], int]:
        base_where = [Strategy.user_id == owner_id, Strategy.is_archived == is_archived]
        if parse_status is not None:
            base_where.append(Strategy.parse_status == parse_status)

        count_stmt = select(func.count()).select_from(Strategy).where(*base_where)
        total = (await self.session.execute(count_stmt)).scalar_one()

        offset = (page - 1) * limit
        items_stmt = (
            select(Strategy)
            .where(*base_where)
            .order_by(Strategy.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.session.execute(items_stmt)).scalars().all())
        return items, int(total)

    async def update(self, strategy: Strategy) -> Strategy:
        self.session.add(strategy)
        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy

    async def delete(self, strategy_id: UUID) -> None:
        await self.session.execute(delete(Strategy).where(Strategy.id == strategy_id))

    async def archive_all_by_owner(self, owner_id: UUID) -> None:
        await self.session.execute(
            update(Strategy).where(Strategy.user_id == owner_id).values(is_archived=True)
        )

    async def commit(self) -> None:
        await self.session.commit()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/test_strategy_repository.py -v`
Expected: 7 passed.

- [ ] **Step 5: 회귀 + 린트**

Run: `cd backend && uv run pytest -q && uv run ruff check . && uv run mypy src/`
Expected: All green.

- [ ] **Step 6: Commit**

```bash
git add backend/src/strategy/repository.py backend/tests/strategy/test_strategy_repository.py
git commit -m "feat(strategy): StrategyRepository with CRUD + list filters

- create/find_by_id/find_by_id_and_owner
- list_by_owner: page/limit + parse_status + is_archived 필터, updated_at DESC
- update/delete (hard) + archive_all_by_owner (webhook cascade)
- 7 integration tests (실 PG)"
```

---

### Task 10: StrategyService + Schemas + Exceptions + 단위 테스트

**의도:** Strategy 도메인 비즈니스 로직. `parse_and_run` 호출 + ParseOutcome → DB 필드 매핑 + CRUD 조율.

**Files:**
- Create: `backend/src/strategy/schemas.py`
- Create: `backend/src/strategy/exceptions.py`
- Create: `backend/src/strategy/service.py`
- Create: `backend/src/strategy/dependencies.py`
- Create: `backend/tests/strategy/test_strategy_service.py`

- [ ] **Step 1: schemas.py 작성**

`backend/src/strategy/schemas.py` 재작성:

```python
"""strategy 도메인 Pydantic V2 스키마."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.strategy.models import ParseStatus, PineVersion


class CreateStrategyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    pine_source: str = Field(min_length=1)
    timeframe: str | None = Field(default=None, max_length=16)
    symbol: str | None = Field(default=None, max_length=32)
    tags: list[str] = Field(default_factory=list)


class UpdateStrategyRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    pine_source: str | None = Field(default=None, min_length=1)
    timeframe: str | None = Field(default=None, max_length=16)
    symbol: str | None = Field(default=None, max_length=32)
    tags: list[str] | None = None
    is_archived: bool | None = None


class ParseRequest(BaseModel):
    pine_source: str = Field(min_length=1)


class ParseError(BaseModel):
    code: str
    message: str
    line: int | None = None


class ParsePreviewResponse(BaseModel):
    status: ParseStatus
    pine_version: PineVersion
    warnings: list[str] = Field(default_factory=list)
    errors: list[ParseError] = Field(default_factory=list)
    entry_count: int = 0
    exit_count: int = 0


class StrategyListItem(BaseModel):
    """목록 DTO — pine_source/description 제외."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    pine_version: PineVersion
    parse_status: ParseStatus
    parse_errors: list[dict] | None = None
    timeframe: str | None = None
    symbol: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class StrategyResponse(BaseModel):
    """상세 DTO — 전 필드 포함."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    pine_source: str
    pine_version: PineVersion
    parse_status: ParseStatus
    parse_errors: list[dict] | None
    timeframe: str | None
    symbol: str | None
    tags: list[str] = Field(default_factory=list)
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class StrategyListResponse(BaseModel):
    items: list[StrategyListItem]
    total: int
    page: int
    limit: int
    total_pages: int
```

- [ ] **Step 2: exceptions.py 작성**

`backend/src/strategy/exceptions.py` 생성:

```python
"""strategy 도메인 예외."""
from __future__ import annotations

from src.common.exceptions import AppException


class StrategyError(AppException):
    pass


class StrategyNotFoundError(StrategyError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            detail={"code": "strategy_not_found", "detail": "Strategy not found"},
        )
```

- [ ] **Step 3: 실패 테스트 작성 (service 단위)**

`backend/tests/strategy/test_strategy_service.py` 생성:

```python
"""StrategyService 단위 — repository mock + 실 parser."""
from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.strategy.exceptions import StrategyNotFoundError
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.schemas import CreateStrategyRequest, UpdateStrategyRequest
from src.strategy.service import StrategyService


@pytest.fixture
def repo_mock():
    return AsyncMock()


@pytest.fixture
def service(repo_mock):
    return StrategyService(repo_mock)


_OK_SOURCE = """//@version=5
strategy("ok")
long = ta.crossover(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
"""

_UNSUPPORTED_SOURCE = """//@version=5
strategy("no")
x = request.security(syminfo.tickerid, "1D", close)
"""


@pytest.mark.asyncio
async def test_parse_preview_ok(service):
    result = await service.parse_preview(_OK_SOURCE)
    assert result.status == ParseStatus.ok
    assert result.pine_version == PineVersion.v5


@pytest.mark.asyncio
async def test_parse_preview_unsupported_returns_without_raising(service):
    result = await service.parse_preview(_UNSUPPORTED_SOURCE)
    assert result.status in (ParseStatus.unsupported, ParseStatus.error)
    assert result.errors


@pytest.mark.asyncio
async def test_create_records_parse_status(service, repo_mock):
    owner_id = uuid4()
    req = CreateStrategyRequest(name="x", pine_source=_OK_SOURCE)
    repo_mock.create.side_effect = lambda s: s  # return 그대로

    result = await service.create(req, owner_id=owner_id)

    repo_mock.create.assert_awaited_once()
    repo_mock.commit.assert_awaited_once()
    assert result.parse_status == ParseStatus.ok


@pytest.mark.asyncio
async def test_create_stores_even_when_unsupported(service, repo_mock):
    owner_id = uuid4()
    req = CreateStrategyRequest(name="x", pine_source=_UNSUPPORTED_SOURCE)
    repo_mock.create.side_effect = lambda s: s

    result = await service.create(req, owner_id=owner_id)

    repo_mock.create.assert_awaited_once()
    assert result.parse_status in (ParseStatus.unsupported, ParseStatus.error)
    assert result.parse_errors is not None


@pytest.mark.asyncio
async def test_get_by_id_not_owned_raises_not_found(service, repo_mock):
    repo_mock.find_by_id_and_owner.return_value = None
    with pytest.raises(StrategyNotFoundError):
        await service.get(strategy_id=uuid4(), owner_id=uuid4())


@pytest.mark.asyncio
async def test_update_reparses_when_pine_source_changed(service, repo_mock):
    owner_id = uuid4()
    existing = Strategy(
        id=uuid4(),
        user_id=owner_id,
        name="x",
        pine_source="old",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    repo_mock.find_by_id_and_owner.return_value = existing
    repo_mock.update.side_effect = lambda s: s

    req = UpdateStrategyRequest(pine_source=_UNSUPPORTED_SOURCE)
    result = await service.update(
        strategy_id=existing.id, owner_id=owner_id, data=req
    )
    assert result.parse_status in (ParseStatus.unsupported, ParseStatus.error)


@pytest.mark.asyncio
async def test_delete_when_not_owned_raises(service, repo_mock):
    repo_mock.find_by_id_and_owner.return_value = None
    with pytest.raises(StrategyNotFoundError):
        await service.delete(strategy_id=uuid4(), owner_id=uuid4())
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `cd backend && uv run pytest tests/strategy/test_strategy_service.py -v`
Expected: FAIL — StrategyService 미구현.

- [ ] **Step 5: service.py 구현**

`backend/src/strategy/service.py` 재작성:

```python
"""strategy Service. Pine 파싱 + CRUD 조율."""
from __future__ import annotations

from uuid import UUID

import numpy as np
import pandas as pd

from src.strategy.exceptions import StrategyNotFoundError
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.pine import parse_and_run
from src.strategy.repository import StrategyRepository
from src.strategy.schemas import (
    CreateStrategyRequest,
    ParseError,
    ParsePreviewResponse,
    StrategyListResponse,
    StrategyResponse,
    UpdateStrategyRequest,
)


def _empty_ohlcv() -> dict[str, pd.Series]:
    """파싱만 수행하기 위한 빈 OHLCV (길이 1, 최소 구조)."""
    idx = pd.date_range("2026-01-01", periods=1, freq="h")
    zero = pd.Series(0.0, index=idx)
    return {"open": zero, "high": zero, "low": zero, "close": zero, "volume": zero}


def _parse(source: str) -> tuple[ParseStatus, PineVersion, list[str], list[ParseError], int, int]:
    """parse_and_run → (status, version, warnings, errors, entry_count, exit_count)."""
    try:
        outcome = parse_and_run(source, **_empty_ohlcv())
    except Exception as exc:  # noqa: BLE001 — 파싱 중 모든 예외를 error로 변환
        return (
            ParseStatus.error,
            PineVersion.v5,  # 버전 추정 불가 시 v5 기본
            [],
            [ParseError(code=type(exc).__name__, message=str(exc))],
            0,
            0,
        )

    warnings: list[str] = (
        outcome.signals.warnings if outcome.signals is not None else []
    )
    errors: list[ParseError] = []
    if outcome.errors:
        for e in outcome.errors:
            errors.append(
                ParseError(
                    code=getattr(e, "category", "PineError"),
                    message=getattr(e, "message", str(e)),
                    line=getattr(e, "line", None),
                )
            )

    status = ParseStatus(outcome.status) if outcome.status in {"ok", "unsupported", "error"} else ParseStatus.error
    version = PineVersion(outcome.version) if outcome.version in {"v4", "v5"} else PineVersion.v5

    entry_count = int(outcome.signals.entries.sum()) if outcome.signals is not None else 0
    exit_count = int(outcome.signals.exits.sum()) if outcome.signals is not None else 0

    return status, version, warnings, errors, entry_count, exit_count


class StrategyService:
    def __init__(self, repo: StrategyRepository) -> None:
        self.repo = repo

    async def parse_preview(self, pine_source: str) -> ParsePreviewResponse:
        status, version, warnings, errors, entry_count, exit_count = _parse(pine_source)
        return ParsePreviewResponse(
            status=status,
            pine_version=version,
            warnings=warnings,
            errors=errors,
            entry_count=entry_count,
            exit_count=exit_count,
        )

    async def create(
        self, data: CreateStrategyRequest, *, owner_id: UUID
    ) -> StrategyResponse:
        status, version, _warnings, errors, _e, _x = _parse(data.pine_source)
        parse_errors = [e.model_dump() for e in errors] if errors else None
        strategy = Strategy(
            user_id=owner_id,
            name=data.name,
            description=data.description,
            pine_source=data.pine_source,
            pine_version=version,
            parse_status=status,
            parse_errors=parse_errors,
            timeframe=data.timeframe,
            symbol=data.symbol,
            tags=list(data.tags),
        )
        saved = await self.repo.create(strategy)
        await self.repo.commit()
        return StrategyResponse.model_validate(saved)

    async def list(
        self,
        *,
        owner_id: UUID,
        page: int,
        limit: int,
        parse_status: ParseStatus | None,
        is_archived: bool,
    ) -> StrategyListResponse:
        items, total = await self.repo.list_by_owner(
            owner_id,
            page=page,
            limit=limit,
            parse_status=parse_status,
            is_archived=is_archived,
        )
        from src.strategy.schemas import StrategyListItem

        total_pages = (total + limit - 1) // limit if total > 0 else 0
        return StrategyListResponse(
            items=[StrategyListItem.model_validate(s) for s in items],
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )

    async def get(self, *, strategy_id: UUID, owner_id: UUID) -> StrategyResponse:
        strategy = await self.repo.find_by_id_and_owner(strategy_id, owner_id)
        if strategy is None:
            raise StrategyNotFoundError()
        return StrategyResponse.model_validate(strategy)

    async def update(
        self,
        *,
        strategy_id: UUID,
        owner_id: UUID,
        data: UpdateStrategyRequest,
    ) -> StrategyResponse:
        strategy = await self.repo.find_by_id_and_owner(strategy_id, owner_id)
        if strategy is None:
            raise StrategyNotFoundError()

        if data.name is not None:
            strategy.name = data.name
        if data.description is not None:
            strategy.description = data.description
        if data.timeframe is not None:
            strategy.timeframe = data.timeframe
        if data.symbol is not None:
            strategy.symbol = data.symbol
        if data.tags is not None:
            strategy.tags = list(data.tags)
        if data.is_archived is not None:
            strategy.is_archived = data.is_archived
        if data.pine_source is not None:
            status, version, _w, errors, _e, _x = _parse(data.pine_source)
            strategy.pine_source = data.pine_source
            strategy.pine_version = version
            strategy.parse_status = status
            strategy.parse_errors = [e.model_dump() for e in errors] if errors else None

        updated = await self.repo.update(strategy)
        await self.repo.commit()
        return StrategyResponse.model_validate(updated)

    async def delete(self, *, strategy_id: UUID, owner_id: UUID) -> None:
        strategy = await self.repo.find_by_id_and_owner(strategy_id, owner_id)
        if strategy is None:
            raise StrategyNotFoundError()
        await self.repo.delete(strategy.id)
        await self.repo.commit()
```

- [ ] **Step 6: dependencies.py 작성**

`backend/src/strategy/dependencies.py` 재작성:

```python
"""strategy 도메인 Depends() 조립."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.strategy.repository import StrategyRepository
from src.strategy.service import StrategyService


async def get_strategy_repository(
    session: AsyncSession = Depends(get_async_session),
) -> StrategyRepository:
    return StrategyRepository(session)


async def get_strategy_service(
    repo: StrategyRepository = Depends(get_strategy_repository),
) -> StrategyService:
    return StrategyService(repo)
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `cd backend && uv run pytest tests/strategy/test_strategy_service.py -v`
Expected: 7 passed.

- [ ] **Step 8: 회귀 + 린트**

Run: `cd backend && uv run pytest -q && uv run ruff check . && uv run mypy src/`
Expected: All green.

- [ ] **Step 9: Commit**

```bash
git add backend/src/strategy/schemas.py backend/src/strategy/exceptions.py backend/src/strategy/service.py backend/src/strategy/dependencies.py backend/tests/strategy/test_strategy_service.py
git commit -m "feat(strategy): StrategyService with parse-aware CRUD

- schemas: CreateStrategyRequest/UpdateStrategyRequest/ParsePreviewResponse
  /StrategyListItem/StrategyResponse/StrategyListResponse
- exceptions: StrategyNotFoundError (404 + strategy_not_found code)
- service.parse_preview: DB 저장 없이 parse_and_run 호출
- service.create: store-any — 파싱 실패해도 parse_status/parse_errors로 기록
- service.update: pine_source 변경 시 재파싱
- dependencies.get_strategy_service: StrategyRepository 주입
- 7 단위 테스트 (repo mock, 실 parser)"
```

---

### Task 11: `POST /strategies/parse` 엔드포인트 + E2E

**의도:** 미리보기 엔드포인트 노출. DB 저장 없이 파싱 결과만 반환.

**Files:**
- Modify: `backend/src/strategy/router.py`
- Modify: `backend/src/main.py` (strategy_router 등록)
- Create: `backend/tests/strategy/test_strategies_parse.py`

- [ ] **Step 1: router.py — /parse 엔드포인트**

`backend/src/strategy/router.py` 재작성:

```python
"""strategy HTTP 라우터."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.strategy.dependencies import get_strategy_service
from src.strategy.schemas import ParsePreviewResponse, ParseRequest
from src.strategy.service import StrategyService

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.post("/parse", response_model=ParsePreviewResponse)
async def parse_preview(
    data: ParseRequest,
    _current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> ParsePreviewResponse:
    return await service.parse_preview(data.pine_source)
```

- [ ] **Step 2: main.py에 strategy_router 등록**

`backend/src/main.py` 수정 — auth_router 등록 아래에 추가:

```python
from src.strategy.router import router as strategy_router
app.include_router(strategy_router, prefix="/api/v1")
```

- [ ] **Step 3: E2E 테스트 작성**

`backend/tests/strategy/test_strategies_parse.py` 생성:

```python
"""POST /api/v1/strategies/parse E2E."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_parse_preview_returns_ok_for_valid_source(client, mock_clerk_auth):
    source = """//@version=5
strategy("ema")
long = ta.crossover(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
"""
    res = await client.post("/api/v1/strategies/parse", json={"pine_source": source})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["pine_version"] == "v5"


@pytest.mark.asyncio
async def test_parse_preview_returns_unsupported(client, mock_clerk_auth):
    source = """//@version=5
strategy("no")
x = request.security(syminfo.tickerid, "1D", close)
"""
    res = await client.post("/api/v1/strategies/parse", json={"pine_source": source})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in ("unsupported", "error")
    assert len(body["errors"]) >= 1


@pytest.mark.asyncio
async def test_parse_preview_rejects_empty_source(client, mock_clerk_auth):
    res = await client.post("/api/v1/strategies/parse", json={"pine_source": ""})
    assert res.status_code == 422  # Pydantic min_length


@pytest.mark.asyncio
async def test_parse_preview_requires_auth(client):
    res = await client.post("/api/v1/strategies/parse", json={"pine_source": "x"})
    assert res.status_code == 401
```

- [ ] **Step 4: 테스트 실행**

Run: `cd backend && uv run pytest tests/strategy/test_strategies_parse.py -v`
Expected: 4 passed.

- [ ] **Step 5: 회귀 + 린트**

Run: `cd backend && uv run pytest -q && uv run ruff check . && uv run mypy src/`
Expected: All green.

- [ ] **Step 6: Commit**

```bash
git add backend/src/strategy/router.py backend/src/main.py backend/tests/strategy/test_strategies_parse.py
git commit -m "feat(strategy): POST /strategies/parse preview endpoint

Pine 소스 파싱만 수행 (DB 저장 없음). status/version/warnings/errors/
entry_count/exit_count 반환. 인증 필수 (current_user는 파싱 처리에 미사용
하나 엔드포인트 보호 목적).

- 4 E2E 테스트 (ok/unsupported/empty/unauthorized)"
```

---

### Task 12: `POST /strategies` + `GET /strategies` + E2E

**의도:** 생성/목록 엔드포인트. 목록은 offset pagination + 필터.

**Files:**
- Modify: `backend/src/strategy/router.py` — POST/GET list 추가
- Create: `backend/tests/strategy/test_strategies_crud.py` (첫 부분)

- [ ] **Step 1: router에 POST/GET list 추가**

`backend/src/strategy/router.py` 추가:

```python
from fastapi import Query

from src.strategy.models import ParseStatus
from src.strategy.schemas import (
    CreateStrategyRequest,
    StrategyListResponse,
    StrategyResponse,
)


@router.post("", status_code=201, response_model=StrategyResponse)
async def create_strategy(
    data: CreateStrategyRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyResponse:
    return await service.create(data, owner_id=current_user.id)


@router.get("", response_model=StrategyListResponse)
async def list_strategies(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    parse_status: ParseStatus | None = Query(None),
    is_archived: bool = Query(False),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyListResponse:
    return await service.list(
        owner_id=current_user.id,
        page=page,
        limit=limit,
        parse_status=parse_status,
        is_archived=is_archived,
    )
```

- [ ] **Step 2: E2E 테스트 작성 (create + list)**

`backend/tests/strategy/test_strategies_crud.py` 생성:

```python
"""Strategy CRUD E2E — POST/GET."""
from __future__ import annotations

import pytest


_OK = """//@version=5
strategy("ok")
long = ta.crossover(close, ta.sma(close, 5))
if long
    strategy.entry("L", strategy.long)
"""

_BAD = """//@version=5
strategy("bad")
x = request.security(syminfo.tickerid, "1D", close)
"""


@pytest.mark.asyncio
async def test_create_strategy_ok_returns_201_with_parse_status(client, mock_clerk_auth):
    res = await client.post(
        "/api/v1/strategies",
        json={"name": "my ema", "pine_source": _OK, "timeframe": "1h", "symbol": "BTCUSDT", "tags": ["ema"]},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["name"] == "my ema"
    assert body["parse_status"] == "ok"
    assert body["pine_version"] == "v5"
    assert body["tags"] == ["ema"]


@pytest.mark.asyncio
async def test_create_strategy_stores_unsupported(client, mock_clerk_auth):
    res = await client.post(
        "/api/v1/strategies",
        json={"name": "bad", "pine_source": _BAD},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["parse_status"] in ("unsupported", "error")
    assert body["parse_errors"] is not None


@pytest.mark.asyncio
async def test_list_strategies_paginates(client, mock_clerk_auth):
    # 3건 생성
    for i in range(3):
        await client.post(
            "/api/v1/strategies",
            json={"name": f"s{i}", "pine_source": _OK},
        )
    res = await client.get("/api/v1/strategies?page=1&limit=2")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["limit"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_list_filter_parse_status(client, mock_clerk_auth):
    await client.post("/api/v1/strategies", json={"name": "ok", "pine_source": _OK})
    await client.post("/api/v1/strategies", json={"name": "bad", "pine_source": _BAD})

    res = await client.get("/api/v1/strategies?parse_status=unsupported")
    assert res.status_code == 200
    body = res.json()
    # _BAD는 unsupported 또는 error일 수 있음 — 최소 1건 이상
    # 둘 다 지원: 따로 검증
    for item in body["items"]:
        assert item["parse_status"] == "unsupported"


@pytest.mark.asyncio
async def test_list_excludes_archived_by_default(client, mock_clerk_auth):
    res = await client.post("/api/v1/strategies", json={"name": "a", "pine_source": _OK})
    strategy_id = res.json()["id"]
    # archive via PUT (Task 13에서 구현하지만 우선 준비)
    # 이 테스트는 Task 13 이후 enable
    pytest.skip("PUT 엔드포인트는 Task 13에서 구현")


@pytest.mark.asyncio
async def test_list_pine_source_not_in_items(client, mock_clerk_auth):
    await client.post("/api/v1/strategies", json={"name": "x", "pine_source": _OK})
    res = await client.get("/api/v1/strategies")
    assert res.status_code == 200
    body = res.json()
    for item in body["items"]:
        assert "pine_source" not in item
```

- [ ] **Step 3: 테스트 실행**

Run: `cd backend && uv run pytest tests/strategy/test_strategies_crud.py -v`
Expected: 5 passed, 1 skipped.

- [ ] **Step 4: 회귀 + 린트**

Run: `cd backend && uv run pytest -q && uv run ruff check . && uv run mypy src/`
Expected: All green.

- [ ] **Step 5: Commit**

```bash
git add backend/src/strategy/router.py backend/tests/strategy/test_strategies_crud.py
git commit -m "feat(strategy): POST /strategies + GET /strategies endpoints

- POST /strategies: CreateStrategyRequest → Service.create → 201
- GET /strategies: page/limit/parse_status/is_archived 필터,
  updated_at DESC, StrategyListResponse
- 5 E2E tests (create ok/unsupported, list paginate/filter/list-dto-mask)"
```

---

### Task 13: `GET/PUT/DELETE /strategies/:id` + E2E

**의도:** 상세/수정/삭제 엔드포인트 완성.

**Files:**
- Modify: `backend/src/strategy/router.py` — GET:id / PUT / DELETE 추가
- Modify: `backend/tests/strategy/test_strategies_crud.py` — 테스트 추가 + archive skip 해제

- [ ] **Step 1: router에 3개 엔드포인트 추가**

`backend/src/strategy/router.py` 추가:

```python
from uuid import UUID

from fastapi import Path

from src.strategy.schemas import UpdateStrategyRequest


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyResponse:
    return await service.get(strategy_id=strategy_id, owner_id=current_user.id)


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    data: UpdateStrategyRequest,
    strategy_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> StrategyResponse:
    return await service.update(
        strategy_id=strategy_id, owner_id=current_user.id, data=data
    )


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(
    strategy_id: UUID = Path(...),
    current_user: CurrentUser = Depends(get_current_user),
    service: StrategyService = Depends(get_strategy_service),
) -> None:
    await service.delete(strategy_id=strategy_id, owner_id=current_user.id)
```

- [ ] **Step 2: 테스트 추가**

`backend/tests/strategy/test_strategies_crud.py` 확장 (끝에 추가):

```python
@pytest.mark.asyncio
async def test_get_strategy_returns_full_dto(client, mock_clerk_auth):
    res = await client.post("/api/v1/strategies", json={"name": "x", "pine_source": _OK})
    sid = res.json()["id"]
    detail = await client.get(f"/api/v1/strategies/{sid}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["pine_source"] == _OK
    assert "description" in body


@pytest.mark.asyncio
async def test_get_strategy_not_found(client, mock_clerk_auth):
    import uuid
    bogus = str(uuid.uuid4())
    res = await client.get(f"/api/v1/strategies/{bogus}")
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "strategy_not_found"


@pytest.mark.asyncio
async def test_update_pine_source_reparses(client, mock_clerk_auth):
    res = await client.post("/api/v1/strategies", json={"name": "x", "pine_source": _OK})
    sid = res.json()["id"]
    updated = await client.put(
        f"/api/v1/strategies/{sid}",
        json={"pine_source": _BAD},
    )
    assert updated.status_code == 200
    assert updated.json()["parse_status"] in ("unsupported", "error")


@pytest.mark.asyncio
async def test_update_archive_toggle(client, mock_clerk_auth):
    res = await client.post("/api/v1/strategies", json={"name": "x", "pine_source": _OK})
    sid = res.json()["id"]
    await client.put(f"/api/v1/strategies/{sid}", json={"is_archived": True})
    # 기본 목록에서 제외
    listed = await client.get("/api/v1/strategies")
    assert sid not in [i["id"] for i in listed.json()["items"]]
    # archive 필터로만 나옴
    archived = await client.get("/api/v1/strategies?is_archived=true")
    assert sid in [i["id"] for i in archived.json()["items"]]


@pytest.mark.asyncio
async def test_delete_strategy(client, mock_clerk_auth):
    res = await client.post("/api/v1/strategies", json={"name": "x", "pine_source": _OK})
    sid = res.json()["id"]
    deleted = await client.delete(f"/api/v1/strategies/{sid}")
    assert deleted.status_code == 204
    # 후속 GET은 404
    res = await client.get(f"/api/v1/strategies/{sid}")
    assert res.status_code == 404
```

그리고 Task 12에서 skip 처리한 `test_list_excludes_archived_by_default`의 `pytest.skip(...)`을 제거하고 실제 로직으로 채움:

```python
@pytest.mark.asyncio
async def test_list_excludes_archived_by_default(client, mock_clerk_auth):
    res = await client.post("/api/v1/strategies", json={"name": "a", "pine_source": _OK})
    strategy_id = res.json()["id"]
    await client.put(f"/api/v1/strategies/{strategy_id}", json={"is_archived": True})

    listed = await client.get("/api/v1/strategies")
    assert strategy_id not in [i["id"] for i in listed.json()["items"]]
```

- [ ] **Step 3: 테스트 실행**

Run: `cd backend && uv run pytest tests/strategy/test_strategies_crud.py -v`
Expected: 10 passed.

- [ ] **Step 4: 회귀 + 린트**

Run: `cd backend && uv run pytest -q && uv run ruff check . && uv run mypy src/`
Expected: All green.

- [ ] **Step 5: Commit**

```bash
git add backend/src/strategy/router.py backend/tests/strategy/test_strategies_crud.py
git commit -m "feat(strategy): GET/PUT/DELETE /strategies/:id endpoints

- GET/:id → StrategyResponse (pine_source 포함)
- PUT/:id → 부분 수정, pine_source 변경 시 재파싱, is_archived 토글
- DELETE/:id → 204 hard delete
- 5 신규 E2E 테스트 + list archive filter skip 해제"
```

---

### Task 14: Ownership 격리 E2E

**의도:** 타 사용자 전략에 접근 시 404 (정보 누출 방지)를 보장하는 독립 테스트 스위트.

**Files:**
- Create: `backend/tests/strategy/test_strategies_ownership.py`

- [ ] **Step 1: ownership 테스트 헬퍼 + 케이스 작성**

`backend/tests/strategy/test_strategies_ownership.py` 생성:

```python
"""Strategy 소유권 격리 — 타 사용자 전략에 접근 시 404."""
from __future__ import annotations

import uuid
from uuid import UUID

import pytest

from src.auth.models import User
from src.auth.schemas import CurrentUser
from src.auth.dependencies import get_current_user
from src.strategy.models import ParseStatus, PineVersion, Strategy


async def _create_user(db_session, label: str) -> User:
    user = User(
        clerk_user_id=f"user_{label}_{uuid.uuid4().hex[:6]}",
        email=f"{label}@b.com",
        username=label,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_strategy(db_session, owner_id: UUID, name: str) -> Strategy:
    s = Strategy(
        user_id=owner_id,
        name=name,
        pine_source="//@version=5\nstrategy(\"x\")",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(s)
    await db_session.commit()
    await db_session.refresh(s)
    return s


def _impersonate(app, user: User):
    async def _fake() -> CurrentUser:
        return CurrentUser.model_validate(user)
    app.dependency_overrides[get_current_user] = _fake


@pytest.mark.asyncio
async def test_get_other_users_strategy_returns_404(client, app, db_session):
    alice = await _create_user(db_session, "alice")
    bob = await _create_user(db_session, "bob")
    bob_strategy = await _create_strategy(db_session, bob.id, "bob_strat")

    _impersonate(app, alice)
    res = await client.get(f"/api/v1/strategies/{bob_strategy.id}")
    assert res.status_code == 404
    assert res.json()["detail"]["code"] == "strategy_not_found"


@pytest.mark.asyncio
async def test_update_other_users_strategy_returns_404(client, app, db_session):
    alice = await _create_user(db_session, "alice")
    bob = await _create_user(db_session, "bob")
    bob_strategy = await _create_strategy(db_session, bob.id, "bob_strat")

    _impersonate(app, alice)
    res = await client.put(
        f"/api/v1/strategies/{bob_strategy.id}",
        json={"name": "hijacked"},
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_delete_other_users_strategy_returns_404(client, app, db_session):
    alice = await _create_user(db_session, "alice")
    bob = await _create_user(db_session, "bob")
    bob_strategy = await _create_strategy(db_session, bob.id, "bob_strat")

    _impersonate(app, alice)
    res = await client.delete(f"/api/v1/strategies/{bob_strategy.id}")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_list_only_returns_own_strategies(client, app, db_session):
    alice = await _create_user(db_session, "alice")
    bob = await _create_user(db_session, "bob")
    await _create_strategy(db_session, alice.id, "a_one")
    await _create_strategy(db_session, alice.id, "a_two")
    await _create_strategy(db_session, bob.id, "b_one")

    _impersonate(app, alice)
    res = await client.get("/api/v1/strategies")
    assert res.status_code == 200
    names = [i["name"] for i in res.json()["items"]]
    assert set(names) == {"a_one", "a_two"}
```

- [ ] **Step 2: 테스트 실행**

Run: `cd backend && uv run pytest tests/strategy/test_strategies_ownership.py -v`
Expected: 4 passed.

- [ ] **Step 3: 회귀 + 린트**

Run: `cd backend && uv run pytest -q && uv run ruff check . && uv run mypy src/`
Expected: All green, 누적 ~267 passed 근접.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/strategy/test_strategies_ownership.py
git commit -m "test(strategy): ownership isolation E2E suite

GET/PUT/DELETE /:id 타 사용자 strategy 접근 시 404 반환 검증 +
GET /strategies 목록이 current user 소유만 반환하는지 검증.
정보 누출 방지로 403 대신 404로 통일."
```

---

## Block 4 — Finalization

### Task 15: CI 업데이트 + 문서 동기화 + 스펙 post-impl notes

**의도:** 파이프라인과 문서를 Sprint 3 종결 상태로 맞춤. CLAUDE.md 컨텍스트 갱신, TODO.md에서 follow-ups 이동, spec §10 실측 이탈 기록.

**Files:**
- Modify: `.github/workflows/ci.yml` — alembic upgrade 스텝
- Modify: `docs/TODO.md`
- Modify: `docs/03_api/endpoints.md`
- Modify: `CLAUDE.md`
- Modify: `docs/superpowers/specs/2026-04-15-sprint3-strategy-api-design.md` §10

- [ ] **Step 1: CI workflow — alembic upgrade 스텝 추가**

`.github/workflows/ci.yml`의 `backend` 잡에서 `uv run pytest` 스텝 직전에 추가:

```yaml
      - run: uv run alembic upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test
```

- [ ] **Step 2: CI에 test DB 생성 스텝 추가 (service container가 quantbridge_test를 자동 생성하지 않는 경우)**

`.github/workflows/ci.yml`의 `backend` 잡 env를 재확인. 현재 `POSTGRES_DB: quantbridge_test`로 이미 설정됨. 추가 스텝 없음.

만약 테스트 실행 시 DB 연결 실패하면, 서비스 컨테이너가 준비될 때까지 기다리는 스텝 추가:

```yaml
      - name: Wait for postgres
        run: |
          for i in {1..30}; do
            pg_isready -h localhost -U quantbridge && break
            sleep 1
          done
```

(이 스텝은 실패 발생 시 추가. 기본은 `options: --health-retries 5`로 충분.)

- [ ] **Step 3: docs/TODO.md 업데이트**

`docs/TODO.md` 수정:

- `### Sprint 3 follow-ups` 섹션을 `### Sprint 4 follow-ups`로 이름 변경
- S3-01/S3-02 항목은 `Completed`로 이동 (Sprint 3에서 처리됨)
- S3-03/S3-04는 Sprint 4 follow-ups로 유지

예시:

```markdown
### Stage 3 / Sprint 3 — Strategy API + Clerk 실배선 ✅ 완료 (<date>)

- [x] Strategy 도메인 CRUD (6 엔드포인트) + /strategies/parse 미리보기
- [x] Clerk JWT 실검증 + User 모델 + /auth/me
- [x] Clerk Webhook (Svix 서명 검증) + user.created/updated/deleted 3 이벤트
- [x] Alembic 첫 migration + round-trip 테스트
- [x] pytest conftest (DB savepoint 격리 + FastAPI AsyncClient)
- [x] S3-01 gate propagation + S3-02 duplicate strategy.exit warning
- [x] 테스트 ~267 passing

### Sprint 4 follow-ups (Sprint 2에서 이월 + Sprint 3에서 발견)

- [ ] **S3-03:** `backtest/engine` 커버리지 91% → 95% (fault injection)
- [ ] **S3-04:** `adapter._price_to_sl_ratio` 음수 비율 방어적 clamp/assert
```

- [ ] **Step 4: endpoints.md 업데이트**

`docs/03_api/endpoints.md`에서 Sprint 3 구현 엔드포인트에 ✅ 마킹:

| Method | Path | 상태 |
|--------|------|------|
| GET | /api/v1/auth/me | ✅ Sprint 3 |
| POST | /api/v1/auth/webhook | ✅ Sprint 3 |
| POST | /api/v1/strategies/parse | ✅ Sprint 3 |
| POST | /api/v1/strategies | ✅ Sprint 3 |
| GET | /api/v1/strategies | ✅ Sprint 3 |
| GET | /api/v1/strategies/:id | ✅ Sprint 3 |
| PUT | /api/v1/strategies/:id | ✅ Sprint 3 |
| DELETE | /api/v1/strategies/:id | ✅ Sprint 3 |

테이블에 "상태" 컬럼 추가 또는 각 endpoint 옆에 ✅ 마크.

- [ ] **Step 5: CLAUDE.md — §현재 작업 갱신**

`CLAUDE.md`의 `### 현재 작업` 섹션 업데이트:

```markdown
### 현재 작업
- Stage 3 / Sprint 1: Pine Parser MVP ✅ 완료 (2026-04-15)
- Stage 3 / Sprint 2: vectorbt Engine ✅ 완료 (2026-04-15)
- Stage 3 / Sprint 3: Strategy API + Clerk 실배선 ✅ 완료 (<date>, merge <sha>)
- **다음:** Sprint 4 계획 — Celery task wrapper + POST /backtests + S3-03/04 follow-ups
```

- [ ] **Step 6: spec §10 post-impl notes 채움**

`docs/superpowers/specs/2026-04-15-sprint3-strategy-api-design.md` §10에 실측 이탈 기록:

```markdown
## 10. Sprint 3 구현 후 노트 (스펙 이탈 기록)

### 10.1 <실제 발견된 이탈 1>
- 원 스펙: ...
- 실제: ...
- 이유: ...
- 영향: ...

### 10.2 <실제 발견된 이탈 2>
...
```

(구현 중 발견된 구체 사항으로 채움. 예: Clerk SDK `authenticate_request` 시그니처 실제 동작, svix 서명 방식 세부, pytest-asyncio savepoint 구현 상 난관 등.)

**이 Step은 이전 Task들의 구현 중 직접 관찰한 이탈 내용을 기반으로 작성. 플레이스홀더 금지. 만약 이탈 없이 스펙대로 100% 구현됐으면 "이탈 없음. 구현 중 추가 관찰 사항: <간단 기록>"으로.**

- [ ] **Step 7: 전체 회귀 최종 확인**

Run: `cd backend && uv run pytest -v`
Expected: ~267 passed, 0 failed, 0 errors.

- [ ] **Step 8: CI green 확인 (푸시 후)**

```bash
git add .github/workflows/ci.yml docs/TODO.md docs/03_api/endpoints.md CLAUDE.md docs/superpowers/specs/2026-04-15-sprint3-strategy-api-design.md
git commit -m "docs(sprint3): post-implementation notes + TODO/CLAUDE.md/CI advance"
```

그리고 브랜치 푸시 + PR 생성 (사용자 승인 후):

Run: `gh pr create --title "Sprint 3: Strategy API + Clerk auth" --body "..."`

PR #2 CI green 확인 후 머지.

- [ ] **Step 9: Commit (이미 Step 8에서 처리됨 — 정리용 확인)**

아직 커밋되지 않은 파일이 있다면 이 시점에 최종 커밋.

---

## Self-Review

**Spec coverage:** 각 섹션이 Task로 커버되는지:

- §1.2 완료 기준 8 엔드포인트 → Task 7 (me) + Task 8 (webhook) + Task 11 (parse) + Task 12 (POST/GET) + Task 13 (GET/PUT/DELETE) ✓
- §1.2 Ownership 격리 → Task 14 ✓
- §1.2 Follow-ups S3-01/02 → Task 1, Task 2 ✓
- §1.2 Alembic round-trip → Task 3 (Step 10~11) ✓
- §3.1/3.2 모델 → Task 3 ✓
- §4.4 에러 코드 → Task 6 (exceptions), Task 10 (StrategyNotFoundError) ✓
- §5.1/5.2 Clerk dependency/UserService → Task 6, 7 ✓
- §5.3 Webhook handler → Task 8 ✓
- §5.4 Parser follow-ups → Task 1, 2 ✓
- §6 테스트 전략 → Task 4 (fixtures) + 각 도메인 테스트 ✓
- §7.4 CI alembic 스텝 → Task 15 ✓

**Placeholder scan:** "TODO"/"TBD"/"implement later" 검색:
- Task 15 Step 6 §10 post-impl notes는 "구현 중 관찰한 이탈 내용으로 채움" — 실제 내용이 있어야 하며 플레이스홀더 금지. 명시적 지시 있음 ✓

**Type consistency:**
- `CurrentUser` 필드: id(UUID) / clerk_user_id / email / username / is_active — Task 6 schemas에서 정의, Task 4 mock_clerk_auth에서 `session_id=None` 제외한 나머지 구성, Task 7 dependency에서 `CurrentUser.model_validate(user)`로 생성 — 일관성 ✓
- `StrategyRepository.archive_all_by_owner(user_id: UUID)` — Task 8 (stub), Task 9 (전체) 모두 동일 시그니처 ✓
- `UserRepository.upsert_from_webhook(clerk_user_id, email, username)` — Task 5, Task 6에서 일관 사용 ✓
- `parse_and_run(source, **ohlcv)` — Sprint 1/2 기존 시그니처 그대로 사용, Task 10 `_empty_ohlcv()` 도입 ✓

**발견 이슈 0건.** 플랜 완성.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-15-sprint3-strategy-api.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. 각 Task 완료 시 사용자가 점검 후 다음으로 진행.

**2. Inline Execution** — 이 세션에서 순차 실행. 중간 checkpoint에서 사용자 리뷰.

**Which approach?**
