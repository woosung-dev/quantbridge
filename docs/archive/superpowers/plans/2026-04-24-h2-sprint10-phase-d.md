# H2 Sprint 10 — Phase D: CCXT Error Rate Metric Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 거래소 CCXT 호출 실패를 exchange × endpoint × error_class 세 차원으로 관측 가능하게 해서 "거래소가 5xx 를 토하면 즉시 알 수 있는가?" Beta pain 을 해소한다.

**Architecture:** 기존 `ccxt_timer` async context manager 의 `try / finally` 를 `try / except / finally` 로 확장. except 분기에서 `qb_ccxt_request_errors_total` counter 를 `(exchange, endpoint, error_class)` 라벨로 inc 한 뒤 `raise`. Grafana 대시보드 runbook 에 error rate alert 추가.

**Tech Stack:** `prometheus_client` (이미 설치됨 — Sprint 9 Phase D). 신규 deps 없음.

---

## Files

**Modify:**

- `backend/src/common/metrics.py:48-79` — `qb_ccxt_request_errors_total` Counter 1개 추가 + `ccxt_timer` 의 try block 확장
- `docs/07_infra/grafana-cloud-setup.md` — panel + alert rule 추가

**Create:**

- `backend/tests/common/test_ccxt_timer_errors.py` — 3 TDD (정상·ExchangeError·커스텀 예외)

**Reuse (수정 금지):**

- `backend/src/common/metrics.py:48-54` `qb_ccxt_request_duration_seconds` — 기존 histogram 형식 차용
- `backend/src/trading/providers.py` — 여러 provider 의 `async with ccxt_timer(...)` 호출자들. 본 PR 은 core 만 수정, provider 쪽 변경 없음

---

## Background

H2 Sprint 10 master plan §Phase D:

> Sprint 9 는 latency 만. error rate 필요.

ccxt_timer 현 구현 (`backend/src/common/metrics.py:63-79`):

```python
@asynccontextmanager
async def ccxt_timer(exchange: str, endpoint: str) -> AsyncIterator[None]:
    started = time.monotonic()
    try:
        yield
    finally:
        qb_ccxt_request_duration_seconds.labels(...).observe(...)
```

→ 예외 발생 시에도 finally 가 latency 기록은 하지만 **어떤 예외였는지 / 어떤 거래소 / 어떤 엔드포인트에서 발생했는지** 구분할 길 없음. Alert 관점에서 `error rate > 5%` 기반 페이징 불가능.

---

## Task 1: Counter metric 추가

**Files:**

- Modify: `backend/src/common/metrics.py` (라인 1-17 docstring + 라인 60 Gauge 다음에 추가)

- [ ] **Step 1.1: docstring 업데이트**

`backend/src/common/metrics.py` 의 module docstring (라인 1-17) 의 "5종 metrics" 리스트에 한 줄 추가:

```
- qb_ccxt_request_errors_total    (Counter, labels: exchange, endpoint, error_class)  ← Sprint 10 Phase D
```

- [ ] **Step 1.2: Counter 정의**

`backend/src/common/metrics.py` 의 `qb_active_orders = Gauge(...)` (라인 56-60) 다음, `@asynccontextmanager` (라인 63) 위에 추가:

```python
# 6. CCXT exchange API errors (Sprint 10 Phase D)
# `ccxt_timer` 의 except 분기에서 inc. `error_class = type(exc).__name__`.
# 정상 경로에서는 inc 되지 않음. `qb_ccxt_request_duration_seconds` 와 상관관계로
# rate(errors[5m]) / rate(duration_count[5m]) 가 error rate alert 의 기준.
qb_ccxt_request_errors_total = Counter(
    "qb_ccxt_request_errors_total",
    "CCXT exchange API errors — raise 직전 inc, exchange/endpoint/exception class 로 라벨링",
    labelnames=("exchange", "endpoint", "error_class"),
)
```

label cardinality 주의:

- exchange ∈ {bybit, bybit_futures, okx} ≤ 4 values
- endpoint ∈ {create_order, cancel_order, fetch_balance, fetch_ohlcv, ...} ≤ ~10
- error_class = `type(exc).__name__` — ccxt 는 ~20 정도의 예외 계열이지만 실전에서는 `ExchangeError`, `NetworkError`, `RateLimitExceeded`, `InsufficientFunds`, `InvalidOrder` 등 ~10 수준

총 cardinality ≈ 4 × 10 × 10 = ~400. prometheus 허용 범위 내.

- [ ] **Step 1.3: smoke**

```bash
cd /Users/woosung/project/agy-project/quant-bridge/.worktrees/h2s10-ccxt-errors/backend
uv run python -c "
from src.common.metrics import qb_ccxt_request_errors_total
assert qb_ccxt_request_errors_total._name == 'qb_ccxt_request_errors_total'
assert qb_ccxt_request_errors_total._labelnames == ('exchange', 'endpoint', 'error_class')
print('OK: Counter registered with 3 labels')
"
```

Expected: `OK: Counter registered with 3 labels`.

- [ ] **Step 1.4: 커밋**

```bash
git add backend/src/common/metrics.py
git commit -m "feat(observability): add qb_ccxt_request_errors_total Counter

Sprint 10 Phase D — CCXT 호출 실패를 exchange × endpoint × error_class
세 차원으로 관측. rate(errors[5m]) / rate(duration_count[5m]) 가 Grafana
error rate alert 의 기준.

TDD + ccxt_timer 확장은 별도 커밋."
```

---

## Task 2: Test 1 — 정상 호출 시 errors counter 미증가 (RED → GREEN)

**Files:**

- Create: `backend/tests/common/test_ccxt_timer_errors.py`

- [ ] **Step 2.1: Test 작성**

`backend/tests/common/test_ccxt_timer_errors.py` 신규:

```python
"""Sprint 10 Phase D — ccxt_timer 의 error counter 검증.

TDD 3 case:
1. 정상 호출 (except 미발동) → qb_ccxt_request_errors_total 미증가
2. ExchangeError raise → counter +1 (exchange/endpoint/error_class=ExchangeError) + raise 보존
3. 커스텀 예외 raise → error_class = type(exc).__name__ 정확 라벨링
"""

from __future__ import annotations

import pytest

from src.common.metrics import ccxt_timer, qb_ccxt_request_errors_total


def _counter_value(exchange: str, endpoint: str, error_class: str) -> float:
    """Counter labels value 조회 — _value.get() 으로 현재 누적치 반환."""
    return qb_ccxt_request_errors_total.labels(
        exchange=exchange, endpoint=endpoint, error_class=error_class
    )._value.get()


@pytest.mark.asyncio
async def test_ccxt_timer_normal_path_does_not_increment_errors() -> None:
    """정상 호출 (yield 만) → errors counter 절대 inc 하지 않음."""
    before = _counter_value("bybit", "create_order", "ExchangeError")
    async with ccxt_timer("bybit", "create_order"):
        pass  # 정상 종료
    after = _counter_value("bybit", "create_order", "ExchangeError")
    assert after == before, f"counter must not inc on success (before={before}, after={after})"
```

- [ ] **Step 2.2: RED 확인**

```bash
uv run pytest tests/common/test_ccxt_timer_errors.py::test_ccxt_timer_normal_path_does_not_increment_errors -v
```

Expected: PASS (이미 ccxt_timer 정상 path 는 finally 만 동작. except 분기 없으므로 counter 변경 없음). 본 테스트는 **regression 보호** 목적 — Task 3 에서 except 분기 추가 후에도 정상 path 불변 검증.

---

## Task 3: Test 2 — ExchangeError 시 counter inc + raise 보존

**Files:**

- Modify: `backend/tests/common/test_ccxt_timer_errors.py`

- [ ] **Step 3.1: 테스트 추가**

```python
class _SimulatedExchangeError(Exception):
    """ccxt.ExchangeError 시뮬레이션 (본 테스트는 ccxt import 회피)."""


@pytest.mark.asyncio
async def test_ccxt_timer_on_exception_increments_errors_and_reraises() -> None:
    """예외 raise 시 errors counter +1 + 원 예외 그대로 전파."""
    before = _counter_value("bybit_futures", "cancel_order", "_SimulatedExchangeError")

    with pytest.raises(_SimulatedExchangeError, match="boom"):
        async with ccxt_timer("bybit_futures", "cancel_order"):
            raise _SimulatedExchangeError("boom")

    after = _counter_value("bybit_futures", "cancel_order", "_SimulatedExchangeError")
    assert after == before + 1, f"counter must inc by 1 (before={before}, after={after})"
```

- [ ] **Step 3.2: RED 확인**

```bash
uv run pytest tests/common/test_ccxt_timer_errors.py::test_ccxt_timer_on_exception_increments_errors_and_reraises -v
```

Expected: FAIL (ccxt_timer 의 try/finally 는 예외 흡수 안 하지만 counter inc 는 없음 → counter after == before).

- [ ] **Step 3.3: GREEN — ccxt_timer try/except/finally 확장**

`backend/src/common/metrics.py` 의 `ccxt_timer` 함수를 다음으로 교체:

```python
@asynccontextmanager
async def ccxt_timer(exchange: str, endpoint: str) -> AsyncIterator[None]:
    """CCXT 호출을 감싸 latency + error 를 관측.

    사용:
        async with ccxt_timer("bybit", "create_order"):
            await exchange.create_order(...)

    - latency: 정상/예외 관계없이 finally 블록에서 duration histogram 에 observe.
    - error:   except 블록에서 `qb_ccxt_request_errors_total` counter 를
               `(exchange, endpoint, type(exc).__name__)` 라벨로 +1 후 `raise`.
               원 예외는 변형 없이 전파 (Sprint 10 Phase D).
    """
    started = time.monotonic()
    try:
        yield
    except Exception as exc:
        qb_ccxt_request_errors_total.labels(
            exchange=exchange,
            endpoint=endpoint,
            error_class=type(exc).__name__,
        ).inc()
        raise
    finally:
        qb_ccxt_request_duration_seconds.labels(exchange=exchange, endpoint=endpoint).observe(
            time.monotonic() - started
        )
```

변경 한 가지: try 블록 다음에 `except Exception` 분기 추가. `raise` 유지 — 예외 흡수 금지.

- [ ] **Step 3.4: 실행 → 2 PASS**

```bash
uv run pytest tests/common/test_ccxt_timer_errors.py -v
```

Expected: 2 passed.

---

## Task 4: Test 3 — 다양한 예외 클래스 정확히 라벨링

**Files:**

- Modify: `backend/tests/common/test_ccxt_timer_errors.py`

- [ ] **Step 4.1: 테스트 추가**

```python
@pytest.mark.asyncio
async def test_ccxt_timer_labels_error_class_exactly() -> None:
    """서로 다른 예외 클래스 각각 독립 시리즈로 라벨링."""
    class _RateLimitExceeded(Exception):
        pass

    class _InsufficientFunds(Exception):
        pass

    before_rate = _counter_value("okx", "fetch_balance", "_RateLimitExceeded")
    before_funds = _counter_value("okx", "fetch_balance", "_InsufficientFunds")

    with pytest.raises(_RateLimitExceeded):
        async with ccxt_timer("okx", "fetch_balance"):
            raise _RateLimitExceeded()

    with pytest.raises(_InsufficientFunds):
        async with ccxt_timer("okx", "fetch_balance"):
            raise _InsufficientFunds()

    assert _counter_value("okx", "fetch_balance", "_RateLimitExceeded") == before_rate + 1
    assert _counter_value("okx", "fetch_balance", "_InsufficientFunds") == before_funds + 1
```

- [ ] **Step 4.2: 3 PASS 확인 + 커밋**

```bash
uv run pytest tests/common/test_ccxt_timer_errors.py -v
```

Expected: 3 passed.

```bash
git add backend/src/common/metrics.py backend/tests/common/test_ccxt_timer_errors.py
git commit -m "feat(observability): ccxt_timer 에러 계측 — try/except/finally + 3 TDD

Sprint 10 Phase D — 기존 try/finally 를 try/except/finally 로 확장.
except 분기에서 qb_ccxt_request_errors_total.labels(exchange, endpoint,
error_class=type(exc).__name__).inc() 후 raise. 원 예외 그대로 전파.

TDD 3:
- 정상 호출 시 errors counter 미증가 (regression 보호)
- 예외 발생 시 +1 + raise 보존
- 서로 다른 예외 클래스 각각 독립 시리즈로 라벨링"
```

---

## Task 5: 기존 테스트 회귀 확인

- [ ] **Step 5.1: 전체 pytest**

```bash
cd /Users/woosung/project/agy-project/quant-bridge/.worktrees/h2s10-ccxt-errors/backend
uv run pytest -q --tb=short -p no:randomly 2>&1 | tail -10
```

Expected: 1087 + 3 신규 = 1090 green / 17 skip / 0 fail.

**중요:** 기존 `test_metrics_instrumentation.py` 에서 `ccxt_timer` 정상 path 만 커버 — except 분기 추가로 기존 테스트 깨질 위험 낮음. 그러나 다른 provider 테스트 (`test_providers_*`) 가 mock 거래소에서 예외를 던질 수 있으므로, 해당 테스트가 counter 값을 검증하지 않는 한 무영향.

만약 회귀 발견 시:

- provider 테스트가 `qb_ccxt_request_errors_total` 을 직접 참조하는 경우 → 해당 테스트의 before/after delta 검증으로 수정
- 그 외는 깨지지 않아야 함

- [ ] **Step 5.2: mypy + ruff**

```bash
uv run ruff check . && uv run mypy src/
```

Expected: 0 error / 0 error.

---

## Task 6: Grafana runbook 업데이트

**Files:**

- Modify: `docs/07_infra/grafana-cloud-setup.md`

- [ ] **Step 6.1: 현 내용 확인**

```bash
cat docs/07_infra/grafana-cloud-setup.md | head -50
```

기존 5 metrics panel + 1 alert (order_rejected_rate > 10%) 구조 파악.

- [ ] **Step 6.2: panel + alert 추가**

`docs/07_infra/grafana-cloud-setup.md` 의 기존 "Alert rules" 섹션 끝에 추가:

````markdown
### Alert: CCXT error rate > 5%

**Sprint 10 Phase D**

CCXT 호출 실패가 전체 호출의 5% 를 초과 시 페이지. `qb_ccxt_request_errors_total`
(신규) 와 `qb_ccxt_request_duration_seconds_count` (Histogram 의 count series) 비율.

**PromQL:**

```promql
sum by (exchange) (rate(qb_ccxt_request_errors_total[5m]))
  / clamp_min(
      sum by (exchange) (rate(qb_ccxt_request_duration_seconds_count[5m])),
      1e-9
    )
  > 0.05
```
````

`clamp_min(..., 1e-9)` 은 호출 0건 시 division-by-zero 방지.

**Panel (Grafana JSON):**

- panel type: `stat` 또는 `timeseries`
- legend: `{{exchange}}`
- thresholds: 0.01 (green) / 0.05 (yellow) / 0.10 (red)
- unit: `percentunit`

**Alert rule (Grafana Cloud Free):**

- evaluate every: 1m
- pending period: 5m (false-positive 방지)
- labels: `severity=warning`
- annotations:
  - summary: `CCXT {{ $labels.exchange }} error rate {{ $value | humanizePercentage }}`
  - runbook_url: (향후 Sprint 11 runbook docs)

**해결 체크리스트:**

1. `qb_ccxt_request_errors_total{exchange=...}` 의 top error_class 확인
2. `RateLimitExceeded` 다수 → 거래소 rate limit 초과. API key 분리 또는 backoff 조정
3. `NetworkError` / `RequestTimeout` 다수 → 거래소 API 장애 또는 네트워크 이슈. Bybit status 페이지 확인
4. `AuthenticationError` → API key 만료/revoked. ExchangeAccount 회전 필요
5. `InsufficientFunds` → 거래 전략이 잔고 부족 상태에서 반복 시도. Kill Switch 검토

````

- [ ] **Step 6.3: 커밋**

```bash
git add docs/07_infra/grafana-cloud-setup.md
git commit -m "docs(observability): Grafana CCXT error rate alert runbook

Sprint 10 Phase D — rate(qb_ccxt_request_errors_total[5m]) /
rate(qb_ccxt_request_duration_seconds_count[5m]) > 0.05 alert.
clamp_min 으로 division-by-zero 방지. error_class top breakdown 에
따른 해결 체크리스트 추가 (RateLimitExceeded / NetworkError /
AuthenticationError / InsufficientFunds)."
````

---

## Task 7: Gate-D 최종 검증

- [ ] **Step 7.1: 전체 suite**

```bash
cd backend
uv run ruff check . && uv run mypy src/ && uv run pytest -q --tb=short -p no:randomly
```

Expected: ruff 0 / mypy 0 / 1090 green.

- [ ] **Step 7.2: /metrics 노출 확인 (mock 환경)**

```bash
uv run python -c "
from src.common.metrics import qb_ccxt_request_errors_total, ccxt_timer
import asyncio

async def _trigger():
    try:
        async with ccxt_timer('bybit', 'create_order'):
            raise Exception('simulated')
    except Exception:
        pass

asyncio.run(_trigger())

from prometheus_client import generate_latest
output = generate_latest().decode()
assert 'qb_ccxt_request_errors_total' in output
assert 'exchange=\"bybit\"' in output
print('OK: qb_ccxt_request_errors_total in /metrics output')
print([line for line in output.split('\n') if 'ccxt_request_errors' in line][:3])
"
```

Expected: `OK: ...` + 최소 3 라인 (metric + HELP + TYPE + labeled series).

---

## Verification Summary (Gate-D)

| 항목            | 명령                                                                           | 통과 기준                                |
| --------------- | ------------------------------------------------------------------------------ | ---------------------------------------- |
| Lint            | `ruff check .`                                                                 | 0 error                                  |
| Type            | `mypy src/`                                                                    | 0 error                                  |
| Tests           | `pytest -q -p no:randomly`                                                     | 1087 + 3 = 1090 green / 17 skip / 0 fail |
| Counter 등록    | `python -c "from src.common.metrics import qb_ccxt_request_errors_total; ..."` | labels match                             |
| /metrics 노출   | trigger + generate_latest()                                                    | `qb_ccxt_request_errors_total` 포함      |
| Grafana runbook | `docs/07_infra/grafana-cloud-setup.md`                                         | alert rule + 해결 체크리스트             |

---

## What this Phase is NOT

- 거래소 rate limit 회피 — 별도 backoff 정책 필요 (Sprint 11)
- 실제 Grafana Cloud 배포/alert 테스트 — 사용자 수동 (외부 계정)
- error class 정규화 — ccxt 의 exception 계층을 그대로 사용 (cardinality 관리는 미래 과제)
- 특정 error_class 에 대한 자동 recovery — 운영자 수동 개입 전제

---

## Generator-Evaluator (Phase 완료 직후)

Phase A1 / B 와 동일 절차:

1. `git diff stage/h2-sprint10..feat/h2s10-ccxt-errors > /tmp/h2s10-d-diff.patch`
2. **codex** (foreground, 5min timeout) — diff + 다음 체크리스트:
   - `except Exception as exc` 의 범위가 적절한가? (`BaseException` / `KeyboardInterrupt` 제외 의도 명확?)
   - counter label cardinality 가 유지 가능한가? (`error_class` 가 동적으로 폭발 가능?)
   - `raise` 가 context 보존하는가? (`raise` vs `raise exc` 차이)
   - 기존 호출자 중 `except Exception` 가 있어 본 PR 의 counter inc 가 누락되는 path 가 있는가?
3. **Opus blind** (background, model=opus) — 파일 경로 + Golden Rules
4. **Sonnet blind** (background, model=sonnet) — PR body + edge case (예: `asyncio.CancelledError`, `GeneratorExit` 시나리오)
5. PASS = avg ≥ 8/10 ∧ blocker 0 ∧ major ≤ 2

---

## Phase A2/C 연결 맥락

- Phase A2 (Redis 분산 락) — 본 Phase D 와 무관. 독립 진행.
- Phase C (real broker E2E) — nightly CI 에서 본 PR 의 metric 을 Bybit Demo 실호출 경로에서 검증. Phase D 완료 후 Phase C 가 진짜 error 발생 가능한 환경에서 `qb_ccxt_request_errors_total` 수치를 눈으로 볼 수 있음.
