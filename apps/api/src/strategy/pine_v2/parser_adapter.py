"""pynescript 호출 레이어 — 이 파일만 `import pynescript` 허용.

라이선스 경계를 한 지점으로 집중시키기 위한 설계. QB 비즈니스 로직은
`ast_metrics.py` / 향후 `interpreter.py` 등에서 pynescript 공개 API만 호출.
"""
from __future__ import annotations

from typing import Any

from pynescript import ast as pyne_ast


def parse_to_ast(source: str) -> Any:
    """Pine 소스를 pynescript AST로 변환. 반환 타입은 pynescript 내부 AST 노드."""
    return pyne_ast.parse(source)
