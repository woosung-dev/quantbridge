"""Pine Script Tier-0 v2 모듈 — Sprint 8a pynescript 포크 기반 (ADR-011).

WARNING (라이선스):
- pynescript는 LGPL-3.0. PyPI 외부 의존성으로만 사용. 소스 copy 금지.
- 혹시라도 향후 포크·패치가 필요하면 `third_party/pynescript/` 서브디렉토리에
  원본 LGPL 헤더 보존 + NOTICE 갱신 후 격리.

공개 API:
- parse_and_run_v2(source, ohlcv) -> ParseOutcome  (Sprint 8b에서 구현 예정)
"""
from __future__ import annotations

from src.strategy.pine_v2.compat import parse_and_run_v2

__all__ = ["parse_and_run_v2"]
