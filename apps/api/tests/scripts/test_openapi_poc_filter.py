"""[BL-717] OpenAPI PoC 필터의 전제 거부와 `$ref` 폐포를 고정한다.

실제 스크립트는 파일 위치에서 입력·출력 경로를 계산하고 출력 파일을 쓴다. 따라서 이 테스트는
항상 `tmp_path` 아래 가짜 저장소에 스크립트와 최소 OpenAPI 문서를 복사해 subprocess로 실행한다.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REAL = Path(__file__).resolve().parents[4] / "tools" / "scripts" / "openapi-poc-filter.py"


def _fake_repo(tmp_path: Path, source_doc: dict[str, Any] | None) -> Path:
    """`tmp_path`에 스크립트와 선택적인 전량 OpenAPI 문서를 만든다."""
    scripts = tmp_path / "tools" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REAL, scripts / "openapi-poc-filter.py")
    if source_doc is not None:
        source = tmp_path / "contracts" / "openapi" / "openapi.json"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(json.dumps(source_doc, ensure_ascii=False), encoding="utf-8")
    return scripts / "openapi-poc-filter.py"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _operation(schema_name: str | None = None) -> dict[str, Any]:
    response: dict[str, Any] = {"description": "ok"}
    if schema_name is not None:
        response["content"] = {
            "application/json": {
                "schema": {"$ref": f"#/components/schemas/{schema_name}"},
            },
        }
    return {"responses": {"200": response}}


def _source_doc() -> dict[str, Any]:
    """필터가 요구하는 세 경로와 최소 최상위 키를 모두 둔 원본 문서다."""
    return {
        "openapi": "3.1.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/health": {"get": _operation()},
            "/api/v1/strategies": {"get": _operation()},
            "/api/v1/backtests/{backtest_id}": {"get": _operation()},
        },
        "components": {"schemas": {}},
    }


def _output_path(repo_root: Path) -> Path:
    return repo_root / "contracts" / "openapi" / "poc" / "openapi.poc.json"


def test_missing_source_returns_precondition_error(tmp_path: Path) -> None:
    script = _fake_repo(tmp_path, source_doc=None)

    result = _run(script)

    assert result.returncode == 2
    assert "export_openapi.py 를 먼저 돌려라" in result.stderr


def test_missing_keep_path_returns_precondition_error(tmp_path: Path) -> None:
    source_doc = _source_doc()
    del source_doc["paths"]["/health"]
    script = _fake_repo(tmp_path, source_doc)

    result = _run(script)

    assert result.returncode == 2
    assert "/health" in result.stderr


def test_missing_keep_method_returns_precondition_error(tmp_path: Path) -> None:
    source_doc = _source_doc()
    source_doc["paths"]["/health"] = {"post": _operation()}
    script = _fake_repo(tmp_path, source_doc)

    result = _run(script)

    assert result.returncode == 2
    assert "메서드 누락" in result.stderr
    assert "/health" in result.stderr


def test_schema_refs_expand_to_transitive_closure(tmp_path: Path) -> None:
    source_doc = _source_doc()
    source_doc["paths"]["/health"] = {"get": _operation("A")}
    source_doc["components"]["schemas"] = {
        "A": {"properties": {"child": {"$ref": "#/components/schemas/B"}}},
        "B": {"properties": {"child": {"$ref": "#/components/schemas/C"}}},
        "C": {"type": "string"},
        "D": {"type": "number"},
    }
    script = _fake_repo(tmp_path, source_doc)

    result = _run(script)

    assert result.returncode == 0, result.stderr
    output = json.loads(_output_path(tmp_path).read_text(encoding="utf-8"))
    assert set(output["components"]["schemas"]) == {"A", "B", "C"}


def test_missing_schema_ref_target_returns_precondition_error(tmp_path: Path) -> None:
    source_doc = _source_doc()
    source_doc["paths"]["/health"] = {"get": _operation("Missing")}
    script = _fake_repo(tmp_path, source_doc)

    result = _run(script)

    assert result.returncode == 2
    assert "Missing" in result.stderr


@pytest.mark.parametrize("has_security_schemes", [True, False])
def test_security_schemes_are_preserved_only_when_present(
    tmp_path: Path,
    has_security_schemes: bool,
) -> None:
    source_doc = _source_doc()
    if has_security_schemes:
        source_doc["components"]["securitySchemes"] = {
            "bearerAuth": {"type": "http", "scheme": "bearer"},
        }
    script = _fake_repo(tmp_path, source_doc)

    result = _run(script)

    assert result.returncode == 0, result.stderr
    output = json.loads(_output_path(tmp_path).read_text(encoding="utf-8"))
    if has_security_schemes:
        assert output["components"]["securitySchemes"] == source_doc["components"][
            "securitySchemes"
        ]
    else:
        assert "securitySchemes" not in output["components"]
