"""Pine 런타임 primitives — bar-by-bar 이벤트 루프가 사용하는 상태 컨테이너.

ADR-011 Tier-0 §2.0.2 "PyneCore transformers/ 참조 이식" 중 **var/varip 런타임**.
PyneCore(Apache 2.0)의 `transformers/persistent.py`는 **Python AST 변환**(pre-compile) 접근.
QB pine_v2는 **Pine AST 직접 해석** 파이프라인이므로 Python AST 재작성이 아닌
**런타임 state container**로 재설계. 의미론(초기화 한 번 + 바 지속 + varip 롤백 예외)만 이식.

공개 API:
- `PersistentStore` — var/varip 변수 상태 저장소
"""
from __future__ import annotations

from src.strategy.pine_v2.runtime.persistent import PersistentStore

__all__ = ["PersistentStore"]
