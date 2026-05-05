"""Sprint 21 Phase A.0 — backend 422 shape 표준화.

codex G.0 P1 #5 — FE 가 detail 의 string 을 split 하지 않고 list 직접 접근하도록
`StrategyNotRunnable` exception 에 `unsupported_builtins: list[str]` 필드 추가 +
`app_exc_handler` 가 response body 에 list 노출.

Sprint 32 E (BL-163) — `friendly_message: str` 추가 + `StrategyDegraded` parity +
unhandled Exception 표준 5xx 응답 (`{"detail": "Internal server error..."}`).

본 test 는 conftest.py 의 db_session 의존 `app`/`client` fixture 를 우회하기 위해
standalone FastAPI app + TestClient 로 진행. handler 는 src.main module-level 에서 import.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.backtest.exceptions import (
    BacktestNotFound,
    StrategyDegraded,
    StrategyNotRunnable,
    format_friendly_message,
)
from src.common.exceptions import AppException
from src.main import app_exc_handler, unhandled_exc_handler


def _build_test_app() -> FastAPI:
    """conftest.py 의 db_session 의존 fixture 와 무관한 standalone app."""
    app = FastAPI()
    app.add_exception_handler(AppException, app_exc_handler)
    app.add_exception_handler(Exception, unhandled_exc_handler)
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


# -----------------------------------------------------------------------------
# Sprint 32 E (BL-163) — friendly_message + StrategyDegraded parity + 5xx 표준화
# -----------------------------------------------------------------------------


def test_format_friendly_message_includes_workaround_for_known_builtin() -> None:
    """`heikinashi` 는 corruption category + workaround SSOT 메시지를 포함."""
    msg = format_friendly_message(["heikinashi"])
    assert "heikinashi" in msg
    assert "Trust Layer" in msg
    assert "ADR-003 supported list" in msg
    # coverage._UNSUPPORTED_WORKAROUNDS 에 heikinashi 자체 entry 가 없을 수 있으나
    # category 라벨 (corruption) 은 항상 포함.


def test_format_friendly_message_array_new_float_workaround() -> None:
    """Pine v6 `array.new_float` — syntax category + 단일 series 변수 권장 안내."""
    msg = format_friendly_message(["array.new_float"])
    assert "array.new_float" in msg
    assert "Pine v6" in msg or "paradigm mismatch" in msg
    assert "단일 series" in msg or "ta.highest" in msg


def test_format_friendly_message_empty_returns_empty_string() -> None:
    """빈 list 는 빈 문자열 — FE 가 fallback root.serverError 로 분기."""
    assert format_friendly_message([]) == ""


def test_format_friendly_message_unknown_builtin_uses_generic_label() -> None:
    """매핑 미존재 builtin 은 generic '미지원 빌트인' fallback (KeyError 차단)."""
    msg = format_friendly_message(["xyz.zzz_random_unknown"])
    assert "xyz.zzz_random_unknown" in msg
    assert "미지원" in msg


def test_app_exc_handler_emits_friendly_message_for_strategy_not_runnable() -> None:
    """Sprint 32 E (BL-163): 422 response 가 friendly_message 필드 포함."""
    app = _build_test_app()

    @app.get("/_test_friendly")
    async def _raise() -> None:  # pragma: no cover — exception path
        raise StrategyNotRunnable(
            detail="Strategy contains unsupported Pine built-ins: heikinashi",
            unsupported_builtins=["heikinashi"],
        )

    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.get("/_test_friendly")

    assert res.status_code == 422
    body = res.json()
    assert body["detail"]["unsupported_builtins"] == ["heikinashi"]
    fm = body["detail"]["friendly_message"]
    assert isinstance(fm, str) and len(fm) > 0
    assert "heikinashi" in fm
    assert "ADR-003" in fm


def test_app_exc_handler_emits_friendly_message_for_strategy_degraded() -> None:
    """Sprint 32 E (BL-163): StrategyDegraded 도 friendly_message + degraded_calls 노출."""
    app = _build_test_app()

    @app.get("/_test_degraded")
    async def _raise() -> None:  # pragma: no cover — exception path
        raise StrategyDegraded(
            detail="Strategy uses degraded functions: heikinashi",
            degraded_calls=["heikinashi"],
        )

    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.get("/_test_degraded")

    assert res.status_code == 422
    body = res.json()
    assert body["detail"]["code"] == "strategy_degraded"
    assert body["detail"]["degraded_calls"] == ["heikinashi"]
    fm = body["detail"]["friendly_message"]
    assert isinstance(fm, str) and len(fm) > 0
    assert "heikinashi" in fm


def test_strategy_not_runnable_explicit_friendly_message_overrides_default() -> None:
    """호출부가 명시적으로 friendly_message 주입 시 그대로 사용 (자동 합성 무시)."""
    exc = StrategyNotRunnable(
        detail="generic",
        unsupported_builtins=["heikinashi"],
        friendly_message="custom override message",
    )
    assert exc.friendly_message == "custom override message"


def test_unhandled_exc_handler_returns_standardized_500_response() -> None:
    """Sprint 32 E (BL-163): unhandled Exception → JSON `{detail: "Internal..."}`.

    raw plain text "Internal Server Error" 또는 HTML 페이지 대신 정규화 dict 반환 →
    FE readErrorBody 가 일관 처리. dev 모드에선 exc class 노출.
    """
    app = _build_test_app()

    @app.get("/_test_unhandled")
    async def _raise() -> None:  # pragma: no cover — exception path
        raise RuntimeError("celery broker unreachable")

    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.get("/_test_unhandled")

    assert res.status_code == 500
    body = res.json()
    assert "detail" in body
    assert isinstance(body["detail"], str)
    # debug=True (test/dev) 시 exc class 노출, production 은 generic.
    # 둘 다 한국어 안내 포함 보장.
    assert "잠시 후 다시 시도" in body["detail"]


def test_unhandled_exc_handler_does_not_leak_stack_trace() -> None:
    """raw RuntimeError args (sensitive: e.g. SQL query) 가 body 에 노출되지 않음."""
    app = _build_test_app()

    @app.get("/_test_no_leak")
    async def _raise() -> None:  # pragma: no cover — exception path
        raise RuntimeError("SECRET_DB_URL=postgres://user:pass@host/db")

    with TestClient(app, raise_server_exceptions=False) as client:
        res = client.get("/_test_no_leak")

    assert res.status_code == 500
    body = res.json()
    # exc.args 의 raw 메시지는 노출 금지 (보안 leak risk).
    assert "SECRET_DB_URL" not in body["detail"]
    assert "postgres://" not in body["detail"]
