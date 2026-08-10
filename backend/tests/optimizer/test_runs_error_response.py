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
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.optimizer.router import (
    submit_bayesian,
    submit_genetic,
    submit_grid_search,
)

# ★2026-08-11 — 아래 HTTP integration 2건이 2026-05-14 부터 `@pytest.mark.skip("fixture
#   DB password 환경 issue")` 로 죽어 있었다. **그 사유는 거짓이다** — DB 도 비밀번호도
#   무관하고, 실제 원인은 이 payload 가 **낡았다**는 것이다. `CreateOptimizationRunRequest`
#   는 `extra="forbid"` 인데 payload 가 `cost_assumption`·`max_concurrent_evaluations` 를
#   보냈고, `ParamSpace` 는 그 사이 `objective_metric`·`direction`·`max_evaluations` 를
#   필수로 얻었다. 그래서 두 건 다 요청 검증 단계에서 **422** 로 튕겼다.
#
# ★그리고 그 422 는 조용한 거짓 초록을 만들었다 — `test_forced_service_exception…` 은
#   `status_code >= 400` 과 `detail` 키만 보므로 422 로도 통과한다. 즉 skip 을 떼자마자
#   「통과」하지만 `_BoomService` 에는 **도달조차 못 한다.** 그래서 페이로드를 지금 스키마로
#   고치고, 도달 여부를 상태코드로 못 박는다(422 는 실패로 본다).
_PARAM_SPACE: dict = {
    "schema_version": 1,
    "objective_metric": "sharpe_ratio",
    "direction": "maximize",
    "max_evaluations": 10,
    "parameters": {"length": {"kind": "integer", "min": 5, "max": 20, "step": 5}},
}


def _request_body(kind: str) -> dict:
    """`CreateOptimizationRunRequest` 가 실제로 받는 3키 그대로 (extra="forbid")."""
    return {"backtest_id": str(uuid4()), "kind": kind, "param_space": _PARAM_SPACE}


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


@pytest.mark.asyncio
async def test_forced_service_exception_returns_json_not_text_traceback(
    app: FastAPI,
    db_session: AsyncSession,
    mock_clerk_auth: User,
) -> None:
    """P1-4 채택 — service 가 RuntimeError 발생시켜도 응답이 JSON + no traceback.

    BL-244 fix 후에도 다른 unhandled exception 이 stack-trace 로 누설되면 안 됨.
    Sprint 32 BL-163 unhandled_exc_handler (json 정규화) + Sprint 54 BL-230
    OptimizationExecutionError(public, internal) 패턴 보존 검증.

    ★공용 `client` 픽스처를 안 쓴다 — 그쪽 `ASGITransport` 는 `raise_app_exceptions=True`
    (httpx 기본)라 starlette `ServerErrorMiddleware` 가 핸들러로 응답을 만들어 보낸 **뒤
    다시 raise** 하는 예외를 호출부까지 올려버린다. 그러면 검사할 응답 자체가 손에
    안 들어온다. 실서버(uvicorn)는 그 재-raise 를 삼키고 응답만 내보내므로, 그 계약을
    재현하려면 `raise_app_exceptions=False` 여야 한다.
    """
    from src.optimizer.dependencies import get_optimizer_service

    class _BoomService:
        async def submit_grid_search(self, *args, **kwargs):
            raise RuntimeError("internal secret detail leak attempt 7f3a")

        async def submit_bayesian(self, *args, **kwargs):
            raise RuntimeError("internal secret detail leak attempt 7f3a")

        async def submit_genetic(self, *args, **kwargs):
            raise RuntimeError("internal secret detail leak attempt 7f3a")

    # ★프로덕션 경로를 재현한다. `app_env=production` 은 validator 가 `debug=False` 를
    #   강제하지만(`core/config.py:372-374`) 로컬 `.env.local` 은 `DEBUG=true` 다. 그러면
    #   starlette `ServerErrorMiddleware` 가 `unhandled_exc_handler` 대신 debug 분기로
    #   빠져 **19,534바이트 text/plain 트레이스백**을 낸다(2026-08-11 실측). 그것은 의도된
    #   dev 동작이지 BL-244 회귀가 아니다 — 이 테스트가 재려는 것은 프로덕션 계약이다.
    #   미들웨어 스택은 첫 요청에서 lazy 로 세워지므로 여기서 None 으로 되돌리면 다시 선다.
    app.debug = False
    app.middleware_stack = None

    app.dependency_overrides[get_optimizer_service] = lambda: _BoomService()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as boom_client:
            resp = await boom_client.post(
                "/api/v1/optimizer/runs/grid-search",
                json=_request_body("grid_search"),
            )
    finally:
        app.dependency_overrides.pop(get_optimizer_service, None)

    # 0) ★도달 확인 — 422 면 요청 검증에서 튕겨 `_BoomService` 를 부르지도 못한 것이다.
    #    아래 1~5 는 422 로도 전부 통과하므로 이 한 줄이 없으면 **무증거 초록**이 된다.
    assert resp.status_code != 422, (
        f"payload 가 낡아 요청 검증에서 422 로 튕겼다 — _BoomService 에 도달하지 못했다: "
        f"{resp.text[:300]!r}"
    )

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
                param_space=_PARAM_SPACE,
                # ★`best_params`·`best_objective_value`·`task_id` 는 스키마에서 사라졌고
                #   `result` 로 합쳐졌다. `extra="forbid"` 라 옛 이름은 그대로 터진다 —
                #   이 파일이 3개월 skip 되어 있던 동안 벌어진 두 번째 드리프트다.
                result=None,
                error_message=None,
                created_at=now,
                started_at=None,
                completed_at=None,
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
            resp = await client.post(f"/api/v1/optimizer/runs/{path}", json=_request_body(kind))
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
