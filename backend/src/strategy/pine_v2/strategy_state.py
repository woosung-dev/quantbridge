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
from typing import Any, Literal

Direction = Literal["long", "short"]


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
class StrategyState:
    """포지션 상태 + 체결 기록.

    단일 포지션 가정 — id별 슬롯이지만 한 번에 하나의 id만 open 권장.
    """

    open_trades: dict[str, Trade] = field(default_factory=dict)
    closed_trades: list[Trade] = field(default_factory=list)
    # 경고/미지원 파라미터 추적 (`stop=`, `limit=` 등) — 사용자에게 알림용
    warnings: list[str] = field(default_factory=list)

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

    def entry(
        self,
        trade_id: str,
        direction: Direction,
        *,
        qty: float,
        bar: int,
        fill_price: float,
        comment: str = "",
        unsupported_kwargs: list[str] | None = None,
    ) -> Trade:
        """시장가 진입 — 현재 bar의 fill_price에서 즉시 체결.

        이미 같은 id가 open인 경우 Pine 기본 동작은 "override"이나, 구현 단순화를 위해
        기존 trade를 먼저 close한 뒤 새 entry를 건다.
        """
        if unsupported_kwargs:
            self.warnings.append(
                f"strategy.entry({trade_id!r}): ignored unsupported kwargs: {unsupported_kwargs}"
            )
        # 중복 id 처리 — 기존 청산
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
        self.closed_trades.append(trade)
        return trade

    def close_all(self, *, bar: int, fill_price: float) -> list[Trade]:
        """모든 open 포지션 청산."""
        ids = list(self.open_trades.keys())
        closed: list[Trade] = []
        for tid in ids:
            t = self.close(tid, bar=bar, fill_price=fill_price)
            if t is not None:
                closed.append(t)
        return closed

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
