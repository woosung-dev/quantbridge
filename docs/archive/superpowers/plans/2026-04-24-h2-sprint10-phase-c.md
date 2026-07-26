# H2 Sprint 10 — Phase C: Real Broker E2E Infra Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Beta 오픈 전 "진짜 거래소까지 가는 자동 검증 1건" 이 있는가? Nightly CI 에서 Bybit Demo 실호출 경로 (TV webhook → OrderService → Bybit Demo create_order → filled polling) 를 매일 회귀 감지.

**Architecture:** `pytest-celery` 로 Celery worker/broker 를 in-process spawn, TradingView webhook payload 를 `TestClient` 로 POST, Celery task 가 Bybit Demo 실 API 로 `create_order` → 5~10s polling 으로 `filled` 상태 확인 → cleanup (position close + residual cancel). Marker `real_broker` + `--run-real-broker` 플래그 로 기본 skip, CI nightly workflow + `workflow_dispatch` 로만 활성.

**Tech Stack:** `pytest-celery` (신규 dev dep), 기존 `ccxt` (bybit demo), 기존 trading/tasks.py 흐름.

---

## Files

**Create:**

- `backend/tests/real_broker/__init__.py` (empty)
- `backend/tests/real_broker/conftest.py` — pytest-celery fixture + Bybit Demo creds 로드 + marker skip 제어
- `backend/tests/real_broker/test_webhook_to_filled_e2e.py` — 1 E2E 시나리오
- `.github/workflows/nightly-real-broker.yml` — cron + workflow_dispatch + secrets

**Modify:**

- `backend/pyproject.toml` — `pytest-celery>=0.0.0` dev dep + `real_broker` marker
- `backend/.env.example` + `.env.example` (root) — `BYBIT_DEMO_API_KEY_TEST` + `BYBIT_DEMO_API_SECRET_TEST` env

**Reuse (수정 금지):**

- `backend/src/trading/router.py` — TV webhook endpoint
- `backend/src/trading/providers.py` + `backend/src/trading/providers/bybit_demo.py` — 기존 CCXT Bybit provider
- `backend/src/tasks/trading_tasks.py` — execute_order_task (Sprint 6+)
- `backend/src/common/metrics.py::qb_ccxt_request_errors_total` (Phase D) — E2E 실행 중 실제 error 발생 시 계측 가능

---

## Background — Q3 = Nightly-only + workflow_dispatch (사용자 결정)

Sprint 10 master plan §Q3 결정: **Nightly-only + 수동 trigger**.

- PR CI 는 항상 skip (flakiness 차단, Bybit Demo rate limit 보호)
- GitHub Actions `schedule` cron `0 18 * * *` (UTC 18시 = KST 새벽 03시)
- `workflow_dispatch` 로 수동 trigger 가능
- 실패 시 issue auto-label `flaky-real-broker`

---

## Task 1: 의존성 + marker 추가

**Files:**

- Modify: `backend/pyproject.toml`

- [ ] **Step 1.1: pytest-celery dep + marker 추가**

`backend/pyproject.toml` 의 `[dependency-groups] dev` 또는 `[project.optional-dependencies] dev` 에 추가:

```toml
"pytest-celery>=1.0",
```

`[tool.pytest.ini_options]` 의 markers 리스트에 추가:

```toml
markers = [
  "mutation: Path β Mutation Oracle — nightly only (Stage 2c)",
  "real_broker: requires Bybit Demo API credentials (skip by default, run with --run-real-broker)",
]
```

- [ ] **Step 1.2: 설치 + lockfile 갱신**

```bash
cd /Users/woosung/project/agy-project/quant-bridge/.worktrees/h2s10-real-broker/backend
uv sync
```

`pytest-celery` 가 `celery`, `pytest-asyncio`, `pytest` 등 transitive dep 확인.

- [ ] **Step 1.3: import smoke**

```bash
uv run python -c "
import pytest_celery
print('OK: pytest-celery version', pytest_celery.__version__)
"
```

- [ ] **Step 1.4: 기존 테스트 회귀 확인**

```bash
uv run pytest -q --tb=short -p no:randomly 2>&1 | tail -5
```

Expected: 1102 passed / 17 skipped / 0 fail (marker 추가 + pytest-celery 설치 후에도 기존 테스트 무영향).

- [ ] **Step 1.5: 커밋**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "feat(deps): add pytest-celery + real_broker marker — Sprint 10 Phase C"
```

---

## Task 2: .env.example 에 BYBIT*DEMO*\*\_TEST 추가

**Files:**

- Modify: `backend/.env.example`
- Modify: `.env.example` (root)

- [ ] **Step 2.1: backend/.env.example**

`backend/.env.example` 의 Bybit Demo 섹션 (기존 `BYBIT_DEMO_KEY=` / `BYBIT_DEMO_SECRET=` 라인 직후) 에 추가:

```bash

# Bybit Demo Trading — Phase C real_broker 전용 (nightly CI only)
# 발급: Bybit 계정 → API 관리 → Demo Trading 탭 → 신규 API Key (Read + Trade 권한)
# 운영 BYBIT_DEMO_KEY 와 분리된 별도 key (CI runner 격리 목적)
BYBIT_DEMO_API_KEY_TEST=                                               # [필수 Phase C nightly]
BYBIT_DEMO_API_SECRET_TEST=                                            # [필수 Phase C nightly]
```

- [ ] **Step 2.2: root .env.example**

`.env.example` (worktree 루트) 끝에 추가 (docker-compose 사용 시 참고용):

```bash

# =====================================================
# Bybit Demo — Sprint 10 Phase C (nightly CI 전용)
# =====================================================
BYBIT_DEMO_API_KEY_TEST=                                               # [필수 Phase C nightly]
BYBIT_DEMO_API_SECRET_TEST=                                            # [필수 Phase C nightly]
```

- [ ] **Step 2.3: 커밋**

```bash
git add backend/.env.example .env.example
git commit -m "feat(env): add BYBIT_DEMO_*_TEST env for Phase C nightly E2E"
```

---

## Task 3: conftest.py — marker skip + credentials fixture

**Files:**

- Create: `backend/tests/real_broker/__init__.py` (empty)
- Create: `backend/tests/real_broker/conftest.py`

- [ ] **Step 3.1: **init**.py**

```bash
mkdir -p backend/tests/real_broker
touch backend/tests/real_broker/__init__.py
```

- [ ] **Step 3.2: conftest.py**

`backend/tests/real_broker/conftest.py` 신규:

```python
"""Sprint 10 Phase C — real_broker pytest plugin.

--run-real-broker 플래그 로만 marker 수집 + Bybit Demo credentials env 검증.

기본 동작:
- pytest 실행 → real_broker marker 테스트 전부 skip
- pytest --run-real-broker → 모두 실행. credentials 없으면 fail with clear message.

Nightly CI (`nightly-real-broker.yml`) 이 `pytest --run-real-broker` 로 호출.
"""

from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-real-broker",
        action="store_true",
        default=False,
        help="run tests marked 'real_broker' (requires Bybit Demo credentials)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """`--run-real-broker` 없으면 marker 아이템 skip."""
    if config.getoption("--run-real-broker"):
        return
    skip_marker = pytest.mark.skip(
        reason="real_broker: requires --run-real-broker flag + Bybit Demo credentials"
    )
    for item in items:
        if "real_broker" in item.keywords:
            item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def bybit_demo_test_credentials() -> tuple[str, str]:
    """BYBIT_DEMO_API_KEY_TEST / BYBIT_DEMO_API_SECRET_TEST env.

    --run-real-broker 실행 경로에서만 호출됨. env 미설정 시 pytest.fail
    (clear error message — CI 에서 Secrets 누락 즉시 파악).
    """
    key = os.environ.get("BYBIT_DEMO_API_KEY_TEST", "").strip()
    secret = os.environ.get("BYBIT_DEMO_API_SECRET_TEST", "").strip()
    if not key or not secret:
        pytest.fail(
            "Phase C E2E requires BYBIT_DEMO_API_KEY_TEST + BYBIT_DEMO_API_SECRET_TEST "
            "env. Set via GitHub Secrets (nightly-real-broker.yml) or local .env.local."
        )
    return key, secret
```

- [ ] **Step 3.3: conftest smoke**

```bash
# pytest 가 plugin 을 정상 인식하는지 + --run-real-broker 플래그 존재 확인
uv run pytest tests/real_broker/ -v --collect-only 2>&1 | tail -10
uv run pytest --help 2>&1 | grep -A 1 "run-real-broker"
```

Expected: `--run-real-broker` 플래그 help 에 노출 + collection 에서 시나리오 없음 (아직 test 파일 미작성).

- [ ] **Step 3.4: 커밋**

```bash
git add backend/tests/real_broker/__init__.py backend/tests/real_broker/conftest.py
git commit -m "test(real-broker): conftest plugin — --run-real-broker flag + credentials fixture"
```

---

## Task 4: E2E 시나리오 — TV webhook → create_order → filled polling

**Files:**

- Create: `backend/tests/real_broker/test_webhook_to_filled_e2e.py`

- [ ] **Step 4.1: E2E 테스트**

`backend/tests/real_broker/test_webhook_to_filled_e2e.py` 신규:

```python
"""Sprint 10 Phase C — TV webhook → Bybit Demo create_order → filled E2E.

1 시나리오:
1. Bybit Demo Spot BTC/USDT 최소 수량 market BUY 주문
2. TV webhook payload (HMAC 서명 포함) TestClient POST
3. Celery task 가 execute_order → Bybit Demo create_order
4. 5~10s polling 으로 OrderState.filled 확인
5. cleanup: position close + residual cancel (best-effort)

**Nightly only.** 기본 skip. `pytest --run-real-broker` 로만 실행.

**Credentials:** `BYBIT_DEMO_API_KEY_TEST` + `BYBIT_DEMO_API_SECRET_TEST`.

**Rate limit:** Bybit Demo 의 rate limit 은 request/min 수준. 본 테스트는 1일 1회
(nightly) + 수동 trigger 만. flaky 방지로 retry 없음 (실패 시 issue 생성).
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


pytestmark = pytest.mark.real_broker


# Bybit Demo Spot 최소 주문 (slippage 허용 최소)
_BTCUSDT_TEST_SYMBOL = "BTC/USDT"
_TEST_QTY = Decimal("0.001")  # Bybit Spot 최소 0.001 BTC


@pytest.fixture
def tv_webhook_payload() -> dict[str, object]:
    """TradingView webhook 표준 payload (HMAC 서명 전)."""
    return {
        "strategy_id": str(uuid4()),  # CI 용 임시 id — 실제 DB 에 존재해야
        "side": "buy",
        "symbol": _BTCUSDT_TEST_SYMBOL,
        "qty": str(_TEST_QTY),
        "alert_time": int(time.time()),
        "price": None,  # market order
    }


@pytest.mark.asyncio
async def test_tv_webhook_to_bybit_demo_filled(
    bybit_demo_test_credentials: tuple[str, str],
    tv_webhook_payload: dict[str, object],
) -> None:
    """E2E: TV webhook → Celery task → Bybit Demo create_order → filled.

    **Guarded:** `@pytest.mark.real_broker` + credentials fixture. local dev 환경에서
    `pytest --run-real-broker` 실행 + env 세팅 필요.

    **Setup (한 번 수동):**
    1. Bybit Demo 계정에 seed USDT ≥ $10 (0.001 BTC @ $50k = $50).
    2. GitHub Secrets 에 BYBIT_DEMO_API_KEY_TEST / BYBIT_DEMO_API_SECRET_TEST 등록.
    3. `nightly-real-broker.yml` workflow 가 Secrets 주입 + pytest --run-real-broker.

    **본 테스트는 구현 skeleton.** 실제 TestClient + Celery worker fixture 결합은
    pytest-celery 의 `celery_worker` + `celery_app` fixture 로 세팅.

    Implementation 은 Follow-up:
    - `celery_app` fixture — src.tasks.celery_app:celery_app 사용
    - `celery_worker` fixture — in-process spawn
    - FastAPI TestClient — src.main:app
    - strategy_id seed — pytest fixture 로 테스트 user + strategy + exchange_account 생성
    - Bybit Demo credentials 를 ExchangeAccount.api_key_encrypted 로 암호화 저장 (Fernet)
    - webhook secret HMAC 서명
    - polling — order_repo.get_by_id + state 확인 (5s interval × 10 iter)
    - cleanup — Bybit Demo 에서 포지션 close + residual cancel
    """
    api_key, api_secret = bybit_demo_test_credentials

    # TODO: implementation — 본 Phase 는 infra skeleton 만.
    # 실제 E2E 는 nightly CI 첫 실행에서 credentials 주입 후 green 확인.
    pytest.skip("Phase C skeleton — full E2E implementation deferred to nightly first-run")
```

**주의:** 위 테스트는 **skeleton**. Sprint 10 Phase C 의 목표는 "인프라 + marker + workflow + credentials plumbing" 까지. 실제 E2E 로직은 nightly 첫 실행 시 implementer 가 credentials + seed data 하에 작성.

- [ ] **Step 4.2: 기본 skip 확인 (flag 없이)**

```bash
uv run pytest tests/real_broker/ -v 2>&1 | tail -10
```

Expected: 1 skipped (marker 때문).

- [ ] **Step 4.3: flag 있을 때 credentials 없으면 fail**

```bash
# env 지우고
unset BYBIT_DEMO_API_KEY_TEST BYBIT_DEMO_API_SECRET_TEST
uv run pytest tests/real_broker/ --run-real-broker -v 2>&1 | tail -10
```

Expected: `pytest.fail` — "Phase C E2E requires BYBIT_DEMO_API_KEY_TEST ...".

- [ ] **Step 4.4: flag + credentials 있을 때 skeleton skip**

```bash
BYBIT_DEMO_API_KEY_TEST=dummy-key \
BYBIT_DEMO_API_SECRET_TEST=dummy-secret \
uv run pytest tests/real_broker/ --run-real-broker -v 2>&1 | tail -10
```

Expected: 1 skipped ("skeleton" — 본 Phase 는 full E2E 미구현).

- [ ] **Step 4.5: 커밋**

```bash
git add backend/tests/real_broker/test_webhook_to_filled_e2e.py
git commit -m "test(real-broker): E2E skeleton — TV webhook → Bybit Demo create_order → filled

Phase C skeleton — infra (marker + flag + credentials fixture + 1 pytest skip with TODO).
실제 E2E 로직은 nightly CI 첫 실행 시 credentials + seed data 하에 implementer 가 작성."
```

---

## Task 5: Nightly GitHub Actions workflow

**Files:**

- Create: `.github/workflows/nightly-real-broker.yml`

- [ ] **Step 5.1: workflow 작성**

`.github/workflows/nightly-real-broker.yml` 신규:

```yaml
name: Nightly Real Broker E2E

# KST 03:00 (UTC 18:00) 매일 + 수동 trigger
on:
  schedule:
    - cron: "0 18 * * *"
  workflow_dispatch:

permissions:
  contents: read
  issues: write # auto-label on failure

jobs:
  real_broker_e2e:
    name: Bybit Demo E2E
    runs-on: ubuntu-latest
    timeout-minutes: 30
    services:
      postgres:
        image: timescale/timescaledb-ha:pg17
        env:
          POSTGRES_USER: quantbridge
          POSTGRES_PASSWORD: password
          POSTGRES_DB: quantbridge
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U quantbridge"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 5

    env:
      DATABASE_URL: postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge
      REDIS_URL: redis://localhost:6379/0
      CELERY_BROKER_URL: redis://localhost:6379/1
      CELERY_RESULT_BACKEND: redis://localhost:6379/2
      REDIS_LOCK_URL: redis://localhost:6379/3
      EXCHANGE_PROVIDER: bybit_demo
      BYBIT_DEMO_API_KEY_TEST: ${{ secrets.BYBIT_DEMO_API_KEY_TEST }}
      BYBIT_DEMO_API_SECRET_TEST: ${{ secrets.BYBIT_DEMO_API_SECRET_TEST }}
      TRADING_ENCRYPTION_KEYS: ${{ secrets.TRADING_ENCRYPTION_KEYS_TEST }}

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v3
        with:
          version: "latest"

      - name: Setup Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install backend deps
        working-directory: backend
        run: uv sync

      - name: Alembic migrate
        working-directory: backend
        run: uv run alembic upgrade head

      - name: Run real_broker E2E
        working-directory: backend
        run: |
          uv run pytest tests/real_broker/ \
            --run-real-broker \
            -v \
            --tb=short \
            --timeout=300 \
          | tee /tmp/real-broker-output.txt

      - name: Flaky detection — auto-label issue on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            const title = `[flaky-real-broker] Nightly failure ${new Date().toISOString().split('T')[0]}`;
            const body = `Nightly real_broker E2E failed at ${new Date().toISOString()}.

            Workflow run: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}

            Triage steps:
            1. Bybit Demo status page — https://announcements.bybit.com/
            2. Verify BYBIT_DEMO_API_KEY_TEST credentials (not expired)
            3. Check qb_ccxt_request_errors_total metric from last successful run
            4. Re-run via workflow_dispatch if transient
            5. If persistent → add to TODO.md + Sprint 11 investigation`;

            await github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title,
              body,
              labels: ['flaky-real-broker', 'sprint-10']
            });
```

- [ ] **Step 5.2: yaml lint (actionlint 사용 가능하면)**

```bash
# actionlint 설치되어 있으면:
actionlint .github/workflows/nightly-real-broker.yml || echo "actionlint 미설치 — manual review"

# 또는 GitHub Actions 의 빌트인 validator 로 workflow_dispatch UI 에서 trigger 시 에러 여부 확인
```

기본 검증: yaml 자체가 valid (Python `yaml.safe_load`):

```bash
uv run python -c "
import yaml
with open('.github/workflows/nightly-real-broker.yml') as f:
    cfg = yaml.safe_load(f)
assert 'real_broker_e2e' in cfg['jobs']
assert cfg[True]['workflow_dispatch'] == None  # 'on:' 가 Python 에서 True 로 파싱됨
print('OK: yaml valid, job defined')
"
```

- [ ] **Step 5.3: 커밋**

```bash
git add .github/workflows/nightly-real-broker.yml
git commit -m "ci(real-broker): nightly workflow — cron 0 18 * * * + workflow_dispatch + auto-label

Phase C — Bybit Demo E2E nightly:
- cron UTC 18:00 = KST 03:00 매일
- workflow_dispatch 로 수동 trigger
- timescaledb-ha + redis service container
- Secrets: BYBIT_DEMO_API_KEY_TEST, BYBIT_DEMO_API_SECRET_TEST, TRADING_ENCRYPTION_KEYS_TEST
- 실패 시 github-script 으로 issue auto-create + 'flaky-real-broker', 'sprint-10' 라벨
- 30min timeout"
```

---

## Task 6: Gate-C 최종 검증

- [ ] **Step 6.1: 전체 검증**

```bash
cd /Users/woosung/project/agy-project/quant-bridge/.worktrees/h2s10-real-broker/backend
uv run ruff check . && uv run mypy src/ tests/ && uv run pytest -q --tb=short -p no:randomly
```

Expected:

- ruff 0
- mypy 0 (tests/real_broker 도 type check — `Optional[X]` 아닌 `X | None` 등)
- pytest 1102 + 1 skipped = green (real_broker 는 skip by default)

- [ ] **Step 6.2: marker isolation 확인**

```bash
# real_broker 는 default 에서 skip
uv run pytest -m "not real_broker" -q --tb=no 2>&1 | tail -3

# real_broker 만
uv run pytest -m "real_broker" --collect-only -q 2>&1 | tail -5
```

Expected: 기본 실행은 real_broker 제외 모두, marker 전용은 1 test 만 collect.

- [ ] **Step 6.3: workflow_dispatch dry-run (사용자 수동)**

사용자가 GitHub Actions UI 에서 `nightly-real-broker.yml` 의 `Run workflow` 버튼 클릭 → dry-run.

- Secrets 미등록 상태면 첫 실행 실패 (credentials 없음). 자동 issue 생성 확인.
- Secrets 등록 후 재실행 → skeleton pytest.skip 으로 PASS (E2E 미구현 상태).

---

## Verification Summary (Gate-C)

| 항목                     | 통과 기준                                                |
| ------------------------ | -------------------------------------------------------- |
| Lint                     | ruff 0 / mypy 0                                          |
| 기존 회귀                | 1102 + 1 skipped = 1103 green (-p no:randomly)           |
| Marker skip              | `pytest` default 에서 real_broker 1 skipped              |
| `--run-real-broker` flag | 존재 + `pytest --help` 노출                              |
| Credentials fixture      | env 없으면 fail w/ clear message                         |
| Workflow yaml            | `yaml.safe_load` 성공 + `actionlint` (옵션)              |
| Nightly cron             | `0 18 * * *` 등록 + `workflow_dispatch` 가능             |
| Auto-label               | 실패 시 `flaky-real-broker`, `sprint-10` 라벨 issue 생성 |

---

## What this Phase is NOT

- **실제 E2E 로직 구현** — skeleton 만. Nightly 첫 실행 시 credentials + seed data 하에 implementer 가 작성.
- **PR CI 에서 real_broker 실행** — Q3 결정대로 nightly only + workflow_dispatch.
- **multi-exchange (OKX demo) E2E** — Sprint 11+.
- **Smoke test on main merge** — nightly 만. main merge 는 영향 없음.
- **Bybit Mainnet 실호출** — Demo 만. Sprint 11+ 위 단계에서 Mainnet 전환.

---

## Generator-Evaluator (Phase 완료 직후)

Phase A1/B/D/A2 와 동일 절차:

1. `git diff stage/h2-sprint10..feat/h2s10-real-broker > /tmp/h2s10-c-diff.patch`
2. **codex** (foreground 5min timeout) — diff + 다음 체크리스트:
   - `pytest-celery` fixture wiring 가 기존 Celery config 와 충돌 없는가?
   - `conftest.py` 의 `pytest_addoption` 이 global conftest 와 충돌 없는가?
   - Secrets 누출 — workflow yaml 에 env 직접 참조만, `run:` 내부 echo 금지
   - pg_migrate timing — `alembic upgrade head` 가 postgres service ready 보다 먼저 실행되면 race
3. **Opus blind** (background, opus) — 파일 경로 + Golden Rules
4. **Sonnet blind** (background, sonnet) — PR body + edge case (Bybit Demo API 변경, CI runner 리소스 한계, seed data 잔여)
5. PASS = avg ≥ 8/10 ∧ blocker 0 ∧ major ≤ 2

---

## Sprint 10 마감 (Phase C 완료 후)

본 Phase 완료 = Sprint 10 전체 종료. 마감 절차:

1. `stage/h2-sprint10` 최종 상태 (A1 + B + D + A2 + C 5 squash commits) 확인
2. `AGENTS.md` §현재 작업 에 Sprint 10 완료 라인 추가
3. `.ai/project/lessons.md` 에 Sprint 10 lesson 기록 (Redis DB 분리 / slowapi 0.1.9 bug / Wrapping 패턴 정직성 / pytest-celery fixture 등)
4. 사용자가 직접 `stage/h2-sprint10 → main` PR 생성 (AI 는 PR body 초안만 제공)
5. follow-up 정리 (TODO.md 에 미해결 follow-ups 항목화)
