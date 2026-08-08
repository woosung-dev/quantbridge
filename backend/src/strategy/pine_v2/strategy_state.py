"""Pine `strategy.*` 실행 상태 (Week 2 Day 4).

ADR-011 §6 H1 MVP scope 엄수 (#19 PR):
- In-scope: strategy.entry(long/short), strategy.close, strategy.close_all
- H2+ 이연: trail_points, qty_percent (분할익절), pyramiding, stop/limit 쌍 OCO 지연 체결

Day 4 단순화:
- 시장가(market) entry만 — 주문 즉시 현재 bar close에서 체결
- 단일 포지션 슬롯 (id별 중복 진입 시 기존 덮어씀)
- stop=/limit= 인자가 있으면 현 구현 범위 밖 → 경고 로그 후 무시 (NOP)
- 수수료/슬리피지 Day 4 범위 밖 (Week 3 또는 별도 Sprint)
- PnL은 청산 시점에 기록

공개 API:
- `StrategyState` — entry/close/close_all 호출 + 체결 결과
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, NamedTuple

from src.strategy.pine_v2.exit_orders import SAME_BAR_FILL_PRIORITY, ExitOrderKind
from src.strategy.pine_v2.leverage_model import (
    is_leverage_active,
    liquidation_price,
    margin_available_ok,
    required_margin,
)

Direction = Literal["long", "short"]


@dataclass
class MarketIntent:
    """fill_timing=next_bar_open 용 시장가 인텐트 (TV parity).

    bar N 신호 → 큐 등록 → bar N+1 시가에 체결 (TV `process_orders_on_close=false`
    기본 동작). qty=None 이면 체결 시가 기준 default sizing (compute_qty) — TV 의
    percent_of_equity 가 체결가로 sizing 되는 것과 정합.
    """

    kind: Literal["entry", "close", "close_all"]
    trade_id: str
    direction: Direction = "long"  # entry 만 의미
    qty: float | None = None  # None = 체결 시 default sizing
    comment: str = ""
    placed_bar: int = 0


@dataclass
class PendingOrder:
    """Stop/Limit 지연 체결 주문.

    - direction='long', stop=price: BUY STOP (high >= price에서 fill, 돌파 매수)
    - direction='short', stop=price: SELL STOP (low <= price에서 fill, 돌파 매도)
    - limit 주문(가격 도달 시 지정가 체결)은 H1 MVP scope 외 — 추후 확장
    """

    id: str
    direction: Direction
    qty: float
    stop_price: float
    placed_bar: int
    comment: str = ""

    def try_fill(self, bar: int, high: float, low: float, open_: float) -> float | None:
        """이 bar의 OHLC로 체결 가능한지 판단. 체결 시 fill price 반환, 아니면 None.

        Pine 표준: stop price가 bar open과 high/low 사이면 stop price에 체결,
        bar open이 이미 stop을 넘어섰으면 open에 체결 (갭).
        """
        if self.placed_bar >= bar:
            # 같은 bar에서 즉시 체결 방지 (Pine 표준: 다음 bar부터 체결 가능)
            return None
        if self.direction == "long":
            # BUY STOP: high가 stop_price에 도달해야 fill
            if high >= self.stop_price:
                return max(open_, self.stop_price)
        else:  # short
            # SELL STOP: low가 stop_price에 도달해야 fill
            if low <= self.stop_price:
                return min(open_, self.stop_price)
        return None


@dataclass
class ExitOrder:
    """OCO TP/SL/Trailing exit-order 단일 leg (BL-104).

    하나의 open 포지션을 청산하는 exit. `position_direction` = 청산 대상 포지션의
    방향이고, 실제 체결은 그 반대편(long → SELL, short → BUY). 한 entry 에 대해
    SL+TP 두 leg(또는 trailing) 가 같은 `from_entry` 로 묶여 OCO 형제를 이룬다.

    - TAKE_PROFIT: limit. long → high>=limit, short → low<=limit. gap-through → open.
    - STOP_LOSS: stop. long → low<=stop, short → high>=stop. gap-through → open.
    - TRAILING_STOP: trail_offset 만큼 떨어진 stop. anchor 가 유리방향으로만 ratchet.
    float 유지 — pine_v2 가격 관례 (Decimal 경계는 cost SSOT).
    """

    from_entry: str
    exit_id: str
    position_direction: Direction
    kind: ExitOrderKind
    placed_bar: int
    stop_price: float | None = None
    limit_price: float | None = None
    trail_offset: float | None = None
    trail_anchor: float | None = None  # trailing 최적가 추적 (runtime)
    comment: str = ""

    def update_trailing(self, high: float, low: float) -> None:
        """trailing anchor 를 유리방향으로만 갱신 (ratchet). 비-trailing 은 no-op."""
        if self.kind != ExitOrderKind.TRAILING_STOP or self.trail_offset is None:
            return
        if self.position_direction == "long":
            self.trail_anchor = high if self.trail_anchor is None else max(self.trail_anchor, high)
        else:
            self.trail_anchor = low if self.trail_anchor is None else min(self.trail_anchor, low)

    def _trail_stop_level(self) -> float | None:
        if self.trail_anchor is None or self.trail_offset is None:
            return None
        if self.position_direction == "long":
            return self.trail_anchor - self.trail_offset
        return self.trail_anchor + self.trail_offset

    def try_fill_exit(self, *, bar: int, open_: float, high: float, low: float) -> float | None:
        """이 bar OHLC 로 exit 체결 가능한지 판단. 체결가 반환, 아니면 None.

        placed_bar >= bar 면 같은 bar 즉시 체결 금지 (entry 관례 일치).
        """
        if self.placed_bar >= bar:
            return None
        if self.kind == ExitOrderKind.TAKE_PROFIT:
            lp = self.limit_price
            if lp is None:
                return None
            if self.position_direction == "long":
                return max(open_, lp) if high >= lp else None
            return min(open_, lp) if low <= lp else None
        if self.kind == ExitOrderKind.STOP_LOSS:
            sp = self.stop_price
            if sp is None:
                return None
            if self.position_direction == "long":
                return min(open_, sp) if low <= sp else None
            return max(open_, sp) if high >= sp else None
        # TRAILING_STOP
        level = self._trail_stop_level()
        if level is None:
            return None
        if self.position_direction == "long":
            return min(open_, level) if low <= level else None
        return max(open_, level) if high >= level else None


@dataclass
class Trade:
    id: str
    direction: Direction
    qty: float
    entry_bar: int
    entry_price: float
    exit_bar: int | None = None
    exit_price: float | None = None
    pnl: float | None = None
    comment: str = ""
    # BL-104 — 청산 leg 종류 (TP/SL/Trailing). market close/flip 등 일반 청산은 None.
    # C6 비용 split(maker/taker) 의 입력. exit_kind=None → taker (byte-identical).
    exit_kind: ExitOrderKind | None = None
    # BL-186a — 격리 레버리지 강제청산 여부와 진입 시 계산한 청산가.
    liquidated: bool = False
    liq_price: float | None = None
    # BL-186a — 격리 증거금. 가용 증거금은 open trade 합계에서 파생한다.
    margin_used: float | None = None

    @property
    def is_open(self) -> bool:
        return self.exit_bar is None

    @property
    def is_liquidation(self) -> bool:
        """강제청산으로 종료된 거래인지 반환한다."""
        return self.liquidated

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "direction": self.direction,
            "qty": self.qty,
            "entry_bar": self.entry_bar,
            "entry_price": self.entry_price,
            "exit_bar": self.exit_bar,
            "exit_price": self.exit_price,
            "pnl": self.pnl,
            "comment": self.comment,
            "liquidated": self.liquidated,
        }


@dataclass(frozen=True, slots=True)
class LedgerSeedLeg:
    """주문 원장이 증언하는 포지션 1건 — `seed_positions_from_ledger` 의 입력 (BL-544).

    체결 1건당 leg 1개다. 여러 체결을 합쳐 하나로 만들면 안 된다 — `open_trades` 는
    trade id 가 key 이고 `strategy.close(id)` 는 그 id 하나만 pop 하므로, 합치는 순간
    Pine 의 trade-id 의미론이 깨진다.
    """

    trade_id: str
    direction: Direction
    qty: float
    entry_price: float


@dataclass(frozen=True, slots=True)
class LedgerConditionalFill:
    """주문 원장이 증언하는 **조건부 진입 체결** 1건 (ADR-025 / BL-595).

    `LedgerSeedLeg`(포지션 스냅샷)와 다르다. 이쪽은 **사건**이다 — 「그 `trade_id` 의
    조건부 진입이 이 시각에 이 가격으로 체결됐다」. 그래서 수량을 싣지 않는다:
    원장의 `filled_quantity` 는 반전 시 청산+진입이 합쳐진 **병합 수량**(실측 0.058)이고
    엔진의 leg 수량(0.0297)과 단위가 다르다. 병합 수량을 그대로 쓰면 이 레포가 [ADR-022]
    에서 이미 덴 「net 은 맞고 legs 는 틀리다」를 반복한다. 수량은 엔진의 `PendingOrder.qty`
    를 그대로 쓰고, 이 타입은 **체결 여부와 체결가**만 증언한다.

    ★`filled_at` 은 거래소 체결시각이 아니라 **우리 관측시각**이다(`LedgerFill` docstring).
    항상 실제보다 **늦으므로** 봉 귀속도 같거나 늦은 봉을 고른다 — 오차 방향이 한쪽이고
    그 방향은 무해한 `replay_lag` 쪽이지 유령 쪽이 아니다.
    """

    trade_id: str
    filled_at: datetime
    fill_price: float


@dataclass(frozen=True, slots=True)
class ConditionalFillAuthority:
    """라이브에서 조건부 진입 체결의 **권한자** — 봉 인덱스 → 그 봉이 증언하는 체결들.

    ★**존재 자체가 신호다.** `None`(= 이 객체가 없다) 은 「모른다」이고 엔진이 종전대로
    시뮬한다(= 백테스트). 이 객체가 있으면 — **`by_bar` 가 비어 있어도** — 「원장이 답했다」
    이고 엔진은 증언 없는 체결을 만들지 않는다. 둘을 같은 값으로 접으면 판정 불가가 flat
    으로 위장된다(`ledger_position.py` 가 같은 교훈을 적어 두었다).
    """

    by_bar: dict[int, tuple[LedgerConditionalFill, ...]]
    # 창 시작보다 앞서 관측돼 어느 봉에도 못 얹은 체결 수. 「거래소에는 있는데 엔진이
    # 표현할 수 없는 포지션」의 개수이며, 조용히 버리지 않으려고 세어 둔다.
    dropped_before_window: int = 0
    # ★census 를 셀 봉. `None` 이면 **모든 봉**에서 센다(단위 테스트용).
    #
    # ★★왜 필요한가 — 프로덕션 실측으로 확정된 것이다. 모든 봉에서 세면 매 tick 300봉
    # warmup 을 **다시** 세어 카운터가 tick 당 **정확히 +121** 로 자란다(2026-08-05 소크
    # 실측). 그러면 「이 tick 의 판정에서 [BL-595] 순간이 일어났나」를 그 값으로 물을 수
    # 없다 — 사건과 무관하게 항상 크다. 사전등록 관측량이 **판별력 0** 이 되는 것이다.
    # ⇒ 이 tick 이 **실제로 판정하는 봉**(마지막 봉)에서만 센다.
    # ★한계: 더 앞선 봉에 얹힌 원장 체결은 **적용되지만 계상되지 않는다**(행위는 그대로).
    census_bar: int | None = None

    def for_bar(self, bar: int) -> tuple[LedgerConditionalFill, ...]:
        return self.by_bar.get(bar, ())

    def counts_census(self, bar: int) -> bool:
        return self.census_bar is None or bar == self.census_bar


@dataclass
class TradeEvent:
    """Sprint 26 codex G.0 P1 #2 — bar-level entry/close/fill event log.

    `run_live` (Phase B) 가 마지막 bar 의 event 만 LiveSignalEvent outbox 로
    변환. final-state diff 방식은 same-bar entry+close 를 entry 로 감지 못 함 →
    명시적 event log 가 필요.

    sequence_no: 같은 bar 안 event 순서 (0-based). same-bar entry+close 시
    entry sequence_no=0 + close sequence_no=1.

    broker_filled: 이 이벤트가 **broker 가 이미 체결한 것을 엔진이 뒤늦게 재도출한
    기록**인가 (BL-560). `action="fill"` 이 이름만으로 뜻하던 것을 값으로 옮긴 것이며,
    그 fill 에 딸려 나온 반전 청산(`_flip_opposite_positions`)까지 포함한다. 원장에는
    그대로 남지만 거래소 지시로는 재발신하면 안 된다 — 이미 닫힌 포지션을 또 닫으라는
    주문이 되어 `110017 reduce-only ... same side` 로 거절된다.
    """

    bar_index: int
    action: Literal["entry", "close", "fill"]
    direction: Direction
    trade_id: str
    qty: float
    price: float
    sequence_no: int
    comment: str = ""
    broker_filled: bool = False


class ExitLevels(NamedTuple):
    """Phase 3 — 현재 포지션의 라이브 placement 용 exit 레벨 (pine_v2 float 관례).

    take_profit = TP leg limit_price / stop_loss = SL leg stop_price /
    trailing_stop = Trail leg trail_offset (quote 거리). 레그 부재 시 None.
    """

    take_profit: float | None
    stop_loss: float | None
    trailing_stop: float | None


@dataclass
class StrategyState:
    """포지션 상태 + 체결 기록.

    단일 포지션 가정 — id별 슬롯이지만 한 번에 하나의 id만 open 권장.
    """

    open_trades: dict[str, Trade] = field(default_factory=dict)
    closed_trades: list[Trade] = field(default_factory=list)
    # pending 주문: id → PendingOrder (stop/limit 아직 미체결)
    pending_orders: dict[str, PendingOrder] = field(default_factory=dict)
    # BL-104 — pending exit 브래킷: from_entry(trade id) → OCO leg 리스트.
    # 비어있으면 check_exit_fills no-op → strategy.exit 미사용 시 byte-identical.
    pending_exits: dict[str, list[ExitOrder]] = field(default_factory=dict)
    # 경고/미지원 파라미터 추적 (`limit=`, `trail_points=` 등) — 사용자에게 알림용
    warnings: list[str] = field(default_factory=list)
    # 진입이 엔진 게이트에서 삼켜진 구조화된 기록. warnings 소비처와 분리한다.
    entry_skips: list[dict[str, Any]] = field(default_factory=list)
    # Sprint 26 codex G.0 P1 #2 — bar-level event log. `run_live` 가 마지막 bar 의
    # entry/close 만 LiveSignalEvent outbox 로 변환. same-bar entry+close 회귀 방어.
    events: list[TradeEvent] = field(default_factory=list)
    # Sprint 37 BL-185 — Pine strategy() 포지션 사이징 spot-equivalent.
    # configure_sizing() 호출 시 초기화. 미호출 시 compute_qty()=1.0 fallback (기존 호환).
    initial_capital: float | None = None
    running_equity: float | None = None
    default_qty_type: str | None = (
        None  # "strategy.percent_of_equity" | "strategy.cash" | "strategy.fixed" | None
    )
    default_qty_value: float | None = None
    # BL-186a — 1.0 이하는 기존 현물 경로, 초과 시 격리 레버리지 모델을 적용한다.
    leverage: float = 1.0
    # BL-186a — 실행 중 발생한 격리 강제청산 횟수.
    liquidation_count: int = 0
    # BL-460 — 증거금 게이트 **전용** net 자본과 그 비용률.
    #
    # `running_equity` 는 gross 다(`close()` 가 pnl 만 누적 — "fees=0 Sprint 37 가정").
    # 그 값은 `compute_qty`(percent_of_equity) 입력이자 Pine `strategy.equity` 라서
    # net 으로 바꾸면 leverage=1 byte-identity 가 즉시 깨진다. 그래서 게이트가 볼
    # 자본만 따로 누적한다 — 두 값은 **의도적으로 다르다**.
    #
    # `taker_cost_rate` = leg 당 (수수료 + 슬리피지) 비율. 엔진의 모든 체결은 taker
    # 이므로(`v2_adapter._leg_cost` docstring 의 grounding) 단일 비율로 재현된다.
    # 기본값 0.0 = 두 자본이 항상 같음 → 기존 전 호출부와 판정 구분 불가(회귀 0).
    taker_cost_rate: float = 0.0
    gate_equity: float | None = None
    # Sprint 38 BL-188 v3 — entry placement + pending fill 양쪽에 적용되는 trading session gate.
    # event_loop / virtual_strategy 가 cfg.trading_sessions 로 주입. 비어있으면 24h (회귀 0).
    # 단일 reference: src.strategy.trading_sessions.is_allowed (Live `is_allowed` 와 동일 함수).
    sessions_allowed: tuple[str, ...] = ()
    # BL-104 — pyramiding cap. 같은 방향 최대 동시 open entry 수. None 이면 cap 무효
    # (기존 무제한 중첩 동작 byte-identical). strategy(pyramiding=N) 선언 시 주입.
    pyramiding: int | None = None
    # TV parity — 시장가 체결 타이밍. "bar_close"(기본, 신호 bar 종가 즉시) |
    # "next_bar_open"(다음 bar 시가 — TV process_orders_on_close=false 기본).
    # run_historical/run_virtual_strategy 가 주입. 기본값 = 기존 동작 byte-identical.
    fill_timing: str = "bar_close"
    # next_bar_open 모드의 시장가 인텐트 큐 — process_market_intents 가 소비.
    pending_market_intents: list[MarketIntent] = field(default_factory=list)
    # ADR-025 — 원장 권한이 켜진 재생에서 「시뮬이 하려던 것 vs 원장이 증언한 것」 census.
    # 백테스트(권한 없음)에서는 **항상 비어 있다** — 그래서 최종상태 비교가 안 깨진다.
    # 키: agree / engine_only_suppressed / ledger_only_adopted / ledger_only_orphan.
    ledger_fill_census: dict[str, int] = field(default_factory=dict)

    def discard_state_before_epoch(self) -> None:
        """position epoch 이전 재생이 만든 포지션 및 손익 상태를 폐기한다.

        warmup 재생에서 outbox 발행 허용 시점 이전에 열린 거래는 실제 거래소 주문으로
        이어진 적이 없으므로, open/closed 거래와 exit 브래킷, 강제청산 횟수를 모두
        없던 일로 만든다. 사이징이 과거 가상 손익을 쓰지 않도록 running_equity 도
        configure_sizing()이 받은 initial_capital 로 되돌린다. 폐기 과정은 close 이벤트나
        closed_trades 기록을 만들지 않는다.

        pending_orders, pending_market_intents, events, warnings, entry_skips 는 유지한다.
        특히 epoch 직전 bar 의 next_bar_open 시장가 인텐트는 epoch bar 에 체결되어 그
        bar 의 outbox 대상이 될 수 있다. 단, 그 인텐트가 close_all 이면 close_all 자체의
        기존 계약에 따라 pending_orders 와 pending_exits 를 비울 수 있다.
        """
        self.open_trades.clear()
        self.pending_exits.clear()
        self.closed_trades.clear()
        self.liquidation_count = 0
        if self.running_equity is not None:
            self.running_equity = self.initial_capital
        # BL-460 — 게이트 전용 net 도 같은 이유로 되돌린다. 안 되돌리면 폐기된 재생이
        # 물린 비용이 남아 게이트만 조용히 빡빡해진다.
        if self.gate_equity is not None:
            self.gate_equity = self.initial_capital

    def seed_positions_from_ledger(
        self, legs: Sequence[LedgerSeedLeg], *, bar: int
    ) -> tuple[str, ...]:
        """주문 원장이 증언하는 포지션을 재생 상태로 채택한다. 채택한 trade id 들을 돌려준다.

        `discard_state_before_epoch` 의 대칭이다 — 그쪽은 재생이 **지어낸** 포지션을 지우고,
        이쪽은 재생이 **놓친** 포지션을 들여온다(BL-544). 대상은 평가 공백 동안 거래소에서
        체결됐지만 재생이 재도출하지 못한 진입이다. 조건부 진입의 trigger 는 tick 마다
        재도출되므로(실측 이동 64235.3 → 64166.7) 공백이 지나면 재생은 그 체결을 아예
        만들지 않는다.

        ★**멱등** — 이미 open 포지션이 하나라도 있으면 아무것도 하지 않는다. 재생이 같은
        진입을 스스로 다시 만들었을 수 있고, 그때 더하면 이중 계상이다. 감량·반전을 맞추는
        것도 이 메서드의 책임이 아니다 — 그런 상태는 호출부의 거래소 대조가 불일치로 잡아
        fail-closed 로 죽인다. 채택은 "엔진이 완전히 비어 있을 때 원장을 믿는다" 하나뿐이다.

        정상 진입(`_open_trade`)과 **의도적으로** 다른 점 둘:

        - **증거금 게이트를 돌리지 않는다.** 그 포지션은 이미 거래소에 존재한다. 여기서
          거절해도 현실은 되돌아가지 않고, 엔진만 그 포지션을 모르는 상태가 유지된다.
        - **`_record_event` 를 하지 않는다.** 이벤트를 남기면 outbox 가 **이미 나간 주문을
          다시 낸다.**

        `liq_price` / `margin_used` 는 `_open_trade` 와 같은 helper 로 채운다 — 비워두면
        `check_liquidations` 가 이 포지션만 조용히 건너뛴다.
        """
        if not legs or self.open_trades:
            return ()
        leveraged = is_leverage_active(self.leverage)
        for leg in legs:
            self.open_trades[leg.trade_id] = Trade(
                id=leg.trade_id,
                direction=leg.direction,
                qty=leg.qty,
                entry_bar=bar,
                entry_price=leg.entry_price,
                comment="ledger_seed",
                liq_price=(
                    liquidation_price(
                        entry_price=leg.entry_price,
                        direction=leg.direction,
                        leverage=self.leverage,
                    )
                    if leveraged
                    else None
                ),
                margin_used=(
                    required_margin(
                        qty=leg.qty,
                        price=leg.entry_price,
                        leverage=self.leverage,
                    )
                    if leveraged
                    else None
                ),
            )
        return tuple(leg.trade_id for leg in legs)

    # ---- Sprint 37 BL-185: 포지션 사이징 (spot-equivalent) ------------

    def configure_sizing(
        self,
        *,
        initial_capital: float,
        default_qty_type: str | None = None,
        default_qty_value: float | None = None,
        leverage: float = 1.0,
        taker_cost_rate: float = 0.0,
    ) -> None:
        """백테스트 시작 시 1회 호출. running_equity 초기화 + Pine default_qty_* 등록.

        BL-185: running_equity 갱신 = closed_trades PnL 누적 (fees=0 Sprint 37 가정).
        BL-186a: leverage 는 주문 수량이 아닌 증거금 게이트와 청산가에만 사용한다.
        BL-460: taker_cost_rate 지정 시 게이트 전용 net 자본(`gate_equity`)이 leg 마다
        비용을 차감한다. 미지정(0.0)이면 gross 와 항상 같아 기존 판정과 구분 불가하다.
        """
        self.initial_capital = float(initial_capital)
        self.running_equity = float(initial_capital)
        self.default_qty_type = default_qty_type
        self.default_qty_value = float(default_qty_value) if default_qty_value is not None else None
        self.leverage = float(leverage)
        self.taker_cost_rate = float(taker_cost_rate)
        self.gate_equity = float(initial_capital)

    def compute_qty(self, *, fill_price: float) -> float:
        """default_qty_type/value 기반 entry qty 계산.

        - configure_sizing 미호출 또는 default_qty_type=None → 1.0 (기존 qty=1 호환)
        - percent_of_equity → running_equity * pct / 100 / fill_price
        - cash → cash / fill_price
        - fixed → value (fill_price 무관)
        - fill_price <= 0 시 percent_of_equity / cash 는 0.0 (DivisionByZero 차단)
        - 미지원 default_qty_type 문자열 → 1.0 (silent drift 방지 + warning 미발행 unit-level)
        """
        if (
            self.default_qty_type is None
            or self.default_qty_value is None
            or self.running_equity is None
        ):
            return 1.0
        qt = self.default_qty_type
        qv = self.default_qty_value
        if qt == "strategy.percent_of_equity":
            if fill_price <= 0:
                return 0.0
            return self.running_equity * qv / 100.0 / fill_price
        if qt == "strategy.cash":
            if fill_price <= 0:
                return 0.0
            return qv / fill_price
        if qt == "strategy.fixed":
            return qv
        return 1.0

    def _next_sequence_no(self, bar: int) -> int:
        """같은 bar 안 event 순서 (0-based)."""
        return sum(1 for e in self.events if e.bar_index == bar)

    def _record_event(
        self,
        *,
        bar: int,
        action: Literal["entry", "close", "fill"],
        direction: Direction,
        trade_id: str,
        qty: float,
        price: float,
        comment: str = "",
        broker_filled: bool = False,
    ) -> None:
        """TradeEvent 추가 — sequence_no 자동 할당."""
        self.events.append(
            TradeEvent(
                bar_index=bar,
                action=action,
                direction=direction,
                trade_id=trade_id,
                qty=qty,
                price=price,
                sequence_no=self._next_sequence_no(bar),
                comment=comment,
                broker_filled=broker_filled,
            )
        )

    def _record_entry_skip(self, *, bar: int, reason: str, trade_id: str) -> None:
        """엔진 게이트가 삼킨 진입을 구조화해 기록한다."""
        skip = {"bar_index": bar, "reason": reason, "trade_id": trade_id}
        if self.entry_skips[-1:] == [skip]:
            return
        self.entry_skips.append(skip)

    def _leg_cost(self, *, qty: float, price: float) -> float:
        """단일 체결(leg)의 taker 비용. BL-460 게이트 전용 net 자본에만 쓴다.

        `v2_adapter._leg_cost` 와 같은 공식(notional × 비율)이며, 그쪽이 리포트용
        Decimal 정밀 비용의 SSOT 다. 여기서는 게이트 판정용 float 추정치면 충분하다.
        """
        return abs(qty) * price * self.taker_cost_rate

    def _can_afford_entry(
        self,
        *,
        trade_id: str,
        direction: Direction,
        qty: float,
        fill_price: float,
    ) -> bool:
        """flip/close 부작용을 내기 전에 진입 가능 여부를 판정한다.

        flip은 반대방향 전부와 동일 id를 청산하므로 그 증거금은 해제되고 PnL이
        실현된다. 두 효과를 모두 반영한 사후 상태로 판정해 주문 전체 거부와 맞춘다.

        ★BL-460 — 기준 자본은 `running_equity`(gross)가 아니라 `gate_equity`(net)다.
        청산될 포지션의 **exit leg 비용까지** 미리 빼야 실제로 close 가 일어난 뒤의
        `_open_trade` 게이트와 같은 값에 도달한다(둘이 어긋나면 preflight 가 거짓말한다).
        """
        if not is_leverage_active(self.leverage) or self.gate_equity is None:
            return True

        opposite: Direction = "short" if direction == "long" else "long"
        closing_ids = {
            tid
            for tid, trade in self.open_trades.items()
            if trade.direction == opposite or tid == trade_id
        }
        post_close_equity = self.gate_equity + sum(
            (fill_price - trade.entry_price)
            * trade.qty
            * (1.0 if trade.direction == "long" else -1.0)
            - self._leg_cost(qty=trade.qty, price=fill_price)
            for tid, trade in self.open_trades.items()
            if tid in closing_ids
        )
        available = post_close_equity - sum(
            trade.margin_used or 0.0
            for tid, trade in self.open_trades.items()
            if tid not in closing_ids
        )
        required = required_margin(
            qty=qty,
            price=fill_price,
            leverage=self.leverage,
        )
        return margin_available_ok(required=required, available=available)

    def _open_trade(
        self,
        *,
        trade_id: str,
        direction: Direction,
        qty: float,
        bar: int,
        fill_price: float,
        comment: str,
        event_action: Literal["entry", "fill"],
        enforce_margin: bool = True,
    ) -> Trade | None:
        """마진 게이트 후 청산가를 계산해 Trade를 생성하는 유일한 관문.

        ★`enforce_margin=False` 는 **원장이 증언한 체결**(ADR-025)에만 쓴다. 그 포지션은
        이미 거래소에 존재하므로 여기서 거절해도 현실은 되돌아가지 않고, 엔진만 그 포지션을
        모르는 상태가 유지된다 — 이 ADR 이 없애려는 바로 그 상태다.
        `seed_positions_from_ledger`(`:357` 근방)가 같은 이유로 게이트를 안 돌린다.
        ★단 `margin_used`/`liq_price` 는 **그대로 계산한다.** 비워두면 `check_liquidations`
        가 이 포지션만 조용히 건너뛴다(그쪽 docstring 이 적어 둔 함정).
        """
        margin_used: float | None = None
        liq_price: float | None = None
        if is_leverage_active(self.leverage):
            if self.gate_equity is not None:
                required = required_margin(
                    qty=qty,
                    price=fill_price,
                    leverage=self.leverage,
                )
                # BL-460 — gross(`running_equity`)가 아니라 net(`gate_equity`) 기준.
                available = self.gate_equity - sum(
                    trade.margin_used or 0.0 for trade in self.open_trades.values()
                )
                margin_used = required
                if enforce_margin and not margin_available_ok(
                    required=required, available=available
                ):
                    self.warnings.append(f"strategy.entry({trade_id!r}): 증거금 부족으로 진입 skip")
                    self._record_entry_skip(
                        bar=bar,
                        reason="margin_insufficient",
                        trade_id=trade_id,
                    )
                    return None
            liq_price = liquidation_price(
                entry_price=fill_price,
                direction=direction,
                leverage=self.leverage,
            )

        trade = Trade(
            id=trade_id,
            direction=direction,
            qty=qty,
            entry_bar=bar,
            entry_price=fill_price,
            comment=comment,
            liq_price=liq_price,
            margin_used=margin_used,
        )
        self.open_trades[trade_id] = trade
        # BL-460 — 진입 leg 비용은 체결 즉시 net 에서 뺀다. 청산 때 몰아서 빼면 포지션을
        # 들고 있는 동안 게이트가 낙관적으로 보인다.
        if self.gate_equity is not None:
            self.gate_equity -= self._leg_cost(qty=qty, price=fill_price)
        self._record_event(
            bar=bar,
            action=event_action,
            direction=direction,
            trade_id=trade_id,
            qty=qty,
            price=fill_price,
            comment=comment,
        )
        return trade

    # ---- 포지션 정보 (strategy.position_size 등 built-in 응답) -------

    @property
    def position_size(self) -> float:
        """현재 순 포지션 크기 (long: +qty, short: -qty, flat: 0)."""
        if not self.open_trades:
            return 0.0
        total = 0.0
        for t in self.open_trades.values():
            total += t.qty if t.direction == "long" else -t.qty
        return total

    @property
    def position_avg_price(self) -> float:
        """가중 평균 진입가 (현재 open trades)."""
        opens = list(self.open_trades.values())
        if not opens:
            return float("nan")
        total_qty = sum(t.qty for t in opens)
        if total_qty == 0:
            return float("nan")
        weighted = sum(t.entry_price * t.qty for t in opens)
        return weighted / total_qty

    # ---- fill_timing=next_bar_open — 시장가 인텐트 큐 ----------------

    def queue_market_intent(self, intent: MarketIntent) -> None:
        """next_bar_open 모드에서 시장가 entry/close/close_all 인텐트 등록."""
        self.pending_market_intents.append(intent)

    def process_market_intents(
        self,
        *,
        bar: int,
        open_: float,
        bar_ts: datetime | None = None,
    ) -> None:
        """큐된 시장가 인텐트를 이번 bar 시가로 체결.

        event_loop 가 매 bar 시작(check_pending_fills 이전)에 호출. session gate
        (BL-188 v3)는 pending stop fill 과 동일 정책 — disallowed bar 면 체결하지
        않고 carry-over.
        """
        if not self.pending_market_intents:
            return
        if self.sessions_allowed and bar_ts is not None:
            from src.strategy.trading_sessions import is_allowed

            if not is_allowed(list(self.sessions_allowed), bar_ts):
                return  # carry-over — 허용 세션 bar 에서 체결
        intents = self.pending_market_intents
        self.pending_market_intents = []
        for intent in intents:
            if intent.kind == "entry":
                qty = intent.qty if intent.qty is not None else self.compute_qty(fill_price=open_)
                self.entry(
                    intent.trade_id,
                    intent.direction,
                    qty=qty,
                    bar=bar,
                    fill_price=open_,
                    comment=intent.comment,
                )
            elif intent.kind == "close":
                self.close(
                    intent.trade_id,
                    bar=bar,
                    fill_price=open_,
                    comment=intent.comment,
                )
            else:
                self.close_all(bar=bar, fill_price=open_)

    # ---- 주문 접수 --------------------------------------------------

    def _flip_opposite_positions(
        self,
        new_direction: Direction,
        *,
        bar: int,
        fill_price: float,
        broker_filled: bool = False,
    ) -> None:
        """opposite-direction auto-flip 근사: 신규 direction 과 반대편 open 을 전부 close.

        TradingView 는 pyramiding 값과 무관하게 `strategy.entry` 가 반대 방향 entry
        를 받으면 기존 opposite-side open 포지션을 전부 reverse-close 한다
        (예: long 3 개 open 상태 + short entry → long 3 개 전부 close 후 short open).
        이 auto-flip 이 없으면 long+short 동시 유지로 `position_size = long_qty - short_qty = 0`
        이 되어 SLTP 의 `strategy.position_size > 0` 조건이 영구 False 가 되는
        dogfood 버그가 발생한다.

        comment 는 전달하지 않는다 — TradingView 는 reverse 로 닫힌 trade 에 synthetic
        comment 를 부여하지 않으며, 덮어쓰면 사용자 entry comment 오염.

        broker_filled 는 호출자가 "이 flip 은 broker 가 이미 한 장으로 끝냈다" 를
        표시하는 값이다 (BL-560 — `check_pending_fills` 경로). 원장 기록은 동일하고
        라이브 dispatch 대상에서만 빠진다.
        """
        opposite: Direction = "short" if new_direction == "long" else "long"
        ids_to_flip = [tid for tid, tr in self.open_trades.items() if tr.direction == opposite]
        for tid in ids_to_flip:
            self.close(tid, bar=bar, fill_price=fill_price, broker_filled=broker_filled)

    def entry(
        self,
        trade_id: str,
        direction: Direction,
        *,
        qty: float,
        bar: int,
        fill_price: float,
        comment: str = "",
        stop: float | None = None,
        unsupported_kwargs: list[str] | None = None,
    ) -> Trade | None:
        """시장가 또는 stop 주문 진입.

        - stop=None → 시장가 즉시 체결
        - stop=price → pending BUY/SELL STOP 주문 생성 (다음 bar에서 high/low 도달 시 fill)
        - 같은 id가 pending이면 덮어씀 (Pine은 re-issue 시 가격만 갱신)
        - opposite direction entry → 기존 same-side open 모두 자동 close (Pine pyramiding)
        """
        if unsupported_kwargs:
            self.warnings.append(
                f"strategy.entry({trade_id!r}): ignored unsupported kwargs: {unsupported_kwargs}"
            )

        # BL-376: na/inf qty → 주문 skip + warning (라이브 nan→reject 미러, money-path 무음오염 차단).
        # 시장가·pending-stop / 백테스트 RawTrade·라이브 LiveSignal 단일 chokepoint.
        # qty<=0 은 skip 안 함 — compute_qty 가 fill_price<=0 시 유한 0.0 정상 반환 (over-skip 방지).
        if not math.isfinite(qty):
            self.warnings.append(
                f"strategy.entry({trade_id!r}): non-finite qty ({qty}) → 주문 skip"
            )
            self._record_entry_skip(bar=bar, reason="non_finite_qty", trade_id=trade_id)
            return None

        if stop is not None:
            # Pending stop 주문 — 기존 동일 id pending 있으면 갱신 (Pine re-issue 의미론).
            # flip 은 체결 시점(check_pending_fills)에서 처리 — pending 상태에서는 반대 포지션 유지.
            self.pending_orders[trade_id] = PendingOrder(
                id=trade_id,
                direction=direction,
                qty=qty,
                stop_price=stop,
                placed_bar=bar,
                comment=comment,
            )
            return None

        if not self._can_afford_entry(
            trade_id=trade_id,
            direction=direction,
            qty=qty,
            fill_price=fill_price,
        ):
            self.warnings.append(f"strategy.entry({trade_id!r}): 증거금 부족으로 진입 skip")
            self._record_entry_skip(
                bar=bar,
                reason="margin_insufficient",
                trade_id=trade_id,
            )
            return None

        # 시장가: opposite direction 전부 flip (Pine 표준) → 중복 id 청산 → 신규 entry
        self._flip_opposite_positions(direction, bar=bar, fill_price=fill_price)
        if trade_id in self.open_trades:
            self.close(trade_id, bar=bar, fill_price=fill_price)

        # BL-104 — pyramiding cap (gated). 같은 방향 open 수가 한도 도달 시 skip.
        # None 이면 무효 → 기존 무제한 중첩 byte-identical.
        if self.pyramiding is not None:
            same_dir = sum(1 for t in self.open_trades.values() if t.direction == direction)
            if same_dir >= self.pyramiding:
                self.warnings.append(f"strategy.entry({trade_id!r}): pyramiding cap으로 진입 skip")
                self._record_entry_skip(
                    bar=bar,
                    reason="pyramiding_cap",
                    trade_id=trade_id,
                )
                return None

        return self._open_trade(
            trade_id=trade_id,
            direction=direction,
            qty=qty,
            bar=bar,
            fill_price=fill_price,
            comment=comment,
            event_action="entry",
        )

    def close(
        self,
        trade_id: str,
        *,
        bar: int,
        fill_price: float,
        comment: str = "",
        broker_filled: bool = False,
    ) -> Trade | None:
        """id 기준 포지션 청산. open 없으면 None.

        broker_filled=True 는 이 청산이 **거래소가 이미 실행한 체결**에서 파생됐다는
        뜻이다 (BL-560). 원장 갱신(closed_trades / PnL / running_equity)은 전혀 다르지
        않고, 남기는 close 이벤트에만 표시가 붙어 라이브 재발신에서 제외된다.
        """
        trade = self.open_trades.pop(trade_id, None)
        if trade is None:
            return None
        # BL-104 — 포지션 청산 시 그 entry 의 OCO exit 브래킷도 purge (반대신호/flip
        # 시 stale exit leg 잔존 방지). pending_exits 비어있으면 무영향 (회귀 0).
        self.pending_exits.pop(trade_id, None)
        trade.exit_bar = bar
        trade.exit_price = fill_price
        if comment:
            trade.comment = f"{trade.comment};{comment}" if trade.comment else comment
        # PnL: long이면 (exit - entry) * qty, short면 반대
        sign = 1.0 if trade.direction == "long" else -1.0
        trade.pnl = (fill_price - trade.entry_price) * trade.qty * sign
        # Sprint 37 BL-185: running_equity 갱신 (configure_sizing 호출된 경우만, fees=0 가정)
        if self.running_equity is not None:
            self.running_equity += trade.pnl
        # BL-460 — 게이트 전용 net 은 같은 pnl 에서 exit leg 비용을 뺀 값으로 간다.
        # 이 한 줄이 gross/net 괴리를 만드는 자리다(gross 는 위에서 그대로 둔다).
        if self.gate_equity is not None:
            self.gate_equity += trade.pnl - self._leg_cost(qty=trade.qty, price=fill_price)
        self.closed_trades.append(trade)
        # Sprint 26 P1 #2 — close event log (same-bar entry+close 모두 포착)
        self._record_event(
            bar=bar,
            action="close",
            direction=trade.direction,
            trade_id=trade_id,
            qty=trade.qty,
            price=fill_price,
            comment=comment,
            broker_filled=broker_filled,
        )
        return trade

    def close_all(self, *, bar: int, fill_price: float) -> list[Trade]:
        """모든 open 포지션 청산."""
        ids = list(self.open_trades.keys())
        closed: list[Trade] = []
        for tid in ids:
            t = self.close(tid, bar=bar, fill_price=fill_price)
            if t is not None:
                closed.append(t)
        # pending 주문도 취소
        self.pending_orders.clear()
        # BL-104 — pending exit 브래킷도 전부 취소 (close_all = 전량 청산).
        self.pending_exits.clear()
        return closed

    def _authoritative_fill_candidates(
        self,
        authority: ConditionalFillAuthority,
        *,
        bar: int,
        open_: float,
        high: float,
        low: float,
    ) -> list[tuple[str, PendingOrder, float]]:
        """원장이 이 봉에서 증언한 체결만 후보로 만든다 + census 를 센다 (ADR-025).

        시뮬 판정(`try_fill`)은 **읽기 전용으로 함께 돌린다** — 체결 여부를 정하기 위해서가
        아니라 「엔진이 체결했을 자리 vs 원장이 실제로 체결한 자리」를 세기 위해서다. 그
        차이가 백테스트 낙관 편의의 첫 실측치이고, 지금은 아무도 그 값을 모른다.
        """
        witnessed = authority.for_bar(bar)
        witnessed_ids = {fill.trade_id for fill in witnessed}
        # ★계상은 이 tick 이 **실제로 판정하는 봉**에서만 한다. 모든 봉에서 세면 warmup 300봉을
        #   매 tick 다시 세어 카운터가 사건과 무관하게 자란다(실측 tick 당 +121).
        count = authority.counts_census(bar)

        # ① 시뮬은 체결했을 텐데 원장이 증언하지 않는다 = 유령 차단 (BL-595 형 A).
        if count:
            for order_id, order in self.pending_orders.items():
                if order_id in witnessed_ids:
                    continue
                if order.try_fill(bar, high, low, open_) is not None:
                    self._bump_ledger_census("engine_only_suppressed")

        candidates: list[tuple[str, PendingOrder, float]] = []
        # 원장 순서가 곧 현실의 순서다 — 시뮬 경로의 "open 가격과의 거리" 휴리스틱을 쓸
        # 이유가 없다(그건 intrabar path 를 모를 때의 최소 가정이었다).
        # ★같은 봉에 같은 `trade_id` 증언이 둘이면 **마지막 것만** 쓴다. 그냥 순회하면
        #   `pending_orders.pop` 이 루프 **뒤**에 있어 두 번째도 매칭되고, 반전 close+open 이
        #   두 번 실행돼 없던 왕복 거래가 생긴다(codex challenge). 원장에 재발행·재관측이
        #   섞이면 실제로 도달한다.
        deduped: dict[str, LedgerConditionalFill] = {}
        for fill in sorted(witnessed, key=lambda item: item.filled_at):
            deduped[fill.trade_id] = fill
        for fill in deduped.values():
            witnessed_order = self.pending_orders.get(fill.trade_id)
            if witnessed_order is None:
                # 고아 — 엔진이 그 주문을 아예 안 들고 있다. **여기서는 아무것도 하지 않는다**
                # (ADR-025 R4: 사망 5건 중 0건이라 관측되지 않은 경우에 기계를 짓지 않는다).
                if count:
                    self._bump_ledger_census("ledger_only_orphan")
                continue
            if count:
                simulated = witnessed_order.try_fill(bar, high, low, open_)
                self._bump_ledger_census(
                    "agree" if simulated is not None else "ledger_only_adopted"
                )
            candidates.append((fill.trade_id, witnessed_order, fill.fill_price))
        return candidates

    def _bump_ledger_census(self, key: str) -> None:
        self.ledger_fill_census[key] = self.ledger_fill_census.get(key, 0) + 1

    def check_pending_fills(
        self,
        *,
        bar: int,
        open_: float,
        high: float,
        low: float,
        bar_ts: datetime | None = None,
        conditional_fill_authority: ConditionalFillAuthority | None = None,
    ) -> list[Trade]:
        """현재 bar OHLC로 pending 주문 체결 검사. 체결된 주문은 Trade로 전환.

        Event loop가 매 bar 시작 시 호출 (execute 전).

        BL-188 v3 fill gate (E3 — Live parity): `sessions_allowed` 가 비어있지 않고
        `bar_ts` 가 disallowed session 이면 fill 자체를 skip → pending_orders 는
        carry-over 되어 다음 allowed bar 에서 재시도. 단일 reference =
        `src.strategy.trading_sessions.is_allowed`.

        ADR-025 (BL-595) — `conditional_fill_authority` 는 **라이브 전용**이다.

        - `None`(기본, 백테스트) — 지금까지와 **byte-identical**. `try_fill` 이 체결을 정한다.
        - 값 있음(라이브) — **원장이 증언한 체결만** 인정하고 체결가도 원장 값을 쓴다.
          엔진의 시뮬 stop 과 거래소의 resting stop 은 수준도 수명도 다른 **다른 주문**이라
          양쪽 모두 혼자 발화한다. 라이브에는 진짜 매칭엔진이 있으므로 시뮬 체결은 잉여다.
        """
        if self.sessions_allowed and bar_ts is not None:
            from src.strategy.trading_sessions import is_allowed

            if not is_allowed(list(self.sessions_allowed), bar_ts):
                # disallowed session — fill skip, order 는 다음 bar 로 carry-over.
                # ★원장 권한이 켜져 있어도 이 게이트가 먼저다: 금지 세션에서는 reconciler 가
                #   거래소 주문을 걷어내는 것이 계약이고(`event_loop.py:353`), 그 계약을
                #   여기서 뒤집으면 걷어내기와 채택이 서로를 지운다.
                return []

        if conditional_fill_authority is not None:
            candidates = self._authoritative_fill_candidates(
                conditional_fill_authority, bar=bar, open_=open_, high=high, low=low
            )
        else:
            # Same-bar 에 long stop + short stop 둘 다 trigger 되는 경우 결정성 확보:
            # dict 순회 대신 먼저 체결 후보를 전부 수집한 뒤 "open 가격과의 거리 오름차순"
            # 으로 정렬 → bar open 에서 가장 빨리 닿는 주문부터 순차 체결.
            # TradingView 는 pessimistic simulation 을 기본으로 쓰지만 intrabar path 는 알 수
            # 없으므로 거리 기반 결정론이 최소 가정이고, dict insertion order 의존보다 훨씬 안전하다.
            candidates = []
            for order_id, order in self.pending_orders.items():
                fill_price = order.try_fill(bar, high, low, open_)
                if fill_price is None:
                    continue
                candidates.append((order_id, order, fill_price))
            candidates.sort(key=lambda c: abs(c[2] - open_))

        filled: list[Trade] = []
        to_remove: list[str] = []
        for order_id, order, fill_price in candidates:
            # ★원장 권한 경로에서는 증거금 게이트를 돌리지 않는다 — `seed_positions_from_ledger`
            #   가 같은 이유를 이미 적고 있다: **그 포지션은 이미 거래소에 존재한다.** 여기서
            #   거절해도 현실은 되돌아가지 않고 엔진만 그 포지션을 모르는 상태가 유지된다
            #   (= 이 ADR 이 없애려는 바로 그 상태).
            if conditional_fill_authority is None and not self._can_afford_entry(
                trade_id=order_id,
                direction=order.direction,
                qty=order.qty,
                fill_price=fill_price,
            ):
                self.warnings.append(f"strategy.entry({order_id!r}): 증거금 부족으로 진입 skip")
                self._record_entry_skip(
                    bar=bar,
                    reason="margin_insufficient",
                    trade_id=order_id,
                )
                to_remove.append(order_id)
                continue
            # 체결: opposite direction flip → 동일 id 중복 청산 → 신규 open
            #
            # ★BL-560 — 이 세 leg 는 **거래소에서 이미 한 장으로 끝난 일**이다.
            # 조건부 진입은 `abs(target_position - current_position)` 수량의 병합 주문
            # 1건으로 등재되므로(`trading/services/conditional_entry_planner.py:444`),
            # 트리거 시 거래소는 반대편 청산과 신규 진입을 동시에 처리한다. 엔진은 그
            # 체결을 다음 봉 평가에서야 재도출하는데, 그때 나온 close 를 지시로 되돌려
            # 보내면 이미 닫힌 포지션을 또 닫으라는 주문이 되어 거절된다
            # (실측 2.60건/h · 청산 시도의 46.2%). `broker_filled` 로 표시해 라이브
            # dispatch 에서만 뺀다 — 원장은 그대로다.
            self._flip_opposite_positions(
                order.direction, bar=bar, fill_price=fill_price, broker_filled=True
            )
            if order_id in self.open_trades:
                self.close(order_id, bar=bar, fill_price=fill_price, broker_filled=True)
            trade = self._open_trade(
                trade_id=order_id,
                direction=order.direction,
                qty=order.qty,
                bar=bar,
                fill_price=fill_price,
                comment=order.comment,
                event_action="fill",
                # ★원장이 증언한 체결에는 증거금 게이트를 걸지 않는다 — 위 `_can_afford_entry`
                #   우회만으로는 절반이다. `_open_trade` 가 **또 하나의 게이트**를 갖고 있고,
                #   거기서 막히면 엔진만 그 포지션을 모르는 상태가 그대로 남는다.
                enforce_margin=conditional_fill_authority is None,
            )
            to_remove.append(order_id)
            if trade is not None:
                filled.append(trade)
        for oid in to_remove:
            self.pending_orders.pop(oid, None)
        return filled

    def check_liquidations(
        self,
        *,
        bar: int,
        open_: float,
        high: float,
        low: float,
    ) -> list[Trade]:
        """현재 bar OHLC로 활성 격리 포지션의 강제청산을 검사한다."""
        if not is_leverage_active(self.leverage):
            return []

        liquidated: list[Trade] = []
        for trade_id, trade in list(self.open_trades.items()):
            liq_price = trade.liq_price
            if liq_price is None or trade.entry_bar >= bar:
                continue
            if trade.direction == "long":
                if low > liq_price:
                    continue
                fill_price = min(open_, liq_price)
            else:
                if high < liq_price:
                    continue
                fill_price = max(open_, liq_price)
            closed = self.close(
                trade_id,
                bar=bar,
                fill_price=fill_price,
                comment="liquidation",
            )
            if closed is not None:
                closed.liquidated = True
                self.liquidation_count += 1
                liquidated.append(closed)
        return liquidated

    # ---- BL-104: OCO TP/SL exit orders ------------------------------

    def place_exit(
        self,
        *,
        from_entry: str,
        exit_id: str,
        bar: int,
        stop: float | None = None,
        limit: float | None = None,
        profit_offset: float | None = None,
        loss_offset: float | None = None,
        trail_offset: float | None = None,
        comment: str = "",
    ) -> None:
        """strategy.exit 브래킷 placement. from_entry="" → 모든 open 포지션.

        - 절대가: stop(SL price) / limit(TP price). 우선.
        - 상대오프셋: profit(TP)/loss(SL) → target entry 가 기준 price-distance 로 환산.
          long: TP=entry+profit, SL=entry-loss. short: TP=entry-profit, SL=entry+loss.
          (pine_v2 는 mintick 모델 부재 → 1:1 price-distance 근사.)
        Pine re-issue 의미론: 같은 from_entry 의 기존 브래킷을 교체(가격 갱신).
        교체 시 동일 (exit_id, TRAILING_STOP) leg 의 trail_anchor 는 보존 (ratchet 유지).
        """
        if from_entry:
            targets = [from_entry] if from_entry in self.open_trades else []
        else:
            targets = list(self.open_trades.keys())

        for tid in targets:
            trade = self.open_trades[tid]
            pos_dir = trade.direction
            entry = trade.entry_price
            # 절대가 우선, 없으면 오프셋으로 환산.
            eff_stop = stop
            if eff_stop is None and loss_offset is not None:
                eff_stop = entry - loss_offset if pos_dir == "long" else entry + loss_offset
            eff_limit = limit
            if eff_limit is None and profit_offset is not None:
                eff_limit = entry + profit_offset if pos_dir == "long" else entry - profit_offset

            prev_legs = self.pending_exits.get(tid, [])
            prev_trail_anchor: float | None = None
            for pl in prev_legs:
                if pl.exit_id == exit_id and pl.kind == ExitOrderKind.TRAILING_STOP:
                    prev_trail_anchor = pl.trail_anchor

            legs: list[ExitOrder] = []
            if eff_stop is not None:
                legs.append(
                    ExitOrder(
                        from_entry=tid,
                        exit_id=exit_id,
                        position_direction=pos_dir,
                        kind=ExitOrderKind.STOP_LOSS,
                        placed_bar=bar,
                        stop_price=eff_stop,
                        comment=comment,
                    )
                )
            if eff_limit is not None:
                legs.append(
                    ExitOrder(
                        from_entry=tid,
                        exit_id=exit_id,
                        position_direction=pos_dir,
                        kind=ExitOrderKind.TAKE_PROFIT,
                        placed_bar=bar,
                        limit_price=eff_limit,
                        comment=comment,
                    )
                )
            if trail_offset is not None:
                legs.append(
                    ExitOrder(
                        from_entry=tid,
                        exit_id=exit_id,
                        position_direction=pos_dir,
                        kind=ExitOrderKind.TRAILING_STOP,
                        placed_bar=bar,
                        trail_offset=trail_offset,
                        trail_anchor=prev_trail_anchor,
                        comment=comment,
                    )
                )
            if legs:
                self.pending_exits[tid] = legs

    def check_exit_fills(
        self,
        *,
        bar: int,
        open_: float,
        high: float,
        low: float,
        bar_ts: datetime | None = None,
    ) -> list[Trade]:
        """현재 bar OHLC 로 pending exit 브래킷 체결 검사. 체결 leg 는 포지션 청산.

        - pending_exits 비어있으면 즉시 [] → strategy.exit 미사용 시 no-op (회귀 0).
        - BL-188 v3 session gate 재사용: disallowed bar 면 fill skip → carry-over.
        - 한 entry 의 leg 가 체결되면 포지션 청산 + OCO 형제 전부 purge.
        - 같은 bar 에 여러 leg trigger 시 체결 우선순위 = 거리순 (C4 에서 pessimistic 으로 교체).
        """
        if not self.pending_exits:
            return []
        if self.sessions_allowed and bar_ts is not None:
            from src.strategy.trading_sessions import is_allowed

            if not is_allowed(list(self.sessions_allowed), bar_ts):
                return []

        filled: list[Trade] = []
        for entry_id in list(self.pending_exits.keys()):
            legs = self.pending_exits.get(entry_id)
            if not legs or entry_id not in self.open_trades:
                continue
            for leg in legs:
                leg.update_trailing(high, low)
            candidates: list[tuple[ExitOrder, float]] = []
            for leg in legs:
                fp = leg.try_fill_exit(bar=bar, open_=open_, high=high, low=low)
                if fp is not None:
                    candidates.append((leg, fp))
            if not candidates:
                continue
            # 동시-bar trigger 시 SAME_BAR_FILL_PRIORITY(SL→Trail→TP) 순 = pessimistic.
            # intrabar path 미상 → SL 우선 = 실거래 최악가정 일치.
            candidates.sort(key=lambda c: SAME_BAR_FILL_PRIORITY.index(c[0].kind))
            leg, fill_price = candidates[0]
            trade = self.close(entry_id, bar=bar, fill_price=fill_price, comment=leg.comment)
            if trade is not None:
                trade.exit_kind = leg.kind
                filled.append(trade)
            # 포지션 청산 → OCO 형제 전부 purge.
            self.pending_exits.pop(entry_id, None)
        return filled

    def exit_levels_for(self, trade_id: str) -> ExitLevels:
        """Phase 3 — trade_id 의 pending exit 레그에서 TP/SL/trail 레벨 추출 (라이브 surfacing).

        백테스트 sim 의 exit 계약(`pending_exits`)을 라이브 주문 경로로 노출하는
        read-only accessor — 상태 변경 없음. pending_exits 미존재/빈 레그 → 전부 None
        (exit 미사용 전략 회귀 0).
        """
        take_profit: float | None = None
        stop_loss: float | None = None
        trailing_stop: float | None = None
        for leg in self.pending_exits.get(trade_id, []):
            if leg.kind == ExitOrderKind.TAKE_PROFIT:
                take_profit = leg.limit_price
            elif leg.kind == ExitOrderKind.STOP_LOSS:
                stop_loss = leg.stop_price
            elif leg.kind == ExitOrderKind.TRAILING_STOP:
                trailing_stop = leg.trail_offset
        return ExitLevels(take_profit, stop_loss, trailing_stop)

    def to_report(self) -> dict[str, Any]:
        """실행 결과 리포트 딕셔너리."""
        return {
            "open_trades": [t.to_dict() for t in self.open_trades.values()],
            "closed_trades": [t.to_dict() for t in self.closed_trades],
            "position_size": self.position_size,
            "position_avg_price": self.position_avg_price,
            "warnings": list(self.warnings),
            "entry_skips": list(self.entry_skips),
            "liquidation_count": self.liquidation_count,
            "total_pnl": sum((t.pnl or 0.0) for t in self.closed_trades),
            "trade_count": len(self.closed_trades) + len(self.open_trades),
        }
