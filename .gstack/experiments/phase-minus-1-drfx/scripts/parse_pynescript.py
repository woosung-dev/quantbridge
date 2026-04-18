"""E2 — pynescript 파서 커버리지 측정.

corpus/ 내 6개 .pine 스크립트를 pynescript로 파싱 시도하여 AST 생성 성공률 + 미지원 노드 종류를 기록한다.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from pynescript import ast as pyne_ast

PYNESCRIPT_VERSION = "0.3.0"

CORPUS = Path(__file__).resolve().parents[1] / "corpus"
OUT_PATH = Path(__file__).resolve().parents[1] / "output" / "e2_pynescript_coverage.md"
JSON_PATH = OUT_PATH.with_suffix(".json")


def count_nodes(tree) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in pyne_ast.walk(tree):
        name = type(node).__name__
        counts[name] = counts.get(name, 0) + 1
    return counts


def parse_one(path: Path) -> dict:
    source = path.read_text(encoding="utf-8")
    rec: dict = {"file": path.name, "size": len(source)}
    try:
        tree = pyne_ast.parse(source)
        rec["ok"] = True
        rec["node_types"] = len(set(type(n).__name__ for n in pyne_ast.walk(tree)))
        rec["node_counts"] = count_nodes(tree)
    except Exception as e:
        rec["ok"] = False
        rec["error_class"] = type(e).__name__
        rec["error_msg"] = str(e)[:300]
        rec["trace_tail"] = traceback.format_exc().splitlines()[-3:]
    return rec


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(CORPUS.glob("*.pine"))
    results = [parse_one(f) for f in files]

    JSON_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    lines = ["# E2 — pynescript 파서 커버리지", "", f"pynescript: `{PYNESCRIPT_VERSION}`", "", "| 파일 | 크기 | 파싱 | 노드 종류 | 총 노드 | 에러 |", "|------|:---:|:--:|:---:|:---:|------|"]
    for r in results:
        if r["ok"]:
            total = sum(r["node_counts"].values())
            lines.append(f"| {r['file']} | {r['size']}B | ✅ | {r['node_types']} | {total} | — |")
        else:
            lines.append(f"| {r['file']} | {r['size']}B | ❌ | — | — | {r['error_class']}: {r['error_msg'][:80]} |")

    lines.append("")
    lines.append("## 파싱 실패 상세")
    for r in results:
        if not r["ok"]:
            lines.append(f"\n### {r['file']}\n```\n{r['error_class']}: {r['error_msg']}\n...\n{chr(10).join(r['trace_tail'])}\n```")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"written: {OUT_PATH}")
    for r in results:
        status = "✅" if r["ok"] else "❌"
        print(f"  {status} {r['file']:30} " + (f"{r.get('node_types', 0)} types, {sum(r.get('node_counts', {}).values())} nodes" if r["ok"] else r["error_class"]))


if __name__ == "__main__":
    main()
