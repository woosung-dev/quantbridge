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
    # ★★`CONCURRENTLY` 다 (2026-08-15 적대 리뷰 P2). `trading.orders` 는 **라이브 주문이
    #   실시간으로 들어오는 테이블**이고, 평범한 `CREATE INDEX` 는 그 동안 INSERT/UPDATE/DELETE 를
    #   **잠근다**. 즉 마이그레이션이 도는 시간만큼 라이브 발주가 대기한다.
    #   `CONCURRENTLY` 는 트랜잭션 안에서 돌 수 없으므로 `autocommit_block` 이 필요하다
    #   (`20260419_1200` 이 `ALTER TYPE ... ADD VALUE` 로 같은 패턴을 이미 쓴다).
    #   ★대가: 실패 시 **INVALID 인덱스**가 남는다. `IF NOT EXISTS` 로 재실행은 안전하게 하되,
    #   실패했다면 `DROP INDEX` 후 다시 돌려야 한다(INVALID 인덱스는 조회에 안 쓰이고 쓰기 비용만 낸다).
    with op.get_context().autocommit_block():
        op.execute(
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_INDEX} "
            "ON trading.orders (exchange_account_id, created_at)"
        )


def downgrade() -> None:
    # 내리는 쪽도 같은 이유로 CONCURRENTLY 다 — `DROP INDEX` 는 테이블 ACCESS EXCLUSIVE 를 잡는다.
    with op.get_context().autocommit_block():
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS trading.{_INDEX}")
