"""pynescript 파스 어댑터 — 백테스트 파싱 진입점은 이 파일 하나다.

AST 노드 `isinstance` 판정에는 여러 모듈의 pynescript 공개 API import가 필요하다.
파스 결과는 최근 소스 8개만 보관한다. parse preview에는 rate limit·소스 길이 상한이
없으므로 무제한 캐시 대신, 반복 백테스트 이득과 메모리 상한을 함께 둔다.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pynescript import ast as pyne_ast


@lru_cache(maxsize=8)
def parse_to_ast(source: str) -> Any:
    """Pine 소스를 pynescript AST로 변환. 반환 타입은 pynescript 내부 AST 노드."""
    return pyne_ast.parse(source)
