# backtest_trades 에 TV Trades-parity 컬럼 10종 추가 (순수 additive nullable)
"""add_backtest_trade_tv_parity_columns

Revision ID: 20260705_0001
Revises: 20260627_0001
Create Date: 2026-07-05 00:00:00.000000

TV Strategy Tester 거래목록 parity — per-trade run-up/drawdown(MFE/MAE, bar 근사),
bars_in_trade, fee/slippage 분리(불변식: fee_paid + slippage_paid == fees 결합 컬럼
유지), cumulative_pnl(trade_index 순 누적), exit_kind(wire 문자열 — PG enum 회피,
LESSON-066), comment. 전부 nullable = 구 row 회귀 0, FE graceful hide.

Idempotent ADD/DROP COLUMN IF (NOT) EXISTS (20260627_0001 패턴 mirror).
"""

from __future__ import annotations

from alembic import op

revision = "20260705_0001"
down_revision = "20260627_0001"
branch_labels = None
depends_on = None

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("runup_abs", "NUMERIC(20, 8)"),
    ("runup_pct", "NUMERIC(12, 6)"),
    ("drawdown_abs", "NUMERIC(20, 8)"),
    ("drawdown_pct", "NUMERIC(12, 6)"),
    ("bars_in_trade", "INTEGER"),
    ("fee_paid", "NUMERIC(20, 8)"),
    ("slippage_paid", "NUMERIC(20, 8)"),
    ("cumulative_pnl", "NUMERIC(20, 8)"),
    ("exit_kind", "VARCHAR(16)"),
    ("comment", "TEXT"),
)


def upgrade() -> None:
    for name, ddl_type in _COLUMNS:
        op.execute(f"ALTER TABLE backtest_trades ADD COLUMN IF NOT EXISTS {name} {ddl_type}")


def downgrade() -> None:
    for name, _ in reversed(_COLUMNS):
        op.execute(f"ALTER TABLE backtest_trades DROP COLUMN IF EXISTS {name}")
