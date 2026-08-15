# 인증 공급자를 Clerk 에서 self-host Better Auth 로 옮긴다 — 컬럼 1개 rename + 테이블 5개 (ADR-034).
"""better auth tables + users.clerk_user_id -> users.auth_subject

★**컬럼을 지웠다 만들지 않는다 — rename 이다.** autogenerate 는 이 변경을 drop+add 로 내는데,
그러면 기존 사용자의 외부 ID 가 사라지고 `NOT NULL` 때문에 마이그레이션 자체가 실패한다.
프로덕션에 실사용자 2명(그중 데이터 보유 1명, 파생 6,081행)이 매달려 있으므로 값 보존이 요구사항이다.
※ 남는 값은 **구 Clerk subject** 다. 새 로그인이 만들어 낸 Better Auth subject 로 잇는 것은
   데이터 마이그레이션이 아니라 **운영 한 줄**이고, 사용자 승인 아래 별도로 집행한다
   (`apps/api/scripts/link_auth_subject.py`).

★`auth_*` 5테이블의 DDL 정본은 **이 레포**다. Better Auth 의 `migrate` CLI 로 서버 DB 를 치지
않는다 — 이 레포 규약이 「서버 소크 DB DDL = `soak-stack.sh migrate --confirm` + 매번 명시 승인」
이기 때문이다([BL-743]). 스키마는 `@better-auth/cli generate` 산출을 그대로 옮겼고, 선언은
`src/auth/better_auth_tables.py` 가 들고 있다(`alembic check` 가 removed table 로 오인하지 않게).

★컬럼 이름이 camelCase 인 것은 Better Auth 규약이다. 따옴표 식별자로 만들어야 한다 —
snake_case 로 바꾸면 라이브러리가 그 컬럼을 못 찾는다.

Revision ID: 20260817_0001
Revises: 20260815_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260817_0001"
down_revision: str | Sequence[str] | None = "20260815_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TS = sa.TIMESTAMP(timezone=True)
_NOW = sa.text("CURRENT_TIMESTAMP")


def upgrade() -> None:
    # ── 1. users.clerk_user_id → users.auth_subject (값 보존) ────────────────────
    op.alter_column("users", "clerk_user_id", new_column_name="auth_subject")
    # 인덱스 이름도 함께 옮긴다 — `insert_if_absent` 의 `on_conflict(index_elements=...)` 가
    # 컬럼 이름으로 인덱스를 찾으므로 이름이 어긋나면 upsert 가 조용히 깨진다.
    op.execute("ALTER INDEX IF EXISTS ix_users_clerk_user_id RENAME TO ix_users_auth_subject")

    # ── 2. Better Auth 코어 4테이블 + jwks ──────────────────────────────────────
    op.create_table(
        "auth_user",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("emailVerified", sa.Boolean(), nullable=False),
        sa.Column("image", sa.Text(), nullable=True),
        sa.Column("createdAt", _TS, nullable=False, server_default=_NOW),
        sa.Column("updatedAt", _TS, nullable=False, server_default=_NOW),
        # `user.additionalFields.country` — geo-block L3 이 가입 시점에 채운다.
        sa.Column("country", sa.Text(), nullable=True),
    )
    op.create_table(
        "auth_session",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("expiresAt", _TS, nullable=False),
        sa.Column("token", sa.Text(), nullable=False, unique=True),
        sa.Column("createdAt", _TS, nullable=False, server_default=_NOW),
        sa.Column("updatedAt", _TS, nullable=False),
        sa.Column("ipAddress", sa.Text(), nullable=True),
        sa.Column("userAgent", sa.Text(), nullable=True),
        sa.Column(
            "userId",
            sa.Text(),
            sa.ForeignKey("auth_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index("auth_session_userId_idx", "auth_session", ["userId"])
    op.create_table(
        "auth_account",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("accountId", sa.Text(), nullable=False),
        sa.Column("providerId", sa.Text(), nullable=False),
        sa.Column(
            "userId",
            sa.Text(),
            sa.ForeignKey("auth_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("accessToken", sa.Text(), nullable=True),
        sa.Column("refreshToken", sa.Text(), nullable=True),
        sa.Column("idToken", sa.Text(), nullable=True),
        sa.Column("accessTokenExpiresAt", _TS, nullable=True),
        sa.Column("refreshTokenExpiresAt", _TS, nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        # ★비밀번호 해시(scrypt)가 사는 곳 — `auth_user` 가 아니다.
        sa.Column("password", sa.Text(), nullable=True),
        sa.Column("createdAt", _TS, nullable=False, server_default=_NOW),
        sa.Column("updatedAt", _TS, nullable=False),
    )
    op.create_index("auth_account_userId_idx", "auth_account", ["userId"])
    op.create_table(
        "auth_verification",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("expiresAt", _TS, nullable=False),
        sa.Column("createdAt", _TS, nullable=False, server_default=_NOW),
        sa.Column("updatedAt", _TS, nullable=False, server_default=_NOW),
    )
    op.create_index("auth_verification_identifier_idx", "auth_verification", ["identifier"])
    op.create_table(
        "auth_jwks",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("publicKey", sa.Text(), nullable=False),
        # AES256-GCM 으로 암호화되어 저장된다. 그래도 인증 전용 DB 롤만 읽을 수 있어야 한다.
        sa.Column("privateKey", sa.Text(), nullable=False),
        sa.Column("createdAt", _TS, nullable=False),
        sa.Column("expiresAt", _TS, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("auth_jwks")
    op.drop_index("auth_verification_identifier_idx", table_name="auth_verification")
    op.drop_table("auth_verification")
    op.drop_index("auth_account_userId_idx", table_name="auth_account")
    op.drop_table("auth_account")
    op.drop_index("auth_session_userId_idx", table_name="auth_session")
    op.drop_table("auth_session")
    op.drop_table("auth_user")
    op.execute("ALTER INDEX IF EXISTS ix_users_auth_subject RENAME TO ix_users_clerk_user_id")
    op.alter_column("users", "auth_subject", new_column_name="clerk_user_id")
