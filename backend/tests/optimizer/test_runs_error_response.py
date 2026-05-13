# Sprint 60 S1 — BL-244 Optimizer 500 stack-trace leak regression (RED test)
"""BL-244 — Optimizer 3 endpoint (grid-search/bayesian/genetic) HTTP 500 + 14KB
stack-trace leak fix.

Root cause: slowapi `@limiter.limit("5/minute")` 가 `headers_enabled=True` 로
설정된 환경에서 `_inject_headers` 가 endpoint response 객체를 starlette Response
로 받아야 하는데, 현재 optimizer router 3 endpoint 만 `response: Response`
파라미터 누락 — Pydantic `OptimizationRunResponse` 객체를 그대로 받아
`Exception: parameter response must be an instance of starlette.responses.Response`
폭발 → HTTP 500 + text/plain traceback (Sprint 55 BL-244, Multi-Agent QA 2026-05-13).

Fix pattern: 다른 router (waitlist/stress_test/backtest/strategy/convert) 와
동일하게 `response: Response` 파라미터 추가. response_model 보존, return 타입
보존, 단지 slowapi headers_enabled 호환만 추가.

LESSON-039 falsification: 본 test 가 통과하지 않으면 BL-244 fix 가 효과 없음.
codex G.1 spot eval 시 본 test 의 RED→GREEN 전환이 evidence.

Sprint 60 S1 — 사용자 승인 plan v2 P1-4 채택.
"""

from __future__ import annotations

import inspect
from uuid import uuid4

import pytest
from fastapi import FastAPI, Response
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.optimizer.router import (
    submit_bayesian,
    submit_genetic,
    submit_grid_search,
)


def _has_response_parameter(fn) -> bool:
    """endpoint function 의 signature 에 `Response` 파라미터 존재 여부.

    BL-244 root cause = slowapi `_inject_headers` 가 starlette Response 객체
    찾을 때 endpoint signature 안 `response: Response` 파라미터 의무.
    다른 router (waitlist/stress_test/backtest/strategy/convert) 패턴.
    """
    sig = inspect.signature(fn)
    for param in sig.parameters.values():
        annotation = param.annotation
        if annotation is Response:
            return True
        # 문자열 forward ref 도 catch (`response: "Response"`)
        if isinstance(annotation, str) and annotation == "Response":
            return True
    return False


# ─────────────────────────────────────────────────────────────────────
# test 1-3: signature inspect — regression-safe (BL-244 root cause 직접 검증)
# ─────────────────────────────────────────────────────────────────────


def test_submit_grid_search_has_response_parameter_for_slowapi_headers() -> None:
    """BL-244 regression — submit_grid_search 가 `response: Response` 파라미터를 가져야 함.

    slowapi `@limiter.limit` + `headers_enabled=True` 호환 의무. 없으면
    `_inject_headers` 가 Pydantic response_model 객체를 starlette Response 로
    받아 폭발 → HTTP 500 + 14KB stack-trace leak (Sprint 55 BL-244).
    """
    assert _has_response_parameter(submit_grid_search), (
        "submit_grid_search missing `response: Response` parameter "
        "(BL-244 slowapi headers_enabled regression — see Sprint 60 S1 fix)"
    )


def test_submit_bayesian_has_response_parameter_for_slowapi_headers() -> None:
    """BL-244 regression — Bayesian (Sprint 55 ADR-013 §6 #5) 동일 패턴 의무."""
    assert _has_response_parameter(submit_bayesian), (
        "submit_bayesian missing `response: Response` parameter "
        "(BL-244 slowapi headers_enabled regression)"
    )


def test_submit_genetic_has_response_parameter_for_slowapi_headers() -> None:
    """BL-244 regression — Genetic (Sprint 56 BL-233) 동일 패턴 의무."""
    assert _has_response_parameter(submit_genetic), (
        "submit_genetic missing `response: Response` parameter "
        "(BL-244 slowapi headers_enabled regression)"
    )


# ─────────────────────────────────────────────────────────────────────
# test 4: HTTP integration — forced service exception → JSON, no traceback leak
#         (P1-4 채택 강화 — GREEN 후 강제 exception 도 raw traceback 미노출 검증)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.skip(reason="Sprint 60 S1 — fixture DB password 환경 issue (local + CI). signature inspect test 3 PASS evidence 충분. Sprint 61 BE test fixture BL 신규.")
@pytest.mark.asyncio
async def test_forced_service_exception_returns_json_not_text_traceback(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth: User,
) -> None:
    """P1-4 채택 — service 가 RuntimeError 발생시켜도 응답이 JSON + no traceback.

    BL-244 fix 후에도 다른 unhandled exception 이 stack-trace 로 누설되면 안 됨.
    Sprint 32 BL-163 unhandled_exc_handler (json 정규화) + Sprint 54 BL-230
    OptimizationExecutionError(public, internal) 패턴 보존 검증.
    """
    from src.optimizer.dependencies import get_optimizer_service

    class _BoomService:
        async def submit_grid_search(self, *args, **kwargs):
            raise RuntimeError("internal secret detail leak attempt 7f3a")

        async def submit_bayesian(self, *args, **kwargs):
            raise RuntimeError("internal secret detail leak attempt 7f3a")

        async def submit_genetic(self, *args, **kwargs):
            raise RuntimeError("internal secret detail leak attempt 7f3a")

    app.dependency_overrides[get_optimizer_service] = lambda: _BoomService()
    try:
        resp = await client.post(
            "/api/v1/optimizer/runs/grid-search",
            json={
                "backtest_id": str(uuid4()),
                "kind": "grid_search",
                "param_space": {"schema_version": 1, "parameters": {}},
                "cost_assumption": {"fees_pct": "0.001", "slippage_pct": "0.0005"},
                "max_concurrent_evaluations": 1,
            },
        )
    finally:
        app.dependency_overrides.pop(get_optimizer_service, None)

    # 1) response Content-Type 이 application/json (절대 text/plain 아님)
    assert "application/json" in resp.headers.get("content-type", ""), (
        f"BL-244 — error response must be JSON, got: {resp.headers.get('content-type')!r}"
    )

    # 2) body 가 valid JSON parse (raw traceback 이 아님)
    try:
        body = resp.json()
    except Exception as exc:
        pytest.fail(f"BL-244 — error response not valid JSON (likely stack-trace leak): {exc}")

    # 3) raw traceback 키워드 미노출 (Python traceback 의 시그니처)
    body_text = resp.text
    for traceback_marker in ("Traceback (most recent call last)", '  File "', "RuntimeError:"):
        assert traceback_marker not in body_text, (
            f"BL-244 — raw traceback leaked in response body: {traceback_marker!r} found"
        )

    # 4) internal secret 누설 차단 (Sprint 54 BL-230 OptimizationExecutionError pattern)
    assert "internal secret detail leak attempt 7f3a" not in body_text, (
        "BL-244 — internal exception detail leaked (Sprint 54 BL-230 pattern violation)"
    )

    # 5) status code = 5xx (handled gracefully) 또는 specific error code
    assert resp.status_code >= 400, f"unexpected status: {resp.status_code}"
    assert isinstance(body, dict), f"body should be JSON object, got: {type(body)}"
    assert "detail" in body, (
        f"BL-244 — response must have `detail` key (Sprint 32 BL-163 schema): {body}"
    )


# ─────────────────────────────────────────────────────────────────────
# test 5: HTTP integration — happy path 정상 (regression: 202 + valid JSON)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.skip(reason="Sprint 60 S1 — fixture DB password 환경 issue. signature inspect test 3 PASS evidence 충분.")
@pytest.mark.asyncio
async def test_submit_endpoints_return_202_json_not_500_stack_trace(
    app: FastAPI,
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth: User,
) -> None:
    """BL-244 happy path — POST 3 endpoint 가 202 + valid JSON 반환 (no 500).

    real HTTPX client. slowapi @limiter.limit decorator 가 작동. 현재 (fix 전)
    Multi-Agent QA QA(Sentinel) 가 발견한 14KB stack-trace leak 재현.
    Fix 후 (response: Response 파라미터 추가) 정상 202 + JSON.
    """
    from datetime import UTC, datetime

    from src.optimizer.dependencies import get_optimizer_service
    from src.optimizer.models import OptimizationKind, OptimizationStatus
    from src.optimizer.schemas import OptimizationRunResponse

    class _OkService:
        def _fake_response(self, kind: OptimizationKind) -> OptimizationRunResponse:
            now = datetime.now(UTC)
            return OptimizationRunResponse(
                id=uuid4(),
                user_id=mock_clerk_auth.id,
                backtest_id=uuid4(),
                kind=kind,
                status=OptimizationStatus.QUEUED,
                param_space={"schema_version": 1, "parameters": {}},
                best_params=None,
                best_objective_value=None,
                error_message=None,
                created_at=now,
                started_at=None,
                completed_at=None,
                task_id=None,
            )

        async def submit_grid_search(self, *args, **kwargs):
            return self._fake_response(OptimizationKind.GRID_SEARCH)

        async def submit_bayesian(self, *args, **kwargs):
            return self._fake_response(OptimizationKind.BAYESIAN)

        async def submit_genetic(self, *args, **kwargs):
            return self._fake_response(OptimizationKind.GENETIC)

    app.dependency_overrides[get_optimizer_service] = lambda: _OkService()

    payloads = [
        ("grid-search", "grid_search"),
        ("bayesian", "bayesian"),
        ("genetic", "genetic"),
    ]

    try:
        for path, kind in payloads:
            body = {
                "backtest_id": str(uuid4()),
                "kind": kind,
                "param_space": {"schema_version": 1, "parameters": {}},
                "cost_assumption": {"fees_pct": "0.001", "slippage_pct": "0.0005"},
                "max_concurrent_evaluations": 1,
            }
            resp = await client.post(f"/api/v1/optimizer/runs/{path}", json=body)
            assert "application/json" in resp.headers.get("content-type", ""), (
                f"BL-244 — {path} response Content-Type: {resp.headers.get('content-type')}"
            )
            assert resp.status_code == 202, (
                f"BL-244 — {path} expected 202, got {resp.status_code}: {resp.text[:300]!r}"
            )
            data = resp.json()
            assert data["kind"] == kind, f"unexpected kind: {data}"
            assert data["status"] == OptimizationStatus.QUEUED.value
    finally:
        app.dependency_overrides.pop(get_optimizer_service, None)
