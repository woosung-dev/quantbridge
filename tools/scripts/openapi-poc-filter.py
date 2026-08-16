#!/usr/bin/env python3
"""BL-717 PoC — contracts/openapi/openapi.json 에서 엔드포인트 3개만 추린 스키마를 만든다.

전체 스키마(63 엔드포인트)로 후보 3종을 돌리면 산출물이 커서 수기 타입과의
구조 diff 를 읽을 수 없다. PoC 는 health + strategies list + backtest detail 로
고정하고, $ref 폐포(transitive closure)를 따라 참조되는 components.schemas 만 남긴다.
출력도 export_openapi.py 와 같은 결정적 직렬화(키 정렬 · indent 2 · 개행 고정)다.

실행: python3 tools/scripts/openapi-poc-filter.py
출력: contracts/openapi/poc/openapi.poc.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "contracts" / "openapi" / "openapi.json"
OUTPUT = REPO_ROOT / "contracts" / "openapi" / "poc" / "openapi.poc.json"

# PoC 대상 — BL-717 처방의 「health + strategies list + backtest status 급」
KEEP: dict[str, list[str]] = {
    "/health": ["get"],
    "/api/v1/strategies": ["get"],
    "/api/v1/backtests/{backtest_id}": ["get"],
}

_REF_RE = re.compile(r"#/components/schemas/([^\"/]+)")


def _collect_refs(node: Any, found: set[str]) -> None:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            m = _REF_RE.match(ref)
            if m:
                found.add(m.group(1))
        for v in node.values():
            _collect_refs(v, found)
    elif isinstance(node, list):
        for v in node:
            _collect_refs(v, found)


def main() -> int:
    if not SOURCE.exists():
        print(
            f"원본 스키마가 없다: {SOURCE} — export_openapi.py 를 먼저 돌려라",
            file=sys.stderr,
        )
        return 2

    full = json.loads(SOURCE.read_text(encoding="utf-8"))

    paths: dict[str, Any] = {}
    for path, methods in KEEP.items():
        src = full["paths"].get(path)
        if src is None:
            print(f"경로가 스키마에 없다: {path}", file=sys.stderr)
            return 2
        kept = {m: src[m] for m in methods if m in src}
        if len(kept) != len(methods):
            print(f"메서드 누락: {path} {methods} vs {sorted(src)}", file=sys.stderr)
            return 2
        paths[path] = kept

    # $ref 폐포 — 새로 편입된 스키마가 또 참조하는 스키마까지 수렴할 때까지 돈다.
    all_schemas = full.get("components", {}).get("schemas", {})
    needed: set[str] = set()
    _collect_refs(paths, needed)
    while True:
        expanded = set(needed)
        for name in needed:
            if name in all_schemas:
                _collect_refs(all_schemas[name], expanded)
        if expanded == needed:
            break
        needed = expanded

    missing = sorted(n for n in needed if n not in all_schemas)
    if missing:
        print(f"$ref 대상이 components.schemas 에 없다: {missing}", file=sys.stderr)
        return 2

    poc = {
        "openapi": full["openapi"],
        "info": {
            **full["info"],
            "title": full["info"]["title"] + " (BL-717 PoC subset)",
        },
        "paths": paths,
        "components": {
            "schemas": {n: all_schemas[n] for n in sorted(needed)},
            **(
                {"securitySchemes": full["components"]["securitySchemes"]}
                if "securitySchemes" in full.get("components", {})
                else {}
            ),
        },
    }

    rendered = json.dumps(poc, sort_keys=True, indent=2, ensure_ascii=False) + "\n"

    # ★`--check` — 커밋된 부분집합이 현재 전량 export 에서 다시 뽑은 것과 같은가.
    #   2026-08-16 적대 리뷰가 이 2단이 **무게이트**임을 잡았다: `export_openapi.py --check`
    #   는 1단(전량 파일)만 보고, orval 이 실제로 읽는 것은 이 2단 산출물인데 아무도 안 봤다.
    #   그래서 실제로 drift 해 있었다(`warnings` 필드 누락).
    if "--check" in sys.argv[1:]:
        if not OUTPUT.exists():
            print(f"drift: {OUTPUT} 가 없다. 먼저 인자 없이 실행해라.", file=sys.stderr)
            return 1
        if OUTPUT.read_text(encoding="utf-8") == rendered:
            print(f"drift 없음: {OUTPUT} — 경로 {len(paths)}개 · 스키마 {len(needed)}개")
            return 0
        print(
            f"drift: 커밋된 {OUTPUT.name} 이 현재 전량 export 에서 뽑은 것과 다르다.\n"
            "  재생성: python3 tools/scripts/openapi-poc-filter.py",
            file=sys.stderr,
        )
        return 1

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"작성: {OUTPUT} — 경로 {len(paths)}개 · 스키마 {len(needed)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
