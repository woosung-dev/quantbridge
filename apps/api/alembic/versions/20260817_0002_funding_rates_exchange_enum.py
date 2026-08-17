"""funding_rates.exchange VARCHAR(32) -> exchangename enum

Revision ID: 20260817_0002
Revises: 20260816_0001
Create Date: 2026-08-17 00:02:00.000000

[BL-782] `trading.funding_rates.exchange` 만 migration 계보에서 VARCHAR(32) 로 태어났다
(`20260421_0001:29`). 모델(`src/trading/models.py:438`)은 처음부터 `ExchangeName` 이고,
같은 enum 을 쓰는 `trading.exchange_accounts.exchange` 는 `20260416_2206` 에서 이미
native `exchangename` 으로 만들어졌다. 즉 이 한 컬럼만 두 스키마 경로가 갈렸다 —
`alembic upgrade head` 로 만든 DB 는 VARCHAR, `SQLModel.metadata.create_all` 로 만든
DB(=pytest)는 enum. 그래서 `alembic check` 의 답이 **어느 DB 에 대고 재느냐에 따라 달랐고**,
[BL-770] 이 「rc=0 이 처음」이라 닫은 측정은 enum 쪽 DB 의 것이었다.

여기서 닫는 것은 그 한 컬럼**뿐**이다. 같은 절차로 다른 축을 함께 켜면 게이트가 상시 red
가 된다([BL-749]).

값 안전 — 2026-08-17 실측: 개발 DB `trading.funding_rates` 162행 전건 `bybit` 이고
`exchangename` 라벨은 `bybit`·`binance`·`okx` 다. 인제스션 경로(`src/trading/funding.py`)도
`ExchangeName` 로 타입이 잡혀 있어 그 밖의 값이 들어갈 자리가 없다.
★**서버 소크 DB 의 값 집합은 확인하지 않았다**(서버 접속 금지). 라벨 밖 값이 있으면
`USING` 캐스트가 `invalid input value for enum exchangename` 으로 **소리 내며** 실패한다 —
조용히 잘못된 결과를 내지는 않는다.

enum value 를 더하거나 빼지 않으므로 [LESSON-066] 의 downgrade enum swap 패턴은 대상이 아니다.
downgrade 는 컬럼 타입만 VARCHAR(32) 로 되돌린다 — `exchangename` 타입 자체는
`exchange_accounts` 가 계속 쓰므로 남긴다.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "20260817_0002"
down_revision: str = "20260816_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE trading.funding_rates "
        "ALTER COLUMN exchange TYPE exchangename USING exchange::exchangename"
    )


def downgrade() -> None:
    op.alter_column(
        "funding_rates",
        "exchange",
        type_=sa.String(length=32),
        existing_nullable=False,
        postgresql_using="exchange::text",
        schema="trading",
    )
