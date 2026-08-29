"""`@limiter.limit` 엔드포인트의 `request`/`response` 파라미터 census.

★**왜 이 검사가 있나.** slowapi 는 엔드포인트가 `Response` 가 아닌 값을 돌려주면
``_inject_headers(kwargs.get("response"), ...)`` 를 부르고(`slowapi/extension.py:734-741`),
거기서 ``isinstance(response, Response)`` 가 거짓이면 **예외를 raise 한다**(`:381-384`).
`headers_enabled=True`(`src/common/rate_limit.py:151`)이므로 **`response: Response` 를 선언하지 않은
rate-limited 엔드포인트는 성공 응답마다 500 이다.**

`request: Request` 쪽도 같다 — slowapi 가 `kwargs` 에서 `Request` 를 못 찾으면 예외를 던진다(`:725-727`).

★이 실패는 **유닛 테스트로 안 잡힌다** — 서비스 계층은 초록인 채 HTTP 경로만 죽는다.
2026-08-28 에 한 번, 2026-08-30 에 또 한 번 같은 방식으로 났다. 그래서 시그니처를 직접 잰다.

★**이 검사기가 못 보는 것**([LESSON-092]) — ⑴ 데코레이터 수신자 이름이 `limiter` 가 아닌 경우
(별칭 import·다른 Limiter 인스턴스)는 안 센다. ⑵ `app.state.limiter.exempt(...)` 로 면제된 경로도
똑같이 센다(면제와 무관하게 시그니처는 있어야 하므로 의도한 동작이다). ⑶ `router.py` 밖에 정의된
엔드포인트는 스캔 범위 밖이다 — 현재 전 엔드포인트가 `router.py` 에 있고, 그 사실을
`test_limited_endpoint_census_is_non_vacuous` 의 하한이 지킨다.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPOSITORY_ROOT = _BACKEND_ROOT.parent.parent
_SOURCE_ROOT = _BACKEND_ROOT / "src"

_REQUIRED_PARAMS = (("request", "Request"), ("response", "Response"))


@dataclass(frozen=True)
class _LimitedEndpoint:
    path: str
    lineno: int
    function_name: str
    missing: tuple[str, ...]


def _is_limiter_limit_decorator(node: ast.expr) -> bool:
    """``@limiter.limit(...)`` 만 참. ``@router.post(...)`` 등은 거짓."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "limit"
        and isinstance(func.value, ast.Name)
        and func.value.id == "limiter"
    )


def _annotation_name(annotation: ast.expr | None) -> str | None:
    if annotation is None:
        return None
    return ast.unparse(annotation).rsplit(".", maxsplit=1)[-1]


def _missing_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    declared = {
        arg.arg: _annotation_name(arg.annotation)
        for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
    }
    return tuple(name for name, annotation in _REQUIRED_PARAMS if declared.get(name) != annotation)


def _limited_endpoints(path: Path) -> list[_LimitedEndpoint]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    relative_path = path.relative_to(_REPOSITORY_ROOT).as_posix()
    found: list[_LimitedEndpoint] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not any(_is_limiter_limit_decorator(dec) for dec in node.decorator_list):
            continue
        found.append(
            _LimitedEndpoint(
                path=relative_path,
                lineno=node.lineno,
                function_name=node.name,
                missing=_missing_params(node),
            )
        )
    return found


def _router_paths() -> list[Path]:
    return sorted(_SOURCE_ROOT.rglob("router.py"))


def _all_limited_endpoints() -> list[_LimitedEndpoint]:
    return [endpoint for path in _router_paths() for endpoint in _limited_endpoints(path)]


def test_detector_separates_limiter_decorators_from_route_decorators() -> None:
    """양성/음성 대조 — 이 검사가 무엇을 보는지 먼저 증명한다."""
    tree = ast.parse(
        """
@router.post("/a", response_model=X)
@limiter.limit("5/minute")
async def both_present(request: Request, response: Response) -> X: ...

@router.get("/b")
@limiter.limit("5/minute")
async def response_missing(request: Request) -> X: ...

@router.get("/c")
@limiter.limit("5/minute")
async def request_missing(response: Response) -> X: ...

@router.get("/d")
async def not_limited(x: int) -> X: ...

@limiter.limit("5/minute")
def wrong_annotation(request: int, response: str) -> X: ...
"""
    )
    found = {
        node.name: _missing_params(node)
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and any(_is_limiter_limit_decorator(dec) for dec in node.decorator_list)
    }

    assert found == {
        "both_present": (),
        "response_missing": ("response",),
        "request_missing": ("request",),
        "wrong_annotation": ("request", "response"),
    }


def test_limited_endpoint_census_is_non_vacuous() -> None:
    """빈 입력을 초록으로 통과시키지 않는다."""
    endpoints = _all_limited_endpoints()

    assert len(_router_paths()) >= 8
    assert len(endpoints) >= 14


def test_every_rate_limited_endpoint_declares_request_and_response() -> None:
    violations = {
        (endpoint.path, endpoint.function_name, endpoint.missing)
        for endpoint in _all_limited_endpoints()
        if endpoint.missing
    }

    assert violations == set(), (
        "slowapi `_inject_headers` 가 성공 응답마다 500 을 낸다 — "
        f"누락 시그니처: {sorted(violations)}"
    )
