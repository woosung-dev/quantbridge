# pine_v2 — Track S/A/M dispatcher unified registry (BL-201)
"""Sprint 48 BL-201 — Track S/A/M dispatch 단일 레지스트리.

`compat.parse_and_run_v2` 의 if-chain (Track S → run_historical / Track A →
run_virtual_strategy / Track M → run_historical / unknown → ValueError) 을
dict 기반 registry 로 압축.

deepen-modules audit (Sprint 47 codex G.0) 에서 발견된 cross-module dispatcher
분산 패턴 통합. 동일 코드 경로 4 분산 사이트 (compat.py / 향후 trace 등) 를
단일 invoke() 로 좁힌다.

설계 원칙 (codex Fix #2 의무):
    - `classify_script()` 는 대체 금지. compat.py 의 `track = profile.track`
      단계는 그대로 유지. TrackRunner 는 dispatch 부분만 줄인다.
    - `_dispatch_table` 은 module-level dict. import 시점에 함수 레퍼런스 고정
      (object identity `is` 비교 통과 → BL-200 SSOT 패턴 정합).
    - kwargs 전부 forward (D2 sizing + sessions_allowed). 명시적 field 펼침
      금지 — runner signature 변경 시 forward 누락 위험 차단.

V2RunResult shape 보존:
    - Track S/M → V2RunResult(track=..., historical=<RunResult>, virtual=None)
    - Track A   → V2RunResult(track=..., historical=None, virtual=<VirtualRunResult>)
    - unknown   → ValueError raise (compat.py:137 형식 보존)
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar

from src.strategy.pine_v2.ast_classifier import Track
from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.virtual_strategy import run_virtual_strategy

if TYPE_CHECKING:
    from src.strategy.pine_v2.compat import V2RunResult


class TrackRunner:
    """Track S/A/M → runner 함수 매핑 + 통합 invoke()."""

    # dict registry — object identity 보존 (`is` 비교 통과).
    # S/M 은 같은 run_historical 을 가리킴 (compat.py:109+127 동일 분기 통합).
    _dispatch_table: ClassVar[dict[Track, Callable[..., Any]]] = {
        "S": run_historical,
        "A": run_virtual_strategy,
        "M": run_historical,
    }

    @classmethod
    def invoke(
        cls,
        track: Track,
        *,
        source: str,
        ohlcv: Any,
        **kwargs: Any,
    ) -> V2RunResult:
        """track 에 매칭되는 runner 호출 후 V2RunResult 반환.

        kwargs 는 그대로 forward — D2 sizing (initial_capital /
        default_qty_type / default_qty_value) + sessions_allowed + strict 등
        runner 가 수용하는 모든 인자.

        unknown track 시 ValueError raise (compat.py:137 형식 보존).

        Note: V2RunResult import 는 함수 안에서 — module-level 시 compat.py 와
        circular import 발생 (compat → track_runner → compat).
        """
        from src.strategy.pine_v2.compat import V2RunResult

        runner = cls._dispatch_table.get(track)
        if runner is None:
            raise ValueError(
                f"parse_and_run_v2: unknown script track (track={track!r})"
            )

        result = runner(source, ohlcv, **kwargs)

        if track == "A":
            return V2RunResult(track=track, virtual=result)
        return V2RunResult(track=track, historical=result)
