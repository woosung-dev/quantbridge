"""Sprint 21 Phase A.0 — backend 422 shape 표준화.

codex G.0 P1 #5 — FE 가 detail 의 string 을 split 하지 않고 list 직접 접근하도록
`StrategyNotRunnable` exception 에 `unsupported_builtins: list[str]` 필드 추가 +
`app_exc_handler` 가 response body 에 list 노출.

본 test 는 conftest.py 의 db_session 의존 `app`/`client` fixture 를 우회하기 위해
standalone FastAPI app + TestClient 로 진행. handler 는 src.main module-level 에서 import.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.backtest.exceptions import BacktestNotFound, StrategyNotRunnable
from src.common.exceptions import AppException
from src.main import app_exc_handler


def _build_test_app() -> FastAPI:
    """conftest.py 의 db_session 의존 fixture 와 무관한 standalone app."""
    app = FastAPI()
    app.add_exception_handler(AppException, app_exc_handler)
    return app


def test_strategy_not_runnable_has_unsupported_builtins_attribute() -> None:
    """exception 자체가 unsupported_builtins list 보유 (codex G.0 P1 #5)."""
    exc = StrategyNotRunnable(
        detail=(
            "Strategy contains unsupported Pine built-ins: heikinashi, security. "
            "See docs/02_domain/supported-indicators.md for the supported list."
        ),
        unsupported_builtins=["heikinashi", "security"],
    )
    assert exc.unsupported_builtins == ["heikinashi", "security"]
    assert exc.code == "strategy_not_runnable"
    assert exc.status_code == 422


def test_strategy_not_runnable_default_empty_unsupported_builtins() -> None:
    """unsupported_builtins 미명시 시 빈 list (backward compat)."""
    exc = StrategyNotRunnable(detail="legacy detail message")
    assert exc.unsupported_builtins == []


def test_app_exc_handler_serializes_unsupported_builtins() -> None:
    """422 response body 가 detail.unsupported_builtins 를 list 로 노출.

    기존 detail string 도 backward compat 유지 (FE 가 신규 list 우선,
    fallback 으로 string 사용 가능).
    """
    app = _build_test_app()

    @app.get("/_test_strategy_not_runnable")
    async def _raise() -> None:  # pragma: no cover — exception path
        raise StrategyNotRunnable(
            detail=(
                "Strategy contains unsupported Pine built-ins: heikinashi, security. "
                "See docs/02_domain/supported-indicators.md for the supported list."
            ),
            unsupported_builtins=["heikinashi", "security"],
        )

    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.get("/_test_strategy_not_runnable")

    assert res.status_code == 422
    body = res.json()
    assert body["detail"]["code"] == "strategy_not_runnable"
    assert body["detail"]["unsupported_builtins"] == ["heikinashi", "security"]
    assert "heikinashi, security" in body["detail"]["detail"]


def test_app_exc_handler_omits_list_for_other_app_exceptions() -> None:
    """다른 AppException 에서는 unsupported_builtins 키 미포함 (StrategyNotRunnable 한정)."""
    app = _build_test_app()

    @app.get("/_test_other_app_exception")
    async def _raise() -> None:  # pragma: no cover — exception path
        raise BacktestNotFound()

    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.get("/_test_other_app_exception")

    assert res.status_code == 404
    body = res.json()
    assert body["detail"]["code"] == "backtest_not_found"
    assert "unsupported_builtins" not in body["detail"]


def test_app_exc_handler_empty_unsupported_builtins_still_emits_list_key() -> None:
    """unsupported_builtins 가 빈 list 라도 key 는 노출 (FE 가 빈 list 처리 가능)."""
    app = _build_test_app()

    @app.get("/_test_empty_unsupported")
    async def _raise() -> None:  # pragma: no cover — exception path
        raise StrategyNotRunnable(detail="generic message", unsupported_builtins=[])

    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.get("/_test_empty_unsupported")

    assert res.status_code == 422
    body = res.json()
    assert body["detail"]["unsupported_builtins"] == []
