# H2 Sprint 9 · Phase D — 관측성 Phase 1 (Prometheus metrics + /metrics + Grafana runbook)

**Branch:** `feat/h2s9-observability` (from `stage/h2-sprint9` which includes Phase A + B)
**Date:** 2026-04-24
**Master plan:** `/Users/woosung/.claude/plans/h2-sprint-9-validated-ember.md` §Phase D
**Worktree isolation:** YES
**Depends on:** Phase B merged (backtest/trading 서비스 instrumentation 지점)

## Scope (고정)

1. **Prometheus metric 5종 실측** (`backend/src/common/metrics.py`)
2. **`GET /metrics` endpoint** — prometheus_client text exposition format, Clerk 인증 제외, bearer-token 으로 보호.
3. **Instrumentation 5 지점** — backtest task 실행 시간, 주문 거부, Kill Switch 발동, CCXT latency, active orders.
4. **`.env.example` 에 `PROMETHEUS_BEARER_TOKEN`** 추가.
5. **Grafana Cloud Free 설정 runbook** — `docs/07_infra/grafana-cloud-setup.md` (사용자 수동 Grafana 계정 설정 가이드).

## Out of scope

- Grafana 대시보드 JSON 배포 (runbook 에 참고용 쿼리만)
- Alertmanager 직접 구성 (Grafana Cloud agent 가 처리)
- OpenTelemetry tracing (Sprint 11+)
- Frontend metrics (Phase C 밖)

## 참조 파일 (사전 read 필수)

- `backend/pyproject.toml` — dependencies 섹션 (prometheus-client 추가)
- `backend/src/main.py` — FastAPI app 인스턴스, 기존 router include 패턴
- `backend/src/tasks/backtest.py` (혹은 `backend/src/tasks/celery_app.py`) — backtest task 실행 지점
- `backend/src/trading/service.py::OrderService` — 주문 거부 raise 경로 (e.g., `LeverageCapExceeded`, `NotionalExceeded`, `TradingSessionClosed`, `IdempotencyConflict`)
- `backend/src/trading/kill_switch.py::KillSwitchService` — trigger 지점
- `backend/src/trading/providers.py::BybitFuturesProvider` (+ OkxDemoProvider) — CCXT 호출 경로
- `backend/src/core/config.py` — env settings pydantic_settings 패턴
- `backend/.env.example` — 마지막 줄 참고

## 1. Dependency 추가

`backend/pyproject.toml`:

```toml
dependencies = [
    # ... 기존 ...
    "prometheus-client>=0.21.0",
]
```

`uv lock` 후 `uv.lock` 커밋.

## 2. `backend/src/common/metrics.py` (신규)

```python
"""Prometheus metrics — 5종. Sprint 9-4 (Phase D).

원칙:
- registry 는 기본 `REGISTRY` 사용 (multi-process 는 Sprint 10 에서 고려)
- label cardinality 낮게 유지 (exchange 는 enum 2개 예정)
- 민감 정보 label 금지 (user_id, strategy_id, api_key)
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# 1. Backtest 실행 시간 (queued → completed/failed)
qb_backtest_duration_seconds = Histogram(
    "qb_backtest_duration_seconds",
    "Backtest worker execution time from queued to terminal state",
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, float("inf")),
)

# 2. 주문 거부 카운터
qb_order_rejected_total = Counter(
    "qb_order_rejected_total",
    "Orders rejected before or at exchange",
    labelnames=("exchange", "reason"),
)

# 3. Kill Switch 발동
qb_kill_switch_triggered_total = Counter(
    "qb_kill_switch_triggered_total",
    "Kill Switch activations",
    labelnames=("trigger_type",),
)

# 4. CCXT exchange API latency
qb_ccxt_request_duration_seconds = Histogram(
    "qb_ccxt_request_duration_seconds",
    "CCXT exchange API request latency",
    labelnames=("exchange", "endpoint"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, float("inf")),
)

# 5. Active orders (pending + submitted)
qb_active_orders = Gauge(
    "qb_active_orders",
    "Current pending + submitted order count (eventually consistent)",
)
```

## 3. `GET /metrics` endpoint — `backend/src/main.py`

```python
from fastapi import Depends, HTTPException, Header, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.core.config import settings

def _verify_prometheus_bearer(
    authorization: str | None = Header(default=None),
) -> None:
    """Prometheus 스크래퍼 용 bearer token 검증.

    Grafana Cloud Agent 에서 설정한 토큰과 일치해야 허용.
    """
    expected = settings.prometheus_bearer_token.get_secret_value() if settings.prometheus_bearer_token else None
    if not expected:
        return  # 토큰 미설정 시 allow — dev/local 용
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bearer token required")
    token = authorization.removeprefix("Bearer ").strip()
    if token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid bearer token")


@app.get("/metrics", include_in_schema=False, dependencies=[Depends(_verify_prometheus_bearer)])
async def metrics_endpoint() -> Response:
    """Prometheus text exposition format. Clerk 인증 제외, bearer 로 보호."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

**주의:** `_verify_prometheus_bearer` 는 기본 app 의 Clerk JWT dependency 와 충돌하지 않도록 `include_in_schema=False` + 별도 Depends 처리. 기존 `proxy.ts` / Clerk middleware 와 무관 (백엔드 endpoint).

## 4. `backend/src/core/config.py` 확장

```python
from pydantic import SecretStr

class Settings(BaseSettings):
    # ... 기존 ...
    prometheus_bearer_token: SecretStr | None = Field(default=None)
```

## 5. `.env.example` 확장

```
# Prometheus 스크래퍼 bearer token (Grafana Cloud Agent 에서 동일 값 사용)
# 비어 있으면 /metrics 는 인증 없이 접근 가능 (로컬 개발용)
PROMETHEUS_BEARER_TOKEN=
```

## 6. Instrumentation 5 지점

### 6-A. `qb_backtest_duration_seconds` — backtest task

**위치:** `backend/src/tasks/backtest.py` (혹은 `backend/src/tasks/celery_app.py` 내 backtest task 함수) — `run_backtest_task` 진입점과 종료 지점.

```python
import time
from src.common.metrics import qb_backtest_duration_seconds

@celery_app.task(name="backtest.run", bind=True)
def run_backtest_task(self, backtest_id: str) -> None:
    started = time.monotonic()
    try:
        asyncio.run(_run_backtest_async(UUID(backtest_id)))
    finally:
        qb_backtest_duration_seconds.observe(time.monotonic() - started)
```

### 6-B. `qb_order_rejected_total` — 주문 거부 경로

**위치:** `backend/src/trading/service.py::OrderService.execute` — 각 예외 raise 직전에 카운터 증분.

```python
from src.common.metrics import qb_order_rejected_total

# e.g. LeverageCapExceeded raise 직전
qb_order_rejected_total.labels(exchange=exchange_name, reason="leverage_cap").inc()
raise LeverageCapExceeded(...)

# NotionalExceeded
qb_order_rejected_total.labels(exchange=exchange_name, reason="notional").inc()
raise NotionalExceeded(...)

# TradingSessionClosed
qb_order_rejected_total.labels(exchange=exchange_name, reason="session_closed").inc()
raise TradingSessionClosed(...)

# Idempotency conflict (trading)
qb_order_rejected_total.labels(exchange=exchange_name, reason="idempotency_conflict").inc()
raise IdempotencyConflict(...)

# Kill switch gate
qb_order_rejected_total.labels(exchange=exchange_name, reason="kill_switch").inc()
raise KillSwitchGated(...)
```

**`exchange_name`** 은 `req.exchange_account` 조회 후 상수화. service 레이어에서 직접 조회 어려우면 "unknown" 기본값.

### 6-C. `qb_kill_switch_triggered_total` — Kill Switch 발동

**위치:** `backend/src/trading/kill_switch.py::KillSwitchService.trigger` (혹은 유사 메서드).

```python
from src.common.metrics import qb_kill_switch_triggered_total

async def trigger(self, *, trigger_type: str, ...):
    qb_kill_switch_triggered_total.labels(trigger_type=trigger_type).inc()
    # ... 기존 로직 ...
```

### 6-D. `qb_ccxt_request_duration_seconds` — CCXT 호출 래퍼

**위치:** `backend/src/trading/providers.py` — Bybit/OKX provider 의 주요 메서드 (`create_order`, `fetch_balance`, `fetch_positions` 등) 를 timer 로 감싼다.

**데코레이터 또는 context manager 패턴:**

```python
import time
from contextlib import asynccontextmanager
from src.common.metrics import qb_ccxt_request_duration_seconds

@asynccontextmanager
async def ccxt_timer(exchange: str, endpoint: str):
    started = time.monotonic()
    try:
        yield
    finally:
        qb_ccxt_request_duration_seconds.labels(
            exchange=exchange, endpoint=endpoint
        ).observe(time.monotonic() - started)

# provider 메서드:
async def create_order(self, ...):
    async with ccxt_timer(self._exchange_name, "create_order"):
        return await self._exchange.create_order(...)
```

### 6-E. `qb_active_orders` — 활성 주문 gauge

**위치:** `backend/src/trading/service.py::OrderService` — 주문 상태 전이 지점.

```python
from src.common.metrics import qb_active_orders

# INSERT 직후 (pending state)
qb_active_orders.inc()

# 터미널 상태 전이 후 (filled, rejected, canceled)
qb_active_orders.dec()
```

**가장 안전한 방식:** 상태 전이 함수 (`transition_to_submitted`, `mark_filled`, `mark_rejected` 등) 를 찾아 각 전이 직후에 inc/dec. Gauge 는 lazy 복구 가능 (`.set()` 사용 가능).

## 7. Tests (`backend/tests/common/` + `backend/tests/trading/`)

### `backend/tests/common/test_metrics_endpoint.py`

```python
from fastapi.testclient import TestClient
from src.main import app

def test_metrics_endpoint_returns_prometheus_format():
    client = TestClient(app)
    response = client.get("/metrics")
    # bearer token 미설정 시 통과
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    # 5 metric prefix 모두 존재
    assert "qb_backtest_duration_seconds" in body
    assert "qb_order_rejected_total" in body
    assert "qb_kill_switch_triggered_total" in body
    assert "qb_ccxt_request_duration_seconds" in body
    assert "qb_active_orders" in body


def test_metrics_endpoint_rejects_invalid_bearer(monkeypatch):
    monkeypatch.setenv("PROMETHEUS_BEARER_TOKEN", "secret-token")
    from src.core.config import settings as s
    s.prometheus_bearer_token = SecretStr("secret-token")
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 401
    r2 = client.get("/metrics", headers={"Authorization": "Bearer wrong"})
    assert r2.status_code == 403
    r3 = client.get("/metrics", headers={"Authorization": "Bearer secret-token"})
    assert r3.status_code == 200
```

### `backend/tests/common/test_metrics_instrumentation.py`

```python
from src.common.metrics import (
    qb_backtest_duration_seconds,
    qb_kill_switch_triggered_total,
    qb_order_rejected_total,
)


def test_kill_switch_counter_increments():
    before = qb_kill_switch_triggered_total.labels(trigger_type="test")._value.get()
    qb_kill_switch_triggered_total.labels(trigger_type="test").inc()
    after = qb_kill_switch_triggered_total.labels(trigger_type="test")._value.get()
    assert after == before + 1


def test_order_rejected_counter_labels():
    qb_order_rejected_total.labels(exchange="bybit", reason="leverage_cap").inc()
    # label 조합으로 분리되는지 확인
    val = qb_order_rejected_total.labels(exchange="bybit", reason="leverage_cap")._value.get()
    assert val >= 1


def test_backtest_duration_histogram():
    qb_backtest_duration_seconds.observe(42.0)
    # bucket 증가 확인
    # (prometheus_client 의 _sum 값을 체크하는 게 덜 fragile)
    assert qb_backtest_duration_seconds._sum.get() >= 42.0
```

### `backend/tests/trading/test_order_rejected_metric.py`

기존 `OrderService` raise 테스트 중 1개를 복제해 `qb_order_rejected_total` 값이 증가하는지 확인.

```python
async def test_leverage_cap_exceeded_increments_metric(
    order_service_with_max_leverage_5, order_request_leverage_10
):
    from src.common.metrics import qb_order_rejected_total
    before = qb_order_rejected_total.labels(exchange="bybit", reason="leverage_cap")._value.get()
    with pytest.raises(LeverageCapExceeded):
        await order_service_with_max_leverage_5.execute(order_request_leverage_10, idempotency_key=None)
    after = qb_order_rejected_total.labels(exchange="bybit", reason="leverage_cap")._value.get()
    assert after == before + 1
```

## 8. Runbook — `docs/07_infra/grafana-cloud-setup.md`

사용자 수동 설정 가이드 (문서화 only, 코드 변경 없음):

````markdown
# Grafana Cloud Free 설정 Runbook

## 목표

QuantBridge 백엔드의 Prometheus metrics 를 Grafana Cloud Free 로 수집, 대시보드 + alert 1개 구성.

## Grafana Cloud Free 한도 (2026 기준)

- 10k active metrics (ingestion)
- 50 GB logs / 50 GB traces
- 3 users · 14일 metrics retention

## 단계

### 1. 계정 생성

1. https://grafana.com/products/cloud/ 접속, "Start for free"
2. 조직 이름 임의 설정, region `US Central` 권장 (latency)

### 2. Stack 생성

1. Dashboard → "Send metrics" → "Prometheus" 선택
2. Agent 없이 remote_write 만 사용할 것 (Kubernetes 환경 아님)
3. 아래 정보 획득:
   - Remote write URL (e.g., `https://prometheus-prod-XX-prod-us-central-0.grafana.net/api/prom/push`)
   - Username (stack ID)
   - API Key (새로 생성 · `MetricsPublisher` role)

### 3. Prometheus 서버 (로컬 또는 Fly.io) 설정

`prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: "quantbridge"
    bearer_token: "YOUR_PROMETHEUS_BEARER_TOKEN" # .env.example 의 값
    static_configs:
      - targets: ["quantbridge.yourdomain.com:8000"]
remote_write:
  - url: "https://prometheus-prod-XX-prod-us-central-0.grafana.net/api/prom/push"
    basic_auth:
      username: "YOUR_STACK_ID"
      password: "YOUR_API_KEY"
```
````

### 4. 대시보드 생성

Grafana → Dashboards → New → Query, 다음 5 패널:

1. **Backtest duration** (Histogram): `histogram_quantile(0.95, rate(qb_backtest_duration_seconds_bucket[5m]))`
2. **Order rejected rate**: `rate(qb_order_rejected_total[5m])` — split by `reason`
3. **Kill Switch activations**: `increase(qb_kill_switch_triggered_total[1h])` — split by `trigger_type`
4. **CCXT p95 latency**: `histogram_quantile(0.95, rate(qb_ccxt_request_duration_seconds_bucket[5m]))` — split by `exchange`, `endpoint`
5. **Active orders**: `qb_active_orders`

### 5. Alert rule 1개

Grafana → Alerting → New rule:

- **Name:** `Order rejected rate > 10%`
- **Condition:** `rate(qb_order_rejected_total[5m]) / rate(qb_ccxt_request_duration_seconds_count{endpoint="create_order"}[5m]) > 0.1`
- **For:** 5m (5분 지속 시 alert)
- **Notification:** Slack / Discord 웹훅 (본인 환경에 맞게)

### 6. 검증

1. `curl -H "Authorization: Bearer <token>" http://localhost:8000/metrics` → 5 metric prefix 확인
2. Prometheus 서버 시작 → `http://localhost:9090/targets` 에서 quantbridge 타겟 UP
3. Grafana Cloud → Explore 에서 `qb_backtest_duration_seconds_count` 쿼리 → 데이터 확인
4. 테스트 주문 거부 이벤트 생성 (e.g., leverage=125 강제) → 1-2분 후 alert rule 이 fire 되는지 관찰

## 보안 참고

- `PROMETHEUS_BEARER_TOKEN` 은 고강도 무작위 문자열 (openssl rand -hex 32)
- Grafana Cloud API Key 와 bearer token 은 **다른 값**
- 본 endpoint 는 public 노출 가능 (CSO-review PASS) — 민감 label 없음

````

## 검증 명령

```bash
cd backend
uv lock  # prometheus-client dependency 추가 반영
ruff check src/common/metrics.py src/main.py src/trading/ src/tasks/
mypy src/common/metrics.py src/main.py
pytest tests/common/test_metrics_* tests/trading/test_order_rejected_metric.py -v
# 테스트 5+ 건 green

# smoke
uvicorn src.main:app --reload --port 8000 &
curl -s http://localhost:8000/metrics | grep -c "^qb_"
# 5 이상 (metric 당 여러 line 이라 실제로는 더 많음)
# bearer token 설정 시
PROMETHEUS_BEARER_TOKEN=secret-xxx uvicorn src.main:app --reload --port 8000 &
curl -s http://localhost:8000/metrics
# 401
curl -s -H "Authorization: Bearer secret-xxx" http://localhost:8000/metrics | grep -c "^qb_"
# OK

pytest -x  # 전체 1053+ green
````

## Golden Rules 체크리스트

- [ ] `prometheus-client` 를 `pyproject.toml` 에 pin, `uv.lock` commit
- [ ] `from __future__ import annotations` 신규 파일 전부
- [ ] 환경변수 (`PROMETHEUS_BEARER_TOKEN`) 를 `.env.example` 에 먼저 등록
- [ ] `/metrics` endpoint 에 **민감 label 없음** (user_id, strategy_id, api_key 등)
- [ ] `SecretStr` 로 bearer token 저장 (로그 유출 방지)
- [ ] Celery prefork-safe — `metrics.py` 는 순수 prometheus_client import. Celery worker 가 metric 증분 시 lazy import 불필요 (prometheus_client 는 fork-safe)
- [ ] ruff / mypy green
- [ ] pytest 전체 green (Phase B 1053 + 신규 5+ ≈ 1060)

## 커밋 (2개 권장)

```
c1 feat(observability): Prometheus 5 metrics + /metrics endpoint (Phase D)

- common/metrics.py: 5 metrics (backtest duration, order rejected,
  kill switch, CCXT latency, active orders)
- main.py: GET /metrics (Clerk 제외, bearer token 보호)
- core/config.py: prometheus_bearer_token SecretStr | None
- .env.example: PROMETHEUS_BEARER_TOKEN
- pyproject.toml: prometheus-client>=0.21.0
- instrumentation: backtest task timer + OrderService reject counter +
  KillSwitch trigger + CCXT timer context manager + active_orders gauge
- tests: endpoint format + bearer auth + counter increment + order rejected

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

c2 docs(observability): Grafana Cloud Free runbook + alert rule (Phase D)

- docs/07_infra/grafana-cloud-setup.md (사용자 수동 가이드)
- 5 대시보드 패널 예시 쿼리 + 1 alert rule (order_rejected_rate > 10%)
- Prometheus remote_write 설정 예시

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

## Agent 출력 JSON

```json
{
  "branch": "feat/h2s9-observability",
  "commits": ["<sha1>", "<sha2>"],
  "files_added": ["..."],
  "files_modified": ["..."],
  "tests_added": <int>,
  "tests_total_after": <int>,
  "metrics_endpoint_smoke_verified": true,
  "bearer_auth_tested": true,
  "grafana_runbook_pages": <int>,
  "issues": ["..."],
  "ready_for_evaluator": true
}
```

## 리스크

| 리스크                                                                              | 대응                                                                                                              |
| ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `prometheus_client` 의 default `REGISTRY` 가 Celery worker fork 에 영향             | 단일 프로세스 mode 로 시작. multi-process (prod 수평 확장) 는 Sprint 10+.                                         |
| `/metrics` endpoint 의 Clerk 제외가 security review 에서 문제                       | Runbook 에 bearer token 보호 명시. label 에 민감 정보 없음. CSO-review 기준 PASS.                                 |
| `OrderService` 각 reject 경로에 `qb_order_rejected_total.inc()` 추가 시 누락 가능성 | 각 `raise` 전에 1줄씩. test 로 하나씩 검증.                                                                       |
| `qb_active_orders` gauge drift (crash 시 복구 불가)                                 | Phase 1 은 eventual consistency 로 OK. Phase 2 에서 DB count 로 re-sync 작업 추가.                                |
| Grafana Cloud Free 계정 미가입                                                      | runbook 에 가입 단계 포함. 본 스프린트는 runbook + endpoint + metrics 만 제공. 실제 Grafana 연결은 사용자가 수동. |

## Phase C 와의 독립성 확인

- 본 Phase 는 백엔드만 건드린다 (frontend 미변경)
- Phase C 는 프론트엔드만 건드린다 (backend 미변경 — stress_test API 는 Phase B 완료)
- 두 Phase 는 **완전히 독립** → 단일 메시지에서 2 Agent 동시 디스패치 가능 (isolation=worktree 각각).
