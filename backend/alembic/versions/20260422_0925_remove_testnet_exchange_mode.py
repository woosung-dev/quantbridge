"""remove testnet from exchangemode enum

Revision ID: 00cfa7d536e4
Revises: 20260421_0001, 20260421_0002
Create Date: 2026-04-22 09:25:10.649264

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "00cfa7d536e4"
down_revision: str | Sequence[str] | None = ("20260421_0001", "20260421_0002")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. 기존 testnet 계정 → demo로 변환 (data migration)
    op.execute("UPDATE trading.exchange_accounts SET mode = 'demo' WHERE mode = 'testnet'")

    # 2. 신규 ENUM 타입 생성 (testnet 없음)
    op.execute("CREATE TYPE exchangemode_new AS ENUM ('demo', 'live')")

    # 3. 컬럼 타입 교체
    op.execute(
        "ALTER TABLE trading.exchange_accounts "
        "ALTER COLUMN mode TYPE exchangemode_new "
        "USING mode::text::exchangemode_new"
    )

    # 4. 구 타입 삭제 후 이름 복원
    op.execute("DROP TYPE exchangemode")
    op.execute("ALTER TYPE exchangemode_new RENAME TO exchangemode")


def downgrade() -> None:
    op.execute("CREATE TYPE exchangemode_old AS ENUM ('demo', 'testnet', 'live')")
    op.execute(
        "ALTER TABLE trading.exchange_accounts "
        "ALTER COLUMN mode TYPE exchangemode_old "
        "USING mode::text::exchangemode_old"
    )
    op.execute("DROP TYPE exchangemode")
    op.execute("ALTER TYPE exchangemode_old RENAME TO exchangemode")
