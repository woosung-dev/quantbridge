# 빈 개발 DB 를 dogfood 가능한 상태로 복원하는 시더 — 전략·백테스트를 실 서비스 계층으로 생성한다
"""dogfood 복원 시더.

빈 로컬 DB(`ts.ohlcv` 0행 포함)에서 전 화면을 쓸 수 있는 최소 데이터를 만든다.
2026-07-25 개발 DB 전소 사고 이후 복원 경로가 없어 3스프린트 연속 실화면 dogfood 가
불가능했던 것을 닫는다.

## 왜 HTTP 가 아니라 서비스 계층인가

`authenticate_clerk_request` 는 `authorized_parties=[frontend_url]` 로 검증하고,
clerk SDK `verifytoken.py:44-46` 은 **`azp` 클레임을 필수**로 요구한다. Clerk Backend
API 로 발급한 세션 토큰에는 `azp` 가 없어(브라우저 발급 토큰에만 있다) 헤드리스
HTTP 시딩은 구조적으로 불가능하다. 그래서 HTTP + auth 계층만 우회하고 그 아래는
전부 실제 경로를 탄다 — `StrategyService` / `BacktestService` / `CeleryTaskDispatcher`
/ pine_v2 엔진. 즉 `metrics` JSONB · `backtest_trades` · `equity_curve` 는 전부
**진짜 엔진 출력**이고 손으로 지어낸 값이 하나도 없다.

## OHLCV 는 따로 안 심는다

`TimescaleProvider` 는 cache-first + live CCXT fill 이라(`providers/timescale.py:37-73`)
캔들이 없으면 Bybit 에서 받아 `ts.ohlcv` 에 직접 쓴다. **첫 백테스트 한 번이 곧 시딩**
이다. 별도 backfill 이 필요 없다.

## 사용

    cd backend && set -a; source .env.local; set +a
    uv run python scripts/seed_dogfood.py --confirm                # 전체
    uv run python scripts/seed_dogfood.py --confirm --only legacy  # 하나만

멱등하다 — 같은 이름의 전략/같은 파라미터의 백테스트가 이미 있으면 건너뛴다.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from sqlalchemy import select  # noqa: E402

from src.backtest.models import Backtest, BacktestStatus  # noqa: E402
from src.backtest.schemas import CreateBacktestRequest  # noqa: E402
from src.strategy.models import Strategy  # noqa: E402
from src.strategy.schemas import CreateStrategyRequest  # noqa: E402
from src.tasks._worker_engine import create_worker_engine_and_sm  # noqa: E402

# --- 함정 3종을 상수로 박는다 -------------------------------------------------
#
# 1. 심볼은 canonical `BTC/USDT`. `ts.ohlcv` 는 읽기·쓰기 양쪽이 `normalize_symbol`
#    을 지나므로(`providers/timescale.py:45`) `BTCUSDT` 로 심으면 **모든 독자에게
#    안 보인다**. 겉보기엔 적재된 테이블인데 캐시는 영원히 miss 다.
# 2. 기간 경계는 **봉 격자에 정렬된 UTC 자정**. 어긋나면 `find_gaps` 의
#    `generate_series` 가 영구 유령 갭을 보고 매 실행마다 재fetch 한다(BL-309).
# 3. `ts.ohlcv.exchange` 는 NOT NULL 무기본값 — provider 가 `default_exchange` 로
#    채우므로 이 스크립트는 직접 INSERT 하지 않는다.
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
INITIAL_CAPITAL = Decimal("10000")

# 펀딩은 최근 16시간 3행뿐이라(beat 가 2일 창만 backfill) 과거 구간 백테스트에
# 재현 불가능한 부분 펀딩 아티팩트만 더한다. 시드는 끄고, dogfood 중에 의도적으로
# 켠 실행을 따로 한 번 만든다.
INCLUDE_FUNDING = False

PINE_PBR = REPO_ROOT / "backend/tests/fixtures/pine_corpus_v2/s1_pbr.pine"
# ★`tmp_code/pine_code/` 를 쓰면 안 된다 — `.gitignore:65` 로 무시되는 untracked
#   경로다. `PbR_strategy_easy.pine` 과 md5 동일(31b0674d…)이라 손실 없이 대체된다.
PINE_EMA = REPO_ROOT / "frontend/public/samples/ema-crossover.pine"
# ★옵티마이저 전용. Grid Search MVP 는 `input.int`/`input.float` 만 sweep 하고
#   bare `input(4, …)` 은 `input.generic` 으로 분류돼 거부된다(`grid_search.py:168`).
#   s1_pbr 은 bare input 만 쓴다 → 옵티마이저 베이스로 못 쓴다. s4 는 타입 입력 7개.
#   EMA 도 타입 입력이지만 그쪽은 degenerate 실행이 **최신이어야** 전략목록에서
#   D1 이 재현되므로 백테스트를 더 붙이면 안 된다.
PINE_HMA = REPO_ROOT / "backend/tests/fixtures/pine_corpus_v2/s4_hma_curvature.pine"


def _utc(y: int, m: int, d: int) -> datetime:
    """봉 격자에 정렬된 UTC 자정 — BL-309 유령 갭 방지."""
    return datetime(y, m, d, tzinfo=UTC)


@dataclass(frozen=True)
class StrategySpec:
    key: str
    name: str
    pine_path: Path


@dataclass(frozen=True)
class RunSpec:
    key: str
    strategy_key: str
    period_start: datetime
    period_end: datetime
    leverage: Decimal = Decimal("1.0")
    phase: str = "current"  # "legacy" = 구 워커에서 돌려야 하는 실행
    note: str = ""
    allow_degraded: bool = False
    # ★중복 판정의 구분자. `legacy` 와 `monthly` 는 입력이 **완전 동일**하고 엔진
    #   버전만 다르다 — 그게 두 실행의 존재 이유다(혼재 정렬 고지의 짝, 그리고
    #   컨벤션 변화를 입력 변수 없이 격리해 보여준다). 그래서 (전략·창·레버리지)
    #   만으로 중복을 재면 둘이 서로를 지운다. 실제 구분 성질인 `sharpe_convention`
    #   키 유무로 잰다. False = 구 엔진 산출물, True = 현 엔진 산출물.
    expect_convention: bool = True


# S-A 는 성과 실행 전부를, S-B 는 degenerate 실행 하나만 갖는다.
# 전략 목록·대시보드 §performance 는 전략별 **최신 COMPLETED 백테스트** 하나만
# 읽으므로(`DISTINCT ON`), degenerate 실행을 S-A 에 섞으면 화면에서 그 상태를
# 재현할 수 없다.
STRATEGIES: tuple[StrategySpec, ...] = (
    StrategySpec("pbr", "PbR Pivot Reversal", PINE_PBR),
    StrategySpec("ema", "EMA Crossover Demo", PINE_EMA),
    StrategySpec("hma", "HMA Curvature", PINE_HMA),
)

# 마스터 창 — 격자 정렬 + 과거에서 끝나 trailing 유령 갭이 없고,
# 커밋된 `BTCUSDT-RECENT_1h.csv`(perp, 2025-07-01→2026-06-30)와 겹쳐
# spot/perp 편차를 공짜로 잴 수 있다.
MASTER_START = _utc(2025, 7, 1)
MASTER_END = _utc(2026, 7, 25)

RUNS: tuple[RunSpec, ...] = (
    RunSpec(
        "legacy",
        "pbr",
        MASTER_START,
        MASTER_END,
        phase="legacy",
        expect_convention=False,
        note="구 엔진 = sharpe_convention 키 부재. 유일한 CCXT fetch 도 이 실행이 한다",
    ),
    RunSpec(
        "monthly",
        "pbr",
        MASTER_START,
        MASTER_END,
        note="legacy 와 입력 완전 동일 — 엔진 버전만 다르다. 혼재 정렬 고지의 짝",
    ),
    RunSpec(
        "leveraged",
        "pbr",
        MASTER_START,
        MASTER_END,
        leverage=Decimal("100.0"),
        note="마진 배너 + 강제청산 + MDD 각주",
    ),
    # `_periodic_returns` 는 `equity.resample("ME")` 월말 빈 개수로 분기한다
    # (`engine/metrics.py:40-48`). 한 달력월 **안에** 완전히 들어가야 빈이 1개라
    # daily fallback 이 된다. "2개월 미만" 이 아니라 "월말 빈 <2" 가 기준이다.
    RunSpec(
        "daily",
        "pbr",
        _utc(2026, 3, 2),
        _utc(2026, 3, 30),
        note="월말 빈 1개 → tv_daily_rfr2",
    ),
    RunSpec(
        "degenerate",
        "ema",
        _utc(2026, 7, 22),
        _utc(2026, 7, 25),
        note="거래 0 → 자본 평탄 → sd=0 → unavailable. 리포트 '—' vs 대시보드 '0.00' 대조군",
    ),
    RunSpec(
        "optimizer_base",
        "hma",
        _utc(2026, 3, 2),
        _utc(2026, 3, 30),
        note="옵티마이저 grid-search 의 베이스 — 타입 입력을 선언한 전략이어야 한다",
    ),
)


# optimizer 가 참조할 백테스트. 짧은 창이라 4셀 재실행이 빠르다.
OPTIMIZER_BASE_RUN = "optimizer_base"


@dataclass
class Result:
    created_strategies: list[str] = field(default_factory=list)
    skipped_strategies: list[str] = field(default_factory=list)
    created_runs: list[tuple[str, str]] = field(default_factory=list)
    skipped_runs: list[str] = field(default_factory=list)


async def _resolve_owner(sm) -> UUID:
    """단일 사용자 환경 전제 — users 1행. 여러 행이면 명시 요구."""
    from src.auth.models import User

    async with sm() as session:
        rows = (await session.execute(select(User))).scalars().all()
    if not rows:
        raise SystemExit("users 0행 — 브라우저로 한 번 로그인해 사용자를 만든 뒤 다시 실행하라.")
    if len(rows) > 1:
        raise SystemExit(f"users {len(rows)}행 — 이 시더는 단일 사용자 환경 전용이다.")
    return rows[0].id


async def _ensure_strategy(sm, spec: StrategySpec, owner_id: UUID, result: Result) -> UUID:
    from src.backtest.repository import BacktestRepository
    from src.strategy.repository import StrategyRepository
    from src.strategy.service import StrategyService
    from src.trading.dependencies import get_encryption_service
    from src.trading.repositories.webhook_secret_repository import WebhookSecretRepository
    from src.trading.services.webhook_secret_service import WebhookSecretService

    async with sm() as session:
        existing = (
            (
                await session.execute(
                    select(Strategy).where(Strategy.user_id == owner_id, Strategy.name == spec.name)
                )
            )
            .scalars()
            .first()
        )
        if existing is not None:
            result.skipped_strategies.append(spec.name)
            return existing.id

        if not spec.pine_path.exists():
            raise SystemExit(f"Pine 소스 없음: {spec.pine_path}")

        service = StrategyService(
            repo=StrategyRepository(session),
            backtest_repo=BacktestRepository(session),
            secret_svc=WebhookSecretService(
                repo=WebhookSecretRepository(session),
                crypto=get_encryption_service(),
            ),
        )
        created = await service.create(
            CreateStrategyRequest(
                name=spec.name,
                pine_source=spec.pine_path.read_text(encoding="utf-8"),
                symbol=SYMBOL,
                timeframe=TIMEFRAME,
            ),
            owner_id=owner_id,
        )
        result.created_strategies.append(spec.name)
        return created.id


async def _ensure_run(
    sm, run: RunSpec, strategy_id: UUID, owner_id: UUID, result: Result
) -> UUID | None:
    from src.backtest.dispatcher import CeleryTaskDispatcher
    from src.backtest.repository import BacktestRepository
    from src.backtest.service import BacktestService
    from src.core.config import settings
    from src.market_data.providers.ccxt import CCXTProvider
    from src.market_data.providers.timescale import TimescaleProvider
    from src.market_data.repository import OHLCVRepository
    from src.strategy.repository import StrategyRepository
    from src.trading.repositories.funding_rate_repository import FundingRateRepository

    async with sm() as session:
        # leverage 는 컬럼이 아니라 `config` JSONB 안에 산다(`models.py:90`).
        # 상태도 파이썬에서 거른다 — SQLModel enum 필드의 `.in_()` 는 타입 체커가
        # 못 읽고 레포엔 그 우회 관례가 따로 없다.
        alive = {BacktestStatus.QUEUED, BacktestStatus.RUNNING, BacktestStatus.COMPLETED}
        candidates = (
            (
                await session.execute(
                    select(Backtest).where(
                        Backtest.user_id == owner_id,
                        Backtest.strategy_id == strategy_id,
                        Backtest.period_start == run.period_start,
                        Backtest.period_end == run.period_end,
                    )
                )
            )
            .scalars()
            .all()
        )
        for cand in candidates:
            if cand.status not in alive:
                continue
            if Decimal(str((cand.config or {}).get("leverage", "1.0"))) != run.leverage:
                continue
            # 아직 안 끝난 실행은 컨벤션을 판정할 수 없으므로 같은 것으로 본다.
            if cand.status is BacktestStatus.COMPLETED:
                has_conv = "sharpe_convention" in (cand.metrics or {})
                if has_conv != run.expect_convention:
                    continue
            result.skipped_runs.append(run.key)
            return cand.id

        # HTTP 경로와 동일한 조립 — dispatcher 는 실제 Celery.
        # provider 는 이 프로세스에서 쓰이지 않는다(엔진 실행은 워커에서 일어난다).
        service = BacktestService(
            repo=BacktestRepository(session),
            strategy_repo=StrategyRepository(session),
            ohlcv_provider=TimescaleProvider(
                OHLCVRepository(session),
                CCXTProvider(),
                exchange_name=settings.default_exchange,
            ),
            ohlcv_repo=OHLCVRepository(session),
            dispatcher=CeleryTaskDispatcher(),
            funding_repo=FundingRateRepository(session),
        )
        created = await service.submit(
            CreateBacktestRequest(
                strategy_id=strategy_id,
                symbol=SYMBOL,
                timeframe=TIMEFRAME,
                period_start=run.period_start,
                period_end=run.period_end,
                initial_capital=INITIAL_CAPITAL,
                leverage=run.leverage,
                include_funding=INCLUDE_FUNDING,
                allow_degraded_pine=run.allow_degraded,
            ),
            user_id=owner_id,
        )
        result.created_runs.append((run.key, str(created.backtest_id)))
        return created.backtest_id


async def _wait(sm, backtest_id: UUID, timeout_s: int) -> str:
    """QUEUED/RUNNING 이 끝날 때까지 폴링. 워커가 죽어 있으면 timeout 으로 드러난다."""
    deadline = asyncio.get_running_loop().time() + timeout_s
    last = "?"
    while asyncio.get_running_loop().time() < deadline:
        async with sm() as session:
            bt = (
                (await session.execute(select(Backtest).where(Backtest.id == backtest_id)))
                .scalars()
                .one()
            )
            last = str(bt.status)
            if bt.status in (
                BacktestStatus.COMPLETED,
                BacktestStatus.FAILED,
                BacktestStatus.CANCELLED,
            ):
                if bt.status is BacktestStatus.FAILED:
                    print(f"    FAILED — {bt.error}")
                return last
        await asyncio.sleep(3)
    return f"TIMEOUT(last={last})"


async def _ensure_optimizer_run(sm, backtest_id: UUID, owner_id: UUID, timeout_s: int) -> None:
    """완료 백테스트 위에 grid-search 1건. authed e2e 가 완료 run 상세를 요구한다.

    ★`optimizer.run` 은 `optimizer_heavy` 큐로만 라우팅되고 그 큐의 유일한 소비자가
    `backend-optimizer-heavy` 다. 그 컨테이너에 OHLCV_PROVIDER 계열 env 가 빠져 있으면
    provider 가 없는 경로를 가리켜 전부 실패한다(이 스프린트에서 compose 수정).
    """
    from src.optimizer.models import OptimizationRun, OptimizationStatus

    async with sm() as session:
        existing = (
            (
                await session.execute(
                    select(OptimizationRun).where(OptimizationRun.user_id == owner_id)
                )
            )
            .scalars()
            .all()
        )
    if any(r.status is OptimizationStatus.COMPLETED for r in existing):
        print("\n▶ optimizer — skip (완료 run 이미 존재)")
        return

    from src.backtest.repository import BacktestRepository
    from src.core.config import settings
    from src.market_data.providers.ccxt import CCXTProvider
    from src.market_data.providers.timescale import TimescaleProvider
    from src.market_data.repository import OHLCVRepository
    from src.optimizer.dispatcher import CeleryOptimizationTaskDispatcher
    from src.optimizer.repository import OptimizationRepository
    from src.optimizer.schemas import CreateOptimizationRunRequest
    from src.optimizer.service import OptimizerService
    from src.strategy.repository import StrategyRepository

    print("\n▶ optimizer — grid-search 2×2 (fastLength × slowLength)")
    async with sm() as session:
        # HTTP 경로(`get_optimizer_service`)와 동일 조립 — dispatcher 는 실제 Celery.
        service = OptimizerService(
            repo=OptimizationRepository(session),
            backtest_repo=BacktestRepository(session),
            strategy_repo=StrategyRepository(session),
            ohlcv_provider=TimescaleProvider(
                OHLCVRepository(session),
                CCXTProvider(),
                exchange_name=settings.default_exchange,
            ),
            dispatcher=CeleryOptimizationTaskDispatcher(),
        )
        run = await service.submit_grid_search(
            CreateOptimizationRunRequest.model_validate(
                {
                    "backtest_id": str(backtest_id),
                    "kind": "grid_search",
                    "param_space": {
                        "schema_version": 1,
                        "objective_metric": "sharpe_ratio",
                        "direction": "maximize",
                        "max_evaluations": 4,
                        # s4 가 실제로 선언한 `input.int` 두 개. 미선언 이름이나
                        # bare `input()`(= input.generic)은 `_validate_grid_search_pre`
                        # 가 거부한다(`grid_search.py:168`).
                        "parameters": {
                            "fastLength": {"kind": "integer", "min": 14, "max": 15, "step": 1},
                            "slowLength": {"kind": "integer", "min": 34, "max": 35, "step": 1},
                        },
                    },
                }
            ),
            user_id=owner_id,
        )
        run_id = run.id
    print(f"    submitted {run_id} — 대기 중…")

    deadline = asyncio.get_running_loop().time() + timeout_s
    while asyncio.get_running_loop().time() < deadline:
        async with sm() as session:
            cur = (
                (await session.execute(select(OptimizationRun).where(OptimizationRun.id == run_id)))
                .scalars()
                .one()
            )
            if cur.status in (OptimizationStatus.COMPLETED, OptimizationStatus.FAILED):
                if cur.status is OptimizationStatus.FAILED:
                    print(f"    FAILED — {cur.error_message}")
                else:
                    print(f"    {cur.status}")
                return
        await asyncio.sleep(3)
    print("    TIMEOUT — optimizer_heavy 워커가 살아 있는지 확인하라")


async def _find_completed(sm, owner_id: UUID, run_key: str) -> UUID | None:
    """이미 완료된 실행 중 `run_key` 창과 일치하는 것을 찾는다(멱등 재실행용)."""
    spec = next(r for r in RUNS if r.key == run_key)
    async with sm() as session:
        rows = (
            (
                await session.execute(
                    select(Backtest).where(
                        Backtest.user_id == owner_id,
                        Backtest.period_start == spec.period_start,
                        Backtest.period_end == spec.period_end,
                    )
                )
            )
            .scalars()
            .all()
        )
    for row in rows:
        if row.status is BacktestStatus.COMPLETED:
            return row.id
    return None


async def _run(only: str | None, timeout_s: int) -> None:
    engine, sm = create_worker_engine_and_sm()
    result = Result()
    optimizer_base: UUID | None = None
    try:
        owner_id = await _resolve_owner(sm)
        print(f"owner={owner_id}")

        wanted = [r for r in RUNS if only is None or r.key == only]
        if only is not None and not wanted:
            raise SystemExit(f"--only {only} — 없는 키. 가능: {[r.key for r in RUNS]}")

        needed_strategies = {r.strategy_key for r in wanted}
        ids: dict[str, UUID] = {}
        for spec in STRATEGIES:
            if spec.key in needed_strategies:
                ids[spec.key] = await _ensure_strategy(sm, spec, owner_id, result)
                print(f"strategy[{spec.key}] {ids[spec.key]}")

        for run in wanted:
            print(f"\n▶ {run.key} (lev={run.leverage}) — {run.note}")
            bt_id = await _ensure_run(sm, run, ids[run.strategy_key], owner_id, result)
            if bt_id is None:
                continue
            if run.key in result.skipped_runs:
                print(f"    skip (이미 존재) {bt_id}")
                continue
            print(f"    submitted {bt_id} — 대기 중…")
            status = await _wait(sm, bt_id, timeout_s)
            print(f"    {status}")
            if run.key == OPTIMIZER_BASE_RUN:
                optimizer_base = bt_id

        # optimizer 는 완료 백테스트를 참조해야 한다 — `daily`(69 거래, 짧은 창)를
        # 베이스로 쓴다. 마스터 창(1028 거래)을 4셀 재실행하면 불필요하게 느리다.
        if only is None or only == OPTIMIZER_BASE_RUN:
            if optimizer_base is None:
                optimizer_base = await _find_completed(sm, owner_id, OPTIMIZER_BASE_RUN)
            if optimizer_base is not None:
                await _ensure_optimizer_run(sm, optimizer_base, owner_id, timeout_s)
    finally:
        await engine.dispose()

    print("\n=== 요약 ===")
    print(f"전략 생성 {len(result.created_strategies)} / 스킵 {len(result.skipped_strategies)}")
    print(f"실행 생성 {len(result.created_runs)} / 스킵 {len(result.skipped_runs)}")
    for key, bid in result.created_runs:
        print(f"  {key}: {bid}")


def main() -> None:
    p = argparse.ArgumentParser(description="dogfood 복원 시더")
    p.add_argument("--confirm", action="store_true", required=True, help="실행 확인 (필수)")
    p.add_argument("--only", default=None, help=f"하나만 실행. 키: {[r.key for r in RUNS]}")
    p.add_argument("--timeout", type=int, default=600, help="실행당 완료 대기 상한(초)")
    args = p.parse_args()
    if not args.confirm:
        raise SystemExit("--confirm 필요")
    asyncio.run(_run(args.only, args.timeout))


if __name__ == "__main__":
    main()
