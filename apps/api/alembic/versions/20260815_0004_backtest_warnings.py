# 백테스트 실행이 남긴 경고를 원장에 싣는다 — 지금까지는 계산되고 버려졌다 (2026-08-15 · U8).
"""add backtests.warnings

엔진은 `strategy_state.warnings` 를 **이미 만들고 있었다** — `v2_adapter.py:218-221` 의
주석이 「사용자가 silent success 받지 않도록 `BacktestOutcome.parse.warnings` 로 노출」이라고
스스로 적어 뒀다. 없었던 것은 **소비자**다: `BacktestService` 는 `outcome.parse` 를 한 번도
참조하지 않았고(grep 0건), 그래서 그 경고는 계산된 자리에서 그대로 사라졌다.

★`metrics` JSONB 에 얹는 안은 **틀렸다**. `metrics` 는 `BacktestMetrics` 직렬화이고
`tests/backtest/test_metrics_field_parity.py` 가 그 필드 집합을 양방향으로 동결한다.
경고는 지표가 아니라 실행의 성질이므로 자리도 따로여야 한다.

★nullable 이다 — 이 컬럼 이전에 끝난 행은 NULL 이고 그것은 「경고 없음」이 아니라
**「모른다」**다. 빈 배열(`[]`)이 「경고 없음」이다. 화면은 그 둘을 구분한다.

★backfill 하지 않는다 — 과거 실행의 경고는 **복원할 수 없다**(엔진 상태가 남아 있지 않다).
빈 배열로 채우면 「경고 없이 돌았다」는 거짓을 원장에 쓰게 된다.

Revision ID: 20260815_0004
Revises: 20260815_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260815_0004"
down_revision: str | Sequence[str] | None = "20260815_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "backtests",
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("backtests", "warnings")
