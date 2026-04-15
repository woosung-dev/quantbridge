# vectorbt 백테스트 엔진 + SignalResult 필드 채움 — 설계 문서

- **작성일:** 2026-04-15
- **단계:** Stage 3 / Sprint 2
- **관련 ADR:** ADR-003 (Pine 런타임 안전성 + 파서 범위)
- **선행 스프린트:** Sprint 1 (Pine Parser MVP, commit `e433a45`)
- **방법론:** brainstorming → writing-plans → TDD 구현
- **시간박스:** 없음. 완료 기준 충족 시 종료.

---

## 1. 목적과 범위

### 1.1 왜 이 스프린트인가

Sprint 1에서 Pine 파서 MVP가 `SignalResult.entries`/`exits`만 실값으로 산출하고 나머지 4개 필드(`direction`, `sl_stop`, `tp_limit`, `position_size`)는 `None`인 상태다. 또한 vectorbt 의존성이 아직 없어 "파서 → 백테스트 숫자" 엔드투엔드가 끊겨 있다.

본 스프린트는 두 갭을 동시에 메운다:
1. 파서가 `PineUnsupportedError`로 막아둔 `strategy.exit(stop=, limit=)`를 해금해 브래킷 오더 전략을 지원하고 `sl_stop`/`tp_limit` Series를 채움.
2. vectorbt 기반 순수 라이브러리 함수 `run_backtest()`를 도입해 5개 표준 지표를 산출.

### 1.2 스프린트 목표 (완료 기준 / Go-No-Go)

두 기준 모두 충족 시 스프린트 종료:

1. **정확성 (Ground zero):** Sprint 1의 EMA Cross v4/v5 golden에 `BacktestResult` 기대값(5개 지표)이 추가된 테스트 통과.
2. **범위 해금:** `strategy.exit(stop=, limit=)`를 포함하는 합성 브래킷 오더 골든 1~2케이스(ATR 기반 SL/TP) 통과.

**명시적 제외:** TradingView 원본 수치 대조는 하지 않는다. vectorbt 출력값을 snapshot으로 고정해 회귀만 방어한다. TV ↔ vectorbt 엔진 간 수수료 모델·fill 타이밍 차이는 별도 "엔진 검증 스프린트" 대상.

### 1.3 범위 밖

- Celery 태스크, `/backtests` API 엔드포인트, Strategy 도메인 CRUD
- `strategy.short`, pyramiding, `qty_percent=` (명시적 `PineUnsupportedError`)
- Pine `strategy(...)` 선언 파라미터(`initial_capital`, `default_qty_type` 등) 자동 주입
- Stress test / optimizer 연동, TimescaleDB OHLCV 로딩, 프론트엔드 편집기
- TV 원본 수치 대조 (다음 스프린트에서 별도 추적)

### 1.4 SignalResult 필드 채움 범위 (확정)

| 필드 | Sprint 1 | Sprint 2 후 |
|------|----------|-------------|
| `entries` | `pd.Series[bool]` (실값) | 동일 |
| `exits` | `pd.Series[bool]` (실값) | 동일 |
| `direction` | `None` | `pd.Series[str]` — 항상 `"long"` 리터럴 (short은 Unsupported 유지) |
| `sl_stop` | `None` | `pd.Series[float]` — `strategy.exit(stop=<price>)` 시 진입 바에 가격, 청산까지 carry forward, 포지션 없을 때 `NaN` |
| `tp_limit` | `None` | 동일 패턴, `strategy.exit(limit=<price>)` |
| `position_size` | `None` | `pd.Series[float]` — `strategy.entry(qty=<literal>)` 있을 때만 상수 Series. 없으면 `None` 유지 (vectorbt 기본값 사용) |

타입 스키마는 변경하지 않는다. Sprint 1의 `types.py` 필드 정의 그대로. 인터프리터의 **산출 규칙**만 확장.

---

## 2. 아키텍처 결정

### 2.1 코드 배치 원칙

파서는 `strategy` 도메인, 백테스트 엔진은 `backtest` 도메인. 관심사 분리로 단위 테스트 격리와 향후 여러 엔진(vectorbt, 이벤트 드리븐 등) 확장을 용이하게 한다.

### 2.2 디렉토리 구조

```
backend/src/
├── strategy/pine/
│   ├── interpreter.py          # 변경: strategy.exit(stop, limit) 해금 + BracketState
│   ├── types.py                # 변경 없음 (필드 정의 유지)
│   └── ... (기타 Sprint 1 파일 불변)
├── backtest/
│   ├── engine/                 # [신규] 본 스프린트 산출물
│   │   ├── __init__.py         # 공개 API: run_backtest, 타입 re-export
│   │   ├── adapter.py          # SignalResult → Portfolio.from_signals kwargs
│   │   ├── metrics.py          # Portfolio → BacktestMetrics
│   │   └── types.py            # BacktestConfig / BacktestResult / BacktestOutcome
│   └── {router,service,repository,models,schemas}.py   # 스텁 유지 (다음 스프린트)

backend/tests/
├── strategy/pine/
│   └── golden/ema_cross_v{4,5}/expected.json   # backtest 키 추가
└── backtest/engine/
    ├── test_adapter.py
    ├── test_metrics.py
    ├── test_run_backtest.py
    └── golden/ema_cross_atr_sltp_v5/
        ├── strategy.pine
        ├── ohlcv.csv
        └── expected.json
```

### 2.3 공개 API 단일 진입점

```python
# backend/src/backtest/engine/__init__.py
def run_backtest(
    source: str,
    ohlcv: pd.DataFrame,
    config: BacktestConfig | None = None,
) -> BacktestOutcome: ...
```

파서 공개 API `parse_and_run`은 변경 없이 유지. 파싱만 필요한 호출자(미래 `/strategies/parse` 엔드포인트 등)는 기존 함수 사용.

### 2.4 내부 파이프라인

```
source + ohlcv
    ↓
parse_and_run(source, ohlcv)                ── 기존
    ↓
ParseOutcome
    │
    ├─ status != "ok" → BacktestOutcome(status="parse_failed", parse=..., result=None)
    │
    └─ status == "ok":
           ↓
       adapter.to_portfolio_kwargs(signal, ohlcv, config)
           ↓
       vectorbt.Portfolio.from_signals(**kwargs)
           ↓
       metrics.extract_metrics(portfolio)
           ↓
       BacktestOutcome(status="ok", parse, result=BacktestResult(metrics, equity_curve, config))
```

---

## 3. 컴포넌트 상세

### 3.1 신규 타입 (`src/backtest/engine/types.py`)

```python
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
class BacktestResult:
    metrics: BacktestMetrics
    equity_curve: pd.Series    # bar별 자본 (UI 차트용)
    config_used: BacktestConfig


@dataclass
class BacktestOutcome:
    status: Literal["ok", "unsupported", "error", "parse_failed"]
    parse: ParseOutcome        # 파싱 결과를 투명 노출
    result: BacktestResult | None = None
    error: PineError | str | None = None
```

**설계 의도:**
- `BacktestOutcome.parse`로 `supported_feature_report` 등 파서 메타데이터를 호출자에 투명 전달.
- `status="parse_failed"`는 파서가 ok 외 상태를 반환한 경우의 명시적 분기. 백테스트 단계 에러(`"error"`)와 구분.
- `equity_curve`를 `metrics`에 넣지 않는 이유는 Series 크기(수백~수천) 때문.

### 3.2 인터프리터 변경 (`src/strategy/pine/interpreter.py`)

**현재 상태** (interpreter.py:299-305):
```python
if name == "strategy.exit":
    raise PineUnsupportedError(
        "strategy.exit with bracket orders (stop/limit) is deferred to next sprint",
        feature="strategy.exit(stop,limit)",
    )
```

**변경 후 동작:**

```python
if name == "strategy.exit":
    stop_price = _eval_kwarg(call, "stop")     # float or None
    limit_price = _eval_kwarg(call, "limit")   # float or None
    if stop_price is None and limit_price is None:
        raise PineUnsupportedError(
            "strategy.exit requires stop= or limit= argument",
            feature="strategy.exit(no-args)",
        )
    state.register_bracket(stop=stop_price, limit=limit_price)
    return
```

**BracketState 상태 루프 핵심:**
- bar-by-bar 루프에 진입 바에서 `sl_stop`/`tp_limit` Series에 값 기록.
- 포지션 종료(`strategy.close` 호출 또는 `exits=True` 평가) 시 Series에 NaN 복귀.
- `strategy.short`, `strategy.entry(qty=<non-literal-expression>)`, `qty_percent=` 등장 시 즉시 `PineUnsupportedError`.

### 3.3 어댑터 (`src/backtest/engine/adapter.py`)

```python
def to_portfolio_kwargs(
    signal: SignalResult,
    ohlcv: pd.DataFrame,
    config: BacktestConfig,
) -> dict[str, Any]:
    """SignalResult + OHLCV + config → Portfolio.from_signals() kwargs."""
    kwargs: dict[str, Any] = {
        "close": ohlcv["close"],
        "entries": signal.entries,
        "exits": signal.exits,
        "init_cash": float(config.init_cash),   # vectorbt는 float
        "fees": config.fees,
        "slippage": config.slippage,
        "freq": config.freq,
    }
    if signal.sl_stop is not None:
        kwargs["sl_stop"] = signal.sl_stop       # 가격 직접 지원
    if signal.tp_limit is not None:
        kwargs["tp_stop"] = _price_to_ratio(signal.tp_limit, ohlcv["close"])  # tp_stop은 ratio만
    if signal.position_size is not None:
        kwargs["size"] = signal.position_size
    # direction: Sprint 2에선 항상 long → 생략 (vectorbt 기본값)
    return kwargs
```

**주의:**
- vectorbt `Portfolio.from_signals`의 `sl_stop`은 가격/비율 모두 지원하지만 `tp_stop`은 비율만(해당 버전 API). 가격 → `(target - close) / close` 변환.
- OHLCV 인덱스와 SignalResult Series 인덱스 정렬은 어댑터 진입에서 `assert` 또는 명시적 `ValueError`로 체크.

### 3.4 메트릭스 (`src/backtest/engine/metrics.py`)

```python
def extract_metrics(pf: "vbt.Portfolio") -> BacktestMetrics:
    trades = pf.trades
    return BacktestMetrics(
        total_return=Decimal(str(float(pf.total_return()))),
        sharpe_ratio=Decimal(str(float(pf.sharpe_ratio()))),
        max_drawdown=Decimal(str(float(pf.max_drawdown()))),
        win_rate=Decimal(str(float(trades.win_rate()))) if trades.count() > 0 else Decimal("0"),
        num_trades=int(trades.count()),
    )
```

- 경계에서 Decimal 변환 (CLAUDE.md 규칙).
- `trades.count() == 0`인 경우 `win_rate=0`. 다른 지표는 vectorbt 반환값 그대로 (NaN 허용, 골든 비교 시 문자열 `"NaN"`).

---

## 4. 에러 처리

| 발생 지점 | 처리 |
|-----------|------|
| 파서 단계 에러 (ok 외) | `BacktestOutcome(status="parse_failed", parse=ParseOutcome, error=parse.error)` — 백테스트 단계 미진입 |
| adapter — 인덱스 정렬 실패 / 필드 타입 오류 | `ValueError` catch → `status="error"` + 에러 메시지 문자열 |
| vectorbt 실행 예외 | 동일하게 `status="error"` — 스택트레이스는 로거, outcome에는 요약 메시지 |
| metrics 추출 예외 | 동일. NaN 자체는 허용 (`Decimal("NaN")` 저장) |

**불변 규칙 (ADR-003 연장):**
- adapter / metrics에서 silent fallback 금지. 값 누락 시 명시적 예외.
- 파서가 status="unsupported" 반환한 시그널을 "그래도 돌려보자"로 실행하지 않음 → `parse_failed`로 차단.

**로깅:**
- `logger.exception()`으로 어댑터/vectorbt 예외 구조화 기록.
- 성공 케이스: `logger.info("backtest_ok", extra={"num_trades": ..., "total_return": ...})` 수준.

---

## 5. 테스트 전략

### 5.1 테스트 레이어

| 레벨 | 파일 | 범위 |
|------|------|------|
| Unit | `test_interpreter_strategy_exit.py` | `strategy.exit(stop=, limit=)` 인터프리터 처리. SL/TP Series carry forward. `strategy.short` 등 Unsupported 유지 검증. |
| Unit | `test_adapter.py` | SignalResult → Portfolio kwargs 변환. tp_limit 가격 → ratio 변환. 선택 필드 None 처리. 인덱스 미정렬 예외. |
| Unit | `test_metrics.py` | 목 Portfolio로 5개 지표 추출. trades.count()==0 케이스. Decimal 변환. |
| Integration | `test_run_backtest.py` | 공개 API `run_backtest()` end-to-end. ok / parse_failed / error 분기. |
| Golden | `test_golden_backtest/` | EMA Cross v4/v5 expected.json에 `backtest` 키 추가. 합성 브래킷 오더 케이스. |

### 5.2 Ground zero 기대값 확장

기존 `tests/strategy/pine/golden/ema_cross_v5/expected.json`에 추가:

```json
{
  "signal": { "entries": [...], "exits": [...] },
  "backtest": {
    "metrics": {
      "total_return": "...",
      "sharpe_ratio": "...",
      "max_drawdown": "...",
      "win_rate": "...",
      "num_trades": 0
    }
  }
}
```

수치는 "TV 원본 일치"가 아니라 **vectorbt 자체 출력을 한 번 고정한 snapshot**. 리그레션 감지 목적.

### 5.3 합성 브래킷 오더 골든

```
tests/backtest/engine/golden/ema_cross_atr_sltp_v5/
  strategy.pine       # EMA cross entry + strategy.exit(stop=close-atr, limit=close+2*atr)
  ohlcv.csv           # 고정 200 bar
  expected.json       # SignalResult + BacktestMetrics
```

`strategy.exit`가 Unsupported였던 전략이 이제 ok로 돌아가는 사실을 단위로 검증.

### 5.4 커버리지 목표

- 신규 모듈 `src/backtest/engine/`: ≥95% 라인 커버리지.
- interpreter의 신규 브래킷 분기: ≥95% 브랜치 커버리지.
- 전체 테스트 실행 시간: <5초 유지 (vectorbt 포함).

### 5.5 `pine_coverage_report.py` 확장 (선택)

기존 스크립트는 `parse_and_run` 결과만 체크. 본 스프린트 말미에 백테스트 스냅샷 모드를 추가. 미구현 시 별도 Task로 분리.

---

## 6. 구현 순서 (Path 1 — 인터프리터 먼저, 엔진 다음)

| # | Step | 산출물 | 테스트 |
|---|------|--------|--------|
| 1 | `strategy.exit(stop=, limit=)` 인터프리터 지원 | interpreter.py 수정, BracketState 도입 | stop만 / limit만 / 둘 다 / carry forward / 청산 후 NaN |
| 2 | SignalResult 실값 산출 확장 | interpreter에서 sl_stop/tp_limit/direction/position_size Series 채움. types.py 불변 | Step 1 확장 + `strategy.entry(qty=<literal>)` 케이스 |
| 3 | `strategy.short` / pyramiding / `qty_percent=` Unsupported 명시 | interpreter + stdlib 화이트리스트. 명확한 에러 메시지 | Unsupported 감지 테스트 |
| 4 | vectorbt 의존성 추가 + smoke test | pyproject.toml `vectorbt>=0.26,<0.27` 추가, `uv sync`, 최소 smoke | smoke test 1건 |
| 5 | `src/backtest/engine/types.py` | BacktestConfig/Metrics/Result/Outcome dataclass | 인스턴스화 / equality |
| 6 | `src/backtest/engine/adapter.py` | `to_portfolio_kwargs` | 전 조합 + 인덱스 미정렬 예외 + tp_limit ratio 변환 |
| 7 | `src/backtest/engine/metrics.py` | `extract_metrics` | 정상 / zero-trades / NaN |
| 8 | `src/backtest/engine/__init__.py` `run_backtest()` 공개 API | 파서 호출 → adapter → vectorbt → metrics 조립 | ok / parse_failed / error 분기 |
| 9 | Ground zero golden 확장 | EMA Cross v4/v5 expected.json `backtest` 키 추가. snapshot 기록 | golden runner 통과 |
| 10 | 합성 브래킷 골든 추가 | `ema_cross_atr_sltp_v5/` 케이스 | golden runner 통과 |
| 11 | `pine_coverage_report.py` 백테스트 스냅샷 모드 (선택) | Go/No-Go 스크립트 확장. 실패 시 exit code 변별 | 수동 실행 확인 |

**의존성:** 1 → 2 → (3, 4 병렬) → 5 → 6 → 7 → 8 → 9 → 10 → 11

---

## 7. 리스크와 대응

| 리스크 | 확률 | 영향 | 대응 |
|--------|------|------|------|
| vectorbt API 차이 (`tp_stop` ratio vs 가격 혼란) | 중 | 중 | Step 4 smoke test에서 실제 버전 API 서명 확인 후 adapter 작성. 의존성 버전 핀(`>=0.26,<0.27`) |
| BracketState carry forward 구현 복잡도 과소평가 | 중 | 중 | Step 1에서 TDD. 청산 엣지 케이스(강제 exits, EOD) 테스트 우선 |
| SignalResult.direction/position_size를 Series로 바꾸는 변경이 Sprint 1 호환성 깨뜨림 | 낮 | 중 | types.py의 `\| None` 유지. Sprint 1 골든은 None 그대로, 이번 스프린트 신규 케이스만 실값. 기존 테스트 green 유지 |
| vectorbt 설치 크기(pandas-ta+numba 포함)로 CI 속도 저하 | 낮 | 낮 | uv lock 캐시. 실측 이슈 시 별도 대응 |
| `Decimal("NaN")` 저장이 JSON 직렬화 실패 유발 | 낮 | 낮 | 골든 비교 시 NaN은 문자열 `"NaN"`으로 기록하는 serializer 명시 |
| interpreter의 kwarg 평가가 parser 구현에 의존 | 중 | 낮 | Step 1 초기에 parser.py 현재 kwarg 지원 상태 확인. 필요 시 parser 소폭 수정 Task로 분기 |

---

## 8. 다음 스프린트 및 장기 확장 연결

- **Sprint 3 (예상):** Strategy 도메인 CRUD API + Celery 태스크 래퍼 + `POST /backtests`. 본 스프린트의 `run_backtest()`는 Celery 태스크가 호출하는 순수 함수 — 인터페이스 안정성 덕분에 얇은 래핑으로 충분.
- **Sprint 4 이후:** stress test / optimizer 연동, `strategy(...)` 선언 파라미터 자동 주입, `strategy.short` / pyramiding 지원, TV 원본 수치 대조 (엔진 검증 스프린트).
- **Phase A 수집(50개 TV 전략):** 본 스프린트와 병행하지 않음 (백그라운드 트랙). 브래킷 오더 전략이 많이 포함될수록 본 스프린트의 언락 효과 증대.

---

## 9. 참조

- ADR-003: Pine 런타임 안전성 + 파서 범위
- Sprint 1 spec: `docs/superpowers/specs/2026-04-15-pine-parser-mvp-design.md` §4.7, §9 (장기 로드맵)
- Sprint 1 plan: `docs/superpowers/plans/2026-04-15-pine-parser-mvp.md`
- CLAUDE.md §QuantBridge 고유 규칙 (금융 숫자 Decimal, Celery 비동기, exec/eval 금지)
- docs/01_requirements/pine-coverage-assignment.md (Phase A 템플릿)
- vectorbt: https://vectorbt.dev/ (BSD, `Portfolio.from_signals` API)

---

## 10. Sprint 2 구현 후 노트 (스펙 이탈 기록)

본 스펙 작성 시점 이후 구현 과정에서 발견된 현실과의 차이. 이후 스프린트에서는 아래 내용이 실제 구현을 반영하도록 참고한다.

### 10.1 vectorbt 버전 상향 (0.26 → 0.28.5)
- 원 스펙: `vectorbt>=0.26,<0.27`
- 실제: `vectorbt>=0.28,<0.29` (`backend/pyproject.toml`)
- 이유: vectorbt 0.26.x가 numpy 1.x 전용 private API(`numpy.lib.stride_tricks._broadcast_shape`)에 의존. `pandas-ta`가 numpy≥2.2.6을 요구하므로 공존 불가.
- 영향: `Portfolio.from_signals` API 서명 동일 → 어댑터 코드 변경 없음.

### 10.2 `sl_stop` 시맨틱 — 가격 → 비율 변환 필요
- 원 스펙 §3.3: `sl_stop`은 가격 Series 직접 전달 가능.
- 실제: vectorbt 0.28.x에서 `sl_stop`은 **비율(ratio)만 해석**. 절대 가격 Series 전달 시 SL 미작동 (smoke test로 확인).
- 해결: `adapter._price_to_sl_ratio(sl_price, close) = (close - sl_price) / close`로 변환 후 전달. `tp_stop`(이미 비율 변환)과 동일한 패턴.
- 주의: sl_price > close인 malformed 입력 시 음수 ratio가 silent pass됨 → Sprint 3 follow-up S3-04에서 방어적 clamp 추가 예정.

### 10.3 SignalResult 필드 타입 정정
- 원 스펙 §1.4는 `direction`/`sl_stop`/`tp_limit`/`position_size`를 `pd.Series | None`으로 기술.
- Sprint 1의 실제 types.py는 `float | None` / `str | None`이었음 (스펙과 불일치).
- Task 1에서 `pd.Series | None`으로 정정 (스펙 §1.4 의도대로).

### 10.4 `ta.atr(length)` OHLCV 암묵 주입 패치 (Task 10 중 발견)
- Pine Script에서 `ta.atr(14)`는 `high`/`low`/`close` 컨텍스트를 암묵적으로 사용.
- Sprint 1 인터프리터는 인자를 그대로 stdlib 함수에 넘겨 호출 실패.
- 픽스: `interpreter._eval_fncall`에 4줄 surgical 패치 — `node.name == "ta.atr" and len(args) == 1 and not kwargs` 조건에서 `env.lookup("high"/"low"/"close")`로 주입.
- 영향 범위: `ta.atr` 1-arg 호출에만 한정. 다른 `ta.*` 함수는 무영향.
- 후속: 다른 implicit-OHLCV 함수들(`ta.rsi` 등)도 유사 패턴 필요 시 Sprint 3에서 확장.

### 10.5 커버리지 목표 미달 (91% vs 95%)
- 스펙 §5.4 목표: 신규 `src/backtest/engine/` 모듈 ≥95% 라인 커버리지.
- 실제: 91% (exception 분기 일부 미커버).
- 원인: `run_backtest` 예외 분기는 현재 fixture로 자연 트리거가 어려움.
- 후속: Sprint 3 S3-03 — fault injection 테스트 추가.

### 10.6 Task 1 follow-ups (Sprint 3로 이월)
- S3-01: `strategy.exit` gate propagation — `if cond: strategy.exit(...)` 시 gate 무시됨.
- S3-02: 중복 `strategy.exit` 호출 시 경고 (현재 조용히 마지막 값 덮어씀).
