"""Better Auth 가 쓰는 5테이블의 **선언** — 우리 코드는 이 테이블을 읽지도 쓰지도 않는다(ADR-034).

왜 여기 있나: DDL 정본을 alembic 하나로 유지하기 위해서다. Better Auth 의 `migrate` CLI 는
Kysely 로 DB 를 직접 치는데, 이 레포는 「서버 소크 DB 에 DDL = `soak-stack.sh migrate --confirm`
+ 매번 명시 승인」이 규약이다([BL-743]). 그래서 스키마는 `@better-auth/cli generate` 로 **뽑아서**
alembic revision 으로 옮겼고, 그 결과를 metadata 에 선언해 `alembic check` 가 이 5개를
「removed table」로 오인하지 않게 한다([BL-770] 과 같은 축).

★**ORM 엔티티가 아니다.** repository 도 service 도 이 테이블을 건드리지 않는다 —
소유자는 Next 앱 안의 Better Auth 이고, 우리는 그 사람이 발급한 JWT 만 본다.

★**부채 하나**: Better Auth 버전을 올릴 때 `pnpm --dir apps/web exec @better-auth/cli generate`
를 다시 돌려 이 선언과 대조해라. 절차는 `docs/reference/operations/better-auth-setup.md`.
컬럼 이름이 camelCase 인 것은 Better Auth 규약이라 그대로 둔다(따옴표 식별자).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlmodel import SQLModel

_TS = sa.TIMESTAMP(timezone=True)
_NOW = sa.text("CURRENT_TIMESTAMP")

auth_user = sa.Table(
    "auth_user",
    SQLModel.metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("email", sa.Text, nullable=False, unique=True),
    sa.Column("emailVerified", sa.Boolean, nullable=False),
    sa.Column("image", sa.Text, nullable=True),
    sa.Column("createdAt", _TS, nullable=False, server_default=_NOW),
    sa.Column("updatedAt", _TS, nullable=False, server_default=_NOW),
    # `user.additionalFields.country` — geo-block L3 이 가입 시점에 채운다.
    sa.Column("country", sa.Text, nullable=True),
)

auth_session = sa.Table(
    "auth_session",
    SQLModel.metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("expiresAt", _TS, nullable=False),
    sa.Column("token", sa.Text, nullable=False, unique=True),
    sa.Column("createdAt", _TS, nullable=False, server_default=_NOW),
    sa.Column("updatedAt", _TS, nullable=False),
    sa.Column("ipAddress", sa.Text, nullable=True),
    sa.Column("userAgent", sa.Text, nullable=True),
    sa.Column(
        "userId",
        sa.Text,
        sa.ForeignKey("auth_user.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Index("auth_session_userId_idx", "userId"),
)

auth_account = sa.Table(
    "auth_account",
    SQLModel.metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("accountId", sa.Text, nullable=False),
    sa.Column("providerId", sa.Text, nullable=False),
    sa.Column(
        "userId",
        sa.Text,
        sa.ForeignKey("auth_user.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("accessToken", sa.Text, nullable=True),
    sa.Column("refreshToken", sa.Text, nullable=True),
    sa.Column("idToken", sa.Text, nullable=True),
    sa.Column("accessTokenExpiresAt", _TS, nullable=True),
    sa.Column("refreshTokenExpiresAt", _TS, nullable=True),
    sa.Column("scope", sa.Text, nullable=True),
    # ★비밀번호 해시가 사는 곳은 `auth_user` 가 아니라 여기다(providerId='credential').
    sa.Column("password", sa.Text, nullable=True),
    sa.Column("createdAt", _TS, nullable=False, server_default=_NOW),
    sa.Column("updatedAt", _TS, nullable=False),
    sa.Index("auth_account_userId_idx", "userId"),
)

auth_verification = sa.Table(
    "auth_verification",
    SQLModel.metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("identifier", sa.Text, nullable=False),
    sa.Column("value", sa.Text, nullable=False),
    sa.Column("expiresAt", _TS, nullable=False),
    sa.Column("createdAt", _TS, nullable=False, server_default=_NOW),
    sa.Column("updatedAt", _TS, nullable=False, server_default=_NOW),
    sa.Index("auth_verification_identifier_idx", "identifier"),
)

auth_jwks = sa.Table(
    "auth_jwks",
    SQLModel.metadata,
    sa.Column("id", sa.Text, primary_key=True),
    sa.Column("publicKey", sa.Text, nullable=False),
    # ★암호화되어 저장된다(AES256-GCM). 그래도 이 테이블은 인증 전용 DB 롤만 읽을 수 있어야 한다.
    sa.Column("privateKey", sa.Text, nullable=False),
    sa.Column("createdAt", _TS, nullable=False),
    sa.Column("expiresAt", _TS, nullable=True),
)

__all__ = [
    "auth_account",
    "auth_jwks",
    "auth_session",
    "auth_user",
    "auth_verification",
]
