#!/usr/bin/env python
"""기존 `users` 행을 새 인증 공급자의 subject 에 잇는다 (ADR-034 이관 도구).

왜 필요한가 — 인증을 Clerk 에서 Better Auth 로 옮기면 **사용자의 외부 ID 가 바뀐다.**
`users.auth_subject` 에는 아직 구 Clerk subject 가 들어 있고, 새로 로그인하면 그 subject 가
DB 에 없으므로 JIT 프로비저닝이 **빈 계정을 새로 만든다** — 전략·백테스트·주문이 그대로
남아 있는데 화면에는 아무것도 안 보이는 상태가 된다.

이 스크립트는 그 한 줄을 잇는다. **대량 이관 스크립트가 아니다** — 프로덕션 실사용자가
2명(데이터 보유 1명)이라 CSV 파이프라인을 만들 이유가 없다고 판정했다(ADR-034 §D9).

사용법:
    cd apps/api && set -a; . ./.env.local; set +a
    # ① 지금 상태를 본다 (쓰기 없음)
    uv run python scripts/link_auth_subject.py --list
    # ② 이을 대상을 확인한다 (기본 dry-run — 무엇이 바뀌는지만 출력)
    uv run python scripts/link_auth_subject.py --user-id <UUID> --subject <새 subject>
    # ③ 집행 (★사용자 승인 뒤에만 — 이것은 남의 데이터 UPDATE 다)
    uv run python scripts/link_auth_subject.py --user-id <UUID> --subject <새 subject> --confirm

★새 subject 는 로그인한 뒤 브라우저에서 `/api/auth/token` 의 JWT `sub`, 또는 서버에서
  `SELECT id FROM auth_user WHERE email = ...` 로 얻는다.
★`--confirm` 없이는 **아무것도 쓰지 않는다.** 기본이 dry-run 인 것은 이 레포 관례다
  (`soak-stack.sh migrate` · `soak-restart.sh` 와 같은 형태).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

# 스크립트 직접 실행 지원 — `apps/api` 를 import 루트에 얹는다(레포 관례).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.auth.models import User
from src.core.config import secret_value, settings


def _mask(value: str | None) -> str:
    """이메일을 그대로 찍지 않는다 — 로그·터미널 스크롤백에 남는다."""
    if not value:
        return "(없음)"
    head, _, domain = value.partition("@")
    return f"{head[:2]}***@{domain}" if domain else f"{head[:2]}***"


async def _list(session: AsyncSession) -> int:
    rows = (await session.execute(select(User).order_by(User.created_at))).scalars().all()
    if not rows:
        print("users 행이 없다.")
        return 0
    print(f"{'id':38}  {'auth_subject':34}  {'email':22}  active")
    for u in rows:
        print(f"{u.id!s:38}  {u.auth_subject:34}  {_mask(u.email):22}  {u.is_active}")
    return 0


async def _link(session: AsyncSession, user_id: UUID, subject: str, confirm: bool) -> int:
    target = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()  # type: ignore[arg-type]
    if target is None:
        print(f"✗ users.id={user_id} 를 찾지 못했다.", file=sys.stderr)
        return 1

    clash = (
        await session.execute(select(User).where(User.auth_subject == subject))  # type: ignore[arg-type]
    ).scalar_one_or_none()
    if clash is not None and clash.id != user_id:
        # ★이 경우가 실제로 흔하다 — 새로 로그인하면 JIT 이 **빈 계정**을 먼저 만들어 둔다.
        #   그 행을 지우는 것은 이 스크립트의 일이 아니다(사람이 판단한다).
        print(
            f"✗ subject={subject} 는 이미 다른 사용자({clash.id})가 갖고 있다.\n"
            "  새 로그인이 만든 빈 계정일 가능성이 높다 — 어느 행을 남길지 사람이 정해라.",
            file=sys.stderr,
        )
        return 1

    print(f"users.id={user_id}")
    print(f"  auth_subject: {target.auth_subject}  →  {subject}")
    print(f"  email(마스킹): {_mask(target.email)} · is_active={target.is_active}")
    if not confirm:
        print("\n(dry-run — 아무것도 쓰지 않았다. 집행하려면 --confirm)")
        return 0

    target.auth_subject = subject
    session.add(target)
    await session.commit()
    print("\n✓ 적용했다.")
    return 0


async def _main() -> int:
    parser = argparse.ArgumentParser(description="users.auth_subject 를 새 subject 로 잇는다")
    parser.add_argument("--list", action="store_true", help="현재 users 행을 출력하고 끝낸다")
    parser.add_argument("--user-id", type=UUID, help="대상 users.id (UUID)")
    parser.add_argument("--subject", help="새 auth_subject (Better Auth user id)")
    parser.add_argument("--confirm", action="store_true", help="실제로 UPDATE 한다")
    args = parser.parse_args()

    engine = create_async_engine(secret_value(settings.database_url), echo=False)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with maker() as session:
            if args.list:
                return await _list(session)
            if args.user_id is None or not args.subject:
                parser.error("--list 이거나 --user-id 와 --subject 를 함께 줘야 한다")
            return await _link(session, args.user_id, args.subject, args.confirm)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
