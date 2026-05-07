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

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

Direction = Literal["long", "short"]


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

    @property
    def is_open(self) -> bool:
        return self.exit_bar is None

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
        }


@dataclass
class TradeEvent:
    """Sprint 26 codex G.0 P1 #2 — bar-level entry/close/fill event log.

    `run_live` (Phase B) 가 마지막 bar 의 event 만 LiveSignalEvent outbox 로
    변환. final-state diff 방식은 same-bar entry+close 를 entry 로 감지 못 함 →
    명시적 event log 가 필요.

    sequence_no: 같은 bar 안 event 순서 (0-based). same-bar entry+close 시
    entry sequence_no=0 + close sequence_no=1.
    """

    bar_index: int
    action: Literal["entry", "close", "fill"]
    direction: Direction
    trade_id: str
    qty: float
    price: float
    sequence_no: int
    comment: str = ""


@dataclass
class StrategyState:
    """포지션 상태 + 체결 기록.

    단일 포지션 가정 — id별 슬롯이지만 한 번에 하나의 id만 open 권장.
    """

    open_trades: dict[str, Trade] = field(default_factory=dict)
    closed_trades: list[Trade] = field(default_factory=list)
    # pending 주문: id → PendingOrder (stop/limit 아직 미체결)
    pending_orders: dict[str, PendingOrder] = field(default_factory=dict)
    # 경고/미지원 파라미터 추적 (`limit=`, `trail_points=` 등) — 사용자에게 알림용
    warnings: list[str] = field(default_factory=list)
    # Sprint 26 codex G.0 P1 #2 — bar-level event log. `run_live` 가 마지막 bar 의
    # entry/close 만 LiveSignalEvent outbox 로 변환. same-bar entry+close 회귀 방어.
    events: list[TradeEvent] = field(default_factory=list)
    # Sprint 37 BL-185 — Pine strategy() 포지션 사이징 spot-equivalent.
    # configure_sizing() 호출 시 초기화. 미호출 시 compute_qty()=1.0 fallback (기존 호환).
    initial_capital: float | None = None
    running_equity: float | None = None
    default_qty_type: str | None = None  # "strategy.percent_of_equity" | "strategy.cash" | "strategy.fixed" | None
    default_qty_value: float | None = None
    # Sprint 38 BL-188 v3 — entry placement + pending fill 양쪽에 적용되는 trading session gate.
    # event_loop / virtual_strategy 가 cfg.trading_sessions 로 주입. 비어있으면 24h (회귀 0).
    # 단일 reference: src.strategy.trading_sessions.is_allowed (Live `is_allowed` 와 동일 함수).
    sessions_allowed: tuple[str, ...] = ()

    # ---- Sprint 37 BL-185: 포지션 사이징 (spot-equivalent) ------------

    def configure_sizing(
        self,
        *,
        initial_capital: float,
        default_qty_type: str | None = None,
        default_qty_value: float | None = None,
    ) -> None:
        """백테스트 시작 시 1회 호출. running_equity 초기화 + Pine default_qty_* 등록.

        BL-185: leverage / funding / liquidation 미반영 (Sprint 38 BL-186 후속).
        running_equity 갱신 = closed_trades PnL 누적 (fees=0 Sprint 37 가정).
        """
        self.initial_capital = float(initial_capital)
        self.running_equity = float(initial_capital)
        self.default_qty_type = default_qty_type
        self.default_qty_value = (
            float(default_qty_value) if default_qty_value is not None else None
        )

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
            )
        )

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

    # ---- 주문 접수 --------------------------------------------------

    def _flip_opposite_positions(
        self,
        new_direction: Direction,
        *,
        bar: int,
        fill_price: float,
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
        """
        opposite: Direction = "short" if new_direction == "long" else "long"
        ids_to_flip = [
            tid for tid, tr in self.open_trades.items() if tr.direction == opposite
        ]
        for tid in ids_to_flip:
            self.close(tid, bar=bar, fill_price=fill_price)

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

        # 시장가: opposite direction 전부 flip (Pine 표준) → 중복 id 청산 → 신규 entry
        self._flip_opposite_positions(direction, bar=bar, fill_price=fill_price)
        if trade_id in self.open_trades:
            self.close(trade_id, bar=bar, fill_price=fill_price)

        trade = Trade(
            id=trade_id,
            direction=direction,
            qty=qty,
            entry_bar=bar,
            entry_price=fill_price,
            comment=comment,
        )
        self.open_trades[trade_id] = trade
        # Sprint 26 P1 #2 — 시장가 entry event log
        self._record_event(
            bar=bar,
            action="entry",
            direction=direction,
            trade_id=trade_id,
            qty=qty,
            price=fill_price,
            comment=comment,
        )
        return trade

    def close(
        self,
        trade_id: str,
        *,
        bar: int,
        fill_price: float,
        comment: str = "",
    ) -> Trade | None:
        """id 기준 포지션 청산. open 없으면 None."""
        trade = self.open_trades.pop(trade_id, None)
        if trade is None:
            return None
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
        return closed

    def check_pending_fills(
        self,
        *,
        bar: int,
        open_: float,
        high: float,
        low: float,
        bar_ts: datetime | None = None,
    ) -> list[Trade]:
        """현재 bar OHLC로 pending 주문 체결 검사. 체결된 주문은 Trade로 전환.

        Event loop가 매 bar 시작 시 호출 (execute 전).

        BL-188 v3 fill gate (E3 — Live parity): `sessions_allowed` 가 비어있지 않고
        `bar_ts` 가 disallowed session 이면 fill 자체를 skip → pending_orders 는
        carry-over 되어 다음 allowed bar 에서 재시도. 단일 reference =
        `src.strategy.trading_sessions.is_allowed`.
        """
        if self.sessions_allowed and bar_ts is not None:
            from src.strategy.trading_sessions import is_allowed
            if not is_allowed(list(self.sessions_allowed), bar_ts):
                # disallowed session — fill skip, order 는 다음 bar 로 carry-over.
                return []

        # Same-bar 에 long stop + short stop 둘 다 trigger 되는 경우 결정성 확보:
        # dict 순회 대신 먼저 체결 후보를 전부 수집한 뒤 "open 가격과의 거리 오름차순"
        # 으로 정렬 → bar open 에서 가장 빨리 닿는 주문부터 순차 체결.
        # TradingView 는 pessimistic simulation 을 기본으로 쓰지만 intrabar path 는 알 수 없으므로
        # 거리 기반 결정론이 최소 가정이고, dict insertion order 의존보다 훨씬 안전하다.
        candidates: list[tuple[str, PendingOrder, float]] = []
        for order_id, order in self.pending_orders.items():
            fill_price = order.try_fill(bar, high, low, open_)
            if fill_price is None:
                continue
            candidates.append((order_id, order, fill_price))
        candidates.sort(key=lambda c: abs(c[2] - open_))

        filled: list[Trade] = []
        to_remove: list[str] = []
        for order_id, order, fill_price in candidates:
            # 체결: opposite direction flip → 동일 id 중복 청산 → 신규 open
            self._flip_opposite_positions(order.direction, bar=bar, fill_price=fill_price)
            if order_id in self.open_trades:
                self.close(order_id, bar=bar, fill_price=fill_price)
            trade = Trade(
                id=order_id,
                direction=order.direction,
                qty=order.qty,
                entry_bar=bar,
                entry_price=fill_price,
                comment=order.comment,
            )
            self.open_trades[order_id] = trade
            # Sprint 26 P1 #2 — pending fill event (action=fill 로 entry 와 구분)
            self._record_event(
                bar=bar,
                action="fill",
                direction=order.direction,
                trade_id=order_id,
                qty=order.qty,
                price=fill_price,
                comment=order.comment,
            )
            filled.append(trade)
            to_remove.append(order_id)
        for oid in to_remove:
            self.pending_orders.pop(oid, None)
        return filled

    def to_report(self) -> dict[str, Any]:
        """실행 결과 리포트 딕셔너리."""
        return {
            "open_trades": [t.to_dict() for t in self.open_trades.values()],
            "closed_trades": [t.to_dict() for t in self.closed_trades],
            "position_size": self.position_size,
            "position_avg_price": self.position_avg_price,
            "warnings": list(self.warnings),
            "total_pnl": sum((t.pnl or 0.0) for t in self.closed_trades),
            "trade_count": len(self.closed_trades) + len(self.open_trades),
        }
