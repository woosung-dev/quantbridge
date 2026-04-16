# Sprint 4 — Celery + Backtest REST API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sprint 2의 순수 `run_backtest()` 엔진을 Celery task로 래핑하고, Backtest 도메인 7개 REST 엔드포인트를 완성한다. Sprint 3 이월 follow-up (S3-04 필수, S3-03 stretch)을 브랜치 초반에 정리한다.

**Architecture:**
- FastAPI + SQLModel + asyncpg (100% async). Celery 5.x prefork worker + Redis broker/result backend.
- Worker에서는 `asyncio.run()` per-task로 async Repository/Service 재사용 (Repository 이중화 없음).
- `TaskDispatcher` Protocol + `CeleryTaskDispatcher`(submit 경로) / `NoopTaskDispatcher`(worker 경로)로 순환 import 방지.
- 3-guard cancel 로직 + transient `CANCELLING` 상태 + 조건부 UPDATE로 race 수습.
- `OHLCVProvider` Protocol + `FixtureProvider`로 Sprint 5 `TimescaleProvider` 교체 경로 확보.

**Tech Stack:**
- Backend: Python 3.12, FastAPI, SQLModel, SQLAlchemy 2.0, asyncpg, Pydantic V2, Celery 5.4+, Redis
- Test: pytest + pytest-asyncio, httpx AsyncClient, Postgres savepoint fixture
- Engine: vectorbt 0.28.x (기존 유지), pandas

**Spec reference:** `docs/superpowers/specs/2026-04-15-sprint4-backtest-api-design.md`

**Branch:** `feat/sprint4-backtest-api` (이미 생성됨, main @ `3687028` 기반)

---

## 파일 구조 개요

### 신규 생성
```
backend/src/tasks/__init__.py                    # celery_app re-export
backend/src/tasks/celery_app.py                  # Celery 인스턴스 + @worker_ready hook
backend/src/tasks/backtest.py                    # run_backtest_task + _execute + reclaim_stale_running

backend/src/backtest/exceptions.py               # BacktestNotFound / StateConflict / OHLCVFixtureNotFound / TaskDispatchError
backend/src/backtest/dispatcher.py               # TaskDispatcher Protocol + 3 impls
backend/src/backtest/serializers.py              # JSONB Decimal/datetime helpers

backend/src/backtest/engine/trades.py            # extract_trades() — vectorbt → RawTrade

backend/src/market_data/providers/__init__.py    # OHLCVProvider Protocol
backend/src/market_data/providers/fixture.py     # FixtureProvider

backend/alembic/versions/XXXX_add_backtests.py   # migration

backend/data/fixtures/ohlcv/BTCUSDT_1h.csv       # 합성 OHLCV fixture
```

### 대규모 재작성 (현재 1-line 스텁)
```
backend/src/backtest/router.py                   # 7 endpoints
backend/src/backtest/service.py                  # BacktestService
backend/src/backtest/repository.py               # BacktestRepository
backend/src/backtest/models.py                   # Backtest + BacktestTrade + enums
backend/src/backtest/schemas.py                  # Pydantic DTOs
backend/src/backtest/dependencies.py             # DI
```

### 소규모 수정
```
backend/src/backtest/engine/adapter.py           # S3-04 — _price_to_sl_ratio ValueError
backend/src/backtest/engine/types.py             # BacktestResult.trades 필드 추가
backend/src/backtest/engine/__init__.py          # run_backtest() trades 주입
backend/src/strategy/service.py                  # delete()에 backtest 존재 검사 + IntegrityError catch
backend/src/strategy/exceptions.py               # StrategyHasBacktests 추가
backend/src/core/config.py                       # backtest_stale_threshold_seconds 필드
backend/src/main.py                              # backtest router 등록
backend/tests/conftest.py                        # from src.backtest.models import ...
backend/.env.example                             # BACKTEST_STALE_THRESHOLD_SECONDS + OHLCV_FIXTURE_ROOT
docs/03_api/endpoints.md                         # cancel 추가 + task_id → backtest_id
docs/TODO.md                                     # Sprint 4 완료 표시
```

### 테스트 파일 (신규)
```
backend/tests/backtest/test_service.py
backend/tests/backtest/test_repository.py
backend/tests/backtest/test_exceptions.py
backend/tests/backtest/test_dispatcher.py
backend/tests/backtest/test_serializers.py
backend/tests/backtest/engine/test_fault_injection.py    # S3-03
backend/tests/backtest/engine/test_trades_extract.py
backend/tests/tasks/test_backtest_task.py
backend/tests/market_data/test_fixture_provider.py
backend/tests/api/test_backtests_submit.py
backend/tests/api/test_backtests_list.py
backend/tests/api/test_backtests_detail.py
backend/tests/api/test_backtests_cancel.py
backend/tests/api/test_backtests_delete.py
backend/tests/api/test_backtests_trades.py
backend/tests/api/test_strategy_delete_with_backtests.py  # Sprint 3 회귀
```

---

## Milestone 1 — Engine Follow-ups (S3-04 필수 + S3-03 stretch 준비)

### Task 1: S3-04 — `_price_to_sl_ratio` ValueError

**Files:**
- Modify: `backend/src/backtest/engine/adapter.py` (lines 73-80)
- Modify: `backend/tests/backtest/engine/test_adapter.py` (기존 파일 있으면 추가, 없으면 생성)

- [ ] **Step 1: 기존 test_adapter.py 존재 확인**

```bash
ls backend/tests/backtest/engine/test_adapter.py 2>/dev/null || echo "NEW"
```

Expected: 기존 파일 없음 → NEW. 신규 생성.

- [ ] **Step 2: 실패 테스트 작성**

`backend/tests/backtest/engine/test_adapter.py`:
```python
"""adapter._price_to_sl_ratio S3-04 회귀 방지 테스트."""
from __future__ import annotations

import pandas as pd
import pytest

from src.backtest.engine.adapter import _price_to_sl_ratio


class TestPriceToSlRatio:
    def test_valid_positive_ratio(self) -> None:
        """sl_price < close → 양수 ratio."""
        close = pd.Series([100.0, 110.0, 120.0])
        sl = pd.Series([95.0, 104.5, 114.0])
        result = _price_to_sl_ratio(sl, close)
        assert result.tolist() == pytest.approx([0.05, 0.05, 0.05])

    def test_nan_preserved(self) -> None:
        """NaN (signal 없는 bar) 는 NaN 유지."""
        close = pd.Series([100.0, 110.0])
        sl = pd.Series([95.0, float("nan")])
        result = _price_to_sl_ratio(sl, close)
        assert result.iloc[0] == pytest.approx(0.05)
        assert pd.isna(result.iloc[1])

    def test_negative_ratio_raises(self) -> None:
        """sl_price > close → ValueError (silent mis-stop 방지)."""
        close = pd.Series([100.0, 110.0])
        sl = pd.Series([95.0, 115.0])  # 2번째 bar는 sl > close
        with pytest.raises(ValueError, match="Invalid SL price"):
            _price_to_sl_ratio(sl, close)

    def test_all_nan_no_error(self) -> None:
        """전체 NaN은 error 아님."""
        close = pd.Series([100.0, 110.0])
        sl = pd.Series([float("nan"), float("nan")])
        result = _price_to_sl_ratio(sl, close)
        assert pd.isna(result).all()
```

- [ ] **Step 3: 실패 확인**

```bash
cd backend && uv run pytest tests/backtest/engine/test_adapter.py::TestPriceToSlRatio::test_negative_ratio_raises -v
```

Expected: FAIL — ValueError 미발생 (현재 `_price_to_sl_ratio`가 조용히 음수 반환)

- [ ] **Step 4: 구현 — `_price_to_sl_ratio` ValueError 추가**

`backend/src/backtest/engine/adapter.py` 의 `_price_to_sl_ratio` 교체:

```python
def _price_to_sl_ratio(sl_price: pd.Series, close: pd.Series) -> pd.Series:
    """sl_stop 비율 변환: (close - sl_price) / close.

    smoke check 결과: vectorbt 0.28.x는 sl_stop을 비율로 해석함.
    절대 가격 Series를 직접 전달하면 SL이 작동하지 않음.
    NaN은 NaN 유지.
    음수 ratio (sl_price > close) 는 silent mis-stop 방지를 위해 ValueError.
    """
    ratio = (close - sl_price) / close
    # NaN은 허용. 음수만 감지
    dropped = ratio.dropna()
    if (dropped < 0).any():
        bad_idx = ratio.index[ratio.fillna(0) < 0]
        raise ValueError(
            f"Invalid SL price: sl_price exceeds close at index {list(bad_idx[:3])} "
            f"(would produce negative stop ratio, silent mis-stop). "
            f"Check strategy.exit(stop=...) value."
        )
    return ratio
```

- [ ] **Step 5: 전체 테스트 + 엔진 회귀 확인**

```bash
cd backend && uv run pytest tests/backtest/engine -v
```

Expected: PASS (4 신규 + 기존 엔진 골든 테스트 모두 green)

- [ ] **Step 6: ruff + mypy**

```bash
cd backend && uv run ruff check src/backtest/engine/adapter.py tests/backtest/engine/test_adapter.py && uv run mypy src/backtest/engine/adapter.py
```

Expected: All checks passed.

- [ ] **Step 7: 커밋**

```bash
git add backend/src/backtest/engine/adapter.py backend/tests/backtest/engine/test_adapter.py
git commit -m "$(cat <<'EOF'
fix(backtest-engine): S3-04 — _price_to_sl_ratio rejects negative ratio

sl_price > close 시 silent mis-stop 방지 위해 ValueError raise.
기존: 음수 ratio를 그대로 vectorbt에 전달 → |ratio| 로 해석되어 잘못된 stop 가동.
이후: ValueError → run_backtest() catch → BacktestOutcome(status='error').

Sprint 3 follow-up S3-04 해결.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Engine `BacktestResult.trades` 필드 추가 + `RawTrade` DTO

**Files:**
- Modify: `backend/src/backtest/engine/types.py`
- Test: (Task 4에서 extract_trades 통합 테스트로 커버)

- [ ] **Step 1: `RawTrade` + `BacktestResult.trades` 추가**

`backend/src/backtest/engine/types.py` 교체:

```python
"""백테스트 엔진 타입 정의."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

import pandas as pd

from src.strategy.pine import ParseOutcome, PineError


@dataclass(frozen=True)
class BacktestConfig:
    """vectorbt Portfolio.from_signals() 호출 파라미터."""

    init_cash: Decimal = Decimal("10000")
    fees: float = 0.001        # 0.1%
    slippage: float = 0.0005   # 0.05%
    freq: str = "1D"           # pandas offset alias


@dataclass(frozen=True)
class BacktestMetrics:
    """5개 표준 지표. 금융 수치는 Decimal."""

    total_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal      # 음수 (-0.25 = -25%)
    win_rate: Decimal          # 0.0 ~ 1.0
    num_trades: int


@dataclass(frozen=True)
class RawTrade:
    """엔진 레벨 trade 레코드. vectorbt records_readable → 도메인 중립 DTO.

    bar_index는 유지 (service layer에서 ohlcv.index로 datetime 변환).
    """

    trade_index: int
    direction: Literal["long", "short"]
    status: Literal["open", "closed"]
    entry_bar_index: int
    exit_bar_index: int | None
    entry_price: Decimal
    exit_price: Decimal | None
    size: Decimal
    pnl: Decimal
    return_pct: Decimal
    fees: Decimal


@dataclass(frozen=True)
class BacktestResult:
    """백테스트 실행 결과."""

    metrics: BacktestMetrics
    equity_curve: pd.Series
    trades: list[RawTrade] = field(default_factory=list)    # Sprint 4 신규
    config_used: BacktestConfig = field(default_factory=BacktestConfig)


@dataclass
class BacktestOutcome:
    """run_backtest() 공개 반환 타입. ParseOutcome을 래핑."""

    status: Literal["ok", "unsupported", "error", "parse_failed"]
    parse: ParseOutcome
    result: BacktestResult | None = None
    error: PineError | str | None = None
```

- [ ] **Step 2: 기존 골든 테스트 회귀 확인**

```bash
cd backend && uv run pytest tests/backtest/engine -v
```

Expected: PASS — `trades`가 default `[]`라 기존 테스트 영향 없음.

- [ ] **Step 3: mypy + ruff**

```bash
cd backend && uv run ruff check src/backtest/engine/types.py && uv run mypy src/backtest/engine/types.py
```

Expected: green.

- [ ] **Step 4: 커밋**

```bash
git add backend/src/backtest/engine/types.py
git commit -m "$(cat <<'EOF'
feat(backtest-engine): RawTrade DTO + BacktestResult.trades

Sprint 4 대비 engine 리턴 확장. Service layer에서 bar_index → datetime 변환.
기본값 [] 로 기존 Sprint 2 골든 테스트 회귀 없음.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: `engine/trades.py` — `extract_trades()` 함수

**Files:**
- Create: `backend/src/backtest/engine/trades.py`
- Create: `backend/tests/backtest/engine/test_trades_extract.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/backtest/engine/test_trades_extract.py`:
```python
"""extract_trades() — vectorbt Portfolio → RawTrade list."""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest
import vectorbt as vbt

from src.backtest.engine.trades import extract_trades
from src.backtest.engine.types import RawTrade


@pytest.fixture
def simple_portfolio() -> vbt.Portfolio:
    close = pd.Series([100.0, 101.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0])
    entries = pd.Series([True, False, False, False, True, False, False, False])
    exits = pd.Series([False, False, True, False, False, False, True, False])
    return vbt.Portfolio.from_signals(close, entries, exits, init_cash=10000, fees=0.001)


class TestExtractTrades:
    def test_returns_list_of_raw_trade(self, simple_portfolio: vbt.Portfolio) -> None:
        ohlcv = pd.DataFrame({"close": simple_portfolio.close}, index=simple_portfolio.wrapper.index)
        trades = extract_trades(simple_portfolio, ohlcv)
        assert isinstance(trades, list)
        assert len(trades) == 2  # entries 2개, exits 2개
        for t in trades:
            assert isinstance(t, RawTrade)

    def test_decimal_precision(self, simple_portfolio: vbt.Portfolio) -> None:
        """엔트리 가격/수량이 Decimal로 변환되어야."""
        ohlcv = pd.DataFrame({"close": simple_portfolio.close}, index=simple_portfolio.wrapper.index)
        trades = extract_trades(simple_portfolio, ohlcv)
        assert all(isinstance(t.entry_price, Decimal) for t in trades)
        assert all(isinstance(t.pnl, Decimal) for t in trades)
        assert all(isinstance(t.fees, Decimal) for t in trades)

    def test_fees_decimal_first_sum(self, simple_portfolio: vbt.Portfolio) -> None:
        """fees = Decimal(entry) + Decimal(exit). float 공간 합산 금지."""
        ohlcv = pd.DataFrame({"close": simple_portfolio.close}, index=simple_portfolio.wrapper.index)
        trades = extract_trades(simple_portfolio, ohlcv)
        # 모든 fee는 0보다 커야 (fees=0.001 적용)
        assert all(t.fees > Decimal("0") for t in trades)

    def test_closed_trades_have_exit(self, simple_portfolio: vbt.Portfolio) -> None:
        ohlcv = pd.DataFrame({"close": simple_portfolio.close}, index=simple_portfolio.wrapper.index)
        trades = extract_trades(simple_portfolio, ohlcv)
        closed = [t for t in trades if t.status == "closed"]
        for t in closed:
            assert t.exit_bar_index is not None
            assert t.exit_price is not None

    def test_direction_lowercase(self, simple_portfolio: vbt.Portfolio) -> None:
        ohlcv = pd.DataFrame({"close": simple_portfolio.close}, index=simple_portfolio.wrapper.index)
        trades = extract_trades(simple_portfolio, ohlcv)
        for t in trades:
            assert t.direction in ("long", "short")

    def test_empty_trades(self) -> None:
        """signals 없는 portfolio → 빈 list."""
        close = pd.Series([100.0, 101.0, 102.0])
        entries = pd.Series([False, False, False])
        exits = pd.Series([False, False, False])
        pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=10000)
        ohlcv = pd.DataFrame({"close": close})
        trades = extract_trades(pf, ohlcv)
        assert trades == []
```

- [ ] **Step 2: 실패 확인**

```bash
cd backend && uv run pytest tests/backtest/engine/test_trades_extract.py -v
```

Expected: FAIL — `ModuleNotFoundError: src.backtest.engine.trades`

- [ ] **Step 3: `extract_trades()` 구현**

`backend/src/backtest/engine/trades.py`:
```python
"""vectorbt Portfolio.trades → RawTrade list 변환."""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
import vectorbt as vbt

from src.backtest.engine.types import RawTrade


def extract_trades(pf: vbt.Portfolio, ohlcv: pd.DataFrame) -> list[RawTrade]:
    """vectorbt Portfolio → RawTrade list.

    Bar index는 유지 (service layer에서 ohlcv.index로 datetime 복원).

    Decimal 변환 원칙: float 공간에서 arithmetic 수행 전 str() 경유로 Decimal 진입.
    fees 같이 합산이 필요한 필드는 Decimal 변환 후 합산 — CLAUDE.md 금융 규칙.
    """
    df = pf.trades.records_readable
    raw_trades: list[RawTrade] = []

    for _, row in df.iterrows():
        # fees: Decimal-first 합산
        fees_total = Decimal(str(row["Entry Fees"])) + Decimal(str(row["Exit Fees"]))
        is_closed = row["Status"] == "Closed"

        raw_trades.append(
            RawTrade(
                trade_index=int(row["Exit Trade Id"]),
                direction="long" if row["Direction"] == "Long" else "short",
                status="closed" if is_closed else "open",
                entry_bar_index=int(row["Entry Timestamp"]),
                exit_bar_index=int(row["Exit Timestamp"]) if is_closed else None,
                entry_price=Decimal(str(row["Avg Entry Price"])),
                exit_price=Decimal(str(row["Avg Exit Price"])) if is_closed else None,
                size=Decimal(str(row["Size"])),
                pnl=Decimal(str(row["PnL"])),
                return_pct=Decimal(str(row["Return"])),
                fees=fees_total,
            )
        )

    return raw_trades
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd backend && uv run pytest tests/backtest/engine/test_trades_extract.py -v
```

Expected: PASS (6 tests)

- [ ] **Step 5: ruff + mypy**

```bash
cd backend && uv run ruff check src/backtest/engine/trades.py tests/backtest/engine/test_trades_extract.py && uv run mypy src/backtest/engine/trades.py
```

- [ ] **Step 6: 커밋**

```bash
git add backend/src/backtest/engine/trades.py backend/tests/backtest/engine/test_trades_extract.py
git commit -m "feat(backtest-engine): extract_trades() for vectorbt records_readable → RawTrade

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `run_backtest()` — trades 주입

**Files:**
- Modify: `backend/src/backtest/engine/__init__.py` (lines 22-62)

- [ ] **Step 1: run_backtest() 내부에서 extract_trades 호출**

`backend/src/backtest/engine/__init__.py` 의 `run_backtest` 함수 교체:

```python
"""백테스트 엔진 공개 API."""
from __future__ import annotations

import logging

import pandas as pd
import vectorbt as vbt

from src.backtest.engine.adapter import to_portfolio_kwargs
from src.backtest.engine.metrics import extract_metrics
from src.backtest.engine.trades import extract_trades
from src.backtest.engine.types import (
    BacktestConfig,
    BacktestMetrics,
    BacktestOutcome,
    BacktestResult,
    RawTrade,
)
from src.strategy.pine import parse_and_run

logger = logging.getLogger(__name__)


def run_backtest(
    source: str,
    ohlcv: pd.DataFrame,
    config: BacktestConfig | None = None,
) -> BacktestOutcome:
    """Pine source + OHLCV → BacktestOutcome.

    파서가 ok로 반환하면 vectorbt로 백테스트를 실행하고 지표+trades를 추출한다.
    파서가 ok 외 상태를 반환하면 status='parse_failed'로 즉시 반환한다.
    """
    cfg = config if config is not None else BacktestConfig()
    parse = parse_and_run(source, ohlcv)

    if parse.status != "ok" or parse.result is None:
        return BacktestOutcome(
            status="parse_failed",
            parse=parse,
            result=None,
            error=parse.error,
        )

    try:
        kwargs = to_portfolio_kwargs(parse.result, ohlcv, cfg)
        pf = vbt.Portfolio.from_signals(**kwargs)
        metrics = extract_metrics(pf)
        equity_curve = _as_series(pf.value())
        trades = extract_trades(pf, ohlcv)
    except Exception as exc:
        logger.exception("backtest_engine_error")
        return BacktestOutcome(
            status="error",
            parse=parse,
            result=None,
            error=str(exc),
        )

    result = BacktestResult(
        metrics=metrics,
        equity_curve=equity_curve,
        trades=trades,
        config_used=cfg,
    )
    logger.info(
        "backtest_ok",
        extra={
            "num_trades": metrics.num_trades,
            "total_return": str(metrics.total_return),
            "trades_extracted": len(trades),
        },
    )
    return BacktestOutcome(status="ok", parse=parse, result=result, error=None)


def _as_series(value: object) -> pd.Series:
    """pf.value() 반환이 Series/DataFrame 어느 쪽이든 1-D Series로 정규화."""
    if isinstance(value, pd.DataFrame):
        return value.iloc[:, 0]
    if isinstance(value, pd.Series):
        return value
    return pd.Series([value])


__all__ = [
    "BacktestConfig",
    "BacktestMetrics",
    "BacktestOutcome",
    "BacktestResult",
    "RawTrade",
    "run_backtest",
]
```

- [ ] **Step 2: 기존 골든 테스트 회귀 확인**

```bash
cd backend && uv run pytest tests/backtest -v
```

Expected: PASS. 골든 테스트는 `outcome.result.metrics`/`equity_curve`만 참조하므로 trades 추가로 회귀 없음.

- [ ] **Step 3: 골든에 trades 검증 1건 추가 (간단)**

`backend/tests/backtest/engine/test_golden_backtest.py` 에 이미 golden 테스트 있다면 추가 assertion, 없다면 skip.

```bash
cd backend && uv run pytest tests/backtest/engine/test_golden_backtest.py -v
```

Expected: PASS.

- [ ] **Step 4: ruff + mypy**

```bash
cd backend && uv run ruff check src/backtest/engine/ && uv run mypy src/backtest/engine/
```

- [ ] **Step 5: 커밋**

```bash
git add backend/src/backtest/engine/__init__.py
git commit -m "feat(backtest-engine): run_backtest() fills BacktestResult.trades

vectorbt records_readable → RawTrade list via extract_trades().
Sprint 4 BacktestService가 이를 bar_index → datetime으로 변환 후 DB bulk insert.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: S3-03 — Engine fault injection 테스트 (stretch, non-blocking)

**Files:**
- Create: `backend/tests/backtest/engine/test_fault_injection.py`

> **Stretch target:** 미완성이어도 Sprint 4 완료 막지 않음. 최소 3건만 추가 후 다음 milestone으로 진행. 남은 미커버 라인은 §10.2 Post-Impl Notes에 기록 → Sprint 5 이관.

- [ ] **Step 1: fault injection 테스트 작성**

`backend/tests/backtest/engine/test_fault_injection.py`:
```python
"""S3-03: engine exception 분기 fault injection.

목표: src/backtest/engine/* 커버리지 91% → 95%. non-blocking stretch.
"""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from src.backtest.engine import run_backtest
from src.strategy.pine import PineError


SIMPLE_PINE_V5 = """//@version=5
strategy("T", overlay=true)
ema_fast = ta.ema(close, 10)
ema_slow = ta.ema(close, 30)
if ta.crossover(ema_fast, ema_slow)
    strategy.entry("L", strategy.long)
if ta.crossunder(ema_fast, ema_slow)
    strategy.close("L")
"""


@pytest.fixture
def valid_ohlcv() -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=100, freq="1h")
    return pd.DataFrame(
        {
            "open": range(100, 200),
            "high": range(101, 201),
            "low": range(99, 199),
            "close": range(100, 200),
            "volume": [100.0] * 100,
        },
        index=idx,
    )


class TestRunBacktestFaultInjection:
    def test_vectorbt_exception_becomes_error(self, valid_ohlcv: pd.DataFrame) -> None:
        """vbt.Portfolio.from_signals 예외 → BacktestOutcome(status='error')."""
        with patch("src.backtest.engine.vbt.Portfolio.from_signals", side_effect=RuntimeError("vbt boom")):
            outcome = run_backtest(SIMPLE_PINE_V5, valid_ohlcv)
        assert outcome.status == "error"
        assert outcome.result is None
        assert "vbt boom" in str(outcome.error)

    def test_extract_metrics_exception(self, valid_ohlcv: pd.DataFrame) -> None:
        """extract_metrics 예외 → error status."""
        with patch("src.backtest.engine.extract_metrics", side_effect=ValueError("metrics fail")):
            outcome = run_backtest(SIMPLE_PINE_V5, valid_ohlcv)
        assert outcome.status == "error"

    def test_parse_and_run_returns_non_ok(self, valid_ohlcv: pd.DataFrame) -> None:
        """parser가 'unsupported' 반환하면 parse_failed로 리턴."""
        invalid_pine = "//@version=5\nstrategy('X')\nstrategy.entry('L', strategy.long, qty_percent=10)"
        outcome = run_backtest(invalid_pine, valid_ohlcv)
        assert outcome.status == "parse_failed"
        assert outcome.result is None
```

- [ ] **Step 2: 테스트 실행 + 커버리지 측정**

```bash
cd backend && uv run pytest tests/backtest/engine/test_fault_injection.py -v
cd backend && uv run pytest --cov=src.backtest.engine --cov-report=term-missing tests/backtest/engine/
```

Expected: 3 tests PASS. 커버리지 % 숫자 관찰 → §10.2 기록용.

- [ ] **Step 3: ruff + 커밋**

```bash
cd backend && uv run ruff check tests/backtest/engine/test_fault_injection.py
git add backend/tests/backtest/engine/test_fault_injection.py
git commit -m "test(backtest-engine): S3-03 fault injection (stretch)

3 cases: vbt exception, metrics exception, parser non-ok.
Non-blocking — 미커버 라인은 §10.2 Post-Impl에 기록 후 Sprint 5 이관.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Milestone 2 — Data Layer (Config, Models, Migration)

### Task 6: `config.py` — `backtest_stale_threshold_seconds` 필드

**Files:**
- Modify: `backend/src/core/config.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: 현재 config.py 구조 확인**

```bash
cd backend && cat src/core/config.py | head -80
```

- [ ] **Step 2: Settings 필드 추가**

`backend/src/core/config.py`의 `Settings` 클래스에 신규 필드 삽입 (celery_* 설정 뒤):

```python
# 기존 celery_broker_url / celery_result_backend 다음에 추가

backtest_stale_threshold_seconds: int = Field(
    default=1800,
    description=(
        "running/cancelling 상태가 몇 초 초과 시 stale로 판정 "
        "(worker startup reclaim + GET /:id/progress의 stale 플래그). 기본 30분."
    ),
)

ohlcv_fixture_root: str = Field(
    default="backend/data/fixtures/ohlcv",
    description="FixtureProvider가 OHLCV CSV를 읽는 루트 경로. 프로세스 CWD 기준.",
)
```

- [ ] **Step 3: `.env.example` 업데이트**

`backend/.env.example` 에 추가 (Celery 섹션 뒤):

```env
# Backtest (Sprint 4)
BACKTEST_STALE_THRESHOLD_SECONDS=1800
OHLCV_FIXTURE_ROOT=backend/data/fixtures/ohlcv
```

- [ ] **Step 4: 전체 테스트 회귀 확인 (config 로드 검증)**

```bash
cd backend && uv run pytest -q
```

Expected: PASS (Settings import 시 validation 통과).

- [ ] **Step 5: 커밋**

```bash
git add backend/src/core/config.py backend/.env.example
git commit -m "feat(config): add backtest_stale_threshold_seconds + ohlcv_fixture_root

Sprint 4 — §8.3 stale reclaim + §7 fixture path.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: `backtest/models.py` — Backtest + BacktestTrade SQLModel

**Files:**
- Modify: `backend/src/backtest/models.py` (현재 1-line 스텁)

- [ ] **Step 1: 실제 파일 구조 확인**

```bash
cd backend && cat src/backtest/models.py && cat src/strategy/models.py | head -30
```

Sprint 3 `_utcnow()` 패턴 확인.

- [ ] **Step 2: 전체 모델 작성**

`backend/src/backtest/models.py` 전체 교체:

```python
"""Backtest 도메인 SQLModel."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


def _utcnow() -> datetime:
    """naive UTC datetime. Sprint 3 패턴 재사용 (S3-05 workaround)."""
    return datetime.utcnow()


class BacktestStatus(str, Enum):
    """Backtest 라이프사이클. CANCELLING은 transient."""

    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"  # transient — Worker 3-guard가 'cancelled'로 최종 전이
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TradeDirection(str, Enum):
    LONG = "long"
    SHORT = "short"


class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


if TYPE_CHECKING:
    pass  # Relationship forward refs는 문자열 사용


class Backtest(SQLModel, table=True):
    __tablename__ = "backtests"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        sa_column=Column(
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    strategy_id: UUID = Field(
        sa_column=Column(
            ForeignKey("strategies.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        )
    )

    # 입력 파라미터 (불변)
    symbol: str = Field(max_length=32, nullable=False)
    timeframe: str = Field(max_length=8, nullable=False)
    period_start: datetime = Field(nullable=False)
    period_end: datetime = Field(nullable=False)
    initial_capital: Decimal = Field(max_digits=20, decimal_places=8, nullable=False)

    # 실행 상태
    status: BacktestStatus = Field(
        sa_column=Column(
            SAEnum(BacktestStatus, name="backtest_status"),
            nullable=False,
            default=BacktestStatus.QUEUED,
        )
    )
    celery_task_id: str | None = Field(default=None, max_length=64)

    # 결과 (completed 시에만)
    metrics: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    equity_curve: list[Any] | None = Field(default=None, sa_column=Column(JSONB))
    error: str | None = Field(default=None, sa_column=Column(String(2000)))

    # Timestamps (S3-05 workaround — naive UTC)
    created_at: datetime = Field(default_factory=_utcnow, nullable=False)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    # Relations
    trades: list["BacktestTrade"] = Relationship(
        back_populates="backtest",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    __table_args__ = (
        Index("ix_backtests_user_created", "user_id", "created_at"),
        Index("ix_backtests_status", "status"),
    )


class BacktestTrade(SQLModel, table=True):
    __tablename__ = "backtest_trades"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    backtest_id: UUID = Field(
        sa_column=Column(
            ForeignKey("backtests.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    trade_index: int = Field(nullable=False)

    direction: TradeDirection = Field(
        sa_column=Column(SAEnum(TradeDirection, name="trade_direction"), nullable=False)
    )
    status: TradeStatus = Field(
        sa_column=Column(SAEnum(TradeStatus, name="trade_status"), nullable=False)
    )

    entry_time: datetime = Field(nullable=False)
    exit_time: datetime | None = Field(default=None)
    entry_price: Decimal = Field(max_digits=20, decimal_places=8)
    exit_price: Decimal | None = Field(default=None, max_digits=20, decimal_places=8)
    size: Decimal = Field(max_digits=20, decimal_places=8)
    pnl: Decimal = Field(max_digits=20, decimal_places=8)
    return_pct: Decimal = Field(max_digits=12, decimal_places=6)  # 10,000% 여유
    fees: Decimal = Field(max_digits=20, decimal_places=8, default=Decimal("0"))

    backtest: "Backtest" = Relationship(back_populates="trades")

    __table_args__ = (
        Index("ix_backtest_trades_backtest_idx", "backtest_id", "trade_index"),
    )
```

- [ ] **Step 3: mypy + ruff 검증**

```bash
cd backend && uv run ruff check src/backtest/models.py && uv run mypy src/backtest/models.py
```

- [ ] **Step 4: conftest.py에 import 추가**

`backend/tests/conftest.py` 상단 models import 블록에 추가:

```python
# 기존 User, Strategy import 뒤에 추가
from src.backtest.models import Backtest, BacktestTrade  # noqa: F401
```

- [ ] **Step 5: 전체 테스트 회귀 확인**

```bash
cd backend && uv run pytest -q
```

Expected: PASS. 새 테이블이 create_all()에 반영됨.

- [ ] **Step 6: 커밋**

```bash
git add backend/src/backtest/models.py backend/tests/conftest.py
git commit -m "feat(backtest): Backtest + BacktestTrade SQLModel

6 상태 enum (queued/running/cancelling/completed/failed/cancelled).
FK: user_id CASCADE, strategy_id RESTRICT, backtest_trades CASCADE.
conftest.py 에 import 추가해 create_all()에 반영.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: Alembic migration — backtests + backtest_trades 테이블

**Files:**
- Create: `backend/alembic/versions/XXXX_add_backtests.py` (Alembic autogenerate)

- [ ] **Step 1: migration 자동 생성**

```bash
cd backend && uv run alembic revision --autogenerate -m "add backtests and backtest_trades tables"
```

- [ ] **Step 2: 생성된 migration 파일 검토**

```bash
cd backend && ls -lt alembic/versions/*.py | head -3
```

최신 migration 파일 열어서 확인:
- `op.create_table("backtests", ...)` + `op.create_table("backtest_trades", ...)` 생성
- enum 타입 3개 (`backtest_status`, `trade_direction`, `trade_status`) CREATE
- 인덱스 `ix_backtests_user_created`, `ix_backtests_status`, `ix_backtest_trades_backtest_idx`
- FK `users.id` CASCADE, `strategies.id` **RESTRICT**, `backtests.id` CASCADE

필요 시 수동 수정 (RESTRICT가 autogenerate에서 누락될 수 있음).

- [ ] **Step 3: upgrade 실행**

```bash
cd backend && uv run alembic upgrade head
```

- [ ] **Step 4: downgrade → upgrade round-trip 검증**

```bash
cd backend && uv run alembic downgrade -1 && uv run alembic upgrade head
```

Expected: 오류 없음. Enum drop/create 순서 주의.

- [ ] **Step 5: 테스트 회귀**

```bash
cd backend && uv run pytest -q
```

- [ ] **Step 6: 커밋**

```bash
git add backend/alembic/versions/
git commit -m "feat(migration): add backtests + backtest_trades tables

- 3 enum types: backtest_status (6 values incl. CANCELLING), trade_direction, trade_status
- FK policies: user_id CASCADE, strategy_id RESTRICT, backtest_trades.backtest_id CASCADE
- 3 indexes

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Milestone 3 — Serializers + Exceptions

### Task 9: `serializers.py` — JSONB 직렬화 헬퍼

**Files:**
- Create: `backend/src/backtest/serializers.py`
- Create: `backend/tests/backtest/test_serializers.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/backtest/test_serializers.py`:
```python
"""JSONB serialization helpers — Decimal + datetime."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pandas as pd
import pytest

from src.backtest.engine.types import BacktestMetrics
from src.backtest.serializers import (
    _parse_utc_iso,
    _utc_iso,
    equity_curve_from_jsonb,
    equity_curve_to_jsonb,
    metrics_from_jsonb,
    metrics_to_jsonb,
)


class TestUtcIso:
    def test_naive_utc_to_z(self) -> None:
        dt = datetime(2024, 1, 1, 12, 34, 56)
        assert _utc_iso(dt) == "2024-01-01T12:34:56Z"

    def test_roundtrip(self) -> None:
        original = datetime(2024, 6, 15, 9, 0, 0)
        assert _parse_utc_iso(_utc_iso(original)) == original


class TestMetricsSerialization:
    def test_to_jsonb(self) -> None:
        m = BacktestMetrics(
            total_return=Decimal("0.18"),
            sharpe_ratio=Decimal("1.4"),
            max_drawdown=Decimal("-0.08"),
            win_rate=Decimal("0.56"),
            num_trades=24,
        )
        data = metrics_to_jsonb(m)
        assert data == {
            "total_return": "0.18",
            "sharpe_ratio": "1.4",
            "max_drawdown": "-0.08",
            "win_rate": "0.56",
            "num_trades": 24,
        }

    def test_roundtrip(self) -> None:
        m = BacktestMetrics(
            total_return=Decimal("0.1234"),
            sharpe_ratio=Decimal("2.0"),
            max_drawdown=Decimal("-0.05"),
            win_rate=Decimal("0.6"),
            num_trades=10,
        )
        restored = metrics_from_jsonb(metrics_to_jsonb(m))
        assert restored == m


class TestEquityCurveSerialization:
    def test_to_jsonb(self) -> None:
        idx = pd.DatetimeIndex([datetime(2024, 1, 1), datetime(2024, 1, 2)])
        s = pd.Series([Decimal("10000"), Decimal("10100")], index=idx)
        data = equity_curve_to_jsonb(s)
        assert data == [
            ["2024-01-01T00:00:00Z", "10000"],
            ["2024-01-02T00:00:00Z", "10100"],
        ]

    def test_float_series_to_jsonb(self) -> None:
        """pf.value()는 float Series — Decimal str로 변환."""
        idx = pd.DatetimeIndex([datetime(2024, 1, 1)])
        s = pd.Series([10000.5], index=idx)
        data = equity_curve_to_jsonb(s)
        assert data == [["2024-01-01T00:00:00Z", "10000.5"]]

    def test_roundtrip(self) -> None:
        data = [
            ["2024-01-01T00:00:00Z", "10000"],
            ["2024-01-01T01:00:00Z", "10050.25"],
        ]
        restored = equity_curve_from_jsonb(data)
        assert restored == [
            (datetime(2024, 1, 1, 0, 0, 0), Decimal("10000")),
            (datetime(2024, 1, 1, 1, 0, 0), Decimal("10050.25")),
        ]
```

- [ ] **Step 2: 실패 확인**

```bash
cd backend && uv run pytest tests/backtest/test_serializers.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: 구현**

`backend/src/backtest/serializers.py`:
```python
"""Backtest JSONB 직렬화 helpers.

metrics/equity_curve는 PostgreSQL JSONB 컬럼에 저장.
Decimal → str, datetime → ISO 8601 Z.
naive UTC datetime 전제 (Sprint 3 _utcnow() 규약).
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pandas as pd

from src.backtest.engine.types import BacktestMetrics


def _utc_iso(dt: datetime) -> str:
    """naive UTC datetime → ISO 8601 with Z suffix."""
    if dt.tzinfo is not None:
        # tz-aware → UTC 변환 후 naive화 (방어적)
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc_iso(s: str) -> datetime:
    """'2024-01-01T00:00:00Z' → naive UTC datetime."""
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


# --- metrics ---

def metrics_to_jsonb(m: BacktestMetrics) -> dict[str, Any]:
    """BacktestMetrics → JSONB dict (Decimal → str)."""
    return {
        "total_return": str(m.total_return),
        "sharpe_ratio": str(m.sharpe_ratio),
        "max_drawdown": str(m.max_drawdown),
        "win_rate": str(m.win_rate),
        "num_trades": m.num_trades,
    }


def metrics_from_jsonb(data: dict[str, Any]) -> BacktestMetrics:
    """JSONB dict → BacktestMetrics."""
    return BacktestMetrics(
        total_return=Decimal(data["total_return"]),
        sharpe_ratio=Decimal(data["sharpe_ratio"]),
        max_drawdown=Decimal(data["max_drawdown"]),
        win_rate=Decimal(data["win_rate"]),
        num_trades=int(data["num_trades"]),
    )


# --- equity_curve ---

def equity_curve_to_jsonb(series: pd.Series) -> list[list[str]]:
    """pd.Series(DatetimeIndex, Decimal or float values) → [[ISO str, Decimal str], ...]."""
    result: list[list[str]] = []
    for ts, value in series.items():
        if not isinstance(ts, datetime):
            # pandas Timestamp → datetime
            ts = pd.Timestamp(ts).to_pydatetime()
        # Decimal이 아니면 str()이 float repr일 수 있음 — str()로 직접 변환
        result.append([_utc_iso(ts), str(value)])
    return result


def equity_curve_from_jsonb(data: list[list[str]]) -> list[tuple[datetime, Decimal]]:
    """JSONB list → [(datetime, Decimal), ...]."""
    return [(_parse_utc_iso(ts), Decimal(v)) for ts, v in data]
```

- [ ] **Step 4: 테스트 통과**

```bash
cd backend && uv run pytest tests/backtest/test_serializers.py -v
```

- [ ] **Step 5: ruff + mypy + 커밋**

```bash
cd backend && uv run ruff check src/backtest/serializers.py tests/backtest/test_serializers.py && uv run mypy src/backtest/serializers.py
git add backend/src/backtest/serializers.py backend/tests/backtest/test_serializers.py
git commit -m "feat(backtest): JSONB serializers for metrics + equity_curve

naive UTC → ISO 8601 Z, Decimal ↔ str. Service layer 진입점.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Backtest + Strategy 예외 정의

**Files:**
- Create: `backend/src/backtest/exceptions.py`
- Modify: `backend/src/strategy/exceptions.py`

- [ ] **Step 1: 기존 AppException 구조 확인**

```bash
cd backend && cat src/common/exceptions.py src/strategy/exceptions.py
```

- [ ] **Step 2: `backtest/exceptions.py` 작성**

`backend/src/backtest/exceptions.py`:
```python
"""Backtest 도메인 예외. main.py 전역 핸들러에서 직렬화."""
from __future__ import annotations

from src.common.exceptions import AppException


class BacktestNotFound(AppException):
    code = "backtest_not_found"
    status_code = 404
    detail = "Backtest not found"


class BacktestStateConflict(AppException):
    code = "backtest_state_conflict"
    status_code = 409
    detail = "Backtest state does not allow this action"


class OHLCVFixtureNotFound(AppException):
    code = "ohlcv_fixture_not_found"
    status_code = 400
    detail = "OHLCV fixture not found"


class TaskDispatchError(AppException):
    code = "task_dispatch_failed"
    status_code = 503
    detail = "Failed to dispatch background task"
```

- [ ] **Step 3: `strategy/exceptions.py`에 `StrategyHasBacktests` 추가**

기존 파일 끝에 추가:

```python
class StrategyHasBacktests(AppException):
    code = "strategy_has_backtests"
    status_code = 409
    detail = "Strategy has associated backtests. Archive instead of delete."
```

- [ ] **Step 4: 예외 import smoke test**

```bash
cd backend && uv run python -c "from src.backtest.exceptions import BacktestNotFound, BacktestStateConflict, OHLCVFixtureNotFound, TaskDispatchError; from src.strategy.exceptions import StrategyHasBacktests; print('OK')"
```

Expected: OK

- [ ] **Step 5: ruff + 커밋**

```bash
cd backend && uv run ruff check src/backtest/exceptions.py src/strategy/exceptions.py
git add backend/src/backtest/exceptions.py backend/src/strategy/exceptions.py
git commit -m "feat(exceptions): backtest domain + strategy_has_backtests

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Milestone 4 — TaskDispatcher + OHLCVProvider

### Task 11: `backtest/dispatcher.py` — TaskDispatcher Protocol + 구현체

**Files:**
- Create: `backend/src/backtest/dispatcher.py`
- Create: `backend/tests/backtest/test_dispatcher.py`

- [ ] **Step 1: 실패 테스트**

`backend/tests/backtest/test_dispatcher.py`:
```python
"""TaskDispatcher 구현체 테스트."""
from __future__ import annotations

from uuid import uuid4

import pytest

from src.backtest.dispatcher import (
    FakeTaskDispatcher,
    NoopTaskDispatcher,
    TaskDispatcher,
)


class TestNoopTaskDispatcher:
    def test_raises_on_dispatch(self) -> None:
        """Worker 내부에서 실수로 dispatch 호출되면 명시적 실패."""
        d = NoopTaskDispatcher()
        with pytest.raises(RuntimeError, match="must not dispatch"):
            d.dispatch_backtest(uuid4())


class TestFakeTaskDispatcher:
    def test_returns_fixed_id(self) -> None:
        d = FakeTaskDispatcher(task_id="fake-task-42")
        assert d.dispatch_backtest(uuid4()) == "fake-task-42"

    def test_records_calls(self) -> None:
        d = FakeTaskDispatcher()
        id1, id2 = uuid4(), uuid4()
        d.dispatch_backtest(id1)
        d.dispatch_backtest(id2)
        assert d.dispatched == [id1, id2]
```

- [ ] **Step 2: 실패 확인**

```bash
cd backend && uv run pytest tests/backtest/test_dispatcher.py -v
```

Expected: FAIL — module not found.

- [ ] **Step 3: 구현**

`backend/src/backtest/dispatcher.py`:
```python
"""TaskDispatcher — submit 경로에서 Celery task enqueue.

BacktestService가 src.tasks를 직접 import하면 순환 의존 발생 (tasks가 service import).
Dispatcher Protocol로 추상화하고 dependencies.py에서 CeleryTaskDispatcher 주입.
"""
from __future__ import annotations

from typing import Protocol
from uuid import UUID


class TaskDispatcher(Protocol):
    def dispatch_backtest(self, backtest_id: UUID) -> str:
        """Enqueue backtest task. Returns celery task id."""
        ...


class CeleryTaskDispatcher:
    """실 구현 — HTTP submit 경로(dependencies.py)에서만 사용."""

    def dispatch_backtest(self, backtest_id: UUID) -> str:
        from src.tasks.backtest import run_backtest_task  # 지연 import
        async_result = run_backtest_task.delay(str(backtest_id))
        return async_result.id


class NoopTaskDispatcher:
    """Worker `_execute()` 내부 / 일부 테스트용.

    dispatch 호출되면 RuntimeError — submit/run 책임 분리 명시.
    """

    def dispatch_backtest(self, backtest_id: UUID) -> str:
        raise RuntimeError("NoopTaskDispatcher must not dispatch")


class FakeTaskDispatcher:
    """테스트 전용 — 고정 task_id 반환 + 호출 기록."""

    def __init__(self, task_id: str = "test-task-id") -> None:
        self.task_id = task_id
        self.dispatched: list[UUID] = []

    def dispatch_backtest(self, backtest_id: UUID) -> str:
        self.dispatched.append(backtest_id)
        return self.task_id
```

- [ ] **Step 4: 테스트 통과 + 커밋**

```bash
cd backend && uv run pytest tests/backtest/test_dispatcher.py -v && uv run ruff check src/backtest/dispatcher.py tests/backtest/test_dispatcher.py
git add backend/src/backtest/dispatcher.py backend/tests/backtest/test_dispatcher.py
git commit -m "feat(backtest): TaskDispatcher Protocol + 3 impls

CeleryTaskDispatcher (real), NoopTaskDispatcher (worker guard), FakeTaskDispatcher (test).
순환 import 방지를 위한 지연 import 패턴.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: OHLCV fixture CSV 생성 (`BTCUSDT_1h.csv`)

**Files:**
- Create: `backend/data/fixtures/ohlcv/BTCUSDT_1h.csv`

- [ ] **Step 1: 디렉토리 생성 + 합성 CSV 생성**

```bash
mkdir -p backend/data/fixtures/ohlcv
```

- [ ] **Step 2: 합성 OHLCV 생성 script 작성 + 실행**

```bash
cd backend && uv run python -c "
import pandas as pd
import numpy as np
np.random.seed(42)

# 2024년 1년치 1h OHLCV 합성 (8760 rows)
idx = pd.date_range('2024-01-01T00:00:00', periods=8760, freq='1h', tz='UTC').tz_localize(None)
n = len(idx)

# Brownian motion-like close
returns = np.random.normal(0.0001, 0.005, n)
close = 42000 * np.exp(np.cumsum(returns))

# OHLC from close
high = close * (1 + np.abs(np.random.normal(0, 0.002, n)))
low = close * (1 - np.abs(np.random.normal(0, 0.002, n)))
open_ = np.roll(close, 1)
open_[0] = close[0]
volume = np.abs(np.random.normal(100, 30, n))

df = pd.DataFrame({
    'timestamp': idx.strftime('%Y-%m-%dT%H:%M:%SZ'),
    'open': open_.round(2),
    'high': high.round(2),
    'low': low.round(2),
    'close': close.round(2),
    'volume': volume.round(2),
})
df.to_csv('data/fixtures/ohlcv/BTCUSDT_1h.csv', index=False)
print(f'Generated {n} rows, first: {df.iloc[0].tolist()}')
"
```

Expected: `Generated 8760 rows, first: [...]`

- [ ] **Step 3: CSV 검증**

```bash
cd backend && head -3 data/fixtures/ohlcv/BTCUSDT_1h.csv && wc -l data/fixtures/ohlcv/BTCUSDT_1h.csv
```

Expected: 헤더 `timestamp,open,high,low,close,volume` + 8760 데이터 행.

- [ ] **Step 4: 커밋**

```bash
git add backend/data/fixtures/ohlcv/BTCUSDT_1h.csv
git commit -m "feat(data): BTCUSDT_1h synthetic OHLCV fixture for Sprint 4

2024 전체 기간 8760 rows (1h). Brownian motion 합성.
OHLCVProvider 기반 테스트/로컬 smoke용.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: `market_data/providers/` — Protocol + FixtureProvider

**Files:**
- Create: `backend/src/market_data/providers/__init__.py`
- Create: `backend/src/market_data/providers/fixture.py`
- Create: `backend/tests/market_data/test_fixture_provider.py`

- [ ] **Step 1: 테스트 먼저 작성**

`backend/tests/market_data/test_fixture_provider.py`:
```python
"""FixtureProvider — CSV 로드 + 기간 필터."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src.backtest.exceptions import OHLCVFixtureNotFound
from src.market_data.providers import OHLCVProvider
from src.market_data.providers.fixture import FixtureProvider


@pytest.fixture
def fixture_root(tmp_path: Path) -> Path:
    """임시 fixture 디렉토리 + 미니 CSV 생성."""
    root = tmp_path / "ohlcv"
    root.mkdir()
    csv = root / "BTCUSDT_1h.csv"
    csv.write_text(
        "timestamp,open,high,low,close,volume\n"
        "2024-01-01T00:00:00Z,100.0,101.0,99.0,100.5,10.0\n"
        "2024-01-01T01:00:00Z,100.5,102.0,100.0,101.5,11.0\n"
        "2024-01-01T02:00:00Z,101.5,103.0,101.0,102.5,12.0\n"
        "2024-01-01T03:00:00Z,102.5,104.0,102.0,103.5,13.0\n"
    )
    return root


class TestFixtureProvider:
    def test_satisfies_protocol(self, fixture_root: Path) -> None:
        """Protocol static check."""
        provider: OHLCVProvider = FixtureProvider(root=fixture_root)
        assert provider is not None

    @pytest.mark.asyncio
    async def test_get_ohlcv_full_range(self, fixture_root: Path) -> None:
        provider = FixtureProvider(root=fixture_root)
        df = await provider.get_ohlcv(
            symbol="BTCUSDT",
            timeframe="1h",
            period_start=datetime(2024, 1, 1, 0, 0, 0),
            period_end=datetime(2024, 1, 1, 3, 0, 0),
        )
        assert len(df) == 4
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]
        assert isinstance(df.index, pd.DatetimeIndex)

    @pytest.mark.asyncio
    async def test_period_filter(self, fixture_root: Path) -> None:
        provider = FixtureProvider(root=fixture_root)
        df = await provider.get_ohlcv(
            symbol="BTCUSDT",
            timeframe="1h",
            period_start=datetime(2024, 1, 1, 1, 0, 0),
            period_end=datetime(2024, 1, 1, 2, 0, 0),
        )
        assert len(df) == 2

    @pytest.mark.asyncio
    async def test_missing_file_raises(self, fixture_root: Path) -> None:
        provider = FixtureProvider(root=fixture_root)
        with pytest.raises(OHLCVFixtureNotFound):
            await provider.get_ohlcv(
                symbol="ETHUSDT",  # 없는 심볼
                timeframe="1h",
                period_start=datetime(2024, 1, 1),
                period_end=datetime(2024, 1, 2),
            )
```

- [ ] **Step 2: 실패 확인**

```bash
cd backend && uv run pytest tests/market_data/test_fixture_provider.py -v
```

Expected: FAIL — modules not found.

- [ ] **Step 3: Protocol + FixtureProvider 구현**

`backend/src/market_data/providers/__init__.py`:
```python
"""OHLCVProvider Protocol — backtest 도메인이 OHLCV를 조회하는 추상 경계.

Sprint 4: FixtureProvider.
Sprint 5: TimescaleProvider 추가 예정 (TimescaleDB hypertable).
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

import pandas as pd


class OHLCVProvider(Protocol):
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
    ) -> pd.DataFrame:
        """DatetimeIndex + [open, high, low, close, volume] 컬럼 DataFrame 반환.

        Raises:
            OHLCVFixtureNotFound (or Sprint 5 equivalent): 데이터 미존재.
        """
        ...
```

`backend/src/market_data/providers/fixture.py`:
```python
"""FixtureProvider — Sprint 4 fixture CSV 기반 OHLCV."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.backtest.exceptions import OHLCVFixtureNotFound
from src.core.config import settings


class FixtureProvider:
    """data/fixtures/ohlcv/{SYMBOL}_{TIMEFRAME}.csv 기반 provider.

    Sprint 5에서 TimescaleProvider로 교체 예정.
    """

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else Path(settings.ohlcv_fixture_root)

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        period_start: datetime,
        period_end: datetime,
    ) -> pd.DataFrame:
        path = self.root / f"{symbol}_{timeframe}.csv"
        if not path.exists():
            raise OHLCVFixtureNotFound(
                detail=f"No fixture for {symbol} {timeframe} at {path}"
            )

        # pandas async I/O는 없으므로 동기 read (fixture 크기 작음)
        df = pd.read_csv(path, parse_dates=["timestamp"])
        df = df.set_index("timestamp")

        # period 필터
        mask = (df.index >= period_start) & (df.index <= period_end)
        return df.loc[mask]
```

- [ ] **Step 4: 테스트 통과**

```bash
cd backend && uv run pytest tests/market_data/test_fixture_provider.py -v
```

- [ ] **Step 5: ruff + mypy + 커밋**

```bash
cd backend && uv run ruff check src/market_data/providers/ tests/market_data/ && uv run mypy src/market_data/providers/
mkdir -p backend/tests/market_data  # 디렉토리 없으면
touch backend/tests/market_data/__init__.py
git add backend/src/market_data/providers/ backend/tests/market_data/
git commit -m "feat(market-data): OHLCVProvider Protocol + FixtureProvider

Sprint 5 TimescaleProvider 교체 가능 설계. Fixture 경로는 settings.ohlcv_fixture_root.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Milestone 5 — Repository

### Task 14: `BacktestRepository` — CRUD + 조건부 UPDATE

**Files:**
- Modify: `backend/src/backtest/repository.py` (전체 재작성)
- Create: `backend/tests/backtest/test_repository.py`

- [ ] **Step 1: 테스트 먼저 — 핵심 경로 8건**

`backend/tests/backtest/test_repository.py`:
```python
"""BacktestRepository — CRUD + 조건부 UPDATE."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus, BacktestTrade, TradeDirection, TradeStatus
from src.backtest.repository import BacktestRepository


async def _make_user_and_strategy(session: AsyncSession) -> tuple[Backtest, BacktestRepository]:
    """User + Strategy 생성 + 기본 Backtest row."""
    from src.auth.models import User
    from src.strategy.models import ParseStatus, PineVersion, Strategy

    user = User(
        id=uuid4(),
        clerk_user_id=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@ex.com",
    )
    session.add(user)
    await session.flush()

    strategy = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="T",
        pine_source="//@version=5\nstrategy('T')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    session.add(strategy)
    await session.flush()

    bt = Backtest(
        id=uuid4(),
        user_id=user.id,
        strategy_id=strategy.id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1),
        period_end=datetime(2024, 1, 31),
        initial_capital=Decimal("10000"),
    )
    session.add(bt)
    await session.flush()
    return bt, BacktestRepository(session)


class TestBacktestRepository:
    @pytest.mark.asyncio
    async def test_create_and_get(self, db_session: AsyncSession) -> None:
        bt, repo = await _make_user_and_strategy(db_session)
        fetched = await repo.get_by_id(bt.id, user_id=bt.user_id)
        assert fetched is not None
        assert fetched.id == bt.id

    @pytest.mark.asyncio
    async def test_get_other_user_returns_none(self, db_session: AsyncSession) -> None:
        bt, repo = await _make_user_and_strategy(db_session)
        other_user = uuid4()
        fetched = await repo.get_by_id(bt.id, user_id=other_user)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_update_status_to_running_conditional(self, db_session: AsyncSession) -> None:
        bt, repo = await _make_user_and_strategy(db_session)
        rows = await repo.transition_to_running(bt.id, started_at=datetime.utcnow())
        assert rows == 1

        # 두 번째 호출 — status='queued'가 아니므로 rows=0
        rows2 = await repo.transition_to_running(bt.id, started_at=datetime.utcnow())
        assert rows2 == 0

    @pytest.mark.asyncio
    async def test_complete_conditional(self, db_session: AsyncSession) -> None:
        bt, repo = await _make_user_and_strategy(db_session)
        await repo.transition_to_running(bt.id, started_at=datetime.utcnow())
        rows = await repo.complete(
            bt.id,
            metrics={"total_return": "0.18"},
            equity_curve=[["2024-01-01T00:00:00Z", "10000"]],
            where_status=BacktestStatus.RUNNING,
        )
        assert rows == 1

    @pytest.mark.asyncio
    async def test_cancel_conditional(self, db_session: AsyncSession) -> None:
        bt, repo = await _make_user_and_strategy(db_session)
        rows = await repo.request_cancel(bt.id)
        assert rows == 1

        # 재호출 — 이미 cancelling
        rows2 = await repo.request_cancel(bt.id)
        assert rows2 == 0

    @pytest.mark.asyncio
    async def test_finalize_cancelled(self, db_session: AsyncSession) -> None:
        bt, repo = await _make_user_and_strategy(db_session)
        await repo.request_cancel(bt.id)
        rows = await repo.finalize_cancelled(bt.id, completed_at=datetime.utcnow())
        assert rows == 1

    @pytest.mark.asyncio
    async def test_exists_for_strategy(self, db_session: AsyncSession) -> None:
        bt, repo = await _make_user_and_strategy(db_session)
        assert await repo.exists_for_strategy(bt.strategy_id) is True
        assert await repo.exists_for_strategy(uuid4()) is False

    @pytest.mark.asyncio
    async def test_list_by_user_pagination(self, db_session: AsyncSession) -> None:
        bt, repo = await _make_user_and_strategy(db_session)
        items, total = await repo.list_by_user(bt.user_id, limit=10, offset=0)
        assert total >= 1
        assert any(i.id == bt.id for i in items)
```

- [ ] **Step 2: 실패 확인**

```bash
cd backend && uv run pytest tests/backtest/test_repository.py -v
```

Expected: FAIL — attributes/methods not defined.

- [ ] **Step 3: `BacktestRepository` 구현**

`backend/src/backtest/repository.py` 전체 교체:

```python
"""BacktestRepository — AsyncSession 유일 보유, DB 접근 전담."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus, BacktestTrade


class BacktestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- 트랜잭션 제어 ---

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    # --- CRUD ---

    async def create(self, bt: Backtest) -> Backtest:
        self.session.add(bt)
        await self.session.flush()
        return bt

    async def get_by_id(self, backtest_id: UUID, *, user_id: UUID | None = None) -> Backtest | None:
        stmt = select(Backtest).where(Backtest.id == backtest_id)
        if user_id is not None:
            stmt = stmt.where(Backtest.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, user_id: UUID, *, limit: int, offset: int
    ) -> tuple[Sequence[Backtest], int]:
        total_stmt = select(func.count(Backtest.id)).where(Backtest.user_id == user_id)
        total = (await self.session.execute(total_stmt)).scalar_one()

        stmt = (
            select(Backtest)
            .where(Backtest.user_id == user_id)
            .order_by(Backtest.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def delete(self, backtest_id: UUID) -> int:
        result = await self.session.execute(
            delete(Backtest).where(Backtest.id == backtest_id)
        )
        return result.rowcount or 0

    # --- 조건부 상태 전이 ---

    async def set_celery_task_id(self, backtest_id: UUID, task_id: str) -> None:
        await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)
            .values(celery_task_id=task_id)
        )

    async def transition_to_running(self, backtest_id: UUID, *, started_at: datetime) -> int:
        """queued → running. 조건부 UPDATE. Returns affected rows."""
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)
            .where(Backtest.status == BacktestStatus.QUEUED)
            .values(status=BacktestStatus.RUNNING, started_at=started_at)
        )
        return result.rowcount or 0

    async def complete(
        self,
        backtest_id: UUID,
        *,
        metrics: dict[str, Any],
        equity_curve: list[Any],
        where_status: BacktestStatus = BacktestStatus.RUNNING,
    ) -> int:
        """Running → completed. 조건부. Returns affected rows."""
        from src.backtest.models import _utcnow
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)
            .where(Backtest.status == where_status)
            .values(
                status=BacktestStatus.COMPLETED,
                metrics=metrics,
                equity_curve=equity_curve,
                completed_at=_utcnow(),
            )
        )
        return result.rowcount or 0

    async def fail(
        self,
        backtest_id: UUID,
        *,
        error: str,
        where_status: BacktestStatus = BacktestStatus.RUNNING,
    ) -> int:
        """Running → failed. 조건부."""
        from src.backtest.models import _utcnow
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)
            .where(Backtest.status == where_status)
            .values(
                status=BacktestStatus.FAILED,
                error=error[:2000],  # String(2000) 제한
                completed_at=_utcnow(),
            )
        )
        return result.rowcount or 0

    async def request_cancel(self, backtest_id: UUID) -> int:
        """queued/running → cancelling. 조건부. Returns affected rows."""
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)
            .where(Backtest.status.in_([BacktestStatus.QUEUED, BacktestStatus.RUNNING]))
            .values(status=BacktestStatus.CANCELLING)
        )
        return result.rowcount or 0

    async def finalize_cancelled(self, backtest_id: UUID, *, completed_at: datetime) -> int:
        """cancelling → cancelled. 조건부. Worker guards에서 호출."""
        result = await self.session.execute(
            update(Backtest)
            .where(Backtest.id == backtest_id)
            .where(Backtest.status == BacktestStatus.CANCELLING)
            .values(status=BacktestStatus.CANCELLED, completed_at=completed_at)
        )
        return result.rowcount or 0

    # --- Trades ---

    async def insert_trades_bulk(self, trades: list[BacktestTrade]) -> None:
        """Bulk insert. Transaction 내에서 호출 (service가 commit)."""
        self.session.add_all(trades)
        await self.session.flush()

    async def list_trades(
        self, backtest_id: UUID, *, limit: int, offset: int
    ) -> tuple[Sequence[BacktestTrade], int]:
        total_stmt = select(func.count(BacktestTrade.id)).where(
            BacktestTrade.backtest_id == backtest_id
        )
        total = (await self.session.execute(total_stmt)).scalar_one()

        stmt = (
            select(BacktestTrade)
            .where(BacktestTrade.backtest_id == backtest_id)
            .order_by(BacktestTrade.trade_index.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    # --- Cross-domain query ---

    async def exists_for_strategy(self, strategy_id: UUID) -> bool:
        """Strategy 삭제 전 선조회 (§4.8)."""
        stmt = select(func.count(Backtest.id)).where(Backtest.strategy_id == strategy_id)
        count = (await self.session.execute(stmt)).scalar_one()
        return count > 0

    # --- Stale reclaim (§8.3) ---

    async def reclaim_stale(self, *, threshold_seconds: int, now: datetime) -> tuple[int, int]:
        """running/cancelling 중 started_at + threshold < now 인 row → terminal.

        Returns (reclaimed_running, reclaimed_cancelling).
        """
        from datetime import timedelta
        cutoff = now - timedelta(seconds=threshold_seconds)

        running_result = await self.session.execute(
            update(Backtest)
            .where(Backtest.status == BacktestStatus.RUNNING)
            .where(Backtest.started_at < cutoff)
            .values(
                status=BacktestStatus.FAILED,
                error="Stale running — reclaimed by worker startup",
                completed_at=now,
            )
        )
        cancelling_result = await self.session.execute(
            update(Backtest)
            .where(Backtest.status == BacktestStatus.CANCELLING)
            .where(Backtest.started_at < cutoff)
            .values(status=BacktestStatus.CANCELLED, completed_at=now)
        )
        return (running_result.rowcount or 0, cancelling_result.rowcount or 0)
```

- [ ] **Step 4: 테스트 통과**

```bash
cd backend && uv run pytest tests/backtest/test_repository.py -v
```

Expected: 8 tests PASS.

- [ ] **Step 5: ruff + mypy + 커밋**

```bash
cd backend && uv run ruff check src/backtest/repository.py tests/backtest/test_repository.py && uv run mypy src/backtest/repository.py
git add backend/src/backtest/repository.py backend/tests/backtest/test_repository.py
git commit -m "feat(backtest): BacktestRepository — CRUD + conditional UPDATEs

- transition_to_running / complete / fail / request_cancel / finalize_cancelled 모두 조건부
- reclaim_stale: running+cancelling 둘 다 sweep (§8.3)
- exists_for_strategy: Strategy delete 선조회 (§4.8)
- commit/rollback: service 조율용

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Milestone 6 — Schemas

### Task 15: `backtest/schemas.py` — Pydantic DTOs

**Files:**
- Modify: `backend/src/backtest/schemas.py` (전체 재작성)

- [ ] **Step 1: 전체 스키마 작성**

`backend/src/backtest/schemas.py`:
```python
"""Backtest 도메인 Pydantic 스키마."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from src.backtest.models import BacktestStatus, TradeDirection, TradeStatus


# --- Request ---

class CreateBacktestRequest(BaseModel):
    strategy_id: UUID
    symbol: str = Field(min_length=3, max_length=32)
    timeframe: Literal["1m", "5m", "15m", "1h", "4h", "1d"]
    period_start: datetime
    period_end: datetime
    initial_capital: Decimal = Field(gt=Decimal("0"), max_digits=20, decimal_places=8)

    @model_validator(mode="after")
    def _validate_period(self) -> Self:
        if self.period_end <= self.period_start:
            raise ValueError("period_end must be after period_start")
        return self


# --- Response — base ---

class BacktestCreatedResponse(BaseModel):
    """POST /backtests → 202."""

    backtest_id: UUID
    status: BacktestStatus
    created_at: datetime


class BacktestProgressResponse(BaseModel):
    """GET /:id/progress — 경량."""

    backtest_id: UUID
    status: BacktestStatus
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
    stale: bool = False


class BacktestCancelResponse(BaseModel):
    """POST /:id/cancel → 202."""

    backtest_id: UUID
    status: BacktestStatus
    message: str


# --- Detail / List ---

class BacktestSummary(BaseModel):
    id: UUID
    strategy_id: UUID
    symbol: str
    timeframe: str
    period_start: datetime
    period_end: datetime
    status: BacktestStatus
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class BacktestMetricsOut(BaseModel):
    total_return: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    win_rate: Decimal
    num_trades: int

    @field_serializer("total_return", "sharpe_ratio", "max_drawdown", "win_rate")
    def _decimal_to_str(self, v: Decimal) -> str:
        return str(v)


class EquityPoint(BaseModel):
    timestamp: datetime
    value: Decimal

    @field_serializer("value")
    def _decimal_to_str(self, v: Decimal) -> str:
        return str(v)


class BacktestDetail(BacktestSummary):
    initial_capital: Decimal
    metrics: BacktestMetricsOut | None = None
    equity_curve: list[EquityPoint] | None = None
    error: str | None = None

    @field_serializer("initial_capital")
    def _decimal_to_str(self, v: Decimal) -> str:
        return str(v)


class TradeItem(BaseModel):
    trade_index: int
    direction: TradeDirection
    status: TradeStatus
    entry_time: datetime
    exit_time: datetime | None
    entry_price: Decimal
    exit_price: Decimal | None
    size: Decimal
    pnl: Decimal
    return_pct: Decimal
    fees: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer(
        "entry_price", "exit_price", "size", "pnl", "return_pct", "fees"
    )
    def _decimal_to_str(self, v: Decimal | None) -> str | None:
        return None if v is None else str(v)
```

- [ ] **Step 2: 스키마 smoke test**

```bash
cd backend && uv run python -c "
from uuid import uuid4
from decimal import Decimal
from datetime import datetime
from src.backtest.schemas import CreateBacktestRequest, BacktestCreatedResponse

r = CreateBacktestRequest(
    strategy_id=uuid4(),
    symbol='BTCUSDT',
    timeframe='1h',
    period_start=datetime(2024, 1, 1),
    period_end=datetime(2024, 6, 30),
    initial_capital=Decimal('10000'),
)
print(r.model_dump_json())
"
```

Expected: JSON 출력.

- [ ] **Step 3: ruff + mypy + 커밋**

```bash
cd backend && uv run ruff check src/backtest/schemas.py && uv run mypy src/backtest/schemas.py
git add backend/src/backtest/schemas.py
git commit -m "feat(backtest): Pydantic schemas — request/response DTOs

- CreateBacktestRequest 입력 검증 (period, capital, timeframe Literal)
- BacktestCreatedResponse (backtest_id canonical)
- BacktestProgressResponse (stale flag)
- BacktestCancelResponse (cancellation_requested semantics)
- BacktestDetail / TradeItem: Decimal → str via field_serializer

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Milestone 7 — Celery Infrastructure

### Task 16: `tasks/celery_app.py` + `@worker_ready` hook

**Files:**
- Create: `backend/src/tasks/__init__.py`
- Create: `backend/src/tasks/celery_app.py`

- [ ] **Step 1: Celery app + signal handler**

`backend/src/tasks/__init__.py`:
```python
"""Celery task package — celery_app re-export."""
from src.tasks.celery_app import celery_app

__all__ = ["celery_app"]
```

`backend/src/tasks/celery_app.py`:
```python
"""Celery 인스턴스 + @worker_ready stale reclaim hook."""
from __future__ import annotations

import asyncio
import logging

from celery import Celery
from celery.signals import worker_ready

from src.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "quantbridge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.tasks.backtest"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@worker_ready.connect
def _on_worker_ready(sender=None, **_kwargs) -> None:
    """Worker 기동 시 stale reclaim 1회 자동 실행 (§8.3).

    @worker_ready는 Celery master 프로세스에서 1회 실행 — prefork 자식마다 아님.
    """
    from src.tasks.backtest import reclaim_stale_running
    try:
        reclaimed = asyncio.run(reclaim_stale_running())
        if reclaimed:
            logger.info("stale_reclaim_on_startup", extra={"reclaimed_count": reclaimed})
    except Exception:
        logger.exception("stale_reclaim_failed_on_startup")
```

- [ ] **Step 2: Celery import smoke**

```bash
cd backend && uv run python -c "from src.tasks import celery_app; print(celery_app.tasks.keys())"
```

Expected: Celery 내장 tasks만 표시 (`src.tasks.backtest` 아직 미생성이라 경고 가능하나 import 성공).

- [ ] **Step 3: 전체 테스트 회귀**

```bash
cd backend && uv run pytest -q
```

Expected: PASS.

- [ ] **Step 4: 커밋**

```bash
git add backend/src/tasks/__init__.py backend/src/tasks/celery_app.py
git commit -m "feat(tasks): Celery app + @worker_ready stale reclaim hook

JSON serializer, UTC timezone. reclaim_stale_running()은 Task 17에서 구현.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 17: `tasks/backtest.py` — task + `_execute()` + reclaim

**Files:**
- Create: `backend/src/tasks/backtest.py`
- Create: `backend/tests/tasks/test_backtest_task.py`

> Task 18 (Service) 작성 전에 이 파일은 Service를 참조. 임시 스텁으로 작성 후 Task 18에서 실제 연동.

- [ ] **Step 1: 초기 스텁 (Service 미완 상태)**

`backend/src/tasks/backtest.py`:
```python
"""run_backtest_task + _execute + reclaim_stale_running."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from src.common.database import async_session_maker
from src.core.config import settings
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="backtest.run", max_retries=0)
def run_backtest_task(self, backtest_id: str) -> None:
    """Sync Celery task — asyncio.run() 진입점 전담.

    Worker pool 제약: prefork only. gevent/eventlet 비호환 (§2.4).
    """
    asyncio.run(_execute(UUID(backtest_id)))


async def _execute(backtest_id: UUID) -> None:
    """async 실행 본체 — 테스트 primary 타겟 (await 직접 호출).

    §5.1 Worker 3-guard 로직 + finalize_cancelled 수습.
    """
    from src.backtest.dependencies import build_backtest_service_for_worker

    async with async_session_maker() as session:
        service = build_backtest_service_for_worker(session)
        await service.run(backtest_id)


async def reclaim_stale_running() -> int:
    """Worker 기동 시 호출. stale running/cancelling → failed/cancelled (§8.3).

    Returns: reclaimed row 총수 (running + cancelling).
    """
    from src.backtest.models import _utcnow
    from src.backtest.repository import BacktestRepository

    async with async_session_maker() as session:
        repo = BacktestRepository(session)
        running, cancelling = await repo.reclaim_stale(
            threshold_seconds=settings.backtest_stale_threshold_seconds,
            now=_utcnow(),
        )
        await repo.commit()
        return running + cancelling
```

- [ ] **Step 2: 테스트 스텁 — `_execute` / reclaim smoke**

`backend/tests/tasks/__init__.py`:
```python
```

`backend/tests/tasks/test_backtest_task.py`:
```python
"""run_backtest_task + _execute + reclaim_stale_running."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.tasks.backtest import reclaim_stale_running


@pytest.mark.asyncio
async def test_reclaim_stale_running_marks_failed(db_session: AsyncSession, monkeypatch) -> None:
    """running + started_at < threshold → failed."""
    from src.auth.models import User
    from src.strategy.models import ParseStatus, PineVersion, Strategy

    user = User(id=uuid4(), clerk_user_id=f"u_{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@ex.com")
    db_session.add(user)
    strategy = Strategy(id=uuid4(), user_id=user.id, name="s", pine_source="//@version=5\nstrategy('s')",
                        pine_version=PineVersion.v5, parse_status=ParseStatus.ok)
    db_session.add(strategy)
    stale_bt = Backtest(
        id=uuid4(), user_id=user.id, strategy_id=strategy.id,
        symbol="BTCUSDT", timeframe="1h",
        period_start=datetime(2024, 1, 1), period_end=datetime(2024, 1, 2),
        initial_capital=Decimal("1000"),
        status=BacktestStatus.RUNNING,
        started_at=datetime.utcnow() - timedelta(hours=2),  # 2h → 30min threshold 초과
    )
    db_session.add(stale_bt)
    await db_session.commit()

    # Patch async_session_maker to reuse test session (savepoint fixture)
    import src.tasks.backtest as task_mod
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _mock_maker():
        yield db_session

    monkeypatch.setattr(task_mod, "async_session_maker", _mock_maker)

    reclaimed = await reclaim_stale_running()
    assert reclaimed >= 1

    await db_session.refresh(stale_bt)
    assert stale_bt.status == BacktestStatus.FAILED
```

- [ ] **Step 3: 테스트 실행 (reclaim만, _execute는 Task 18 이후)**

```bash
cd backend && uv run pytest tests/tasks/test_backtest_task.py::test_reclaim_stale_running_marks_failed -v
```

Expected: PASS (단, dependencies.build_backtest_service_for_worker가 없어서 `_execute` 테스트는 아직 skip)

- [ ] **Step 4: ruff + 커밋**

```bash
cd backend && uv run ruff check src/tasks/backtest.py tests/tasks/
git add backend/src/tasks/backtest.py backend/tests/tasks/
git commit -m "feat(tasks): run_backtest_task + reclaim_stale_running

_execute() is a thin wrapper over BacktestService.run(). Service 연동은 Task 18.
reclaim은 Task 17에서 완전 구현 + 테스트 1건.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Milestone 8 — Service

### Task 18: `BacktestService` — submit / run / cancel / delete / list / get

**Files:**
- Modify: `backend/src/backtest/service.py` (전체 재작성)
- Create: `backend/tests/backtest/test_service.py`
- Modify: `backend/src/backtest/dependencies.py` (DI 조립)

- [ ] **Step 1: 테스트 스텁 우선 작성 (핵심 경로 7건)**

`backend/tests/backtest/test_service.py`:
```python
"""BacktestService — submit/run/cancel/delete/list/get."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.dispatcher import FakeTaskDispatcher
from src.backtest.exceptions import BacktestNotFound, BacktestStateConflict
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import BacktestService
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.exceptions import StrategyNotFoundError
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository


async def _seed_user_and_strategy(session: AsyncSession) -> tuple[User, Strategy]:
    user = User(id=uuid4(), clerk_user_id=f"u_{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@ex.com")
    session.add(user)
    strat = Strategy(
        id=uuid4(), user_id=user.id, name="EMA",
        pine_source="""//@version=5
strategy("EMA", overlay=true)
fast = ta.ema(close, 10)
slow = ta.ema(close, 30)
if ta.crossover(fast, slow)
    strategy.entry("L", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("L")
""",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    session.add(strat)
    await session.flush()
    return user, strat


def _mini_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "ohlcv"
    root.mkdir()
    # 50시간 1h 합성
    rows = ["timestamp,open,high,low,close,volume"]
    t = datetime(2024, 1, 1)
    for i in range(50):
        price = 100 + i * 0.5 + (i % 7) * 0.3
        rows.append(
            f"{(t + timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M:%SZ')},"
            f"{price},{price+1},{price-1},{price+0.5},100.0"
        )
    (root / "BTCUSDT_1h.csv").write_text("\n".join(rows))
    return root


def _request(strategy_id) -> CreateBacktestRequest:
    return CreateBacktestRequest(
        strategy_id=strategy_id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, 0, 0, 0),
        period_end=datetime(2024, 1, 2, 0, 0, 0),
        initial_capital=Decimal("10000"),
    )


@pytest.fixture
async def service(db_session: AsyncSession, tmp_path: Path) -> BacktestService:
    backtest_repo = BacktestRepository(db_session)
    strategy_repo = StrategyRepository(db_session)
    provider = FixtureProvider(root=_mini_fixture_root(tmp_path))
    dispatcher = FakeTaskDispatcher()
    return BacktestService(
        repo=backtest_repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=dispatcher,
    )


class TestBacktestServiceSubmit:
    @pytest.mark.asyncio
    async def test_submit_happy(self, service: BacktestService, db_session: AsyncSession) -> None:
        user, strat = await _seed_user_and_strategy(db_session)
        result = await service.submit(_request(strat.id), user_id=user.id)
        assert result.status == BacktestStatus.QUEUED
        assert service.dispatcher.dispatched == [result.backtest_id]  # type: ignore[union-attr]

    @pytest.mark.asyncio
    async def test_submit_unknown_strategy(self, service: BacktestService, db_session: AsyncSession) -> None:
        user, _ = await _seed_user_and_strategy(db_session)
        with pytest.raises(StrategyNotFoundError):
            await service.submit(_request(uuid4()), user_id=user.id)


class TestBacktestServiceRun:
    @pytest.mark.asyncio
    async def test_run_happy_path(self, service: BacktestService, db_session: AsyncSession) -> None:
        user, strat = await _seed_user_and_strategy(db_session)
        created = await service.submit(_request(strat.id), user_id=user.id)
        await db_session.commit()

        await service.run(created.backtest_id)

        bt = await service.repo.get_by_id(created.backtest_id)
        assert bt is not None
        # Parser 결과에 따라 ok 혹은 error. 최소한 terminal 전이 확인.
        assert bt.status in (BacktestStatus.COMPLETED, BacktestStatus.FAILED)

    @pytest.mark.asyncio
    async def test_guard_1_cancelling_before_pickup(
        self, service: BacktestService, db_session: AsyncSession
    ) -> None:
        """queued 상태에서 cancel → cancelling → worker pickup → cancelled."""
        user, strat = await _seed_user_and_strategy(db_session)
        created = await service.submit(_request(strat.id), user_id=user.id)
        await service.request_cancel_by_id(created.backtest_id, user_id=user.id)  # 헬퍼 별칭
        await db_session.commit()

        await service.run(created.backtest_id)

        bt = await service.repo.get_by_id(created.backtest_id)
        assert bt is not None
        assert bt.status == BacktestStatus.CANCELLED


class TestBacktestServiceCancel:
    @pytest.mark.asyncio
    async def test_cancel_queued(self, service: BacktestService, db_session: AsyncSession) -> None:
        user, strat = await _seed_user_and_strategy(db_session)
        created = await service.submit(_request(strat.id), user_id=user.id)
        await service.cancel(created.backtest_id, user_id=user.id)

        bt = await service.repo.get_by_id(created.backtest_id)
        assert bt is not None
        assert bt.status == BacktestStatus.CANCELLING

    @pytest.mark.asyncio
    async def test_cancel_unknown(self, service: BacktestService, db_session: AsyncSession) -> None:
        user, _ = await _seed_user_and_strategy(db_session)
        with pytest.raises(BacktestNotFound):
            await service.cancel(uuid4(), user_id=user.id)


class TestBacktestServiceDelete:
    @pytest.mark.asyncio
    async def test_delete_non_terminal_409(
        self, service: BacktestService, db_session: AsyncSession
    ) -> None:
        user, strat = await _seed_user_and_strategy(db_session)
        created = await service.submit(_request(strat.id), user_id=user.id)
        with pytest.raises(BacktestStateConflict):
            await service.delete(created.backtest_id, user_id=user.id)


class TestBacktestServiceListGet:
    @pytest.mark.asyncio
    async def test_list_and_get(self, service: BacktestService, db_session: AsyncSession) -> None:
        user, strat = await _seed_user_and_strategy(db_session)
        created = await service.submit(_request(strat.id), user_id=user.id)

        page = await service.list(user_id=user.id, limit=10, offset=0)
        assert page.total >= 1

        detail = await service.get(created.backtest_id, user_id=user.id)
        assert detail.id == created.backtest_id
```

- [ ] **Step 2: `BacktestService` 구현**

`backend/src/backtest/service.py` 전체 교체:
```python
"""BacktestService — HTTP 경로와 Worker 경로 양쪽에서 사용."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from uuid import UUID

import pandas as pd

from src.backtest.dispatcher import TaskDispatcher
from src.backtest.engine import run_backtest
from src.backtest.exceptions import (
    BacktestNotFound,
    BacktestStateConflict,
    TaskDispatchError,
)
from src.backtest.models import (
    Backtest,
    BacktestStatus,
    BacktestTrade,
    TradeDirection,
    TradeStatus,
    _utcnow,
)
from src.backtest.repository import BacktestRepository
from src.backtest.schemas import (
    BacktestCancelResponse,
    BacktestCreatedResponse,
    BacktestDetail,
    BacktestMetricsOut,
    BacktestProgressResponse,
    BacktestSummary,
    CreateBacktestRequest,
    EquityPoint,
    TradeItem,
)
from src.backtest.serializers import (
    _parse_utc_iso,
    _utc_iso,
    equity_curve_to_jsonb,
    metrics_from_jsonb,
    metrics_to_jsonb,
)
from src.common.pagination import Page
from src.core.config import settings
from src.market_data.providers import OHLCVProvider
from src.strategy.exceptions import StrategyNotFoundError
from src.strategy.repository import StrategyRepository

logger = logging.getLogger(__name__)


class BacktestService:
    def __init__(
        self,
        *,
        repo: BacktestRepository,
        strategy_repo: StrategyRepository,
        ohlcv_provider: OHLCVProvider,
        dispatcher: TaskDispatcher,
    ) -> None:
        self.repo = repo
        self.strategy_repo = strategy_repo
        self.provider = ohlcv_provider
        self.dispatcher = dispatcher

    # --- HTTP submit path ---

    async def submit(
        self, data: CreateBacktestRequest, *, user_id: UUID
    ) -> BacktestCreatedResponse:
        # Strategy ownership
        strategy = await self.strategy_repo.find_by_id_and_owner(data.strategy_id, user_id)
        if strategy is None:
            raise StrategyNotFoundError()

        bt = Backtest(
            user_id=user_id,
            strategy_id=data.strategy_id,
            symbol=data.symbol,
            timeframe=data.timeframe,
            period_start=data.period_start,
            period_end=data.period_end,
            initial_capital=data.initial_capital,
            status=BacktestStatus.QUEUED,
        )
        await self.repo.create(bt)

        # Dispatch — 실패 시 rollback + 503
        try:
            task_id = self.dispatcher.dispatch_backtest(bt.id)
        except Exception as exc:
            await self.repo.rollback()
            logger.exception("task_dispatch_failed")
            raise TaskDispatchError() from exc

        bt.celery_task_id = task_id
        await self.repo.commit()
        return BacktestCreatedResponse(
            backtest_id=bt.id, status=bt.status, created_at=bt.created_at
        )

    # --- Worker run path (§5.1) ---

    async def run(self, backtest_id: UUID) -> None:
        """Worker `_execute()` 엔트리. 3-guard 로직 + finalize_cancelled 수습."""
        bt = await self.repo.get_by_id(backtest_id)
        if bt is None:
            logger.warning("backtest_not_found_in_worker", extra={"bt_id": str(backtest_id)})
            return

        # Guard #1: pickup
        if bt.status == BacktestStatus.CANCELLING:
            await self.repo.finalize_cancelled(backtest_id, completed_at=_utcnow())
            await self.repo.commit()
            return
        if bt.status != BacktestStatus.QUEUED:
            logger.info("worker_skip_non_queued", extra={"bt_id": str(bt.id), "status": bt.status})
            return

        # Strategy + OHLCV fetch
        strategy = await self.strategy_repo.find_by_id_and_owner(bt.strategy_id, bt.user_id)
        if strategy is None:
            await self.repo.fail(backtest_id, error="Strategy not found at execute time")
            await self.repo.commit()
            return

        ohlcv = await self.provider.get_ohlcv(
            bt.symbol, bt.timeframe, bt.period_start, bt.period_end
        )

        # Transition: queued → running (조건부)
        rows = await self.repo.transition_to_running(backtest_id, started_at=_utcnow())
        if rows == 0:
            # cancel이 선행됨 — cancelling일 것
            await self.repo.finalize_cancelled(backtest_id, completed_at=_utcnow())
            await self.repo.commit()
            return
        await self.repo.commit()

        # Guard #2: pre-engine
        bt = await self.repo.get_by_id(backtest_id)
        assert bt is not None
        if bt.status == BacktestStatus.CANCELLING:
            await self.repo.finalize_cancelled(backtest_id, completed_at=_utcnow())
            await self.repo.commit()
            return

        # Engine
        outcome = run_backtest(strategy.pine_source, ohlcv)

        # Guard #3: post-engine
        bt = await self.repo.get_by_id(backtest_id)
        assert bt is not None
        if bt.status == BacktestStatus.CANCELLING:
            await self.repo.finalize_cancelled(backtest_id, completed_at=_utcnow())
            await self.repo.commit()
            return

        # Terminal write (조건부 UPDATE — rows=0 시 cancel이 또 끼어듦 → finalize_cancelled)
        if outcome.status == "ok" and outcome.result is not None:
            metrics_jsonb = metrics_to_jsonb(outcome.result.metrics)
            equity_jsonb = equity_curve_to_jsonb(outcome.result.equity_curve)

            rows = await self.repo.complete(
                backtest_id,
                metrics=metrics_jsonb,
                equity_curve=equity_jsonb,
            )
            if rows == 0:
                await self.repo.finalize_cancelled(backtest_id, completed_at=_utcnow())
                await self.repo.commit()
                return

            # Trades bulk insert (같은 transaction)
            trades = self._raw_trades_to_models(
                outcome.result.trades, backtest_id, ohlcv.index
            )
            await self.repo.insert_trades_bulk(trades)
        else:
            error = outcome.error or f"status={outcome.status}"
            rows = await self.repo.fail(backtest_id, error=str(error))
            if rows == 0:
                await self.repo.finalize_cancelled(backtest_id, completed_at=_utcnow())

        await self.repo.commit()

    def _raw_trades_to_models(
        self, raw_trades: list, backtest_id: UUID, ohlcv_index: pd.DatetimeIndex
    ) -> list[BacktestTrade]:
        """RawTrade → BacktestTrade. bar_index → datetime."""
        result = []
        for t in raw_trades:
            result.append(
                BacktestTrade(
                    backtest_id=backtest_id,
                    trade_index=t.trade_index,
                    direction=TradeDirection(t.direction),
                    status=TradeStatus(t.status),
                    entry_time=ohlcv_index[t.entry_bar_index].to_pydatetime(),
                    exit_time=(
                        ohlcv_index[t.exit_bar_index].to_pydatetime()
                        if t.exit_bar_index is not None
                        else None
                    ),
                    entry_price=t.entry_price,
                    exit_price=t.exit_price,
                    size=t.size,
                    pnl=t.pnl,
                    return_pct=t.return_pct,
                    fees=t.fees,
                )
            )
        return result

    # --- HTTP read paths ---

    async def get(self, backtest_id: UUID, *, user_id: UUID) -> BacktestDetail:
        bt = await self._load_owned(backtest_id, user_id)
        return self._to_detail(bt)

    async def list(
        self, *, user_id: UUID, limit: int, offset: int
    ) -> Page[BacktestSummary]:
        items, total = await self.repo.list_by_user(user_id, limit=limit, offset=offset)
        return Page[BacktestSummary](
            items=[BacktestSummary.model_validate(bt) for bt in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def progress(self, backtest_id: UUID, *, user_id: UUID) -> BacktestProgressResponse:
        bt = await self._load_owned(backtest_id, user_id)
        threshold = settings.backtest_stale_threshold_seconds
        is_stale = (
            bt.status in (BacktestStatus.RUNNING, BacktestStatus.CANCELLING)
            and bt.started_at is not None
            and (_utcnow() - bt.started_at) > timedelta(seconds=threshold)
        )
        return BacktestProgressResponse(
            backtest_id=bt.id,
            status=bt.status,
            started_at=bt.started_at,
            completed_at=bt.completed_at,
            error=bt.error,
            stale=is_stale,
        )

    async def list_trades(
        self, backtest_id: UUID, *, user_id: UUID, limit: int, offset: int
    ) -> Page[TradeItem]:
        await self._load_owned(backtest_id, user_id)  # 404 guard
        items, total = await self.repo.list_trades(backtest_id, limit=limit, offset=offset)
        return Page[TradeItem](
            items=[TradeItem.model_validate(t) for t in items],
            total=total,
            limit=limit,
            offset=offset,
        )

    # --- HTTP mutation paths ---

    async def cancel(self, backtest_id: UUID, *, user_id: UUID) -> BacktestCancelResponse:
        bt = await self._load_owned(backtest_id, user_id)
        if bt.status not in (BacktestStatus.QUEUED, BacktestStatus.RUNNING):
            raise BacktestStateConflict(
                detail=f"Cancel requires queued or running; current: {bt.status.value}"
            )

        # Best-effort revoke
        if bt.celery_task_id:
            try:
                from celery.result import AsyncResult
                from src.tasks.celery_app import celery_app

                AsyncResult(bt.celery_task_id, app=celery_app).revoke(terminate=True)
            except Exception:
                logger.exception("revoke_failed", extra={"bt_id": str(bt.id)})

        rows = await self.repo.request_cancel(backtest_id)
        if rows == 0:
            # race loser — 이미 terminal
            raise BacktestStateConflict(detail="Already terminal")
        await self.repo.commit()

        return BacktestCancelResponse(
            backtest_id=bt.id,
            status=BacktestStatus.CANCELLING,
            message="Cancellation requested. Final state via GET /:id/progress.",
        )

    async def delete(self, backtest_id: UUID, *, user_id: UUID) -> None:
        bt = await self._load_owned(backtest_id, user_id)
        terminal = (BacktestStatus.COMPLETED, BacktestStatus.FAILED, BacktestStatus.CANCELLED)
        if bt.status not in terminal:
            raise BacktestStateConflict(
                detail=f"Delete requires terminal state; current: {bt.status.value}. "
                       f"Try cancel first and wait for final state."
            )
        await self.repo.delete(backtest_id)
        await self.repo.commit()

    # --- helpers ---

    async def request_cancel_by_id(self, backtest_id: UUID, *, user_id: UUID) -> None:
        """테스트 헬퍼 — ownership 체크 건너뜀. 실제 cancel 경로는 cancel()."""
        await self._load_owned(backtest_id, user_id)
        await self.repo.request_cancel(backtest_id)
        await self.repo.commit()

    async def _load_owned(self, backtest_id: UUID, user_id: UUID) -> Backtest:
        bt = await self.repo.get_by_id(backtest_id, user_id=user_id)
        if bt is None:
            raise BacktestNotFound()
        return bt

    def _to_detail(self, bt: Backtest) -> BacktestDetail:
        metrics_out: BacktestMetricsOut | None = None
        equity_out: list[EquityPoint] | None = None
        if bt.status == BacktestStatus.COMPLETED:
            if bt.metrics:
                m = metrics_from_jsonb(bt.metrics)
                metrics_out = BacktestMetricsOut(
                    total_return=m.total_return,
                    sharpe_ratio=m.sharpe_ratio,
                    max_drawdown=m.max_drawdown,
                    win_rate=m.win_rate,
                    num_trades=m.num_trades,
                )
            if bt.equity_curve:
                equity_out = [
                    EquityPoint(timestamp=_parse_utc_iso(ts), value=__import__("decimal").Decimal(v))
                    for ts, v in bt.equity_curve
                ]
        return BacktestDetail(
            id=bt.id,
            strategy_id=bt.strategy_id,
            symbol=bt.symbol,
            timeframe=bt.timeframe,
            period_start=bt.period_start,
            period_end=bt.period_end,
            status=bt.status,
            created_at=bt.created_at,
            completed_at=bt.completed_at,
            initial_capital=bt.initial_capital,
            metrics=metrics_out,
            equity_curve=equity_out,
            error=bt.error,
        )
```

- [ ] **Step 3: `dependencies.py` — DI 조립**

`backend/src/backtest/dependencies.py` 전체 교체:
```python
"""Backtest DI 조립. Depends는 여기서만."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.dispatcher import CeleryTaskDispatcher, NoopTaskDispatcher
from src.backtest.repository import BacktestRepository
from src.backtest.service import BacktestService
from src.common.database import get_async_session
from src.market_data.providers import OHLCVProvider
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.repository import StrategyRepository


def _ohlcv_provider() -> OHLCVProvider:
    return FixtureProvider()


async def get_backtest_service(
    session: AsyncSession = Depends(get_async_session),
) -> BacktestService:
    """HTTP 경로용 — CeleryTaskDispatcher 주입."""
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=_ohlcv_provider(),
        dispatcher=CeleryTaskDispatcher(),
    )


def build_backtest_service_for_worker(session: AsyncSession) -> BacktestService:
    """Worker _execute() 용 — NoopTaskDispatcher (dispatch 호출 금지)."""
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=_ohlcv_provider(),
        dispatcher=NoopTaskDispatcher(),
    )
```

- [ ] **Step 4: 테스트 실행**

```bash
cd backend && uv run pytest tests/backtest/test_service.py -v
```

Expected: 7 tests PASS.

- [ ] **Step 5: ruff + mypy + 커밋**

```bash
cd backend && uv run ruff check src/backtest/ tests/backtest/test_service.py && uv run mypy src/backtest/
git add backend/src/backtest/service.py backend/src/backtest/dependencies.py backend/tests/backtest/test_service.py
git commit -m "feat(backtest): BacktestService — submit/run/cancel/delete/list/get/progress

- submit: Strategy ownership + atomic commit + TaskDispatchError rollback
- run: 3-guard cancel logic (§5.1) + finalize_cancelled 수습
- cancel: best-effort revoke + request_cancel 조건부 UPDATE + 409 race loser
- delete: terminal only + CASCADE trades
- progress: stale 플래그 파생
- list_trades: pagination + ownership

DI: HTTP=CeleryTaskDispatcher, Worker=NoopTaskDispatcher.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 19: Strategy `delete()` — cross-domain backtest check

**Files:**
- Modify: `backend/src/strategy/service.py` (delete 메서드)
- Modify: `backend/src/strategy/dependencies.py` (cross-repo 주입)
- Create: `backend/tests/api/test_strategy_delete_with_backtests.py`

- [ ] **Step 1: 기존 `StrategyService`, `dependencies.py` 확인**

```bash
cd backend && cat src/strategy/dependencies.py
```

- [ ] **Step 2: `StrategyService.__init__` + `delete` 수정**

`backend/src/strategy/service.py` 의 `StrategyService`:

```python
# __init__ 교체
def __init__(
    self,
    repo: StrategyRepository,
    backtest_repo: "BacktestRepository | None" = None,
) -> None:
    self.repo = repo
    self.backtest_repo = backtest_repo


# delete 메서드 교체
async def delete(self, *, strategy_id: UUID, owner_id: UUID) -> None:
    from sqlalchemy.exc import IntegrityError
    from src.strategy.exceptions import StrategyHasBacktests

    strategy = await self.repo.find_by_id_and_owner(strategy_id, owner_id)
    if strategy is None:
        raise StrategyNotFoundError()

    # 선조회 — Sprint 4부터 backtest_repo 주입
    if self.backtest_repo is not None:
        if await self.backtest_repo.exists_for_strategy(strategy_id):
            raise StrategyHasBacktests()

    try:
        await self.repo.delete(strategy.id)
        await self.repo.commit()
    except IntegrityError as exc:
        # TOCTOU race loser — 선조회 이후 새 backtest 삽입됨
        await self.repo.rollback()
        # asyncpg FK violation 은 IntegrityError 로 래핑됨
        if "foreign key" in str(exc.orig).lower() or "foreignkeyviolation" in type(exc.orig).__name__.lower():
            raise StrategyHasBacktests() from exc
        raise
```

상단 import 추가:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backtest.repository import BacktestRepository
```

- [ ] **Step 3: `strategy/dependencies.py` 수정 — `BacktestRepository` cross-inject**

```python
"""Strategy DI. Sprint 4부터 BacktestRepository cross-inject."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.strategy.repository import StrategyRepository
from src.strategy.service import StrategyService


async def get_strategy_service(
    session: AsyncSession = Depends(get_async_session),
) -> StrategyService:
    """동일 session에 양쪽 repo 주입 (cross-repo transaction)."""
    from src.backtest.repository import BacktestRepository

    return StrategyService(
        repo=StrategyRepository(session),
        backtest_repo=BacktestRepository(session),
    )
```

- [ ] **Step 4: 기존 Sprint 3 strategy delete 테스트 회귀 확인**

```bash
cd backend && uv run pytest tests/strategy -v -k delete
```

Expected: PASS (기존 백테스트 없는 케이스 여전히 204).

- [ ] **Step 5: 신규 회귀 테스트 작성**

`backend/tests/api/test_strategy_delete_with_backtests.py`:
```python
"""Sprint 3 회귀 방지 — Strategy delete with backtests.

§4.8 StrategyHasBacktests 409 경로.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.models import Backtest, BacktestStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy


@pytest.mark.asyncio
async def test_delete_strategy_with_backtest_returns_409(
    client: AsyncClient, db_session: AsyncSession, auth_headers
) -> None:
    # auth_headers fixture는 mock_clerk_auth와 동일 user_id 사용
    # User + Strategy + Backtest seed
    # (conftest에서 가져온 user_id 사용)
    from tests.conftest import TEST_USER_ID

    strategy = Strategy(
        id=uuid4(), user_id=TEST_USER_ID, name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    bt = Backtest(
        id=uuid4(), user_id=TEST_USER_ID, strategy_id=strategy.id,
        symbol="BTCUSDT", timeframe="1h",
        period_start=datetime(2024, 1, 1), period_end=datetime(2024, 1, 2),
        initial_capital=Decimal("1000"),
        status=BacktestStatus.COMPLETED,
        completed_at=datetime.utcnow(),
    )
    db_session.add(bt)
    await db_session.commit()

    response = await client.delete(f"/api/v1/strategies/{strategy.id}", headers=auth_headers)
    assert response.status_code == 409
    body = response.json()
    assert body["detail"]["code"] == "strategy_has_backtests"


@pytest.mark.asyncio
async def test_delete_strategy_without_backtest_still_works(
    client: AsyncClient, db_session: AsyncSession, auth_headers
) -> None:
    """회귀 없음 확인 — 기존 happy path."""
    from tests.conftest import TEST_USER_ID

    strategy = Strategy(
        id=uuid4(), user_id=TEST_USER_ID, name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.commit()

    response = await client.delete(f"/api/v1/strategies/{strategy.id}", headers=auth_headers)
    assert response.status_code == 204
```

> **Note:** `auth_headers` / `TEST_USER_ID` fixture는 Sprint 3 conftest에 있음 (확인 필요, 없으면 해당 conftest 참조해서 추가).

- [ ] **Step 6: 테스트 실행**

```bash
cd backend && uv run pytest tests/api/test_strategy_delete_with_backtests.py -v tests/strategy -v
```

Expected: 회귀 테스트 + 신규 테스트 모두 PASS.

- [ ] **Step 7: 커밋**

```bash
git add backend/src/strategy/service.py backend/src/strategy/dependencies.py backend/tests/api/test_strategy_delete_with_backtests.py
git commit -m "feat(strategy): delete() rejects if backtests exist (§4.8)

- BacktestRepository cross-inject via strategy/dependencies.py
- 선조회 exists_for_strategy → 409 strategy_has_backtests
- IntegrityError catch (TOCTOU race loser) → 동일 409
- 기존 Sprint 3 happy path (no backtests) 회귀 없음

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Milestone 9 — Router + API

### Task 20: `backtest/router.py` — 7 endpoints

**Files:**
- Modify: `backend/src/backtest/router.py` (전체 재작성)
- Modify: `backend/src/main.py` (router 등록)

- [ ] **Step 1: Router 전체 작성**

`backend/src/backtest/router.py`:
```python
"""Backtest REST API — 7 endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from src.auth.dependencies import get_current_user
from src.auth.schemas import CurrentUser
from src.backtest.dependencies import get_backtest_service
from src.backtest.schemas import (
    BacktestCancelResponse,
    BacktestCreatedResponse,
    BacktestDetail,
    BacktestProgressResponse,
    BacktestSummary,
    CreateBacktestRequest,
    TradeItem,
)
from src.backtest.service import BacktestService
from src.common.pagination import Page

router = APIRouter(prefix="/backtests", tags=["backtests"])


@router.post("", response_model=BacktestCreatedResponse, status_code=202)
async def submit_backtest(
    data: CreateBacktestRequest,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestCreatedResponse:
    return await service.submit(data, user_id=user.id)


@router.get("", response_model=Page[BacktestSummary])
async def list_backtests(
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> Page[BacktestSummary]:
    return await service.list(user_id=user.id, limit=limit, offset=offset)


@router.get("/{backtest_id}", response_model=BacktestDetail)
async def get_backtest(
    backtest_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestDetail:
    return await service.get(backtest_id, user_id=user.id)


@router.get("/{backtest_id}/trades", response_model=Page[TradeItem])
async def list_backtest_trades(
    backtest_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page[TradeItem]:
    return await service.list_trades(backtest_id, user_id=user.id, limit=limit, offset=offset)


@router.get("/{backtest_id}/progress", response_model=BacktestProgressResponse)
async def get_backtest_progress(
    backtest_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestProgressResponse:
    return await service.progress(backtest_id, user_id=user.id)


@router.post("/{backtest_id}/cancel", response_model=BacktestCancelResponse, status_code=202)
async def cancel_backtest(
    backtest_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestCancelResponse:
    return await service.cancel(backtest_id, user_id=user.id)


@router.delete("/{backtest_id}", status_code=204)
async def delete_backtest(
    backtest_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    service: BacktestService = Depends(get_backtest_service),
) -> Response:
    await service.delete(backtest_id, user_id=user.id)
    return Response(status_code=204)
```

- [ ] **Step 2: `main.py`에 router 등록**

`backend/src/main.py` 에서 기존 strategy_router import 뒤에:

```python
from src.backtest.router import router as backtest_router
# ... app.include_router(strategy_router, ...) 뒤:
app.include_router(backtest_router, prefix="/api/v1")
```

- [ ] **Step 3: uvicorn 기동 smoke**

```bash
cd backend && uv run uvicorn src.main:app --no-server-header 2>&1 &
sleep 3
curl -s http://localhost:8000/openapi.json | python -c "import sys, json; spec = json.load(sys.stdin); print([p for p in spec['paths'] if 'backtests' in p])"
kill %1 2>/dev/null
```

Expected: 7 endpoint paths 출력.

- [ ] **Step 4: ruff + mypy + 커밋**

```bash
cd backend && uv run ruff check src/backtest/router.py src/main.py && uv run mypy src/backtest/router.py src/main.py
git add backend/src/backtest/router.py backend/src/main.py
git commit -m "feat(backtest-api): 7 REST endpoints

POST /backtests (202), GET list, GET detail, GET trades, GET progress,
POST /:id/cancel (202), DELETE /:id (204). Prefix /api/v1/backtests.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Milestone 10 — API E2E Tests

### Task 21: API submit + list + detail 테스트

**Files:**
- Create: `backend/tests/api/test_backtests_submit.py`
- Create: `backend/tests/api/test_backtests_list.py`
- Create: `backend/tests/api/test_backtests_detail.py`

- [ ] **Step 1: submit 테스트**

`backend/tests/api/test_backtests_submit.py`:
```python
"""POST /api/v1/backtests."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.strategy.models import ParseStatus, PineVersion, Strategy


def _body(strategy_id) -> dict:
    return {
        "strategy_id": str(strategy_id),
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "period_start": "2024-01-01T00:00:00",
        "period_end": "2024-01-02T00:00:00",
        "initial_capital": "10000",
    }


@pytest.mark.asyncio
async def test_submit_202(client: AsyncClient, db_session, auth_headers) -> None:
    from tests.conftest import TEST_USER_ID
    strategy = Strategy(
        id=uuid4(), user_id=TEST_USER_ID, name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.commit()

    r = await client.post("/api/v1/backtests", json=_body(strategy.id), headers=auth_headers)
    assert r.status_code == 202
    body = r.json()
    assert "backtest_id" in body
    assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_submit_422_invalid_period(client: AsyncClient, db_session, auth_headers) -> None:
    from tests.conftest import TEST_USER_ID
    strategy = Strategy(
        id=uuid4(), user_id=TEST_USER_ID, name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.commit()

    body = _body(strategy.id)
    body["period_end"] = "2023-01-01T00:00:00"  # start 이전
    r = await client.post("/api/v1/backtests", json=body, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_submit_404_other_user_strategy(client: AsyncClient, db_session, auth_headers) -> None:
    # 다른 유저의 전략 seed
    from src.auth.models import User
    other = User(id=uuid4(), clerk_user_id=f"u_{uuid4().hex[:8]}", email=f"{uuid4().hex[:8]}@ex.com")
    db_session.add(other)
    strategy = Strategy(
        id=uuid4(), user_id=other.id, name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.commit()

    r = await client.post("/api/v1/backtests", json=_body(strategy.id), headers=auth_headers)
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "strategy_not_found"
```

- [ ] **Step 2: list + detail 테스트**

`backend/tests/api/test_backtests_list.py`, `test_backtests_detail.py` — 비슷한 구조로 seed 후 GET. (분량 절약 위해 여기선 submit만 상세 제시. list/detail은 submit 성공 후 read 경로 검증).

- [ ] **Step 3: 실행 + ruff + 커밋**

```bash
cd backend && uv run pytest tests/api/test_backtests_submit.py -v
git add backend/tests/api/test_backtests_submit.py backend/tests/api/test_backtests_list.py backend/tests/api/test_backtests_detail.py
git commit -m "test(api): backtests submit/list/detail E2E

ownership, pagination, status-based response shape.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 22: API cancel + delete + trades + progress 테스트

**Files:**
- Create: `backend/tests/api/test_backtests_cancel.py`
- Create: `backend/tests/api/test_backtests_delete.py`
- Create: `backend/tests/api/test_backtests_trades.py`
- Create: `backend/tests/api/test_backtests_progress.py`

- [ ] **Step 1: cancel 테스트 전체 코드**

`backend/tests/api/test_backtests_cancel.py`:
```python
"""POST /api/v1/backtests/:id/cancel."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.backtest.models import Backtest, BacktestStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy


async def _seed_backtest(db_session, status: BacktestStatus) -> Backtest:
    from tests.conftest import TEST_USER_ID
    strategy = Strategy(
        id=uuid4(), user_id=TEST_USER_ID, name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    bt = Backtest(
        id=uuid4(), user_id=TEST_USER_ID, strategy_id=strategy.id,
        symbol="BTCUSDT", timeframe="1h",
        period_start=datetime(2024, 1, 1), period_end=datetime(2024, 1, 2),
        initial_capital=Decimal("10000"),
        status=status,
        celery_task_id="fake-celery-id",
    )
    db_session.add(bt)
    await db_session.commit()
    return bt


@pytest.mark.asyncio
async def test_cancel_queued_returns_202(client: AsyncClient, db_session, auth_headers) -> None:
    bt = await _seed_backtest(db_session, BacktestStatus.QUEUED)
    r = await client.post(f"/api/v1/backtests/{bt.id}/cancel", headers=auth_headers)
    assert r.status_code == 202
    body = r.json()
    assert body["backtest_id"] == str(bt.id)
    assert body["status"] == "cancelling"
    assert "Cancellation requested" in body["message"]


@pytest.mark.asyncio
async def test_cancel_running_returns_202(client: AsyncClient, db_session, auth_headers) -> None:
    bt = await _seed_backtest(db_session, BacktestStatus.RUNNING)
    r = await client.post(f"/api/v1/backtests/{bt.id}/cancel", headers=auth_headers)
    assert r.status_code == 202
    assert r.json()["status"] == "cancelling"


@pytest.mark.asyncio
async def test_cancel_already_terminal_returns_409(client: AsyncClient, db_session, auth_headers) -> None:
    bt = await _seed_backtest(db_session, BacktestStatus.COMPLETED)
    r = await client.post(f"/api/v1/backtests/{bt.id}/cancel", headers=auth_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "backtest_state_conflict"


@pytest.mark.asyncio
async def test_cancel_not_found_returns_404(client: AsyncClient, db_session, auth_headers) -> None:
    r = await client.post(f"/api/v1/backtests/{uuid4()}/cancel", headers=auth_headers)
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "backtest_not_found"
```

- [ ] **Step 2: delete 테스트 전체 코드**

`backend/tests/api/test_backtests_delete.py`:
```python
"""DELETE /api/v1/backtests/:id."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.backtest.models import Backtest, BacktestStatus, BacktestTrade, TradeDirection, TradeStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy


async def _seed_bt(db_session, status: BacktestStatus, with_trades: bool = False) -> Backtest:
    from tests.conftest import TEST_USER_ID
    strategy = Strategy(
        id=uuid4(), user_id=TEST_USER_ID, name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    bt = Backtest(
        id=uuid4(), user_id=TEST_USER_ID, strategy_id=strategy.id,
        symbol="BTCUSDT", timeframe="1h",
        period_start=datetime(2024, 1, 1), period_end=datetime(2024, 1, 2),
        initial_capital=Decimal("10000"),
        status=status,
    )
    db_session.add(bt)
    if with_trades:
        db_session.add(BacktestTrade(
            id=uuid4(), backtest_id=bt.id, trade_index=0,
            direction=TradeDirection.LONG, status=TradeStatus.CLOSED,
            entry_time=datetime(2024, 1, 1), exit_time=datetime(2024, 1, 1, 1),
            entry_price=Decimal("100"), exit_price=Decimal("102"),
            size=Decimal("10"), pnl=Decimal("20"), return_pct=Decimal("0.02"),
            fees=Decimal("0.1"),
        ))
    await db_session.commit()
    return bt


@pytest.mark.asyncio
async def test_delete_completed_204(client: AsyncClient, db_session, auth_headers) -> None:
    bt = await _seed_bt(db_session, BacktestStatus.COMPLETED)
    r = await client.delete(f"/api/v1/backtests/{bt.id}", headers=auth_headers)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_running_409(client: AsyncClient, db_session, auth_headers) -> None:
    bt = await _seed_bt(db_session, BacktestStatus.RUNNING)
    r = await client.delete(f"/api/v1/backtests/{bt.id}", headers=auth_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "backtest_state_conflict"


@pytest.mark.asyncio
async def test_delete_cascade_trades(client: AsyncClient, db_session, auth_headers) -> None:
    from sqlalchemy import select, func
    bt = await _seed_bt(db_session, BacktestStatus.COMPLETED, with_trades=True)
    before = (await db_session.execute(
        select(func.count(BacktestTrade.id)).where(BacktestTrade.backtest_id == bt.id)
    )).scalar_one()
    assert before == 1

    r = await client.delete(f"/api/v1/backtests/{bt.id}", headers=auth_headers)
    assert r.status_code == 204

    after = (await db_session.execute(
        select(func.count(BacktestTrade.id)).where(BacktestTrade.backtest_id == bt.id)
    )).scalar_one()
    assert after == 0
```

- [ ] **Step 3: trades + progress 테스트 전체 코드**

`backend/tests/api/test_backtests_trades.py`:
```python
"""GET /api/v1/backtests/:id/trades."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.backtest.models import Backtest, BacktestStatus, BacktestTrade, TradeDirection, TradeStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy


@pytest.mark.asyncio
async def test_trades_pagination_and_decimal_str(client: AsyncClient, db_session, auth_headers) -> None:
    from tests.conftest import TEST_USER_ID
    strategy = Strategy(
        id=uuid4(), user_id=TEST_USER_ID, name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    bt = Backtest(
        id=uuid4(), user_id=TEST_USER_ID, strategy_id=strategy.id,
        symbol="BTCUSDT", timeframe="1h",
        period_start=datetime(2024, 1, 1), period_end=datetime(2024, 1, 2),
        initial_capital=Decimal("10000"), status=BacktestStatus.COMPLETED,
    )
    db_session.add(bt)
    # 5 trades seed
    for i in range(5):
        db_session.add(BacktestTrade(
            id=uuid4(), backtest_id=bt.id, trade_index=i,
            direction=TradeDirection.LONG, status=TradeStatus.CLOSED,
            entry_time=datetime(2024, 1, 1, i), exit_time=datetime(2024, 1, 1, i + 1),
            entry_price=Decimal("100.12345678"), exit_price=Decimal("102.00000001"),
            size=Decimal("10"), pnl=Decimal("18.87654321"), return_pct=Decimal("0.01876543"),
            fees=Decimal("0.10000000"),
        ))
    await db_session.commit()

    r = await client.get(
        f"/api/v1/backtests/{bt.id}/trades?limit=3&offset=0", headers=auth_headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 5
    assert body["limit"] == 3
    assert body["offset"] == 0
    assert len(body["items"]) == 3

    first = body["items"][0]
    # Decimal은 문자열로 직렬화
    assert first["entry_price"] == "100.12345678"
    assert first["pnl"] == "18.87654321"
    assert first["direction"] == "long"
    assert first["status"] == "closed"
```

`backend/tests/api/test_backtests_progress.py`:
```python
"""GET /api/v1/backtests/:id/progress."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.backtest.models import Backtest, BacktestStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy


@pytest.mark.asyncio
async def test_progress_queued_not_stale(client: AsyncClient, db_session, auth_headers) -> None:
    from tests.conftest import TEST_USER_ID
    strategy = Strategy(
        id=uuid4(), user_id=TEST_USER_ID, name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    bt = Backtest(
        id=uuid4(), user_id=TEST_USER_ID, strategy_id=strategy.id,
        symbol="BTCUSDT", timeframe="1h",
        period_start=datetime(2024, 1, 1), period_end=datetime(2024, 1, 2),
        initial_capital=Decimal("10000"), status=BacktestStatus.QUEUED,
    )
    db_session.add(bt)
    await db_session.commit()

    r = await client.get(f"/api/v1/backtests/{bt.id}/progress", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "queued"
    assert body["started_at"] is None
    assert body["stale"] is False


@pytest.mark.asyncio
async def test_progress_stale_running(client: AsyncClient, db_session, auth_headers) -> None:
    from tests.conftest import TEST_USER_ID
    strategy = Strategy(
        id=uuid4(), user_id=TEST_USER_ID, name="s",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5, parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    # started_at을 2시간 전으로 설정 → threshold 30분 초과 → stale
    bt = Backtest(
        id=uuid4(), user_id=TEST_USER_ID, strategy_id=strategy.id,
        symbol="BTCUSDT", timeframe="1h",
        period_start=datetime(2024, 1, 1), period_end=datetime(2024, 1, 2),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.RUNNING,
        started_at=datetime.utcnow() - timedelta(hours=2),
    )
    db_session.add(bt)
    await db_session.commit()

    r = await client.get(f"/api/v1/backtests/{bt.id}/progress", headers=auth_headers)
    body = r.json()
    assert body["status"] == "running"
    assert body["stale"] is True
```

- [ ] **Step 4: 전체 실행 + 커밋**

```bash
cd backend && uv run pytest tests/api/test_backtests_cancel.py tests/api/test_backtests_delete.py tests/api/test_backtests_trades.py tests/api/test_backtests_progress.py -v
git add backend/tests/api/test_backtests_cancel.py backend/tests/api/test_backtests_delete.py backend/tests/api/test_backtests_trades.py backend/tests/api/test_backtests_progress.py
git commit -m "test(api): backtests cancel/delete/trades/progress E2E

cancel 202+cancelling, delete terminal-only, stale flag, CASCADE.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Milestone 11 — Post-Impl: Smoke + Docs Sync

### Task 23: L4 로컬 실 broker smoke 3건

**Files:**
- Modify: `docs/superpowers/specs/2026-04-15-sprint4-backtest-api-design.md` (§10.1 기록)

- [ ] **Step 1: Docker 서비스 기동**

```bash
docker compose up -d quantbridge-db quantbridge-redis
docker ps | grep quantbridge
```

- [ ] **Step 2: Alembic migration + backend 기동 + Celery worker 기동**

```bash
cd backend && uv run alembic upgrade head
cd backend && uv run uvicorn src.main:app --port 8000 &
cd backend && uv run celery -A src.tasks worker --pool=prefork --concurrency=4 --loglevel=info &
```

- [ ] **Step 3: S1 Happy Path smoke**

```bash
# 1. Strategy 생성 (Clerk token 세팅 필요 — spec §10.1 실제 수행 시)
# 2. POST /api/v1/backtests → 202 + backtest_id
# 3. GET /api/v1/backtests/<id>/progress 폴링
# 4. status='completed' 관측 → GET /api/v1/backtests/<id> 검증
```

결과를 §10.1 S1 체크박스에 기록:
```markdown
- [x] S1 Happy Path: POST /backtests → queued → running → completed (총 3.2s, 2 trades)
```

- [ ] **Step 4: S2 Broker down smoke**

```bash
docker stop quantbridge-redis
# POST /backtests → 503 + task_dispatch_failed. DB row 미존재 확인.
docker start quantbridge-redis
```

- [ ] **Step 5: S3 Cancel smoke**

- [ ] **Step 6: §10.1 결과 커밋**

```bash
git add docs/superpowers/specs/2026-04-15-sprint4-backtest-api-design.md
git commit -m "docs(sprint4): L4 smoke 3건 결과 기록 (§10.1)

S1 happy: <소요> / <trades 수>
S2 broker down: 503 확인, DB row 미존재
S3 running cancel: terminal 수렴 확인

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

### Task 24: endpoints.md + TODO.md 동기화 + 최종 검증

**Files:**
- Modify: `docs/03_api/endpoints.md`
- Modify: `docs/TODO.md`

- [ ] **Step 1: `endpoints.md` §Backtests 수정**

- "**202 + task_id**" → "**202 + backtest_id**"로 교체
- cancel 행 추가:
  ```
  | `POST` | `/api/v1/backtests/:id/cancel` | 실행 중 백테스트 취소 (best-effort) | Required | **202** |
  ```

- [ ] **Step 2: `docs/TODO.md` 업데이트**

```markdown
### Stage 3 / Sprint 4 — Celery + Backtest API ✅ 완료 (2026-04-15)

- [x] S3-04 _price_to_sl_ratio ValueError (브랜치 첫 commit)
- [x] S3-03 engine fault injection (stretch, coverage <수치>%)
- [x] Celery celery_app + @worker_ready hook
- [x] Backtest SQLModel + migration
- [x] BacktestRepository 조건부 UPDATE
- [x] BacktestService 3-guard cancel 로직
- [x] 7 REST endpoints + Clerk auth
- [x] FixtureProvider + BTCUSDT_1h fixture
- [x] StrategyService delete 선조회 + IntegrityError 번역
- [x] L4 smoke 3건 통과
- [x] 테스트 <최종 수>개 통과
```

Sprint 4 follow-ups 섹션 제거, Sprint 5 이관 Open Issues 추가.

- [ ] **Step 3: 전체 테스트 final run**

```bash
cd backend && uv run pytest -q && uv run ruff check . && uv run mypy src/
```

Expected: 모두 green.

- [ ] **Step 4: 최종 커밋**

```bash
git add docs/03_api/endpoints.md docs/TODO.md
git commit -m "docs(sprint4): endpoints.md cancel 추가 + task_id→backtest_id + TODO 동기화

Sprint 4 완료 표시. Open Issues #1-14 Sprint 5+ 이관.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 5: PR 생성 (사용자 승인 필요)**

> **중지. 사용자 승인 없이 push/PR 금지.** Git Safety Protocol:
> - "푸쉬할까요?" 승인 후 `git push -u origin feat/sprint4-backtest-api`
> - "PR 생성할까요?" 승인 후 `gh pr create --base main --title "..." --body "..."`

---

## 완료 기준 체크리스트 (spec §1.2 대응)

- [ ] S3-04 필수 처리 완료
- [ ] S3-03 stretch 시도 (coverage 수치 기록)
- [ ] 7 endpoints API integration green
- [ ] Ownership 격리 (타 유저 404)
- [ ] Celery `asyncio.run()` per-task + pool=prefork
- [ ] Alembic round-trip
- [ ] 필수 시나리오 9건 L3 테스트 통과
- [ ] L4 smoke 3건 기록 (§10.1)
- [ ] CI green (ruff/mypy/pytest)
- [ ] Stale reclaim + stale 플래그 동작 확인
- [ ] endpoints.md / TODO.md 동기화

---

## 참고

- **Spec:** `docs/superpowers/specs/2026-04-15-sprint4-backtest-api-design.md` (1262 라인)
- **선행 스프린트 plan:** `docs/superpowers/plans/2026-04-15-sprint3-strategy-api.md`
- **Backend rules:** `.ai/stacks/fastapi/backend.md`
- **CLAUDE.md QuantBridge 고유 규칙:** 금융 Decimal, Celery 비동기, AES-256
