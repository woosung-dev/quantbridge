#!/usr/bin/env python
"""CI authed e2e 를 위한 **결정론 시더** ([BL-802]).

왜 `seed_dogfood.py` 가 아닌가 — 그것은 `CeleryTaskDispatcher`(`:310`)와 CCXT 라이브 fill
(`:305-309`)을 경유한다. CI 잡에는 celery worker 도 네트워크도 없다. 이 시더는 **Repository
계층만** 쓰고 엔진을 한 번도 부르지 않는다 — 완료된 백테스트를 「실행」이 아니라 **행으로** 만든다.

무엇을 심는가 — 전부 2026-08-18 CI 실측(run `32082953745`)이 지목한 것만이다. 그 판이
`ci-authed-manifest.json` 의 19건을 전량 돌려 **79 passed / 13 failed** 를 냈고, 실패 13건이
요구한 데이터가 정확히 아래 넷이다:

    · ExchangeAccount 1건 (bybit demo)     → `/trading` 표 · 테스트 주문 다이얼로그
    · Strategy 12건 (하나는 고정 UUID)      → 목록 필터(11+ 필요) · `/strategies/:id/edit`
    · 완료 Backtest 1건 + BacktestTrade 3행 → `/backtests` 성과 목록 · `/backtests/:id/trades`
    · 완료 OptimizationRun 1건              → `/optimizer/:id`

★**고정 UUID 를 쓰는 이유** — `authed-settings-save.spec.ts:16` 이
`process.env.QB_BL570_STRATEGY_ID ?? "0d94167b-8c24-444b-a124-870a2a9f0243"` 로 그 값을 **직접**
연다. 시더가 그 UUID 를 그대로 심으면 spec 도 CI YAML 도 고칠 것이 없다.

★**모든 UUID 는 RFC 4122 variant nibble(`[89ab]`)을 지킨다.** FE 의 Zod `z.uuid()` 가 거부하면
화면이 **조용히 미렌더**되고, 그러면 「데이터가 없다」와 구분되지 않는다.

사용법:
    cd apps/api
    uv run python scripts/seed_ci_e2e.py --confirm

    # 무엇이 심어질지만 본다 (쓰기 0건)
    uv run python scripts/seed_ci_e2e.py

★**`--confirm` 없이는 아무것도 쓰지 않는다** — `soak-restart.sh`·`link_auth_subject.py` 와 같은
레포 관례다.

★★**버릴 수 있는 DB 가 아니면 거부한다** — database 이름이 `_test` 로 끝나야 한다.
이 가드가 없으면 개발 DB(`quantbridge`)에 시드 행을 쏟아붓는다. `apps/api/tests/_db_guard.py` 가
pytest 쪽에서 하는 일을 여기서 같은 이유로 한 번 더 한다.

재실행은 안전하다 — 고정 UUID 로 이미 있으면 아무것도 만들지 않고 종료한다.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

# 스크립트 직접 실행 지원 — `apps/api` 를 import 루트에 얹는다(레포 관례).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.auth.models import User
from src.backtest.models import Backtest, BacktestStatus, BacktestTrade, TradeDirection, TradeStatus
from src.backtest.serializers import equity_curve_to_jsonb
from src.core.config import settings
from src.optimizer.models import OptimizationKind, OptimizationRun, OptimizationStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.encryption import EncryptionService
from src.trading.models import ExchangeAccount, ExchangeMode, ExchangeName

# ── 고정 식별자 ────────────────────────────────────────────────────────────────
# ★spec 이 직접 여는 UUID. `authed-settings-save.spec.ts:16` 의 기본값과 **글자 그대로** 같아야 한다.
BL570_STRATEGY_ID = UUID("0d94167b-8c24-444b-a124-870a2a9f0243")
SEED_BACKTEST_ID = UUID("b0000000-0000-4000-8000-0000000c1000")
SEED_ACCOUNT_ID = UUID("a0000000-0000-4000-8000-0000000c1000")
SEED_OPTIMIZER_ID = UUID("00000000-0000-4000-8000-0000000c1000")

# 목록 필터 spec(`sprint46-tier3-nth` #15)이 **11건 이상**을 요구한다. 12건을 심어 여유를 둔다.
STRATEGY_COUNT = 12

SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"

# 파서를 실제로 지나는 최소 v5 전략. `StrategyService` 를 거치지 않으므로 `parse_status` 는
# 손으로 `ok` 를 넣는다 — 이 시더의 목적은 파서 검증이 아니라 **화면이 그릴 행**을 만드는 것이다.
PINE_SOURCE = """//@version=5
strategy("QB CI seed", overlay=true)
fast = ta.sma(close, 10)
slow = ta.sma(close, 30)
if ta.crossover(fast, slow)
    strategy.entry("L", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("L")
"""


def _assert_disposable_database(url: str) -> str:
    """`_test` 로 끝나지 않는 DB 를 향하면 **연결 전에** 멈춘다.

    ★탈출구를 두지 않는다. 이 스크립트의 유일한 소비자는 CI 의 일회용 `quantbridge_test` 이고,
      「그래도 진행」이 필요한 상황은 곧 개발 DB 를 겨냥한 상황이다.
    """
    database = make_url(url).database or ""
    if not database.endswith("_test"):
        raise SystemExit(
            f"[QB-GUARD-SEED-CI] 중단 — database='{database}' 는 버려도 되는 DB(_test 접미사)가 아니다.\n"
            "  이 시더는 CI 의 일회용 DB 전용이다. 개발 DB 에는 `mise run seed` 를 써라."
        )
    return database


async def _resolve_owner(session, email: str) -> UUID:
    """Better Auth 사용자 → 앱 `users.id` 를 2홉으로 해석한다.

    `auth_user`(Better Auth 소유, TEXT PK) → `users.auth_subject` → `users.id`.
    정본 = `scripts/link_auth_subject.py:21-22`.

    ★**앱 `users` 행은 sign-up 만으로는 안 생긴다** — 인증된 FastAPI 요청이 한 번 지나야
      `AuthService.get_or_create` 가 JIT 프로비저닝한다(`src/auth/service.py:89-129`).
      playwright `setup` project 의 `/strategies` 방문(`e2e/global.setup.ts:94`)이 그 요청이다.
      그래서 이 시더는 **`--project=setup` 뒤에** 돌아야 한다. 0행이면 그 순서가 틀린 것이다.
    """
    subject = (
        await session.execute(
            text("SELECT id FROM auth_user WHERE email = :email"), {"email": email}
        )
    ).scalar_one_or_none()
    if subject is None:
        raise SystemExit(
            f"auth_user 에 email='{email}' 가 없다 — sign-up 이 아직 안 지났다.\n"
            "  playwright `--project=setup` 을 먼저 돌려라."
        )
    user = (
        (await session.execute(select(User).where(User.auth_subject == str(subject))))
        .scalars()
        .first()
    )
    if user is None:
        raise SystemExit(
            f"auth_user 는 있는데 users.auth_subject='{subject}' 행이 없다 — JIT 프로비저닝이 아직 안 돌았다.\n"
            "  `global.setup.ts` 가 로그인 뒤 `/strategies` 를 방문하는 단계까지 지나야 한다."
        )
    return user.id


def _build_strategies(owner_id: UUID) -> list[Strategy]:
    """전략 12건. 첫 건만 고정 UUID 이고 나머지는 무작위 UUID 다.

    이름을 서로 다르게 두는 이유 — `sprint46-tier3-nth` #15 가 **filter input** 에 문자열을 넣고
    목록이 줄어드는지 본다. 같은 이름 12건이면 필터가 아무것도 가르지 못한다.
    """
    now = datetime.now(UTC)
    rows = [
        Strategy(
            id=BL570_STRATEGY_ID,
            user_id=owner_id,
            name="CI Seed — BL-570 settings",
            description="`authed-settings-save.spec.ts` 가 이 UUID 를 직접 연다. 이름을 바꿔도 되지만 id 는 고정이다.",
            pine_source=PINE_SOURCE,
            pine_version=PineVersion.v5,
            parse_status=ParseStatus.ok,
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            created_at=now,
            updated_at=now,
        )
    ]
    for i in range(1, STRATEGY_COUNT):
        rows.append(
            Strategy(
                user_id=owner_id,
                name=f"CI Seed {i:02d} — {'EMA' if i % 2 else 'RSI'} demo",
                pine_source=PINE_SOURCE,
                pine_version=PineVersion.v5,
                parse_status=ParseStatus.ok,
                symbol=SYMBOL,
                timeframe=TIMEFRAME,
                # 목록 정렬이 결정적이도록 생성 시각을 1분씩 벌린다.
                created_at=now - timedelta(minutes=i),
                updated_at=now - timedelta(minutes=i),
            )
        )
    return rows


def _build_backtest_and_trades(owner_id: UUID) -> tuple[Backtest, list[BacktestTrade]]:
    """완료 상태 백테스트 1건 + 체결 3행.

    ★엔진을 부르지 않는다. `/backtests` 목록은 `tr[data-status="completed"]` 를 보고
      `/backtests/:id/trades` 는 `[data-testid="trade-detail-table"] tbody tr` 를 본다 —
      둘 다 **행의 존재**를 보지 시뮬레이션의 정합성을 보지 않는다.
    """
    now = datetime.now(UTC)
    period_end = now - timedelta(days=1)
    period_start = period_end - timedelta(days=30)
    backtest = Backtest(
        id=SEED_BACKTEST_ID,
        user_id=owner_id,
        strategy_id=BL570_STRATEGY_ID,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        period_start=period_start,
        period_end=period_end,
        initial_capital=Decimal("10000.00000000"),
        status=BacktestStatus.COMPLETED,
        # ★키 이름을 지어내지 마라 — 정본은 `src/backtest/schemas.py:293 BacktestMetricsOut` 이고
        #   `total_return`·`sharpe_ratio`·`max_drawdown`·`win_rate`·`num_trades` 5개가 **필수**다.
        #   초판이 `total_return_pct`·`win_rate_pct`·`total_trades` 로 써서 상세 응답 파싱이
        #   죽었고, 그 결과 `/backtests/:id` 리포트 셸과 `/backtests/:id/trades` 표가
        #   **둘 다 조용히 비었다**(2026-08-18 CI run `32088...`). 「행은 있는데 화면이 빈다」의 전형이다.
        metrics={
            "total_return": "12.5",
            "sharpe_ratio": "1.35",
            "max_drawdown": "-4.25",
            "win_rate": "66.67",
            "num_trades": 3,
            "profit_factor": "2.1",
        },
        # ★★**정본을 재사용한다 — 손으로 만들지 않는다.** 저장 형상은 `[[isoZ, "값"], …]` 이고
        #   그것을 정하는 것은 `serializers.equity_curve_to_jsonb` 하나다. 종전 판은 이 자리에
        #   `{timestamp, value}` dict 를 적었는데, 그것은 `_to_detail` 이 **변환한 응답**의
        #   모양이지 저장의 모양이 아니었다 — `for ts, v in <dict>` 가 키를 언패킹해
        #   `GET /backtests/{id}` 가 500 이 됐다([BL-807]). 형상을 두 곳에 적는 한 또 갈린다.
        equity_curve=equity_curve_to_jsonb(
            pd.Series(
                [Decimal(10000 + d * 40) for d in range(0, 31, 5)],
                index=pd.DatetimeIndex([period_start + timedelta(days=d) for d in range(0, 31, 5)]),
            )
        ),
        warnings=[],
        created_at=now - timedelta(hours=2),
        started_at=now - timedelta(hours=2),
        completed_at=now - timedelta(hours=1),
    )
    trades: list[BacktestTrade] = []
    cumulative = Decimal("0")
    for i in range(3):
        pnl = Decimal("125.50") if i != 1 else Decimal("-40.25")
        cumulative += pnl
        entry = period_start + timedelta(days=3 * i + 1)
        trades.append(
            BacktestTrade(
                backtest_id=SEED_BACKTEST_ID,
                trade_index=i + 1,
                direction=TradeDirection.LONG,
                status=TradeStatus.CLOSED,
                entry_time=entry,
                exit_time=entry + timedelta(hours=8),
                entry_price=Decimal("64000.00000000") + Decimal(i * 100),
                exit_price=Decimal("64500.00000000") + Decimal(i * 100),
                size=Decimal("0.02500000"),
                pnl=pnl,
                return_pct=Decimal("1.255000") if i != 1 else Decimal("-0.402500"),
                fees=Decimal("0.80000000"),
                cumulative_pnl=cumulative,
                exit_kind="signal",
            )
        )
    return backtest, trades


def _build_optimization_run(owner_id: UUID) -> OptimizationRun:
    now = datetime.now(UTC)
    return OptimizationRun(
        id=SEED_OPTIMIZER_ID,
        user_id=owner_id,
        backtest_id=SEED_BACKTEST_ID,
        kind=OptimizationKind.GRID_SEARCH,
        status=OptimizationStatus.COMPLETED,
        # ★`ParamSpace` 는 평평한 dict 가 아니다 — `src/optimizer/schemas.py:142` 가
        #   `objective_metric`·`direction`·`max_evaluations`·`parameters` 를 요구하고
        #   `extra="forbid"` 다. 초판의 `{"fast": [...]}` 는 응답 검증을 못 지나
        #   `/optimizer` 목록에 행이 안 떴다.
        param_space={
            "schema_version": 1,
            "objective_metric": "sharpe_ratio",
            "direction": "maximize",
            "max_evaluations": 9,
            "parameters": {
                "fast": {"kind": "integer", "min": 5, "max": 15, "step": 5},
                "slow": {"kind": "integer", "min": 20, "max": 40, "step": 10},
            },
        },
        # ★★`result` 는 **`kind` 로 갈리는 discriminated union** 이다
        #   (`apps/web/src/features/optimizer/schemas.ts:332`). 초판은 `{best_params, combinations}`
        #   라는 지어낸 모양이었고, `kind` 가 없으면 FE 의 row-level `safeParse` 가 그 행을
        #   **조용히 건너뛴다**(:366-369 가 그렇게 설계돼 있다) — 목록에 링크가 안 뜨고
        #   `/optimizer/:id` 캐논이 「완료 run 시딩 필요」로 죽는다. 2026-08-18 codex 적대 리뷰가 잡았다.
        result={
            "schema_version": 1,
            "kind": "grid_search",
            "param_names": ["fast", "slow"],
            "param_values": {"fast": ["5", "10", "15"], "slow": ["20", "30", "40"]},
            "cells": [
                {
                    "param_values": {"fast": f, "slow": sl},
                    "sharpe": sharpe,
                    "total_return": tr,
                    "max_drawdown": "-4.25",
                    "num_trades": 3,
                    "is_degenerate": False,
                    "objective_value": sharpe,
                }
                for f, sl, tr, sharpe in (
                    ("5", "20", "4.1", "0.62"),
                    ("10", "30", "12.5", "1.35"),
                    ("15", "40", "7.9", "0.91"),
                )
            ],
            "objective_metric": "sharpe_ratio",
            "direction": "maximize",
            "best_cell_index": 1,
        },
        created_at=now - timedelta(minutes=50),
        started_at=now - timedelta(minutes=50),
        completed_at=now - timedelta(minutes=30),
    )


def _build_exchange_account(owner_id: UUID, crypto: EncryptionService) -> ExchangeAccount:
    """bybit demo 계정 1건.

    ★`/trading` 은 `table[aria-label^="거래소 계정"] tbody tr` 를 세고, 테스트 주문 다이얼로그는
      계정이 하나라도 있어야 열린다. **거래소에 나가는 요청은 없다** — 화면이 행을 그리는 데
      필요한 것은 DB 행뿐이다. 키는 실제 Fernet 로 암호화해 마스킹 경로가 복호화에 실패하지 않게 한다.
    """
    return ExchangeAccount(
        id=SEED_ACCOUNT_ID,
        user_id=owner_id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=crypto.encrypt("ci-e2e-seed-api-key"),
        api_secret_encrypted=crypto.encrypt("ci-e2e-seed-api-secret"),
        label="CI seed (bybit demo)",
    )


async def _run(email: str, confirm: bool) -> int:
    url = settings.database_url
    database = _assert_disposable_database(url)

    engine = create_async_engine(url)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sm() as session:
            owner_id = await _resolve_owner(session, email)

            existing = await session.get(Strategy, BL570_STRATEGY_ID)
            if existing is not None:
                print(f"이미 시드돼 있다 (strategy {BL570_STRATEGY_ID}) — 아무것도 하지 않는다.")
                return 0

            strategies = _build_strategies(owner_id)
            account = _build_exchange_account(
                owner_id, EncryptionService(settings.trading_encryption_keys)
            )
            backtest, trades = _build_backtest_and_trades(owner_id)
            optimization = _build_optimization_run(owner_id)

            print(f"대상 DB      : {database}")
            print(f"소유자       : users.id={owner_id}  (email={email})")
            print(f"전략         : {len(strategies)}건 (고정 {BL570_STRATEGY_ID})")
            print(f"거래소 계정  : 1건 bybit/demo {SEED_ACCOUNT_ID}")
            print(f"백테스트     : 1건 completed {SEED_BACKTEST_ID} + trades {len(trades)}행")
            print(f"옵티마이저   : 1건 completed {SEED_OPTIMIZER_ID}")

            if not confirm:
                print("\n══ dry-run 종료 — 아무것도 쓰지 않았다. 집행하려면 --confirm ══")
                return 0

            # ★★**단계별 flush 가 필요하다** (2026-08-18 CI 실측, run `32088709...`).
            #   한 번에 `add_all` 하면 `backtests_strategy_id_fkey` 로 죽는다 —
            #   `Strategy` 와 `Backtest` 사이에 `relationship()` 이 **없어서**(FK 컬럼만 있다)
            #   SQLAlchemy 의 unit-of-work 가 두 표의 의존 순서를 알 수 없고, backtests 를
            #   strategies 보다 먼저 INSERT 한다. `Backtest ↔ BacktestTrade` 는 relationship 이
            #   있어 그 쌍만은 알아서 정렬된다.
            #   ★이 결함은 `--selftest` 가 못 잡는다 — 행을 짓는 것과 넣는 것은 다른 문제다.
            session.add_all(strategies)
            session.add(account)
            await session.flush()
            session.add(backtest)
            await session.flush()
            session.add_all(trades)
            session.add(optimization)
            await session.flush()
            await session.commit()
            print("\n✓ 시드 완료")
            return 0
    finally:
        await engine.dispose()


def _selftest() -> int:
    """DB 없이 **모든 행을 실제로 구성**한다.

    ★이것이 있는 이유 — 초판은 `OptimizationKind.GRID`(실재하지 않는 멤버)를 썼는데
      **로컬 검증이 그 줄에 도달한 적이 없었다.** 로컬은 `auth_user` 가 비어 `_resolve_owner`
      에서 먼저 죽었고, 그 뒤 코드는 CI 에서 처음 실행됐다(run `32087714072`).
      즉 「로컬에서 확인했다」가 **닿지 않은 경로에 대해서는 아무것도 뜻하지 않았다.**
      이 selftest 는 DB·네트워크 없이 그 경로 전부를 지난다.
    """
    owner = UUID("00000000-0000-4000-8000-00000000dead")
    crypto = EncryptionService(settings.trading_encryption_keys)

    strategies = _build_strategies(owner)
    # ★`== STRATEGY_COUNT` 로 쓰지 마라 — `_build_strategies` 가 그 상수만큼 만드니 **항진명제**다.
    #   재는 것은 spec 의 실제 요구다: `sprint46-tier3-nth` #15 가 목록 **11건 이상**을 요구한다.
    assert len(strategies) >= 11, len(strategies)
    assert strategies[0].id == BL570_STRATEGY_ID
    # 필터 spec 이 의미를 가지려면 이름이 서로 달라야 한다(같은 이름이면 필터가 아무것도 못 가른다).
    assert len({s.name for s in strategies}) == len(strategies)

    account = _build_exchange_account(owner, crypto)
    assert crypto.decrypt(account.api_key_encrypted) == "ci-e2e-seed-api-key"

    backtest, trades = _build_backtest_and_trades(owner)
    assert backtest.status is BacktestStatus.COMPLETED
    assert backtest.strategy_id == BL570_STRATEGY_ID
    assert len(trades) >= 1

    optimization = _build_optimization_run(owner)
    assert optimization.status is OptimizationStatus.COMPLETED
    assert optimization.backtest_id == backtest.id

    # ★★**JSONB 페이로드를 정본 스키마에 실제로 먹인다.**
    #   초판 selftest 는 「행이 만들어지는가」만 봤고, 그래서 `metrics` 키 이름 3개와
    #   `param_space` 구조와 `equity_curve` 키 2개가 전부 틀린 채 초록이었다. 화면은
    #   조용히 비었고 CI 한 판을 태우고서야 드러났다(2026-08-18).
    #   ⇒ **구성 가능성이 아니라 계약 통과를 재라.** 이 두 줄이 그 세 결함을 전부 잡는다.
    from src.backtest.schemas import BacktestMetricsOut
    from src.backtest.serializers import equity_curve_from_jsonb
    from src.optimizer.schemas import ParamSpace

    BacktestMetricsOut.model_validate(backtest.metrics)
    ParamSpace.model_validate(optimization.param_space)
    # ★`result` 의 계약은 **FE 에만** 있다 — BE 는 `result: dict[str, Any]` 라 pydantic 이 안 잡는다.
    #   `OptimizationResultSchema` 는 `kind` 로 갈리는 discriminated union 이고, `kind` 가 없으면
    #   FE 가 그 행을 **조용히 건너뛴다**. 그래서 그 키들을 여기서 직접 못박는다.
    result = optimization.result or {}
    assert result.get("kind") == "grid_search", result.get("kind")
    assert result.get("schema_version") == 1, result.get("schema_version")
    assert result.get("cells"), "cells 가 비었다 — 목록이 그릴 것이 없다"
    for cell in result["cells"]:
        assert set(cell) == {
            "param_values",
            "sharpe",
            "total_return",
            "max_drawdown",
            "num_trades",
            "is_degenerate",
            "objective_value",
        }, cell
    assert isinstance(result.get("best_cell_index"), int), result.get("best_cell_index")
    # ★★★**equity_curve 의 정본은 「저장 형상」이다** — `serializers.equity_curve_to_jsonb` 가
    #   `[[isoZ, "값"], …]` 로 쓰고 `_to_detail`(`service.py:849-855`)이 `for ts, v in …` 으로
    #   되읽는다. ~~「`EquityPointSchema`(FE) 가 정본이라 BE 모델이 없다」~~ 는 **거짓이었다** —
    #   그 스키마는 `_to_detail` 이 **변환한 응답**의 모양이지 저장의 모양이 아니다.
    #   ★그리고 키만 재던 종전 검사가 그 오해를 **계약으로 승격**했다: dict 를 심은 시더가
    #   초록으로 통과했고, 실제로는 `for ts, v in <dict 리스트>` 가 **키를 언패킹**해
    #   `_parse_utc_iso("timestamp")` ValueError → `GET /backtests/{id}` **500** → 리포트 셸과
    #   체결 표가 **함께** 사라졌다([BL-807] ⑴·⑶ 은 같은 하나의 결함이었다).
    #   ⇒ 키를 세지 말고 **되읽기를 실제로 시켜라.** 이 한 줄이 두 축(모양·포맷)을 다 잡는다.
    assert backtest.equity_curve, "equity_curve 가 비었다"
    equity_curve_from_jsonb(backtest.equity_curve)

    # ★UUID variant nibble — Zod `z.uuid()` 가 거부하면 화면이 조용히 미렌더된다.
    for fixed in (BL570_STRATEGY_ID, SEED_BACKTEST_ID, SEED_ACCOUNT_ID, SEED_OPTIMIZER_ID):
        assert fixed.version == 4, (fixed, fixed.version)
        assert str(fixed)[19] in "89ab", fixed

    print(
        f"✓ selftest — 전략 {len(strategies)} · 계정 1 · 백테스트 1(+trades {len(trades)}) · 옵티마이저 1"
        " 을 DB 없이 전부 구성했다."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CI authed e2e 결정론 시더 (BL-802)")
    parser.add_argument(
        "--email",
        default=os.environ.get("E2E_AUTH_EMAIL"),
        help="시드를 붙일 Better Auth 사용자 (기본: $E2E_AUTH_EMAIL)",
    )
    parser.add_argument("--confirm", action="store_true", help="실제로 쓴다 (없으면 dry-run)")
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="DB 없이 모든 행을 구성해 본다 (배선 확인 전용)",
    )
    args = parser.parse_args()
    if args.selftest:
        return _selftest()
    if not args.email:
        raise SystemExit("--email 또는 E2E_AUTH_EMAIL 이 필요하다.")
    return asyncio.run(_run(args.email, args.confirm))


if __name__ == "__main__":
    raise SystemExit(main())
