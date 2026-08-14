# 주문↔원장 상관 조회의 인덱스 축 ([BL-731]).
"""add ix_exchange_exits_account_order

`_HAS_EXCHANGE_EXIT_ROW`(EXISTS)와 [BL-731] 이 더한 `_EXCHANGE_EXIT_PNL_SUM`(상관 SUM)은 둘 다
`(exchange_account_id, exchange_order_id)` 로 원장을 찾는다. 그런데 기존 인덱스 셋
(`uq(account,row_hash)` · `(account,exchange_created_at)` · `classification`) 중 어느 것도
`exchange_order_id` 로 좁히지 못해 **후보 주문마다 계정 원장을 Seq Scan** 했다.

2026-08-15 `EXPLAIN (ANALYZE, BUFFERS)` 실측 (891행 · 주문 70건):

    -> Seq Scan on exchange_exits e2 (actual time=0.006..0.051 rows=1 loops=70)
         Filter: ((exchange_account_id = o.exchange_account_id)
                  AND ((exchange_order_id)::text = (o.exchange_order_id)::text))
         Rows Removed by Filter: 890
         Buffers: shared hit=6860

891행에서는 3.9ms 라 눈에 안 띈다. 문제는 **원장이 단조 증가**한다는 것이고
(그것이 [BL-731] 자체의 내용이다), 이 조회는 5분 beat 스윕이 계정마다 돈다.

★`uq_exchange_exits_row` 를 재사용할 수 없다 — 두 번째 컬럼이 `row_hash` 라
`exchange_order_id` 조건을 인덱스로 못 민다.

★unique 가 아니다. 한 거래소 주문이 **분할 청산 행 여러 개**를 갖는 것이 정상이고
(그래서 EXISTS 를 쓰고 JOIN 을 안 쓴다), SUM 은 그 행들을 합치는 것이 목적이다.

Revision ID: 20260815_0001
Revises: 20260801_0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260815_0001"
down_revision: str | Sequence[str] | None = "20260801_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX = "ix_exchange_exits_account_order"


def upgrade() -> None:
    op.create_index(
        _INDEX,
        "exchange_exits",
        ["exchange_account_id", "exchange_order_id"],
        unique=False,
        schema="trading",
    )


def downgrade() -> None:
    op.drop_index(_INDEX, table_name="exchange_exits", schema="trading")
