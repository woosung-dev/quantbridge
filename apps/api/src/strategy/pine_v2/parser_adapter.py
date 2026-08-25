"""pynescript 파스 어댑터 — 백테스트 파싱 진입점은 이 파일 하나다.

AST 노드 `isinstance` 판정에는 여러 모듈의 pynescript 공개 API import가 필요하다.

캐시는 2층이다 (BL-832).
- **L1** `lru_cache(maxsize=8)` — 프로세스 안. n13이 백테스트 1회의 파스를 4→1로 만든 층이다.
- **L2** 디스크 — 프로세스 **밖**. L1은 프로세스가 바뀌면 통째로 사라지는데, 콜드 파스 1회는
  실측상 `s5_ema_trend` 2.69초 · `s3_rsid` 11.47초 · `i3_drfx`(38,954B) **53.38초**다.
  celery `worker_max_tasks_per_child`가 워커를 주기적으로 재활용하고 uvicorn 워커·테스트
  프로세스가 각각 자기 콜드를 물기 때문에, 프로세스 경계는 실제로 자주 넘는다.

★**그 초는 「느린 코드」가 아니라 ANTLR 런타임의 ATN 클로저 계산이다** — `s3_rsid` cProfile에서
`ParserATNSimulator.closure_`의 cumtime이 35.77/36.96초(96.8%)다. 따라서 파서 층을 손대는
축(SLL 2단계·기동 워밍·문법 모호성 축소)은 이 성분을 못 건드린다([BL-829] 기각 tombstone).
줄이는 방법은 **다시 파싱하지 않는 것** 하나다.

★**캐시 키에 pynescript 버전과 스키마 버전이 들어간다** — 버전이 바뀌면 같은 소스라도 미스가
나야 한다. 안 그러면 업그레이드 후 낡은 AST가 조용히 살아남는다.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import pickle
import tempfile
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from pynescript import ast as pyne_ast

from src.core.config import settings

# 이 파일이 pickle로 저장하는 것의 구조가 바뀌면 올려라 — 옛 항목이 전부 미스가 된다.
_CACHE_SCHEMA_VERSION = "1"


def _pynescript_version() -> str:
    try:
        return version("pynescript")
    except PackageNotFoundError:  # pragma: no cover - 설치 경로가 깨진 경우
        return "unknown"


def _cache_key(source: str) -> str:
    """소스 + pynescript 버전 + 스키마 버전의 sha256."""
    material = "\0".join((_CACHE_SCHEMA_VERSION, _pynescript_version(), source)).encode()
    return hashlib.sha256(material).hexdigest()


def _cache_dir() -> Path | None:
    """설정된 캐시 디렉토리. 빈 값이면 None(비활성)."""
    raw = settings.pine_ast_cache_dir.strip()
    if not raw:
        return None
    return Path(raw)


def _load(path: Path) -> Any | None:
    """디스크에서 AST를 읽는다. 어떤 이유로든 실패하면 None — 캐시는 파스를 못 막는다.

    동시에 도는 프로세스가 쓰는 중일 수 있고 pynescript 업그레이드로 클래스가 사라졌을 수도
    있다. 캐시 실패는 **정상 경로로 떨어지는 것**이지 에러가 아니다.
    """
    try:
        return pickle.loads(path.read_bytes())  # noqa: S301 - 우리가 쓴 파일만 읽는다
    except Exception:
        with contextlib.suppress(OSError):
            path.unlink()
        return None


def _evict_if_over_budget(directory: Path, budget: int) -> None:
    """총 용량이 상한을 넘으면 mtime이 오래된 항목부터 지운다."""
    try:
        entries = [(p, p.stat()) for p in directory.glob("*.ast")]
    except OSError:
        return
    total = sum(st.st_size for _, st in entries)
    if total <= budget:
        return
    for path, st in sorted(entries, key=lambda pair: pair[1].st_mtime):
        try:
            path.unlink()
        except OSError:
            continue
        total -= st.st_size
        if total <= budget:
            return


def _store(path: Path, node: Any, budget: int) -> None:
    """원자적으로 쓴다 — 다른 프로세스가 반쯤 쓰인 파일을 읽으면 안 된다."""
    directory = path.parent
    try:
        directory.mkdir(parents=True, exist_ok=True)
        blob = pickle.dumps(node, protocol=pickle.HIGHEST_PROTOCOL)
        fd, tmp_name = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(blob)
            os.replace(tmp_name, path)
        except Exception:
            Path(tmp_name).unlink(missing_ok=True)
            raise
    except Exception:
        return
    _evict_if_over_budget(directory, budget)


@lru_cache(maxsize=8)
def parse_to_ast(source: str) -> Any:
    """Pine 소스를 pynescript AST로 변환. 반환 타입은 pynescript 내부 AST 노드."""
    directory = _cache_dir()
    path = directory / f"{_cache_key(source)}.ast" if directory is not None else None

    if path is not None and path.is_file():
        cached = _load(path)
        if cached is not None:
            return cached

    node = pyne_ast.parse(source)

    # 파스가 던지면 여기 오지 않는다 — 실패는 캐시되지 않는다.
    if path is not None:
        _store(path, node, settings.pine_ast_cache_max_bytes)
    return node
