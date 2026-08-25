"""가장 느린 pine_v2 corpus의 함수별 cProfile 관측값을 보존한다."""

from __future__ import annotations

import ast
import cProfile
import json
import math
import os
import pstats
from functools import cache
from pathlib import Path
from time import perf_counter
from typing import Any

from tests.strategy.pine_v2.test_execution_speed import _CORPUS_DIR, _load_frozen_ohlcv

_HOTSPOTS_PATH = _CORPUS_DIR / "execution_hotspots.json"
_APP_ROOT = Path(__file__).parents[3]
_MEASURED_CORPUS = ("s3_rsid", "s5_ema_trend")
_HOTSPOT_LIMIT = 20
_REGEN_ENV = "REGEN_EXECUTION_HOTSPOTS"


def _normalize_file(filename: str) -> str:
    """pstats 파일명을 apps/api 기준 상대경로로 보존한다."""
    path = Path(filename)
    if not path.is_absolute():
        return filename
    try:
        return path.relative_to(_APP_ROOT).as_posix()
    except ValueError:
        return filename


def _function_key(filename: str, line: int, function: str) -> str:
    """동명 함수 충돌 없이 두 프로파일의 호출 수를 대응한다."""
    return f"{_normalize_file(filename)}:{line}:{function}"


def _profile_corpus(corpus_id: str) -> tuple[dict[str, Any], dict[str, int]]:
    """동결 OHLCV에서 한 corpus를 실행하고 누적 시간순 pstats 행을 추출한다."""
    from src.backtest.engine.v2_adapter import run_backtest_v2

    source = (_CORPUS_DIR / f"{corpus_id}.pine").read_text(encoding="utf-8")
    profiler = cProfile.Profile()
    started_at = perf_counter()
    outcome = profiler.runcall(run_backtest_v2, source, _load_frozen_ohlcv())
    total_seconds = perf_counter() - started_at

    assert outcome.status == "ok" and outcome.result is not None, (
        f"{corpus_id}: run_backtest_v2 status={outcome.status} error={outcome.error}"
    )

    stats = pstats.Stats(profiler).sort_stats(pstats.SortKey.CUMULATIVE)
    assert stats.fcn_list is not None

    rows: list[dict[str, Any]] = []
    call_counts: dict[str, int] = {}
    for filename, line, function in stats.fcn_list:
        call_count, _primitive_call_count, tottime, cumulative, _callers = stats.stats[
            (filename, line, function)
        ]
        normalized_file = _normalize_file(filename)
        rows.append(
            {
                "function": function,
                "file": normalized_file,
                "line": line,
                "call_count": call_count,
                "cumulative_seconds": cumulative,
                "tottime_seconds": tottime,
            }
        )
        call_counts[_function_key(filename, line, function)] = call_count

    return (
        {
            "total_seconds": total_seconds,
            "hotspots": rows[:_HOTSPOT_LIMIT],
        },
        call_counts,
    )


@cache
def _profiled_hotspots() -> dict[str, Any]:
    """두 corpus의 pstats 결과와 공통 함수 호출 수 비율을 묶는다."""
    profiled = {corpus_id: _profile_corpus(corpus_id) for corpus_id in _MEASURED_CORPUS}
    call_counts = {corpus_id: profiled[corpus_id][1] for corpus_id in _MEASURED_CORPUS}
    common_functions = sorted(set.intersection(*(set(counts) for counts in call_counts.values())))

    return {corpus_id: profiled[corpus_id][0] for corpus_id in _MEASURED_CORPUS} | {
        "call_count_ratio": {
            function: {
                "s3_rsid": call_counts["s3_rsid"][function],
                "s5_ema_trend": call_counts["s5_ema_trend"][function],
                "ratio": call_counts["s3_rsid"][function] / call_counts["s5_ema_trend"][function],
            }
            for function in common_functions
            if call_counts["s5_ema_trend"][function] > 0
        }
    }


def _load_hotspots() -> dict[str, Any]:
    assert _HOTSPOTS_PATH.exists(), (
        "hotspot 프로파일 결과가 없습니다. "
        f"{_REGEN_ENV}=1 uv run pytest tests/strategy/pine_v2/test_execution_hotspots.py -q 로 생성하세요."
    )
    return json.loads(_HOTSPOTS_PATH.read_text(encoding="utf-8"))


def _write_hotspots(hotspots: dict[str, Any]) -> None:
    _HOTSPOTS_PATH.write_text(
        json.dumps(hotspots, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _function_coordinates(path: Path) -> set[tuple[str, int]]:
    """AST에서 phantom 검증에 쓸 함수명·정의 줄 좌표를 수집한다."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    coordinates: set[tuple[str, int]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        coordinates.add((node.name, node.lineno))
        coordinates.update((node.name, decorator.lineno) for decorator in node.decorator_list)
    return coordinates


def test_profiled_hotspots_include_project_source() -> None:
    """pstats 누적 시간 상위 함수에는 최소 하나의 pine_v2 소스 함수가 있다."""
    profiled = _profiled_hotspots()

    for corpus_id in _MEASURED_CORPUS:
        hotspots = profiled[corpus_id]["hotspots"]
        assert len(hotspots) >= 5
        assert all(item["cumulative_seconds"] > 0 for item in hotspots)
        assert any(item["file"].startswith("src/") for item in hotspots[:5]), (
            f"{corpus_id}: 상위 5개가 전부 프로젝트 밖 함수입니다: "
            f"{[item['file'] for item in hotspots[:5]]}"
        )

    if os.environ.get(_REGEN_ENV) == "1":
        _write_hotspots(profiled)


def test_execution_hotspot_json_source_coordinates_are_real() -> None:
    """기록된 src 함수 좌표는 현재 소스 AST에 실제로 존재해야 한다."""
    hotspots = _load_hotspots()

    assert set(_MEASURED_CORPUS).issubset(hotspots)
    assert hotspots["call_count_ratio"]
    for corpus_id in _MEASURED_CORPUS:
        rows = hotspots[corpus_id]["hotspots"]
        assert len(rows) >= 5
        assert all(item["cumulative_seconds"] > 0 for item in rows)
        assert any(item["file"].startswith("src/") for item in rows[:5])

        for item in rows:
            if not item["file"].startswith("src/"):
                continue
            source_path = _APP_ROOT / item["file"]
            assert source_path.is_file(), f"{corpus_id}: source 파일이 없습니다: {source_path}"
            assert (item["function"], item["line"]) in _function_coordinates(source_path), (
                f"{corpus_id}: phantom hotspot 좌표 "
                f"{item['file']}:{item['line']} {item['function']}"
            )

    for function, counts in hotspots["call_count_ratio"].items():
        assert set(counts) == {"s3_rsid", "s5_ema_trend", "ratio"}, function
        assert counts["s3_rsid"] > 0 and counts["s5_ema_trend"] > 0, function
        assert math.isclose(
            counts["ratio"],
            counts["s3_rsid"] / counts["s5_ema_trend"],
            rel_tol=1e-12,
        ), function
