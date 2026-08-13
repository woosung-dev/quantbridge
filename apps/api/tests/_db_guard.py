# 파괴적 테스트 경로가 향할 DSN 을 고르고 그것이 버려도 되는 DB 인지 판정한다 (BL-451).
"""테스트 DSN 판정의 SSOT.

★**왜 한 곳인가.** 2026-07-25 exit-attribution 회차에 로컬 개발 DB 가 전소했다 — 주문 17행 ·
암호화된 Bybit demo API 키 1 · 전략 6종 Pine 소스 · 세션 4 · 이벤트 10. `.env.local` 에 평문
키가 없어 API 키는 **복구 불가**였다. 그 뒤 붙인 가드는 `tests/test_migrations.py` 안에만
있었고, `tests/real_broker/conftest.py` 가 같은 판정을 **베껴서** 한 벌 더 갖고 있었다.
판정이 두 벌이면 한 벌만 고쳐지는 날이 온다.

## 판정 규칙

1. `TEST_DATABASE_URL` 이 있으면 그것을 쓴다 — 단 database 이름이 `_test` 로 끝나야 한다.
2. `TEST_DATABASE_URL` 없이 `DATABASE_URL` 만 있으면 **거부한다**(폴백 금지).
   ★이것이 실사고의 형태였다. 종전에는 `DATABASE_URL` 로 조용히 폴백하고 그 DSN 의 이름만
   검사했다 — 「개발 DB 를 겨냥한 뒤 이름으로 걸러낸다」는 순서 자체가 위험했다.
3. 둘 다 없으면 `DEFAULT_TEST_DSN`.

## 왜 `effective_dsn()` 에는 폴백이 아예 없나

`refusal_reason()` 이 뚫려도(변이·리팩터·미래의 예외 처리) 겨냥 대상이 개발 DB 가 되지
않게 하려는 것이다. 가드는 판정만 하고, **어디를 겨냥할지는 애초에 `TEST_DATABASE_URL`
아니면 기본값뿐**이다. 두 층이 서로의 구멍을 막는다.

## `_test` 판정은 database 이름으로만 한다

`"_test" in dsn` 은 user/password/host 에 `_test` 가 있으면 통과해 버린다
(`tests/tasks/test_prefork_smoke_integration.py:30-62` 의 codex G.2 P1 #2 교훈).
"""

from __future__ import annotations

import os

DEFAULT_TEST_DSN = "postgresql+asyncpg://quantbridge:password@localhost:5432/quantbridge_test"

# 세션 중단 종료 코드. `tests/real_broker/conftest.py` 가 쓰던 값을 그대로 승계한다.
GUARD_EXIT_CODE = 3

_HOWTO = "해소: `cd apps/api && set -a; . ./.env.local; set +a` 로 TEST_DATABASE_URL 을 export 해라."


class NonDisposableDatabaseError(RuntimeError):
    """파괴적 경로가 버려도 되지 않는 DB 를 향했다."""


def effective_dsn() -> str:
    """파괴적 경로가 **실제로 겨냥할** DSN 하나.

    ★`DATABASE_URL` 폴백이 없다 — 위 모듈 독스트링 참조. 판정과 무관하게 이 함수는
    개발 DB 를 돌려주지 않는다.
    """
    return os.environ.get("TEST_DATABASE_URL") or DEFAULT_TEST_DSN


def refusal_reason() -> str | None:
    """세션을 끝내야 할 이유를 사람이 읽을 문장으로. 막을 이유가 없으면 `None`.

    ★`pytest` 에 의존하지 않는다 — 중단 방법(`pytest.exit` / `SystemExit`)을 고르는 것은
    호출자의 몫이다. 그래야 conftest 와 alembic 양쪽이 같은 판정을 쓸 수 있다.
    """
    explicit = os.environ.get("TEST_DATABASE_URL")

    if not explicit and os.environ.get("DATABASE_URL"):
        return (
            "중단 — TEST_DATABASE_URL 없이 DATABASE_URL 만 있다.\n"
            "  종전에는 여기서 DATABASE_URL 로 폴백했고, 그 DSN 이 개발 DB 를 가리켜 "
            "tests/conftest.py 의 세션 픽스처(SQLModel.metadata.drop_all)와 "
            "tests/test_migrations.py 의 downgrade(base) 가 개발 DB 를 전소시킨 적이 있다.\n"
            f"  {_HOWTO}"
        )

    dsn = effective_dsn()
    try:
        from sqlalchemy.engine import make_url

        database = make_url(dsn).database
    except Exception as exc:  # 파싱 실패 자체가 중단 사유다
        return f"중단 — TEST_DATABASE_URL 파싱 실패: {exc}\n  {_HOWTO}"

    if not database or not database.endswith("_test"):
        return (
            f"중단 — 유효 DSN 의 database='{database}' 가 '_test' 로 끝나지 않는다.\n"
            "  이 DB 에 SQLModel.metadata.drop_all 과 alembic downgrade(base) 가 돈다. "
            "개발 DB 를 물고 있으면 테이블이 전부 날아간다.\n"
            f"  {_HOWTO}"
        )

    return None


def resolve_test_dsn() -> str:
    """판정을 통과한 DSN. 통과 못 하면 `NonDisposableDatabaseError`.

    세션 최상단(`pytest_configure`)이 이미 같은 판정을 하므로 정상 실행에서 이 예외는
    올라오지 않는다 — 이것은 `tests/test_migrations.py` 가 **자기 파일만 읽는 사람에게도**
    무엇이 파괴적인지 보이게 하는 이중 방어다.
    """
    reason = refusal_reason()
    if reason is not None:
        raise NonDisposableDatabaseError(reason)
    return effective_dsn()


def assert_disposable(dsn: str) -> None:
    """주어진 DSN 하나가 버려도 되는 DB 인지 검사한다 (env 와 무관한 순수 판정)."""
    from sqlalchemy.engine import make_url

    database = make_url(dsn).database
    if not database or not database.endswith("_test"):
        raise NonDisposableDatabaseError(
            "파괴적 마이그레이션은 downgrade base 로 전 테이블을 드롭한다. "
            f"버려도 되는 DB(_test 접미사)만 허용하는데 '{database}' 를 받았다. "
            f"{_HOWTO}"
        )
