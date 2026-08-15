# 주문 목록의 정렬 축 인덱스 (2026-08-15 surface-truth · S5).
"""add ix_orders_account_created

`OrderRepository.list_by_user` 는 `ExchangeAccount` 로 조인해 사용자를 좁힌 뒤
`ORDER BY orders.created_at DESC` 로 페이지네이션하고, **같은 조인으로 COUNT(\\*) 를 한 번 더**
돈다. 그런데 `trading.orders` 의 인덱스 3종 중 어느 것도 그 정렬을 못 민다:

- `ix_orders_strategy(strategy_id)` — 조인 축이 아니다.
- `ix_orders_account_state(exchange_account_id, state)` — 두 번째 컬럼이 `state` 라
  `created_at` 정렬을 인덱스로 못 민다.
- `uq_orders_idempotency_key` — `WHERE idempotency_key IS NOT NULL` partial 이라 후보가 아니다.

★**지금 안 아픈 것이 나중에 확실히 아프다** — 라이브 자동매매 도메인이라 이 테이블은
**단조 증가**한다. 하루 전 `exchange_exits` 가 정확히 같은 이유로 Seq Scan 을 냈다([BL-731] ·
`20260815_0001`). 여기서는 「원장이 커지기 전에」 붙인다.

★unique 가 아니다 — 한 계정이 같은 순간에 여러 주문을 가질 수 있다.

Revision ID: 20260815_0002
Revises: 20260815_0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260815_0002"
down_revision: str | Sequence[str] | None = "20260815_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX = "ix_orders_account_created"


def upgrade() -> None:
    op.create_index(
        _INDEX,
        "orders",
        ["exchange_account_id", "created_at"],
        unique=False,
        schema="trading",
    )


def downgrade() -> None:
    op.drop_index(_INDEX, table_name="orders", schema="trading")
