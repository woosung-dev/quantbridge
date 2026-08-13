# 라이브 세션 운영자 도구 — 종료·청산을 **서비스 계층**으로 태워 원장에 남긴다 (BL-593)
"""라이브 세션 운영 CLI.

## 왜 이 스크립트가 있는가 (BL-593)

`ClosePositionService` 는 `dependencies.py` 를 통해 **HTTP 에만 조립**돼 있었다. 그래서
소크를 끄거나 거래소를 손으로 flat 으로 만들 때 운영자 스크립트가 그걸 못 쓰고
`BybitFuturesProvider` 를 **직접 호출**했고, 그 청산에 대응하는 `trading.orders` 행이
**남지 않았다**.

2026-08-04 실측(`trading.exchange_exits`, 계정 `19a8166a`): 청산 **103건** 중 원장 밖
(`external_manual`) **12건 = 11.7%** — 07-24/27/28/31, 08-01/03 **6일에 걸쳐 상시**다.

★**앱 코드에는 원장을 건너뛰는 청산 경로가 없다.** `ClosePositionService.close_position` 은
`OrderService.execute(...)` 를 타므로 `Order` 행을 남긴다. 문제는 **도구**였다.

[BL-591] 이 채택한 설계는 **원장을 진실로 써서 엔진에 주입**한다(ADR-022). 원장에 없는
청산이 있으면 틀린 포지션을 주입하게 되므로, 이 구멍은 그 전제를 직접 갉는다.

## 왜 HTTP 가 아니라 서비스 계층인가

`authenticate_clerk_request` 는 clerk SDK 가 **`azp` 클레임을 필수**로 요구하는데 Backend
API 로 발급한 토큰에는 그게 없다(브라우저 발급 토큰에만 있다). 헤드리스 HTTP 는 구조적으로
불가능하다. 선례 = `scripts/seed_dogfood.py`. HTTP + auth 계층만 우회하고 그 아래는 전부
실제 경로를 탄다 — Kill Switch 게이트도 그대로 통과한다.

## 사용

    QB=/path/to/quant-bridge
    set -a; . $QB/apps/api/.env.local; set +a; cd $QB/apps/api

    uv run python scripts/live_session_admin.py status
    uv run python scripts/live_session_admin.py stop    <session_id> --confirm
    uv run python scripts/live_session_admin.py flatten <session_id> --confirm

★**순서는 `stop` → `flatten` 이다.** 세션이 살아 있는 채로 청산하면 다음 tick 에 엔진이
다시 진입한다. 반대로 세션만 끄는 것은 **거래소를 flat 으로 만들지 않는다** — 세션 행을
지우거나 비활성화해도 포지션과 대기 주문은 그대로 남는다(3회 데인 함정).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from src.strategy.repository import StrategyRepository  # noqa: E402
from src.tasks._worker_engine import create_worker_engine_and_sm  # noqa: E402
from src.trading.account_identity import (  # noqa: E402
    dedupe_accounts_by_exchange_uid,
)
from src.trading.dependencies import (  # noqa: E402
    _CeleryOrderDispatcher,
    _StrategySessionsAdapter,
    get_bybit_futures_provider,
    get_encryption_service,
)
from src.trading.models import ExchangeName, LiveSignalSession  # noqa: E402
from src.trading.repositories.exchange_account_repository import (  # noqa: E402
    ExchangeAccountRepository,
)
from src.trading.repositories.kill_switch_event_repository import (  # noqa: E402
    KillSwitchEventRepository,
)
from src.trading.repositories.live_signal_session_repository import (  # noqa: E402
    LiveSignalSessionRepository,
)
from src.trading.repositories.order_repository import OrderRepository  # noqa: E402
from src.trading.services.account_exclusivity import (  # noqa: E402
    AccountExclusivityService,
)
from src.trading.services.account_service import ExchangeAccountService  # noqa: E402
from src.trading.services.close_service import ClosePositionService  # noqa: E402
from src.trading.services.order_service import OrderService  # noqa: E402


def _build_close_service(session: AsyncSession) -> ClosePositionService:
    """`get_close_service` 와 **같은 배선**을 HTTP 밖에서 만든다.

    ★배선을 여기서 새로 발명하지 않는다 — `dependencies.py` 의 조립을 그대로 옮긴 것이며,
    그쪽이 바뀌면 여기도 바꿔야 한다. 이 도구의 목적은 "서비스를 우회하는 것" 이 아니라
    **"서비스를 HTTP 없이 쓰는 것"** 이다.
    """
    from src.core.config import settings
    from src.trading.kill_switch import (
        CumulativeLossEvaluator,
        DailyLossEvaluator,
        KillSwitchEvaluator,
        KillSwitchService,
    )

    bybit = get_bybit_futures_provider()
    account_service = ExchangeAccountService(
        repo=ExchangeAccountRepository(session),
        crypto=get_encryption_service(),
        bybit_futures_provider=bybit,
    )
    order_repo = OrderRepository(session)
    evaluators: list[KillSwitchEvaluator] = [
        CumulativeLossEvaluator(
            order_repo,
            threshold_percent=settings.kill_switch_cumulative_loss_percent,
            capital_base=settings.kill_switch_capital_base_usd,
            balance_provider=account_service,
        ),
        DailyLossEvaluator(
            order_repo,
            threshold_usd=settings.kill_switch_daily_loss_usd,
        ),
    ]
    order_service = OrderService(
        session=session,
        repo=order_repo,
        dispatcher=_CeleryOrderDispatcher(),
        kill_switch=KillSwitchService(
            evaluators=evaluators,
            events_repo=KillSwitchEventRepository(session),
        ),
        sessions_port=_StrategySessionsAdapter(session),
        exchange_service=account_service,
    )
    return ClosePositionService(
        session_repo=LiveSignalSessionRepository(session),
        account_repo=ExchangeAccountRepository(session),
        strategy_repo=StrategyRepository(session),
        account_service=account_service,
        bybit_futures_provider=bybit,
        order_service=order_service,
    )


async def _load_session(session: AsyncSession, session_id: UUID) -> LiveSignalSession:
    sess = await LiveSignalSessionRepository(session).get_by_id(session_id)
    if sess is None:
        raise SystemExit(f"✗ 세션을 찾을 수 없다: {session_id}")
    return sess


async def _cmd_status(symbol: str) -> None:
    """활성 세션 + **계정별 거래소 포지션**.

    ★포지션 조회를 활성 세션에 매달지 않는다. 소크 재시작 직전은 세션이 **없는** 상태이고,
    바로 그때 `FLAT=YES` 를 확인해야 하기 때문이다. 세션에 매달면 "세션이 없다 = 아무것도
    출력 안 함" 이 되어 flat 이 아닌데 flat 으로 읽게 된다.
    """
    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            from sqlalchemy import text

            rows = (
                (
                    await session.execute(
                        text(
                            "SELECT id, symbol, interval, "
                            "  round(EXTRACT(epoch FROM (now() - created_at))/60.0, 1) AS mins "
                            "FROM trading.live_signal_sessions "
                            "WHERE is_active = true ORDER BY created_at"
                        )
                    )
                )
                .mappings()
                .all()
            )
            print(f"활성 세션: {len(rows)}개")
            for row in rows:
                print(f"  {row['id']}  {row['symbol']}  {row['interval']}  {row['mins']}분")

            account_repo = ExchangeAccountRepository(session)
            svc = ExchangeAccountService(
                repo=account_repo,
                crypto=get_encryption_service(),
                bybit_futures_provider=get_bybit_futures_provider(),
            )
            # ★BL-651 — 이 루프는 계정 **행**이 아니라 **실제 거래소 계정**을 돌아야 한다.
            #   같은 `exchange_uid` 를 공유하는 행이 2개면 같은 계정을 두 번 조회하고,
            #   거래소는 두 번 다 **같은 주문**을 돌려준다. 실측(2026-08-08):
            #   `RESTING_CONDITIONAL=2` 인데 실제 조건부 주문은 1건(같은 `link=464fc5ed`),
            #   flatten 직후엔 `=4` 인데 실제 2건 — 정확히 2배가 두 번 재현됐다.
            #   존재 판정(`EXCLUSIVE`)은 배수에 불변이라 지금 깨지는 것은 없지만,
            #   [BL-634] 가드가 이 **개수**를 문턱으로 쓰는 순간 틀린다.
            #
            # ★[BL-605] 의 스윕 루프 처방은 이 자리를 안 고친다 — 다른 루프다. 축만 같다.
            #
            # ★raw SQL 을 걷어내고 repository 를 쓴다 — `exchange_uid`·`read_only` 가
            #   필요한데 그 둘은 이미 모델에 있고, Repository 밖 DB 접근은 금지다.
            #   모집단이 「전 계정」에서 「bybit 계정」으로 좁아지는데, 이 함수는 어차피
            #   `get_bybit_futures_provider()` 로만 조회하므로 **좁히는 쪽이 옳다**.
            accounts = dedupe_accounts_by_exchange_uid(
                list(await account_repo.list_by_exchange(ExchangeName.bybit))
            )
            # 이 원장이 아는 주문 id 전량. 배타성 판별의 **소유권** 축이다.
            # ★내부 id 가 그대로 `orderLinkId` 로 거래소에 나간다는 규약 때문에 이 대조가 결정적이다.
            ledger_order_ids = {
                str(row[0])
                for row in (await session.execute(text("SELECT id FROM trading.orders"))).all()
            }

            print(f"\n거래소 포지션 ({symbol}):")
            any_open = False
            for account in accounts:
                label = account.label or "(no label)"
                creds = await svc.get_credentials_for_order(account.id)
                positions = await get_bybit_futures_provider().fetch_open_positions(creds, symbol)
                for pos in positions:
                    any_open = True
                    print(f"  {label}: {pos.side} {pos.size}")
                if not positions:
                    print(f"  {label}: 없음")

            # ── 미체결(resting) 조건부 주문 + 소유권 ────────────────────────────
            #
            # ★★★왜 **체결 이력**이 아니라 **미체결 주문**을 보는가.
            #   ~~2026-08-08 실측: 미조인 행은 상시 존재한다(34행 전량 ⇒ 판별력 0)~~
            #   ★**그 값은 계정 스코프 없이 센 것이라 틀렸다**(같은 날 재측정, [BL-639]).
            #   계정을 `19a8166a` 로 좁히면 287행 중 **25행(8.7%)** 이고 `ours/exact` 262행은
            #   미조인 **0** 이다. 그래도 결론은 그대로다 — 남은 25 중 12가
            #   `external_manual`(사용자 수동 청산)이라 **정상 상황에서도 난다**. 오염 창에만
            #   몰린 `unknown` 8건은 그 창 하나에서 유도한 값이라 **적합이지 검증이 아니다**.
            #   resting 은 그런 유도 없이 지금 이 순간 그 계정에 걸려 있는 주문이라
            #   「다른 호스트가 붙어 있다」의 직접 증거다.
            #
            # ★`reduce_only=None` 이어야 한다 — 기본값 `True` 는 TP/SL 만 준다.
            #   오염을 만드는 것은 **조건부 진입**(reduce-only 가 아니다)이다.
            #
            # ★★가드가 정상 재기동을 막지 않게 판별자는 반드시 `order_link_id` **소유권**이다.
            #   우리 것까지 「남의 것」으로 세면 영원히 거부된다.
            print(f"\n미체결 조건부 주문 ({symbol}):")
            resting_total = 0
            foreign: list[str] = []
            for account in accounts:
                label = account.label or "(no label)"
                creds = await svc.get_credentials_for_order(account.id)
                orders = await get_bybit_futures_provider().fetch_open_conditional_orders(
                    creds, symbol, reduce_only=None
                )
                resting_total += len(orders)
                for order in orders:
                    link = order.order_link_id
                    owned = link is not None and link in ledger_order_ids
                    if not owned:
                        foreign.append(f"{label}:{order.order_id}:{link or '(link 없음)'}")
                    mark = "ours" if owned else "★FOREIGN"
                    print(
                        f"  {label}: {order.side} {order.kind} qty={order.qty} "
                        f"trigger={order.trigger_price} link={link or '-'} [{mark}]"
                    )
                if not orders:
                    print(f"  {label}: 없음")

            # ★`FLAT=` 은 **한 줄만** 출력한다 — `soak-restart.sh` 가 sed 로 마지막 줄을 긁는다.
            #   포지션 축과 resting 축을 한 낱말에 섞지 않는다. 섞으면 「무엇이 flat 이 아닌가」를
            #   호출부가 되물을 수 없다.
            print(f"\nFLAT={'NO' if any_open else 'YES'}")
            print(f"RESTING_CONDITIONAL={resting_total}")
            print(f"FOREIGN_RESTING={len(foreign)}")
            for item in foreign:
                print(f"  FOREIGN {item}")
            # 계정 배타성 — 원장이 소유권을 주장하지 못하는 resting 이 하나도 없을 때만 YES.
            print(f"EXCLUSIVE={'NO' if foreign else 'YES'}")
            # 재기동 전 「조용한 계정」 — 포지션 0 AND resting 0.
            print(f"QUIET={'NO' if (any_open or resting_total) else 'YES'}")
    finally:
        await engine.dispose()


def _build_session_service(session: AsyncSession) -> Any:
    """`get_live_signal_session_service` 와 **같은 배선**을 HTTP 밖에서 만든다.

    ★`balance_service` 는 등재에 **필수**다 — 그게 `equity_baseline_usdt` 를 채운다.
    손 INSERT 로 세션 행을 만들면 이 값이 비어 **첫 tick 에 자동 비활성화**된다(데인 함정).
    """
    from src.auth.repository import UserRepository
    from src.common.redis_client import get_redis_lock_pool
    from src.trading.services.balance_service import AccountBalanceService
    from src.trading.services.live_session_service import LiveSignalSessionService

    account_repo = ExchangeAccountRepository(session)
    account_service = ExchangeAccountService(
        repo=account_repo,
        crypto=get_encryption_service(),
        bybit_futures_provider=get_bybit_futures_provider(),
    )
    return LiveSignalSessionService(
        repo=LiveSignalSessionRepository(session),
        account_repo=account_repo,
        strategy_repo=StrategyRepository(session),
        balance_service=AccountBalanceService(
            account_repo=account_repo,
            account_service=account_service,
            bybit_futures_provider=get_bybit_futures_provider(),
            redis=get_redis_lock_pool(),
        ),
        # ★[BL-634] — 소크 재시작 경로도 같은 가드를 탄다. 종전의 유일한 강제는
        #   `scripts/soak-restart.sh` 셸 한 곳이었고, 그 셸을 안 거치는 `_cmd_start`
        #   직접 호출은 무방비였다.
        exclusivity_service=AccountExclusivityService(
            account_repo=account_repo,
            order_repo=OrderRepository(session),
            account_service=account_service,
            bybit_futures_provider=get_bybit_futures_provider(),
        ),
        user_repo=UserRepository(session),
    )


async def _cmd_start(strategy_id: UUID, account_id: UUID, symbol: str, interval: str) -> None:
    """세션을 **서비스 계층으로** 등재한다 (소크 재시작).

    ★HTTP 는 헤드리스 불가(Clerk `azp`)이고 손 INSERT 는 `equity_baseline_usdt` 를 건너뛴다.
    ★등재 **전에** 거래소가 flat 인지 `status` 로 확인해라 — 세션 등재는 아무것도 청산하지 않는다.
    """
    from src.trading.schemas import RegisterLiveSessionRequest

    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            account = await ExchangeAccountRepository(session).get_by_id(account_id)
            if account is None:
                raise SystemExit(f"✗ 거래소 계정을 찾을 수 없다: {account_id}")
            service = _build_session_service(session)
            request = RegisterLiveSessionRequest(
                strategy_id=strategy_id,
                exchange_account_id=account_id,
                symbol=symbol,
                interval=interval,
            )
            created = await service.register(account.user_id, request)
            print(f"✓ 세션 등재: {created.id}")
            print(f"  T0={created.created_at}  equity_baseline={created.equity_baseline_usdt}")
            print("  ★`.soak/session` 을 이 id 로 갱신하고 `soak-observe.sh --baseline` 을 돌려라.")
    finally:
        await engine.dispose()


async def _cmd_stop(session_id: UUID) -> None:
    """세션만 비활성화한다. ★거래소는 이것으로 flat 이 되지 않는다."""
    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            sess = await _load_session(session, session_id)
            from src.trading.services.live_session_service import LiveSignalSessionService

            # `balance_service` / `exclusivity_service` / `user_repo` 는 **등록 경로
            # 전용**이다(equity baseline · 계정 배타성 · 데모 안정일수 검증).
            # `deactivate` 는 셋 다 건드리지 않으므로 여기서는 넘기지 않는다 — 조립을
            # 위해 안 쓰는 의존성을 억지로 만들지 않는다.
            # ★[BL-634] 가 `exclusivity_service` 를 **필수 인자**로 만들었을 때 이 자리를
            #   빠뜨려 `stop` 이 즉시 `TypeError` 로 죽었다. mypy 는 `src/` 만 보고
            #   `scripts/` 는 안 보며, `_cmd_stop` 에는 테스트가 없었다 — 그래서 아래
            #   `test_stop_can_still_assemble_the_session_service` 를 같이 뒀다.
            service = LiveSignalSessionService(
                repo=LiveSignalSessionRepository(session),
                account_repo=ExchangeAccountRepository(session),
                strategy_repo=StrategyRepository(session),
                balance_service=None,  # type: ignore[arg-type]
                exclusivity_service=None,  # type: ignore[arg-type]
            )
            await service.deactivate(sess.user_id, session_id)
            print(f"✓ 세션 비활성화: {session_id}")
            print("  ★거래소는 아직 flat 이 아니다 — `flatten` 을 이어서 실행해라.")
    finally:
        await engine.dispose()


async def _cmd_flatten(session_id: UUID) -> None:
    """`ClosePositionService` 로 청산한다 — **`Order` 행이 남는다**(BL-593 의 핵심)."""
    engine, sm = create_worker_engine_and_sm()
    try:
        async with sm() as session:
            sess = await _load_session(session, session_id)
            service = _build_close_service(session)
            try:
                response = await service.close_position(sess.user_id, session_id)
            except Exception as exc:  # HTTPException(409 no_open_position) 등
                detail = getattr(exc, "detail", None) or str(exc)
                if detail == "no_open_position":
                    print("✓ 이미 flat 이다 (no_open_position). 주문을 내지 않았다.")
                    return
                if isinstance(detail, dict) and detail.get("code") == "resting_conditional_entries":
                    message = detail.get("detail") or (
                        f"포지션은 없지만 미체결 진입 주문 {detail.get('count', 0)}건이 남아 있다."
                    )
                    print(f"✗ {message}")
                    for order in detail.get("orders", []):
                        print(
                            f"  order_id={order['order_id']} side={order['side']} "
                            f"qty={order['qty']} trigger={order['trigger_price']} "
                            f"link={order['order_link_id'] or '-'}"
                        )
                    # 3은 일반 청산 실패 1과 달라야 자동화가 잔존 진입을 분기할 수 있다.
                    raise SystemExit(3) from exc
                raise SystemExit(f"✗ 청산 실패: {detail}") from exc
            await session.commit()
            print(f"✓ 청산 주문 접수: order_id={response.order_id} state={response.state}")
            # ★BL-684 — 원장 검증 안내를 **rc 4 분기보다 먼저** 찍는다. 잔량이 남은 회차야말로
            #   청산이 실제로 체결됐는지 확인해야 하는데, 안내를 exit 뒤에 두면 그 상황에서만
            #   사라진다(가장 필요한 자리에서 없어진다).
            print("  ★원장에 남았다 — 체결은 비동기다. `exchange_exits` 에서")
            print("    `external_manual` 이 늘지 않고 `ours` 가 느는지로 검증해라.")
            if response.resting_entries_unknown:
                print("  ⚠ 미체결 진입 주문 확인 실패(거래소 조회 오류). 청산 주문은 접수됐다.")
                # 4는 「주문 접수 + 잔량/확인 실패」다 — 「주문 미발행」인 3과도, 실패 1과도 다르다.
                raise SystemExit(4)
            if response.resting_entries:
                print(f"  ⚠ 미체결 진입 주문 {len(response.resting_entries)}건이 남아 있다.")
                for order in response.resting_entries:
                    print(
                        f"  order_id={order.order_id} side={order.side} "
                        f"qty={order.qty} trigger={order.trigger_price} "
                        f"link={order.order_link_id or '-'}"
                    )
                raise SystemExit(4)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    status_parser = sub.add_parser("status", help="활성 세션 + 계정별 거래소 포지션")
    status_parser.add_argument("--symbol", default="BTC/USDT")

    start_parser = sub.add_parser("start", help="세션 등재 (소크 재시작)")
    start_parser.add_argument("--strategy-id", required=True)
    start_parser.add_argument("--account-id", required=True)
    start_parser.add_argument("--symbol", default="BTC/USDT")
    start_parser.add_argument("--interval", default="1m", choices=("1m", "5m", "15m", "1h"))
    start_parser.add_argument("--confirm", action="store_true", required=True)
    for name, help_text in (
        ("stop", "세션 비활성화 (거래소는 flat 안 됨)"),
        (
            "flatten",
            "reduce-only 시장가 청산 — rc 0=flat/잔량 없음, 1=실패, 3=미발행 잔량, 4=접수 후 잔량/확인 실패",
        ),
    ):
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument("session_id")
        sp.add_argument("--confirm", action="store_true", required=True)

    args = parser.parse_args()
    if args.command == "status":
        asyncio.run(_cmd_status(args.symbol))
    elif args.command == "start":
        asyncio.run(
            _cmd_start(UUID(args.strategy_id), UUID(args.account_id), args.symbol, args.interval)
        )
    elif args.command == "stop":
        asyncio.run(_cmd_stop(UUID(args.session_id)))
    elif args.command == "flatten":
        asyncio.run(_cmd_flatten(UUID(args.session_id)))


if __name__ == "__main__":
    main()
